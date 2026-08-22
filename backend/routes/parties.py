"""Routes for the Party Quests MVP (Phase 2).

Registered via `attach_party_routes(api_router, ...)`.

Endpoints (all authed):
  POST /api/parties                       — create a party as host
  GET  /api/parties                       — list open parties
  GET  /api/parties/mine                  — list my parties (host or member)
  GET  /api/parties/{id}                  — party details
  POST /api/parties/{id}/join             — join as a player
  POST /api/parties/{id}/leave            — leave the party (not host)
  POST /api/parties/{id}/start            — host: transition to active
  POST /api/parties/{id}/finish           — host: end the party
  POST /api/parties/{id}/action           — submit a turn action
  GET  /api/parties/{id}/actions          — full scene log
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from party_service import PartyService


def _raise_from_value_error(ve: ValueError) -> None:
    """Translate a service ValueError into the right HTTP status."""
    msg = str(ve)
    if "not found" in msg.lower():
        raise HTTPException(status_code=404, detail=msg) from ve
    raise HTTPException(status_code=409, detail=msg) from ve


class PartyCreatePayload(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    scene_description: str = Field(..., min_length=20, max_length=1500)
    location: str = Field(..., min_length=2, max_length=160)
    host_character_id: str = Field(..., min_length=1, max_length=128)
    max_members: int = Field(default=6, ge=2, le=8)


class PartyJoinPayload(BaseModel):
    character_id: str = Field(..., min_length=1, max_length=128)


class PartyActionPayload(BaseModel):
    action_text: str = Field(..., min_length=3, max_length=2000)


def attach_party_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    @api_router.post("/parties")
    async def create_party(
        payload: PartyCreatePayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.host_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            return await PartyService(db).create_party(
                host_user={
                    "id": current_user.id,
                    "username": current_user.username,
                },
                host_character=char,
                name=payload.name,
                scene_description=payload.scene_description,
                location=payload.location,
                max_members=payload.max_members,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.get("/parties")
    async def list_parties(
        status: Optional[str] = None,
        limit: int = 50,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await PartyService(db).list_parties(status=status, limit=limit)
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.get("/parties/mine")
    async def list_my_parties(current_user: User = Depends(get_current_user)):
        rows = await db.parties.find(
            {"members.user_id": current_user.id}, {"_id": 0},
        ).sort("created_at", -1).to_list(length=100)
        return rows

    @api_router.get("/parties/{party_id}")
    async def get_party(
        party_id: str,
        current_user: User = Depends(get_current_user),
    ):
        p = await PartyService(db).get_party(party_id)
        if not p:
            raise HTTPException(status_code=404, detail="Party not found.")
        return p

    @api_router.post("/parties/{party_id}/join")
    async def join_party(
        party_id: str,
        payload: PartyJoinPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            return await PartyService(db).join_party(
                party_id=party_id,
                user={
                    "id": current_user.id,
                    "username": current_user.username,
                },
                character=char,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/parties/{party_id}/leave")
    async def leave_party(
        party_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await PartyService(db).leave_party(
                party_id=party_id,
                user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/parties/{party_id}/start")
    async def start_party(
        party_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await PartyService(db).start_party(
                party_id=party_id,
                user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/parties/{party_id}/finish")
    async def finish_party(
        party_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await PartyService(db).finish_party(
                party_id=party_id,
                user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/parties/{party_id}/action")
    async def submit_action(
        party_id: str,
        payload: PartyActionPayload,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await PartyService(db).submit_action(
                party_id=party_id,
                user_id=current_user.id,
                action_text=payload.action_text,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.get("/parties/{party_id}/actions")
    async def get_party_actions(
        party_id: str,
        limit: int = 500,
        current_user: User = Depends(get_current_user),
    ):
        p = await PartyService(db).get_party(party_id)
        if not p:
            raise HTTPException(status_code=404, detail="Party not found.")
        return await PartyService(db).get_actions(party_id, limit=limit)
