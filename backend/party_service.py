"""Party Quests — multi-player shared RP sessions.

A `party` is a small (2-6) RP session with a host and a rotating turn
order. On each turn the active player submits an action; an AI Master of
Ceremonies (MoC) narrates the world's response in the second person to
that player only. The response, along with the player's action, becomes
the next entry in a shared scene log visible to every party member.

Design notes:
    • Everyone in the party is a real player character (owned by a real
      user). No NPC "party fills" — this is human-with-human RP.
    • Turns strictly rotate through `turn_order` (the order players
      joined). If a player drops mid-session, their slot is removed from
      the rotation cleanly.
    • The MoC never puppeteers PCs. It sets scene, narrates NPCs and
      environment, and cues the next actor.
    • The MoC is aware of active Elder-Gods festivals (see
      `elder_gods_festivals`) and injects atmospheric flavour when
      applicable.

Collections:
    • `parties`         — one doc per party.
    • `party_actions`   — append-only scene log; one doc per turn.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# ── constants ─────────────────────────────────────────────────────────
DEFAULT_MAX_MEMBERS = 6
MIN_MAX_MEMBERS = 2
MAX_MAX_MEMBERS = 8

STATUS_RECRUITING = "recruiting"
STATUS_ACTIVE = "active"
STATUS_FINISHED = "finished"
VALID_STATUSES = {STATUS_RECRUITING, STATUS_ACTIVE, STATUS_FINISHED}

ROLE_HOST = "host"
ROLE_PLAYER = "player"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _party_public(party: Dict) -> Dict:
    """Strip Mongo _id and normalise timestamps for API responses."""
    if not party:
        return party
    p = {k: v for k, v in party.items() if k != "_id"}
    return p


def _load_active_festival() -> Optional[Dict]:
    """Optional import — festival calendar is a soft dependency."""
    try:
        from elder_gods_festivals import get_active_festival
        return get_active_festival()
    except Exception as e:  # pragma: no cover — defensive
        logger.warning(f"party_service festival lookup failed: {e}")
        return None


class PartyService:
    """All party lifecycle + MoC turn narration."""

    def __init__(self, db):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    # ── lifecycle ────────────────────────────────────────────────────

    async def create_party(
        self,
        *,
        host_user: Dict,
        host_character: Dict,
        name: str,
        scene_description: str,
        location: str,
        max_members: int = DEFAULT_MAX_MEMBERS,
    ) -> Dict:
        max_members = max(MIN_MAX_MEMBERS, min(MAX_MAX_MEMBERS, int(max_members)))
        party_id = str(uuid.uuid4())
        host_member = {
            "user_id": host_user["id"],
            "username": host_user.get("username", ""),
            "character_id": host_character["id"],
            "character_name": host_character.get("name", ""),
            "character_race": host_character.get("race", ""),
            "character_class": host_character.get("character_class", ""),
            "role": ROLE_HOST,
            "joined_at": _now_iso(),
        }
        party = {
            "id": party_id,
            "name": name.strip()[:120],
            "scene_description": scene_description.strip()[:1500],
            "location": location.strip()[:160],
            "host_user_id": host_user["id"],
            "host_character_id": host_character["id"],
            "max_members": max_members,
            "members": [host_member],
            "turn_order": [host_character["id"]],
            "current_turn_index": 0,
            "status": STATUS_RECRUITING,
            "created_at": _now_iso(),
            "started_at": None,
            "finished_at": None,
        }
        await self.db.parties.insert_one(party)
        return _party_public(party)

    async def list_parties(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        query: Dict = {}
        if status:
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'")
            query["status"] = status
        else:
            # Default: hide finished
            query["status"] = {"$in": [STATUS_RECRUITING, STATUS_ACTIVE]}
        rows = await self.db.parties.find(query, {"_id": 0}) \
            .sort("created_at", -1) \
            .limit(max(1, min(200, limit))) \
            .to_list(length=limit)
        return rows

    async def get_party(self, party_id: str) -> Optional[Dict]:
        p = await self.db.parties.find_one({"id": party_id}, {"_id": 0})
        return p

    async def join_party(
        self,
        *,
        party_id: str,
        user: Dict,
        character: Dict,
    ) -> Dict:
        party = await self.get_party(party_id)
        if not party:
            raise ValueError("Party not found.")
        if party["status"] != STATUS_RECRUITING:
            raise ValueError("This party is no longer recruiting.")
        # Duplicate check first — more informative than "full"
        if any(m["user_id"] == user["id"] for m in party["members"]):
            raise ValueError("You are already in this party.")
        if len(party["members"]) >= party["max_members"]:
            raise ValueError("This party is full.")
        member = {
            "user_id": user["id"],
            "username": user.get("username", ""),
            "character_id": character["id"],
            "character_name": character.get("name", ""),
            "character_race": character.get("race", ""),
            "character_class": character.get("character_class", ""),
            "role": ROLE_PLAYER,
            "joined_at": _now_iso(),
        }
        await self.db.parties.update_one(
            {"id": party_id},
            {
                "$push": {
                    "members": member,
                    "turn_order": character["id"],
                },
            },
        )
        return await self.get_party(party_id)

    async def leave_party(
        self,
        *,
        party_id: str,
        user_id: str,
    ) -> Dict:
        party = await self.get_party(party_id)
        if not party:
            raise ValueError("Party not found.")
        if party["status"] == STATUS_FINISHED:
            raise ValueError("This party has already ended.")
        # Host can't leave; must dissolve (finish) instead
        if user_id == party["host_user_id"]:
            raise ValueError("The host cannot leave. Dissolve the party instead.")
        member = next((m for m in party["members"] if m["user_id"] == user_id), None)
        if not member:
            raise ValueError("You are not a member of this party.")
        cid = member["character_id"]
        new_order = [c for c in party["turn_order"] if c != cid]
        new_members = [m for m in party["members"] if m["user_id"] != user_id]
        # Recompute turn index cleanly. If the leaver was up, roll to next
        # remaining player; otherwise, keep pointing at the same character.
        was_up = (party["turn_order"][party["current_turn_index"]] == cid) if party["turn_order"] else False
        if not new_order:
            new_index = 0
        elif was_up:
            new_index = party["current_turn_index"] % len(new_order)
        else:
            up_cid = party["turn_order"][party["current_turn_index"]]
            if up_cid in new_order:
                new_index = new_order.index(up_cid)
            else:
                new_index = 0
        await self.db.parties.update_one(
            {"id": party_id},
            {
                "$set": {
                    "members": new_members,
                    "turn_order": new_order,
                    "current_turn_index": new_index,
                },
            },
        )
        return await self.get_party(party_id)

    async def start_party(
        self,
        *,
        party_id: str,
        user_id: str,
    ) -> Dict:
        party = await self.get_party(party_id)
        if not party:
            raise ValueError("Party not found.")
        if party["host_user_id"] != user_id:
            raise ValueError("Only the host can start the party.")
        if party["status"] != STATUS_RECRUITING:
            raise ValueError("This party has already started or ended.")
        if len(party["members"]) < 1:
            raise ValueError("A party needs at least one member.")

        # Opening narration from the MoC
        opening = await self._compose_opening_narration(party)

        await self.db.parties.update_one(
            {"id": party_id},
            {"$set": {
                "status": STATUS_ACTIVE,
                "started_at": _now_iso(),
            }},
        )
        # Persist opening as turn 0 (system entry)
        await self.db.party_actions.insert_one({
            "id": str(uuid.uuid4()),
            "party_id": party_id,
            "turn_number": 0,
            "actor_user_id": "SYSTEM",
            "actor_character_id": "MOC",
            "actor_character_name": "Master of Ceremonies",
            "action_text": "[Scene opens]",
            "ai_response": opening,
            "created_at": _now_iso(),
        })
        return await self.get_party(party_id)

    async def finish_party(
        self,
        *,
        party_id: str,
        user_id: str,
    ) -> Dict:
        party = await self.get_party(party_id)
        if not party:
            raise ValueError("Party not found.")
        if party["host_user_id"] != user_id:
            raise ValueError("Only the host can end the party.")
        if party["status"] == STATUS_FINISHED:
            return _party_public(party)
        await self.db.parties.update_one(
            {"id": party_id},
            {"$set": {"status": STATUS_FINISHED, "finished_at": _now_iso()}},
        )
        return await self.get_party(party_id)

    # ── turn actions ─────────────────────────────────────────────────

    async def submit_action(
        self,
        *,
        party_id: str,
        user_id: str,
        action_text: str,
    ) -> Dict:
        party = await self.get_party(party_id)
        if not party:
            raise ValueError("Party not found.")
        if party["status"] != STATUS_ACTIVE:
            raise ValueError("This party is not currently active.")
        if not party["turn_order"]:
            raise ValueError("No players in this party.")

        active_cid = party["turn_order"][party["current_turn_index"]]
        actor = next(
            (m for m in party["members"] if m["character_id"] == active_cid),
            None,
        )
        if not actor:
            raise ValueError("The current actor has left the party — please advance the turn.")
        if actor["user_id"] != user_id:
            raise ValueError("It is not your turn.")
        if not action_text.strip():
            raise ValueError("Action text is required.")

        # Fetch last 12 turns for context; use a light count query for turn_number
        turn_number = await self.db.party_actions.count_documents({"party_id": party_id})
        history = await self.db.party_actions.find(
            {"party_id": party_id}, {"_id": 0},
        ).sort("turn_number", -1).limit(12).to_list(length=12)
        history.reverse()

        ai_response = await self._compose_turn_response(
            party=party,
            actor=actor,
            action_text=action_text.strip(),
            history=history,
        )

        action_doc = {
            "id": str(uuid.uuid4()),
            "party_id": party_id,
            "turn_number": turn_number,
            "actor_user_id": actor["user_id"],
            "actor_character_id": actor["character_id"],
            "actor_character_name": actor["character_name"],
            "action_text": action_text.strip(),
            "ai_response": ai_response,
            "created_at": _now_iso(),
        }
        await self.db.party_actions.insert_one(action_doc)

        # Advance turn
        n = len(party["turn_order"])
        next_index = (party["current_turn_index"] + 1) % n if n else 0
        await self.db.parties.update_one(
            {"id": party_id},
            {"$set": {"current_turn_index": next_index}},
        )
        return {k: v for k, v in action_doc.items() if k != "_id"}

    async def get_actions(self, party_id: str, limit: int = 500) -> List[Dict]:
        return await self.db.party_actions.find(
            {"party_id": party_id}, {"_id": 0},
        ).sort("turn_number", 1).limit(max(1, min(1000, limit))).to_list(length=limit)

    # ── AI (MoC) narration ───────────────────────────────────────────

    def _festival_line(self) -> str:
        f = _load_active_festival()
        if not f:
            return ""
        return (
            f"\nATMOSPHERE — {f['festival_name']} is observed today: "
            f"{f['atmosphere']} Weave this atmosphere lightly into the scene "
            f"when it fits — never force it. "
        )

    def _system_prompt(self, party: Dict) -> str:
        roster_lines = "\n".join(
            f"  • {m['character_name']} ({m['character_race']} "
            f"{m['character_class']})" for m in party["members"]
        )
        return (
            "You are the Master of Ceremonies for a shared multi-player "
            "roleplay session set in the world of Delarom (Continent I).\n\n"
            "Respond in English ONLY. Never emit CJK, Cyrillic, or other "
            "non-Latin script tokens.\n\n"
            "Setting canon:\n"
            "  • The current age is 215 A.E. (After Ehena).\n"
            "  • Magic uses the ACT system: aspect · conduit · toll. Every "
            "spell has a cost.\n"
            "  • Elder Gods are Seren (Life), Yros (Earth), Uesis (Heavens), "
            "Ehena (Time). They cannot descend.\n"
            "  • Do NOT invent generic-fantasy pantheons, planes, or lore.\n\n"
            "How to narrate a turn:\n"
            "  • Address the acting player in the SECOND PERSON ('you feel', "
            "'you see').\n"
            "  • Narrate NPCs, environment, and consequence — never speak or "
            "act on behalf of ANY player character.\n"
            "  • Reference OTHER party members only via what the acting "
            "player observes.\n"
            "  • 2-5 short paragraphs; vivid but tight. End with a natural "
            "prompt (a sound, a choice, a stranger's glance) that hands the "
            "story to whoever is up next.\n"
            "  • Never state game mechanics, dice, HP, XP, or the word "
            "'turn'. This is prose, not a table read.\n\n"
            f"Party name: {party['name']}\n"
            f"Location: {party['location']}\n"
            f"Opening scene set by host: {party['scene_description']}\n"
            f"Roster:\n{roster_lines}\n"
            f"{self._festival_line()}"
        )

    async def _compose_opening_narration(self, party: Dict) -> str:
        system_message = self._system_prompt(party)
        first_cid = party["turn_order"][0] if party["turn_order"] else None
        first_name = next(
            (m["character_name"] for m in party["members"] if m["character_id"] == first_cid),
            "the first player",
        )
        user_payload = (
            "Open the scene. Introduce the location, sights, sounds, and "
            "any onlookers or NPCs relevant to the host's opening. Do NOT "
            "introduce the player characters — they are already present.\n"
            f"End your narration by naturally handing the moment to "
            f"{first_name}."
        )
        return await self._call_llm(
            system_message,
            user_payload,
            session_key=f"party_open_{party['id']}",
        )

    async def _compose_turn_response(
        self,
        *,
        party: Dict,
        actor: Dict,
        action_text: str,
        history: List[Dict],
    ) -> str:
        system_message = self._system_prompt(party)
        # Build history block
        hist_lines = []
        for h in history:
            who = h["actor_character_name"]
            act = h.get("action_text", "")
            resp = h.get("ai_response", "")
            hist_lines.append(f"[{who}] {act}\n[MoC] {resp}")
        hist_block = "\n\n".join(hist_lines) if hist_lines else "(scene just opened)"

        # Next actor cue
        n = len(party["turn_order"])
        next_index = (party["current_turn_index"] + 1) % n if n else 0
        next_cid = party["turn_order"][next_index] if party["turn_order"] else None
        next_name = next(
            (m["character_name"] for m in party["members"] if m["character_id"] == next_cid),
            None,
        )
        next_line = f"After narrating consequences, hand the next beat to {next_name}." \
            if next_name and next_name != actor["character_name"] \
            else "After narrating consequences, leave a natural opening."

        user_payload = (
            f"SCENE SO FAR:\n{hist_block}\n\n"
            f"NOW — {actor['character_name']} "
            f"({actor['character_race']} {actor['character_class']}) acts:\n"
            f"  \"{action_text}\"\n\n"
            f"Narrate the world's response for {actor['character_name']}. "
            f"{next_line}"
        )
        return await self._call_llm(
            system_message,
            user_payload,
            session_key=f"party_turn_{party['id']}",
        )

    async def _call_llm(
        self,
        system_message: str,
        user_payload: str,
        *,
        session_key: str,
    ) -> str:
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"{session_key}_{uuid.uuid4().hex[:8]}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o")
            resp = await chat.send_message(UserMessage(text=user_payload))
            return (resp or "").strip() or self._fallback_narration()
        except Exception as e:
            logger.exception(f"party MoC call failed: {e}")
            return self._fallback_narration()

    @staticmethod
    def _fallback_narration() -> str:
        return (
            "The moment holds — the light shifts, the crowd's hum settles, "
            "and every gaze in the room turns, just briefly, toward the "
            "next thread of the scene."
        )
