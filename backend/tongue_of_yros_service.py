"""Tongue of Y'ros — legendary sword trial (Tier 1/2 feature).

Deep in Thal'Karrak (Thalgrer's Tomb, capital of Stonehearth Hold), a
consecrated stone blade — the Tongue of Y'ros — waits for the one it
will answer to. The lore is strict:

  1. ONLY a Dwarf may draw it. Any other race's attempt returns silence.
  2. Even for Dwarves, the sword judges the attempt itself — sincerity,
     honour, and worthiness of the moment.
  3. There are only three outcomes:
       • silence — nothing happens; the sword did not stir.
       • tremor — the sword shifted, hummed, or lit briefly, but did NOT
                  lift free of the stone. A near-miss.
       • drawn  — the sword lifts free. This is exceptional; the
                  character is now bearer of the Tongue of Y'ros.

Only ONE bearer at a time can exist realm-wide. If the sword is already
drawn (bearer_active), all further attempts return silence with a
"the sword is already claimed" narration.

Once drawn, the bearer's `has_tongue_of_yros = True` flag is set on their
character document, and the scene state surfaces this fact to future RP
scenes ("wields the Tongue of Y'ros — dwarven eyes track this blade").
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

# Cooldown so a player can't spam the trial.
ATTEMPT_COOLDOWN_HOURS = 6

# When the bearer dies / passes it on, the sword is undrawn — the next
# worthy dwarf may attempt again. Tracked via a `tongue_of_yros_state`
# singleton document.
STATE_DOC_ID = "tongue_of_yros_state"


def _safe_parse_json(text: str) -> Optional[Dict]:
    if not text:
        return None
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
    return None


class TongueOfYrosService:
    def __init__(self, db):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    async def get_state(self) -> Dict:
        state = await self.db.tongue_of_yros_state.find_one({"_id": STATE_DOC_ID})
        if not state:
            state = {
                "_id": STATE_DOC_ID,
                "bearer_active": False,
                "bearer_character_id": None,
                "bearer_character_name": None,
                "bearer_drawn_at": None,
            }
            await self.db.tongue_of_yros_state.insert_one(state)
        state.pop("_id", None)
        return state

    async def _last_attempt(self, character_id: str) -> Optional[Dict]:
        return await self.db.tongue_of_yros_attempts.find_one(
            {"character_id": character_id},
            sort=[("attempted_at", -1)],
        )

    async def get_recent_attempts(self, character_id: str, limit: int = 25):
        cur = self.db.tongue_of_yros_attempts.find(
            {"character_id": character_id}, {"_id": 0},
        ).sort("attempted_at", -1).limit(max(1, min(50, limit)))
        return await cur.to_list(length=limit)

    async def _judge_attempt(self, *, character: Dict, attempt_text: str) -> Dict:
        """Calls the AI as Y'ros the god himself, judging the attempt.
        Returns {verdict, narration, judgement_reason}."""
        is_dwarf = "dwarf" in (character.get("race", "") or "").lower()
        if not is_dwarf:
            # Never even reach the AI — canonical lore is absolute.
            return {
                "verdict": "silence",
                "narration": (
                    f"You take hold of the ancient hilt. Nothing. The stone is stone; "
                    f"the blade is stone. No warmth answers your touch. The dwarves "
                    f"watching say nothing, though something like pity flickers behind "
                    f"their beards. This blade knows the hands of the earth-folk. Yours "
                    f"are not among them."
                ),
                "judgement_reason": "Non-dwarven petitioner — the sword does not respond.",
            }

        system_message = (
            "You are Yros, God of Earth, Patron of the Dwarves, Shaper of Mountains. "
            "Your voice is deep, gravelled, slow as tectonic shift. You speak in "
            "maxims and anvil-rhythms. You favour the steadfast, the oath-keeper, "
            "the maker. You disdain cowardice, broken vows, and idle hands.\n\n"
            "The petitioner stands in Thal'Karrak, Thalgrer's Tomb, and lays hand "
            "on the Tongue of Y'ros — a stone blade consecrated in your name at "
            "the founding of the Astral Era. ONLY dwarves may draw it, AND only "
            "when their attempt honours you.\n\n"
            "You judge each attempt by:\n"
            "  1. THE PLAYER'S OWN WORDS (their in-character declaration).\n"
            "  2. THE CHARACTER'S HISTORY (backstory, oaths kept, trials survived).\n"
            "  3. THE HUMILITY OF THE APPROACH — arrogance repels the blade.\n\n"
            "You return EXACTLY one of three verdicts:\n"
            "  • silence — the stone does not stir. The petitioner is unworthy today.\n"
            "  • tremor  — the sword hums, sparks, or shifts, but does NOT lift.\n"
            "               A near-miss. The petitioner is close, but not yet.\n"
            "  • drawn   — the sword lifts free of the stone. This is rare and\n"
            "               reserved for a petitioner whose words AND life align with\n"
            "               your domain: oath, stone, craft, ancestry, unbroken will.\n\n"
            "Output STRICT JSON: {\"verdict\": \"silence|tremor|drawn\", "
            "\"narration\": \"...\", \"judgement_reason\": \"...\"}\n"
            "  • narration: 3-5 sentences, present tense, second person. Describe "
            "the moment the hand meets the hilt. Weave in the dwarves watching, "
            "the tomb's cold air, the deep hum of stone (or its absence). Honour "
            "your voice — deep, spare, weighty. NEVER puppeteer the petitioner.\n"
            "  • judgement_reason: ONE short private sentence naming why.\n\n"
            "Grant 'drawn' sparingly — perhaps 1 in 30 attempts, and ONLY when "
            "the words + history clearly ring true. Most sincere dwarves earn "
            "tremor. Insincere or arrogant ones earn silence."
        )

        user_payload = (
            f"Petitioner:\n"
            f"  Name: {character.get('name','?')}\n"
            f"  Race: {character.get('race','?')}\n"
            f"  Class: {character.get('character_class','?')}\n"
            f"  Backstory: {(character.get('backstory') or '')[:400]}\n"
            f"  Nation: {character.get('nation','?')}\n\n"
            f"The petitioner's declaration as they lay hand on the hilt:\n"
            f"  \"{attempt_text.strip()}\"\n\n"
            "Judge this attempt. Return strict JSON only."
        )

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"tongue_of_yros_{character.get('id','?')}_{uuid.uuid4().hex[:8]}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o")
            response = await chat.send_message(UserMessage(text=user_payload))
        except Exception as e:
            logger.exception(f"Tongue of Y'ros AI call failed: {e}")
            return {
                "verdict": "silence",
                "narration": (
                    "You take hold of the hilt. The tomb is silent. Nothing answers. "
                    "You cannot tell if you have been judged, or merely overlooked."
                ),
                "judgement_reason": "AI unavailable — default silence.",
            }

        parsed = _safe_parse_json(response) or {}
        verdict = (parsed.get("verdict") or "").strip().lower()
        if verdict not in {"silence", "tremor", "drawn"}:
            verdict = "silence"
        narration = (parsed.get("narration") or "").strip() or (
            "The stone does not answer. The dwarves' eyes do not meet yours."
        )
        judgement_reason = (parsed.get("judgement_reason") or "").strip()[:300]
        return {"verdict": verdict, "narration": narration, "judgement_reason": judgement_reason}

    async def submit_attempt(self, *, character: Dict, attempt_text: str) -> Dict:
        text = (attempt_text or "").strip()
        if len(text) < 15:
            raise ValueError("Your declaration must be at least 15 characters of heartfelt intent.")
        if len(text) > 2000:
            raise ValueError("Declaration too long — keep it under 2000 characters.")

        # Cooldown
        last = await self._last_attempt(character["id"])
        if last:
            attempted_at = last.get("attempted_at")
            try:
                dt = datetime.fromisoformat(attempted_at) if isinstance(attempted_at, str) else attempted_at
            except (TypeError, ValueError):
                dt = None
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                cd_end = dt + timedelta(hours=ATTEMPT_COOLDOWN_HOURS)
                now = datetime.now(timezone.utc)
                if now < cd_end:
                    secs = int((cd_end - now).total_seconds())
                    hrs = secs // 3600
                    mins = (secs % 3600) // 60
                    raise ValueError(
                        f"You must rest and gather your resolve. The sword will not answer again "
                        f"for {hrs}h {mins}m."
                    )

        # Is the sword already claimed?
        state = await self.get_state()
        already_claimed = bool(state.get("bearer_active"))
        if already_claimed:
            record = {
                "id": str(uuid.uuid4()),
                "character_id": character["id"],
                "user_id": character.get("user_id"),
                "character_name": character.get("name"),
                "race": character.get("race"),
                "attempt_text": text,
                "verdict": "silence",
                "narration": (
                    f"The hilt is warm to the touch — but not for you. The blade already "
                    f"answers to another: {state.get('bearer_character_name') or 'the current bearer'}. "
                    f"Until they set it down or fall in battle, no other hand may claim it. "
                    f"The dwarves nod, respectful. You withdraw."
                ),
                "judgement_reason": "Blade already claimed by another bearer.",
                "attempted_at": datetime.now(timezone.utc).isoformat(),
                "bearer_at_time": state.get("bearer_character_name"),
            }
            await self.db.tongue_of_yros_attempts.insert_one({**record})
            return record

        judgement = await self._judge_attempt(character=character, attempt_text=text)

        record = {
            "id": str(uuid.uuid4()),
            "character_id": character["id"],
            "user_id": character.get("user_id"),
            "character_name": character.get("name"),
            "race": character.get("race"),
            "attempt_text": text,
            "verdict": judgement["verdict"],
            "narration": judgement["narration"],
            "judgement_reason": judgement["judgement_reason"],
            "attempted_at": datetime.now(timezone.utc).isoformat(),
            "bearer_at_time": None,
        }
        await self.db.tongue_of_yros_attempts.insert_one({**record})

        # If drawn — mark bearer + flag the character.
        if judgement["verdict"] == "drawn":
            await self.db.tongue_of_yros_state.update_one(
                {"_id": STATE_DOC_ID},
                {"$set": {
                    "bearer_active": True,
                    "bearer_character_id": character["id"],
                    "bearer_character_name": character.get("name"),
                    "bearer_drawn_at": record["attempted_at"],
                }},
                upsert=True,
            )
            await self.db.characters.update_one(
                {"id": character["id"]},
                {"$set": {"has_tongue_of_yros": True}},
            )

        return record

    async def relinquish(self, *, character_id: str) -> Dict:
        """A bearer voluntarily puts the sword back. The blade will accept
        new petitioners again."""
        state = await self.get_state()
        if not state.get("bearer_active") or state.get("bearer_character_id") != character_id:
            raise ValueError("You are not the current bearer of the Tongue of Y'ros.")
        await self.db.tongue_of_yros_state.update_one(
            {"_id": STATE_DOC_ID},
            {"$set": {
                "bearer_active": False,
                "bearer_character_id": None,
                "bearer_character_name": None,
                "bearer_drawn_at": None,
            }},
        )
        await self.db.characters.update_one(
            {"id": character_id},
            {"$set": {"has_tongue_of_yros": False}},
        )
        return {"ok": True}
