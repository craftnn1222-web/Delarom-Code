"""Routes for the Four Elder Gods Prayer System (Tier 2a).

Registered via `attach_prayer_routes(api_router, ...)`.

Endpoints:
  GET  /api/prayers/gods                    — public; list the four Elder Gods + domains
  POST /api/prayers/submit                  — authed; submit a prayer for a character
  GET  /api/prayers/recent                  — authed; my recent prayers (any character)
  GET  /api/prayers/character/{cid}         — authed; one character's prayer history
  GET  /api/prayers/character/{cid}/active  — authed; active blessings for one character
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from elder_gods_festivals import get_active_festival, list_calendar
from prayer_service import GODS, PrayerService, list_gods


class PrayerSubmitPayload(BaseModel):
    character_id: str = Field(..., min_length=1, max_length=128)
    god: str = Field(..., min_length=1, max_length=32)
    prayer_text: str = Field(..., min_length=10, max_length=1500)


def attach_prayer_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    @api_router.get("/prayers/gods")
    async def prayers_list_gods():
        """Public catalogue of the Four Elder Gods + their domains and race affinities."""
        return {"gods": list_gods()}

    @api_router.get("/prayers/festivals")
    async def prayers_festivals():
        """Public — the Elder-Gods festival calendar + whichever festival
        (if any) is active right now. The client shows this as a banner on
        the /prayers page so players can plan their prayers around a
        festival window."""
        active = get_active_festival()
        return {
            "active": active,
            "calendar": list_calendar(),
        }

    @api_router.post("/prayers/submit")
    async def prayers_submit(
        payload: PrayerSubmitPayload,
        current_user: User = Depends(get_current_user),
    ):
        god_key = payload.god.strip().lower()
        if god_key not in GODS:
            raise HTTPException(status_code=400, detail=f"Unknown god '{payload.god}'. Must be one of: {', '.join(GODS)}.")
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            record = await PrayerService(db).submit_prayer(
                character=char,
                god_key=god_key,
                prayer_text=payload.prayer_text,
            )
        except ValueError as ve:
            raise HTTPException(status_code=409, detail=str(ve)) from ve
        return record

    @api_router.get("/prayers/recent")
    async def prayers_recent_for_me(
        limit: int = 25,
        current_user: User = Depends(get_current_user),
    ):
        """All recent prayers across all of the current user's characters."""
        owned = await db.characters.find(
            {"user_id": current_user.id}, {"_id": 0, "id": 1},
        ).to_list(length=200)
        owned_ids = [c["id"] for c in owned]
        if not owned_ids:
            return []
        rows = await db.prayers.find(
            {"character_id": {"$in": owned_ids}}, {"_id": 0}
        ).sort("prayed_at", -1).limit(max(1, min(100, limit))).to_list(length=limit)
        return rows

    @api_router.get("/prayers/character/{character_id}")
    async def prayers_for_character(
        character_id: str,
        limit: int = 20,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        return await PrayerService(db).get_recent_prayers(character_id, limit=limit)

    @api_router.get("/prayers/character/{character_id}/active")
    async def prayers_active_for_character(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": character_id, "user_id": current_user.id},
            {"_id": 0, "id": 1},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        active = await PrayerService(db).get_active_blessings(character_id)
        return {"active_blessings": active}
