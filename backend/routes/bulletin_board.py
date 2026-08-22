"""
Tavern Bulletin Board.

Per-location notice board where characters can post in-character notes
(caravan jobs, lost-and-found, recruitment, gossip). Notices auto-expire
after 7 days. Anyone can read; only the author or admin/mod can delete.
"""
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


class NoticeCreate(BaseModel):
    character_id: str
    body: str = Field(min_length=1, max_length=500)


def attach_bulletin_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.post("/locations/{nation}/{location}/notices")
    async def post_notice(
        nation: str,
        location: str,
        payload: NoticeCreate,
        current_user: User = Depends(get_current_user),
    ):
        char = await resolve_character_for_user(payload.character_id, current_user)
        now = _now()
        doc = {
            "id": str(uuid.uuid4()),
            "author_character_id": char["id"],
            "author_character_name": char.get("name", "Unknown"),
            "author_user_id": current_user.id,
            "nation": nation,
            "location": location,
            "body": payload.body,
            "posted_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "status": "active",
        }
        await db.bulletin_notices.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @api_router.get("/locations/{nation}/{location}/notices")
    async def list_notices(nation: str, location: str):
        """Public — anyone can read a tavern board."""
        now_iso = _now_iso()
        cursor = db.bulletin_notices.find(
            {
                "nation": nation,
                "location": location,
                "status": "active",
                "expires_at": {"$gt": now_iso},
            },
            {"_id": 0},
        ).sort("posted_at", -1)
        return await cursor.to_list(100)

    @api_router.delete("/notices/{notice_id}")
    async def remove_notice(notice_id: str, current_user: User = Depends(get_current_user)):
        notice = await db.bulletin_notices.find_one({"id": notice_id}, {"_id": 0})
        if not notice:
            raise HTTPException(status_code=404, detail="Notice not found")
        is_author = notice.get("author_user_id") == current_user.id
        is_staff = current_user.role in ("admin", "moderator")
        if not (is_author or is_staff):
            raise HTTPException(status_code=403, detail="You did not post that notice")
        await db.bulletin_notices.update_one(
            {"id": notice_id},
            {"$set": {"status": "removed", "removed_at": _now_iso()}},
        )
        return {"ok": True}
