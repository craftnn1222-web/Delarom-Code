"""
Memorial Hall — "The Dead Linger" (Phase 3, 2026-05-30).

When a character dies (executed, killed in RP, retired by the user), they
are not erased — they are moved to the Memorial Hall. Anyone can browse
the dead. The world remembers.

A character is considered "dead" if their `is_active` flag is False AND
their `status` is one of {"executed", "deceased", "retired"}.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage


DEAD_STATUSES = {"executed", "deceased", "retired"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _generate_eulogy(character: Dict, cause: str) -> str:
    """AI-generate a short eulogy on demand. Returns "" on failure."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return ""
    system = (
        "You are an archivist of Delarom recording brief, dignified eulogies "
        "for the deceased. Tone: solemn, evocative, never sentimental. "
        "Output ONLY the eulogy prose — no preamble, no headings, no quotes."
    )
    prompt = (
        f"Compose a 2-3 sentence eulogy for the character below. "
        f"Mention nation if relevant; capture them as a person, not a stat sheet.\n\n"
        f"Name: {character.get('name','Unknown')}\n"
        f"Race: {character.get('race','Unknown')}\n"
        f"Class: {character.get('character_class','')}\n"
        f"Nation: {character.get('nation','')}\n"
        f"Backstory excerpt: {(character.get('backstory') or '')[:400]}\n"
        f"Cause of death: {cause}"
    )
    chat = LlmChat(
        api_key=api_key,
        session_id=f"eulogy-{uuid.uuid4()}",
        system_message=system,
    ).with_model("openai", "gpt-4o")
    try:
        return (await chat.send_message(UserMessage(text=prompt))).strip()
    except Exception:
        return ""


class EulogyRequest(BaseModel):
    cause: Optional[str] = Field(default="", max_length=400)


def attach_memorial_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
    resolve_character_for_user,
):
    @api_router.get("/memorial")
    async def list_memorial(nation: Optional[str] = None, limit: int = 100):
        """Public — list all dead characters."""
        q: Dict = {
            "is_active": False,
            "status": {"$in": list(DEAD_STATUSES)},
        }
        if nation:
            q["nation"] = nation
        cursor = db.characters.find(q, {"_id": 0}).sort("died_at", -1)
        chars = await cursor.to_list(min(max(limit, 1), 500))
        # Strip image_url base64 (legacy heavy field) — return image_id only.
        for c in chars:
            c.pop("image_url", None)
        return chars

    @api_router.get("/memorial/{character_id}")
    async def get_memorial(character_id: str):
        char = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        if char.get("is_active", True):
            raise HTTPException(status_code=404, detail="That soul still walks the world")
        char.pop("image_url", None)
        return char

    @api_router.post("/characters/{character_id}/retire")
    async def retire_character(
        character_id: str,
        payload: EulogyRequest,
        current_user: User = Depends(get_current_user),
    ):
        """Player-initiated retirement. The character joins the Memorial Hall
        with an AI-generated eulogy. Permanent — there is no reverse on the
        player side (only admin revival can undo it)."""
        char = await resolve_character_for_user(character_id, current_user)
        if not char.get("is_active", True):
            raise HTTPException(status_code=400, detail="That character has already passed")

        cause = (payload.cause or "Their tale came to an end.").strip()
        eulogy = await _generate_eulogy(char, cause)
        now = _now_iso()
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {
                "is_active": False,
                "status": "retired",
                "died_at": now,
                "cause_of_death": cause,
                "eulogy": eulogy,
            }},
        )
        return {"ok": True, "died_at": now, "cause_of_death": cause, "eulogy": eulogy}

    @api_router.post("/admin/characters/{character_id}/eulogize")
    async def admin_eulogize(
        character_id: str,
        payload: EulogyRequest,
        admin: User = Depends(require_admin),
    ):
        """Admin: generate / regenerate the eulogy for an already-dead character
        (useful for characters that died via the law system before eulogies
        existed). Idempotent — overwrites any prior eulogy."""
        char = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        if char.get("is_active", True):
            raise HTTPException(status_code=400, detail="Character is still alive")
        cause = (payload.cause or char.get("cause_of_death") or "Cause unknown.").strip()
        eulogy = await _generate_eulogy(char, cause)
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"eulogy": eulogy, "cause_of_death": cause}},
        )
        return {"eulogy": eulogy}
