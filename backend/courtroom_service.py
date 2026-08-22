"""Courtroom / Trial service for Continents of Delarom.

Transforms the existing one-shot magistrate's narration into a full
multi-turn courtroom RP scene:
    - Player is moved to an auto-created {city}-courthouse location.
    - Persistent NPCs (Judge, Prosecutor) preside.
    - Named victim NPCs from the open crimes are summoned as witnesses.
    - Player gets up to 5 defence turns; the judge can cut them short on
      clearly absurd defences.
    - A running `leniency_score` tally is updated each turn based on the
      quality, cunning, and tone of the player's defence (bribes, alibis,
      pulling rank, intimidation all factor in).
    - When the player rests their case OR runs out of turns OR the judge
      cuts them off, a final verdict is rendered that takes the running
      leniency score into account.

Design notes
------------
- Single new collection: `trials`.
- Trial-state is the source of truth; imprisonments are only created AFTER
  the verdict, so a player on trial is NOT imprisoned yet — they cannot
  attempt escape, they can only defend themselves.
- The Jail and Courthouse locations are siblings under the same city; the
  surrender / auto-arrest flow now moves the player to the courthouse,
  then (on guilty verdict) onward to the jail.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)


COURTHOUSE_LOCATION_TYPE = "courthouse"
MAX_DEFENCE_TURNS = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pretty_name(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-")) if slug else ""


# ────────────────────────── Courthouse location ──────────────────────────


def _build_courthouse_doc(nation: str, city: Optional[str], slug: str, name: str) -> Dict:
    description = (
        f"The {name} — marble pillars worn smooth by centuries of arguments, "
        "an oaken dock for the accused, benches for witnesses, and a high "
        "bench from which the city's judge weighs each soul brought to "
        "justice. The air smells of beeswax, paper, and the faint nervous "
        "sweat of the next defendant."
    )
    return {
        "id": str(uuid.uuid4()),
        "nation": nation,
        "city": city,
        "slug": slug,
        "name": name,
        "location_type": COURTHOUSE_LOCATION_TYPE,
        "description": description,
        "image_url": None,
        "image_id": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": _now_iso(),
    }


async def ensure_courthouse_for_city(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    city: Optional[str],
    fallback_location_slug: Optional[str] = None,
) -> Dict:
    """Return the courthouse location for this city, creating it if needed.

    City-scoped courthouses are preferred. If `city` is None, we fall back
    to a single nation-level courthouse.
    """
    if city:
        existing = await db.locations.find_one(
            {"nation": nation, "city": city, "location_type": COURTHOUSE_LOCATION_TYPE},
            {"_id": 0},
        )
        if existing:
            return existing
        # Older slug pattern as a defensive lookup
        existing = await db.locations.find_one(
            {"nation": nation, "city": city, "slug": f"{city}-courthouse"},
            {"_id": 0},
        )
        if existing:
            return existing
        slug = f"{city}-courthouse"
        name = f"{_pretty_name(city)} Courthouse"
    else:
        existing = await db.locations.find_one(
            {
                "nation": nation,
                "location_type": COURTHOUSE_LOCATION_TYPE,
                "$or": [{"city": None}, {"city": ""}, {"city": {"$exists": False}}],
            },
            {"_id": 0},
        )
        if existing:
            return existing
        slug = f"{nation}-courthouse"
        if fallback_location_slug:
            slug = f"{fallback_location_slug}-courthouse"
        name = f"{_pretty_name(nation)} Courthouse"

    # Slug-collision guard (same nation, different location_type)
    collision = await db.locations.find_one(
        {"nation": nation, "slug": slug}, {"_id": 0, "id": 1, "location_type": 1}
    )
    if collision and collision.get("location_type") != COURTHOUSE_LOCATION_TYPE:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    doc = _build_courthouse_doc(nation=nation, city=city, slug=slug, name=name)
    await db.locations.insert_one(dict(doc))
    return doc


# ────────────────────────── Court NPCs ──────────────────────────


JUDGE_ROLE = "judge"
PROSECUTOR_ROLE = "prosecutor"


async def _find_court_npc(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    courthouse_slug: str,
    role: str,
) -> Optional[Dict]:
    return await db.npcs.find_one(
        {"nation": nation, "location": courthouse_slug, "role": role},
        {"_id": 0},
    )


async def ensure_judge_and_prosecutor(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    courthouse_slug: str,
    city: Optional[str],
) -> Dict[str, Dict]:
    """Make sure the courthouse has a persistent Judge + Prosecutor NPC.

    Returns `{"judge": <npc>, "prosecutor": <npc>}`. Both NPCs are stored
    in the regular `npcs` collection so they show up in scene-state and
    accumulate relationship memory with every defendant.
    """
    judge = await _find_court_npc(db, nation=nation, courthouse_slug=courthouse_slug, role=JUDGE_ROLE)
    prosecutor = await _find_court_npc(db, nation=nation, courthouse_slug=courthouse_slug, role=PROSECUTOR_ROLE)

    city_label = _pretty_name(city) if city else _pretty_name(nation)

    if not judge:
        judge_doc = {
            "id": str(uuid.uuid4()),
            "name": f"Magistrate of {city_label}",
            "race": "Human",
            "role": JUDGE_ROLE,
            "nation": nation,
            "location": courthouse_slug,
            "appearance": (
                "Robed in the city's colours, a chain of office about the neck, "
                "spectacles perched, quill in hand, eyes that have seen every "
                "lie and most of the truths."
            ),
            "personality": (
                "Patient, unflappable, weary of cleverness. Listens far more "
                "than they speak. Cuts off histrionics swiftly."
            ),
            "motivation": (
                "Keep the law of this realm coherent. Mercy when warranted, "
                "iron when not."
            ),
            "background": (
                f"Appointed to preside over the courthouse of {city_label}. "
                "Has heard cases ranging from petty pickpocket squabbles to "
                "noble blood-feuds."
            ),
            "quirks": "Taps the gavel three times before delivering verdict.",
            "importance": "noble",
            "overall_mood": "neutral",
            "mood_score": 0,
            "status": "alive",
            "status_note": "",
            "companion_of": None,
            "created_by_character_id": None,
            "is_admin_seeded": False,
            "created_by": "courtroom_service",
            "created_at": _now_iso(),
            "last_seen_at": _now_iso(),
        }
        await db.npcs.insert_one(dict(judge_doc))
        judge = judge_doc

    if not prosecutor:
        prosecutor_doc = {
            "id": str(uuid.uuid4()),
            "name": f"Crown Advocate of {city_label}",
            "race": "Human",
            "role": PROSECUTOR_ROLE,
            "nation": nation,
            "location": courthouse_slug,
            "appearance": (
                "Sharp robes, sharper tongue. Carries a satchel stuffed with "
                "depositions and reads them with theatrical contempt."
            ),
            "personality": (
                "Combative, ambitious, fond of rhetorical flourishes. Believes "
                "every defendant guilty until inconveniently proven otherwise."
            ),
            "motivation": (
                "Win cases. Rise in the realm's legal apparatus. Be remembered "
                "by name in the city's legal records."
            ),
            "background": (
                f"The Crown's voice in the {city_label} courthouse — appointed to "
                "prosecute crimes against the realm and its peace."
            ),
            "quirks": "Always finishes with the phrase 'I rest my case.'",
            "importance": "notable",
            "overall_mood": "stern",
            "mood_score": -5,
            "status": "alive",
            "status_note": "",
            "companion_of": None,
            "created_by_character_id": None,
            "is_admin_seeded": False,
            "created_by": "courtroom_service",
            "created_at": _now_iso(),
            "last_seen_at": _now_iso(),
        }
        await db.npcs.insert_one(dict(prosecutor_doc))
        prosecutor = prosecutor_doc

    return {"judge": judge, "prosecutor": prosecutor}


# ────────────────────────── Trial state ──────────────────────────


def _baseline_sentence_for_crimes(open_crimes: List[Dict]) -> Dict:
    """Coarse baseline sentence used as the AI's starting point before
    leniency is applied. Mirrors the magistrate's old single-shot logic."""
    if not open_crimes:
        return {"sentence_type": "dismissed", "imprison_turns": 0, "fine_amount": 0}
    severity_order = ["petty", "minor", "major", "capital", "regicide"]
    worst_idx = max(
        (severity_order.index(c.get("severity", "minor"))
         for c in open_crimes if c.get("severity") in severity_order),
        default=1,
    )
    worst = severity_order[worst_idx]
    if worst == "petty":
        return {"sentence_type": "fine", "imprison_turns": 0, "fine_amount": 50}
    if worst == "minor":
        return {"sentence_type": "imprison", "imprison_turns": 3, "fine_amount": 0}
    if worst == "major":
        return {"sentence_type": "imprison", "imprison_turns": 10, "fine_amount": 0}
    if worst == "capital":
        return {"sentence_type": "imprison", "imprison_turns": 25, "fine_amount": 0}
    return {"sentence_type": "execute", "imprison_turns": 0, "fine_amount": 0}


class CourtroomService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.trials = db.trials

    # ─────────────── Read ───────────────

    async def get_active_trial(self, character_id: str) -> Optional[Dict]:
        return await self.trials.find_one(
            {"character_id": character_id, "status": "in_session"},
            {"_id": 0},
        )

    async def get_trial(self, trial_id: str) -> Optional[Dict]:
        return await self.trials.find_one({"id": trial_id}, {"_id": 0})

    # ─────────────── Start ───────────────

    async def start_trial(
        self,
        *,
        character_id: str,
        character_name: str,
        user_id: str,
        nation: str,
        origin_location: str,
        courthouse_location: str,
        city: Optional[str],
        crime_ids: List[str],
        open_crimes_snapshot: List[Dict],
        judge_npc_id: str,
        prosecutor_npc_id: str,
        victim_npc_ids: List[str],
        total_bounty: int,
    ) -> Dict:
        """Create an in_session trial. Idempotent — if the character already
        has an active trial, return it instead of creating a new one."""
        existing = await self.get_active_trial(character_id)
        if existing:
            return existing
        doc = {
            "id": str(uuid.uuid4()),
            "character_id": character_id,
            "character_name": character_name,
            "user_id": user_id,
            "nation": nation,
            "origin_location": origin_location,
            "courthouse_location": courthouse_location,
            "city": city,
            "crime_ids": list(crime_ids),
            "open_crimes_snapshot": open_crimes_snapshot,
            "total_bounty": int(total_bounty or 0),
            "judge_npc_id": judge_npc_id,
            "prosecutor_npc_id": prosecutor_npc_id,
            "victim_npc_ids": [v for v in victim_npc_ids if v],
            "defense_turns_used": 0,
            "max_defense_turns": MAX_DEFENCE_TURNS,
            "leniency_score": 0,
            "defense_history": [],
            "opening_narration": "",
            "status": "in_session",
            "verdict": None,
            "started_at": _now_iso(),
            "ended_at": None,
        }
        await self.trials.insert_one(dict(doc))
        return doc

    async def set_opening_narration(self, trial_id: str, narration: str) -> None:
        await self.trials.update_one(
            {"id": trial_id},
            {"$set": {"opening_narration": (narration or "")[:2000]}},
        )

    # ─────────────── Defence turns ───────────────

    async def append_defence_turn(
        self,
        trial_id: str,
        *,
        defence_text: str,
        ai_narration: str,
        leniency_delta: int,
        judge_remark: str = "",
        judge_cut_off: bool = False,
    ) -> Optional[Dict]:
        trial = await self.get_trial(trial_id)
        if not trial or trial["status"] != "in_session":
            return trial
        turn_no = int(trial.get("defense_turns_used", 0)) + 1
        entry = {
            "turn": turn_no,
            "defence_text": (defence_text or "")[:2000],
            "ai_narration": (ai_narration or "")[:4000],
            "leniency_delta": int(leniency_delta),
            "judge_remark": (judge_remark or "")[:400],
            "judge_cut_off": bool(judge_cut_off),
            "at": _now_iso(),
        }
        new_score = int(trial.get("leniency_score", 0)) + int(leniency_delta)
        # Clamp leniency to a sane range so the AI doesn't drift unbounded.
        if new_score > 100:
            new_score = 100
        elif new_score < -100:
            new_score = -100
        await self.trials.update_one(
            {"id": trial_id},
            {
                "$set": {
                    "defense_turns_used": turn_no,
                    "leniency_score": new_score,
                },
                "$push": {"defense_history": entry},
            },
        )
        return await self.get_trial(trial_id)

    # ─────────────── Conclude ───────────────

    async def finalize_trial(
        self,
        trial_id: str,
        *,
        verdict: Dict,
        new_status: str = "verdict_delivered",
    ) -> Optional[Dict]:
        await self.trials.update_one(
            {"id": trial_id, "status": "in_session"},
            {"$set": {
                "verdict": verdict,
                "status": new_status,
                "ended_at": _now_iso(),
            }},
        )
        return await self.get_trial(trial_id)

    async def abandon_trial(self, trial_id: str, *, reason: str = "") -> Optional[Dict]:
        await self.trials.update_one(
            {"id": trial_id, "status": "in_session"},
            {"$set": {
                "status": "abandoned",
                "ended_at": _now_iso(),
                "abandon_reason": (reason or "")[:200],
            }},
        )
        return await self.get_trial(trial_id)


# ────────────────────────── Witness summoning ──────────────────────────


async def gather_victim_witnesses(
    db: AsyncIOMotorDatabase,
    *,
    open_crimes: List[Dict],
) -> List[Dict]:
    """For each named victim in the open crimes, try to resolve the matching
    persistent NPC (so memory + relationship history can drive their testimony).

    Returns a list of `{name, npc_id?, importance, crime_link}` records the
    AI prompt can use to roleplay each witness vividly.
    """
    out: List[Dict] = []
    seen_names = set()
    for c in open_crimes:
        victim_name = (c.get("victim_name") or "").strip()
        if not victim_name or victim_name.lower() in ("", "unknown", "an unnamed victim"):
            continue
        if victim_name in seen_names:
            continue
        seen_names.add(victim_name)
        # Try to resolve the NPC by name in the same nation.
        npc = await db.npcs.find_one(
            {"name": victim_name, "nation": c.get("nation", "")},
            {"_id": 0, "id": 1, "name": 1, "race": 1, "role": 1,
             "personality": 1, "importance": 1, "overall_mood": 1},
        )
        out.append({
            "name": victim_name,
            "npc_id": (npc or {}).get("id"),
            "race": (npc or {}).get("race", "?"),
            "role": (npc or {}).get("role", "victim"),
            "importance": c.get("victim_importance") or (npc or {}).get("importance") or "commoner",
            "crime_summary": f"{c.get('severity','minor')} {c.get('crime_type','crime')}",
            "personality": (npc or {}).get("personality", ""),
        })
    return out
