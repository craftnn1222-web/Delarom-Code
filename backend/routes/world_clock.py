"""World Clock + Festival routes.

Phase 1 of the Atmospheric Foundations sprint (2026-05-30). Exposes the
in-world time-of-day and Delarom calendar date, plus the current active
festivals. Anonymous-friendly — these are part of the world's flavour and
do not leak any private data.
"""
from typing import Optional
from fastapi import APIRouter

from world_clock_service import get_world_clock
from festival_service import FestivalService


def attach_world_clock_routes(api_router: APIRouter, *, db):
    @api_router.get("/world-clock")
    async def world_clock(nation: Optional[str] = None):
        """Return the in-world time + active festivals, optionally scoped to a nation."""
        clock = get_world_clock()
        fs = FestivalService(db)
        active = await fs.get_active(nation=nation)
        return {**clock, "active_festivals": active}

    @api_router.get("/festivals")
    async def list_festivals():
        """Return the full festival calendar — every seeded holy day across Delarom."""
        fs = FestivalService(db)
        return await fs.list_all()
