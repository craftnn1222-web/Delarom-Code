"""
Personas / Secret Identities / Disguises (Phase 4, 2026-05-30).

A character may declare a Persona — a fake name, race, and short
backstory they assume in certain scenes. When the persona is ACTIVE:
  - NPCs in scene prompts see the persona's name + race (not the real one)
  - The character's bounty / criminal record / reputation are HIDDEN from
    the AI scene prompt — they are walking incognito.
  - The Quest Master AI receives a hint about the character's infamy
    so an observant NPC may *pierce* the disguise on their own initiative.

The real character_id is still used internally for crime detection — so
crimes committed in disguise are still recorded against the real soul.

Stored as a field on the character document:
  persona: { name, race, background, active, declared_at }
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersonaUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    race: Optional[str] = Field(default="", max_length=60)
    background: Optional[str] = Field(default="", max_length=600)


class PersonaToggle(BaseModel):
    active: bool


def attach_persona_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/characters/{character_id}/persona")
    async def get_persona(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Read the persona for one of your own characters. Returns null if
        none has been declared. The persona itself is intentionally NOT
        public — a disguise the world knows about is no disguise."""
        char = await resolve_character_for_user(character_id, current_user)
        return char.get("persona") or None

    @api_router.put("/characters/{character_id}/persona")
    async def upsert_persona(
        character_id: str,
        payload: PersonaUpsert,
        current_user: User = Depends(get_current_user),
    ):
        """Create or overwrite the persona for a character. Inactive by default
        — the player must explicitly turn it on."""
        char = await resolve_character_for_user(character_id, current_user)
        existing = char.get("persona") or {}
        persona = {
            "name": payload.name,
            "race": payload.race or "",
            "background": payload.background or "",
            "active": existing.get("active", False),
            "declared_at": existing.get("declared_at") or _now_iso(),
        }
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"persona": persona}},
        )
        return persona

    @api_router.post("/characters/{character_id}/persona/toggle")
    async def toggle_persona(
        character_id: str,
        payload: PersonaToggle,
        current_user: User = Depends(get_current_user),
    ):
        """Turn the persona on or off. Must already have been declared."""
        char = await resolve_character_for_user(character_id, current_user)
        if not char.get("persona"):
            raise HTTPException(status_code=400, detail="No persona declared. Create one first.")
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"persona.active": bool(payload.active)}},
        )
        char = await db.characters.find_one({"id": character_id}, {"_id": 0, "persona": 1})
        return char.get("persona")

    @api_router.delete("/characters/{character_id}/persona")
    async def drop_persona(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Forget the persona entirely. Cannot be retrieved."""
        await resolve_character_for_user(character_id, current_user)
        await db.characters.update_one(
            {"id": character_id},
            {"$unset": {"persona": ""}},
        )
        return {"ok": True}
