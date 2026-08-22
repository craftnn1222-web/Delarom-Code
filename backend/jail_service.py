"""Jail / Prison location service for Continents of Delarom.

Every city should have a dedicated jail/prison location so that arrested
players are NOT locked inside the random tavern / market square where they
got caught. This service guarantees a jail exists for the city (or nation,
as a fallback) and returns its slug.

Design notes
------------
- Cheap, idempotent. Safe to call on every arrest.
- Pure Mongo helper — does NOT touch the law_service / quest_master_ai.
- Schema is fully compatible with the existing `locations` collection used
  by `routes/cities_locations.py`. A jail is just a regular `LocationArea`
  document with `location_type="prison"`.
- Slugs are namespaced as `f"{city_slug}-jail"` to avoid collisions, or
  `f"{nation_slug}-jail"` for nation-level fallbacks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


JAIL_LOCATION_TYPE = "prison"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pretty_name(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-")) if slug else ""


def _build_jail_doc(nation: str, city: Optional[str], slug: str, name: str) -> Dict:
    """Mongo document mirroring the LocationArea schema in server.py."""
    description = (
        f"The {name} — stone cells, iron bars, watchful guards. "
        "Where the law of this realm keeps its captives until trial, sentence, or escape."
    )
    return {
        "id": str(uuid.uuid4()),
        "nation": nation,
        "city": city,
        "slug": slug,
        "name": name,
        "location_type": JAIL_LOCATION_TYPE,
        "description": description,
        "image_url": None,
        "image_id": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": _now_iso(),
    }


async def _find_existing_jail(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    city: Optional[str],
) -> Optional[Dict]:
    """Look for an existing prison-type location for this city / nation.

    Scoped strictly: when a city is provided we ONLY look for a jail tied to
    that city — we DO NOT fall back to a nation-level prison, because every
    city should have its own jail. Without a city we accept any nation-level
    or city-less prison.
    """
    if city:
        # 1. Best match: city-scoped prison.
        doc = await db.locations.find_one(
            {"nation": nation, "city": city, "location_type": JAIL_LOCATION_TYPE},
            {"_id": 0},
        )
        if doc:
            return doc
        # 2. Older seeds may have used the slug pattern without the type tag.
        doc = await db.locations.find_one(
            {"nation": nation, "city": city, "slug": f"{city}-jail"},
            {"_id": 0},
        )
        if doc:
            return doc
        return None

    # 3. No city — accept any nation-level (city-less) prison.
    doc = await db.locations.find_one(
        {
            "nation": nation,
            "location_type": JAIL_LOCATION_TYPE,
            "$or": [{"city": None}, {"city": ""}, {"city": {"$exists": False}}],
        },
        {"_id": 0},
    )
    return doc


async def ensure_jail_for_city(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    city: Optional[str],
    fallback_location_slug: Optional[str] = None,
) -> Dict:
    """Return the jail location for this city (creating it on the fly if needed).

    Resolution order:
      1. Existing prison in this city.
      2. Existing prison anywhere in this nation (nation-level fallback).
      3. Create a new prison scoped to the city (or to the nation if `city`
         is missing).

    `fallback_location_slug` is only consulted if NO city + NO existing
    prison can be resolved — it lets a caller pass the player's current
    location so we can at least derive a nation-level jail name from
    something contextual.
    """
    existing = await _find_existing_jail(db, nation=nation, city=city)
    if existing:
        return existing

    if city:
        slug = f"{city}-jail"
        name = f"{_pretty_name(city)} Jail"
    else:
        slug = f"{nation}-jail"
        if fallback_location_slug:
            slug = f"{fallback_location_slug}-jail"
        name = f"{_pretty_name(nation)} Jail"

    # Hardening — the same nation may already have a slug collision with a
    # different location_type. Suffix a short uid to keep it unique.
    collision = await db.locations.find_one(
        {"nation": nation, "slug": slug}, {"_id": 0, "id": 1, "location_type": 1}
    )
    if collision and collision.get("location_type") != JAIL_LOCATION_TYPE:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    doc = _build_jail_doc(nation=nation, city=city, slug=slug, name=name)
    await db.locations.insert_one(dict(doc))
    return doc


async def resolve_city_for_location(
    db: AsyncIOMotorDatabase,
    *,
    nation: str,
    location_slug: str,
) -> Optional[str]:
    """Return the `city` slug for a given location, if any.

    Used by the law system to know which city the player was arrested in
    so we can route them to that city's jail (and not the wrong one).
    """
    if not location_slug:
        return None
    loc = await db.locations.find_one(
        {"nation": nation, "slug": location_slug},
        {"_id": 0, "city": 1},
    )
    if not loc:
        return None
    return loc.get("city") or None
