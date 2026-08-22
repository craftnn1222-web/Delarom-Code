"""Courtroom / Trial routes.

REST endpoints for the multi-turn courtroom RP scene introduced as the
follow-up to the Law / Guard / Jail overhaul.

Wiring:
- Trial creation lives in `routes/law.py::character_surrender` and in
  `server.py::_auto_arrest_and_imprison` (auto-arrest hook) — both go through
  the shared helper `create_trial_from_open_crimes` below.
- This module exposes the player-facing endpoints to advance the trial.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from law_service import LawService, law_system_enabled
from npc_memory_service import NPCMemoryService
from world_state_service import WorldStateService
from quest_master_ai import QuestMasterAI
from courtroom_service import (
    CourtroomService,
    ensure_courthouse_for_city,
    ensure_judge_and_prosecutor,
    gather_victim_witnesses,
    _baseline_sentence_for_crimes,
    MAX_DEFENCE_TURNS,
)
from jail_service import ensure_jail_for_city, resolve_city_for_location


async def create_trial_from_open_crimes(
    *,
    db,
    law_service: LawService,
    character_id: str,
    character_name: str,
    user_id: str,
    nation: str,
    origin_location: str,
    logger,
) -> Optional[Dict]:
    """Shared helper used by both manual surrender and auto-arrest flows.

    Returns the trial doc + opening narration, or None if there are no open
    crimes to try (in which case the caller should treat it as a dismissal).
    """
    open_crimes = await law_service.list_open_crimes_in_nation(character_id, nation, limit=10)
    if not open_crimes:
        return None
    bounty = await law_service.get_bounty(character_id, nation)
    total_bounty = (bounty or {}).get("total_bounty", 0)

    city = await resolve_city_for_location(db, nation=nation, location_slug=origin_location)
    courthouse = await ensure_courthouse_for_city(
        db, nation=nation, city=city, fallback_location_slug=origin_location,
    )
    courthouse_slug = courthouse.get("slug")

    court_npcs = await ensure_judge_and_prosecutor(
        db, nation=nation, courthouse_slug=courthouse_slug, city=city,
    )
    judge = court_npcs["judge"]
    prosecutor = court_npcs["prosecutor"]

    witnesses = await gather_victim_witnesses(db, open_crimes=open_crimes)
    victim_npc_ids = [w["npc_id"] for w in witnesses if w.get("npc_id")]

    crt = CourtroomService(db)
    trial = await crt.start_trial(
        character_id=character_id,
        character_name=character_name,
        user_id=user_id,
        nation=nation,
        origin_location=origin_location,
        courthouse_location=courthouse_slug,
        city=city,
        crime_ids=[c["id"] for c in open_crimes],
        open_crimes_snapshot=open_crimes,
        judge_npc_id=judge["id"],
        prosecutor_npc_id=prosecutor["id"],
        victim_npc_ids=victim_npc_ids,
        total_bounty=total_bounty,
    )

    # Build a quick opening narration so the courtroom isn't a cold dock.
    opening = (
        f"The doors of the {courthouse.get('name','courthouse')} groan open. "
        f"{judge['name']} settles behind the high bench. "
        f"{prosecutor['name']} arranges the prosecution's papers with theatrical care."
    )
    if witnesses:
        names = ", ".join(w["name"] for w in witnesses[:4])
        opening += f" The bench for witnesses fills — {names} are summoned to bear testimony."
    opening += (
        f" {character_name} stands in the dock. The reading of charges begins; "
        f"{total_bounty}g of accusations weigh on the air. "
        "The Magistrate looks up and asks for the defence."
    )
    await crt.set_opening_narration(trial["id"], opening)
    trial["opening_narration"] = opening

    # Publish to Chronicle so the world knows a trial has begun.
    try:
        world = WorldStateService(db)
        await world.record_world_event({
            "event_type": "trial",
            "scope": "regional",
            "summary": (
                f"{character_name} stands trial in the {courthouse.get('name','courthouse')} "
                f"({nation.title()}) for {len(open_crimes)} open charge(s)."
            ),
            "details": opening[:800],
            "nations": [nation],
            "involved_characters": [character_id],
        })
    except Exception as ev_err:
        logger.error(f"Trial chronicle publish failed: {ev_err}")

    return {
        "trial": trial,
        "courthouse_location": courthouse_slug,
        "courthouse_nation": nation,
        "judge_name": judge["name"],
        "prosecutor_name": prosecutor["name"],
        "witnesses": witnesses,
    }


async def _resolve_witness_summaries(
    db, trial: Dict,
) -> List[Dict]:
    """Re-resolve the witness records (names + personality + crime link) for
    a defence turn from the trial's snapshot, so the AI prompt always has
    fresh personality / mood data."""
    return await gather_victim_witnesses(db, open_crimes=trial.get("open_crimes_snapshot", []))


async def _execute_verdict(
    *,
    db,
    law_service: LawService,
    trial: Dict,
    verdict: Dict,
    logger,
) -> Optional[Dict]:
    """Persist the verdict outcome:
    - Resolve crimes (paid / served / pardoned / served-executed).
    - Create imprisonment row + route to jail if sentence_type == imprison.
    - Mark character executed if sentence_type == execute.
    Returns the imprisonment doc if one was created."""
    character_id = trial["character_id"]
    nation = trial["nation"]
    crime_ids = list(trial.get("crime_ids", []) or [])

    sentence_type = verdict.get("sentence_type", "imprison")
    imprisonment_doc = None

    if sentence_type == "imprison":
        city = trial.get("city")
        try:
            jail_doc = await ensure_jail_for_city(
                db, nation=nation, city=city,
                fallback_location_slug=trial.get("origin_location"),
            )
            jail_slug = jail_doc.get("slug") or trial.get("origin_location") or ""
        except Exception as jail_err:
            logger.error(f"Verdict jail resolution failed: {jail_err}")
            jail_slug = verdict.get("jail_location") or trial.get("origin_location") or ""
        imprisonment_doc = await law_service.imprison(
            character_id=character_id,
            character_name=trial["character_name"],
            nation=nation,
            jail_location=jail_slug,
            sentence_turns=verdict.get("imprison_turns", 5),
            crime_ids=crime_ids,
            narration=verdict.get("narration", ""),
        )
        verdict["jail_location"] = jail_slug
    elif sentence_type == "fine":
        for cid in crime_ids:
            await law_service.mark_crime_resolved(
                cid, "paid",
                reason=f"Fine paid ({verdict.get('fine_amount',0)}g) after defence",
            )
    elif sentence_type == "exile":
        for cid in crime_ids:
            await law_service.mark_crime_resolved(cid, "served", reason="Exiled by tribunal")
    elif sentence_type == "execute":
        for cid in crime_ids:
            await law_service.mark_crime_resolved(cid, "served", reason="Executed by tribunal")
        from datetime import datetime, timezone
        eulogy = ""
        try:
            from routes.memorial import _generate_eulogy
            char_doc = await db.characters.find_one({"id": character_id}, {"_id": 0})
            cause_line = f"Executed for {verdict.get('verdict_summary','their crimes')}"
            eulogy = await _generate_eulogy(char_doc or {}, cause_line)
        except Exception as eul_err:
            logger.error(f"Verdict eulogy generation failed: {eul_err}")
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {
                "is_active": False,
                "status": "executed",
                "died_at": datetime.now(timezone.utc).isoformat(),
                "cause_of_death": f"Executed for {verdict.get('verdict_summary','their crimes')}",
                "eulogy": eulogy,
            }},
        )
    elif sentence_type == "dismissed":
        for cid in crime_ids:
            await law_service.mark_crime_resolved(cid, "pardoned", reason="Dismissed at trial")

    # Publish verdict to Chronicle.
    try:
        world = WorldStateService(db)
        await world.record_world_event({
            "event_type": "trial",
            "scope": "regional",
            "summary": (
                f"Verdict in {trial.get('courthouse_location','court')} for "
                f"{trial['character_name']}: {verdict.get('verdict_summary','sentence delivered')}."
            ),
            "details": (verdict.get("narration") or "")[:800],
            "nations": [nation],
            "involved_characters": [character_id],
        })
    except Exception as ev_err:
        logger.error(f"Verdict chronicle publish failed: {ev_err}")

    return imprisonment_doc


async def _maybe_finalize(
    *,
    db,
    law_service: LawService,
    courtroom: CourtroomService,
    trial: Dict,
    ai: QuestMasterAI,
    forced: bool,
    logger,
) -> Optional[Dict]:
    """If the trial should end (defendant rested case OR turns exhausted OR
    judge cut off), compute & apply the verdict. Returns the final verdict +
    imprisonment payload, or None if the trial should continue."""
    if not forced:
        # Auto-finalize when turns are spent or the judge cut off.
        turns_used = int(trial.get("defense_turns_used", 0))
        last_cut = (trial.get("defense_history") or [{}])[-1].get("judge_cut_off")
        if turns_used < int(trial.get("max_defense_turns", MAX_DEFENCE_TURNS)) and not last_cut:
            return None

    open_crimes = trial.get("open_crimes_snapshot", [])
    baseline = _baseline_sentence_for_crimes(open_crimes)
    # Resolve judge name
    judge_npc = await db.npcs.find_one({"id": trial.get("judge_npc_id")}, {"_id": 0, "name": 1})
    judge_name = (judge_npc or {}).get("name") or "The Magistrate"

    verdict = await ai.narrate_verdict_with_defence(
        character_name=trial["character_name"],
        nation=trial["nation"],
        courthouse_location=trial.get("courthouse_location", ""),
        judge_name=judge_name,
        open_crimes=open_crimes,
        total_bounty=int(trial.get("total_bounty", 0)),
        defense_history=trial.get("defense_history", []),
        final_leniency=int(trial.get("leniency_score", 0)),
        baseline_sentence=baseline,
    )
    imprisonment_doc = await _execute_verdict(
        db=db, law_service=law_service, trial=trial, verdict=verdict, logger=logger,
    )
    final_trial = await courtroom.finalize_trial(trial["id"], verdict=verdict)
    return {
        "trial": final_trial,
        "verdict": verdict,
        "imprisonment": imprisonment_doc,
    }


def attach_courtroom_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
    logger,
):
    """Register the player-facing trial endpoints on `api_router`."""

    @api_router.get("/characters/{character_id}/trial")
    async def get_active_trial(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        await resolve_character_for_user(character_id, current_user)
        crt = CourtroomService(db)
        trial = await crt.get_active_trial(character_id)
        if not trial:
            return {"trial": None}
        # Re-resolve judge + prosecutor + witness display data for the UI.
        judge_npc = await db.npcs.find_one(
            {"id": trial.get("judge_npc_id")}, {"_id": 0, "name": 1, "role": 1, "appearance": 1},
        )
        prosecutor_npc = await db.npcs.find_one(
            {"id": trial.get("prosecutor_npc_id")}, {"_id": 0, "name": 1, "role": 1, "appearance": 1},
        )
        witnesses = await _resolve_witness_summaries(db, trial)
        return {
            "trial": trial,
            "judge": judge_npc,
            "prosecutor": prosecutor_npc,
            "witnesses": witnesses,
        }

    @api_router.post("/characters/{character_id}/trial/defend")
    async def trial_defend(
        character_id: str,
        payload: Dict = Body(...),
        current_user: User = Depends(get_current_user),
    ):
        """Submit one defence turn.

        Body: `{ "defence_text": "..." }`.
        """
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        char = await resolve_character_for_user(character_id, current_user)
        crt = CourtroomService(db)
        trial = await crt.get_active_trial(character_id)
        if not trial:
            raise HTTPException(status_code=400, detail="No active trial.")

        defence_text = ((payload or {}).get("defence_text") or "").strip()
        if not defence_text:
            raise HTTPException(status_code=400, detail="Describe your defence.")

        turns_used = int(trial.get("defense_turns_used", 0))
        max_turns = int(trial.get("max_defense_turns", MAX_DEFENCE_TURNS))
        if turns_used >= max_turns:
            raise HTTPException(status_code=400, detail="No defence turns remain.")

        # Build witness + court context for the AI.
        witnesses = await _resolve_witness_summaries(db, trial)
        judge_npc = await db.npcs.find_one(
            {"id": trial.get("judge_npc_id")}, {"_id": 0, "name": 1},
        )
        prosecutor_npc = await db.npcs.find_one(
            {"id": trial.get("prosecutor_npc_id")}, {"_id": 0, "name": 1},
        )
        ai = QuestMasterAI()
        try:
            turn_result = await ai.narrate_courtroom_turn(
                character_name=char["name"],
                nation=trial["nation"],
                courthouse_location=trial["courthouse_location"],
                judge_name=(judge_npc or {}).get("name", "The Magistrate"),
                prosecutor_name=(prosecutor_npc or {}).get("name", "The Crown Advocate"),
                witnesses=witnesses,
                open_crimes=trial.get("open_crimes_snapshot", []),
                total_bounty=int(trial.get("total_bounty", 0)),
                defence_text=defence_text,
                turn_no=turns_used + 1,
                max_turns=max_turns,
                current_leniency=int(trial.get("leniency_score", 0)),
                recent_history=trial.get("defense_history", []),
            )
        except Exception as e:
            logger.error(f"Courtroom AI call failed: {e}")
            raise HTTPException(status_code=502, detail=f"AI service unavailable: {e}") from e

        trial = await crt.append_defence_turn(
            trial["id"],
            defence_text=defence_text,
            ai_narration=turn_result.get("narration", ""),
            leniency_delta=int(turn_result.get("leniency_delta", 0)),
            judge_remark=turn_result.get("judge_remark", ""),
            judge_cut_off=bool(turn_result.get("judge_cut_off", False)),
        )

        # If turns are spent OR the judge cut off, finalize immediately.
        law_service = LawService(db)
        finalize_result = await _maybe_finalize(
            db=db, law_service=law_service, courtroom=crt, trial=trial, ai=ai,
            forced=False, logger=logger,
        )
        if finalize_result:
            return {
                "turn_result": turn_result,
                "trial": finalize_result["trial"],
                "verdict": finalize_result["verdict"],
                "imprisonment": finalize_result["imprisonment"],
                "finalized": True,
            }
        return {
            "turn_result": turn_result,
            "trial": trial,
            "finalized": False,
        }

    @api_router.post("/characters/{character_id}/trial/rest-case")
    async def trial_rest_case(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Player rests their case — finalize verdict using whatever defence
        was offered so far (may be zero turns)."""
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        await resolve_character_for_user(character_id, current_user)
        crt = CourtroomService(db)
        trial = await crt.get_active_trial(character_id)
        if not trial:
            raise HTTPException(status_code=400, detail="No active trial.")
        ai = QuestMasterAI()
        law_service = LawService(db)
        finalize_result = await _maybe_finalize(
            db=db, law_service=law_service, courtroom=crt, trial=trial, ai=ai,
            forced=True, logger=logger,
        )
        if not finalize_result:
            raise HTTPException(status_code=500, detail="Failed to finalize trial.")
        return {
            "trial": finalize_result["trial"],
            "verdict": finalize_result["verdict"],
            "imprisonment": finalize_result["imprisonment"],
            "finalized": True,
        }

    @api_router.post("/characters/{character_id}/trial/abandon")
    async def trial_abandon(
        character_id: str,
        payload: Dict = Body(default={}),
        current_user: User = Depends(get_current_user),
    ):
        """Walk away from the trial — locks the player into the baseline
        sentence with no defence credit. Used sparingly (e.g. a player who
        wants to take the verdict on the chin without arguing)."""
        if not law_system_enabled():
            raise HTTPException(status_code=503, detail="The law system is currently disabled.")
        await resolve_character_for_user(character_id, current_user)
        crt = CourtroomService(db)
        trial = await crt.get_active_trial(character_id)
        if not trial:
            raise HTTPException(status_code=400, detail="No active trial.")
        ai = QuestMasterAI()
        law_service = LawService(db)
        result = await _maybe_finalize(
            db=db, law_service=law_service, courtroom=crt, trial=trial, ai=ai,
            forced=True, logger=logger,
        )
        return {
            "trial": result["trial"],
            "verdict": result["verdict"],
            "imprisonment": result["imprisonment"],
            "abandoned": True,
        }
