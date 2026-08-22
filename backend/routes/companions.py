"""Companion + player-owned NPC routes.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_companion_routes(api_router, ...)`.

Includes:
- 3 companion endpoints (list/bond/dismiss)
- 5 owned-NPC endpoints (list/create/update/delete/portrait)
"""
import os
from typing import Optional, Dict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Body

from npc_memory_service import NPCMemoryService
from image_service import ImageService


class OwnedNPCCreate(BaseModel):
    name: str
    race: str = "Human"
    role: str = "Companion"
    appearance: Optional[str] = ""
    personality: Optional[str] = ""
    motivation: Optional[str] = ""
    background: Optional[str] = ""
    quirks: Optional[str] = ""
    importance: Optional[str] = "commoner"
    nation: Optional[str] = ""
    location: Optional[str] = ""
    auto_bond: bool = True


class OwnedNPCUpdate(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    role: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    background: Optional[str] = None
    quirks: Optional[str] = None
    importance: Optional[str] = None


def attach_companion_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
    logger,
):
    @api_router.get("/characters/{character_id}/companions")
    async def list_character_companions(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """List all NPCs currently traveling with the given character."""
        await resolve_character_for_user(character_id, current_user)
        npc_service = NPCMemoryService(db)
        companions = await npc_service.list_companions(character_id)
        return companions

    @api_router.post("/npcs/{npc_id}/companion/bond")
    async def bond_npc_companion(
        npc_id: str,
        payload: Dict = Body(...),
        current_user: User = Depends(get_current_user),
    ):
        """Manually bond an NPC as the companion of the calling user's character.

        Body: `{ "character_id": "<id>" }`. The character must belong to the user.
        Most bonds happen via AI analysis; this endpoint exists for explicit player
        control (e.g. dismissing/re-bonding from the UI).
        """
        character_id = (payload or {}).get("character_id")
        if not character_id:
            raise HTTPException(status_code=400, detail="character_id is required")
        await resolve_character_for_user(character_id, current_user)
        npc_service = NPCMemoryService(db)
        success, message, npc = await npc_service.bond_companion(npc_id, character_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"ok": True, "message": message, "npc": npc}

    @api_router.post("/npcs/{npc_id}/companion/dismiss")
    async def dismiss_npc_companion(
        npc_id: str,
        payload: Dict = Body(...),
        current_user: User = Depends(get_current_user),
    ):
        """Dismiss an NPC who is currently a companion of the calling user's character.

        Body: `{ "character_id": "<id>" }`.
        """
        character_id = (payload or {}).get("character_id")
        if not character_id:
            raise HTTPException(status_code=400, detail="character_id is required")
        await resolve_character_for_user(character_id, current_user)
        npc_service = NPCMemoryService(db)
        success, message, npc = await npc_service.dismiss_companion(npc_id, character_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"ok": True, "message": message, "npc": npc}

    @api_router.get("/characters/{character_id}/owned-npcs")
    async def list_owned_npcs(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """List all player-managed NPCs (preset companions) for a character."""
        await resolve_character_for_user(character_id, current_user)
        npc_service = NPCMemoryService(db)
        return await npc_service.list_owned_npcs(character_id)

    @api_router.post("/characters/{character_id}/owned-npcs")
    async def create_owned_npc(
        character_id: str,
        payload: OwnedNPCCreate,
        current_user: User = Depends(get_current_user),
    ):
        """Create a custom NPC tied to a character. Auto-bonds as a companion by default.

        Use this to register preset companions like a steward, squire, animal
        familiar, etc. that should always travel with the character.
        """
        char = await resolve_character_for_user(character_id, current_user)
        npc_service = NPCMemoryService(db)
        data = payload.model_dump(exclude_none=False)
        auto_bond = bool(data.pop("auto_bond", True))
        npc = await npc_service.create_owned_npc(
            character_id=character_id,
            user_id=current_user.id,
            data=data,
            home_nation=char.get("nation", "") or "",
            home_location=char.get("location", "") or "",
            auto_bond=auto_bond,
        )
        return npc

    @api_router.patch("/owned-npcs/{npc_id}")
    async def update_owned_npc(
        npc_id: str,
        payload: OwnedNPCUpdate,
        current_user: User = Depends(get_current_user),
    ):
        """Edit a player-owned NPC. Caller must own the character that created it."""
        npc_service = NPCMemoryService(db)
        npc = await npc_service.get_npc(npc_id)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        owner_char_id = npc.get("created_by_character_id")
        if not owner_char_id:
            raise HTTPException(status_code=400, detail="That NPC is not player-managed")
        await resolve_character_for_user(owner_char_id, current_user)
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return npc
        success, message, updated = await npc_service.update_owned_npc(npc_id, owner_char_id, updates)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return updated

    @api_router.delete("/owned-npcs/{npc_id}")
    async def delete_owned_npc(
        npc_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Delete a player-owned NPC (and the relationship rows tied to it).

        Caller must own the character that created the NPC.
        """
        npc_service = NPCMemoryService(db)
        npc = await npc_service.get_npc(npc_id)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        owner_char_id = npc.get("created_by_character_id")
        if not owner_char_id:
            raise HTTPException(status_code=400, detail="That NPC is not player-managed")
        await resolve_character_for_user(owner_char_id, current_user)
        if npc.get("image_id"):
            await ImageService(db).delete(npc["image_id"])
        success, message = await npc_service.delete_owned_npc(npc_id, owner_char_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"ok": True, "message": message}

    @api_router.post("/owned-npcs/{npc_id}/portrait")
    async def generate_owned_npc_portrait(
        npc_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Generate an AI portrait for a player-owned NPC using the appearance text.

        Replaces any prior portrait. Returns the new image URL. Costs one image
        generation against the Emergent LLM Key budget.
        """
        npc_service = NPCMemoryService(db)
        npc = await npc_service.get_npc(npc_id)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        owner_char_id = npc.get("created_by_character_id")
        if not owner_char_id:
            raise HTTPException(status_code=400, detail="That NPC is not player-managed")
        await resolve_character_for_user(owner_char_id, current_user)

        name = npc.get("name", "a companion")
        race = npc.get("race") or "Human"
        role = npc.get("role") or "Companion"
        appearance = npc.get("appearance") or ""
        personality = npc.get("personality") or ""
        prompt = (
            f"Detailed character portrait of {name}, a {race} {role}. "
            f"Appearance: {appearance}. "
            f"Personality conveyed through expression: {personality}. "
            "Single-subject portrait, shoulders up, neutral background, "
            "high-fantasy realism, dramatic painterly lighting, masterwork digital art."
        )

        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            api_key = os.environ.get("EMERGENT_LLM_KEY")
            if not api_key:
                raise RuntimeError("EMERGENT_LLM_KEY is not set")
            image_gen = OpenAIImageGeneration(api_key=api_key)
            images = await image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1,
            )
        except Exception as e:
            logger.error(f"Portrait generation failed for NPC {npc_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Image service error: {e}")

        if not images:
            raise HTTPException(status_code=502, detail="No image was returned")

        raw = images[0]
        img_service = ImageService(db)
        if npc.get("image_id"):
            await img_service.delete(npc["image_id"])
        image_id = await img_service.store_bytes(raw, mime_type="image/png")
        await npc_service.update_npc(npc_id, {"image_id": image_id})

        return {"ok": True, "image_id": image_id, "image_url": f"/api/image/{image_id}"}
