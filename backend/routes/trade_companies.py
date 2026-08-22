"""Routes for the Trade Companies MVP.

Mounted via `attach_trade_company_routes(api_router, ...)`.

Endpoints (all authed unless noted):
    GET   /api/trade-companies                     — list active companies
    GET   /api/trade-companies/mine                — companies I founded or own shares in
    POST  /api/trade-companies                     — charter (2500g)
    GET   /api/trade-companies/{id}                — detail
    GET   /api/trade-companies/{id}/routes         — list routes
    POST  /api/trade-companies/{id}/routes         — add route  (founder only)
    POST  /api/trade-companies/{id}/routes/{rid}/toggle — enable/disable
    DELETE /api/trade-companies/{id}/routes/{rid}  — remove
    POST  /api/trade-companies/{id}/invest         — buy shares
    POST  /api/trade-companies/{id}/dissolve       — founder ends
    GET   /api/trade-companies/{id}/shareholders   — list
    GET   /api/trade-companies/{id}/activity       — recent events
    GET   /api/trade-companies/{id}/ledgers        — closed periods
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from trade_companies_service import TradeCompanyService


class CharterPayload(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    motto: str = Field(default="", max_length=200)
    home_nation: str = Field(..., min_length=2, max_length=64)
    founder_character_id: str = Field(..., min_length=1, max_length=128)
    sigil: str = Field(default="coins", max_length=64)
    color: str = Field(default="#f59e0b", max_length=16)


class RoutePayload(BaseModel):
    source_nation: str = Field(..., min_length=2, max_length=64)
    source_city_slug: str = Field(..., min_length=2, max_length=64)
    dest_nation: str = Field(..., min_length=2, max_length=64)
    dest_city_slug: str = Field(..., min_length=2, max_length=64)
    good_slug: str = Field(..., min_length=2, max_length=64)
    units_per_run: int = Field(default=20, ge=1, le=200)


class InvestPayload(BaseModel):
    character_id: str = Field(..., min_length=1, max_length=128)
    gold: int = Field(..., ge=100, le=1_000_000)


def _raise_from_value_error(ve: ValueError) -> None:
    msg = str(ve)
    if "not found" in msg.lower():
        raise HTTPException(status_code=404, detail=msg) from ve
    raise HTTPException(status_code=409, detail=msg) from ve


def attach_trade_company_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
):
    @api_router.post("/trade-companies/admin/seed-npc-rivals")
    async def seed_npc_rivals(current_user: User = Depends(get_current_user)):
        """Admin: seed the canonical NPC trade rivals. Idempotent."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin only.")
        from npc_economy import seed_npc_trade_rivals
        return await seed_npc_trade_rivals(db)

    @api_router.get("/trade-companies")
    async def list_companies(
        status: Optional[str] = None,
        current_user: User = Depends(get_current_user),
    ):
        return await TradeCompanyService(db).list_companies(status=status)

    @api_router.get("/trade-companies/mine")
    async def list_my_companies(current_user: User = Depends(get_current_user)):
        # Companies I founded
        founded = await db.trade_companies.find(
            {"founder_user_id": current_user.id}, {"_id": 0},
        ).sort("created_at", -1).to_list(50)
        # Companies I hold shares in (may overlap with founded)
        holding_ids = await db.trade_company_shareholders.distinct(
            "company_id", {"user_id": current_user.id},
        )
        held = await db.trade_companies.find(
            {"id": {"$in": holding_ids}, "founder_user_id": {"$ne": current_user.id}},
            {"_id": 0},
        ).sort("created_at", -1).to_list(50)
        return {"founded": founded, "shares_only": held}

    @api_router.post("/trade-companies")
    async def create_company(
        payload: CharterPayload,
        current_user: User = Depends(get_current_user),
    ):
        char = await db.characters.find_one(
            {"id": payload.founder_character_id, "user_id": current_user.id},
            {"_id": 0},
        )
        if not char:
            raise HTTPException(status_code=404, detail="Character not found (or not owned by you).")
        try:
            return await TradeCompanyService(db).charter(
                founder_user={"id": current_user.id, "username": current_user.username},
                founder_character=char,
                name=payload.name,
                motto=payload.motto,
                home_nation=payload.home_nation,
                sigil=payload.sigil,
                color=payload.color,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.get("/trade-companies/{company_id}")
    async def get_company(
        company_id: str,
        current_user: User = Depends(get_current_user),
    ):
        c = await TradeCompanyService(db).get_company(company_id)
        if not c:
            raise HTTPException(status_code=404, detail="Trade company not found.")
        return c

    @api_router.get("/trade-companies/{company_id}/routes")
    async def list_routes(
        company_id: str,
        current_user: User = Depends(get_current_user),
    ):
        return await TradeCompanyService(db).list_routes(company_id)

    @api_router.post("/trade-companies/{company_id}/routes")
    async def add_route(
        company_id: str,
        payload: RoutePayload,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await TradeCompanyService(db).add_route(
                company_id=company_id,
                user_id=current_user.id,
                source_nation=payload.source_nation,
                source_city_slug=payload.source_city_slug,
                dest_nation=payload.dest_nation,
                dest_city_slug=payload.dest_city_slug,
                good_slug=payload.good_slug,
                units_per_run=payload.units_per_run,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/trade-companies/{company_id}/routes/{route_id}/toggle")
    async def toggle_route(
        company_id: str,
        route_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await TradeCompanyService(db).toggle_route(
                company_id=company_id, route_id=route_id, user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.delete("/trade-companies/{company_id}/routes/{route_id}")
    async def delete_route(
        company_id: str,
        route_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await TradeCompanyService(db).delete_route(
                company_id=company_id, route_id=route_id, user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/trade-companies/{company_id}/invest")
    async def invest(
        company_id: str,
        payload: InvestPayload,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await TradeCompanyService(db).invest(
                company_id=company_id,
                user_id=current_user.id,
                character_id=payload.character_id,
                gold=payload.gold,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.post("/trade-companies/{company_id}/dissolve")
    async def dissolve(
        company_id: str,
        current_user: User = Depends(get_current_user),
    ):
        try:
            return await TradeCompanyService(db).dissolve(
                company_id=company_id, user_id=current_user.id,
            )
        except ValueError as ve:
            _raise_from_value_error(ve)

    @api_router.get("/trade-companies/{company_id}/shareholders")
    async def list_shareholders(
        company_id: str,
        current_user: User = Depends(get_current_user),
    ):
        return await TradeCompanyService(db).list_shareholders(company_id)

    @api_router.get("/trade-companies/{company_id}/activity")
    async def list_activity(
        company_id: str,
        limit: int = 60,
        current_user: User = Depends(get_current_user),
    ):
        return await TradeCompanyService(db).list_activity(company_id, limit=limit)

    @api_router.get("/trade-companies/{company_id}/ledgers")
    async def list_ledgers(
        company_id: str,
        limit: int = 12,
        current_user: User = Depends(get_current_user),
    ):
        return await TradeCompanyService(db).list_ledgers(company_id, limit=limit)
