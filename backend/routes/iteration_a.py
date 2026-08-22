"""Routes for Iteration A features:
    • /api/world/calendar   — current Delarom year/month/day
    • /api/reputation/*     — read/list reputation web axes
    • /api/duels/*          — challenge / accept / decline / read

Registered via `attach_iteration_a_routes()` from server.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from world_calendar_service import get_world_calendar
from reputation_web_service import ReputationWebService, VALID_AXES
from duel_service import DuelService, VALID_STAKES, VALID_WEAPONS


class DuelChallengePayload(BaseModel):
    challenger_character_id: str = Field(..., min_length=1)
    target_character_id: str = Field(..., min_length=1)
    city_slug: str = Field(..., min_length=1, max_length=64)
    weapon: str = Field(default="blade")
    stakes: str = Field(default="gold")
    wager_gold: int = Field(default=100, ge=0, le=100000)
    wager_item_id: Optional[str] = None


class ClaimCharacterBountyPayload(BaseModel):
    target_character_id: str = Field(..., min_length=1)
    hunter_character_id: str = Field(..., min_length=1)
    nation: str = Field(..., min_length=2, max_length=64)
    method: str = Field(default="captured")


def _err(ve: ValueError) -> HTTPException:
    msg = str(ve)
    return HTTPException(
        status_code=404 if "not found" in msg.lower() else 409,
        detail=msg,
    )


def attach_iteration_a_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    # ── world calendar ──────────────────────────────────────

    @api_router.get("/world/calendar")
    async def world_calendar():
        return get_world_calendar()

    # ── reputation web ──────────────────────────────────────

    @api_router.get("/reputation/characters/{character_id}")
    async def get_rep(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        # Verify the character belongs to the caller (unless admin)
        char = await db.characters.find_one(
            {"id": character_id}, {"_id": 0, "user_id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found.")
        if char["user_id"] != current_user.id and getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Not your character.")
        return await ReputationWebService(db).list_for_character(character_id)

    @api_router.get("/reputation/characters/{character_id}/axis/{axis}/{key}")
    async def get_rep_axis(
        character_id: str, axis: str, key: str,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one({"id": character_id}, {"_id": 0, "user_id": 1})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found.")
        if char["user_id"] != current_user.id and getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Not your character.")
        if axis not in VALID_AXES:
            raise HTTPException(status_code=400, detail=f"axis must be one of {VALID_AXES}")
        try:
            return await ReputationWebService(db).get_axis(character_id, axis, key)
        except ValueError as ve:
            raise _err(ve) from ve

    # ── duels ────────────────────────────────────────────────

    @api_router.post("/duels")
    async def create_duel(
        payload: DuelChallengePayload,
        current_user: User = Depends(get_current_user),
    ):
        chal = await db.characters.find_one(
            {"id": payload.challenger_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not chal:
            raise HTTPException(status_code=404, detail="Challenger character not found (or not yours).")
        if payload.weapon not in VALID_WEAPONS:
            raise HTTPException(status_code=400, detail=f"weapon must be one of {VALID_WEAPONS}")
        if payload.stakes not in VALID_STAKES:
            raise HTTPException(status_code=400, detail=f"stakes must be one of {VALID_STAKES}")
        try:
            return await DuelService(db).challenge(
                challenger_user={"id": current_user.id, "username": current_user.username},
                challenger_character=chal,
                target_character_id=payload.target_character_id,
                city_slug=payload.city_slug,
                weapon=payload.weapon,
                stakes=payload.stakes,
                wager_gold=payload.wager_gold,
                wager_item_id=payload.wager_item_id,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/duels/{duel_id}/accept")
    async def accept_duel(
        duel_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await DuelService(db).accept_and_resolve(
                duel_id=duel_id, user_id=current_user.id,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/duels/{duel_id}/decline")
    async def decline_duel(
        duel_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await DuelService(db).decline(
                duel_id=duel_id, user_id=current_user.id,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.get("/duels")
    async def list_recent_duels(limit: int = 25):
        return await DuelService(db).list_recent(limit=limit)

    @api_router.get("/duels/character/{character_id}")
    async def list_char_duels(character_id: str, limit: int = 25):
        return await DuelService(db).list_for_character(character_id, limit=limit)

    @api_router.get("/duels/{duel_id}")
    async def get_duel(duel_id: str):
        d = await DuelService(db).get(duel_id)
        if not d:
            raise HTTPException(status_code=404, detail="Duel not found.")
        return d

    # ── player-vs-player bounty claim ───────────────────────

    @api_router.post("/bounties/claim-character")
    async def claim_character_bounty(
        payload: ClaimCharacterBountyPayload,
        current_user: User = Depends(get_current_user),
    ):
        # Hunter must own their character
        hunter_char = await db.characters.find_one(
            {"id": payload.hunter_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not hunter_char:
            raise HTTPException(status_code=404, detail="Hunter character not found (or not yours).")

        from law_service import LawService, law_system_enabled
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        law = LawService(db)
        try:
            result = await law.claim_character_bounty(
                target_character_id=payload.target_character_id,
                nation=payload.nation,
                hunter_user_id=current_user.id,
                hunter_character_id=payload.hunter_character_id,
                hunter_character_name=hunter_char.get("name", ""),
                method=payload.method,
            )
        except ValueError as ve:
            raise _err(ve) from ve

        # Credit the hunter — the state pays the bounty
        payout = int(result.get("total_payout", 0))
        if payout > 0:
            await db.users.update_one(
                {"id": current_user.id}, {"$inc": {"currency": payout}},
            )

        # On "killed", retire the target character (soft flag).
        if payload.method == "killed":
            await db.characters.update_one(
                {"id": payload.target_character_id},
                {"$set": {
                    "status": "fallen",
                    "fallen_at": get_world_calendar()["formatted"],
                    "fallen_reason": f"Slain by {hunter_char.get('name','')} while wanted in {payload.nation}",
                }},
            )
        return {**result, "credited": payout}
