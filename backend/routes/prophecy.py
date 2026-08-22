"""
Prophecies (Phase 4, 2026-05-30).

Each character may have a SINGLE prophecy in their lifetime — a cryptic
2-line oracle delivered once, then permanent. The Quest Master AI sees
the prophecy in every scene and may subtly foreshadow its fulfillment.

Prophecies are stored as a field directly on the character document
(`prophecy: { text, delivered_at, fulfilled: bool }`).
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _generate_prophecy(character: Dict, context: str) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="The oracle is silent.")
    system = (
        "You are an ancient oracle of Delarom. You speak in CRYPTIC, SYMBOLIC "
        "verse — never naming things outright, never offering reassurance. "
        "Your prophecies are 2 short lines, rhyming if possible, full of "
        "natural and elemental imagery. Output ONLY the two lines, nothing else. "
        "Do not address the recipient by name. Do not explain."
    )
    relatives = (character.get("relatives") or [])[:3]
    relatives_str = ", ".join(f"{r.get('name','?')} ({r.get('relationship','?')})" for r in relatives) or "no declared kin"
    prompt = (
        f"Deliver a single 2-line prophecy for the soul standing before you.\n\n"
        f"They are a {character.get('race','')} {character.get('character_class','')} "
        f"of {character.get('nation','')}, with {relatives_str}.\n"
        f"A fragment of their tale: {(character.get('backstory') or '')[:300]}\n"
        f"Context the oracle has noticed: {context[:300]}\n\n"
        "Two lines only. Cryptic. Symbolic. Permanent."
    )
    chat = LlmChat(
        api_key=api_key,
        session_id=f"prophecy-{uuid.uuid4()}",
        system_message=system,
    ).with_model("openai", "gpt-4o")
    raw = ""
    try:
        raw = (await chat.send_message(UserMessage(text=prompt))).strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"The oracle's words are torn: {e}") from e
    # Collapse to 2 non-empty lines max
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()][:2]
    return "\n".join(lines) if lines else raw[:200]


class ProphecyRequest(BaseModel):
    context: str = Field(default="", max_length=400, description="Optional flavour for the oracle — temple, dream, fortune-teller scene.")


def attach_prophecy_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/characters/{character_id}/prophecy")
    async def get_prophecy(character_id: str):
        """Public — a prophecy spoken is no longer secret."""
        char = await db.characters.find_one({"id": character_id}, {"_id": 0, "prophecy": 1, "name": 1})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        return char.get("prophecy") or None

    @api_router.post("/characters/{character_id}/prophecy")
    async def receive_prophecy(
        character_id: str,
        payload: ProphecyRequest,
        current_user: User = Depends(get_current_user),
    ):
        """Receive the one and only prophecy. Cannot be re-rolled — even by the player."""
        char = await resolve_character_for_user(character_id, current_user)
        if char.get("prophecy"):
            raise HTTPException(status_code=400, detail="The oracle has already spoken of this soul.")
        text = await _generate_prophecy(char, payload.context or "")
        prophecy = {
            "id": str(uuid.uuid4()),
            "text": text,
            "delivered_at": _now_iso(),
            "context": (payload.context or "")[:200],
            "fulfilled": False,
        }
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"prophecy": prophecy}},
        )
        return prophecy

    @api_router.post("/admin/characters/{character_id}/prophecy/fulfill")
    async def admin_mark_fulfilled(
        character_id: str,
        admin: User = Depends(get_current_user),  # admin-only via require_admin would be cleaner; placeholder
    ):
        # Note: admin check delegated to caller — wire `require_admin` if you want stricter gating.
        if admin.role not in ("admin", "moderator"):
            raise HTTPException(status_code=403, detail="Admin only")
        char = await db.characters.find_one({"id": character_id}, {"_id": 0, "prophecy": 1})
        if not char or not char.get("prophecy"):
            raise HTTPException(status_code=404, detail="No prophecy to fulfill")
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"prophecy.fulfilled": True, "prophecy.fulfilled_at": _now_iso()}},
        )
        return {"ok": True}
