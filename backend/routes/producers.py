"""Routes for producer seeding, city stock reads, and manual ticks.

Mounted via `attach_producer_routes(api_router, ...)` from server.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from producers_service import EconomyProducers


def attach_producer_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
):
    @api_router.get("/economy/producers/state")
    async def get_producers_state():
        state = await EconomyProducers(db).get_state()
        return state

    @api_router.get("/economy/producers/cities/{nation}/{city_slug}")
    async def city_producers(nation: str, city_slug: str):
        prods = EconomyProducers(db)
        return {
            "nation": nation,
            "city_slug": city_slug,
            "producers": await prods.list_city_producers(nation, city_slug),
            "stock": await prods.get_city_stock(nation, city_slug),
        }

    @api_router.get("/economy/producers/ticks")
    async def recent_ticks(limit: int = 20):
        return await EconomyProducers(db).recent_tick_log(limit=limit)

    @api_router.post("/economy/producers/admin/seed")
    async def admin_seed_producers(admin: User = Depends(require_admin)):
        return await EconomyProducers(db).seed_city_producers()

    @api_router.post("/economy/producers/admin/tick")
    async def admin_run_tick(admin: User = Depends(require_admin)):
        """Force a production tick immediately. Also fires trade-company
        route runs and any due ledger closes."""
        return await EconomyProducers(db).run_tick(source="admin")

    @api_router.get("/economy/inventory/{owner_type}/{owner_key}")
    async def get_owner_stock(owner_type: str, owner_key: str):
        if owner_type not in ("city", "faction"):
            raise HTTPException(status_code=400, detail="owner_type must be 'city' or 'faction'")
        rows = await db.producer_inventory.find(
            {"owner_type": owner_type, "owner_key": owner_key},
            {"_id": 0},
        ).sort("good_slug", 1).to_list(200)
        return rows
