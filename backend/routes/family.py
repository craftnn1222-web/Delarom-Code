"""
Family & Bloodline (Phase 3, 2026-05-30).

Each character carries a list of declared relatives. Each entry is a small
free-form record — name, relationship, status, story. NPCs may reference
these in scenes ("Are you any kin to the Veltraus of Ashen Falls?").

The data lives on the character document as a `relatives` array. Endpoints
add / patch / delete entries by relative-id; the array is overwritten as
a whole on each write for simplicity.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


RELATIONSHIP_TYPES = [
    "parent", "child", "sibling", "spouse", "grandparent", "grandchild",
    "aunt-uncle", "niece-nephew", "cousin", "in-law", "guardian", "ward",
    "stepparent", "stepchild", "estranged-kin", "ancestor",
]

STATUS_TYPES = ["living", "deceased", "missing", "estranged", "unknown"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RelativeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relationship: str = Field(description="One of RELATIONSHIP_TYPES")
    status: str = Field(default="unknown", description="One of STATUS_TYPES")
    story: Optional[str] = Field(default="", max_length=800)


class RelativeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    relationship: Optional[str] = None
    status: Optional[str] = None
    story: Optional[str] = Field(default=None, max_length=800)


def attach_family_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/family/relationship-types")
    async def get_relationship_types():
        """Static reference data for the family-tree UI."""
        return {"relationships": RELATIONSHIP_TYPES, "statuses": STATUS_TYPES}

    @api_router.get("/characters/{character_id}/family")
    async def list_relatives(character_id: str):
        """Public — anyone can read a character's declared family.

        Family is part of public character lore, intentionally not hidden.
        """
        char = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        return char.get("relatives", []) or []

    @api_router.post("/characters/{character_id}/family")
    async def add_relative(
        character_id: str,
        payload: RelativeCreate,
        current_user: User = Depends(get_current_user),
    ):
        if payload.relationship not in RELATIONSHIP_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid relationship. Choose one of {RELATIONSHIP_TYPES}")
        if payload.status not in STATUS_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Choose one of {STATUS_TYPES}")
        await resolve_character_for_user(character_id, current_user)
        relative = {
            "id": str(uuid.uuid4()),
            "name": payload.name,
            "relationship": payload.relationship,
            "status": payload.status,
            "story": payload.story or "",
            "added_at": _now_iso(),
        }
        await db.characters.update_one(
            {"id": character_id},
            {"$push": {"relatives": relative}},
        )
        return relative

    @api_router.patch("/characters/{character_id}/family/{relative_id}")
    async def update_relative(
        character_id: str,
        relative_id: str,
        payload: RelativeUpdate,
        current_user: User = Depends(get_current_user),
    ):
        await resolve_character_for_user(character_id, current_user)
        char = await db.characters.find_one({"id": character_id}, {"_id": 0})
        relatives: List[Dict] = char.get("relatives", []) or []
        match = next((r for r in relatives if r.get("id") == relative_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Relative not found")
        if payload.relationship is not None and payload.relationship not in RELATIONSHIP_TYPES:
            raise HTTPException(status_code=400, detail="Invalid relationship.")
        if payload.status is not None and payload.status not in STATUS_TYPES:
            raise HTTPException(status_code=400, detail="Invalid status.")
        updates = payload.model_dump(exclude_none=True)
        match.update(updates)
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"relatives": relatives}},
        )
        return match

    @api_router.delete("/characters/{character_id}/family/{relative_id}")
    async def delete_relative(
        character_id: str,
        relative_id: str,
        current_user: User = Depends(get_current_user),
    ):
        await resolve_character_for_user(character_id, current_user)
        result = await db.characters.update_one(
            {"id": character_id},
            {"$pull": {"relatives": {"id": relative_id}}},
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Relative not found")
        return {"ok": True}
