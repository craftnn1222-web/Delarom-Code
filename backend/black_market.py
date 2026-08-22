"""Black Market — contraband tables + tick-time smuggling rolls.

Certain goods are illegal to import in certain nations (see
`BANNED_GOODS_BY_NATION`). When a trade-company route delivers a
banned good to a banned nation, the route is treated as SMUGGLING:

    • Reward: sale price is multiplied by `SMUGGLE_PROFIT_MULT` (3×
      default) — the black-market markup is real.
    • Risk: on each smuggling run, a d100 is rolled. If it falls under
      `SEIZURE_PCT` (default 30), the goods are seized, the company
      pays a fine, and the founder's Renown in the destination city
      drops.
    • Logging: every smuggle attempt (win or seize) is written to
      `smuggling_events` so players can see the flow.

The `producers_service` tick calls `run_trade_ticks`, which calls
`black_market.evaluate_route()` for each active route. When a route is
smuggling, the standard buy/sell math is REPLACED by our version.
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Per user's tone spec — no over-designed catalogue, just canonical bans
# that mirror the lore already in the seed (elven/dwarven/undead tensions).
BANNED_GOODS_BY_NATION: Dict[str, List[str]] = {
    "selindori":     ["iron-swords", "steel-armor"],           # elves ban dwarven war-gear
    "dhor-kuldor":   ["silken-cloth", "rune-scrolls"],         # dwarves ban "elven decadence"
    "veiled-realms": ["gold-bullion", "fine-jewelry"],         # moon-elves keep silver primacy
    "ammeonon":      ["memory-crystals", "shadow-silk"],       # Ammeonon bans veil-realm exotica
    # Aigraels is contested — legally chaotic; no bans.
    "aigraels":      [],
}

SMUGGLE_PROFIT_MULT = 3.0
SEIZURE_PCT = 30                    # d100 roll under this → caught
FINE_PCT_OF_TREASURY = 25           # % of treasury on seizure (capped by MAX_FINE)
MAX_FINE = 800
RENOWN_DROP_ON_SEIZURE = 12


def is_contraband(dest_nation: str, good_slug: str) -> bool:
    banned = BANNED_GOODS_BY_NATION.get((dest_nation or "").lower(), [])
    return (good_slug or "").lower() in banned


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def evaluate_route(db, company: Dict, route: Dict) -> Optional[Dict]:
    """Called by trade_companies_service._run_single_route BEFORE its
    normal buy/sell logic. Returns:
        None                  → route is not contraband; run normally.
        {"ok": True, ...}     → smuggled successfully; use these numbers.
        {"ok": False, ...}    → seized; company already fined + logged.
    """
    dest_nation = route.get("dest_nation")
    good_slug = route.get("good_slug")
    if not is_contraband(dest_nation, good_slug):
        return None

    units = int(route.get("units_per_run", 0))
    src_nation, src_city = route["source_nation"], route["source_city_slug"]

    # Reuse producer stock check + import-price helpers via the trade module.
    from trade_companies_service import _get_import_price, _get_good_default_cost
    from producers_service import EconomyProducers, OWNER_CITY

    prods = EconomyProducers(db)
    stock = await prods.get_inventory(
        owner_type=OWNER_CITY,
        owner_key=f"{src_nation}:{src_city}",
        good_slug=good_slug,
    )
    if stock < units:
        return {"ok": False, "reason": "no_stock", "stock": stock, "needed": units}

    default_cost = await _get_good_default_cost(db, good_slug)
    buy_unit = await _get_import_price(db, src_nation, src_city, good_slug) or default_cost
    # Black-market sell price: 3× the default (banned goods run hot)
    sell_unit = int(round(default_cost * SMUGGLE_PROFIT_MULT))
    cost_total = buy_unit * units
    revenue_total = sell_unit * units

    if int(company.get("treasury", 0)) < cost_total:
        return {
            "ok": False,
            "reason": "insufficient_treasury",
            "needed": cost_total,
            "treasury": company.get("treasury", 0),
        }

    # ── Seizure roll ─────────────────────────────────────
    roll = random.randint(1, 100)
    seized = roll <= SEIZURE_PCT

    # Draw stock EITHER way — the goods left the source.
    drew = await prods.draw_from_inventory(
        owner_type=OWNER_CITY,
        owner_key=f"{src_nation}:{src_city}",
        nation=src_nation,
        good_slug=good_slug,
        units=units,
    )
    if not drew:
        return {"ok": False, "reason": "stock_race", "stock": stock}

    if seized:
        # Fine + Renown drop
        fine = min(MAX_FINE, max(50, int(company.get("treasury", 0)) * FINE_PCT_OF_TREASURY // 100))
        # Pay the buy cost + fine out of treasury (goods lost, gold lost)
        total_loss = cost_total + fine
        await db.trade_companies.update_one(
            {"id": company["id"]},
            {"$inc": {
                "treasury": -total_loss,
                "period_costs": total_loss,
                "lifetime_costs": total_loss,
            }},
        )
        # Founder Renown drops in the destination city (unless NPC)
        founder_char_id = company.get("founder_character_id")
        if founder_char_id and not str(founder_char_id).startswith("NPC:"):
            try:
                from reputation_web_service import ReputationWebService
                await ReputationWebService(db).adjust(
                    founder_char_id, "city", route["dest_city_slug"],
                    delta=-RENOWN_DROP_ON_SEIZURE,
                    reason=f"Caught smuggling {good_slug} into {route['dest_city_slug']}",
                )
            except Exception as e:  # pragma: no cover
                logger.warning(f"smuggling rep drop failed: {e}")
        await db.smuggling_events.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company["id"],
            "route_id": route["id"],
            "good_slug": good_slug,
            "dest_nation": route["dest_nation"],
            "dest_city_slug": route["dest_city_slug"],
            "outcome": "seized",
            "loss": total_loss,
            "roll": roll,
            "at": _now_iso(),
        })
        await db.trade_company_activity.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company["id"],
            "kind": "smuggle_seized",
            "at": _now_iso(),
            "meta": {
                "good_slug": good_slug,
                "dest": f"{route['dest_nation']}:{route['dest_city_slug']}",
                "loss": total_loss,
            },
        })
        await db.trade_company_routes.update_one(
            {"id": route["id"]},
            {"$set": {
                "last_run_at": _now_iso(),
                "last_run_result": {"units": units, "profit": -total_loss, "smuggled": True, "seized": True},
            },
             "$inc": {"runs_total": 1}},
        )
        return {"ok": False, "reason": "seized", "loss": total_loss, "roll": roll}

    # Successful smuggle
    profit = revenue_total - cost_total
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
                "smuggled": True,
            },
        },
         "$inc": {"runs_total": 1}},
    )
    await db.smuggling_events.insert_one({
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "route_id": route["id"],
        "good_slug": good_slug,
        "dest_nation": route["dest_nation"],
        "dest_city_slug": route["dest_city_slug"],
        "outcome": "success",
        "profit": profit,
        "roll": roll,
        "at": _now_iso(),
    })
    await db.trade_company_activity.insert_one({
        "id": str(uuid.uuid4()),
        "company_id": company["id"],
        "kind": "smuggle_success",
        "at": _now_iso(),
        "meta": {
            "good_slug": good_slug,
            "dest": f"{route['dest_nation']}:{route['dest_city_slug']}",
            "profit": profit,
            "units": units,
            "sell_unit": sell_unit,
        },
    })
    return {"ok": True, "profit": profit, "revenue": revenue_total, "cost": cost_total}
