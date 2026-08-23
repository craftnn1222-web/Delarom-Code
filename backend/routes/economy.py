"""Economy routes — goods, faction specialties, trade contracts, city markets.

Mounted by `server.py::attach_economy_routes(...)`. Public read endpoints
power the Markets UI; admin endpoints let staff seed the catalogue, tune
faction base_costs, and create / break trade contracts.

The AI-driven price-impact hook lives in `apply_event_to_economy`, called
by `world_state_service` whenever a world event is recorded.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from economy_service import (
    EconomyService,
    DEFAULT_FACTION_TO_CITY_TARIFF_PCT,
    goods_affected_by_event,
)
from quest_master_ai import QuestMasterAI

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Pydantic bodies ────────────────────────────────────────────────


class UpsertSpecialtyBody(BaseModel):
    faction_slug: str = Field(min_length=2, max_length=64)
    good_slug: str = Field(min_length=2, max_length=64)
    base_cost: int = Field(ge=1, le=1_000_000)
    capacity: int = Field(default=50, ge=0, le=10_000)
    description: str = Field(default="", max_length=400)
    reason: str = Field(default="manual", max_length=160)


class CustomOfferingBody(BaseModel):
    """Faction leader coins a brand-new tradeable good and lists it as an offering."""
    name: str = Field(min_length=2, max_length=60)
    category: str = Field(default="custom", max_length=40)
    unit: str = Field(default="per unit", max_length=40)
    base_cost: int = Field(ge=1, le=1_000_000)
    capacity: int = Field(default=50, ge=0, le=10_000)
    description: str = Field(default="", max_length=400)


class CreateContractBody(BaseModel):
    from_faction_slug: str = Field(min_length=2, max_length=64)
    to_type: str = Field(default="city")  # "city" | "faction"
    good_slug: str = Field(min_length=2, max_length=64)
    to_city_slug: Optional[str] = Field(default=None, max_length=64)
    to_nation: Optional[str] = Field(default="", max_length=64)
    to_faction_slug: Optional[str] = Field(default=None, max_length=64)
    tariff_pct: int = Field(default=DEFAULT_FACTION_TO_CITY_TARIFF_PCT, ge=0, le=300)
    quantity_per_tick: int = Field(default=50, ge=1, le=10_000)


class BreakContractBody(BaseModel):
    reason: str = Field(default="", max_length=200)


class PostCaravanBody(BaseModel):
    """Faction Leader posts a one-off paid caravan run."""
    good_slug: str = Field(min_length=2, max_length=64)
    quantity: int = Field(ge=1, le=10_000)
    to_city_slug: str = Field(min_length=2, max_length=64)
    reward_gold: int = Field(ge=1, le=500_000)
    origin_city_slug: Optional[str] = Field(default="", max_length=64)
    description: Optional[str] = Field(default="", max_length=600)
    danger_note: Optional[str] = Field(default="", max_length=200)
    expires_in_hours: int = Field(default=72, ge=1, le=720)


class ClaimCaravanBody(BaseModel):
    character_id: str = Field(min_length=4, max_length=64)


class CompleteCaravanBody(BaseModel):
    success: bool = True
    story: Optional[str] = Field(default="", max_length=800)


# ── Route attachment ───────────────────────────────────────────────


def attach_economy_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
):
    """Mount economy endpoints on the api router."""

    # ─── Public READ ─────────────────────────────────────────

    @api_router.get("/economy/goods")
    async def list_goods(category: Optional[str] = None):
        return await EconomyService(db).list_goods(category=category)

    @api_router.get("/economy/goods/{good_slug}")
    async def get_good(good_slug: str):
        es = EconomyService(db)
        doc = await es.get_good(good_slug)
        if not doc:
            raise HTTPException(status_code=404, detail="Good not found")
        # Suppliers: every faction producing this good, ranked cheapest first.
        suppliers = await es.list_specialties_for_good(good_slug)
        # Decorate suppliers with the faction name for the UI.
        for s in suppliers:
            fac = await db.factions.find_one(
                {"slug": s.get("faction_slug")},
                {"_id": 0, "name": 1, "nation_home": 1, "color_hex": 1, "icon": 1},
            )
            if fac:
                s["faction_name"] = fac.get("name")
                s["faction_nation"] = fac.get("nation_home")
                s["faction_color"] = fac.get("color_hex")
                s["faction_icon"] = fac.get("icon")
        doc["suppliers"] = suppliers
        # Markets: every city currently importing this good (cheapest first).
        cur = db.city_market_prices.find(
            {"good_slug": good_slug},
            {"_id": 0},
        )
        markets_rows = await cur.to_list(500)
        # Filter to available + decorate with city name.
        markets = []
        for m in markets_rows:
            if not m.get("is_available") or m.get("import_price") is None:
                continue
            city = await db.cities.find_one(
                {"slug": m.get("city_slug")}, {"_id": 0, "name": 1, "nation": 1},
            )
            markets.append({
                "city_slug": m.get("city_slug"),
                "city_name": (city or {}).get("name") or m.get("city_slug"),
                "nation": m.get("nation"),
                "import_price": m.get("import_price"),
                "source_faction_slug": m.get("source_faction_slug"),
                "source_contract_id": m.get("source_contract_id"),
                "updated_at": m.get("updated_at"),
            })
        markets.sort(key=lambda r: r.get("import_price") or 0)
        doc["markets"] = markets
        return doc

    @api_router.get("/economy/factions/{faction_slug}/specialties")
    async def list_faction_specialties(faction_slug: str):
        faction = await db.factions.find_one(
            {"slug": faction_slug}, {"_id": 0, "id": 1, "slug": 1, "name": 1},
        )
        if not faction:
            raise HTTPException(status_code=404, detail="Faction not found")
        es = EconomyService(db)
        specs = await es.list_specialties_for_faction(faction["id"])
        # Decorate with good name + category for UI display.
        for s in specs:
            g = await es.get_good(s.get("good_slug"))
            if g:
                s["good_name"] = g.get("name")
                s["good_category"] = g.get("category")
                s["good_unit"] = g.get("unit")
                s["is_service"] = g.get("is_service", False)
        return {"faction": faction, "specialties": specs}

    @api_router.get("/economy/markets/{nation}/{city_slug}")
    async def get_city_market(nation: str, city_slug: str):
        es = EconomyService(db)
        prices = await es.get_city_market(nation, city_slug)
        # Decorate with good metadata so the UI can render category/unit.
        for p in prices:
            g = await es.get_good(p.get("good_slug"))
            if g:
                p["good_name"] = g.get("name")
                p["good_category"] = g.get("category")
                p["good_unit"] = g.get("unit")
        return prices

    @api_router.get("/economy/contracts")
    async def list_contracts(
        faction_slug: Optional[str] = None,
        city_slug: Optional[str] = None,
        status: Optional[str] = None,
    ):
        es = EconomyService(db)
        faction_id = None
        if faction_slug:
            f = await db.factions.find_one({"slug": faction_slug}, {"_id": 0, "id": 1})
            if f:
                faction_id = f["id"]
            else:
                return []
        return await es.list_contracts(faction_id=faction_id, to_city_slug=city_slug, status=status)

    @api_router.get("/economy/top-movers")
    async def get_top_movers(limit: int = 10, hours: int = 168):
        return await EconomyService(db).top_movers(limit=limit, hours=hours)

    @api_router.get("/economy/broken-routes")
    async def get_broken_routes(limit: int = 20):
        rows = await EconomyService(db).list_broken_routes(limit=limit)
        return rows

    # ─── ADMIN (mutating) ────────────────────────────────────

    @api_router.post("/economy/admin/seed-catalogue")
    async def admin_seed_catalogue(admin: User = Depends(require_admin)):
        """Insert the canonical 25-good catalogue. Idempotent."""
        es = EconomyService(db)
        goods_result = await es.seed_canonical_goods()
        specs_result = await es.seed_starter_specialties()
        return {"goods": goods_result, "specialties": specs_result}

    @api_router.post("/economy/admin/seed-contracts")
    async def admin_seed_contracts(admin: User = Depends(require_admin)):
        """Seed a spread of active standing contracts so shop auto-pricing has
        live prices across the shop-picker nations. Idempotent."""
        es = EconomyService(db)
        return await es.seed_starter_contracts()

    @api_router.post("/economy/admin/specialties")
    async def admin_upsert_specialty(
        payload: UpsertSpecialtyBody,
        admin: User = Depends(require_admin),
    ):
        faction = await db.factions.find_one(
            {"slug": payload.faction_slug}, {"_id": 0, "id": 1, "slug": 1, "name": 1},
        )
        if not faction:
            raise HTTPException(status_code=404, detail="Faction not found")
        good = await db.goods.find_one({"slug": payload.good_slug}, {"_id": 0, "slug": 1})
        if not good:
            raise HTTPException(status_code=404, detail="Good not in canonical catalogue")
        es = EconomyService(db)
        doc = await es.upsert_specialty(
            faction_id=faction["id"],
            faction_slug=faction["slug"],
            good_slug=payload.good_slug,
            base_cost=payload.base_cost,
            capacity=payload.capacity,
            description=payload.description,
            reason=payload.reason,
        )
        return doc

    @api_router.delete("/economy/admin/specialties/{faction_slug}/{good_slug}")
    async def admin_remove_specialty(
        faction_slug: str,
        good_slug: str,
        admin: User = Depends(require_admin),
    ):
        faction = await db.factions.find_one(
            {"slug": faction_slug}, {"_id": 0, "id": 1},
        )
        if not faction:
            raise HTTPException(status_code=404, detail="Faction not found")
        ok = await EconomyService(db).remove_specialty(faction["id"], good_slug)
        return {"ok": bool(ok)}

    @api_router.post("/economy/admin/contracts")
    async def admin_create_contract(
        payload: CreateContractBody,
        admin: User = Depends(require_admin),
    ):
        from_faction = await db.factions.find_one(
            {"slug": payload.from_faction_slug}, {"_id": 0, "id": 1, "slug": 1, "name": 1},
        )
        if not from_faction:
            raise HTTPException(status_code=404, detail="Source faction not found")

        to_faction_id = None
        to_faction_slug = None
        if payload.to_type == "faction":
            if not payload.to_faction_slug:
                raise HTTPException(status_code=400, detail="to_faction_slug required for faction contracts")
            tf = await db.factions.find_one(
                {"slug": payload.to_faction_slug}, {"_id": 0, "id": 1, "slug": 1},
            )
            if not tf:
                raise HTTPException(status_code=404, detail="Destination faction not found")
            to_faction_id = tf["id"]
            to_faction_slug = tf["slug"]
        elif payload.to_type == "city":
            if not payload.to_city_slug:
                raise HTTPException(status_code=400, detail="to_city_slug required for city contracts")
            city = await db.cities.find_one(
                {"slug": payload.to_city_slug}, {"_id": 0, "slug": 1, "nation": 1},
            )
            if not city:
                raise HTTPException(status_code=404, detail="Destination city not found")
        else:
            raise HTTPException(status_code=400, detail="to_type must be 'city' or 'faction'")

        try:
            doc = await EconomyService(db).create_standing_contract(
                from_faction_id=from_faction["id"],
                from_faction_slug=from_faction["slug"],
                to_type=payload.to_type,
                good_slug=payload.good_slug,
                to_city_slug=payload.to_city_slug,
                to_nation=payload.to_nation or "",
                to_faction_id=to_faction_id,
                to_faction_slug=to_faction_slug,
                tariff_pct=payload.tariff_pct,
                quantity_per_tick=payload.quantity_per_tick,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return doc

    @api_router.post("/economy/admin/contracts/{contract_id}/break")
    async def admin_break_contract(
        contract_id: str,
        payload: BreakContractBody = Body(default=BreakContractBody()),
        admin: User = Depends(require_admin),
    ):
        result = await EconomyService(db).break_contract(contract_id, reason=payload.reason)
        if not result:
            raise HTTPException(status_code=404, detail="Contract not found")
        return result

    # ─── PLAYER-FACTION (leader-only) ────────────────────────
    # Lets the leader of a player-founded faction declare what their faction
    # produces and at what price. Mirrors the admin endpoints but enforces a
    # leader-rank check so only the faction's Leader (or admins) can edit.

    async def _ensure_faction_leader(faction_slug: str, current_user) -> Dict:
        is_admin = (
            getattr(current_user, "is_admin", False)
            or getattr(current_user, "role", "") in ("admin", "moderator")
        )
        if is_admin:
            faction = await db.factions.find_one({"slug": faction_slug}, {"_id": 0})
            if not faction:
                raise HTTPException(status_code=404, detail="Faction not found")
            return faction
        faction = await db.factions.find_one({"slug": faction_slug}, {"_id": 0})
        if not faction:
            raise HTTPException(status_code=404, detail="Faction not found")
        # Find a membership row this user owns at Leader rank in this faction.
        user_chars = await db.characters.find(
            {"user_id": current_user.id, "is_active": True},
            {"_id": 0, "id": 1},
        ).to_list(50)
        char_ids = [c["id"] for c in user_chars]
        membership = await db.faction_memberships.find_one(
            {
                "faction_id": faction["id"],
                "character_id": {"$in": char_ids},
                "rank": "leader",
                "status": "active",
            },
            {"_id": 0},
        )
        if not membership:
            raise HTTPException(status_code=403, detail="Only the Leader of this faction may manage its offerings.")
        return faction

    @api_router.post("/economy/factions/{faction_slug}/specialties")
    async def leader_upsert_specialty(
        faction_slug: str,
        payload: UpsertSpecialtyBody,
        current_user: User = Depends(get_current_user),
    ):
        """Faction-leader endpoint to declare/update what this faction offers.

        Player-founded factions use this to set their `offered_goods` lineup.
        The `faction_slug` in the URL must match the body so the leader can't
        edit a different faction's lineup by accident.
        """
        if payload.faction_slug != faction_slug:
            raise HTTPException(status_code=400, detail="faction_slug mismatch")
        faction = await _ensure_faction_leader(faction_slug, current_user)
        good = await db.goods.find_one({"slug": payload.good_slug}, {"_id": 0, "slug": 1})
        if not good:
            raise HTTPException(status_code=404, detail="Good not in canonical catalogue")
        return await EconomyService(db).upsert_specialty(
            faction_id=faction["id"],
            faction_slug=faction["slug"],
            good_slug=payload.good_slug,
            base_cost=payload.base_cost,
            capacity=payload.capacity,
            description=payload.description,
            reason=payload.reason or f"Set by leader of {faction_slug}",
        )

    @api_router.delete("/economy/factions/{faction_slug}/specialties/{good_slug}")
    async def leader_remove_specialty(
        faction_slug: str,
        good_slug: str,
        current_user: User = Depends(get_current_user),
    ):
        faction = await _ensure_faction_leader(faction_slug, current_user)
        ok = await EconomyService(db).remove_specialty(faction["id"], good_slug)
        return {"ok": bool(ok)}

    @api_router.post("/economy/factions/{faction_slug}/offerings/custom")
    async def leader_add_custom_offering(
        faction_slug: str,
        payload: CustomOfferingBody,
        current_user: User = Depends(get_current_user),
    ):
        """Coin a brand-new good from a typed name and list it as this faction's
        offering. The good enters the canonical catalogue (is_custom=True) so it
        flows through the full economy (city prices, trade routes)."""
        faction = await _ensure_faction_leader(faction_slug, current_user)
        base = re.sub(r"[^a-z0-9]+", "-", payload.name.strip().lower()).strip("-")[:48]
        if not base:
            raise HTTPException(status_code=400, detail="Give the product a real name.")
        # Ensure a unique slug.
        slug = base
        n = 2
        while await db.goods.find_one({"slug": slug}, {"_id": 0, "slug": 1}):
            slug = f"{base}-{n}"
            n += 1
        good_doc = {
            "id": str(uuid.uuid4()),
            "slug": slug,
            "name": payload.name.strip(),
            "category": (payload.category or "custom").strip().lower(),
            "unit": (payload.unit or "per unit").strip(),
            "default_base_cost": int(payload.base_cost),
            "is_service": False,
            "tags": ["custom"],
            "is_custom": True,
            "created_by_faction": faction["slug"],
            "created_at": _now_iso(),
        }
        await db.goods.insert_one(dict(good_doc))
        good_doc.pop("_id", None)
        spec = await EconomyService(db).upsert_specialty(
            faction_id=faction["id"],
            faction_slug=faction["slug"],
            good_slug=slug,
            base_cost=payload.base_cost,
            capacity=payload.capacity,
            description=payload.description,
            reason=f"Custom offering coined by leader of {faction_slug}",
        )
        return {"good": good_doc, "specialty": spec}

    # ─── LEADER-managed trade routes ─────────────────────────
    # Mirrors `/economy/admin/contracts` but scoped to one faction. The
    # `from_faction_slug` is locked to the URL slug, so a leader cannot
    # spoof contracts originating from a different faction.

    @api_router.get("/economy/factions/{faction_slug}/contracts")
    async def list_faction_contracts(faction_slug: str):
        """All contracts where this faction is the source. Public read."""
        f = await db.factions.find_one({"slug": faction_slug}, {"_id": 0, "id": 1})
        if not f:
            return []
        return await EconomyService(db).list_contracts(faction_id=f["id"])

    @api_router.post("/economy/factions/{faction_slug}/contracts")
    async def leader_create_contract(
        faction_slug: str,
        payload: CreateContractBody,
        current_user: User = Depends(get_current_user),
    ):
        """Faction-leader proposes a new standing contract FROM their faction.

        The body's `from_faction_slug` must match the URL slug.
        """
        if payload.from_faction_slug != faction_slug:
            raise HTTPException(status_code=400, detail="from_faction_slug must match URL slug.")
        from_faction = await _ensure_faction_leader(faction_slug, current_user)

        to_faction_id = None
        to_faction_slug = None
        if payload.to_type == "faction":
            if not payload.to_faction_slug:
                raise HTTPException(status_code=400, detail="to_faction_slug required for faction contracts")
            tf = await db.factions.find_one(
                {"slug": payload.to_faction_slug}, {"_id": 0, "id": 1, "slug": 1},
            )
            if not tf:
                raise HTTPException(status_code=404, detail="Destination faction not found")
            to_faction_id = tf["id"]
            to_faction_slug = tf["slug"]
        elif payload.to_type == "city":
            if not payload.to_city_slug:
                raise HTTPException(status_code=400, detail="to_city_slug required for city contracts")
            city = await db.cities.find_one(
                {"slug": payload.to_city_slug}, {"_id": 0, "slug": 1, "nation": 1},
            )
            if not city:
                raise HTTPException(status_code=404, detail="Destination city not found")
        else:
            raise HTTPException(status_code=400, detail="to_type must be 'city' or 'faction'")

        try:
            doc = await EconomyService(db).create_standing_contract(
                from_faction_id=from_faction["id"],
                from_faction_slug=from_faction["slug"],
                to_type=payload.to_type,
                good_slug=payload.good_slug,
                to_city_slug=payload.to_city_slug,
                to_nation=payload.to_nation or "",
                to_faction_id=to_faction_id,
                to_faction_slug=to_faction_slug,
                tariff_pct=payload.tariff_pct,
                quantity_per_tick=payload.quantity_per_tick,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return doc

    @api_router.post("/economy/factions/{faction_slug}/contracts/{contract_id}/break")
    async def leader_break_contract(
        faction_slug: str,
        contract_id: str,
        payload: BreakContractBody = Body(default=BreakContractBody()),
        current_user: User = Depends(get_current_user),
    ):
        """A Leader can ONLY break contracts they originated."""
        faction = await _ensure_faction_leader(faction_slug, current_user)
        contract = await db.trade_contracts.find_one({"id": contract_id}, {"_id": 0})
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        if contract.get("from_faction_id") != faction["id"]:
            raise HTTPException(
                status_code=403,
                detail="Only the originating faction's Leader can break this contract.",
            )
        result = await EconomyService(db).break_contract(contract_id, reason=payload.reason)
        return result

    # ─── SPOT CARAVANS — player-engagement contracts ─────────
    # A one-off paid haul posted by a faction (or admin). Players claim a
    # caravan, RP the journey, then report success/failure. On success the
    # claimer is paid; failure or expiry lets the faction repost or absorb
    # the loss.

    @api_router.get("/economy/caravans")
    async def list_caravans(
        status: Optional[str] = None,
        from_faction_slug: Optional[str] = None,
        to_city_slug: Optional[str] = None,
        limit: int = 50,
    ):
        q: Dict = {}
        if status:
            q["status"] = status
        if from_faction_slug:
            q["from_faction_slug"] = from_faction_slug
        if to_city_slug:
            q["to_city_slug"] = to_city_slug
        cur = db.trade_caravans.find(q, {"_id": 0}).sort("posted_at", -1)
        return await cur.to_list(limit)

    @api_router.get("/economy/caravans/{caravan_id}")
    async def get_caravan(caravan_id: str):
        doc = await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Caravan not found")
        return doc

    @api_router.post("/economy/factions/{faction_slug}/caravans")
    async def leader_post_caravan(
        faction_slug: str,
        payload: PostCaravanBody,
        current_user: User = Depends(get_current_user),
    ):
        """Faction-leader posts a one-off paid caravan run."""
        faction = await _ensure_faction_leader(faction_slug, current_user)
        # Validate good + destination city
        good = await db.goods.find_one({"slug": payload.good_slug}, {"_id": 0, "slug": 1, "name": 1})
        if not good:
            raise HTTPException(status_code=404, detail="Good not in canonical catalogue")
        dest_city = await db.cities.find_one(
            {"slug": payload.to_city_slug}, {"_id": 0, "slug": 1, "nation": 1, "name": 1},
        )
        if not dest_city:
            raise HTTPException(status_code=404, detail="Destination city not found")
        # Reward must be paid from faction treasury OR poster's wallet. Keep it
        # simple in v1 — debit the poster's wallet up-front; refund on cancel.
        if (current_user.currency or 0) < payload.reward_gold:
            raise HTTPException(
                status_code=400,
                detail=f"Reward of {payload.reward_gold}g exceeds your wallet ({current_user.currency}g).",
            )
        await db.users.update_one(
            {"id": current_user.id}, {"$inc": {"currency": -payload.reward_gold}},
        )
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(hours=max(1, int(payload.expires_in_hours)))
        doc = {
            "id": str(uuid.uuid4()),
            "from_faction_id": faction["id"],
            "from_faction_slug": faction["slug"],
            "from_faction_name": faction["name"],
            "good_slug": payload.good_slug,
            "good_name": good.get("name"),
            "quantity": int(payload.quantity),
            "origin_city_slug": payload.origin_city_slug or "",
            "to_city_slug": dest_city["slug"],
            "to_city_name": dest_city.get("name"),
            "to_nation": dest_city.get("nation"),
            "reward_gold": int(payload.reward_gold),
            "description": (payload.description or "")[:600],
            "danger_note": (payload.danger_note or "")[:200],
            "status": "open",
            "posted_by_user_id": current_user.id,
            "posted_at": _now_iso(),
            "claimed_by_character_id": None,
            "claimed_by_character_name": None,
            "claimed_at": None,
            "completed_at": None,
            "completion_story": "",
            "expires_at": expires.isoformat(),
        }
        await db.trade_caravans.insert_one(dict(doc))
        return doc

    @api_router.post("/economy/caravans/{caravan_id}/claim")
    async def claim_caravan(
        caravan_id: str,
        payload: ClaimCaravanBody,
        current_user: User = Depends(get_current_user),
    ):
        """Player accepts the caravan — locks it until completion / abandonment."""
        caravan = await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})
        if not caravan:
            raise HTTPException(status_code=404, detail="Caravan not found")
        if caravan.get("status") != "open":
            raise HTTPException(status_code=400, detail=f"Caravan is already {caravan.get('status')}.")
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id, "is_active": True},
            {"_id": 0, "id": 1, "name": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
        await db.trade_caravans.update_one(
            {"id": caravan_id, "status": "open"},
            {"$set": {
                "status": "claimed",
                "claimed_by_character_id": char["id"],
                "claimed_by_character_name": char["name"],
                "claimed_at": _now_iso(),
            }},
        )
        return await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})

    @api_router.post("/economy/caravans/{caravan_id}/complete")
    async def complete_caravan(
        caravan_id: str,
        payload: CompleteCaravanBody,
        current_user: User = Depends(get_current_user),
    ):
        """Mark a claimed caravan as completed (success or failure).

        SUCCESS: reward is paid to the claimer; a world event is recorded so
                 the AI can ripple a small *deflation* on the destination city.
        FAILURE: caravan is closed; the destination city gets a small
                 *inflation* nudge logged to the chronicle. No reward.
        """
        caravan = await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})
        if not caravan:
            raise HTTPException(status_code=404, detail="Caravan not found")
        if caravan.get("status") != "claimed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete a caravan that is {caravan.get('status')}.",
            )
        char = await db.characters.find_one(
            {"id": caravan.get("claimed_by_character_id"), "user_id": current_user.id},
            {"_id": 0, "id": 1, "name": 1},
        )
        is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"
        if not char and not is_admin:
            raise HTTPException(status_code=403, detail="Only the character who claimed the caravan (or admin) may report it.")

        success = bool(payload.success)
        new_status = "completed" if success else "failed"
        story = (payload.story or "")[:800]

        if success:
            # Pay reward to the claimer's user.
            await db.users.update_one(
                {"id": current_user.id}, {"$inc": {"currency": int(caravan.get("reward_gold", 0))}},
            )

        await db.trade_caravans.update_one(
            {"id": caravan_id, "status": "claimed"},
            {"$set": {
                "status": new_status,
                "completed_at": _now_iso(),
                "completion_story": story,
            }},
        )

        # Chronicle event so the world (and AI economy hook) knows.
        try:
            from world_state_service import WorldStateService
            world = WorldStateService(db)
            event_type = "festival" if success else "disaster"  # success → mild deflation candidates, fail → inflation
            await world.record_world_event({
                "event_type": event_type,
                "scope": "regional",
                "summary": (
                    f"A caravan of {caravan.get('quantity', 0)} {caravan.get('good_slug', '?')} "
                    f"{'safely reached' if success else 'was lost en route to'} "
                    f"{caravan.get('to_city_name') or caravan.get('to_city_slug') or '?'}."
                ),
                "details": story or "(No journey log filed.)",
                "nations": [caravan.get("to_nation")] if caravan.get("to_nation") else [],
                "involved_characters": [char["id"]] if char else [],
            })
        except Exception as ev_err:
            logger.warning(f"Caravan chronicle event failed (non-fatal): {ev_err}")

        return await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})

    @api_router.post("/economy/caravans/{caravan_id}/cancel")
    async def cancel_caravan(
        caravan_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Poster (or admin) cancels an OPEN caravan and refunds the reward."""
        caravan = await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})
        if not caravan:
            raise HTTPException(status_code=404, detail="Caravan not found")
        if caravan.get("status") != "open":
            raise HTTPException(status_code=400, detail=f"Only open caravans can be cancelled (was {caravan.get('status')}).")
        is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"
        if caravan.get("posted_by_user_id") != current_user.id and not is_admin:
            raise HTTPException(status_code=403, detail="Only the poster or an admin may cancel this caravan.")
        # Refund reward to poster.
        await db.users.update_one(
            {"id": caravan.get("posted_by_user_id")},
            {"$inc": {"currency": int(caravan.get("reward_gold", 0))}},
        )
        await db.trade_caravans.update_one(
            {"id": caravan_id, "status": "open"},
            {"$set": {"status": "cancelled", "completed_at": _now_iso()}},
        )
        return await db.trade_caravans.find_one({"id": caravan_id}, {"_id": 0})


# ─────────────────────── World-event hook ───────────────────────


async def apply_event_to_economy(
    db,
    *,
    event_type: str,
    summary: str,
    details: str,
    nations: List[str],
) -> Dict:
    """Called by world_state_service after a world event is recorded.

    Pulls candidate goods (deterministic tag match), asks the AI which goods
    actually move, then applies the delta to the relevant faction specialties
    in the affected nations. Logs each adjustment to `economy_events` for
    auditability.
    """
    es = EconomyService(db)
    candidates = await goods_affected_by_event(db, event_type=event_type, nation_scope=nations or None)
    if not candidates:
        return {"impacts_applied": 0, "candidates": 0}

    ai = QuestMasterAI()
    try:
        impacts = await ai.infer_economy_event_impact(
            event_type=event_type,
            event_summary=summary or "",
            event_details=details or "",
            nations=nations or [],
            candidate_goods=candidates,
        )
    except Exception as e:
        logger.error(f"Economy AI inference failed: {e}")
        impacts = []
    if not impacts:
        return {"impacts_applied": 0, "candidates": len(candidates)}

    applied = 0
    event_log_id = None
    try:
        event_log = {
            "id": __import__("uuid").uuid4().hex,
            "event_type": event_type,
            "summary": (summary or "")[:300],
            "nations": nations or [],
            "impacts": impacts,
            "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        await db.economy_events.insert_one(dict(event_log))
        event_log_id = event_log["id"]
    except Exception as e:
        logger.error(f"Economy event log insert failed: {e}")

    for impact in impacts:
        good_slug = impact.get("good_slug")
        delta_pct = int(impact.get("delta_pct", 0))
        reason = impact.get("reason") or f"World event: {event_type}"
        if not good_slug or delta_pct == 0:
            continue
        # Apply the delta to every specialty for that good in the affected nations.
        cur = db.faction_specialties.find({"good_slug": good_slug}, {"_id": 0})
        async for spec in cur:
            faction = await db.factions.find_one(
                {"slug": spec.get("faction_slug")}, {"_id": 0, "nation_home": 1},
            )
            if nations and faction and faction.get("nation_home") not in nations:
                continue
            old_cost = int(spec.get("base_cost", 0))
            if old_cost <= 0:
                continue
            new_cost = max(1, round(old_cost * (1 + delta_pct / 100.0)))
            if new_cost == old_cost:
                continue
            await es.upsert_specialty(
                faction_id=spec["faction_id"],
                faction_slug=spec["faction_slug"],
                good_slug=good_slug,
                base_cost=new_cost,
                capacity=int(spec.get("capacity", 50)),
                description=spec.get("description", ""),
                reason=f"[{event_type}] {reason}",
            )
            applied += 1

    return {"impacts_applied": applied, "candidates": len(candidates), "event_log_id": event_log_id}
