"""Tier 2a — Four Elder Gods Prayer System.

Characters may pray once per god per 24h. The AI (acting as the Elder God)
judges the prayer text for sincerity, alignment with the god's domain, and
the character's race-affinity. Each prayer returns one of three verdicts:

  • `silence`    — the prayer goes unanswered (default)
  • `flicker`    — the god stirs faintly; a brief blessing is granted
  • `blessing`   — a clear blessing is granted, persisting for the next
                   ~6 hours and surfacing in every RP scene the character
                   enters until expiry

Race affinity (canonical):
  • Seren  (Goddess of Life)     → Elves (any sub-race)
  • Yros   (God of Earth)        → Dwarves
  • Uesis  (God of the Heavens)  → Humans, Half-Elves
  • Ehena  (Goddess of Time)     → no race affinity — she favours those who
                                   demonstrate patience and foresight.

Matching race → +25 affinity bonus on AI judgement; mismatch → −10 penalty.
A character who has already received a `blessing` from this god in the last
6 hours cannot receive another blessing — they may pray, but the verdict
will downgrade to `flicker` at best (gods do not gild the lily).
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# CANON — the Four Elder Gods + race affinities + domains
# ════════════════════════════════════════════════════════════════════════
GODS: Dict[str, Dict] = {
    "seren": {
        "name": "Seren",
        "title": "Goddess of Life, Mother of the Elves, Creator of Yillhone",
        "domain": "life, growth, healing, nature, hope, mercy, beauty",
        "voice": (
            "Warm, ancient, maternal. Speaks slowly, choosing each word like a "
            "gardener choosing seed. Favours the gentle, the merciful, the "
            "creators. Disdains cruelty, waste, and slaughter for slaughter's "
            "sake."
        ),
        "race_affinity": [
            "elf", "high elf", "sun elf", "wood elf", "moon elf", "shadow elf",
            "crystal elf", "half-elf", "halfelf", "tide elf", "mountain elf",
        ],
        "blessing_palette": ["warmth", "gentle light", "the scent of blossom", "honey light"],
        "silence_palette": ["the air still", "no warmth answers", "an empty hush"],
    },
    "yros": {
        "name": "Yros",
        "title": "God of Earth, Patron of the Dwarves, Shaper of Mountains",
        "domain": "stone, metal, craft, oath-keeping, ancestry, strength, the forge",
        "voice": (
            "Deep, gravelled, slow as tectonic shift. Speaks in maxims and "
            "anvil-rhythms. Favours the steadfast, the oath-keeper, the maker. "
            "Disdains cowardice, broken vows, and idle hands."
        ),
        "race_affinity": ["dwarf", "hill dwarf", "mountain dwarf", "deep dwarf"],
        "blessing_palette": ["the deep hum of stone", "iron warmth", "the ring of distant hammers"],
        "silence_palette": ["stone is cold", "no answer in the depths", "the anvil stays silent"],
    },
    "uesis": {
        "name": "Uesis",
        "title": "God of the Heavens, Dragon-Celestial, Speaker through Omens",
        "domain": "sky, sun, stars, knowledge, prophecy, lightning, judgement",
        "voice": (
            "Distant, wind-thinned, with the rustle of vast wings beneath. "
            "Speaks in riddle-shapes and celestial metaphors. Favours seekers, "
            "scholars, those who lift their faces to the sky. Disdains "
            "willful ignorance, blasphemy, and earth-bound cowardice."
        ),
        "race_affinity": ["human", "tiefling", "aasimar", "half-elf", "halfelf"],
        "blessing_palette": ["a thread of starlight", "the smell of rain", "a faint chime above"],
        "silence_palette": ["the sky is mute", "clouds drift, unmoved", "no wind stirs"],
    },
    "ehena": {
        "name": "Ehena",
        "title": "Goddess of Time, Queen of the Elder Gods, Eldest of All",
        "domain": "time, memory, patience, foresight, endings, beginnings, inevitability",
        "voice": (
            "Layered, as if many voices speak at once — past, present, and "
            "future overlaid. Speaks in tenses that do not quite resolve. "
            "Favours patience, the keeping of small promises, the long view. "
            "Disdains haste, betrayal of one's earlier self, and rash oaths."
        ),
        "race_affinity": [],  # universal — she favours patience, not blood
        "blessing_palette": ["a moment held suspended", "the hush between heartbeats", "a thread of timeless quiet"],
        "silence_palette": ["the moment passes", "time flows on, unheeding", "the clock-shadow does not pause"],
    },
}

# Active blessings persist this long after they're granted.
BLESSING_TTL_HOURS = 6

# Cooldown between two prayers to the SAME god.
PER_GOD_COOLDOWN_HOURS = 24


def list_gods() -> List[Dict]:
    """Public catalogue for the frontend — never includes voice / palette."""
    return [
        {
            "key": k,
            "name": v["name"],
            "title": v["title"],
            "domain": v["domain"],
            "race_affinity": v["race_affinity"],
        }
        for k, v in GODS.items()
    ]


def _race_match(god_key: str, race: str) -> bool:
    god = GODS.get(god_key)
    if not god:
        return False
    if not god["race_affinity"]:  # Ehena — universal
        return False
    r = (race or "").strip().lower()
    return any(aff in r for aff in god["race_affinity"])


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


class PrayerService:
    """All prayer logic — judging, persisting, surfacing active blessings."""

    def __init__(self, db):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    async def _last_prayer_for_god(self, character_id: str, god_key: str) -> Optional[Dict]:
        return await self.db.prayers.find_one(
            {"character_id": character_id, "god": god_key},
            sort=[("prayed_at", -1)],
        )

    async def _existing_blessing_active(self, character_id: str, god_key: str) -> bool:
        """True iff this character already has a non-expired blessing FROM
        this god. Used to downgrade verdicts so the player can't farm
        infinite stacked blessings.

        Compares against `expires_at` (not `prayed_at`) — a blessing remains
        active until it expires, regardless of when it was prayed.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        doc = await self.db.prayers.find_one({
            "character_id": character_id,
            "god": god_key,
            "verdict": "blessing",
            "expires_at": {"$gt": now_iso},
        })
        return doc is not None

    async def _judge_prayer(
        self,
        *,
        god_key: str,
        character: Dict,
        prayer_text: str,
        existing_blessing_active: bool,
    ) -> Dict:
        """Calls the AI as the god itself. Returns
        {verdict, narration, boon_text, judgement_reason, affinity_score}."""
        god = GODS[god_key]
        race_match = _race_match(god_key, character.get("race", ""))
        affinity_bias = 25 if race_match else (-10 if god["race_affinity"] else 0)

        # ── Elder-Gods festival boost ──
        # If today is this god's festival day, apply the calendar boost so
        # the AI is nudged more generously. Cross-god festivals (e.g. praying
        # to Seren on a Yros day) grant no bonus.
        festival_note = ""
        active_festival = None
        try:
            from elder_gods_festivals import get_active_festival
            active_festival = get_active_festival()
        except Exception as _fe:  # pragma: no cover — defensive
            logger.warning(f"festival lookup failed: {_fe}")
        if active_festival and active_festival["god"] == god_key:
            affinity_bias += active_festival["affinity_boost"]
            festival_note = (
                f"\nTODAY IS {active_festival['festival_name'].upper()} — "
                f"YOUR festival day. Your favour flows more freely; petitioners "
                f"who bring sincere words on this day are treated with more "
                f"generosity than usual."
            )

        system_message = (
            f"You are {god['name']}, {god['title']}.\n"
            f"DOMAIN: {god['domain']}.\n"
            f"VOICE: {god['voice']}\n\n"
            "You are an Elder God of Delarom. You cannot descend to the mortal "
            "realm — your power is too great. You influence through omens, "
            "fleeting warmth, and rare blessings. You judge each prayer by:\n"
            "  1. SINCERITY — is the prayer heartfelt, or transactional?\n"
            "  2. ALIGNMENT — does the prayer's want align with YOUR domain?\n"
            "  3. CHARACTER — does this petitioner's life and history honour "
            "you, or insult you?\n\n"
            "You return EXACTLY one of three verdicts:\n"
            "  • silence  — the prayer goes unanswered. The world stays still.\n"
            "  • flicker  — a brief, ambiguous sign. You stirred but did not "
            "fully respond.\n"
            "  • blessing — a clear, lingering boon. Reserved for prayers that "
            "land squarely in your domain AND show true devotion.\n\n"
            "Output STRICT JSON: {\"verdict\": \"silence|flicker|blessing\", "
            "\"narration\": \"...\", \"boon_text\": \"...\", "
            "\"judgement_reason\": \"...\"}\n"
            "  • narration: 2-4 sentences, present tense, second person ('you'). "
            "Describe what the petitioner senses (or doesn't). Honour the voice "
            "rules above. NEVER puppeteer the petitioner.\n"
            "  • boon_text: ONE short sentence describing the lingering effect "
            "(only for blessing/flicker; empty string for silence). Example: "
            "'Yros's hand steadies your strikes — your blows ring truer for a "
            "time.'\n"
            "  • judgement_reason: ONE short private sentence (the player will "
            "not see this) summarising WHY you chose this verdict.\n\n"
            "Be sparing. Most prayers should be silence or flicker. Blessings "
            "must be earned."
        )

        affinity_note = (
            f"\nThis petitioner is {character.get('race','?')} — "
            f"{'STRONGLY ALIGNED with your race-affinity' if race_match else 'NOT in your race-affinity'}.\n"
            f"Affinity bias to apply: {affinity_bias:+d} (treat positive as a gentle nudge "
            f"toward generosity, negative as toward severity — but never override sincerity)."
        )
        diminishing_note = (
            "\nNOTE: This petitioner already carries an active BLESSING from you "
            "(< 6h old). You may grant flicker AT MOST — never blessing. Gods do "
            "not gild the lily."
            if existing_blessing_active else ""
        )

        user_payload = (
            f"Petitioner:\n"
            f"  Name: {character.get('name','?')}\n"
            f"  Race: {character.get('race','?')}\n"
            f"  Class: {character.get('character_class','?')}\n"
            f"  Backstory (short): {(character.get('backstory') or '')[:300]}\n"
            f"  Nation: {character.get('nation','?')}\n"
            f"{affinity_note}{diminishing_note}{festival_note}\n\n"
            f"The prayer (their own words):\n  \"{prayer_text.strip()}\"\n\n"
            "Judge this prayer. Return strict JSON only."
        )

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"prayer_{god_key}_{character.get('id','?')}_{uuid.uuid4().hex[:8]}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o")
            response = await chat.send_message(UserMessage(text=user_payload))
        except Exception as e:
            logger.exception(f"Prayer AI call failed: {e}")
            return self._fallback_judgement(god_key, race_match, existing_blessing_active)

        parsed = _safe_parse_json(response) or {}
        verdict = (parsed.get("verdict") or "").strip().lower()
        if verdict not in {"silence", "flicker", "blessing"}:
            verdict = "silence"
        # Downgrade if existing blessing active.
        if existing_blessing_active and verdict == "blessing":
            verdict = "flicker"

        narration = (parsed.get("narration") or "").strip()
        if not narration:
            narration = self._fallback_narration(god_key, verdict)
        boon_text = (parsed.get("boon_text") or "").strip() if verdict in ("flicker", "blessing") else ""
        judgement_reason = (parsed.get("judgement_reason") or "").strip()[:300]

        return {
            "verdict": verdict,
            "narration": narration,
            "boon_text": boon_text,
            "judgement_reason": judgement_reason,
            "affinity_match": race_match,
        }

    def _fallback_judgement(self, god_key: str, race_match: bool, existing_blessing_active: bool) -> Dict:
        if race_match and not existing_blessing_active:
            verdict = "flicker"
        else:
            verdict = "silence"
        return {
            "verdict": verdict,
            "narration": self._fallback_narration(god_key, verdict),
            "boon_text": (
                f"{GODS[god_key]['name']} stirs faintly — a moment's grace." if verdict == "flicker" else ""
            ),
            "judgement_reason": "AI judgement unavailable; fallback verdict applied.",
            "affinity_match": race_match,
        }

    def _fallback_narration(self, god_key: str, verdict: str) -> str:
        god = GODS[god_key]
        if verdict == "silence":
            return f"You speak the words. {god['silence_palette'][0].capitalize()}. {god['name']} does not answer this hour."
        if verdict == "flicker":
            return f"You speak the words. For a moment, {god['blessing_palette'][0]} touches you — then it is gone, leaving only a quiet certainty that you were heard."
        return f"You speak the words. {god['blessing_palette'][0].capitalize()} fills the air — {god['name']} has heard, and answered."

    async def submit_prayer(
        self,
        *,
        character: Dict,
        god_key: str,
        prayer_text: str,
    ) -> Dict:
        if god_key not in GODS:
            raise ValueError(f"Unknown god '{god_key}'. Must be one of: {list(GODS)}")
        text = (prayer_text or "").strip()
        if len(text) < 10:
            raise ValueError("Prayer must be at least 10 characters of heartfelt text.")
        if len(text) > 1500:
            raise ValueError("Prayer too long — keep it under 1500 characters.")

        last = await self._last_prayer_for_god(character["id"], god_key)
        if last:
            prayed_at = last.get("prayed_at")
            try:
                prayed_dt = datetime.fromisoformat(prayed_at) if isinstance(prayed_at, str) else prayed_at
            except (TypeError, ValueError):
                prayed_dt = None
            if prayed_dt is not None:
                if prayed_dt.tzinfo is None:
                    prayed_dt = prayed_dt.replace(tzinfo=timezone.utc)
                cooldown_until = prayed_dt + timedelta(hours=PER_GOD_COOLDOWN_HOURS)
                now = datetime.now(timezone.utc)
                if now < cooldown_until:
                    secs = int((cooldown_until - now).total_seconds())
                    hrs = secs // 3600
                    mins = (secs % 3600) // 60
                    raise ValueError(
                        f"You have already prayed to {GODS[god_key]['name']} recently. "
                        f"Try again in {hrs}h {mins}m."
                    )

        existing_blessing_active = await self._existing_blessing_active(character["id"], god_key)
        judgement = await self._judge_prayer(
            god_key=god_key,
            character=character,
            prayer_text=text,
            existing_blessing_active=existing_blessing_active,
        )

        prayed_at = datetime.now(timezone.utc)
        expires_at = prayed_at + timedelta(hours=BLESSING_TTL_HOURS)
        record = {
            "id": str(uuid.uuid4()),
            "character_id": character["id"],
            "user_id": character.get("user_id"),
            "god": god_key,
            "god_name": GODS[god_key]["name"],
            "prayer_text": text,
            "verdict": judgement["verdict"],
            "narration": judgement["narration"],
            "boon_text": judgement["boon_text"],
            "judgement_reason": judgement["judgement_reason"],
            "affinity_match": judgement["affinity_match"],
            "prayed_at": prayed_at.isoformat(),
            "expires_at": expires_at.isoformat() if judgement["verdict"] in ("blessing", "flicker") else None,
        }
        await self.db.prayers.insert_one({**record})
        return record

    async def get_recent_prayers(self, character_id: str, limit: int = 10) -> List[Dict]:
        cur = self.db.prayers.find(
            {"character_id": character_id},
            {"_id": 0},
        ).sort("prayed_at", -1).limit(max(1, min(50, limit)))
        return await cur.to_list(length=limit)

    async def get_active_blessings(self, character_id: str) -> List[Dict]:
        """Returns currently-active blessings (and flickers — they too colour
        the world briefly) for use in scene state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = self.db.prayers.find(
            {
                "character_id": character_id,
                "verdict": {"$in": ["blessing", "flicker"]},
                "expires_at": {"$gt": now_iso},
            },
            {"_id": 0},
        ).sort("prayed_at", -1)
        rows = await cur.to_list(length=10)
        seen: set = set()
        out: List[Dict] = []
        for r in rows:
            if r["god"] in seen:
                continue
            seen.add(r["god"])
            out.append({
                "god": r["god"],
                "god_name": r["god_name"],
                "verdict": r["verdict"],
                "boon_text": r["boon_text"],
                "expires_at": r["expires_at"],
            })
        return out
