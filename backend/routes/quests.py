"""Auto-extracted routes module — quests.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_quest_routes(api_router, ...)`. The factory takes shared deps as
keyword args; route bodies close over them.
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException


def attach_quest_routes(
    api_router: APIRouter,
    *,
    db, User, get_current_user, require_moderator, Quest, QuestCreate, QuestAcceptance, QuestAcceptRequest, QuestAction, QuestActionCreate, Transaction, TransactionType, quest_master, logger,
):
    # ==================== QUEST ROUTES ====================

    @api_router.post("/quests", response_model=Quest)
    async def create_quest(quest_data: QuestCreate, current_user: User = Depends(get_current_user)):
        # Auto-calculate XP based on difficulty if not provided
        if quest_data.reward_xp is None:
            xp_by_difficulty = {
                "easy": 50,
                "medium": 100,
                "hard": 200,
                "legendary": 400
            }
            quest_data.reward_xp = xp_by_difficulty.get(quest_data.difficulty, 50)
    
        quest = Quest(
            creator_id=current_user.id,
            creator_username=current_user.username,
            **quest_data.model_dump()
        )
    
        quest_doc = quest.model_dump()
        quest_doc['created_at'] = quest_doc['created_at'].isoformat()
    
        await db.quests.insert_one(quest_doc)
    
        # Initialize AI Quest Master narration
        try:
            opening_narration = await quest_master.initialize_quest(quest_doc)
            # Store opening narration as first action
            initial_action = QuestAction(
                quest_id=quest.id,
                user_id="SYSTEM",
                character_id="QUEST_MASTER",
                character_name="Quest Master",
                character_race="AI",
                character_class="Narrator",
                action_text="[Quest Opening]",
                ai_response=opening_narration,
                turn_number=0
            )
            action_doc = initial_action.model_dump()
            action_doc['created_at'] = action_doc['created_at'].isoformat()
            await db.quest_actions.insert_one(action_doc)
        except Exception as e:
            logger.error(f"Failed to initialize AI for quest {quest.id}: {e}")
    
        return quest

    @api_router.get("/quests/my-quests/created", response_model=List[Quest])
    async def get_my_created_quests(current_user: User = Depends(get_current_user)):
        """List quests created by the current user.

        Used for the "My Created Quests" view so quest creators can manage
        the quests they own separately from quests they participate in.
        """
        quests = await db.quests.find(
            {"creator_id": current_user.id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)

        for quest in quests:
            if isinstance(quest.get("created_at"), str):
                quest["created_at"] = datetime.fromisoformat(quest["created_at"])

        return [Quest(**q) for q in quests]


    @api_router.get("/quests", response_model=List[Quest])
    async def get_quests(nation: Optional[str] = None, difficulty: Optional[str] = None, status: Optional[str] = "open"):
        query = {}
        if nation:
            query['nation'] = nation
        if difficulty:
            query['difficulty'] = difficulty
        if status:
            query['status'] = status
    
        quests = await db.quests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        for quest in quests:
            if isinstance(quest.get('created_at'), str):
                quest['created_at'] = datetime.fromisoformat(quest['created_at'])
        return quests

    @api_router.get("/quests/{quest_id}", response_model=Quest)
    async def get_quest(quest_id: str):
        quest_doc = await db.quests.find_one({"id": quest_id}, {"_id": 0})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")
        if isinstance(quest_doc.get('created_at'), str):
            quest_doc['created_at'] = datetime.fromisoformat(quest_doc['created_at'])
        return Quest(**quest_doc)

    @api_router.post("/quests/{quest_id}/accept")
    async def accept_quest(quest_id: str, payload: QuestAcceptRequest, current_user: User = Depends(get_current_user)):
        # Check if quest exists
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")
    
        # Check if character belongs to user
        char_doc = await db.characters.find_one({"id": payload.character_id})
        if not char_doc or char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Character not found or not authorized")
    
        # Check if already accepted
        existing = await db.quest_acceptances.find_one({"quest_id": quest_id, "user_id": current_user.id})
        if existing:
            raise HTTPException(status_code=400, detail="You have already accepted this quest")
    
        # Check if quest is full
        if quest_doc['current_acceptors'] >= quest_doc['max_acceptors']:
            raise HTTPException(status_code=400, detail="Quest is full")
    
        # Create acceptance
        acceptance = QuestAcceptance(
            quest_id=quest_id,
            user_id=current_user.id,
            character_id=payload.character_id
        )
    
        acc_doc = acceptance.model_dump()
        acc_doc['accepted_at'] = acc_doc['accepted_at'].isoformat()
    
        await db.quest_acceptances.insert_one(acc_doc)
    
        # Update quest acceptor count
        await db.quests.update_one(
            {"id": quest_id},
            {"$inc": {"current_acceptors": 1}}
        )

        return {"message": "Quest accepted successfully", "acceptance_id": acceptance.id}


    @api_router.delete("/quests/{quest_id}")
    async def delete_quest(quest_id: str, moderator: User = Depends(require_moderator)):
        """Delete a quest from the board.

        - Admins and moderators can delete any quest.
        - Quest creators can also delete their own quests.
        """
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")

        # Allow admins/moderators always; also allow quest creator to delete their own quests
        if moderator.role not in ["admin", "moderator"] and quest_doc.get("creator_id") != moderator.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this quest")

        # Delete quest and its related records (actions and acceptances)
        await db.quests.delete_one({"id": quest_id})
        await db.quest_acceptances.delete_many({"quest_id": quest_id})
        await db.quest_actions.delete_many({"quest_id": quest_id})

        return {"message": f"Quest '{quest_doc['title']}' has been removed from the board"}

    @api_router.post("/quests/{quest_id}/complete")
    async def complete_quest(quest_id: str, current_user: User = Depends(get_current_user)):
        """[DEPRECATED] Participant self-complete endpoint.

        Disabled in favor of quest-creator controlled completion.
        """
        raise HTTPException(status_code=403, detail="Only quest creator can complete quests. Completion is now handled by the quest creator.")


    @api_router.post("/quests/{quest_id}/participants/{acceptance_id}/complete")
    # Legacy creator completion implementation (kept for reference, not used)
    async def creator_complete_quest_participant_legacy(
        quest_id: str,
        acceptance_id: str,
        current_user: User = Depends(get_current_user)
    ):
        """[LEGACY] Old implementation, kept to avoid losing logic."""
        # Verify quest exists
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")

        # Only quest creator may complete participants
        if quest_doc.get("creator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Only the quest creator can complete participants")

        # Find acceptance
        acceptance_doc = await db.quest_acceptances.find_one({
            "id": acceptance_id,
            "quest_id": quest_id,
            "status": "accepted"
        })

        if not acceptance_doc:
            raise HTTPException(status_code=404, detail="Quest acceptance not found or already completed")

        # Get participant user & character
        participant_user_id = acceptance_doc["user_id"]
        char_doc = await db.characters.find_one({"id": acceptance_doc["character_id"]})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")

        # Update acceptance status
        await db.quest_acceptances.update_one(
            {"id": acceptance_doc["id"]},
            {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
        )

        # Award currency to participant
        reward_gold = quest_doc["reward_currency"]
        reward_xp = quest_doc.get("reward_xp", 50)

        await db.users.update_one({"id": participant_user_id}, {"$inc": {"currency": reward_gold}})

        # Award XP and check for level up
        new_xp = char_doc.get("xp", 0) + reward_xp
        current_level = char_doc.get("level", 1)
        xp_to_next = char_doc.get("xp_to_next_level", 100)
        leveled_up = False
        new_level = current_level

        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            new_level += 1
            xp_to_next = new_level * 100
            leveled_up = True

        # Update character
        await db.characters.update_one(
            {"id": char_doc["id"]},
            {"$set": {
                "xp": new_xp,
                "level": new_level,
                "xp_to_next_level": xp_to_next
            }}
        )

        # Award item rewards
        reward_items = quest_doc.get("reward_items", [])
        items_received = []

        for item_reward in reward_items:
            inventory_item = {
                "id": str(uuid.uuid4()),
                "name": item_reward["name"],
                "description": item_reward.get("description", ""),
                "item_type": item_reward.get("item_type", "equipment"),
                "equipment_slot": item_reward.get("equipment_slot"),
                "stat_bonuses": item_reward.get("stat_bonuses", {}),
                "acquired_from": "quest_reward",
                "quest_id": quest_id,
                "acquired_at": datetime.now(timezone.utc).isoformat()
            }

            await db.characters.update_one(
                {"id": char_doc["id"]},
                {"$push": {"inventory": inventory_item}}
            )
            items_received.append(item_reward["name"])

        # Create transaction for participant
        transaction = Transaction(
            user_id=participant_user_id,
            amount=reward_gold,
            transaction_type=TransactionType.QUEST_REWARD,
            description=f"Completed quest: {quest_doc['title']}",
            related_id=quest_id
        )
        trans_doc = transaction.model_dump()
        trans_doc["created_at"] = trans_doc["created_at"].isoformat()
        await db.transactions.insert_one(trans_doc)

        level_up_message = f" Participant leveled up to level {new_level}!" if leveled_up else ""
        items_message = f" Items received: {', '.join(items_received)}" if items_received else ""

        return {
            "message": f"Participant quest completed!{level_up_message}{items_message}",
            "reward": reward_gold,
            "reward_xp": reward_xp,
            "reward_items": items_received,
            "leveled_up": leveled_up,
            "new_level": new_level if leveled_up else current_level,
            "character_name": char_doc["name"],
        }


    @api_router.post("/quests/{quest_id}/participants/{acceptance_id}/complete")
    async def creator_complete_quest_participant(
        quest_id: str,
        acceptance_id: str,
        current_user: User = Depends(get_current_user)
    ):
        # Find acceptance
        acceptance_doc = await db.quest_acceptances.find_one({
            "quest_id": quest_id,
            "user_id": current_user.id,
            "status": "accepted"
        })
    
        if not acceptance_doc:
            raise HTTPException(status_code=404, detail="Quest acceptance not found or already completed")
    
        # Get quest
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")
    
        # Only quest creator may complete participants
        if quest_doc.get('creator_id') != current_user.id:
            raise HTTPException(status_code=403, detail="Only the quest creator can complete participants")

        # Get participant user & character
        participant_user_id = acceptance_doc['user_id']

        # Get participant character
        char_doc = await db.characters.find_one({"id": acceptance_doc['character_id']})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
    
        # Update acceptance status
        await db.quest_acceptances.update_one(
            {"id": acceptance_doc['id']},
            {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
        )
    
        # Award currency to participant
        reward_gold = quest_doc['reward_currency']
        reward_xp = quest_doc.get('reward_xp', 50)
    
        await db.users.update_one({"id": participant_user_id}, {"$inc": {"currency": reward_gold}})
    
        # Award XP and check for level up
        new_xp = char_doc.get('xp', 0) + reward_xp
        current_level = char_doc.get('level', 1)
        xp_to_next = char_doc.get('xp_to_next_level', 100)
        leveled_up = False
        new_level = current_level
    
        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            new_level += 1
            xp_to_next = new_level * 100
            leveled_up = True
    
        # Update character
        await db.characters.update_one(
            {"id": char_doc['id']},
            {"$set": {
                "xp": new_xp,
                "level": new_level,
                "xp_to_next_level": xp_to_next
            }}
        )
    
        # Award item rewards
        reward_items = quest_doc.get('reward_items', [])
        items_received = []
    
        for item_reward in reward_items:
            inventory_item = {
                "id": str(uuid.uuid4()),
                "name": item_reward['name'],
                "description": item_reward.get('description', ''),
                "item_type": item_reward.get('item_type', 'equipment'),
                "equipment_slot": item_reward.get('equipment_slot'),
                "stat_bonuses": item_reward.get('stat_bonuses', {}),
                "acquired_from": "quest_reward",
                "quest_id": quest_id,
                "acquired_at": datetime.now(timezone.utc).isoformat()
            }
        
            await db.characters.update_one(
                {"id": char_doc['id']},
                {"$push": {"inventory": inventory_item}}
            )
            items_received.append(item_reward['name'])
    
        # Create transaction for participant
        transaction = Transaction(
            user_id=participant_user_id,
            amount=reward_gold,
            transaction_type=TransactionType.QUEST_REWARD,
            description=f"Completed quest: {quest_doc['title']}",
            related_id=quest_id
        )
        trans_doc = transaction.model_dump()
        trans_doc['created_at'] = trans_doc['created_at'].isoformat()
        await db.transactions.insert_one(trans_doc)
    
        level_up_message = f" Participant leveled up to level {new_level}!" if leveled_up else ""
        items_message = f" Items received: {', '.join(items_received)}" if items_received else ""
    
        return {
            "message": f"Participant quest completed!{level_up_message}{items_message}",
            "reward": reward_gold,
            "reward_xp": reward_xp,
            "reward_items": items_received,
            "leveled_up": leveled_up,
            "new_level": new_level if leveled_up else current_level,
            "character_name": char_doc['name']
        }

    @api_router.get("/quests/my-quests/accepted", response_model=List[dict])
    async def get_my_accepted_quests(current_user: User = Depends(get_current_user)):
        acceptances = await db.quest_acceptances.find(
            {"user_id": current_user.id},
            {"_id": 0}
        ).to_list(100)
    
        result = []
        for acc in acceptances:
            quest_doc = await db.quests.find_one({"id": acc['quest_id']}, {"_id": 0})
            if quest_doc:
                # Lightweight character projection — clients only need id/name/race/class
                # here. Excluding portrait_url avoids shipping multi-MB base64 portraits
                # in this list payload (kept the response small for web + mobile My Quests).
                char_doc = await db.characters.find_one(
                    {"id": acc['character_id']},
                    {"_id": 0, "id": 1, "name": 1, "race": 1, "character_class": 1}
                )
                if isinstance(quest_doc.get('created_at'), str):
                    quest_doc['created_at'] = datetime.fromisoformat(quest_doc['created_at'])
                if isinstance(acc.get('accepted_at'), str):
                    acc['accepted_at'] = datetime.fromisoformat(acc['accepted_at'])
                if acc.get('completed_at') and isinstance(acc['completed_at'], str):
                    acc['completed_at'] = datetime.fromisoformat(acc['completed_at'])
            
                result.append({
                    "quest": quest_doc,
                    "acceptance": acc,
                    "character": char_doc
                })
    
        return result

    # ==================== QUEST ACTION & AI ROUTES ====================

    @api_router.post("/quests/{quest_id}/actions")
    async def submit_quest_action(
        quest_id: str,
        action_data: QuestActionCreate,
        current_user: User = Depends(get_current_user)
    ):
        """Submit a roleplay action for a quest - AI responds following T1 rules"""
        # Verify quest exists
        quest_doc = await db.quests.find_one({"id": quest_id})
        if not quest_doc:
            raise HTTPException(status_code=404, detail="Quest not found")
    
        # Verify user has accepted quest
        acceptance = await db.quest_acceptances.find_one({
            "quest_id": quest_id,
            "user_id": current_user.id,
            "status": "accepted"
        })
    
        if not acceptance:
            raise HTTPException(status_code=403, detail="You must accept the quest first")
    
        # Get character info
        char_doc = await db.characters.find_one({"id": acceptance['character_id']})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found")
    
        # Get action history
        action_history = await db.quest_actions.find(
            {"quest_id": quest_id},
            {"_id": 0}
        ).sort("turn_number", 1).to_list(100)
    
        turn_number = len(action_history)
    
        # Prepare character bio for AI context (no stats/levels)
        character_bio = {
            'name': char_doc.get('name', ''),
            'race': char_doc.get('race', ''),
            'class': char_doc.get('character_class', ''),
            'backstory': char_doc.get('backstory', ''),
            'powers': char_doc.get('powers', ''),
            'appearance': char_doc.get('appearance', '')
        }
    
        # Prepare action history for AI (convert to simple format)
        formatted_history = []
        for hist_action in action_history[-10:]:  # Last 10 actions
            formatted_history.append({
                'player_text': hist_action.get('action_text', ''),
                'npc_response': hist_action.get('ai_response', '')
            })
    
        # Build scene data
        scene_data = {
            'id': quest_id,
            'title': quest_doc.get('title', ''),
            'description': quest_doc.get('description', ''),
            'nation': quest_doc.get('nation', ''),
            'location': f"{quest_doc.get('nation', '')} region",
            'setting': quest_doc.get('difficulty', 'medium')
        }
    
        # Get AI response using new T1 system (bio-based, not level-based)
        try:
            ai_response = await quest_master.respond_to_player_action(
                scene_data,
                formatted_history,
                action_data.action_text,
                character_bio
            )
        except Exception as e:
            logger.error(f"AI Quest Master error: {e}")
            ai_response = "[The Quest Master is contemplating your action...]"
    
        # Save action (no more dice rolls)
        quest_action = QuestAction(
            quest_id=quest_id,
            user_id=current_user.id,
            character_id=char_doc['id'],
            character_name=char_doc['name'],
            character_race=char_doc['race'],
            character_class=char_doc['character_class'],
            action_text=action_data.action_text,
            ai_response=ai_response,
            is_valid_t1=True,  # Always valid with new T1 system
            t1_feedback='',
            turn_number=turn_number,
            dice_roll=None,  # No more dice
            modifier=None,
            total_roll=None,
            was_critical=False,
            was_fumble=False
        )
    
        action_doc = quest_action.model_dump()
        action_doc['created_at'] = action_doc['created_at'].isoformat()
        await db.quest_actions.insert_one(action_doc)
    
        return {
            "action_id": quest_action.id,
            "ai_response": ai_response,
            "turn_number": turn_number
        }

    @api_router.get("/quests/{quest_id}/actions")
    async def get_quest_actions(quest_id: str):
        """Get all actions/roleplay history for a quest"""
        actions = await db.quest_actions.find(
            {"quest_id": quest_id},
            {"_id": 0}
        ).sort("turn_number", 1).to_list(1000)
    
        for action in actions:
            if isinstance(action.get('created_at'), str):
                action['created_at'] = datetime.fromisoformat(action['created_at'])
    
        return actions

    @api_router.get("/quests/{quest_id}/participants")
    async def get_quest_participants(quest_id: str):
        """Get all participants in a quest (for quest creator to review)"""
        acceptances = await db.quest_acceptances.find(
            {"quest_id": quest_id},
            {"_id": 0}
        ).to_list(100)
    
        if not acceptances:
            return []
    
        # Batch fetch all users and characters to avoid N+1 queries
        user_ids = [acc['user_id'] for acc in acceptances]
        char_ids = [acc['character_id'] for acc in acceptances]
    
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(100)
        characters = await db.characters.find({"id": {"$in": char_ids}}, {"_id": 0}).to_list(100)
    
        # Create lookup maps
        user_map = {u['id']: u for u in users}
        char_map = {c['id']: c for c in characters}
    
        participants = []
        for acc in acceptances:
            user_doc = user_map.get(acc['user_id'])
            char_doc = char_map.get(acc['character_id'])
        
            if user_doc and char_doc:
                participants.append({
                    "user": {
                        "id": user_doc['id'],
                        "username": user_doc['username']
                    },
                    "character": {
                        "id": char_doc['id'],
                        "name": char_doc['name'],
                        "race": char_doc['race'],
                        "class": char_doc['character_class']
                    },
                    "acceptance": acc
                })
    
        return participants

    # ==================== T1 TUTORIAL & JUDGING ROUTES ====================

    class T1JudgeRequest(BaseModel):
        action_text: str
        context: str = "General roleplay scene"

    @api_router.post("/t1/judge-action")
    async def judge_t1_action(request: T1JudgeRequest, current_user: User = Depends(get_current_user)):
        """
        Analyze a player's action for T1 rule compliance.
        Returns feedback on auto-hitting, puppeteering, metagaming, etc.
        """
        try:
            result = await quest_master.judge_t1_action(request.action_text, request.context)
            return result
        except Exception as e:
            logger.error(f"Failed to judge T1 action: {e}")
            return {
                "is_valid": True,
                "violations": [],
                "severity": "none",
                "feedback": "Unable to analyze action at this time. Please try again.",
                "suggested_rewrite": None
            }


