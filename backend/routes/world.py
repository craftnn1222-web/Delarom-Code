"""Public Chronicle + admin World-State / Butterfly-Effect routes.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_world_routes(api_router, ...)`.
"""
from typing import Optional
from fastapi import APIRouter, Depends

from world_state_service import WorldStateService


def attach_world_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    require_admin,
    NationRelationPayload,
    NationRelationDeltaPayload,
    WorldEventCreatePayload,
):
    @api_router.get("/chronicle")
    async def public_chronicle(limit: int = 50):
        """Public-facing feed of dramatic world events visible to anyone.

        No authentication required — this is the in-world rumor mill. We
        intentionally omit raw IDs of NPCs and characters so the mechanical
        layer stays hidden.
        """
        world_service = WorldStateService(db)
        events = await world_service.list_world_events(limit=min(max(limit, 1), 200))
        public = []
        for ev in events:
            public.append({
                "id": ev.get("id"),
                "event_type": ev.get("event_type", "incident"),
                "scope": ev.get("scope", "world"),
                "summary": ev.get("summary", ""),
                "details": ev.get("details", ""),
                "nations": ev.get("nations", []),
                "created_at": ev.get("created_at"),
            })
        return public

    @api_router.get("/admin/diplomacy")
    async def admin_list_diplomacy(admin: User = Depends(require_admin)):
        """Admin: list all nation-pair relations."""
        world_service = WorldStateService(db)
        return await world_service.list_nation_relations()

    @api_router.post("/admin/diplomacy/set")
    async def admin_set_diplomacy(payload: NationRelationPayload, admin: User = Depends(require_admin)):
        """Admin: explicitly set a nation-pair score (clamped -100..100)."""
        world_service = WorldStateService(db)
        return await world_service.upsert_nation_relation(
            payload.nation_a, payload.nation_b, payload.score, payload.reason or "admin"
        )

    @api_router.post("/admin/diplomacy/adjust")
    async def admin_adjust_diplomacy(payload: NationRelationDeltaPayload, admin: User = Depends(require_admin)):
        """Admin: adjust a nation-pair score by delta and emit a world event."""
        world_service = WorldStateService(db)
        return await world_service.apply_relation_delta(
            payload.nation_a, payload.nation_b, payload.delta, payload.reason or "admin"
        )

    @api_router.get("/admin/world-events")
    async def admin_list_world_events(limit: int = 50, admin: User = Depends(require_admin)):
        world_service = WorldStateService(db)
        return await world_service.list_world_events(limit=limit)

    @api_router.post("/admin/world-events")
    async def admin_create_world_event(payload: WorldEventCreatePayload, admin: User = Depends(require_admin)):
        """Admin: manually record a world event (e.g., seed a war announcement)."""
        world_service = WorldStateService(db)
        return await world_service.record_world_event(payload.model_dump())

    @api_router.get("/admin/cascade-queue")
    async def admin_list_cascades(
        nation: Optional[str] = None,
        location: Optional[str] = None,
        admin: User = Depends(require_admin),
    ):
        world_service = WorldStateService(db)
        return await world_service.list_pending_cascades(nation=nation, location=location)

    @api_router.get("/admin/characters/{character_id}/reputation")
    async def admin_get_character_reputation(character_id: str, admin: User = Depends(require_admin)):
        """Admin: view a character's reputation across all nations (HIDDEN from the player)."""
        world_service = WorldStateService(db)
        return await world_service.list_reputation(character_id)
