"""Routes for the Tongue of Y'ros Trial.

Registered via `attach_tongue_of_yros_routes(api_router, ...)`.

Endpoints:
  GET  /api/tongue-of-yros/state              — public; is the sword currently claimed?
  POST /api/tongue-of-yros/attempt            — authed; attempt to draw the sword
  GET  /api/tongue-of-yros/character/{cid}    — authed; attempt history for one character
  POST /api/tongue-of-yros/relinquish         — authed; current bearer sets it down
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from tongue_of_yros_service import TongueOfYrosService


class TongueAttemptPayload(BaseModel):
    character_id: str = Field(..., min_length=1, max_length=128)
    attempt_text: str = Field(..., min_length=15, max_length=2000)


class TongueRelinquishPayload(BaseModel):
    character_id: str = Field(..., min_length=1, max_length=128)


def attach_tongue_of_yros_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    @api_router.get("/tongue-of-yros/state")
    async def tongue_state():
        return await TongueOfYrosService(db).get_state()

    @api_router.post("/tongue-of-yros/attempt")
    async def tongue_attempt(
        payload: TongueAttemptPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            record = await TongueOfYrosService(db).submit_attempt(
                character=char,
                attempt_text=payload.attempt_text,
            )
        except ValueError as ve:
            raise HTTPException(status_code=409, detail=str(ve)) from ve
        return record

    @api_router.get("/tongue-of-yros/character/{character_id}")
    async def tongue_history(
        character_id: str,
        limit: int = 25,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        return await TongueOfYrosService(db).get_recent_attempts(character_id, limit=limit)

    @api_router.post("/tongue-of-yros/relinquish")
    async def tongue_relinquish(
        payload: TongueRelinquishPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            return await TongueOfYrosService(db).relinquish(character_id=payload.character_id)
        except ValueError as ve:
            raise HTTPException(status_code=409, detail=str(ve)) from ve
