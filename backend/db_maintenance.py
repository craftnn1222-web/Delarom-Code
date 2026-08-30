"""Database maintenance — deduplicate the `locations` collection and add
the missing unique indexes that should have been there from the start.

Why this exists: `populate_ammeonon.py`, `populate_dhor_kuldor.py` and
their siblings are re-runnable seed scripts that simply call `insert_one`
for every location they know about. Without a unique index on
`(nation, slug)` (or `(nation, city, slug)` once we added city-scoping),
re-running a script produces a fresh row for every "Tyr Temple" instead
of an upsert. Production accumulated up to 10 copies of some locations.

This module is idempotent and safe to call repeatedly.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def dedupe_locations(db) -> dict:
    """Collapse duplicate (nation, city, slug) groups in the `locations`
    collection. The canonical survivor is the OLDEST row in each group
    (lowest `created_at`); every other copy is deleted.

    Returns `{groups_collapsed, rows_deleted, total_before, total_after}`.
    """
    total_before = await db.locations.count_documents({})

    # Find all groups with 2+ rows for the same (nation, city, slug).
    # `city` is normalised to empty-string so None/missing/'' collapse into
    # the same equivalence class — the nation-level orphan group.
    pipeline = [
        {
            "$group": {
                "_id": {
                    "nation": "$nation",
                    "city": {"$ifNull": ["$city", ""]},
                    "slug": "$slug",
                },
                "count": {"$sum": 1},
                "ids": {"$push": "$id"},
                "created_ats": {"$push": "$created_at"},
            }
        },
        {"$match": {"count": {"$gt": 1}}},
    ]

    groups_collapsed = 0
    rows_deleted = 0
    async for group in db.locations.aggregate(pipeline):
        # Pair (id, created_at) so we can pick the oldest reliably.
        pairs = list(zip(group["ids"], group["created_ats"]))
        # ISO strings sort lexicographically the same as chronologically,
        # so plain min() picks the oldest. Defensive: missing created_at
        # falls to the start of the sort.
        pairs.sort(key=lambda x: x[1] or "")
        survivor_id = pairs[0][0]
        loser_ids = [p[0] for p in pairs[1:]]
        if not loser_ids:
            continue
        result = await db.locations.delete_many({"id": {"$in": loser_ids}})
        rows_deleted += result.deleted_count
        groups_collapsed += 1
        logger.info(
            "Deduped locations %s/%s/%s: kept %s, removed %s",
            group["_id"].get("nation"),
            group["_id"].get("city") or "(nation-level)",
            group["_id"].get("slug"),
            survivor_id,
            result.deleted_count,
        )

    total_after = await db.locations.count_documents({})
    return {
        "groups_collapsed": groups_collapsed,
        "rows_deleted": rows_deleted,
        "total_before": total_before,
        "total_after": total_after,
    }


async def dedupe_cities(db) -> dict:
    """Same idea as `dedupe_locations` but for `cities` keyed on (nation, slug)."""
    total_before = await db.cities.count_documents({})
    pipeline = [
        {
            "$group": {
                "_id": {"nation": "$nation", "slug": "$slug"},
                "count": {"$sum": 1},
                "ids": {"$push": "$id"},
                "created_ats": {"$push": "$created_at"},
            }
        },
        {"$match": {"count": {"$gt": 1}}},
    ]
    groups_collapsed = 0
    rows_deleted = 0
    async for group in db.cities.aggregate(pipeline):
        pairs = list(zip(group["ids"], group["created_ats"]))
        pairs.sort(key=lambda x: x[1] or "")
        loser_ids = [p[0] for p in pairs[1:]]
        if not loser_ids:
            continue
        result = await db.cities.delete_many({"id": {"$in": loser_ids}})
        rows_deleted += result.deleted_count
        groups_collapsed += 1
    total_after = await db.cities.count_documents({})
    return {
        "groups_collapsed": groups_collapsed,
        "rows_deleted": rows_deleted,
        "total_before": total_before,
        "total_after": total_after,
    }


async def ensure_image_indexes(db) -> dict:
    """Non-unique index on `image_id` for cities + locations so the image-batch
    'missing image' survey (`image_id` null/missing) uses an index instead of a
    full COLLSCAN. The COLLSCAN was timing out against Atlas and pinning the
    single worker. Safe + idempotent (create_index is a no-op if it exists)."""
    created: list[str] = []
    created.append(await db.cities.create_index([("image_id", ASCENDING)], name="cities_image_id"))
    created.append(await db.locations.create_index([("image_id", ASCENDING)], name="locations_image_id"))
    return {"indexes_present": created, "ts": _now_iso()}


async def ensure_geo_indexes(db) -> dict:
    """Create the indexes that should have existed from day one. Idempotent —
    `create_index` is a no-op when an equivalent index already exists.

    - locations.(nation, city, slug) unique
    - locations.(nation, is_active) for the public list-by-nation path
    - cities.(nation, slug) unique
    - cities.(nation, is_active) for the public list path
    """
    created: list[str] = []
    # locations
    name = await db.locations.create_index(
        [("nation", ASCENDING), ("city", ASCENDING), ("slug", ASCENDING)],
        unique=True,
        name="locations_nation_city_slug_unique",
    )
    created.append(name)
    name = await db.locations.create_index(
        [("nation", ASCENDING), ("is_active", ASCENDING)],
        name="locations_nation_is_active",
    )
    created.append(name)
    # cities
    name = await db.cities.create_index(
        [("nation", ASCENDING), ("slug", ASCENDING)],
        unique=True,
        name="cities_nation_slug_unique",
    )
    created.append(name)
    name = await db.cities.create_index(
        [("nation", ASCENDING), ("is_active", ASCENDING)],
        name="cities_nation_is_active",
    )
    created.append(name)
    return {"indexes_present": created, "ts": _now_iso()}


async def run_full_cleanup(db) -> dict:
    """Convenience wrapper — dedupe everything then add indexes.

    Order matters: indexes are added AFTER dedupe because the unique index
    would otherwise refuse to create on a collection that contains
    duplicates.
    """
    loc_summary = await dedupe_locations(db)
    city_summary = await dedupe_cities(db)
    idx_summary = await ensure_geo_indexes(db)
    return {
        "locations": loc_summary,
        "cities": city_summary,
        "indexes": idx_summary,
    }
