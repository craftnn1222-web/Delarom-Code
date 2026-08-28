"""Auto-extracted routes module — characters.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_character_routes(api_router, ...)`. The factory takes shared deps as
keyword args; route bodies close over them.
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from image_service import ImageService


class ActiveCharacterRequest(BaseModel):
    character_id: str


def attach_character_routes(
    api_router: APIRouter,
    *,
    db, User, get_current_user, Character, CharacterCreate,
):
    # ==================== CHARACTER ROUTES ====================

    @api_router.post("/characters", response_model=Character)
    async def create_character(char_data: CharacterCreate, current_user: User = Depends(get_current_user)):
        character = Character(
            user_id=current_user.id,
            **char_data.model_dump()
        )
    
        char_doc = character.model_dump()
        char_doc['created_at'] = char_doc['created_at'].isoformat()
    
        await db.characters.insert_one(char_doc)
        return character

    @api_router.get("/characters", response_model=List[Character])
    async def get_my_characters(current_user: User = Depends(get_current_user)):
        characters = await db.characters.find({"user_id": current_user.id}, {"_id": 0}).to_list(100)
        for char in characters:
            if isinstance(char.get('created_at'), str):
                char['created_at'] = datetime.fromisoformat(char['created_at'])
        return characters

    @api_router.get("/characters/active")
    async def get_active_character(current_user: User = Depends(get_current_user)):
        """Return the user's globally-selected active hero (falls back to their
        first character). Registered BEFORE /characters/{character_id} so the
        static path wins. Returns {"character": null} when they have none."""
        chars = await db.characters.find({"user_id": current_user.id}, {"_id": 0}).to_list(100)
        if not chars:
            return {"character": None, "active_character_id": None}
        active_id = getattr(current_user, "active_character_id", None)
        chosen = next((c for c in chars if c.get("id") == active_id), None) or chars[0]
        if isinstance(chosen.get("created_at"), str):
            chosen["created_at"] = datetime.fromisoformat(chosen["created_at"])
        return {"character": Character(**chosen), "active_character_id": chosen["id"]}

    @api_router.put("/characters/active")
    async def set_active_character(
        payload: ActiveCharacterRequest,
        current_user: User = Depends(get_current_user),
    ):
        """Set the user's active hero (validates ownership)."""
        char = await db.characters.find_one(
            {"id": payload.character_id, "user_id": current_user.id}, {"_id": 0}
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"active_character_id": payload.character_id}},
        )
        if isinstance(char.get("created_at"), str):
            char["created_at"] = datetime.fromisoformat(char["created_at"])
        return {"character": Character(**char), "active_character_id": payload.character_id}

    @api_router.get("/characters/{character_id}", response_model=Character)
    async def get_character(character_id: str):
        char_doc = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
        if isinstance(char_doc.get('created_at'), str):
            char_doc['created_at'] = datetime.fromisoformat(char_doc['created_at'])
        return Character(**char_doc)


    @api_router.post("/characters/{character_id}/upload-image")
    async def upload_character_image(
        character_id: str,
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
    ):
        """Upload a custom image for a character"""
        # Verify character belongs to user
        char_doc = await db.characters.find_one({"id": character_id, "user_id": current_user.id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
    
        # Check file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
    
        # Check file size (max 5MB)
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
    
        # Persist bytes to object storage and reference by a short URL. Storing
        # multi-MB base64 data URIs directly on the character bloated every list
        # endpoint that returns portraits (e.g. the member directory).
        img_service = ImageService(db)
        image_id = await img_service.store_bytes(contents, mime_type=file.content_type)
        portrait_url = f"/api/image/{image_id}"
    
        # Update character with custom image
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"portrait_url": portrait_url, "image_id": image_id, "custom_image": True}}
        )
    
        return {"message": "Image uploaded successfully", "portrait_url": portrait_url}


    @api_router.put("/characters/{character_id}", response_model=Character)
    async def update_character(character_id: str, char_data: CharacterCreate, current_user: User = Depends(get_current_user)):
        char_doc = await db.characters.find_one({"id": character_id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
        if char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
        update_data = char_data.model_dump()
        await db.characters.update_one({"id": character_id}, {"$set": update_data})
    
        updated_doc = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if isinstance(updated_doc.get('created_at'), str):
            updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
        return Character(**updated_doc)

    @api_router.delete("/characters/{character_id}")
    async def delete_character(character_id: str, current_user: User = Depends(get_current_user)):
        char_doc = await db.characters.find_one({"id": character_id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
        if char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
        await db.characters.delete_one({"id": character_id})
        return {"message": "Character deleted successfully"}

