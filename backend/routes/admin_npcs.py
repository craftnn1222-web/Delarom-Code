"""Admin NPC management + scene-event management routes.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_admin_npc_routes(api_router, ...)`.
"""
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException

from npc_memory_service import NPCMemoryService


def attach_admin_npc_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    require_admin,
    NPCCreatePayload,
    NPCUpdatePayload,
    LocationEventCreatePayload,
    LocationEventStatusPayload,
):
    @api_router.get("/admin/npcs")
    async def admin_list_all_npcs(
        nation: Optional[str] = None,
        location: Optional[str] = None,
        include_factions: bool = True,
        admin: User = Depends(require_admin),
    ):
        """Admin: list all persistent NPCs (optionally filtered by nation/location).

        With `include_factions=true` (default) the response is *unioned* with
        faction NPCs (`db.faction_npcs`). Faction NPCs don't have nation /
        location fields — they belong to a faction — so they're included
        whenever no nation/location filter narrows them out. This is the fix
        for the long-standing "Orion doesn't appear in the admin NPCs tab"
        bug: faction members live in their own collection and used to be
        invisible to the admin panel entirely.

        Each faction NPC is decorated with synthetic fields that mirror the
        regular NPC shape so the frontend can render them uniformly:
          - `nation`: '' (no nation — they're scoped to a faction)
          - `location`: '' (no location)
          - `kind`: 'faction'  (vs. 'location' for regular NPCs)
          - `faction_slug` / `faction_name`: surfaces the parent faction
        """
        query: Dict = {}
        if nation:
            query["nation"] = nation
        if location:
            query["location"] = location
        location_npcs_raw = await db.npcs.find(query, {"_id": 0}).sort("last_seen_at", -1).to_list(2000)
        location_npcs = [{**n, "kind": "location"} for n in location_npcs_raw]

        # Don't add faction NPCs if the caller asked for a specific
        # nation/location — those filters can't possibly match faction NPCs
        # because they don't have those fields.
        if include_factions and not nation and not location:
            faction_npcs_raw = await db.faction_npcs.find(
                {"is_active": True}, {"_id": 0}
            ).sort("joined_at", -1).to_list(2000)
            # Look up faction names so the UI can show "Vritra Clan / Orion"
            # rather than just the slug. One round-trip is fine — we'll only
            # ever have a few dozen factions.
            faction_names: Dict[str, str] = {}
            if faction_npcs_raw:
                slugs = list({n["faction_slug"] for n in faction_npcs_raw if n.get("faction_slug")})
                async for f in db.factions.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "name": 1}):
                    faction_names[f["slug"]] = f["name"]
            for fn in faction_npcs_raw:
                fn["kind"] = "faction"
                fn["nation"] = ""
                fn["location"] = ""
                fn["faction_name"] = faction_names.get(fn.get("faction_slug"), fn.get("faction_slug") or "")
                # Mirror common NPC fields so the frontend doesn't have to
                # special-case them everywhere.
                fn.setdefault("role", fn.get("title") or "Faction Member")
                fn.setdefault("personality", fn.get("personality") or "")
                fn.setdefault("background", fn.get("bio") or "")
                fn.setdefault("importance", fn.get("rank") or "member")
                fn.setdefault("status", "alive")
                fn.setdefault("mood_score", 0)
            location_npcs.extend(faction_npcs_raw)

        return location_npcs

    @api_router.get("/admin/npc-scopes")
    async def admin_list_npc_scopes(admin: User = Depends(require_admin)):
        """Admin: list every (nation, location) pair AND every faction that
        currently has at least one NPC. Used to populate the cascading
        dropdowns in the admin NPC manager so admins can browse without
        having to type slugs from memory.

        Returns:
          {
            "locations": [{"nation": "ammeonon", "location": "wymroost", "count": 12}, ...],
            "factions":  [{"slug": "vritra-clan", "name": "Vritra Clan", "count": 6}, ...],
          }
        """
        # Cheap aggregate; locations collection is bounded (~1500).
        loc_pipeline = [
            {"$group": {"_id": {"nation": "$nation", "location": "$location"}, "count": {"$sum": 1}}},
            {"$sort": {"_id.nation": 1, "_id.location": 1}},
        ]
        location_buckets = []
        async for row in db.npcs.aggregate(loc_pipeline):
            location_buckets.append({
                "nation": row["_id"].get("nation") or "",
                "location": row["_id"].get("location") or "",
                "count": row["count"],
            })

        fact_pipeline = [
            {"$match": {"is_active": True}},
            {"$group": {"_id": "$faction_slug", "count": {"$sum": 1}}},
        ]
        faction_counts: Dict[str, int] = {}
        async for row in db.faction_npcs.aggregate(fact_pipeline):
            slug = row["_id"]
            if slug:
                faction_counts[slug] = row["count"]

        factions: list = []
        if faction_counts:
            async for f in db.factions.find(
                {"slug": {"$in": list(faction_counts.keys())}},
                {"_id": 0, "slug": 1, "name": 1},
            ):
                factions.append({
                    "slug": f["slug"],
                    "name": f["name"],
                    "count": faction_counts.get(f["slug"], 0),
                })
            factions.sort(key=lambda f: f["name"])

        return {"locations": location_buckets, "factions": factions}

    @api_router.get("/admin/faction-npcs")
    async def admin_list_faction_npcs(
        faction_slug: Optional[str] = None,
        admin: User = Depends(require_admin),
    ):
        """Admin: list NPC members of a specific faction (or all factions).

        Decorated with `kind: 'faction'` + synthetic `role`/`background`
        fields so the admin UI can render this list with the same card
        template it uses for location NPCs.
        """
        query: Dict = {"is_active": True}
        if faction_slug:
            query["faction_slug"] = faction_slug
        raw = await db.faction_npcs.find(query, {"_id": 0}).sort("joined_at", -1).to_list(1000)
        faction_names: Dict[str, str] = {}
        if raw:
            slugs = list({n["faction_slug"] for n in raw if n.get("faction_slug")})
            async for f in db.factions.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "name": 1}):
                faction_names[f["slug"]] = f["name"]
        for fn in raw:
            fn["kind"] = "faction"
            fn["nation"] = ""
            fn["location"] = ""
            fn["faction_name"] = faction_names.get(fn.get("faction_slug"), fn.get("faction_slug") or "")
            fn.setdefault("role", fn.get("title") or "Faction Member")
            fn.setdefault("background", fn.get("bio") or "")
            fn.setdefault("importance", fn.get("rank") or "member")
            fn.setdefault("status", "alive")
            fn.setdefault("mood_score", 0)
        return raw


    @api_router.get("/npcs/search")
    async def public_npc_search(
        q: str = "",
        nation: Optional[str] = None,
        limit: int = 20,
    ):
        """Public, lightweight NPC search by name fragment. Used by player-
        facing forms that need to name a subject (rumors, bounties, etc.).
        Returns only the fields needed for autocomplete: id, name, role,
        race, nation, location. Requires at least 2 characters in `q`.
        """
        q = (q or "").strip()
        if len(q) < 2:
            return []
        query: Dict = {"name": {"$regex": q, "$options": "i"}}
        if nation:
            query["nation"] = nation
        limit = max(1, min(limit, 50))
        cursor = db.npcs.find(
            query,
            {"_id": 0, "id": 1, "name": 1, "role": 1, "race": 1, "nation": 1, "location": 1},
        ).limit(limit)
        return await cursor.to_list(length=limit)

    @api_router.post("/admin/npcs/{nation}/{location}")
    async def admin_create_npc(
        nation: str,
        location: str,
        payload: NPCCreatePayload,
        admin: User = Depends(require_admin),
    ):
        """Admin: seed a named NPC into a specific location."""
        npc_service = NPCMemoryService(db)
        data = payload.model_dump()
        data["nation"] = nation
        data["location"] = location
        npc = await npc_service.create_npc(data, is_admin_seeded=True, created_by=admin.id)
        return npc

    @api_router.patch("/admin/npcs/{npc_id}")
    async def admin_update_npc(
        npc_id: str,
        payload: NPCUpdatePayload,
        admin: User = Depends(require_admin),
    ):
        npc_service = NPCMemoryService(db)
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        npc = await npc_service.update_npc(npc_id, updates)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        return npc

    @api_router.delete("/admin/npcs/{npc_id}")
    async def admin_delete_npc(npc_id: str, admin: User = Depends(require_admin)):
        npc_service = NPCMemoryService(db)
        ok = await npc_service.delete_npc(npc_id)
        if not ok:
            raise HTTPException(status_code=404, detail="NPC not found")
        return {"deleted": True}

    @api_router.post("/admin/npcs/{npc_id}/reset-memory")
    async def admin_reset_npc_memory(npc_id: str, admin: User = Depends(require_admin)):
        npc_service = NPCMemoryService(db)
        npc = await npc_service.get_npc(npc_id)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        await npc_service.reset_npc_memories(npc_id)
        return {"reset": True}

    @api_router.get("/admin/npcs/{npc_id}/relationships")
    async def admin_list_relationships(npc_id: str, admin: User = Depends(require_admin)):
        npc_service = NPCMemoryService(db)
        return await npc_service.list_relationships_for_npc(npc_id)

    @api_router.get("/admin/scene-events")
    async def admin_list_events(
        nation: Optional[str] = None,
        location: Optional[str] = None,
        active_only: bool = False,
        admin: User = Depends(require_admin),
    ):
        query: Dict = {}
        if nation:
            query["nation"] = nation
        if location:
            query["location"] = location
        if active_only:
            query["status"] = "active"
        events = await db.location_events.find(query, {"_id": 0}).sort("started_at", -1).to_list(500)
        return events

    @api_router.post("/admin/scene-events/{nation}/{location}")
    async def admin_create_event(
        nation: str,
        location: str,
        payload: LocationEventCreatePayload,
        admin: User = Depends(require_admin),
    ):
        npc_service = NPCMemoryService(db)
        data = payload.model_dump()
        data["nation"] = nation
        data["location"] = location
        event = await npc_service.create_event(data, created_by=admin.id)
        return event

    @api_router.patch("/admin/scene-events/{event_id}/status")
    async def admin_update_event_status(
        event_id: str,
        payload: LocationEventStatusPayload,
        admin: User = Depends(require_admin),
    ):
        npc_service = NPCMemoryService(db)
        event = await npc_service.update_event_status(event_id, payload.status, payload.resolution_note)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found or invalid status")
        return event

    @api_router.delete("/admin/scene-events/{event_id}")
    async def admin_delete_event(event_id: str, admin: User = Depends(require_admin)):
        npc_service = NPCMemoryService(db)
        ok = await npc_service.delete_event(event_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"deleted": True}
