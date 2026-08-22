"""
Law / Crime / Trial / Imprisonment / Escape / Bounty Board routes.

Extracted from `server.py` (was lines 3598-3892). Registered via
`attach_law_routes(api_router, ...)` which uses the shared deps passed in
from `server.py` (no module-level imports of `server` to avoid circular
imports).
"""
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Body

from law_service import LawService, law_system_enabled
from npc_memory_service import NPCMemoryService
from world_state_service import WorldStateService
from quest_master_ai import QuestMasterAI
from jail_service import ensure_jail_for_city, resolve_city_for_location


def attach_law_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
    resolve_character_for_user,
    logger,
):
    """Register all law/bounty endpoints onto `api_router`.

    Shared deps (`db`, `User`, auth deps, helpers, logger) are passed in by
    `server.py` so this module remains side-effect-free at import time.
    """

    @api_router.get("/characters/{character_id}/rap-sheet")
    async def get_character_rap_sheet(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Player-facing rap sheet: open crimes, bounties per nation, active imprisonment."""
        await resolve_character_for_user(character_id, current_user)
        law = LawService(db)
        crimes = await law.list_crimes_for_character(character_id, limit=100)
        bounties = await law.list_bounties_for_character(character_id)
        imprisonment = await law.get_active_imprisonment(character_id)
        return {
            "crimes": crimes,
            "bounties": bounties,
            "imprisonment": imprisonment,
            "law_system_enabled": law_system_enabled(),
        }

    @api_router.get("/bounty-board")
    async def get_bounty_board(
        nation: Optional[str] = None,
        limit: int = 100,
    ):
        """Public bounty board — all huntable bounties (NPCs always; characters with
        major+ open crimes). Anyone may view; no auth required.
        """
        if not law_system_enabled():
            return []
        law = LawService(db)
        return await law.get_bounty_board(nation=nation, limit=limit)

    @api_router.post("/characters/{character_id}/surrender")
    async def character_surrender(
        character_id: str,
        payload: Dict = Body(default={}),
        current_user: User = Depends(get_current_user),
    ):
        """Surrender the character to the local authorities of `nation` at `location`.

        Starts a COURTROOM TRIAL scene (the player is moved to the city's
        courthouse and may defend themselves up to 5 turns before the judge
        delivers a final verdict). The actual imprisonment / fine / exile /
        execution only happens after the verdict — not at surrender time.
        """
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        char = await resolve_character_for_user(character_id, current_user)
        nation = (payload or {}).get("nation") or char.get("nation")
        location = (payload or {}).get("location") or ""
        if not nation:
            raise HTTPException(status_code=400, detail="nation is required")
        if not location:
            raise HTTPException(status_code=400, detail="location is required")

        law = LawService(db)
        if await law.get_active_imprisonment(character_id):
            raise HTTPException(status_code=400, detail="Character is already imprisoned.")

        from courtroom_service import CourtroomService
        crt = CourtroomService(db)
        if await crt.get_active_trial(character_id):
            raise HTTPException(status_code=400, detail="Character is already on trial.")

        open_crimes = await law.list_open_crimes_in_nation(character_id, nation, limit=10)
        if not open_crimes:
            return {
                "trial": None,
                "dismissed": True,
                "verdict_summary": "No actionable charges — defendant waved away.",
            }

        from routes.courtroom import create_trial_from_open_crimes
        result = await create_trial_from_open_crimes(
            db=db,
            law_service=law,
            character_id=character_id,
            character_name=char["name"],
            user_id=current_user.id,
            nation=nation,
            origin_location=location,
            logger=logger,
        )
        if not result:
            return {
                "trial": None,
                "dismissed": True,
                "verdict_summary": "No actionable charges — defendant waved away.",
            }
        return result

    @api_router.post("/characters/{character_id}/attempt-escape")
    async def character_attempt_escape(
        character_id: str,
        payload: Dict = Body(...),
        current_user: User = Depends(get_current_user),
    ):
        """Attempt to escape an active imprisonment via roleplay description.

        Body: `{ "description": "I distract the guard with a coin..." }`.
        The AI judges based on creativity and circumstances. On success the
        imprisonment ends as 'escaped' and a new escapee crime is logged so the
        bounty resurfaces. On failure the sentence is extended by 2 turns.
        """
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        char = await resolve_character_for_user(character_id, current_user)
        law = LawService(db)
        imprisonment = await law.get_active_imprisonment(character_id)
        if not imprisonment:
            raise HTTPException(status_code=400, detail="No active imprisonment to escape from.")

        description = (payload or {}).get("description") or ""
        if not description.strip():
            raise HTTPException(status_code=400, detail="Describe your escape attempt.")

        npc_service = NPCMemoryService(db)
        companions = await npc_service.list_companions(character_id)

        ai = QuestMasterAI()
        judgement = await ai.judge_escape_attempt(
            character_name=char['name'],
            jail_location=imprisonment.get('jail_location', ''),
            turns_served=imprisonment.get('turns_served', 0),
            sentence_turns=imprisonment.get('sentence_turns', 0),
            description=description,
            companions_present=companions,
        )

        if judgement.get("success"):
            await law.end_imprisonment(imprisonment["id"], "escaped", reason=description[:120])
            await law.record_crime(
                character_id=character_id,
                character_name=char['name'],
                user_id=current_user.id,
                nation=imprisonment.get("nation", ""),
                location=imprisonment.get("jail_location", ""),
                crime_type="escape_from_custody",
                severity="major",
                victim_name="The Crown",
                victim_importance="ruler",
                description=judgement.get("consequence_summary", "")[:200],
            )
        else:
            new_sentence = int(imprisonment.get("sentence_turns", 0)) + 2
            await db.imprisonments.update_one(
                {"id": imprisonment["id"]},
                {"$set": {"sentence_turns": new_sentence}},
            )

        return {"judgement": judgement, "imprisonment": await law.get_active_imprisonment(character_id)}

    # ---------- Admin law endpoints ----------

    @api_router.get("/admin/crimes")
    async def admin_list_crimes(
        nation: Optional[str] = None,
        status: Optional[str] = None,
        admin: User = Depends(require_admin),
    ):
        law = LawService(db)
        q: Dict = {}
        if nation:
            q["nation"] = nation
        if status:
            q["status"] = status
        cursor = law.crimes.find(q, {"_id": 0}).sort("created_at", -1)
        return await cursor.to_list(500)

    @api_router.post("/admin/crimes/{crime_id}/pardon")
    async def admin_pardon_crime(
        crime_id: str,
        payload: Dict = Body(default={}),
        admin: User = Depends(require_admin),
    ):
        law = LawService(db)
        result = await law.mark_crime_resolved(
            crime_id, "pardoned", reason=(payload or {}).get("reason", "Admin pardon")
        )
        if not result:
            raise HTTPException(status_code=404, detail="Crime not found")
        return result

    @api_router.delete("/admin/crimes/{crime_id}")
    async def admin_expunge_crime(
        crime_id: str,
        admin: User = Depends(require_admin),
    ):
        law = LawService(db)
        result = await law.mark_crime_resolved(crime_id, "expunged", reason="Admin expunge")
        if not result:
            raise HTTPException(status_code=404, detail="Crime not found")
        return {"ok": True}

    @api_router.get("/admin/imprisonments")
    async def admin_list_imprisonments(admin: User = Depends(require_admin)):
        law = LawService(db)
        return await law.list_active_imprisonments()

    @api_router.post("/admin/imprisonments/{imprisonment_id}/release")
    async def admin_release_imprisonment(
        imprisonment_id: str,
        payload: Dict = Body(default={}),
        admin: User = Depends(require_admin),
    ):
        law = LawService(db)
        result = await law.end_imprisonment(
            imprisonment_id,
            new_status=(payload or {}).get("status", "pardoned"),
            reason=(payload or {}).get("reason", "Admin release"),
        )
        if not result:
            raise HTTPException(status_code=404, detail="Imprisonment not found")
        return result

    @api_router.post("/admin/characters/{character_id}/revive")
    async def admin_revive_character(
        character_id: str,
        payload: Dict = Body(default={}),
        admin: User = Depends(require_admin),
    ):
        """Restore a character that was marked deceased (status='executed' or
        is_active=False). Use sparingly — intended for AI verdict reversals,
        wrongful executions, or testing. Optional body `{ "reason": "..." }`."""
        char = await db.characters.find_one({"id": character_id}, {"_id": 0})
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"is_active": True, "status": "alive"}},
        )
        return {
            "ok": True,
            "character_id": character_id,
            "reason": (payload or {}).get("reason", "Admin revive"),
        }
