"""Delarom Economy service.

Single source of truth for goods, faction production, and price propagation.

Two-step price chain
--------------------
    faction.base_cost
        ⟶ city.import_price  = base_cost × (1 + faction_to_city_tariff_pct/100)
            ⟶ shop.retail_price = import_price × (1 + shop.markup_pct/100)

Anything sourcing from a good is recomputed when:
  * a faction's base_cost changes (admin / AI / world event)
  * a standing contract is broken (e.g. by war / hostile diplomacy)
  * a contract is renegotiated (new tariff)
  * the sourcing shop's markup changes (auto-recomputed lazily on read)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from starter_economy import (
    CANONICAL_GOODS,
    STARTER_FACTION_SPECIALTIES,
    EVENT_CATEGORY_TAGS,
)


logger = logging.getLogger(__name__)

DEFAULT_FACTION_TO_CITY_TARIFF_PCT = 25  # cities pay 25% over base by default
DEFAULT_SHOP_MARKUP_PCT = 30             # shops add 30% on top of import price
PRICE_HISTORY_LIMIT = 25                 # rolling window per good


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────── Goods catalogue ───────────────────────────


class EconomyService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.goods = db.goods
        self.specialties = db.faction_specialties
        self.contracts = db.trade_contracts
        self.market_prices = db.city_market_prices  # cached city import prices
        self.cost_history = db.cost_history  # per (faction, good) deltas
        self.economy_events = db.economy_events  # AI-inferred event impacts log

    # ─── Catalogue seeding ───

    async def seed_canonical_goods(self) -> Dict:
        """Idempotent insert of the canonical good list. Returns count
        inserted vs already present."""
        inserted = 0
        skipped = 0
        for spec in CANONICAL_GOODS:
            existing = await self.goods.find_one({"slug": spec["slug"]}, {"_id": 0, "id": 1})
            if existing:
                skipped += 1
                continue
            doc = {
                "id": str(uuid.uuid4()),
                "created_at": _now_iso(),
                **spec,
            }
            await self.goods.insert_one(dict(doc))
            inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    async def seed_starter_specialties(self) -> Dict:
        """Idempotent: for each preset faction, write its specialties.
        Updates base_cost / capacity on re-run so admin can tune the seed
        without manual cleanup."""
        upserts = 0
        for faction_slug, specs in STARTER_FACTION_SPECIALTIES.items():
            faction = await self.db.factions.find_one(
                {"slug": faction_slug, "is_active": True}, {"_id": 0, "id": 1, "slug": 1, "name": 1},
            )
            if not faction:
                logger.info(f"Skipping specialty seed for unknown faction: {faction_slug}")
                continue
            for s in specs:
                payload = {
                    "faction_id": faction["id"],
                    "faction_slug": faction["slug"],
                    "good_slug": s["good_slug"],
                    "base_cost": s["base_cost"],
                    "capacity": s["capacity"],
                    "description": s.get("description", ""),
                    "last_cost_change_at": _now_iso(),
                }
                existing = await self.specialties.find_one(
                    {"faction_id": faction["id"], "good_slug": s["good_slug"]},
                    {"_id": 0, "id": 1},
                )
                if existing:
                    await self.specialties.update_one(
                        {"id": existing["id"]},
                        {"$set": payload},
                    )
                else:
                    await self.specialties.insert_one({
                        "id": str(uuid.uuid4()),
                        "created_at": _now_iso(),
                        "cost_history": [],
                        **payload,
                    })
                upserts += 1
        return {"upserts": upserts}

    # ─── Goods reads ───

    async def list_goods(self, category: Optional[str] = None) -> List[Dict]:
        q: Dict = {}
        if category:
            q["category"] = category
        cur = self.goods.find(q, {"_id": 0}).sort("name", 1)
        return await cur.to_list(200)

    async def get_good(self, good_slug: str) -> Optional[Dict]:
        return await self.goods.find_one({"slug": good_slug}, {"_id": 0})

    # ─── Faction specialties ───

    async def list_specialties_for_faction(self, faction_id: str) -> List[Dict]:
        return await self.specialties.find(
            {"faction_id": faction_id}, {"_id": 0},
        ).sort("good_slug", 1).to_list(50)

    async def list_specialties_for_good(self, good_slug: str) -> List[Dict]:
        return await self.specialties.find(
            {"good_slug": good_slug}, {"_id": 0},
        ).sort("base_cost", 1).to_list(50)

    async def upsert_specialty(
        self,
        *,
        faction_id: str,
        faction_slug: str,
        good_slug: str,
        base_cost: int,
        capacity: int = 50,
        description: str = "",
        reason: str = "manual",
    ) -> Dict:
        """Create or update a faction's offering of a good. Captures cost
        delta in cost_history. Triggers a re-propagation of dependent prices."""
        existing = await self.specialties.find_one(
            {"faction_id": faction_id, "good_slug": good_slug}, {"_id": 0},
        )
        if existing:
            old_cost = int(existing.get("base_cost", base_cost))
            if old_cost != base_cost:
                await self._append_cost_history(existing["id"], old_cost, base_cost, reason)
            await self.specialties.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "base_cost": base_cost,
                    "capacity": capacity,
                    "description": description or existing.get("description", ""),
                    "last_cost_change_at": _now_iso(),
                }},
            )
            doc = await self.specialties.find_one({"id": existing["id"]}, {"_id": 0})
        else:
            doc = {
                "id": str(uuid.uuid4()),
                "faction_id": faction_id,
                "faction_slug": faction_slug,
                "good_slug": good_slug,
                "base_cost": base_cost,
                "capacity": capacity,
                "description": description,
                "cost_history": [],
                "last_cost_change_at": _now_iso(),
                "created_at": _now_iso(),
            }
            await self.specialties.insert_one(dict(doc))
        # Cascade — recompute every city import price tied to this specialty.
        await self._recompute_for_good(good_slug)
        return doc

    async def remove_specialty(self, faction_id: str, good_slug: str) -> bool:
        result = await self.specialties.delete_one(
            {"faction_id": faction_id, "good_slug": good_slug}
        )
        if result.deleted_count > 0:
            await self._recompute_for_good(good_slug)
            return True
        return False

    async def _append_cost_history(
        self, specialty_id: str, from_cost: int, to_cost: int, reason: str,
    ) -> None:
        await self.specialties.update_one(
            {"id": specialty_id},
            {"$push": {
                "cost_history": {
                    "from": int(from_cost),
                    "to": int(to_cost),
                    "delta": int(to_cost - from_cost),
                    "reason": (reason or "")[:160],
                    "at": _now_iso(),
                },
            }},
        )
        # Mirror to global cost history collection for the Markets "top movers"
        await self.cost_history.insert_one({
            "id": str(uuid.uuid4()),
            "specialty_id": specialty_id,
            "from": int(from_cost),
            "to": int(to_cost),
            "delta": int(to_cost - from_cost),
            "reason": (reason or "")[:160],
            "at": _now_iso(),
        })

    # ─── Trade contracts ───

    async def create_standing_contract(
        self,
        *,
        from_faction_id: str,
        from_faction_slug: str,
        to_type: str,         # "city" | "faction"
        good_slug: str,
        to_city_slug: Optional[str] = None,
        to_nation: str = "",
        to_faction_id: Optional[str] = None,
        to_faction_slug: Optional[str] = None,
        tariff_pct: int = DEFAULT_FACTION_TO_CITY_TARIFF_PCT,
        quantity_per_tick: int = 50,
    ) -> Dict:
        spec = await self.specialties.find_one(
            {"faction_id": from_faction_id, "good_slug": good_slug}, {"_id": 0, "base_cost": 1},
        )
        if not spec:
            raise ValueError(f"Faction {from_faction_slug} does not produce {good_slug}")
        doc = {
            "id": str(uuid.uuid4()),
            "type": "standing",
            "from_faction_id": from_faction_id,
            "from_faction_slug": from_faction_slug,
            "to_type": to_type,
            "to_city_slug": to_city_slug,
            "to_nation": to_nation,
            "to_faction_id": to_faction_id,
            "to_faction_slug": to_faction_slug,
            "good_slug": good_slug,
            "base_cost_snapshot": int(spec.get("base_cost", 0)),
            "tariff_pct": int(tariff_pct),
            "quantity_per_tick": int(quantity_per_tick),
            "status": "active",
            "break_reason": None,
            "started_at": _now_iso(),
            "ended_at": None,
        }
        await self.contracts.insert_one(dict(doc))
        if to_type == "city" and to_city_slug:
            await self._recompute_city_good_price(to_nation, to_city_slug, good_slug)
        return doc

    async def seed_starter_contracts(
        self,
        *,
        cities_per_nation: int = 3,
        tariff_pct: int = 25,
    ) -> Dict:
        """Seed a spread of ACTIVE standing contracts so shop auto-pricing has
        live prices in every shop-picker nation. Idempotent — skips a
        (faction, good, city) combo that already has an active contract."""
        PICKER_NATIONS = ["aigraels", "dhor-kuldor", "selindori", "ammeonon"]
        specs = await self.specialties.find({}, {"_id": 0}).to_list(500)
        if not specs:
            return {"created": 0, "skipped": 0, "reason": "no faction specialties seeded"}

        fac_ids: Dict[str, str] = {}
        async for f in self.db.factions.find({}, {"_id": 0, "slug": 1, "id": 1}):
            fac_ids[f["slug"]] = f["id"]

        # De-duplicate near-identical city slugs (e.g. astra-lun / astralun).
        city_targets: List = []
        for n in PICKER_NATIONS:
            cs = await self.db.cities.find(
                {"nation": n}, {"_id": 0, "slug": 1, "name": 1},
            ).sort("name", 1).to_list(500)
            seen: set = set()
            chosen: List[str] = []
            for c in cs:
                key = (c.get("slug") or "").replace("-", "").lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                chosen.append(c["slug"])
                if len(chosen) >= cities_per_nation:
                    break
            for slug in chosen:
                city_targets.append((n, slug))

        created: List[Dict] = []
        skipped = 0
        for i, (nation, city) in enumerate(city_targets):
            spec = specs[i % len(specs)]
            fslug = spec.get("faction_slug")
            good = spec.get("good_slug")
            fid = spec.get("faction_id") or fac_ids.get(fslug)
            if not (fslug and good and fid):
                skipped += 1
                continue
            existing = await self.contracts.find_one({
                "from_faction_slug": fslug,
                "good_slug": good,
                "to_city_slug": city,
                "status": "active",
            })
            if existing:
                skipped += 1
                continue
            try:
                await self.create_standing_contract(
                    from_faction_id=fid,
                    from_faction_slug=fslug,
                    to_type="city",
                    good_slug=good,
                    to_city_slug=city,
                    to_nation=nation,
                    tariff_pct=tariff_pct,
                    quantity_per_tick=50,
                )
                created.append({"faction": fslug, "good": good, "nation": nation, "city": city})
            except ValueError:
                skipped += 1

        available = await self.market_prices.count_documents({"is_available": True})
        return {
            "created": len(created),
            "skipped": skipped,
            "contracts": created,
            "available_market_rows": available,
        }


    async def list_contracts(
        self,
        *,
        faction_id: Optional[str] = None,
        to_city_slug: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        q: Dict = {}
        if faction_id:
            q["$or"] = [{"from_faction_id": faction_id}, {"to_faction_id": faction_id}]
        if to_city_slug:
            q["to_city_slug"] = to_city_slug
        if status:
            q["status"] = status
        cur = self.contracts.find(q, {"_id": 0}).sort("started_at", -1)
        return await cur.to_list(200)

    async def break_contract(self, contract_id: str, reason: str = "") -> Optional[Dict]:
        contract = await self.contracts.find_one({"id": contract_id}, {"_id": 0})
        if not contract or contract["status"] != "active":
            return contract
        await self.contracts.update_one(
            {"id": contract_id},
            {"$set": {
                "status": "broken",
                "break_reason": (reason or "")[:200],
                "ended_at": _now_iso(),
            }},
        )
        if contract.get("to_type") == "city" and contract.get("to_city_slug"):
            await self._recompute_city_good_price(
                contract.get("to_nation", ""), contract["to_city_slug"], contract["good_slug"],
            )
        return await self.contracts.find_one({"id": contract_id}, {"_id": 0})

    async def break_contracts_for_hostile_factions(
        self, faction_a_id: str, faction_b_id: str, reason: str,
    ) -> int:
        """When two factions become hostile/sworn-enemies, break all standing
        contracts between them. Returns count broken."""
        cur = self.contracts.find({
            "status": "active",
            "$or": [
                {"from_faction_id": faction_a_id, "to_faction_id": faction_b_id},
                {"from_faction_id": faction_b_id, "to_faction_id": faction_a_id},
            ],
        }, {"_id": 0, "id": 1})
        rows = await cur.to_list(50)
        for r in rows:
            await self.break_contract(r["id"], reason=reason)
        return len(rows)

    # ─── City market prices ───

    async def _recompute_city_good_price(
        self, nation: str, city_slug: str, good_slug: str,
    ) -> Optional[Dict]:
        """Find the cheapest ACTIVE contract supplying this good to this city
        and cache its derived import price."""
        cheapest_contract = None
        cheapest_price = None
        cur = self.contracts.find({
            "to_type": "city",
            "to_city_slug": city_slug,
            "good_slug": good_slug,
            "status": "active",
        }, {"_id": 0})
        async for c in cur:
            # Always derive the import price from the LIVE base_cost on the
            # faction specialty so admin/AI changes propagate immediately.
            spec = await self.specialties.find_one(
                {"faction_id": c["from_faction_id"], "good_slug": good_slug},
                {"_id": 0, "base_cost": 1},
            )
            if not spec:
                continue
            base_cost = int(spec["base_cost"])
            tariff = int(c.get("tariff_pct", DEFAULT_FACTION_TO_CITY_TARIFF_PCT))
            price = round(base_cost * (1 + tariff / 100.0))
            if cheapest_price is None or price < cheapest_price:
                cheapest_price = price
                cheapest_contract = c

        existing = await self.market_prices.find_one(
            {"city_slug": city_slug, "good_slug": good_slug}, {"_id": 0},
        )
        if cheapest_contract is None:
            # No active contract → mark unavailable.
            doc = {
                "city_slug": city_slug,
                "nation": nation,
                "good_slug": good_slug,
                "import_price": None,
                "source_faction_slug": None,
                "source_contract_id": None,
                "is_available": False,
                "updated_at": _now_iso(),
            }
            if existing:
                await self.market_prices.update_one(
                    {"id": existing.get("id", existing.get("_id"))},
                    {"$set": doc},
                )
            else:
                await self.market_prices.insert_one({
                    "id": str(uuid.uuid4()),
                    **doc,
                })
            return doc

        doc = {
            "city_slug": city_slug,
            "nation": nation,
            "good_slug": good_slug,
            "import_price": cheapest_price,
            "source_faction_slug": cheapest_contract.get("from_faction_slug"),
            "source_contract_id": cheapest_contract.get("id"),
            "is_available": True,
            "updated_at": _now_iso(),
        }
        if existing:
            await self.market_prices.update_one(
                {"id": existing.get("id", existing.get("_id"))},
                {"$set": doc},
            )
        else:
            await self.market_prices.insert_one({
                "id": str(uuid.uuid4()),
                **doc,
            })
        return doc

    async def _recompute_for_good(self, good_slug: str) -> None:
        """Recompute every city's price for a given good (used after a
        base_cost change cascades)."""
        cur = self.contracts.find(
            {"good_slug": good_slug, "to_type": "city", "status": "active"},
            {"_id": 0, "to_nation": 1, "to_city_slug": 1},
        )
        seen: set = set()
        async for c in cur:
            key = (c.get("to_nation", ""), c.get("to_city_slug", ""))
            if key in seen or not key[1]:
                continue
            seen.add(key)
            await self._recompute_city_good_price(key[0], key[1], good_slug)

    async def get_city_market(
        self, nation: str, city_slug: str,
    ) -> List[Dict]:
        cur = self.market_prices.find(
            {"city_slug": city_slug, "nation": nation},
            {"_id": 0},
        ).sort("good_slug", 1)
        return await cur.to_list(200)

    async def get_good_in_city(
        self, nation: str, city_slug: str, good_slug: str,
    ) -> Optional[Dict]:
        return await self.market_prices.find_one(
            {"city_slug": city_slug, "nation": nation, "good_slug": good_slug},
            {"_id": 0},
        )

    # ─── Top movers (recent price changes) ───

    async def top_movers(self, limit: int = 10, hours: int = 168) -> List[Dict]:
        """Largest absolute price deltas across all factions in the last
        `hours` (default 7 days)."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cur = self.cost_history.find(
            {"at": {"$gte": cutoff}},
            {"_id": 0},
        )
        rows = await cur.to_list(500)
        # Pivot: aggregate per (good_slug, faction_slug) latest delta.
        latest_by_specialty: Dict[str, Dict] = {}
        for r in rows:
            sid = r.get("specialty_id")
            if not sid:
                continue
            if sid not in latest_by_specialty or r["at"] > latest_by_specialty[sid]["at"]:
                latest_by_specialty[sid] = r
        # Enrich each row with the current specialty so the UI can show the
        # faction and good slug.
        out = []
        for sid, r in latest_by_specialty.items():
            spec = await self.specialties.find_one({"id": sid}, {"_id": 0})
            if not spec:
                continue
            out.append({
                "good_slug": spec.get("good_slug"),
                "faction_slug": spec.get("faction_slug"),
                "from": r.get("from"),
                "to": r.get("to"),
                "delta": r.get("delta"),
                "reason": r.get("reason"),
                "at": r.get("at"),
            })
        out.sort(key=lambda x: abs(x.get("delta", 0)), reverse=True)
        return out[:limit]

    async def list_broken_routes(self, limit: int = 20) -> List[Dict]:
        cur = self.contracts.find(
            {"status": "broken"},
            {"_id": 0},
        ).sort("ended_at", -1)
        return await cur.to_list(limit)

    # ─── Item sourcing (called by shops route on add/update) ───

    @staticmethod
    def compute_retail_price(import_price: int, shop_markup_pct: int) -> int:
        return int(round(import_price * (1 + (shop_markup_pct or 0) / 100.0)))

    async def resolve_item_auto_price(
        self,
        *,
        nation: str,
        city_slug: Optional[str],
        good_slug: Optional[str],
        markup_pct: Optional[int],
    ) -> Optional[int]:
        """Given an item's sourcing config, return the auto-computed retail
        price, or None if no active price is available."""
        if not good_slug or not city_slug:
            return None
        market = await self.get_good_in_city(nation=nation, city_slug=city_slug, good_slug=good_slug)
        if not market or not market.get("is_available") or market.get("import_price") is None:
            return None
        markup = int(markup_pct) if markup_pct is not None else DEFAULT_SHOP_MARKUP_PCT
        return self.compute_retail_price(int(market["import_price"]), markup)


# ─────────────────── AI event hook helpers ───────────────────


def categorize_event_tags(event_type: str) -> List[str]:
    return EVENT_CATEGORY_TAGS.get((event_type or "").lower(), [])


async def goods_affected_by_event(
    db: AsyncIOMotorDatabase,
    *,
    event_type: str,
    nation_scope: Optional[List[str]] = None,
) -> List[Dict]:
    """Quick non-AI fallback: pull goods whose tags overlap the event's
    category. Used as a deterministic baseline before the AI pass refines."""
    tags = categorize_event_tags(event_type)
    if not tags:
        return []
    cur = db.goods.find({"tags": {"$in": tags}}, {"_id": 0})
    out = await cur.to_list(200)
    if nation_scope:
        # No nation field on goods themselves; filter via specialties.
        affected_slugs = set()
        for g in out:
            specs = await db.faction_specialties.find(
                {"good_slug": g["slug"]}, {"_id": 0, "faction_slug": 1},
            ).to_list(50)
            for s in specs:
                faction = await db.factions.find_one(
                    {"slug": s.get("faction_slug")}, {"_id": 0, "nation_home": 1},
                )
                if faction and faction.get("nation_home") in nation_scope:
                    affected_slugs.add(g["slug"])
                    break
        out = [g for g in out if g["slug"] in affected_slugs]
    return out
