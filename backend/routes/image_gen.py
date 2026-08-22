"""Auto-extracted routes module — image_gen.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_image_gen_routes(api_router, ...)`. The factory takes shared deps as
keyword args; route bodies close over them.
"""
from fastapi import APIRouter, Depends, HTTPException


def attach_image_gen_routes(
    api_router: APIRouter,
    *,
    db, User, get_current_user, image_gen, logger,
):
    # ==================== IMAGE GENERATION ROUTES ====================

    @api_router.post("/quests/{quest_id}/generate-image")
    async def generate_quest_image_endpoint(quest_id: str, current_user: User = Depends(get_current_user)):
        """Generate an AI image for a quest"""
        if image_gen is None:
            raise HTTPException(status_code=503, detail="Image generation not available")
    
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")
    
        # Only creator can generate image
        if quest_doc['creator_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Only quest creator can generate images")
    
        try:
            image_url = await image_gen.generate_quest_image(quest_doc)
        
            if image_url:
                # Store image URL with quest
                await db.quests.update_one(
                    {"id": quest_id},
                    {"$set": {"image_url": image_url}}
                )
                return {"image_url": image_url, "message": "Image generated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate image")
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @api_router.post("/characters/{character_id}/generate-portrait")
    async def generate_character_portrait_endpoint(character_id: str, current_user: User = Depends(get_current_user)):
        """Generate an AI portrait for a character"""
        if image_gen is None:
            raise HTTPException(status_code=503, detail="Image generation not available")
    
        char_doc = await db.characters.find_one({"id": character_id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
    
        # Only owner can generate portrait
        if char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Not your character")
    
        try:
            image_url = await image_gen.generate_character_portrait(char_doc)
        
            if image_url:
                # Store image URL with character
                await db.characters.update_one(
                    {"id": character_id},
                    {"$set": {"portrait_url": image_url}}
                )
                return {"image_url": image_url, "message": "Portrait generated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate portrait")
        except Exception as e:
            logger.error(f"Portrait generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

