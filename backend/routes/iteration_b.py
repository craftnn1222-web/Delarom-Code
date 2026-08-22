"""Routes for Iteration B — Assassinations, Cults, Black Market.

Registered via `attach_iteration_b_routes()` from server.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from assassination_service import AssassinationService
from cults_service import CultService
from black_market import BANNED_GOODS_BY_NATION, SEIZURE_PCT, SMUGGLE_PROFIT_MULT


class ContractPostPayload(BaseModel):
    buyer_character_id: str = Field(..., min_length=1)
    target_character_id: str = Field(..., min_length=1)
    city_slug: str = Field(..., min_length=1, max_length=64)
    reward_gold: int = Field(..., ge=250, le=1_000_000)
    note: str = Field(default="", max_length=400)


class ContractAcceptPayload(BaseModel):
    assassin_character_id: str = Field(..., min_length=1)


class RitualCastPayload(BaseModel):
    character_id: str = Field(..., min_length=1)
    ritual_slug: str = Field(..., min_length=1, max_length=64)
    target_ref: Optional[str] = None


def _err(ve: ValueError) -> HTTPException:
    msg = str(ve)
    return HTTPException(
        status_code=404 if "not found" in msg.lower() else 409,
        detail=msg,
    )


def attach_iteration_b_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    # ── Assassination Contracts ─────────────────────────────

    @api_router.post("/contracts")
    async def post_contract(
        payload: ContractPostPayload,
        current_user: User = Depends(get_current_user),
    ):
        buyer_char = await db.characters.find_one(
            {"id": payload.buyer_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not buyer_char:
            raise HTTPException(status_code=404, detail="Buyer character not found (or not yours).")
        try:
            return await AssassinationService(db).post_contract(
                buyer_user={"id": current_user.id, "username": current_user.username},
                buyer_character=buyer_char,
                target_character_id=payload.target_character_id,
                city_slug=payload.city_slug,
                reward_gold=payload.reward_gold,
                note=payload.note,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.get("/contracts/board")
    async def contract_board(
        city_slug: Optional[str] = None,
        current_user: User = Depends(get_current_user),
    ):
        return await AssassinationService(db).list_board(city_slug=city_slug)

    @api_router.get("/contracts/mine")
    async def my_posted_contracts(current_user: User = Depends(get_current_user)):
        return await AssassinationService(db).list_posted_by_user(current_user.id)

    @api_router.get("/contracts/on-character/{character_id}")
    async def contracts_on(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": character_id, "user_id": current_user.id}, {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=403, detail="Not your character.")
        return await AssassinationService(db).list_attempts_on_target(character_id)

    @api_router.post("/contracts/{contract_id}/accept")
    async def accept_contract(
        contract_id: str,
        payload: ContractAcceptPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.assassin_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Assassin character not found (or not yours).")
        try:
            return await AssassinationService(db).accept_contract(
                contract_id=contract_id,
                assassin_user={"id": current_user.id, "username": current_user.username},
                assassin_character=char,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/contracts/{contract_id}/attempt")
    async def attempt_contract(
        contract_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await AssassinationService(db).attempt(
                contract_id=contract_id,
                assassin_user={"id": current_user.id, "username": current_user.username},
            )
        except ValueError as ve:
            raise _err(ve) from ve

    # ── Cults & Forbidden Faiths ────────────────────────────

    @api_router.get("/cults")
    async def list_cults():
        return await CultService(db).list_cults()

    @api_router.get("/cults/rituals")
    async def list_rituals(current_user: User = Depends(get_current_user)):
        return await CultService(db).list_rituals()

    @api_router.get("/cults/mine/{character_id}")
    async def my_cult(character_id: str, current_user: User = Depends(get_current_user)):
        char = await db.characters.find_one(
            {"id": character_id, "user_id": current_user.id}, {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=403, detail="Not your character.")
        return await CultService(db).get_membership(character_id)

    @api_router.post("/cults/{cult_slug}/join")
    async def join_cult(
        cult_slug: str,
        payload: ContractAcceptPayload,   # reuses {character_id} shape
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.assassin_character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not yours).")
        try:
            return await CultService(db).join_cult(
                character_id=payload.assassin_character_id,
                cult_slug=cult_slug,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/cults/rituals/cast")
    async def cast_ritual(
        payload: RitualCastPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not yours).")
        try:
            return await CultService(db).cast_ritual(
                character_id=payload.character_id,
                user_id=current_user.id,
                ritual_slug=payload.ritual_slug,
                target_ref=payload.target_ref,
            )
        except ValueError as ve:
            raise _err(ve) from ve

    @api_router.post("/cults/admin/seed")
    async def seed_cults(current_user: User = Depends(get_current_user)):
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin only.")
        return await CultService(db).seed_cults()

    # ── Black Market ────────────────────────────────────────

    @api_router.get("/black-market/contraband")
    async def contraband_table():
        return {
            "banned_by_nation": BANNED_GOODS_BY_NATION,
            "seizure_pct": SEIZURE_PCT,
            "smuggle_profit_mult": SMUGGLE_PROFIT_MULT,
        }

    @api_router.get("/black-market/events")
    async def recent_smuggling_events(
        limit: int = 40,
        current_user: User = Depends(get_current_user),
    ):
        rows = await db.smuggling_events.find({}, {"_id": 0}).sort(
            "at", -1,
        ).limit(max(1, min(200, limit))).to_list(limit)
        return rows
