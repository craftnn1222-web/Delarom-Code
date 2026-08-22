"""Trade Companies — player-owned trading houses.

A player charters a Trade Company for a founding fee (2500g).  The
company runs one or more Routes between two cities:  it BUYS a good
from the source city's stockpile at the city's import price and SELLS
in the destination at that city's retail price.  The spread is profit.

Ticks
-----
Every 6-hour economy tick, each active route attempts to run once:
    • If source-city stockpile has ≥ units_per_run, the company
      "purchases" that stock.  Stockpile drops, treasury pays out.
    • Sell revenue = dest-city import price × 1.30  (standard shop
      markup).  If dest has no active import for the good, use the
      good's default_base_cost × 1.4 as a floor sell price.
    • treasury += (revenue − cost);  route.last_run_at updated.
    • activity + revenue recorded on the current-period ledger.

Weekly ledger
-------------
Each company has a rolling weekly ledger.  When `run_trade_ticks`
sees a company whose `next_ledger_at` has passed, it closes the
current period, computes `net_profit` (revenue − costs for the
window), pays a dividend  =  min(treasury, max(0, net_profit))  /
total_shares  to every shareholder in `user.currency`, and rolls
`next_ledger_at` forward 7 days.

Shareholders
------------
Anyone (including the founder) may invest with `POST /invest`.  Shares
are granted at 100g per share.  Investment gold flows into the
treasury.  Dissolving a company (founder-only) refunds the treasury
proportionally to all shareholders.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


CHARTER_FEE = 2500                   # gold
MIN_INVEST_GOLD = 100                # gold — 1 share
SHARE_PRICE = 100                    # gold per share
LEDGER_PERIOD_HOURS = 24 * 7         # weekly close
DEFAULT_UNITS_PER_RUN = 20
MAX_ROUTES_PER_COMPANY = 8
STATUS_ACTIVE = "active"
STATUS_DISSOLVED = "dissolved"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60] or f"co-{uuid.uuid4().hex[:8]}"


# ── service class ────────────────────────────────────────────────


class TradeCompanyService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # ── charter / lifecycle ─────────────────────────────────

    async def charter(
        self,
        *,
        founder_user: Dict,
        founder_character: Dict,
        name: str,
        motto: str,
        home_nation: str,
        sigil: str,
        color: str,
    ) -> Dict:
        # Founder must be able to pay the charter fee
        user = await self.db.users.find_one({"id": founder_user["id"]}, {"_id": 0})
        if not user:
            raise ValueError("Founder user not found.")
        wallet = int(user.get("currency", 0))
        if wallet < CHARTER_FEE:
            raise ValueError(
                f"You need {CHARTER_FEE}g to charter a Trade Company. "
                f"You have {wallet}g.",
            )

        # Unique slug
        base_slug = _slugify(name)
        slug = base_slug
        i = 2
        while await self.db.trade_companies.find_one({"slug": slug}, {"_id": 0, "id": 1}):
            slug = f"{base_slug}-{i}"
            i += 1

        now = _now_iso()
        next_ledger = (datetime.now(timezone.utc) + timedelta(hours=LEDGER_PERIOD_HOURS)).isoformat()

        company_id = str(uuid.uuid4())
        company = {
            "id": company_id,
            "slug": slug,
            "name": name.strip()[:100],
            "motto": motto.strip()[:200],
            "home_nation": home_nation,
            "sigil": sigil or "coins",
            "color": color or "#f59e0b",
            "founder_user_id": founder_user["id"],
            "founder_character_id": founder_character["id"],
            "founder_character_name": founder_character.get("name", ""),
            "is_npc": False,
            "treasury": 0,
            "status": STATUS_ACTIVE,
            "created_at": now,
            "dissolved_at": None,
            "period_start": now,
            "next_ledger_at": next_ledger,
            "period_revenue": 0,
            "period_costs": 0,
            "period_dividends_paid": 0,
            "lifetime_revenue": 0,
            "lifetime_costs": 0,
            "lifetime_dividends_paid": 0,
        }
        await self.db.trade_companies.insert_one(dict(company))

        # Debit charter fee from founder
        await self.db.users.update_one(
            {"id": founder_user["id"]}, {"$inc": {"currency": -CHARTER_FEE}},
        )

        # Founder receives their contribution as initial shares
        founder_shares = CHARTER_FEE // SHARE_PRICE
        await self._grant_shares(
            company_id=company_id,
            user_id=founder_user["id"],
            character_id=founder_character["id"],
            shares=founder_shares,
            invested_gold=CHARTER_FEE,
        )
        # The 2500g charter fee flows into the company treasury as seed capital.
        await self.db.trade_companies.update_one(
            {"id": company_id},
            {"$inc": {"treasury": CHARTER_FEE}},
        )

        await self._log_activity(
            company_id=company_id,
            kind="charter",
            meta={"founder_user_id": founder_user["id"], "fee": CHARTER_FEE},
        )
        return await self.get_company(company_id)

    async def dissolve(self, *, company_id: str, user_id: str) -> Dict:
        c = await self.get_company(company_id)
        if not c:
            raise ValueError("Trade company not found.")
        if c["founder_user_id"] != user_id:
            raise ValueError("Only the founder may dissolve the company.")
        if c["status"] != STATUS_ACTIVE:
            raise ValueError("This company is already dissolved.")

        # Refund treasury proportional to shares
        treasury = int(c.get("treasury", 0))
        shareholders = await self.list_shareholders(company_id)
        total_shares = sum(int(s["shares"]) for s in shareholders) or 1
        refunds = []
        for s in shareholders:
            payout = int(treasury * (int(s["shares"]) / total_shares))
            if payout > 0:
                await self.db.users.update_one(
                    {"id": s["user_id"]}, {"$inc": {"currency": payout}},
                )
                refunds.append({"user_id": s["user_id"], "payout": payout})

        await self.db.trade_companies.update_one(
            {"id": company_id},
            {"$set": {
                "status": STATUS_DISSOLVED,
                "dissolved_at": _now_iso(),
                "treasury": 0,
            }},
        )
        # Disable all routes
        await self.db.trade_company_routes.update_many(
            {"company_id": company_id},
            {"$set": {"is_active": False}},
        )
        await self._log_activity(
            company_id=company_id, kind="dissolve",
            meta={"refunds": refunds, "total_refunded": sum(r["payout"] for r in refunds)},
        )
        return await self.get_company(company_id)

    # ── shares / invest ────────────────────────────────────

    async def invest(
        self,
        *,
        company_id: str,
        user_id: str,
        character_id: str,
        gold: int,
    ) -> Dict:
        if gold < MIN_INVEST_GOLD:
            raise ValueError(f"Minimum investment is {MIN_INVEST_GOLD}g.")
        c = await self.get_company(company_id)
        if not c:
            raise ValueError("Trade company not found.")
        if c["status"] != STATUS_ACTIVE:
            raise ValueError("This company is no longer active.")
        if c.get("is_npc"):
            raise ValueError("NPC houses do not accept outside investment.")

        char = await self.db.characters.find_one(
            {"id": character_id, "user_id": user_id}, {"_id": 0},
        )
        if not char:
            raise ValueError("Character not found (or not owned by you).")

        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        wallet = int((user or {}).get("currency", 0))
        if wallet < gold:
            raise ValueError(f"You have only {wallet}g.")

        shares = gold // SHARE_PRICE
        if shares <= 0:
            raise ValueError(f"You must invest at least {SHARE_PRICE}g for one share.")
        actual_gold = shares * SHARE_PRICE

        await self.db.users.update_one(
            {"id": user_id}, {"$inc": {"currency": -actual_gold}},
        )
        await self.db.trade_companies.update_one(
            {"id": company_id}, {"$inc": {"treasury": actual_gold}},
        )
        await self._grant_shares(
            company_id=company_id,
            user_id=user_id,
            character_id=character_id,
            shares=shares,
            invested_gold=actual_gold,
        )
        await self._log_activity(
            company_id=company_id, kind="invest",
            meta={"user_id": user_id, "gold": actual_gold, "shares": shares},
        )
        return await self.get_company(company_id)

    async def _grant_shares(
        self,
        *,
        company_id: str,
        user_id: str,
        character_id: str,
        shares: int,
        invested_gold: int,
    ) -> None:
        existing = await self.db.trade_company_shareholders.find_one(
            {"company_id": company_id, "user_id": user_id},
            {"_id": 0, "id": 1, "shares": 1, "invested_gold": 1},
        )
        if existing:
            await self.db.trade_company_shareholders.update_one(
                {"id": existing["id"]},
                {"$inc": {"shares": int(shares), "invested_gold": int(invested_gold)},
                 "$set": {"character_id": character_id, "updated_at": _now_iso()}},
            )
        else:
            await self.db.trade_company_shareholders.insert_one({
                "id": str(uuid.uuid4()),
                "company_id": company_id,
                "user_id": user_id,
                "character_id": character_id,
                "shares": int(shares),
                "invested_gold": int(invested_gold),
                "joined_at": _now_iso(),
            })

    async def list_shareholders(self, company_id: str) -> List[Dict]:
        return await self.db.trade_company_shareholders.find(
            {"company_id": company_id}, {"_id": 0},
        ).sort("shares", -1).to_list(200)

    # ── routes ─────────────────────────────────────────────

    async def add_route(
        self,
        *,
        company_id: str,
        user_id: str,
        source_nation: str,
        source_city_slug: str,
        dest_nation: str,
        dest_city_slug: str,
        good_slug: str,
        units_per_run: int = DEFAULT_UNITS_PER_RUN,
    ) -> Dict:
        c = await self.get_company(company_id)
        if not c:
            raise ValueError("Trade company not found.")
        if c["founder_user_id"] != user_id:
            raise ValueError("Only the founder may add routes.")
        if c["status"] != STATUS_ACTIVE:
            raise ValueError("This company is no longer active.")
        route_count = await self.db.trade_company_routes.count_documents(
            {"company_id": company_id},
        )
        if route_count >= MAX_ROUTES_PER_COMPANY:
            raise ValueError(f"Companies are capped at {MAX_ROUTES_PER_COMPANY} routes.")
        if source_nation == dest_nation and source_city_slug == dest_city_slug:
            raise ValueError("Source and destination must be different cities.")
        good = await self.db.goods.find_one({"slug": good_slug}, {"_id": 0, "slug": 1})
        if not good:
            raise ValueError(f"Unknown good '{good_slug}'.")
        route = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "source_nation": source_nation,
            "source_city_slug": source_city_slug,
            "dest_nation": dest_nation,
            "dest_city_slug": dest_city_slug,
            "good_slug": good_slug,
            "units_per_run": max(1, min(200, int(units_per_run))),
            "is_active": True,
            "last_run_at": None,
            "last_run_result": None,
            "runs_total": 0,
            "created_at": _now_iso(),
        }
        await self.db.trade_company_routes.insert_one(dict(route))
        return route

    async def list_routes(self, company_id: str) -> List[Dict]:
        return await self.db.trade_company_routes.find(
            {"company_id": company_id}, {"_id": 0},
        ).sort("created_at", 1).to_list(50)

    async def toggle_route(
        self, *, company_id: str, route_id: str, user_id: str,
    ) -> Dict:
        c = await self.get_company(company_id)
        if not c:
            raise ValueError("Trade company not found.")
        if c["founder_user_id"] != user_id:
            raise ValueError("Only the founder may toggle routes.")
        route = await self.db.trade_company_routes.find_one(
            {"id": route_id, "company_id": company_id}, {"_id": 0},
        )
        if not route:
            raise ValueError("Route not found.")
        new_active = not bool(route.get("is_active"))
        await self.db.trade_company_routes.update_one(
            {"id": route_id}, {"$set": {"is_active": new_active}},
        )
        return {**route, "is_active": new_active}

    async def delete_route(
        self, *, company_id: str, route_id: str, user_id: str,
    ) -> Dict:
        c = await self.get_company(company_id)
        if not c:
            raise ValueError("Trade company not found.")
        if c["founder_user_id"] != user_id:
            raise ValueError("Only the founder may remove routes.")
        r = await self.db.trade_company_routes.find_one_and_delete(
            {"id": route_id, "company_id": company_id},
        )
        if not r:
            raise ValueError("Route not found.")
        return {"deleted": True}

    # ── reads ──────────────────────────────────────────────

    async def get_company(self, company_id: str) -> Optional[Dict]:
        return await self.db.trade_companies.find_one({"id": company_id}, {"_id": 0})

    async def get_company_by_slug(self, slug: str) -> Optional[Dict]:
        return await self.db.trade_companies.find_one({"slug": slug}, {"_id": 0})

    async def list_companies(self, *, status: Optional[str] = None) -> List[Dict]:
        q: Dict = {}
        if status:
            q["status"] = status
        else:
            q["status"] = STATUS_ACTIVE
        return await self.db.trade_companies.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

    async def list_activity(self, company_id: str, limit: int = 60) -> List[Dict]:
        return await self.db.trade_company_activity.find(
            {"company_id": company_id}, {"_id": 0},
        ).sort("at", -1).limit(max(1, min(200, limit))).to_list(limit)

    async def list_ledgers(self, company_id: str, limit: int = 12) -> List[Dict]:
        return await self.db.trade_company_ledger.find(
            {"company_id": company_id}, {"_id": 0},
        ).sort("period_start", -1).limit(max(1, min(60, limit))).to_list(limit)

    async def _log_activity(
        self, *, company_id: str, kind: str, meta: Dict,
    ) -> None:
        await self.db.trade_company_activity.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "kind": kind,
            "at": _now_iso(),
            "meta": meta,
        })


# ── economy-tick integration ─────────────────────────────────────


async def _get_import_price(db, nation: str, city_slug: str, good_slug: str) -> Optional[int]:
    """Cheapest active import price for a good in a city, or None."""
    row = await db.city_market_prices.find_one(
        {"nation": nation, "city_slug": city_slug, "good_slug": good_slug},
        {"_id": 0, "import_price": 1, "is_available": 1},
    )
    if row and row.get("is_available") and row.get("import_price") is not None:
        return int(row["import_price"])
    return None


async def _get_good_default_cost(db, good_slug: str) -> int:
    row = await db.goods.find_one(
        {"slug": good_slug}, {"_id": 0, "default_base_cost": 1},
    )
    return int((row or {}).get("default_base_cost", 20))


async def _run_single_route(db, company: Dict, route: Dict) -> Dict:
    """Attempt to run one route once. Returns a status dict."""
    from producers_service import EconomyProducers, OWNER_CITY

    # ── Black-market short-circuit ────────────────────────
    # If the good is banned in the destination nation, this becomes a
    # smuggling attempt with 3× reward but a 30% seizure risk.
    try:
        from black_market import evaluate_route as _bm_evaluate
        bm = await _bm_evaluate(db, company, route)
        if bm is not None:
            return bm
    except Exception as e:  # pragma: no cover
        logger.warning(f"black-market evaluation failed: {e}")

    good_slug = route["good_slug"]
    units = int(route["units_per_run"])
    src_nation, src_city = route["source_nation"], route["source_city_slug"]
    dst_nation, dst_city = route["dest_nation"], route["dest_city_slug"]

    prods = EconomyProducers(db)

    # 1. Check source stock
    stock = await prods.get_inventory(
        owner_type=OWNER_CITY, owner_key=f"{src_nation}:{src_city}", good_slug=good_slug,
    )
    if stock < units:
        return {"ok": False, "reason": "no_stock", "stock": stock, "needed": units}

    # 2. Compute buy & sell prices
    buy_unit = await _get_import_price(db, src_nation, src_city, good_slug)
    default_cost = await _get_good_default_cost(db, good_slug)
    if buy_unit is None:
        buy_unit = default_cost  # source has native production but no import
    sell_unit_import = await _get_import_price(db, dst_nation, dst_city, good_slug)
    if sell_unit_import is None:
        # No import at destination — sell at default_base_cost × 1.4 (opportunity)
        sell_unit = int(round(default_cost * 1.4))
    else:
        sell_unit = int(round(sell_unit_import * 1.30))

    cost_total = buy_unit * units
    revenue_total = sell_unit * units
    profit = revenue_total - cost_total

    # 3. Company must be able to cover the buy cost
    treasury = int(company.get("treasury", 0))
    if treasury < cost_total:
        return {"ok": False, "reason": "insufficient_treasury", "needed": cost_total, "treasury": treasury}

    # 4. Draw stock, move money
    drew = await prods.draw_from_inventory(
        owner_type=OWNER_CITY, owner_key=f"{src_nation}:{src_city}",
        nation=src_nation, good_slug=good_slug, units=units,
    )
    if not drew:
        return {"ok": False, "reason": "stock_race", "stock": stock, "needed": units}

    await db.trade_companies.update_one(
        {"id": company["id"]},
        {"$inc": {
            "treasury": profit,
            "period_revenue": revenue_total,
            "period_costs": cost_total,
            "lifetime_revenue": revenue_total,
            "lifetime_costs": cost_total,
        }},
    )
    await db.trade_company_routes.update_one(
        {"id": route["id"]},
        {"$set": {
            "last_run_at": _now_iso(),
            "last_run_result": {
                "units": units,
                "buy_unit": buy_unit,
                "sell_unit": sell_unit,
                "profit": profit,
            },
        },
         "$inc": {"runs_total": 1}},
    )
    await db.trade_company_activity.insert_one({
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "kind": "route_run",
        "at": _now_iso(),
        "meta": {
            "route_id": route["id"],
            "good_slug": good_slug,
            "units": units,
            "buy_unit": buy_unit,
            "sell_unit": sell_unit,
            "revenue": revenue_total,
            "cost": cost_total,
            "profit": profit,
        },
    })
    return {"ok": True, "profit": profit, "revenue": revenue_total, "cost": cost_total}


async def _close_ledger_if_due(db, company: Dict) -> Optional[Dict]:
    """If `next_ledger_at` has elapsed, close the current period,
    compute dividends, credit shareholders. Returns the ledger doc or None."""
    due = _parse_iso(company.get("next_ledger_at") or "")
    if not due or due > datetime.now(timezone.utc):
        return None

    revenue = int(company.get("period_revenue", 0))
    costs = int(company.get("period_costs", 0))
    net_profit = revenue - costs
    treasury = int(company.get("treasury", 0))

    dividend_pool = max(0, min(treasury, net_profit))
    shareholders = await db.trade_company_shareholders.find(
        {"company_id": company["id"]}, {"_id": 0},
    ).to_list(200)
    total_shares = sum(int(s["shares"]) for s in shareholders) or 1
    per_share = dividend_pool // total_shares if total_shares else 0
    dividends_paid = 0

    if per_share > 0:
        for s in shareholders:
            payout = int(s["shares"]) * per_share
            if payout > 0:
                await db.users.update_one(
                    {"id": s["user_id"]}, {"$inc": {"currency": payout}},
                )
                dividends_paid += payout

    period_start = company.get("period_start") or company.get("created_at")
    now = _now_iso()
    next_ledger = (datetime.now(timezone.utc) + timedelta(hours=LEDGER_PERIOD_HOURS)).isoformat()

    ledger = {
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "period_start": period_start,
        "period_end": now,
        "revenue": revenue,
        "costs": costs,
        "net_profit": net_profit,
        "per_share_dividend": per_share,
        "dividends_paid": dividends_paid,
        "closed_at": now,
    }
    await db.trade_company_ledger.insert_one(dict(ledger))

    # Reset the period on the company
    await db.trade_companies.update_one(
        {"id": company["id"]},
        {"$set": {
            "period_start": now,
            "next_ledger_at": next_ledger,
            "period_revenue": 0,
            "period_costs": 0,
            "period_dividends_paid": dividends_paid,
        },
         "$inc": {
             "treasury": -dividends_paid,
             "lifetime_dividends_paid": dividends_paid,
         }},
    )
    await db.trade_company_activity.insert_one({
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "kind": "dividend",
        "at": now,
        "meta": {
            "per_share": per_share,
            "shareholders": len(shareholders),
            "paid": dividends_paid,
            "net_profit": net_profit,
        },
    })
    return ledger


async def run_trade_ticks(
    db, *, tick_id: str, tick_at: str,
) -> Dict:
    """Called by producers_service.EconomyProducers.run_tick after
    inventories are refilled. Runs every active route once, then closes
    any ledgers that are due."""
    routes_attempted = 0
    routes_completed = 0
    routes_failed = 0
    ledgers_closed = 0
    total_profit = 0
    failures: List[Dict] = []

    async for company in db.trade_companies.find(
        {"status": STATUS_ACTIVE}, {"_id": 0},
    ):
        # Ledger close first (so this period isn't polluted by this tick's runs)
        ledger = await _close_ledger_if_due(db, company)
        if ledger:
            ledgers_closed += 1
            # Refresh company view for post-close routes
            company = await db.trade_companies.find_one(
                {"id": company["id"]}, {"_id": 0},
            )

        async for route in db.trade_company_routes.find(
            {"company_id": company["id"], "is_active": True}, {"_id": 0},
        ):
            routes_attempted += 1
            res = await _run_single_route(db, company, route)
            if res.get("ok"):
                routes_completed += 1
                total_profit += int(res.get("profit", 0))
                # Refresh company treasury view mid-loop
                company = await db.trade_companies.find_one(
                    {"id": company["id"]}, {"_id": 0},
                )
            else:
                routes_failed += 1
                failures.append({
                    "company_id": company["id"],
                    "route_id": route["id"],
                    "reason": res.get("reason"),
                })

    return {
        "routes_attempted": routes_attempted,
        "routes_completed": routes_completed,
        "routes_failed": routes_failed,
        "ledgers_closed": ledgers_closed,
        "total_profit": total_profit,
        "failures": failures[:20],
    }
