"""Routes for Contested Cities — siege declaration / defence /
contributions / resolution.

Registered via `attach_siege_routes()` from server.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from siege_service import SiegeService, SIDE_ATTACKER, SIDE_DEFENDER


class DeclareSiegePayload(BaseModel):
    character_id: str = Field(..., min_length=1)
    location_id: str = Field(..., min_length=1)
    attacker_faction_slug: str = Field(..., min_length=1, max_length=64)
    duration_world_days: int = Field(default=7, ge=1, le=30)


class CounterClaimPayload(BaseModel):
    character_id: str = Field(..., min_length=1)
    defender_faction_slug: str = Field(..., min_length=1, max_length=64)


class ContributePayload(BaseModel):
    character_id: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1, max_length=16)
    action_text: str = Field(..., min_length=20, max_length=2000)


def _err(ve: ValueError) -> HTTPException:
    msg = str(ve)
    return HTTPException(
        status_code=404 if "not found" in msg.lower() else 409,
        detail=msg,
    )


def attach_siege_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    @api_router.get("/sieges")
    async def list_active_sieges():
        """Board of currently active sieges (public — no auth required for read)."""
        return await SiegeService(db).list_active()

    @api_router.get("/sieges/recent")
    async def list_recent_sieges(limit: int = 50):
        return await SiegeService(db).list_recent(limit=limit)

    @api_router.get("/sieges/{siege_id}")
    async def get_siege(siege_id: str):
        svc = SiegeService(db)
        # Auto-resolve on read if expired
        await svc.resolve_if_due(siege_id)
        s = await svc.get(siege_id)
        if not s:
            raise HTTPException(status_code=404, detail="Siege not found.")
        contribs = await svc.list_contributions(siege_id)
        return {**s, "contributions": contribs}

    @api_router.post("/sieges")
    async def declare(
        payload: DeclareSiegePayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not yours).")
        try:
            return await SiegeService(db).declare_siege(
                user={"id": current_user.id, "username": current_user.username},
                character=char,
                location_id=payload.location_id,
                attacker_faction_slug=payload.attacker_faction_slug,
                duration_world_days=payload.duration_world_days,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/sieges/{siege_id}/answer")
    async def answer(
        siege_id: str,
        payload: CounterClaimPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not yours).")
        try:
            return await SiegeService(db).counter_claim(
                user={"id": current_user.id, "username": current_user.username},
                character=char,
                siege_id=siege_id,
                defender_faction_slug=payload.defender_faction_slug,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/sieges/{siege_id}/contribute")
    async def contribute(
        siege_id: str,
        payload: ContributePayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not yours).")
        if payload.side.lower() not in (SIDE_ATTACKER, SIDE_DEFENDER):
            raise HTTPException(status_code=400, detail=f"side must be '{SIDE_ATTACKER}' or '{SIDE_DEFENDER}'.")
        try:
            return await SiegeService(db).contribute(
                user={"id": current_user.id, "username": current_user.username},
                character=char,
                siege_id=siege_id,
                side=payload.side,
                action_text=payload.action_text,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/sieges/{siege_id}/resolve")
    async def resolve_now(
        siege_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """If expired, resolve. Anyone may call this (used by the UI to
        finalize a stale siege they just opened)."""
        try:
            return await SiegeService(db).resolve_if_due(siege_id)
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/sieges/admin/force-resolve/{siege_id}")
    async def force_resolve(
        siege_id: str,
        current_user: User = Depends(get_current_user),
    ):
        if getattr(current_user, "role", "") not in ("admin", "moderator"):
            raise HTTPException(status_code=403, detail="Admin/moderator only.")
        try:
            return await SiegeService(db).force_resolve(siege_id)
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/sieges/admin/sweep")
    async def sweep_due(
        current_user: User = Depends(get_current_user),
    ):
        if getattr(current_user, "role", "") not in ("admin", "moderator"):
            raise HTTPException(status_code=403, detail="Admin/moderator only.")
        return await SiegeService(db).sweep_due()

    # Convenience: list sieges targeting a given nation (for CityDetail
    # panels and the Contested board's nation filter).
    @api_router.get("/sieges/by-nation/{nation}")
    async def by_nation(nation: str, only_active: Optional[bool] = True):
        query = {"target_nation": nation}
        if only_active:
            query["status"] = "active"
        rows = await db.sieges.find(query, {"_id": 0}).sort(
            "opened_at", -1,
        ).limit(200).to_list(200)
        return rows

    # Locations that a faction currently controls (siezed).
    @api_router.get("/factions/{faction_slug}/holdings")
    async def faction_holdings(faction_slug: str):
        rows = await db.locations.find(
            {"controlling_faction_slug": faction_slug},
            {"_id": 0, "id": 1, "name": 1, "nation": 1, "city": 1,
             "slug": 1, "location_type": 1, "seized_at": 1},
        ).limit(200).to_list(200)
        return rows
