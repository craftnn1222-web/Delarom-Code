"""
Sworn Bonds.

Player characters can propose narrative bonds to other characters —
blood-brothers, mentor/apprentice, sworn friends, rivals, parent/child.
The target character's owner must accept before the bond becomes
permanent. Either party can break an accepted bond.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


BOND_TYPES = {
    "blood-brothers": "Blood-brothers",
    "mentor-apprentice": "Mentor & Apprentice",
    "sworn-friends": "Sworn Friends",
    "rivals": "Rivals",
    "parent-child": "Parent & Child",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BondPropose(BaseModel):
    target_character_id: str
    bond_type: str
    proposal_text: str = Field(min_length=1, max_length=600)


class BondBreak(BaseModel):
    reason: Optional[str] = ""


def attach_bond_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/bonds/types")
    async def list_bond_types():
        """Return the canonical list of bond labels (display-name mapping)."""
        return BOND_TYPES

    @api_router.post("/characters/{character_id}/bonds/propose")
    async def propose_bond(
        character_id: str,
        payload: BondPropose,
        current_user: User = Depends(get_current_user),
    ):
        if payload.bond_type not in BOND_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid bond_type. Choose one of {list(BOND_TYPES)}")
        initiator = await resolve_character_for_user(character_id, current_user)
        if payload.target_character_id == character_id:
            raise HTTPException(status_code=400, detail="A character cannot bond with themselves")
        target = await db.characters.find_one({"id": payload.target_character_id}, {"_id": 0})
        if not target:
            raise HTTPException(status_code=404, detail="Target character not found")

        # Don't allow duplicate active or pending bonds between the same pair.
        existing = await db.character_bonds.find_one({
            "$or": [
                {"initiator_character_id": character_id, "target_character_id": payload.target_character_id},
                {"initiator_character_id": payload.target_character_id, "target_character_id": character_id},
            ],
            "status": {"$in": ["proposed", "accepted"]},
        })
        if existing:
            raise HTTPException(status_code=400, detail="A bond between these two characters already exists or is pending")

        doc = {
            "id": str(uuid.uuid4()),
            "initiator_character_id": initiator["id"],
            "initiator_character_name": initiator.get("name", "Unknown"),
            "initiator_user_id": current_user.id,
            "target_character_id": target["id"],
            "target_character_name": target.get("name", "Unknown"),
            "target_user_id": target.get("user_id"),
            "bond_type": payload.bond_type,
            "bond_label": BOND_TYPES[payload.bond_type],
            "proposal_text": payload.proposal_text,
            "status": "proposed",
            "proposed_at": _now_iso(),
            "accepted_at": None,
            "broken_at": None,
        }
        await db.character_bonds.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def _load_bond_for_party(bond_id: str, user_id: str) -> dict:
        bond = await db.character_bonds.find_one({"id": bond_id}, {"_id": 0})
        if not bond:
            raise HTTPException(status_code=404, detail="Bond not found")
        if bond.get("initiator_user_id") != user_id and bond.get("target_user_id") != user_id:
            raise HTTPException(status_code=403, detail="That bond is not yours")
        return bond

    @api_router.post("/bonds/{bond_id}/accept")
    async def accept_bond(bond_id: str, current_user: User = Depends(get_current_user)):
        bond = await _load_bond_for_party(bond_id, current_user.id)
        if bond["status"] != "proposed":
            raise HTTPException(status_code=400, detail="Bond is not pending")
        if bond.get("target_user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Only the target may accept the bond")
        await db.character_bonds.update_one(
            {"id": bond_id},
            {"$set": {"status": "accepted", "accepted_at": _now_iso()}},
        )
        bond["status"] = "accepted"
        bond["accepted_at"] = _now_iso()
        return bond

    @api_router.post("/bonds/{bond_id}/decline")
    async def decline_bond(bond_id: str, current_user: User = Depends(get_current_user)):
        bond = await _load_bond_for_party(bond_id, current_user.id)
        if bond["status"] != "proposed":
            raise HTTPException(status_code=400, detail="Bond is not pending")
        if bond.get("target_user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Only the target may decline the bond")
        await db.character_bonds.update_one(
            {"id": bond_id},
            {"$set": {"status": "declined", "declined_at": _now_iso()}},
        )
        return {"ok": True}

    @api_router.post("/bonds/{bond_id}/break")
    async def break_bond(
        bond_id: str,
        payload: BondBreak,
        current_user: User = Depends(get_current_user),
    ):
        bond = await _load_bond_for_party(bond_id, current_user.id)
        if bond["status"] != "accepted":
            raise HTTPException(status_code=400, detail="Only accepted bonds can be broken")
        await db.character_bonds.update_one(
            {"id": bond_id},
            {"$set": {
                "status": "broken",
                "broken_at": _now_iso(),
                "broken_by_user_id": current_user.id,
                "break_reason": (payload.reason or "")[:500],
            }},
        )
        bond["status"] = "broken"
        return bond

    @api_router.get("/characters/{character_id}/bonds")
    async def list_bonds_for_character(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """All bonds where this character is initiator OR target. Includes
        accepted, broken, and pending proposals (both directions)."""
        await resolve_character_for_user(character_id, current_user)
        cursor = db.character_bonds.find(
            {
                "$or": [
                    {"initiator_character_id": character_id},
                    {"target_character_id": character_id},
                ],
            },
            {"_id": 0},
        ).sort("proposed_at", -1)
        return await cursor.to_list(200)

    @api_router.get("/users/me/bonds")
    async def list_my_bonds(current_user: User = Depends(get_current_user)):
        """All bonds across all the calling user's characters, grouped by role."""
        cursor = db.character_bonds.find(
            {
                "$or": [
                    {"initiator_user_id": current_user.id},
                    {"target_user_id": current_user.id},
                ],
            },
            {"_id": 0},
        ).sort("proposed_at", -1)
        bonds = await cursor.to_list(500)
        return {
            "incoming_proposals": [b for b in bonds if b["status"] == "proposed" and b["target_user_id"] == current_user.id],
            "outgoing_proposals": [b for b in bonds if b["status"] == "proposed" and b["initiator_user_id"] == current_user.id],
            "accepted": [b for b in bonds if b["status"] == "accepted"],
            "history": [b for b in bonds if b["status"] in ("broken", "declined")],
        }
