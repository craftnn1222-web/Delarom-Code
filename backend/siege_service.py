"""Contested Cities — Siege Service.

A faction may lay siege to a neutral city's key landmark (a `location`
row). The siege runs for a fixed in-world duration (default 7 world
days). During the siege, any character may contribute a single RP action
to the ATTACKER or DEFENDER side. When the timer expires (checked
lazily via `resolve_if_due`), the side with more contributions wins.

Outcomes:
    • **seized**   → attacker faction gains control of the location.
    • **repelled** → defender faction gains a renown boost; attacker takes
                     a small city-wide renown hit.
    • **abandoned**→ neither side rallied; nothing changes.

Rules of the game:
    • Only leaders/officers of an approved faction may declare a siege.
    • The declaration costs 500g (moves from the leader's currency into
      the void — pure sink; discourages spam).
    • Only "neutral" locations can be sieged: `controlling_faction_slug`
      must be unset or None.
    • Only one active siege per location.
    • One contribution per character per siege (no farming).
    • Contributions from the location's `city` (via nation match) are
      first-class — cross-nation contributions still count but the AI
      later can flavour them accordingly (out of scope here).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from world_calendar_service import add_world_days, get_world_calendar

logger = logging.getLogger(__name__)


STATUS_ACTIVE = "active"
STATUS_RESOLVED = "resolved"
STATUS_ABANDONED = "abandoned"

RESOLUTION_SEIZED = "seized"
RESOLUTION_REPELLED = "repelled"
RESOLUTION_ABANDONED = "abandoned"
RESOLUTION_PENDING = "pending"

SIDE_ATTACKER = "attacker"
SIDE_DEFENDER = "defender"

DECLARATION_COST = 500       # gold sink to declare a siege
DEFAULT_WORLD_DAYS = 7       # 7 in-world days ≈ 1.6 real days at 30d/7d ratio


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None


class SiegeService:
    def __init__(self, db):
        self.db = db

    # ── declaration ──────────────────────────────────────────

    async def declare_siege(
        self,
        *,
        user: Dict,
        character: Dict,
        location_id: str,
        attacker_faction_slug: str,
        duration_world_days: int = DEFAULT_WORLD_DAYS,
    ) -> Dict:
        """A faction Leader/Officer declares a siege on a neutral location.

        Raises ValueError on business errors; the routes layer maps those
        to 404/409 based on wording (see routes/siege.py::_err)."""
        duration_world_days = max(1, min(30, int(duration_world_days)))

        # ── resolve target location
        loc = await self.db.locations.find_one({"id": location_id}, {"_id": 0})
        if not loc:
            raise ValueError("Target location not found.")
        if not loc.get("is_active", True):
            raise ValueError("That location is not active in the world.")
        if loc.get("controlling_faction_slug"):
            raise ValueError(
                f"This location is already controlled by "
                f"'{loc['controlling_faction_slug']}'. Break the hold first."
            )

        # No overlapping siege
        existing = await self.db.sieges.find_one(
            {"target_location_id": location_id, "status": STATUS_ACTIVE},
            {"_id": 0},
        )
        if existing:
            raise ValueError("A siege is already active at this location.")

        # ── resolve attacker faction + membership check
        fac = await self.db.factions.find_one(
            {"slug": attacker_faction_slug, "is_active": True},
            {"_id": 0},
        )
        if not fac:
            raise ValueError("Attacking faction not found.")
        if (fac.get("status") or "approved") != "approved":
            raise ValueError("That faction is not yet approved.")

        mem = await self.db.faction_memberships.find_one(
            {"character_id": character["id"], "faction_id": fac["id"], "status": "active"},
            {"_id": 0},
        )
        if not mem:
            raise ValueError("Your character is not a member of that faction.")
        if mem.get("rank") not in ("officer", "leader"):
            raise ValueError(
                "Only an Officer or Leader of the faction may declare a siege."
            )

        # ── cost: 500g from the leader's coffers
        u = await self.db.users.find_one({"id": user["id"]}, {"_id": 0})
        if int((u or {}).get("currency", 0)) < DECLARATION_COST:
            raise ValueError(
                f"Declaring a siege requires {DECLARATION_COST}g in your coffers."
            )
        await self.db.users.update_one(
            {"id": user["id"]}, {"$inc": {"currency": -DECLARATION_COST}},
        )

        opened_at = _now_iso()
        expires_at = add_world_days(opened_at, duration_world_days)
        siege_id = str(uuid.uuid4())
        siege = {
            "id": siege_id,
            "target_location_id": location_id,
            "target_location_slug": loc.get("slug"),
            "target_location_name": loc.get("name"),
            "target_nation": loc.get("nation"),
            "target_city_slug": loc.get("city"),
            "attacker_faction_slug": attacker_faction_slug,
            "attacker_faction_name": fac.get("name"),
            "attacker_faction_id": fac["id"],
            "defender_faction_slug": None,
            "defender_faction_name": None,
            "defender_faction_id": None,
            "declared_by_user_id": user["id"],
            "declared_by_character_id": character["id"],
            "declared_by_character_name": character.get("name"),
            "status": STATUS_ACTIVE,
            "resolution": RESOLUTION_PENDING,
            "duration_world_days": duration_world_days,
            "opened_at": opened_at,
            "expires_at": expires_at,
            "resolved_at": None,
            "attacker_contribution_count": 0,
            "defender_contribution_count": 0,
            "contributor_character_ids": [],   # dedupe list
            "world_date_opened": get_world_calendar()["compact"],
        }
        await self.db.sieges.insert_one(dict(siege))

        # Mark the location as under siege so any subsequent reads can render a banner
        await self.db.locations.update_one(
            {"id": location_id},
            {"$set": {
                "siege_state": {
                    "siege_id": siege_id,
                    "attacker_faction_slug": attacker_faction_slug,
                    "attacker_faction_name": fac.get("name"),
                    "opened_at": opened_at,
                    "expires_at": expires_at,
                    "status": STATUS_ACTIVE,
                },
            }},
        )
        return siege

    # ── defence / counter-claim ──────────────────────────────

    async def counter_claim(
        self,
        *,
        user: Dict,
        character: Dict,
        siege_id: str,
        defender_faction_slug: str,
    ) -> Dict:
        """A defending faction claims itself as the defender.

        Costs no gold but requires the character to be an Officer/Leader
        of the defending faction and that no defender has been claimed
        yet. First-past-the-post — later claims are rejected.
        """
        siege = await self._require_active(siege_id)
        if siege.get("defender_faction_slug"):
            raise ValueError(
                f"'{siege['defender_faction_name']}' has already answered the siege."
            )
        if defender_faction_slug == siege["attacker_faction_slug"]:
            raise ValueError("A faction cannot defend against itself.")

        fac = await self.db.factions.find_one(
            {"slug": defender_faction_slug, "is_active": True},
            {"_id": 0},
        )
        if not fac:
            raise ValueError("Defending faction not found.")

        mem = await self.db.faction_memberships.find_one(
            {"character_id": character["id"], "faction_id": fac["id"], "status": "active"},
            {"_id": 0},
        )
        if not mem:
            raise ValueError("Your character is not a member of that faction.")
        if mem.get("rank") not in ("officer", "leader"):
            raise ValueError(
                "Only an Officer or Leader of the defending faction may answer a siege."
            )

        await self.db.sieges.update_one(
            {"id": siege_id},
            {"$set": {
                "defender_faction_slug": defender_faction_slug,
                "defender_faction_name": fac.get("name"),
                "defender_faction_id": fac["id"],
                "answered_at": _now_iso(),
                "answered_by_character_id": character["id"],
                "answered_by_character_name": character.get("name"),
            }},
        )
        return await self.get(siege_id)

    # ── contributions ────────────────────────────────────────

    async def contribute(
        self,
        *,
        user: Dict,
        character: Dict,
        siege_id: str,
        side: str,
        action_text: str,
    ) -> Dict:
        """Log a single RP contribution to one side of the siege.

        One contribution per character per siege (dedupe by character_id).
        """
        side = (side or "").strip().lower()
        if side not in (SIDE_ATTACKER, SIDE_DEFENDER):
            raise ValueError(f"side must be '{SIDE_ATTACKER}' or '{SIDE_DEFENDER}'.")
        action_text = (action_text or "").strip()
        if len(action_text) < 20:
            raise ValueError("Contribution must be at least 20 characters of RP.")
        if len(action_text) > 2000:
            raise ValueError("Contribution capped at 2000 characters.")

        siege = await self._require_active(siege_id)

        # Auto-resolve expired sieges rather than accept a stale contribution
        expires = _dt(siege.get("expires_at"))
        if expires and datetime.now(timezone.utc) >= expires:
            await self.resolve_if_due(siege_id)
            raise ValueError("This siege has already run its course — check the outcome.")

        # No dupes
        if character["id"] in (siege.get("contributor_character_ids") or []):
            raise ValueError("Your character has already committed to this siege.")

        contrib_id = str(uuid.uuid4())
        contribution = {
            "id": contrib_id,
            "siege_id": siege_id,
            "side": side,
            "character_id": character["id"],
            "character_name": character.get("name"),
            "user_id": user["id"],
            "action_text": action_text,
            "at": _now_iso(),
            "world_date": get_world_calendar()["compact"],
        }
        await self.db.siege_contributions.insert_one(dict(contribution))

        inc_field = (
            "attacker_contribution_count" if side == SIDE_ATTACKER
            else "defender_contribution_count"
        )
        await self.db.sieges.update_one(
            {"id": siege_id},
            {
                "$inc": {inc_field: 1},
                "$push": {"contributor_character_ids": character["id"]},
            },
        )
        return {
            "contribution": contribution,
            "siege": await self.get(siege_id),
        }

    # ── resolution ───────────────────────────────────────────

    async def resolve_if_due(self, siege_id: str) -> Dict:
        """If the siege expiry has passed, resolve it. Otherwise no-op.

        Called lazily from reads + POSTs. A cron-style loop can call
        `sweep_due()` to force-resolve everything past expiry."""
        siege = await self.db.sieges.find_one({"id": siege_id}, {"_id": 0})
        if not siege:
            raise ValueError("Siege not found.")
        if siege["status"] != STATUS_ACTIVE:
            return siege
        expires = _dt(siege.get("expires_at"))
        if not expires or datetime.now(timezone.utc) < expires:
            return siege
        return await self._resolve_now(siege)

    async def force_resolve(self, siege_id: str) -> Dict:
        """Admin/testing helper — resolve immediately regardless of expiry."""
        siege = await self.db.sieges.find_one({"id": siege_id}, {"_id": 0})
        if not siege:
            raise ValueError("Siege not found.")
        if siege["status"] != STATUS_ACTIVE:
            return siege
        return await self._resolve_now(siege)

    async def _resolve_now(self, siege: Dict) -> Dict:
        att = int(siege.get("attacker_contribution_count") or 0)
        dfn = int(siege.get("defender_contribution_count") or 0)

        if att == 0 and dfn == 0:
            resolution = RESOLUTION_ABANDONED
            status = STATUS_ABANDONED
            winner_side = None
        elif att > dfn or (att == dfn and att > 0):
            # Tie -> attacker takes the initiative (aggressor's edge)
            resolution = RESOLUTION_SEIZED
            status = STATUS_RESOLVED
            winner_side = SIDE_ATTACKER
        else:
            resolution = RESOLUTION_REPELLED
            status = STATUS_RESOLVED
            winner_side = SIDE_DEFENDER

        resolved_at = _now_iso()
        await self.db.sieges.update_one(
            {"id": siege["id"]},
            {"$set": {
                "status": status,
                "resolution": resolution,
                "resolved_at": resolved_at,
                "winner_side": winner_side,
                "world_date_resolved": get_world_calendar()["compact"],
                "final_attacker_count": att,
                "final_defender_count": dfn,
            }},
        )

        # Apply the resolution to the world
        loc_update: Dict = {}
        if resolution == RESOLUTION_SEIZED:
            loc_update = {
                "controlling_faction_slug": siege["attacker_faction_slug"],
                "controlling_faction_name": siege["attacker_faction_name"],
                "seized_at": resolved_at,
                "seized_from": None,          # was neutral
                "siege_state": None,
            }
            await self._apply_rep_swing(
                faction_slug=siege["attacker_faction_slug"],
                delta_own=+10,
                loser_slug=siege.get("defender_faction_slug"),
                delta_loser=-5,
                city_slug=siege.get("target_city_slug") or "",
            )
        elif resolution == RESOLUTION_REPELLED:
            loc_update = {"siege_state": None}
            await self._apply_rep_swing(
                faction_slug=siege.get("defender_faction_slug"),
                delta_own=+10,
                loser_slug=siege["attacker_faction_slug"],
                delta_loser=-5,
                city_slug=siege.get("target_city_slug") or "",
            )
        else:
            loc_update = {"siege_state": None}

        if loc_update:
            await self.db.locations.update_one(
                {"id": siege["target_location_id"]}, {"$set": loc_update},
            )

        return await self.get(siege["id"])

    async def _apply_rep_swing(
        self,
        *,
        faction_slug: Optional[str],
        delta_own: int,
        loser_slug: Optional[str],
        delta_loser: int,
        city_slug: str,
    ) -> None:
        """Nudge faction reputations city-wide. Best-effort; won't break
        resolution if the reputation collection has a hiccup."""
        try:
            from routes._factions_lib import _apply_reputation_delta
        except Exception as e:                       # pragma: no cover
            logger.warning(f"faction lib import failed: {e}")
            return
        if faction_slug:
            fac = await self.db.factions.find_one({"slug": faction_slug}, {"_id": 0, "id": 1})
            if fac:
                try:
                    for nation in (await self._nations_for_city(city_slug)):
                        await _apply_reputation_delta(
                            self.db, fac["id"], nation, delta_own,
                            reason=f"Siege outcome at {city_slug}",
                        )
                except Exception as e:                # pragma: no cover
                    logger.warning(f"rep swing (own) failed: {e}")
        if loser_slug:
            fac2 = await self.db.factions.find_one({"slug": loser_slug}, {"_id": 0, "id": 1})
            if fac2:
                try:
                    for nation in (await self._nations_for_city(city_slug)):
                        await _apply_reputation_delta(
                            self.db, fac2["id"], nation, delta_loser,
                            reason=f"Siege outcome at {city_slug}",
                        )
                except Exception as e:                # pragma: no cover
                    logger.warning(f"rep swing (loser) failed: {e}")

    async def _nations_for_city(self, city_slug: str) -> List[str]:
        if not city_slug:
            return []
        row = await self.db.cities.find_one({"slug": city_slug}, {"_id": 0, "nation": 1})
        return [row["nation"]] if row and row.get("nation") else []

    # ── reads ────────────────────────────────────────────────

    async def get(self, siege_id: str) -> Optional[Dict]:
        row = await self.db.sieges.find_one({"id": siege_id}, {"_id": 0})
        return row

    async def list_active(self) -> List[Dict]:
        rows = await self.db.sieges.find(
            {"status": STATUS_ACTIVE}, {"_id": 0},
        ).sort("opened_at", -1).to_list(200)
        # Auto-resolve any that have quietly passed expiry
        now = datetime.now(timezone.utc)
        out: List[Dict] = []
        for r in rows:
            expires = _dt(r.get("expires_at"))
            if expires and now >= expires:
                r = await self._resolve_now(r)
                if r["status"] == STATUS_ACTIVE:
                    out.append(r)          # (unlikely, but guard anyway)
            else:
                out.append(r)
        return out

    async def list_recent(self, limit: int = 50) -> List[Dict]:
        return await self.db.sieges.find({}, {"_id": 0}).sort(
            "opened_at", -1,
        ).limit(max(1, min(200, limit))).to_list(limit)

    async def list_contributions(self, siege_id: str) -> List[Dict]:
        return await self.db.siege_contributions.find(
            {"siege_id": siege_id}, {"_id": 0},
        ).sort("at", 1).to_list(500)

    async def sweep_due(self) -> Dict:
        """Resolve every siege whose expiry has passed. Suitable for a
        background tick loop."""
        now = datetime.now(timezone.utc)
        due = await self.db.sieges.find(
            {"status": STATUS_ACTIVE}, {"_id": 0},
        ).to_list(500)
        resolved = 0
        for s in due:
            expires = _dt(s.get("expires_at"))
            if expires and now >= expires:
                await self._resolve_now(s)
                resolved += 1
        return {"scanned": len(due), "resolved": resolved}

    async def _require_active(self, siege_id: str) -> Dict:
        s = await self.db.sieges.find_one({"id": siege_id}, {"_id": 0})
        if not s:
            raise ValueError("Siege not found.")
        if s["status"] != STATUS_ACTIVE:
            raise ValueError(
                f"This siege is already {s['status']} — no further actions accepted."
            )
        return s
