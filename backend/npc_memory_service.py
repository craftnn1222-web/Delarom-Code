"""
NPC Memory & Location State Service
====================================
Persistent NPCs that remember each character individually,
shared environmental events across all members in a location,
and AI-driven sentiment / event extraction after each roleplay action.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

# ---------- Mood / relationship labels ----------

MOOD_BANDS = [
    (-100, -60, "enraged"),
    (-59, -25, "angry"),
    (-24, -10, "irritated"),
    (-9, 9, "neutral"),
    (10, 24, "amiable"),
    (25, 59, "cheerful"),
    (60, 100, "elated"),
]

RELATIONSHIP_BANDS = [
    (-100, -60, "sworn enemy"),
    (-59, -25, "hostile"),
    (-24, -10, "wary"),
    (-9, 9, "stranger"),
    (10, 24, "acquaintance"),
    (25, 59, "friend"),
    (60, 100, "trusted ally"),
]

EVENT_DECAY_HOURS = {
    "mild": 1,
    "moderate": 4,
    "severe": 12,
    "epic": 48,
}

MAX_MEMORIES_PER_RELATIONSHIP = 8

# Hard cap on how many companions a single character may travel with at once.
# Keeps the AI prompt focused and prevents a runaway entourage.
MAX_COMPANIONS_PER_CHARACTER = 4


def _label_from_bands(score: int, bands: List[Tuple[int, int, str]]) -> str:
    for low, high, label in bands:
        if low <= score <= high:
            return label
    return bands[len(bands) // 2][2]


def mood_label(score: int) -> str:
    return _label_from_bands(score, MOOD_BANDS)


def relationship_label(score: int) -> str:
    return _label_from_bands(score, RELATIONSHIP_BANDS)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# Persistent NPCs
# ============================================================

class NPCMemoryService:
    """All persistence and orchestration around NPCs, relationships and events."""

    def __init__(self, db):
        self.db = db

    # ---------- NPC CRUD ----------

    async def list_npcs(
        self,
        nation: str,
        location: str,
        character_id: Optional[str] = None,
    ) -> List[Dict]:
        """Return NPCs physically present at (nation, location).

        If `character_id` is provided, ALSO include any NPCs currently bonded as
        the character's companions (regardless of their stored location).
        Companions follow the character wherever they go.
        """
        base_query = {"nation": nation, "location": location}
        if character_id:
            query: Dict = {
                "$or": [
                    base_query,
                    {"companion_of": character_id},
                ]
            }
        else:
            query = base_query
        cursor = self.db.npcs.find(query, {"_id": 0}).sort("created_at", 1)
        return await cursor.to_list(200)

    async def get_npc(self, npc_id: str) -> Optional[Dict]:
        return await self.db.npcs.find_one({"id": npc_id}, {"_id": 0})

    async def create_npc(self, data: Dict, *, is_admin_seeded: bool = False, created_by: str = "auto") -> Dict:
        importance = data.get("importance", "commoner")
        if importance not in ("commoner", "notable", "noble", "ruler", "monarch"):
            importance = "commoner"
        npc = {
            "id": str(uuid.uuid4()),
            "name": data.get("name", "Unnamed Stranger"),
            "race": data.get("race", "Unknown"),
            "role": data.get("role", "Local"),
            "nation": data.get("nation", ""),
            "location": data.get("location", ""),
            "appearance": data.get("appearance", ""),
            "personality": data.get("personality", ""),
            "motivation": data.get("motivation", ""),
            "background": data.get("background", ""),
            "quirks": data.get("quirks", ""),
            "importance": importance,
            "overall_mood": data.get("overall_mood", "neutral"),
            "mood_score": int(data.get("mood_score", 0)),
            "status": data.get("status", "alive"),  # alive | wounded | dead | fled | missing
            "status_note": data.get("status_note", ""),
            "companion_of": data.get("companion_of", None),  # character_id when bonded as a companion
            "created_by_character_id": data.get("created_by_character_id", None),  # set when player creates a custom companion
            "is_admin_seeded": is_admin_seeded,
            "created_by": created_by,
            "created_at": _now_iso(),
            "last_seen_at": _now_iso(),
        }
        await self.db.npcs.insert_one(dict(npc))
        return npc

    async def update_npc(self, npc_id: str, updates: Dict) -> Optional[Dict]:
        allowed = {
            "name", "race", "role", "appearance", "personality", "motivation",
            "background", "quirks", "overall_mood", "mood_score", "status",
            "status_note", "importance", "image_id",
        }
        set_fields = {k: v for k, v in updates.items() if k in allowed}
        if not set_fields:
            return await self.get_npc(npc_id)
        if "importance" in set_fields and set_fields["importance"] not in (
            "commoner", "notable", "noble", "ruler", "monarch"
        ):
            set_fields.pop("importance")
        if "mood_score" in set_fields:
            set_fields["mood_score"] = max(-100, min(100, int(set_fields["mood_score"])))
            set_fields["overall_mood"] = mood_label(set_fields["mood_score"])
        set_fields["last_seen_at"] = _now_iso()
        await self.db.npcs.update_one({"id": npc_id}, {"$set": set_fields})
        return await self.get_npc(npc_id)

    async def delete_npc(self, npc_id: str) -> bool:
        result = await self.db.npcs.delete_one({"id": npc_id})
        await self.db.npc_relationships.delete_many({"npc_id": npc_id})
        return result.deleted_count > 0

    async def reset_npc_memories(self, npc_id: str) -> None:
        """Clears all per-character relationships and resets overall mood to neutral."""
        await self.db.npc_relationships.delete_many({"npc_id": npc_id})
        await self.db.npcs.update_one(
            {"id": npc_id},
            {"$set": {"mood_score": 0, "overall_mood": "neutral", "last_seen_at": _now_iso()}},
        )

    # ---------- Relationships ----------

    async def get_relationship(self, npc_id: str, character_id: str) -> Optional[Dict]:
        return await self.db.npc_relationships.find_one(
            {"npc_id": npc_id, "character_id": character_id},
            {"_id": 0},
        )

    async def list_relationships_for_npc(self, npc_id: str) -> List[Dict]:
        cursor = self.db.npc_relationships.find({"npc_id": npc_id}, {"_id": 0}).sort("last_interaction_at", -1)
        return await cursor.to_list(500)

    async def _ensure_relationship(
        self, npc_id: str, character_id: str, user_id: str, character_name: str
    ) -> Dict:
        existing = await self.get_relationship(npc_id, character_id)
        if existing:
            return existing
        rel = {
            "id": str(uuid.uuid4()),
            "npc_id": npc_id,
            "character_id": character_id,
            "character_name": character_name,
            "user_id": user_id,
            "relationship_score": 0,
            "relationship_label": "stranger",
            "memories": [],
            "interaction_count": 0,
            "last_interaction_at": _now_iso(),
            "created_at": _now_iso(),
        }
        await self.db.npc_relationships.insert_one(dict(rel))
        return rel

    async def apply_relationship_update(
        self,
        npc_id: str,
        character_id: str,
        user_id: str,
        character_name: str,
        sentiment_delta: int,
        memory_text: Optional[str],
    ) -> Dict:
        """Adjusts relationship score and appends a memory if provided."""
        sentiment_delta = max(-15, min(15, int(sentiment_delta)))
        rel = await self._ensure_relationship(npc_id, character_id, user_id, character_name)
        new_score = max(-100, min(100, rel["relationship_score"] + sentiment_delta))
        new_label = relationship_label(new_score)

        memories = rel.get("memories", [])
        if memory_text and memory_text.strip():
            memories.append({
                "text": memory_text.strip()[:280],
                "at": _now_iso(),
                "sentiment": sentiment_delta,
            })
            memories = memories[-MAX_MEMORIES_PER_RELATIONSHIP:]

        await self.db.npc_relationships.update_one(
            {"id": rel["id"]},
            {"$set": {
                "relationship_score": new_score,
                "relationship_label": new_label,
                "memories": memories,
                "interaction_count": rel.get("interaction_count", 0) + 1,
                "last_interaction_at": _now_iso(),
                "character_name": character_name,
            }},
        )
        rel["relationship_score"] = new_score
        rel["relationship_label"] = new_label
        rel["memories"] = memories
        return rel

    async def adjust_npc_mood(self, npc_id: str, delta: int) -> None:
        """Smaller global mood shift derived from a per-character interaction."""
        delta = max(-10, min(10, int(delta)))
        npc = await self.get_npc(npc_id)
        if not npc:
            return
        # Damp global mood shift to half the per-character impact
        shift = delta // 2 if abs(delta) > 1 else delta
        new_score = max(-100, min(100, npc.get("mood_score", 0) + shift))
        await self.db.npcs.update_one(
            {"id": npc_id},
            {"$set": {
                "mood_score": new_score,
                "overall_mood": mood_label(new_score),
                "last_seen_at": _now_iso(),
            }},
        )

    # ---------- Companions ----------

    async def list_companions(self, character_id: str) -> List[Dict]:
        """List all NPCs currently bonded as companions of the given character."""
        cursor = self.db.npcs.find(
            {"companion_of": character_id},
            {"_id": 0},
        ).sort("last_seen_at", -1)
        return await cursor.to_list(20)

    async def count_companions(self, character_id: str) -> int:
        return await self.db.npcs.count_documents({"companion_of": character_id})

    async def bond_companion(self, npc_id: str, character_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Make `npc_id` a companion of `character_id`.

        Returns (success, message, npc_after). Refuses if:
        - NPC doesn't exist
        - NPC is dead / fled / missing
        - NPC is already a companion of a different character
        - Character already has MAX_COMPANIONS_PER_CHARACTER companions
        """
        npc = await self.get_npc(npc_id)
        if not npc:
            return False, "NPC not found.", None
        if npc.get("status") in ("dead", "fled", "missing"):
            return False, f"{npc.get('name', 'That NPC')} cannot join you — they are {npc.get('status')}.", None
        existing_owner = npc.get("companion_of")
        if existing_owner and existing_owner != character_id:
            return False, f"{npc.get('name', 'That NPC')} is already traveling with someone else.", None
        if existing_owner == character_id:
            return True, f"{npc.get('name', 'They')} are already with you.", npc
        current_count = await self.count_companions(character_id)
        if current_count >= MAX_COMPANIONS_PER_CHARACTER:
            return False, (
                f"Your party is full (max {MAX_COMPANIONS_PER_CHARACTER} companions). "
                f"Dismiss someone first."
            ), None

        await self.db.npcs.update_one(
            {"id": npc_id},
            {"$set": {
                "companion_of": character_id,
                "last_seen_at": _now_iso(),
            }},
        )
        npc["companion_of"] = character_id
        return True, f"{npc.get('name', 'They')} now travel with you.", npc

    async def dismiss_companion(self, npc_id: str, character_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Release a companion. The NPC returns to their original (stored) location.

        Only the bonded character may dismiss their own companion.
        """
        npc = await self.get_npc(npc_id)
        if not npc:
            return False, "NPC not found.", None
        if npc.get("companion_of") != character_id:
            return False, "That NPC is not your companion.", None

        await self.db.npcs.update_one(
            {"id": npc_id},
            {"$set": {
                "companion_of": None,
                "last_seen_at": _now_iso(),
            }},
        )
        npc["companion_of"] = None
        return True, f"{npc.get('name', 'They')} part ways with you.", npc

    # ---------- Player-owned (preset) companions ----------

    async def list_owned_npcs(self, character_id: str) -> List[Dict]:
        """List custom NPCs the player created for this character (preset companions)."""
        cursor = self.db.npcs.find(
            {"created_by_character_id": character_id},
            {"_id": 0},
        ).sort("created_at", 1)
        docs = await cursor.to_list(50)
        # Surface a render-ready image_url alongside the stored image_id.
        for d in docs:
            if d.get("image_id"):
                d["image_url"] = f"/api/image/{d['image_id']}"
        return docs

    async def create_owned_npc(
        self,
        character_id: str,
        user_id: str,
        data: Dict,
        *,
        home_nation: str = "",
        home_location: str = "",
        auto_bond: bool = True,
    ) -> Dict:
        """Create a player-managed NPC tied to a character.

        - Stored as a regular NPC document with `created_by_character_id` set.
        - If `auto_bond=True`, the new NPC is immediately bonded as a companion
          so they appear in every scene the character visits.
        - `home_nation`/`home_location` default to the character's home if known
          and form the fallback location the NPC returns to if dismissed.
        """
        payload = dict(data)
        payload["created_by_character_id"] = character_id
        payload["created_by"] = user_id
        # Default the NPC's "home" to the character's home nation if the player
        # didn't pick a location. This is where they conceptually live when dismissed.
        payload["nation"] = data.get("nation") or home_nation or ""
        payload["location"] = data.get("location") or home_location or ""
        # Pre-bond so the NPC follows immediately. Players can dismiss anytime.
        if auto_bond:
            payload["companion_of"] = character_id

        npc = await self.create_npc(payload, is_admin_seeded=False, created_by=user_id)
        return npc

    async def update_owned_npc(
        self,
        npc_id: str,
        character_id: str,
        updates: Dict,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Update a player-owned NPC. Only the owning character may edit it."""
        npc = await self.get_npc(npc_id)
        if not npc:
            return False, "NPC not found.", None
        if npc.get("created_by_character_id") != character_id:
            return False, "You do not own this NPC.", None
        updated = await self.update_npc(npc_id, updates)
        return True, "Companion updated.", updated

    async def delete_owned_npc(
        self,
        npc_id: str,
        character_id: str,
    ) -> Tuple[bool, str]:
        """Delete a player-owned NPC. Only the owning character may delete it."""
        npc = await self.get_npc(npc_id)
        if not npc:
            return False, "NPC not found."
        if npc.get("created_by_character_id") != character_id:
            return False, "You do not own this NPC."
        await self.delete_npc(npc_id)
        return True, "Companion released."

    # ---------- Location Events ----------

    async def list_active_events(self, nation: str, location: str) -> List[Dict]:
        """Returns active events, auto-decaying any that have expired."""
        now = _now_dt()
        cursor = self.db.location_events.find(
            {"nation": nation, "location": location, "status": "active"},
            {"_id": 0},
        ).sort("started_at", -1)
        events = await cursor.to_list(50)

        active: List[Dict] = []
        for ev in events:
            expires_at_str = ev.get("expires_at")
            expired = False
            if expires_at_str:
                try:
                    expires_dt = datetime.fromisoformat(expires_at_str)
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                    if expires_dt < now:
                        expired = True
                except (ValueError, TypeError):
                    pass
            if expired:
                await self.db.location_events.update_one(
                    {"id": ev["id"]},
                    {"$set": {"status": "decayed", "resolved_at": _now_iso()}},
                )
            else:
                active.append(ev)
        return active

    async def list_all_events(self, nation: str, location: str, limit: int = 50) -> List[Dict]:
        cursor = self.db.location_events.find(
            {"nation": nation, "location": location},
            {"_id": 0},
        ).sort("started_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def create_event(self, data: Dict, *, created_by: str = "ai") -> Dict:
        intensity = data.get("intensity", "moderate")
        hours = EVENT_DECAY_HOURS.get(intensity, 4)
        event = {
            "id": str(uuid.uuid4()),
            "nation": data.get("nation", ""),
            "location": data.get("location", ""),
            "event_type": data.get("event_type", "incident"),
            "summary": data.get("summary", "Something is happening here.")[:200],
            "description": data.get("description", "")[:1200],
            "participants": data.get("participants", []),
            "npc_participants": data.get("npc_participants", []),
            "intensity": intensity,
            "status": "active",
            "started_at": _now_iso(),
            "expires_at": (_now_dt() + timedelta(hours=hours)).isoformat(),
            "resolved_at": None,
            "resolution_note": None,
            "created_by": created_by,
        }
        await self.db.location_events.insert_one(dict(event))
        return event

    async def update_event_status(
        self, event_id: str, status: str, resolution_note: Optional[str] = None
    ) -> Optional[Dict]:
        if status not in ("active", "resolved", "decayed"):
            return None
        update = {"status": status}
        if status != "active":
            update["resolved_at"] = _now_iso()
        if resolution_note:
            update["resolution_note"] = resolution_note[:400]
        await self.db.location_events.update_one({"id": event_id}, {"$set": update})
        return await self.db.location_events.find_one({"id": event_id}, {"_id": 0})

    async def delete_event(self, event_id: str) -> bool:
        result = await self.db.location_events.delete_one({"id": event_id})
        return result.deleted_count > 0

    # ---------- Scene assembly for prompts ----------

    async def build_scene_state(
        self, nation: str, location: str, character_id: str
    ) -> Dict:
        """Returns a structured dict the AI prompt can consume:
        {
          'npcs': [ {id, name, race, role, mood, status, relationship_score,
                     relationship_label, recent_memories: [text...],
                     is_companion: bool}, ... ],
          'events': [ {summary, description, intensity, started_at}, ... ]
        }
        """
        # character_id-aware listing so companions show up wherever the player goes
        npcs = await self.list_npcs(nation, location, character_id=character_id)
        events = await self.list_active_events(nation, location)

        # Look up open bounties for any NPCs in the scene so the AI prompt can
        # flag them as wanted. Single query bounded by the number of NPCs in scene.
        npc_ids_in_scene = [npc["id"] for npc in npcs if npc.get("id")]
        npc_bounty_lookup: Dict[str, int] = {}
        npc_worst_severity_lookup: Dict[str, str] = {}
        if npc_ids_in_scene:
            cursor = self.db.bounties.find(
                {
                    "perpetrator_type": "npc",
                    "perpetrator_id": {"$in": npc_ids_in_scene},
                    "nation": nation,
                    "open_crime_count": {"$gt": 0},
                },
                {"_id": 0, "perpetrator_id": 1, "total_bounty": 1, "worst_severity": 1},
            )
            async for b in cursor:
                npc_bounty_lookup[b["perpetrator_id"]] = b.get("total_bounty", 0)
                npc_worst_severity_lookup[b["perpetrator_id"]] = b.get("worst_severity", "minor")

        enriched_npcs: List[Dict] = []
        for npc in npcs:
            if npc.get("status") in ("dead",):
                # Dead NPCs are NOT presented as present, but the AI may reference them in history.
                continue
            rel = await self.get_relationship(npc["id"], character_id)
            memories: List[str] = []
            rel_score = 0
            rel_label = "stranger"
            if rel:
                rel_score = rel.get("relationship_score", 0)
                rel_label = rel.get("relationship_label", "stranger")
                memories = [m["text"] for m in rel.get("memories", [])[-4:]]
            enriched_npcs.append({
                "id": npc["id"],
                "name": npc["name"],
                "race": npc.get("race", ""),
                "role": npc.get("role", ""),
                "appearance": npc.get("appearance", ""),
                "personality": npc.get("personality", ""),
                "motivation": npc.get("motivation", ""),
                "importance": npc.get("importance", "commoner"),
                "mood_score": npc.get("mood_score", 0),
                "overall_mood": npc.get("overall_mood", "neutral"),
                "status": npc.get("status", "alive"),
                "status_note": npc.get("status_note", ""),
                "relationship_score": rel_score,
                "relationship_label": rel_label,
                "recent_memories": memories,
                "is_companion": npc.get("companion_of") == character_id,
                "image_url": (f"/api/image/{npc['image_id']}" if npc.get("image_id") else None),
                "open_bounty": npc_bounty_lookup.get(npc["id"], 0),
                "open_bounty_severity": npc_worst_severity_lookup.get(npc["id"], "none"),
            })
        return {"npcs": enriched_npcs, "events": events}

    # ---------- Applying AI analysis output ----------

    async def apply_analysis(
        self,
        *,
        analysis: Dict,
        nation: str,
        location: str,
        character_id: str,
        user_id: str,
        character_name: str,
    ) -> Dict:
        """Persist an analysis dict produced by QuestMasterAI.analyze_interaction.

        Expected schema:
        {
          'npc_updates': [{npc_id, sentiment_delta, memory, status?, status_note?}],
          'new_npcs': [{name, race, role, appearance, personality, motivation, ...,
                        sentiment_delta?, memory?}],
          'new_events': [{event_type, summary, description, intensity, participants?}],
          'event_updates': [{event_id, status, resolution_note?}]
        }
        """
        results = {"npc_updates": 0, "new_npcs": 0, "new_events": 0, "event_updates": 0}

        for upd in analysis.get("npc_updates", []) or []:
            npc_id = upd.get("npc_id")
            if not npc_id:
                continue
            npc = await self.get_npc(npc_id)
            if not npc:
                continue
            delta = int(upd.get("sentiment_delta", 0) or 0)
            memory = upd.get("memory") or ""
            await self.apply_relationship_update(
                npc_id, character_id, user_id, character_name, delta, memory
            )
            await self.adjust_npc_mood(npc_id, delta)
            # Status change (e.g. wounded, dead, fled)
            status_updates: Dict = {}
            if upd.get("status") and upd["status"] in ("alive", "wounded", "dead", "fled", "missing"):
                status_updates["status"] = upd["status"]
            if upd.get("status_note"):
                status_updates["status_note"] = str(upd["status_note"])[:200]
            if status_updates:
                await self.update_npc(npc_id, status_updates)
            # Companion action — AI may emit "bond" when an NPC clearly agrees to
            # accompany the player, or "dismiss" when they part ways.
            companion_action = upd.get("companion_action")
            if companion_action == "bond":
                await self.bond_companion(npc_id, character_id)
            elif companion_action == "dismiss":
                await self.dismiss_companion(npc_id, character_id)
            results["npc_updates"] += 1

        for new_npc in analysis.get("new_npcs", []) or []:
            payload = dict(new_npc)
            payload["nation"] = nation
            payload["location"] = location
            created = await self.create_npc(payload, is_admin_seeded=False, created_by="auto")
            initial_delta = int(new_npc.get("sentiment_delta", 0) or 0)
            memory_text = new_npc.get("memory") or ""
            if initial_delta or memory_text:
                await self.apply_relationship_update(
                    created["id"], character_id, user_id, character_name,
                    initial_delta, memory_text,
                )
                if initial_delta:
                    await self.adjust_npc_mood(created["id"], initial_delta)
            # Brand-new NPCs may also bond on first meeting (e.g. a guide hired in the moment)
            if new_npc.get("companion_action") == "bond":
                await self.bond_companion(created["id"], character_id)
            results["new_npcs"] += 1

        for new_ev in analysis.get("new_events", []) or []:
            payload = dict(new_ev)
            payload["nation"] = nation
            payload["location"] = location
            payload.setdefault("participants", [character_id])
            await self.create_event(payload, created_by="ai")
            results["new_events"] += 1

        for ev_upd in analysis.get("event_updates", []) or []:
            event_id = ev_upd.get("event_id")
            status = ev_upd.get("status")
            if not event_id or not status:
                continue
            await self.update_event_status(
                event_id, status, ev_upd.get("resolution_note")
            )
            results["event_updates"] += 1

        return results
