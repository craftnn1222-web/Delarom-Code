"""Cities & Locations CRUD routes.

Extracted from server.py (2026-05-31 refactor) to reduce server.py from
2684 lines down towards a more manageable size. Surface area unchanged —
this is a pure code-move with no behaviour changes. Each endpoint is
mounted via `attach_cities_locations_routes(api_router, ...)`.

Scope of this module:
- Cities: list/list-by-nation/detail + lazy city-image + admin create/update
- Locations: list/list-by-nation/list-by-city + lazy location-image + admin
  create/update/toggle-active + location meta

NOT extracted (still in server.py — they integrate tightly with the RP
engine, scene-state, and AI tick loops):
- POST /locations/{nation}/{location}/roleplay
- GET  /locations/{nation}/{location}/roleplay
- DELETE /locations/{nation}/{location}/roleplay/{rp_id}
- GET  /locations/{nation}/{location}/scene-state
- GET  /nations/* image endpoints
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request


def _make_image_url(image_id: Optional[str]) -> Optional[str]:
    """Build a relative `/api/image/{id}` URL the frontend can drop into <img src>."""
    if not image_id:
        return None
    return f"/api/image/{image_id}"


def attach_cities_locations_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    City, CityBase, CityUpdate, CityListItem,
    LocationArea, LocationAreaBase, LocationAreaUpdate, LocationAreaListItem,
    ImageService,
    require_moderator,
):
    """Mount cities + locations CRUD routes on the api router.

    Models are passed in (rather than imported from server.py) to avoid the
    circular-import cycle that would arise from server.py importing this
    module while this module imports models from server.
    """

    # ──────────────────────────── helpers ────────────────────────────

    async def _decorate_locations_with_has_image(query: dict) -> List[dict]:
        """Fetch locations without the heavy image_url payload and annotate
        each with has_image=True/False so the frontend can lazy-load images
        via /location-image/{nation}/{location_slug} when a card scrolls
        into view. Same logic as before the refactor — closure captures db.
        """
        projection = {"_id": 0, "image_url": 0, "image_id": 0}
        docs = await db.locations.find(query, projection).sort("name", 1).to_list(1000)
        if not docs:
            return docs

        slugs = [d["slug"] for d in docs]
        nations = list({d["nation"] for d in docs})
        with_image_cursor = db.locations.find(
            {
                "nation": {"$in": nations},
                "slug": {"$in": slugs},
                "$or": [
                    {"image_id": {"$exists": True, "$ne": None, "$nin": [""]}},
                    {"image_url": {"$exists": True, "$ne": None, "$nin": [""]}},
                ],
            },
            {"_id": 0, "nation": 1, "slug": 1},
        )
        with_image_docs = await with_image_cursor.to_list(2000)
        has_image_keys = {(d["nation"], d["slug"]) for d in with_image_docs}

        for doc in docs:
            doc["has_image"] = (doc["nation"], doc["slug"]) in has_image_keys
            if isinstance(doc.get("created_at"), str):
                doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        return docs

    # ────────────────────────── CITY ROUTES ──────────────────────────

    @api_router.get("/cities", response_model=List[City])
    async def list_cities(nation: Optional[str] = None, include_inactive: bool = False):
        """Public listing of cities.

        - By default returns only active cities.
        - Can be filtered by nation slug (e.g. "aigraels").
        """
        query: dict = {}
        if nation:
            query["nation"] = nation
        if not include_inactive:
            query["is_active"] = True

        cities = await db.cities.find(query, {"_id": 0, "image_url": 0}).sort("name", 1).to_list(1000)
        for city in cities:
            if isinstance(city.get("created_at"), str):
                city["created_at"] = datetime.fromisoformat(city["created_at"])
            # Return a tiny `/api/image/{id}` ref, never the heavy base64 blob.
            iid = city.pop("image_id", None)
            city["image_url"] = _make_image_url(iid)
        return [City(**c) for c in cities]

    @api_router.get("/cities/{nation}", response_model=List[CityListItem])
    async def list_cities_by_nation(nation: str, include_inactive: bool = False):
        """Get all cities in a given nation (lightweight, without image data).

        This endpoint returns city metadata without the image_url field to keep
        responses fast. Use /api/city-image/{nation}/{city_slug} to fetch
        individual city images.
        """
        query = {"nation": nation}
        if not include_inactive:
            query["is_active"] = True

        # Exclude image_url from projection for performance (can be large base64 strings)
        projection = {"_id": 0, "image_url": 0, "created_at": 0}
        cities = await db.cities.find(query, projection).sort("name", 1).to_list(1000)

        # Check which cities have images (without loading the actual image data)
        city_slugs = [c["slug"] for c in cities]
        # A city has an image if it has either a new image_id OR a legacy image_url.
        cities_with_images = await db.cities.find(
            {
                "nation": nation,
                "slug": {"$in": city_slugs},
                "$or": [
                    {"image_id": {"$exists": True, "$ne": None, "$nin": [""]}},
                    {"image_url": {"$exists": True, "$ne": None, "$nin": [""]}},
                ],
            },
            {"_id": 0, "slug": 1}
        ).to_list(1000)
        slugs_with_images = {c["slug"] for c in cities_with_images}

        for city in cities:
            city["has_image"] = city["slug"] in slugs_with_images

        return [CityListItem(**c) for c in cities]

    @api_router.get("/city-image/{nation}/{city_slug}")
    async def get_city_image(nation: str, city_slug: str, request: Request):
        """Get just the image URL for a specific city.

        Returns a small JSON `{ "image_url": "/api/image/<id>" }`. Legacy
        base64 blobs are migrated to the `image_blobs` collection on first
        access.
        """
        city_doc = await db.cities.find_one(
            {"nation": nation, "slug": city_slug},
            {"_id": 0, "image_id": 1, "image_url": 1}
        )
        if not city_doc:
            raise HTTPException(status_code=404, detail="City not found")
        image_id = city_doc.get("image_id")
        if not image_id and city_doc.get("image_url"):
            img_service = ImageService(db)
            image_id = await img_service.ensure_migrated("cities", {"nation": nation, "slug": city_slug})
        return {"image_url": _make_image_url(image_id)}

    @api_router.get("/cities/{nation}/{city_slug}", response_model=City)
    async def get_city(nation: str, city_slug: str):
        """Get a specific city by nation and slug."""
        # Exclude the heavy base64 image_url; return a small `/api/image/{id}`
        # ref instead (migrating any legacy blob on first access).
        city_doc = await db.cities.find_one(
            {"nation": nation, "slug": city_slug}, {"_id": 0, "image_url": 0}
        )
        if not city_doc:
            raise HTTPException(status_code=404, detail="City not found")
        if isinstance(city_doc.get("created_at"), str):
            city_doc["created_at"] = datetime.fromisoformat(city_doc["created_at"])
        image_id = city_doc.pop("image_id", None)
        if not image_id:
            img_service = ImageService(db)
            image_id = await img_service.ensure_migrated("cities", {"nation": nation, "slug": city_slug})
        city_doc["image_url"] = _make_image_url(image_id)
        return City(**city_doc)

    @api_router.post("/admin/cities", response_model=City)
    async def create_city(city_data: CityBase, moderator: User = Depends(require_moderator)):
        """Create a new city."""
        # Ensure slug uniqueness within nation
        existing = await db.cities.find_one({"nation": city_data.nation, "slug": city_data.slug})
        if existing:
            raise HTTPException(status_code=400, detail="A city with this slug already exists for this nation")

        city = City(**city_data.model_dump())
        city_doc = city.model_dump()
        city_doc["created_at"] = city_doc["created_at"].isoformat()
        await db.cities.insert_one(city_doc)
        return city

    @api_router.put("/admin/cities/{city_id}", response_model=City)
    async def update_city(city_id: str, updates: CityUpdate, moderator: User = Depends(require_moderator)):
        """Update a city's information."""
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await db.cities.update_one({"id": city_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="City not found")

        city_doc = await db.cities.find_one({"id": city_id}, {"_id": 0})
        if not city_doc:
            raise HTTPException(status_code=404, detail="City not found")
        if isinstance(city_doc.get("created_at"), str):
            city_doc["created_at"] = datetime.fromisoformat(city_doc["created_at"])
        return City(**city_doc)

    # ──────────────────────── LOCATION ROUTES ────────────────────────

    @api_router.get("/locations", response_model=List[LocationAreaListItem])
    async def list_locations(nation: Optional[str] = None, include_inactive: bool = False):
        """Public listing of locations (lightweight — no image_url in payload).

        - By default returns only active locations.
        - Can be filtered by nation slug (e.g. "ammeonon").
        - Use `/api/location-image/{nation}/{location_slug}` to fetch the image
          lazily when a card scrolls into view.
        """
        query: dict = {}
        if nation:
            query["nation"] = nation
        if not include_inactive:
            query["is_active"] = True

        docs = await _decorate_locations_with_has_image(query)
        return [LocationAreaListItem(**doc) for doc in docs]

    @api_router.get("/locations/{nation}", response_model=List[LocationAreaListItem])
    async def list_locations_by_nation(nation: str, include_inactive: bool = False):
        """Convenience endpoint for all locations in a given nation (lightweight)."""
        query: dict = {"nation": nation}
        if not include_inactive:
            query["is_active"] = True

        docs = await _decorate_locations_with_has_image(query)
        return [LocationAreaListItem(**doc) for doc in docs]

    @api_router.get("/locations/{nation}/{city_slug}/locations", response_model=List[LocationAreaListItem])
    async def list_locations_by_city(nation: str, city_slug: str, include_inactive: bool = False):
        """Get all locations within a specific city (lightweight)."""
        query: dict = {"nation": nation, "city": city_slug}
        if not include_inactive:
            query["is_active"] = True

        docs = await _decorate_locations_with_has_image(query)
        return [LocationAreaListItem(**doc) for doc in docs]

    @api_router.get("/location-image/{nation}/{location_slug}")
    async def get_location_image(nation: str, location_slug: str, request: Request):
        """Lazy-load image URL for a single location.

        Returns `{ "image_url": "/api/image/<id>" }` or 404 if the location
        does not exist. Legacy base64 blobs are migrated on first access.
        """
        loc_doc = await db.locations.find_one(
            {"nation": nation, "slug": location_slug},
            {"_id": 0, "image_id": 1, "image_url": 1},
        )
        if not loc_doc:
            raise HTTPException(status_code=404, detail="Location not found")
        image_id = loc_doc.get("image_id")
        if not image_id and loc_doc.get("image_url"):
            img_service = ImageService(db)
            image_id = await img_service.ensure_migrated(
                "locations", {"nation": nation, "slug": location_slug}
            )
        return {"image_url": _make_image_url(image_id)}

    @api_router.post("/admin/locations", response_model=LocationArea)
    async def create_location(location_data: LocationAreaBase, moderator: User = Depends(require_moderator)):
        """Create a new location (RP or lore) for a nation."""
        # Slug uniqueness is scoped to (nation, city, slug) so the same slug
        # (e.g. "market-square") can legitimately exist in different cities
        # within the same nation. A null/missing city is a "nation-level"
        # location and is checked against other nation-level locations only.
        uniqueness_query: dict = {"nation": location_data.nation, "slug": location_data.slug}
        if location_data.city:
            uniqueness_query["city"] = location_data.city
        else:
            # Treat missing/empty/None as a single equivalence class so we
            # don't create two nation-level locations with the same slug.
            uniqueness_query["city"] = {"$in": [None, ""]}
        existing = await db.locations.find_one(uniqueness_query)
        if existing:
            scope = f"city '{location_data.city}'" if location_data.city else "nation level"
            raise HTTPException(
                status_code=400,
                detail=f"A location with slug '{location_data.slug}' already exists at the {scope}.",
            )

        location = LocationArea(**location_data.model_dump())
        loc_doc = location.model_dump()
        loc_doc["created_at"] = loc_doc["created_at"].isoformat()
        await db.locations.insert_one(loc_doc)
        return location

    @api_router.put("/admin/locations/{location_id}", response_model=LocationArea)
    async def update_location(location_id: str, updates: LocationAreaUpdate, moderator: User = Depends(require_moderator)):
        """Update a location's display info or flags."""
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await db.locations.update_one({"id": location_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")

        loc_doc = await db.locations.find_one({"id": location_id}, {"_id": 0})
        if not loc_doc:
            raise HTTPException(status_code=404, detail="Location not found")
        if isinstance(loc_doc.get("created_at"), str):
            loc_doc["created_at"] = datetime.fromisoformat(loc_doc["created_at"])
        return LocationArea(**loc_doc)

    @api_router.post("/admin/locations/{location_id}/toggle-active", response_model=LocationArea)
    async def toggle_location_active(location_id: str, moderator: User = Depends(require_moderator)):
        """Toggle the active flag for a location (soft enable/disable)."""
        loc_doc = await db.locations.find_one({"id": location_id})
        if not loc_doc:
            raise HTTPException(status_code=404, detail="Location not found")

        new_active = not bool(loc_doc.get("is_active", True))
        await db.locations.update_one({"id": location_id}, {"$set": {"is_active": new_active}})

        updated = await db.locations.find_one({"id": location_id}, {"_id": 0})
        if isinstance(updated.get("created_at"), str):
            updated["created_at"] = datetime.fromisoformat(updated["created_at"])
        return LocationArea(**updated)

    @api_router.get("/locations/{nation}/{location_slug}/meta", response_model=LocationArea)
    async def get_location_meta(nation: str, location_slug: str):
        """Get location metadata for a nation/location slug pair.

        Used by the frontend to render dynamic RP area headers and to verify
        whether the location is active and RP-enabled.
        """
        loc_doc = await db.locations.find_one(
            {"nation": nation, "slug": location_slug, "is_active": True},
            {"_id": 0}
        )
        if not loc_doc:
            raise HTTPException(status_code=404, detail="Location not found")

        if isinstance(loc_doc.get("created_at"), str):
            loc_doc["created_at"] = datetime.fromisoformat(loc_doc["created_at"])
        return LocationArea(**loc_doc)
