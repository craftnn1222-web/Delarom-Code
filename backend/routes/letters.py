"""
Letters / Courier System.

Players send in-character letters to other players' characters. Letters
arrive after a delay based on whether sender and recipient are in the same
nation (30 min) or different nations (4 hours). Recipients see only
*delivered* letters in their inbox.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _delay_for_nations(sender_nation: str, recipient_nation: str) -> timedelta:
    if sender_nation and recipient_nation and sender_nation == recipient_nation:
        return timedelta(minutes=30)
    return timedelta(hours=4)


class LetterCreate(BaseModel):
    sender_character_id: str
    recipient_character_id: str
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)


def attach_letter_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.post("/letters")
    async def send_letter(payload: LetterCreate, current_user: User = Depends(get_current_user)):
        sender = await resolve_character_for_user(payload.sender_character_id, current_user)
        recipient = await db.characters.find_one(
            {"id": payload.recipient_character_id}, {"_id": 0}
        )
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient character not found")
        if recipient["id"] == sender["id"]:
            raise HTTPException(status_code=400, detail="You cannot send a letter to yourself")

        now = datetime.now(timezone.utc)
        deliver_at = now + _delay_for_nations(sender.get("nation", ""), recipient.get("nation", ""))
        doc = {
            "id": str(uuid.uuid4()),
            "sender_character_id": sender["id"],
            "sender_character_name": sender.get("name", "Unknown"),
            "sender_user_id": current_user.id,
            "recipient_character_id": recipient["id"],
            "recipient_character_name": recipient.get("name", "Unknown"),
            "recipient_user_id": recipient.get("user_id"),
            "subject": payload.subject,
            "body": payload.body,
            "sent_at": now.isoformat(),
            "deliver_at": deliver_at.isoformat(),
            "read_at": None,
        }
        await db.letters.insert_one(doc)
        doc.pop("_id", None)
        return doc

    def _decorate(letter: dict) -> dict:
        """Add a derived `status` field based on the current time."""
        now = datetime.now(timezone.utc)
        try:
            deliver_at = datetime.fromisoformat(letter["deliver_at"])
        except (KeyError, ValueError):
            deliver_at = now
        if letter.get("read_at"):
            letter["status"] = "read"
        elif now >= deliver_at:
            letter["status"] = "delivered"
        else:
            letter["status"] = "in_transit"
        return letter

    @api_router.get("/characters/{character_id}/letters/inbox")
    async def inbox(character_id: str, current_user: User = Depends(get_current_user)):
        await resolve_character_for_user(character_id, current_user)
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor = db.letters.find(
            {"recipient_character_id": character_id, "deliver_at": {"$lte": now_iso}},
            {"_id": 0},
        ).sort("deliver_at", -1)
        letters = await cursor.to_list(200)
        return [_decorate(letter) for letter in letters]

    @api_router.get("/characters/{character_id}/letters/sent")
    async def sent_letters(character_id: str, current_user: User = Depends(get_current_user)):
        await resolve_character_for_user(character_id, current_user)
        cursor = db.letters.find({"sender_character_id": character_id}, {"_id": 0}).sort("sent_at", -1)
        letters = await cursor.to_list(200)
        return [_decorate(letter) for letter in letters]

    @api_router.post("/letters/{letter_id}/read")
    async def mark_read(letter_id: str, current_user: User = Depends(get_current_user)):
        letter = await db.letters.find_one({"id": letter_id}, {"_id": 0})
        if not letter:
            raise HTTPException(status_code=404, detail="Letter not found")
        if letter.get("recipient_user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="That letter is not yours to read")
        if not letter.get("read_at"):
            await db.letters.update_one({"id": letter_id}, {"$set": {"read_at": _now_iso()}})
            letter["read_at"] = _now_iso()
        return _decorate(letter)
