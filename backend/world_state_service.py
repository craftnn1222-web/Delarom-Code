"""
World State Service — the Butterfly-Effect Layer
================================================
Sits on top of the persistent NPC system and propagates consequences:

* per-character reputation per nation (HIDDEN from the player)
* nation-to-nation diplomatic relations (neutral → tense → cold war → war)
* a cascade queue: high-tier NPCs spread news of slights to peers/courts
  with realistic delays
* world events: discrete, world-level happenings (royal insult, war declared,
  alliance formed)
* hostility triggers: when a character with poor local reputation acts in a
  location, roll a chance the AI introduces a T1-compliant hostile encounter
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import uuid
import random
_rng = random.SystemRandom()  # cryptographically-strong source for flavor randomness
import logging

logger = logging.getLogger(__name__)

# ============================================================
# Tier weights and bands
# ============================================================

IMPORTANCE_TIERS = ("commoner", "notable", "noble", "ruler", "monarch")
IMPORTANCE_WEIGHTS = {
    "commoner": 1,
    "notable": 2,
    "noble": 4,
    "ruler": 6,
    "monarch": 10,
}

REPUTATION_BANDS: List[Tuple[int, int, str]] = [
    (-100, -81, "wanted criminal"),
    (-80, -50, "notorious"),
    (-49, -20, "disliked"),
    (-19, 19, "unknown"),
    (20, 49, "well-regarded"),
    (50, 80, "renowned"),
    (81, 100, "revered"),
]

# Diplomatic stance derived from nation-pair score.
STANCE_BANDS: List[Tuple[int, int, str]] = [
    (-100, -71, "war"),
    (-70, -50, "cold_war"),
    (-49, -20, "tense"),
    (-19, 19, "neutral"),
    (20, 49, "friendly"),
    (50, 100, "alliance"),
]

# Cascade delivery delay ranges, in minutes (min, max).
CASCADE_DELAYS = {
    "gossip": (5, 60),          # same location, commoners hear local rumour
    "court_news": (60, 240),    # same nation, notable+ NPCs hear
    "royal_envoy": (8 * 60, 36 * 60),  # cross-nation, monarchs/rulers
}


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_dt().isoformat()


def _label_from_bands(score: int, bands: List[Tuple[int, int, str]]) -> str:
    for low, high, label in bands:
        if low <= score <= high:
            return label
    return bands[len(bands) // 2][2]


def reputation_label(score: int) -> str:
    return _label_from_bands(score, REPUTATION_BANDS)


def stance_label(score: int) -> str:
    return _label_from_bands(score, STANCE_BANDS)


def _pair_key(nation_a: str, nation_b: str) -> Tuple[str, str]:
    a, b = sorted([nation_a.strip().lower(), nation_b.strip().lower()])
    return a, b


class WorldStateService:
    """Handles everything butterfly-effect: reputation, relations, cascades, events."""

    def __init__(self, db):
        self.db = db

    # ============================================================
    # Reputation (per character, per nation, HIDDEN from player)
    # ============================================================

    async def get_reputation(self, character_id: str, nation: str) -> Dict:
        nation_key = (nation or "").strip().lower()
        rep = await self.db.character_reputation.find_one(
            {"character_id": character_id, "nation": nation_key},
            {"_id": 0},
        )
        if rep:
            return rep
        return {
            "character_id": character_id,
            "nation": nation_key,
            "score": 0,
            "label": "unknown",
            "drivers": [],
            "last_updated": None,
        }

    async def list_reputation(self, character_id: str) -> List[Dict]:
        cursor = self.db.character_reputation.find(
            {"character_id": character_id},
            {"_id": 0},
        )
        return await cursor.to_list(100)

    async def apply_reputation_delta(
        self,
        character_id: str,
        nation: str,
        delta: int,
        reason: str = "",
    ) -> Dict:
        nation_key = (nation or "").strip().lower()
        if not nation_key or delta == 0:
            return await self.get_reputation(character_id, nation_key)
        delta = max(-30, min(30, int(delta)))
        current = await self.get_reputation(character_id, nation_key)
        new_score = max(-100, min(100, current.get("score", 0) + delta))
        new_label = reputation_label(new_score)
        drivers = current.get("drivers", [])
        drivers.append({
            "at": _now_iso(),
            "delta": delta,
            "reason": (reason or "")[:200],
        })
        drivers = drivers[-25:]  # keep last 25
        update = {
            "character_id": character_id,
            "nation": nation_key,
            "score": new_score,
            "label": new_label,
            "drivers": drivers,
            "last_updated": _now_iso(),
        }
        await self.db.character_reputation.update_one(
            {"character_id": character_id, "nation": nation_key},
            {"$set": update},
            upsert=True,
        )
        return update

    # ============================================================
    # Nation-to-nation diplomatic relations
    # ============================================================

    async def get_nation_relation(self, nation_a: str, nation_b: str) -> Dict:
        a, b = _pair_key(nation_a, nation_b)
        if a == b:
            return {"nation_a": a, "nation_b": b, "score": 100, "stance": "alliance",
                    "last_event_at": None, "history": []}
        rel = await self.db.nation_relations.find_one(
            {"nation_a": a, "nation_b": b}, {"_id": 0},
        )
        if rel:
            return rel
        return {
            "nation_a": a, "nation_b": b, "score": 0, "stance": "neutral",
            "last_event_at": None, "history": [],
        }

    async def list_nation_relations(self) -> List[Dict]:
        cursor = self.db.nation_relations.find({}, {"_id": 0})
        return await cursor.to_list(200)

    async def apply_relation_delta(
        self,
        nation_a: str,
        nation_b: str,
        delta: int,
        reason: str = "",
    ) -> Dict:
        a, b = _pair_key(nation_a, nation_b)
        if a == b:
            return {"score": 100, "stance": "alliance"}
        delta = max(-40, min(40, int(delta)))
        if delta == 0:
            return await self.get_nation_relation(a, b)
        current = await self.get_nation_relation(a, b)
        previous_stance = current.get("stance", "neutral")
        new_score = max(-100, min(100, current.get("score", 0) + delta))
        new_stance = stance_label(new_score)
        history = current.get("history", [])
        history.append({
            "at": _now_iso(),
            "delta": delta,
            "reason": (reason or "")[:200],
            "new_score": new_score,
            "new_stance": new_stance,
        })
        history = history[-50:]
        update = {
            "nation_a": a, "nation_b": b,
            "score": new_score,
            "stance": new_stance,
            "last_event_at": _now_iso(),
            "history": history,
        }
        await self.db.nation_relations.update_one(
            {"nation_a": a, "nation_b": b},
            {"$set": update},
            upsert=True,
        )
        # World event on stance change
        if new_stance != previous_stance:
            await self.record_world_event({
                "event_type": f"stance_change:{new_stance}",
                "scope": "diplomatic",
                "summary": f"Relations between {a.title()} and {b.title()} shifted from {previous_stance} to {new_stance}.",
                "nations": [a, b],
                "details": reason,
            })
        return update

    async def upsert_nation_relation(self, nation_a: str, nation_b: str, score: int, reason: str = "admin") -> Dict:
        """Admin-controlled set (clamps to ±100)."""
        a, b = _pair_key(nation_a, nation_b)
        if a == b:
            return {"score": 100, "stance": "alliance"}
        new_score = max(-100, min(100, int(score)))
        new_stance = stance_label(new_score)
        await self.db.nation_relations.update_one(
            {"nation_a": a, "nation_b": b},
            {"$set": {
                "nation_a": a, "nation_b": b,
                "score": new_score, "stance": new_stance,
                "last_event_at": _now_iso(),
            }},
            upsert=True,
        )
        await self.record_world_event({
            "event_type": f"stance_change:{new_stance}",
            "scope": "diplomatic",
            "summary": f"Admin set {a.title()}/{b.title()} relations to {new_stance} ({new_score:+d}).",
            "nations": [a, b],
            "details": reason,
        })
        return await self.get_nation_relation(a, b)

    # ============================================================
    # World events
    # ============================================================

    async def record_world_event(self, data: Dict) -> Dict:
        event = {
            "id": str(uuid.uuid4()),
            "event_type": data.get("event_type", "incident"),
            "scope": data.get("scope", "world"),  # world | diplomatic | local
            "summary": (data.get("summary") or "")[:240],
            "details": (data.get("details") or "")[:1000],
            "nations": data.get("nations", []),
            "involved_npcs": data.get("involved_npcs", []),
            "involved_characters": data.get("involved_characters", []),
            "created_at": _now_iso(),
        }
        await self.db.world_events.insert_one(dict(event))
        # Economy hook — best-effort. Wars/festivals/disasters move prices.
        # Trial / crime / incident events are ignored upstream by
        # `apply_event_to_economy` via the EVENT_CATEGORY_TAGS map so the AI
        # is never queried for irrelevant events.
        try:
            from routes.economy import apply_event_to_economy
            await apply_event_to_economy(
                self.db,
                event_type=event["event_type"],
                summary=event["summary"],
                details=event["details"],
                nations=event["nations"] or [],
            )
        except Exception as econ_err:
            # Non-critical — never block the world event from being saved.
            import logging as _logging
            _logging.getLogger(__name__).warning(
                f"Economy event hook failed (non-fatal): {econ_err}"
            )
        return event

    async def list_world_events(self, limit: int = 50) -> List[Dict]:
        cursor = self.db.world_events.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    # ============================================================
    # Cascade queue
    # ============================================================

    async def enqueue_cascade(
        self,
        *,
        cascade_type: str,
        source_npc_id: Optional[str],
        source_character_id: Optional[str],
        nation_filter: Optional[str],
        location_filter: Optional[str],
        importance_min: str = "commoner",
        sentiment_delta: int = 0,
        memory_text: str = "",
        reason: str = "",
        delay_minutes: Optional[Tuple[int, int]] = None,
    ) -> Dict:
        min_delay, max_delay = delay_minutes or CASCADE_DELAYS.get(cascade_type, (15, 60))
        delay = _rng.randint(min_delay, max_delay)
        entry = {
            "id": str(uuid.uuid4()),
            "cascade_type": cascade_type,
            "source_npc_id": source_npc_id,
            "source_character_id": source_character_id,
            "nation_filter": (nation_filter or "").lower() or None,
            "location_filter": (location_filter or "").lower() or None,
            "importance_min": importance_min,
            "sentiment_delta": int(sentiment_delta),
            "memory_text": (memory_text or "")[:240],
            "reason": (reason or "")[:200],
            "status": "pending",  # pending | delivered | skipped
            "deliver_after": (_now_dt() + timedelta(minutes=delay)).isoformat(),
            "created_at": _now_iso(),
        }
        await self.db.cascade_queue.insert_one(dict(entry))
        return entry

    async def list_pending_cascades(self, nation: Optional[str] = None, location: Optional[str] = None) -> List[Dict]:
        query: Dict = {"status": "pending"}
        if nation:
            query["nation_filter"] = nation.lower()
        if location:
            query["location_filter"] = location.lower()
        cursor = self.db.cascade_queue.find(query, {"_id": 0}).sort("deliver_after", 1).limit(200)
        return await cursor.to_list(200)

    async def process_due_cascades_for_location(
        self,
        nation: str,
        location: str,
        npc_service,
    ) -> int:
        """Deliver any pending cascades that match this location/nation and are now due.

        Returns number of cascades delivered.
        """
        now_iso = _now_iso()
        query = {
            "status": "pending",
            "deliver_after": {"$lte": now_iso},
            "$or": [
                {"location_filter": location.lower()},
                {"nation_filter": nation.lower(), "location_filter": None},
            ],
        }
        due = await self.db.cascade_queue.find(query, {"_id": 0}).limit(50).to_list(50)
        delivered = 0
        for cascade in due:
            try:
                await self._deliver_cascade(cascade, nation, location, npc_service)
                await self.db.cascade_queue.update_one(
                    {"id": cascade["id"]},
                    {"$set": {"status": "delivered", "delivered_at": _now_iso()}},
                )
                delivered += 1
            except Exception as e:  # noqa: BLE001
                logger.error(f"Cascade delivery failed for {cascade.get('id')}: {e}")
                await self.db.cascade_queue.update_one(
                    {"id": cascade["id"]},
                    {"$set": {"status": "skipped", "error": str(e)[:200]}},
                )
        return delivered

    async def _deliver_cascade(self, cascade: Dict, nation: str, location: str, npc_service) -> None:
        """Apply a cascade's effects to NPCs in this location/nation."""
        source_character_id = cascade.get("source_character_id")
        sentiment_delta = cascade.get("sentiment_delta", 0)
        memory_text = cascade.get("memory_text") or cascade.get("reason") or "Heard troubling news"
        importance_min = cascade.get("importance_min", "commoner")
        min_idx = IMPORTANCE_TIERS.index(importance_min) if importance_min in IMPORTANCE_TIERS else 0

        # Find target NPCs
        query: Dict = {"nation": cascade.get("nation_filter") or nation.lower()}
        if cascade.get("location_filter"):
            query["location"] = cascade["location_filter"]
        npc_cursor = self.db.npcs.find(query, {"_id": 0}).limit(50)
        target_npcs = await npc_cursor.to_list(50)

        for npc in target_npcs:
            if npc.get("status") == "dead":
                continue
            npc_imp = npc.get("importance", "commoner")
            if IMPORTANCE_TIERS.index(npc_imp) < min_idx:
                continue
            if npc.get("id") == cascade.get("source_npc_id"):
                continue
            if not source_character_id:
                # Cascade with no specific character target — only shift global mood
                await npc_service.adjust_npc_mood(npc["id"], sentiment_delta // 2)
                continue
            # Per-character relationship update with diminished delta
            diminished = max(-8, min(8, int(sentiment_delta * 0.5)))
            char_doc = await self.db.characters.find_one(
                {"id": source_character_id}, {"_id": 0, "name": 1, "user_id": 1}
            )
            char_name = (char_doc or {}).get("name", "Unknown")
            user_id = (char_doc or {}).get("user_id", "")
            await npc_service.apply_relationship_update(
                npc["id"], source_character_id, user_id, char_name,
                diminished, memory_text,
            )
            await npc_service.adjust_npc_mood(npc["id"], diminished // 2)

    # ============================================================
    # Butterfly trigger logic
    # ============================================================

    async def schedule_butterfly_from_npc_update(
        self,
        *,
        npc: Dict,
        character_id: str,
        sentiment_delta: int,
        memory_text: str,
        character_home_nation: Optional[str],
    ) -> List[Dict]:
        """After a per-character sentiment delta with an NPC, schedule cascades
        appropriate to the NPC's importance tier, update reputation per nation,
        and shift diplomatic relations if the NPC outranks notable and the
        character is foreign.

        Returns list of created cascades + nation event summaries.
        """
        results: List[Dict] = []
        importance = npc.get("importance", "commoner")
        importance_idx = IMPORTANCE_TIERS.index(importance) if importance in IMPORTANCE_TIERS else 0
        weight = IMPORTANCE_WEIGHTS.get(importance, 1)
        nation = (npc.get("nation") or "").lower()
        location = (npc.get("location") or "").lower()
        npc_id = npc.get("id")
        home_nation = (character_home_nation or "").lower()

        # --- 1. Reputation in the NPC's nation, scaled by tier weight ---
        rep_delta = int(round(sentiment_delta * weight * 0.5))
        if rep_delta != 0 and nation:
            await self.apply_reputation_delta(
                character_id, nation, rep_delta,
                reason=memory_text or f"Interaction with {npc.get('name','an NPC')}",
            )

        # --- 2. Local gossip cascade (commoners in same location) ---
        if importance_idx >= 1 and abs(sentiment_delta) >= 3:
            casc = await self.enqueue_cascade(
                cascade_type="gossip",
                source_npc_id=npc_id,
                source_character_id=character_id,
                nation_filter=nation,
                location_filter=location,
                importance_min="commoner",
                sentiment_delta=sentiment_delta,
                memory_text=f"Heard talk: {memory_text}" if memory_text else "Local rumour circulating",
                reason="local gossip cascade",
            )
            results.append(casc)

        # --- 3. Court news (notable+ across the same nation) ---
        if importance_idx >= 2 and abs(sentiment_delta) >= 4:  # noble+ insulted
            casc = await self.enqueue_cascade(
                cascade_type="court_news",
                source_npc_id=npc_id,
                source_character_id=character_id,
                nation_filter=nation,
                location_filter=None,
                importance_min="notable",
                sentiment_delta=sentiment_delta,
                memory_text=memory_text,
                reason="court gossip cascade",
            )
            results.append(casc)

        # --- 4. Royal envoy across nations (ruler/monarch insulted by foreigner) ---
        if importance_idx >= 3 and abs(sentiment_delta) >= 5 and home_nation and home_nation != nation:
            # Diplomatic incident: degrade relations between the two nations
            relation_delta = int(round(sentiment_delta * weight * 0.4))
            if relation_delta != 0:
                await self.apply_relation_delta(
                    nation, home_nation, relation_delta,
                    reason=(
                        f"{npc.get('name','A ruler')} of {nation.title()} was "
                        f"{('insulted' if sentiment_delta < 0 else 'honoured')} by a citizen of "
                        f"{home_nation.title()}."
                    ),
                )
            # Tell allied monarchs (relations score > 20 with NPC's nation)
            allies = await self.db.nation_relations.find(
                {
                    "$or": [{"nation_a": nation}, {"nation_b": nation}],
                    "score": {"$gte": 20},
                }, {"_id": 0},
            ).to_list(20)
            allied_nations = []
            for rel in allies:
                other = rel["nation_b"] if rel["nation_a"] == nation else rel["nation_a"]
                if other not in (nation, home_nation):
                    allied_nations.append(other)
            for ally in allied_nations:
                casc = await self.enqueue_cascade(
                    cascade_type="royal_envoy",
                    source_npc_id=npc_id,
                    source_character_id=character_id,
                    nation_filter=ally,
                    location_filter=None,
                    importance_min="noble",
                    sentiment_delta=int(round(sentiment_delta * 0.5)),
                    memory_text=memory_text,
                    reason=f"royal envoy from {nation}",
                )
                results.append(casc)

            # World event
            await self.record_world_event({
                "event_type": "royal_insult" if sentiment_delta < 0 else "royal_favour",
                "scope": "diplomatic",
                "summary": (
                    f"{npc.get('name','A ruler')} ({importance}) of {nation.title()} was "
                    f"{'gravely insulted' if sentiment_delta <= -7 else 'slighted' if sentiment_delta < 0 else 'honoured'} "
                    f"by a visitor from {home_nation.title()}."
                ),
                "details": memory_text,
                "nations": [nation, home_nation],
                "involved_npcs": [npc_id],
                "involved_characters": [character_id],
            })

        return results

    # ============================================================
    # Hostility roll (T1-compliant: only injects a HINT, AI handles attempt)
    # ============================================================

    def roll_hostility_chance(self, reputation_score: int) -> int:
        """Return hostility-roll chance (0-100). Negative reputation only."""
        if reputation_score >= -29:
            return 0
        return max(0, min(75, (-reputation_score) - 30))

    async def check_hostility_trigger(self, character_id: str, location_nation: str) -> Dict:
        """Returns {triggered: bool, chance: int, reputation_label: str, reputation_score: int}.

        T1 rule: this only marks the prompt that NPCs MAY attempt hostile actions.
        Actual NPC-attack-attempts are still written by the AI as T1 attempts.
        """
        rep = await self.get_reputation(character_id, location_nation)
        score = rep.get("score", 0)
        chance = self.roll_hostility_chance(score)
        if chance <= 0:
            return {"triggered": False, "chance": 0, "reputation_label": rep.get("label", "unknown"),
                    "reputation_score": score}
        triggered = _rng.randint(1, 100) <= chance
        return {
            "triggered": triggered,
            "chance": chance,
            "reputation_label": rep.get("label", "unknown"),
            "reputation_score": score,
        }
