"""Law and Crime service for Continents of Delarom.

Isolated module that handles crime recording, bounty aggregation, trials,
and imprisonment. Designed to be a quiet bolt-on:

* All logic lives here — server.py and other services do NOT mutate law data
  directly, they call `LawService` methods.
* Three dedicated collections only: `crimes`, `bounties`, `imprisonments`.
* No background ticks, no cron — everything is lazy / triggered by player actions.
* Gated by env flag `LAW_SYSTEM_ENABLED` (default "true"). When disabled, the
  whole feature goes dormant.

Severity tiers (with base bounty ranges in gold):
    petty   : 5–25     (pickpocketing, brawling, vandalism)
    minor   : 50–200   (theft, assault, drunken duel)
    major   : 500–2000 (grand theft, assault of a noble, arson)
    capital : 5000–25000 (murder, treason against a noble)
    regicide: 50000+   (assassination of a monarch, mass murder)

Bounty scales with victim importance:
    commoner=1×, notable=2×, noble=5×, ruler=10×, monarch=25×
"""

from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SEVERITY_TIERS: Dict[str, Dict] = {
    "petty":    {"min": 5,     "max": 25,    "label": "Petty"},
    "minor":    {"min": 50,    "max": 200,   "label": "Minor"},
    "major":    {"min": 500,   "max": 2000,  "label": "Major"},
    "capital":  {"min": 5000,  "max": 25000, "label": "Capital"},
    "regicide": {"min": 50000, "max": 200000, "label": "Regicide"},
}

VICTIM_IMPORTANCE_MULTIPLIER: Dict[str, float] = {
    "commoner": 1.0,
    "notable": 2.0,
    "noble":   5.0,
    "ruler":   10.0,
    "monarch": 25.0,
}

# Default suggested sentence length (in roleplay "turns" — the player can attempt
# escape, surrender to additional charges, etc. between turns) per severity.
SEVERITY_SENTENCE_TURNS: Dict[str, int] = {
    "petty":    1,
    "minor":    3,
    "major":    8,
    "capital":  20,
    "regicide": 100,
}

# Active-warrant escalation thresholds. A "warrant" is an actively-pursued
# arrest order — guards announce themselves and try to take the player in.
#
# Tuned aggressive so MINOR crimes graduate quickly (was: only major+ ever
# went public). Anyone with these conditions has a live warrant in-nation:
#   - any open MAJOR / CAPITAL / REGICIDE crime → instant warrant
#   - any open MINOR crime → instant warrant
#   - 2+ open PETTY crimes → warrant (one pickpocket = warning; two = wanted)
WARRANT_TRIGGER_SEVERITIES = {"minor", "major", "capital", "regicide"}
PETTY_WARRANT_COUNT = 2


def law_system_enabled() -> bool:
    """Single point of truth for the feature flag."""
    return os.environ.get("LAW_SYSTEM_ENABLED", "true").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _compute_bounty(severity: str, victim_importance: str) -> int:
    tier = SEVERITY_TIERS.get(severity, SEVERITY_TIERS["minor"])
    base = (tier["min"] + tier["max"]) // 2
    mult = VICTIM_IMPORTANCE_MULTIPLIER.get(victim_importance or "commoner", 1.0)
    return int(base * mult)


class LawService:
    """High-level API for crime/bounty/imprisonment workflows.

    All public methods are async and operate on the three collections. No
    other module should touch those collections directly — go through this
    service so we can change schema later without ripples.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.crimes = db.crimes
        self.bounties = db.bounties
        self.imprisonments = db.imprisonments

    # ---------- Crimes ----------

    @staticmethod
    def _resolve_perpetrator(
        perpetrator_type: str,
        perpetrator_id: Optional[str],
        perpetrator_name: str,
        character_id: Optional[str],
        character_name: str,
    ) -> tuple[str, str, str]:
        """Normalize perpetrator identity for `record_crime`.

        Returns (perpetrator_type, perp_id, perp_name). Raises ValueError if
        a required id is missing.
        """
        if perpetrator_type == "npc":
            if not perpetrator_id:
                raise ValueError("perpetrator_id is required for NPC crimes")
            return "npc", perpetrator_id, (perpetrator_name or "Unknown NPC")
        # default: character perpetrator (preserves legacy call sites)
        perp_id = perpetrator_id or character_id
        if not perp_id:
            raise ValueError("character_id is required for character crimes")
        return "character", perp_id, (perpetrator_name or character_name or "Unknown")

    @staticmethod
    def _build_crime_doc(
        *,
        perpetrator_type: str,
        perp_id: str,
        perp_name: str,
        character_id: Optional[str],
        character_name: str,
        user_id: Optional[str],
        nation: str,
        location: str,
        crime_type: str,
        severity: str,
        victim_name: str,
        victim_importance: str,
        description: str,
        bounty_amount: int,
    ) -> Dict:
        """Build the MongoDB document for a new crime row."""
        return {
            "id": str(uuid.uuid4()),
            # Generalized perpetrator
            "perpetrator_type": perpetrator_type,
            "perpetrator_id": perp_id,
            "perpetrator_name": perp_name,
            # Back-compat aliases (only populated for character perpetrators)
            "character_id": character_id if perpetrator_type == "character" else None,
            "character_name": character_name if perpetrator_type == "character" else "",
            "user_id": user_id,
            "nation": nation,
            "location": location,
            "crime_type": crime_type,
            "severity": severity,
            "victim_name": victim_name or "",
            "victim_importance": victim_importance or "commoner",
            "description": (description or "").strip()[:500],
            "bounty": bounty_amount,
            "status": "open",  # open | paid | served | escaped | pardoned | expunged | claimed
            "created_at": _now_iso(),
            "resolved_at": None,
            "resolved_reason": None,
        }

    async def record_crime(
        self,
        *,
        character_id: Optional[str] = None,
        character_name: str = "",
        user_id: Optional[str] = None,
        nation: str,
        location: str,
        crime_type: str,
        severity: str,
        victim_name: str = "",
        victim_importance: str = "commoner",
        description: str = "",
        # Generalized perpetrator fields. Defaults preserve old behaviour.
        perpetrator_type: str = "character",  # "character" | "npc"
        perpetrator_id: Optional[str] = None,
        perpetrator_name: str = "",
    ) -> Dict:
        """Insert a new crime row and update the aggregated bounty for the
        perpetrator in this nation.

        Backwards-compatible: callers using only `character_id`/`character_name`
        keep working — the new schema also stores `perpetrator_type='character'`
        and `perpetrator_id=character_id`.
        """
        if severity not in SEVERITY_TIERS:
            severity = "minor"
        bounty_amount = _compute_bounty(severity, victim_importance)

        perpetrator_type, perp_id, perp_name = self._resolve_perpetrator(
            perpetrator_type, perpetrator_id, perpetrator_name, character_id, character_name,
        )

        doc = self._build_crime_doc(
            perpetrator_type=perpetrator_type,
            perp_id=perp_id,
            perp_name=perp_name,
            character_id=character_id,
            character_name=character_name,
            user_id=user_id,
            nation=nation,
            location=location,
            crime_type=crime_type,
            severity=severity,
            victim_name=victim_name,
            victim_importance=victim_importance,
            description=description,
            bounty_amount=bounty_amount,
        )
        await self.crimes.insert_one(dict(doc))
        await self._refresh_bounty(perpetrator_type, perp_id, nation, perp_name)

        # Round 2 hook: if a CHARACTER member of a faction commits a crime,
        # the faction's reputation drops in that nation. NPC crimes do not
        # propagate (NPCs don't hold faction memberships in this system).
        if perpetrator_type == "character":
            try:
                # Lazy import to avoid a circular dep on route module import time.
                from routes.factions import apply_crime_to_faction
                await apply_crime_to_faction(
                    self.db,
                    character_id=perp_id,
                    nation=nation,
                    severity=severity,
                    description=description,
                )
            except Exception as e:
                # Faction reputation is best-effort — never block crime recording.
                import logging
                logging.getLogger(__name__).warning(
                    "Faction reputation hook failed for crime %s: %s", doc["id"], e,
                )
        return doc

    async def list_crimes_for_character(
        self,
        character_id: str,
        nation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        q: Dict = {"perpetrator_type": "character", "perpetrator_id": character_id}
        if nation:
            q["nation"] = nation
        if status:
            q["status"] = status
        cursor = self.crimes.find(q, {"_id": 0}).sort("created_at", -1)
        return await cursor.to_list(limit)

    async def list_crimes_for_npc(
        self,
        npc_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        q: Dict = {"perpetrator_type": "npc", "perpetrator_id": npc_id}
        if status:
            q["status"] = status
        cursor = self.crimes.find(q, {"_id": 0}).sort("created_at", -1)
        return await cursor.to_list(limit)

    async def list_open_crimes_in_nation(
        self,
        character_id: str,
        nation: str,
        limit: int = 5,
    ) -> List[Dict]:
        """Returns the most recent open crimes by this CHARACTER in this nation —
        used to build the bounded `criminal_record_here` block injected into
        scene prompts. NPC crimes are excluded from this view (NPCs do not get
        scene-prompt warnings about themselves)."""
        cursor = self.crimes.find(
            {
                "perpetrator_type": "character",
                "perpetrator_id": character_id,
                "nation": nation,
                "status": "open",
            },
            {"_id": 0},
        ).sort("created_at", -1)
        return await cursor.to_list(limit)

    async def mark_crime_resolved(
        self,
        crime_id: str,
        new_status: str,
        reason: str = "",
    ) -> Optional[Dict]:
        """Update one crime row to a terminal state. Also refreshes the
        aggregated bounty for the affected perpetrator × nation."""
        if new_status not in ("paid", "served", "escaped", "pardoned", "expunged", "claimed"):
            return None
        crime = await self.crimes.find_one({"id": crime_id}, {"_id": 0})
        if not crime:
            return None
        await self.crimes.update_one(
            {"id": crime_id},
            {"$set": {
                "status": new_status,
                "resolved_at": _now_iso(),
                "resolved_reason": (reason or "")[:200],
            }},
        )
        await self._refresh_bounty(
            crime.get("perpetrator_type", "character"),
            crime.get("perpetrator_id") or crime.get("character_id"),
            crime["nation"],
            crime.get("perpetrator_name") or crime.get("character_name", ""),
        )
        return await self.crimes.find_one({"id": crime_id}, {"_id": 0})

    # ---------- Bounties (aggregated per perpetrator × nation) ----------

    async def _refresh_bounty(
        self,
        perpetrator_type: str,
        perpetrator_id: str,
        nation: str,
        perpetrator_name: str = "",
    ) -> Dict:
        """Recompute the aggregated bounty row from open crimes of this
        perpetrator in this nation."""
        crimes = await self.crimes.find(
            {
                "perpetrator_type": perpetrator_type,
                "perpetrator_id": perpetrator_id,
                "nation": nation,
                "status": "open",
            },
            {"_id": 0, "bounty": 1, "severity": 1, "perpetrator_name": 1},
        ).to_list(200)
        total = sum(c.get("bounty", 0) for c in crimes)
        order = ["petty", "minor", "major", "capital", "regicide"]
        worst = "none"
        worst_idx = -1
        petty_count = 0
        for c in crimes:
            sev = c.get("severity", "petty")
            if sev in order and order.index(sev) > worst_idx:
                worst = sev
                worst_idx = order.index(sev)
            if sev == "petty":
                petty_count += 1
        if not crimes:
            worst = "none"
        # Active-warrant flag — does this perpetrator have an in-nation
        # warrant for arrest? See module-level thresholds.
        has_active_warrant = bool(
            worst in WARRANT_TRIGGER_SEVERITIES
            or (worst == "petty" and petty_count >= PETTY_WARRANT_COUNT)
        )
        # Keep perp_name fresh if caller didn't supply one
        display_name = perpetrator_name or next(
            (c.get("perpetrator_name") for c in crimes if c.get("perpetrator_name")),
            "",
        )
        update_doc = {
            "perpetrator_type": perpetrator_type,
            "perpetrator_id": perpetrator_id,
            "perpetrator_name": display_name,
            # Back-compat: keep `character_id` populated for character perpetrators.
            "character_id": perpetrator_id if perpetrator_type == "character" else None,
            "nation": nation,
            "total_bounty": total,
            "worst_severity": worst,
            "open_crime_count": len(crimes),
            "petty_count": petty_count,
            "has_active_warrant": has_active_warrant,
            "updated_at": _now_iso(),
        }
        await self.bounties.update_one(
            {
                "perpetrator_type": perpetrator_type,
                "perpetrator_id": perpetrator_id,
                "nation": nation,
            },
            {"$set": update_doc},
            upsert=True,
        )
        return update_doc

    async def get_bounty(self, character_id: str, nation: str) -> Optional[Dict]:
        return await self.bounties.find_one(
            {
                "perpetrator_type": "character",
                "perpetrator_id": character_id,
                "nation": nation,
            },
            {"_id": 0},
        )

    async def list_bounties_for_character(self, character_id: str) -> List[Dict]:
        cursor = self.bounties.find(
            {
                "perpetrator_type": "character",
                "perpetrator_id": character_id,
                "open_crime_count": {"$gt": 0},
            },
            {"_id": 0},
        ).sort("total_bounty", -1)
        return await cursor.to_list(20)

    # ---------- Public Bounty Board ----------

    async def get_bounty_board(
        self,
        nation: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Return all PUBLIC bounties sorted by total bounty (highest first).

        Visibility rules (broadened 2026-02 — minor crimes are now public so
        bounty hunters can chase petty thieves with active warrants too):
        - All NPC bounties are public (NPCs are enemies of the state).
        - Character bounties with `has_active_warrant=True` are public. That
          includes any open MINOR/MAJOR/CAPITAL/REGICIDE crime AND repeat
          petty offenders (2+ open petty crimes).
        - Back-compat: rows recorded before the 2026-02 schema migration
          don't have `has_active_warrant`. We accept them on `worst_severity`
          as a fallback so existing wanted players don't vanish from the board.
        """
        legacy_severities = ["minor", "major", "capital", "regicide"]
        q: Dict = {
            "open_crime_count": {"$gt": 0},
            "$or": [
                {"perpetrator_type": "npc"},
                {
                    "perpetrator_type": "character",
                    "has_active_warrant": True,
                },
                # Back-compat fallback — pre-2026-02 rows.
                {
                    "perpetrator_type": "character",
                    "has_active_warrant": {"$exists": False},
                    "worst_severity": {"$in": legacy_severities},
                },
            ],
        }
        if nation:
            q["nation"] = nation
        cursor = self.bounties.find(q, {"_id": 0}).sort("total_bounty", -1)
        return await cursor.to_list(limit)

    # ---------- NPC bounty claims (player hunts an NPC) ----------

    async def claim_npc_bounty(
        self,
        *,
        npc_id: str,
        nation: str,
        claimed_by_user_id: str,
        claimed_by_character_id: str,
        claimed_by_character_name: str,
        method: str = "captured",  # captured | killed
    ) -> Dict:
        """Close all open crimes of this NPC in this nation, mark them
        'claimed', and return the total payout amount. Caller credits the
        currency to the hunter. Idempotent — calling twice returns 0."""
        open_crimes = await self.crimes.find(
            {
                "perpetrator_type": "npc",
                "perpetrator_id": npc_id,
                "nation": nation,
                "status": "open",
            },
            {"_id": 0},
        ).to_list(200)
        total_payout = sum(c.get("bounty", 0) for c in open_crimes)
        for c in open_crimes:
            await self.mark_crime_resolved(
                c["id"],
                "claimed",
                reason=f"{method} by {claimed_by_character_name}",
            )
        return {
            "total_payout": total_payout,
            "crimes_closed": len(open_crimes),
            "npc_id": npc_id,
            "claimed_by_user_id": claimed_by_user_id,
            "claimed_by_character_id": claimed_by_character_id,
            "method": method,
        }

    # ---------- Character bounty claims (player hunts a player) ----------

    async def claim_character_bounty(
        self,
        *,
        target_character_id: str,
        nation: str,
        hunter_user_id: str,
        hunter_character_id: str,
        hunter_character_name: str,
        method: str = "captured",
    ) -> Dict:
        """A player hunts another player. Closes their open crimes in
        `nation`, returns payout, and (unless captured→jail) resolves the
        confrontation cleanly. Caller credits the payout to the hunter.

        Rules:
            • Cannot hunt yourself.
            • Method must be 'captured' or 'killed'.
            • Only closes crimes with `has_active_warrant=True` — nobody
              cashes in on gossip.
            • On 'killed': target character is soft-flagged
              `status='fallen'`. Their legacy is preserved in the Chronicles.
        """
        if hunter_character_id == target_character_id:
            raise ValueError("You cannot hunt your own character.")
        method = (method or "captured").strip().lower()
        if method not in ("captured", "killed"):
            raise ValueError("method must be 'captured' or 'killed'.")

        # Verify target has an active warrant in the given nation.
        warrant = await self.bounties.find_one(
            {
                "perpetrator_type": "character",
                "perpetrator_id": target_character_id,
                "nation": nation,
                "open_crime_count": {"$gt": 0},
                "has_active_warrant": True,
            },
            {"_id": 0},
        )
        if not warrant:
            raise ValueError("No active warrant for this character in this nation.")

        open_crimes = await self.crimes.find(
            {
                "perpetrator_type": "character",
                "perpetrator_id": target_character_id,
                "nation": nation,
                "status": "open",
            },
            {"_id": 0},
        ).to_list(200)
        total_payout = sum(int(c.get("bounty", 0)) for c in open_crimes)
        for c in open_crimes:
            await self.mark_crime_resolved(
                c["id"],
                "claimed",
                reason=f"{method} by hunter {hunter_character_name}",
            )

        return {
            "total_payout": total_payout,
            "crimes_closed": len(open_crimes),
            "target_character_id": target_character_id,
            "hunter_user_id": hunter_user_id,
            "hunter_character_id": hunter_character_id,
            "method": method,
            "nation": nation,
        }

    # ---------- Imprisonments ----------

    async def get_active_imprisonment(self, character_id: str) -> Optional[Dict]:
        return await self.imprisonments.find_one(
            {"character_id": character_id, "status": "active"},
            {"_id": 0},
        )

    async def imprison(
        self,
        *,
        character_id: str,
        character_name: str,
        nation: str,
        jail_location: str,
        sentence_turns: int,
        crime_ids: List[str],
        narration: str = "",
    ) -> Dict:
        """Create an active imprisonment record and mark the named crimes as
        served. Releases automatically when the character has burned through
        the sentence (decremented on each RP turn while in jail) — but that
        decrement happens elsewhere (in the imprisoned RP turn handler)."""
        # End any prior active imprisonment first — shouldn't happen, but be safe.
        existing = await self.get_active_imprisonment(character_id)
        if existing:
            await self.imprisonments.update_one(
                {"id": existing["id"]},
                {"$set": {"status": "superseded", "ended_at": _now_iso()}},
            )
        doc = {
            "id": str(uuid.uuid4()),
            "character_id": character_id,
            "character_name": character_name,
            "nation": nation,
            "jail_location": jail_location,
            "sentence_turns": max(1, int(sentence_turns)),
            "turns_served": 0,
            "status": "active",  # active | served | escaped | pardoned | executed
            "crime_ids": list(crime_ids),
            "narration": (narration or "")[:1000],
            "started_at": _now_iso(),
            "ended_at": None,
        }
        await self.imprisonments.insert_one(dict(doc))
        for cid in crime_ids:
            await self.mark_crime_resolved(cid, "served", reason="Imprisonment")
        return doc

    async def increment_turn(self, imprisonment_id: str) -> Optional[Dict]:
        """Add one turn served. If we hit the sentence, end the imprisonment.
        Called by the RP turn handler when an imprisoned character roleplays
        from inside the jail."""
        imp = await self.imprisonments.find_one({"id": imprisonment_id}, {"_id": 0})
        if not imp or imp["status"] != "active":
            return imp
        new_turns = imp["turns_served"] + 1
        if new_turns >= imp["sentence_turns"]:
            await self.imprisonments.update_one(
                {"id": imprisonment_id},
                {"$set": {
                    "status": "served",
                    "turns_served": new_turns,
                    "ended_at": _now_iso(),
                }},
            )
        else:
            await self.imprisonments.update_one(
                {"id": imprisonment_id},
                {"$set": {"turns_served": new_turns}},
            )
        return await self.imprisonments.find_one({"id": imprisonment_id}, {"_id": 0})

    async def end_imprisonment(
        self,
        imprisonment_id: str,
        new_status: str,
        reason: str = "",
    ) -> Optional[Dict]:
        if new_status not in ("served", "escaped", "pardoned", "executed"):
            return None
        await self.imprisonments.update_one(
            {"id": imprisonment_id, "status": "active"},
            {"$set": {
                "status": new_status,
                "ended_at": _now_iso(),
                "end_reason": (reason or "")[:200],
            }},
        )
        return await self.imprisonments.find_one({"id": imprisonment_id}, {"_id": 0})

    async def list_active_imprisonments(self, limit: int = 100) -> List[Dict]:
        cursor = self.imprisonments.find({"status": "active"}, {"_id": 0}).sort("started_at", -1)
        return await cursor.to_list(limit)

    # ---------- AI integration ----------

    async def apply_law_analysis(
        self,
        analysis: Dict,
        *,
        character_id: str,
        character_name: str,
        user_id: str,
        nation: str,
        location: str,
        present_npcs: Optional[List[Dict]] = None,
    ) -> Dict:
        """Read the `criminal_acts` array from `analyze_interaction()` output
        and record each one as a crime.

        Crimes may be attributed to the player OR to an NPC. The AI tags each
        act with `perpetrator: "player"` (default) or `perpetrator_npc_id`.

        Also reads `hunted_targets` — NPCs the player just captured/killed in
        this scene who had open bounties. Returns total payout for any caught
        targets so the caller can credit the user's currency.

        Returns a summary dict for downstream cascade logic.
        """
        results = {
            "crimes_recorded": 0,
            "max_severity": "none",
            "recorded": [],
            "npc_crimes_recorded": 0,
            "hunted_payouts": [],
            "total_payout": 0,
        }
        acts = analysis.get("criminal_acts") or []
        npc_lookup = {n.get("id"): n for n in (present_npcs or []) if n.get("id")}
        severity_order = ["petty", "minor", "major", "capital", "regicide"]
        max_idx = -1

        if isinstance(acts, list) and acts:
            for act in acts[:6]:  # cap to keep prompt+response bounded
                if not isinstance(act, dict):
                    continue
                crime_type = (act.get("crime_type") or "").strip()[:40]
                severity = act.get("severity") or "minor"
                if severity not in SEVERITY_TIERS:
                    severity = "minor"
                if not crime_type:
                    continue

                perpetrator_tag = (act.get("perpetrator") or "player").strip()
                if perpetrator_tag == "player" or perpetrator_tag == character_id:
                    doc = await self.record_crime(
                        character_id=character_id,
                        character_name=character_name,
                        user_id=user_id,
                        nation=nation,
                        location=location,
                        crime_type=crime_type,
                        severity=severity,
                        victim_name=(act.get("victim_name") or "").strip()[:80],
                        victim_importance=act.get("victim_importance") or "commoner",
                        description=act.get("description") or "",
                    )
                    results["crimes_recorded"] += 1
                    results["recorded"].append(doc)
                else:
                    # NPC perpetrator — must match a present NPC.
                    npc = npc_lookup.get(perpetrator_tag)
                    if not npc:
                        logger.info(f"Skipping crime with unknown perpetrator tag: {perpetrator_tag}")
                        continue
                    doc = await self.record_crime(
                        nation=nation,
                        location=location,
                        crime_type=crime_type,
                        severity=severity,
                        victim_name=(act.get("victim_name") or "").strip()[:80],
                        victim_importance=act.get("victim_importance") or "commoner",
                        description=act.get("description") or "",
                        perpetrator_type="npc",
                        perpetrator_id=perpetrator_tag,
                        perpetrator_name=npc.get("name", "Unknown NPC"),
                    )
                    results["crimes_recorded"] += 1
                    results["npc_crimes_recorded"] += 1
                    results["recorded"].append(doc)
                try:
                    idx = severity_order.index(severity)
                    if idx > max_idx:
                        max_idx = idx
                        results["max_severity"] = severity
                except ValueError:
                    pass

        # Hunted targets — player killed/captured an NPC with open bounty in this scene.
        hunted = analysis.get("hunted_targets") or []
        if isinstance(hunted, list) and hunted:
            for ht in hunted[:5]:
                if not isinstance(ht, dict):
                    continue
                npc_id = (ht.get("npc_id") or "").strip()
                if not npc_id:
                    continue
                method = (ht.get("method") or "captured").strip()
                if method not in ("captured", "killed"):
                    method = "captured"
                payout = await self.claim_npc_bounty(
                    npc_id=npc_id,
                    nation=nation,
                    claimed_by_user_id=user_id,
                    claimed_by_character_id=character_id,
                    claimed_by_character_name=character_name,
                    method=method,
                )
                if payout["total_payout"] > 0:
                    results["hunted_payouts"].append(payout)
                    results["total_payout"] += payout["total_payout"]

        return results

    @staticmethod
    def format_record_for_prompt(open_crimes: List[Dict], bounty: Optional[Dict]) -> str:
        """Build the bounded text block injected into the scene prompt so AI
        guards know exactly what this character is wanted for in this nation,
        and respond with appropriate force.

        Capped at 5 entries by the caller."""
        if not open_crimes:
            return (
                "CRIMINAL RECORD HERE: None — this character has a clean record in this nation.\n"
                "GUARD PHYSICAL-TOUCH RULE: Even with a clean record, if the player text in this "
                "turn DESCRIBES THE CHARACTER PHYSICALLY TOUCHING, GRABBING, SHOVING, STRIKING, "
                "PULLING, OR RESTRAINING A GUARD (or other lawful officer) in a tense / hostile "
                "moment, the guards present MUST audibly declare an arrest ('You're under arrest!' "
                "/ 'Hands where I can see them!' / 'Lay down your blade!') and attempt to subdue "
                "the character. T1 rules still apply — every shove, grab, or strike from a guard "
                "is an ATTEMPT, never an automatic success."
            )
        has_active_warrant = bool((bounty or {}).get("has_active_warrant"))
        lines = ["CRIMINAL RECORD HERE — guards WILL recognize and act on these:"]
        for c in open_crimes:
            victim = c.get("victim_name") or "an unnamed victim"
            lines.append(
                f"  - [{c.get('severity','minor').upper()}] {c.get('crime_type','crime')} "
                f"against {victim} ({c.get('victim_importance','commoner')}) — "
                f"bounty {c.get('bounty',0)}g. {c.get('description','')}"
            )
        if bounty:
            lines.append(
                f"  TOTAL ACTIVE BOUNTY: {bounty.get('total_bounty',0)}g "
                f"(worst severity: {bounty.get('worst_severity','minor')}). "
                f"ACTIVE WARRANT: {'YES — guards in this nation pursue on sight' if has_active_warrant else 'NO — under threshold for arrest'}."
            )
        # Severity-graded enforcement guidance for the AI.
        worst = (bounty or {}).get("worst_severity", "minor")
        lines.append("GUARD RESPONSE PROTOCOL (severity-graded):")
        lines.append(
            "  - petty (single offence): guards warn or fine; no arrest unless the character resists or escalates."
        )
        lines.append(
            "  - petty (REPEAT — 2+ open) OR minor: ACTIVE WARRANT. The FIRST guard who sees the character "
            "verbally declares the arrest ('In the name of [authority], you're under arrest for [crime]!') "
            "and produces manacles / signals reinforcements. Mild force may be used to subdue."
        )
        lines.append(
            "  - major: guards draw weapons immediately on recognition, demand surrender, and may strike to "
            "subdue. They will attempt to wound, not kill, unless the character draws on them first."
        )
        lines.append(
            "  - capital: at least ONE guard MAY attack on sight, especially if no superior "
            "is present to demand surrender. Reinforcements are summoned. The criminal MUST "
            "choose: fight, flee, or surrender. T1 rules apply — every strike is an ATTEMPT."
        )
        lines.append(
            "  - regicide: KILL ON SIGHT. No demand for surrender. Every guard present "
            "attempts a lethal strike (still T1 — outcome decided by the player's response)."
        )
        lines.append(
            f"This character's worst-severity open crime here is: {worst.upper()}. Pick guard "
            "behaviour accordingly. The criminal can ALWAYS initiate combat to break free of "
            "arrest — honour that choice and let dice/T1 narration decide the outcome."
        )
        # NEW (2026-02 overhaul): physical-touch and first-strike rules.
        lines.append("PHYSICAL-TOUCH RULE (apply REGARDLESS of severity):")
        lines.append(
            "  If the player's action text describes them GRABBING, SHOVING, STRIKING, "
            "TOUCHING, PULLING, RESTRAINING, OR THREATENING WITH A WEAPON a guard or lawful "
            "officer in a tense / charged moment, guards MUST treat this as resisting authority "
            "and IMMEDIATELY declare + attempt the arrest. Announce it audibly. Surrounding "
            "guards and bystanders MAY join in. Every guard action remains a T1 ATTEMPT."
        )
        lines.append("HOSTILE NPC FIRST-STRIKE RULE:")
        lines.append(
            "  Any NPC (guard OR civilian) whose `relationship_label` toward this character is "
            "HOSTILE (or relationship_score <= -50) MAY initiate the first attack of a confrontation. "
            "They do NOT have to wait for the player to swing first. Write it as a clear T1 attempt "
            "(approach, target, intended damage) and leave the outcome to the player's reply."
        )
        return "\n".join(lines)
