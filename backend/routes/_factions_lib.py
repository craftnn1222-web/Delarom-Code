"""Constants, Pydantic models and async helpers for the faction system.

Extracted from routes/factions.py (2026-05-31) so the endpoint file is
under a thousand lines and the data shapes can be grokked at a glance.
No behaviour changes — pure code-move with import re-export.

The public-facing surface (what other modules consume) is:
- attach_faction_routes : still in routes/factions.py
- apply_crime_to_faction : still importable from routes.factions

Everything in this module is private to the faction implementation.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field


# Rank ladder. Order matters — higher index = more authority.
RANKS = ["initiate", "member", "officer", "leader"]
RANK_LABELS = {
    "initiate": "Initiate",
    "member":   "Member",
    "officer":  "Officer",
    "leader":   "Leader",
}

# The five canonical nations of Delarom — reputation lives per (faction, nation).
NATIONS = ["ammeonon", "selindori", "dhor-kuldor", "aigraels", "veiled-realms"]

# Reputation bounds. 0 = neutral; +1000 = revered; -1000 = reviled.
REPUTATION_MIN = -1000
REPUTATION_MAX = 1000

# Severity → reputation delta when a member commits a crime in a nation.
# Vocabulary matches `law_service.SEVERITY_TIERS` (petty/minor/major/capital/regicide)
# so the hook from `record_crime` propagates without translation.
REPUTATION_CRIME_DELTA = {
    "petty":    -5,
    "minor":    -15,
    "major":    -50,
    "capital":  -150,
    "regicide": -400,
}


def _rank_index(rank: str) -> int:
    """Return the seniority index. -1 if unknown rank."""
    try:
        return RANKS.index(rank)
    except ValueError:
        return -1


def _can_manage(actor_rank: str, target_rank: str) -> bool:
    """Officers and Leaders manage members below their own rank only."""
    a = _rank_index(actor_rank)
    t = _rank_index(target_rank)
    return a >= _rank_index("officer") and a > t


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(name: str) -> str:
    """Convert a freeform faction name into a clean slug.
    Examples:
      'The Sable Order' → 'the-sable-order'
      'Wolves & Wyrms!' → 'wolves-wyrms'
    """
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:64]


# ---------------------------- Pydantic models ----------------------------


class JoinFactionBody(BaseModel):
    character_id: str
    pitch: str = Field(default="", max_length=600)


class RankChangeBody(BaseModel):
    # Required so the actor (officer/leader) identifies which of THEIR
    # characters is performing the administrative action — and we can
    # verify that character is in the same faction at the right rank.
    actor_character_id: str


class CreateFactionBody(BaseModel):
    """Admin-only: seed/create a new faction."""
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(min_length=2, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    motto: Optional[str] = Field(default="", max_length=200)
    nation_home: Optional[str] = Field(default="", max_length=64)
    color_hex: Optional[str] = Field(default="#a855f7")  # purple-500
    icon: Optional[str] = Field(default="shield")
    is_secret: bool = False  # if true, hidden from public list


class CreateThreadBody(BaseModel):
    """Faction-only forum thread. Author must be an active member."""
    character_id: str
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=1, max_length=8000)
    min_rank: str = Field(default="initiate")  # readable by initiate+; future: gated threads


class CreateThreadReplyBody(BaseModel):
    character_id: str
    content: str = Field(min_length=1, max_length=4000)


class ReputationGrantBody(BaseModel):
    """Admin-only manual adjustment to a faction's standing."""
    nation: str
    delta: int = Field(ge=-500, le=500)
    reason: Optional[str] = Field(default="", max_length=300)


class SeedLeadersBody(BaseModel):
    """Admin-only: hand out leader seats. Maps faction_slug → character_id.
    The named character must already be a member of that faction (any rank).
    """
    assignments: dict[str, str]


# ----------------------- Player-founded factions (charter system) -----------------------

# Cost to file a charter. Refunded if the application is rejected.
FACTION_CHARTER_COST_GOLD = 5000

# Valid icon set the user can pick — keeps us in lockstep with the frontend ICONS map.
ALLOWED_FACTION_ICONS = {"shield", "swords", "skull", "tree", "hammer", "crown", "scroll", "flame"}


class OfferedGoodBody(BaseModel):
    """One good a player-founded faction promises to produce at filing time.

    On charter APPROVAL, these become rows in the `faction_specialties`
    collection via `EconomyService.upsert_specialty`. Goods must already
    exist in the canonical catalogue (admin seeds them; charter cannot
    invent new goods on the fly).
    """
    good_slug: str = Field(min_length=2, max_length=64)
    base_cost: int = Field(ge=1, le=1_000_000)
    capacity: int = Field(default=50, ge=0, le=10_000)
    description: Optional[str] = Field(default="", max_length=400)


class FileCharterBody(BaseModel):
    """A player submits a charter application to found a new faction.
    A flat fee of FACTION_CHARTER_COST_GOLD is debited up-front from the
    user's wallet. Refunded if rejected; consumed if approved.
    """
    character_id: str             # The character who will become Leader on approval
    name: str = Field(min_length=3, max_length=80)
    motto: Optional[str] = Field(default="", max_length=200)
    description: str = Field(min_length=20, max_length=2000)
    nation_home: Optional[str] = Field(default="", max_length=64)
    color_hex: Optional[str] = Field(default="#a855f7", max_length=9)
    icon: Optional[str] = Field(default="shield", max_length=24)
    # NEW (2026-02-14) — player declares what the faction will produce.
    # Capped to 8 entries to keep charter applications focused.
    offered_goods: Optional[List[OfferedGoodBody]] = Field(default=None, max_length=8)


class CharterReviewBody(BaseModel):
    """Admin approves/rejects with an optional public note."""
    note: Optional[str] = Field(default="", max_length=400)
    # Optional slug override (admin may sanitise a clashing or ugly slug).
    slug_override: Optional[str] = Field(default=None, max_length=64)


# ----------------------- Round 3 — Quests / Treasury / Rivalry -----------------------


class CreateQuestBody(BaseModel):
    """Officer/leader hand-authored quest."""
    actor_character_id: str
    title: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=2, max_length=600)
    flavour: Optional[str] = Field(default="", max_length=200)
    reward_gold: int = Field(default=50, ge=0, le=5000)
    reward_reputation: int = Field(default=10, ge=0, le=200)
    max_completions: int = Field(default=5, ge=1, le=100)


class AiGenerateQuestBody(BaseModel):
    """Officer/leader triggers AI generation; the LLM fills title/objective/flavour."""
    actor_character_id: str
    reward_gold: int = Field(default=50, ge=0, le=5000)
    reward_reputation: int = Field(default=10, ge=0, le=200)
    max_completions: int = Field(default=5, ge=1, le=100)


class CompleteQuestBody(BaseModel):
    """A member self-reports completion of a quest."""
    character_id: str
    proof: str = Field(default="", max_length=600)


class DonateBody(BaseModel):
    """A member donates personal gold into the faction coffer."""
    character_id: str
    amount: int = Field(ge=1, le=100000)


class DeclareRivalryBody(BaseModel):
    """A leader formally declares rivalry against another faction."""
    actor_character_id: str
    target_slug: str
    reason: str = Field(default="", max_length=400)


class EscalateRivalryBody(BaseModel):
    """A leader escalates an existing rivalry (bumps intensity)."""
    actor_character_id: str
    delta: int = Field(default=10, ge=1, le=40)
    reason: Optional[str] = Field(default="", max_length=300)


# Rivalry intensity thresholds → status label.
RIVALRY_STATUSES = [
    (0,   "dormant"),
    (1,   "tense"),
    (25,  "declared"),
    (50,  "escalated"),
    (75,  "sworn-enemies"),
]
RIVALRY_MAX_INTENSITY = 100

# Severity → auto-rivalry intensity delta when a member of one faction
# commits a crime in the rival faction's HOME nation.
RIVALRY_CRIME_DELTA = {
    "petty":    1,
    "minor":    3,
    "major":    8,
    "capital":  15,
    "regicide": 30,
}


def _rivalry_status(intensity: int) -> str:
    label = "dormant"
    for threshold, name in RIVALRY_STATUSES:
        if intensity >= threshold:
            label = name
    return label


def _rivalry_pair(faction_id_a: str, faction_id_b: str) -> tuple[str, str]:
    """Canonical (sorted) pair so we never duplicate the same rivalry."""
    return tuple(sorted([faction_id_a, faction_id_b]))  # type: ignore


# ---------------------------- Async DB helpers ----------------------------


async def _get_faction(db, slug: str) -> dict:
    f = await db.factions.find_one({"slug": slug, "is_active": True}, {"_id": 0})
    if not f:
        raise HTTPException(status_code=404, detail="Faction not found")
    return f


async def _get_membership(db, character_id: str) -> Optional[dict]:
    """The character's CURRENT (active) membership, if any."""
    return await db.faction_memberships.find_one(
        {"character_id": character_id, "status": "active"},
        {"_id": 0},
    )


async def _refresh_member_count(db, faction_id: str) -> None:
    count = await db.faction_memberships.count_documents(
        {"faction_id": faction_id, "status": "active"}
    )
    await db.factions.update_one({"id": faction_id}, {"$set": {"member_count": count}})


async def _get_or_init_reputation(db, faction_id: str, nation: str) -> dict:
    row = await db.faction_reputation.find_one(
        {"faction_id": faction_id, "nation": nation}, {"_id": 0}
    )
    if row:
        return row
    fresh = {
        "id": str(uuid.uuid4()),
        "faction_id": faction_id,
        "nation": nation,
        "score": 0,
        "updated_at": _now_iso(),
    }
    await db.faction_reputation.insert_one(dict(fresh))
    return fresh


async def _apply_reputation_delta(
    db, faction_id: str, nation: str, delta: int, reason: str = ""
) -> dict:
    """Clamp + persist a reputation change and append a history line.
    Returns the post-update row."""
    row = await _get_or_init_reputation(db, faction_id, nation)
    new_score = max(REPUTATION_MIN, min(REPUTATION_MAX, row["score"] + delta))
    await db.faction_reputation.update_one(
        {"faction_id": faction_id, "nation": nation},
        {"$set": {"score": new_score, "updated_at": _now_iso()}},
    )
    await db.faction_reputation_history.insert_one({
        "id": str(uuid.uuid4()),
        "faction_id": faction_id,
        "nation": nation,
        "delta": delta,
        "score_after": new_score,
        "reason": (reason or "")[:300],
        "created_at": _now_iso(),
    })
    return {**row, "score": new_score, "updated_at": _now_iso()}


async def _auto_escalate_rivalries_for_crime(
    db, *, perpetrator_faction_id: str, victim_nation: str, severity: str, description: str
) -> None:
    """When a member of faction A commits a crime in nation N, any rivalry
    pair (A, B) where B.nation_home == N gets its intensity bumped. This is
    the cascade hook that makes rivalries feel alive without needing an
    explicit "rival" target — geography does the work.
    """
    rivalries = await db.faction_rivalries.find({
        "$or": [
            {"faction_a_id": perpetrator_faction_id},
            {"faction_b_id": perpetrator_faction_id},
        ],
    }, {"_id": 0}).to_list(length=None)
    if not rivalries:
        return

    delta = RIVALRY_CRIME_DELTA.get(severity, RIVALRY_CRIME_DELTA["petty"])
    for r in rivalries:
        other_id = r["faction_b_id"] if r["faction_a_id"] == perpetrator_faction_id else r["faction_a_id"]
        other = await db.factions.find_one({"id": other_id}, {"_id": 0, "nation_home": 1, "name": 1})
        if not other or (other.get("nation_home") or "") != victim_nation:
            continue
        old_intensity = (r.get("intensity", 0) or 0)
        new_intensity = min(RIVALRY_MAX_INTENSITY, old_intensity + delta)
        await db.faction_rivalries.update_one(
            {"id": r["id"]},
            {
                "$set": {
                    "intensity": new_intensity,
                    "status": _rivalry_status(new_intensity),
                    "last_escalated_at": _now_iso(),
                },
                "$push": {
                    "history": {
                        "id": str(uuid.uuid4()),
                        "delta": delta,
                        "intensity_after": new_intensity,
                        "reason": f"Crime ({severity}) on {other.get('name', 'rival')}'s soil — {description[:120]}",
                        "kind": "auto",
                        "created_at": _now_iso(),
                    },
                },
            },
        )
        # P1.5 — Economy hook: if this push crossed into actively-hostile
        # territory, break all standing contracts between the two factions.
        await _maybe_break_contracts_on_hostility(
            db,
            faction_a_id=r["faction_a_id"],
            faction_b_id=r["faction_b_id"],
            old_intensity=old_intensity,
            new_intensity=new_intensity,
            reason=f"Rivalry escalated to {_rivalry_status(new_intensity)} via {severity} crime.",
        )


# P1.5 — diplomatic / economy bridge.
# Threshold tuned to "escalated" (intensity >= 50) which is when leaders are
# openly hostile — short of full sworn-enemy war but past the cold-tension
# tier. Any subsequent escalation never re-breaks (idempotent on threshold).
HOSTILITY_BREAK_THRESHOLD = 50


async def _maybe_break_contracts_on_hostility(
    db, *,
    faction_a_id: str,
    faction_b_id: str,
    old_intensity: int,
    new_intensity: int,
    reason: str,
) -> int:
    """If the rivalry intensity FRESHLY crossed into hostile territory (i.e.
    old < threshold AND new >= threshold), break all active standing
    contracts between the two factions. Returns the count broken (0 if no
    threshold crossing).
    """
    if old_intensity >= HOSTILITY_BREAK_THRESHOLD:
        return 0  # already hostile — don't keep re-breaking on every nudge
    if new_intensity < HOSTILITY_BREAK_THRESHOLD:
        return 0
    try:
        from economy_service import EconomyService
        broken = await EconomyService(db).break_contracts_for_hostile_factions(
            faction_a_id, faction_b_id,
            reason=f"Diplomacy: {reason}",
        )
        return broken
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            f"Economy hostility-break hook failed (non-fatal): {e}"
        )
        return 0


async def apply_crime_to_faction(
    db, *, character_id: str, nation: str, severity: str, description: str = ""
) -> Optional[dict]:
    """Hook called from law_service.record_crime — if the perpetrating
    character belongs to a faction, dock that faction's reputation in the
    affected nation. No-op if the perpetrator has no active membership.

    Returns the post-update reputation row (or None)."""
    mem = await db.faction_memberships.find_one(
        {"character_id": character_id, "status": "active"}, {"_id": 0}
    )
    if not mem:
        return None
    delta = REPUTATION_CRIME_DELTA.get(severity, REPUTATION_CRIME_DELTA["petty"])
    # Round 3 — propagate crime into any active rivalries this faction holds.
    await _auto_escalate_rivalries_for_crime(
        db,
        perpetrator_faction_id=mem["faction_id"],
        victim_nation=nation,
        severity=severity,
        description=description,
    )
    return await _apply_reputation_delta(
        db,
        faction_id=mem["faction_id"],
        nation=nation,
        delta=delta,
        reason=f"Member {mem['character_name']} committed a {severity} crime. {description[:120]}".strip(),
    )
