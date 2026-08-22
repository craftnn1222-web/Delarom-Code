"""One-shot migration: rename dhor-khuldor → dhor-kuldor across all Mongo collections.

Idempotent — running twice is a no-op (nothing to rename if already migrated).
"""
from __future__ import annotations

import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient

OLD_SLUG = "dhor-khuldor"
NEW_SLUG = "dhor-kuldor"
OLD_HYPHEN_NAME = "Dhor-Khuldor"
NEW_HYPHEN_NAME = "Dhor-Kuldor"


async def _migrate_field(coll, field: str) -> int:
    """Rename occurrences of the old slug in one field. Returns rows touched."""
    result = await coll.update_many(
        {field: OLD_SLUG}, {"$set": {field: NEW_SLUG}}
    )
    return result.modified_count


async def _migrate_field_ilike(coll, field: str) -> int:
    """Rename any exact match of the old name — case insensitive."""
    result = await coll.update_many(
        {field: {"$regex": f"^{OLD_HYPHEN_NAME}$", "$options": "i"}},
        {"$set": {field: NEW_HYPHEN_NAME}},
    )
    return result.modified_count


async def main() -> None:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    touched: dict = {}

    # Collections with a `nation` field
    for coll_name in [
        "cities", "locations", "npcs", "faction_npcs", "factions",
        "characters", "shops", "items", "quests", "rumors", "bounties",
        "crimes", "chronicles", "trials", "trade_caravans", "diplomacy",
        "city_market_prices", "goods_catalogue",
    ]:
        touched[coll_name] = await _migrate_field(db[coll_name], "nation")

    # world_state has a nested `nations.{slug}` dict — do it separately.
    world = await db.world_state.find_one({})
    if world and isinstance(world.get("nations"), dict) and OLD_SLUG in world["nations"]:
        world["nations"][NEW_SLUG] = world["nations"].pop(OLD_SLUG)
        await db.world_state.update_one({"_id": world["_id"]}, {"$set": {"nations": world["nations"]}})
        touched["world_state.nations"] = 1
    else:
        touched["world_state.nations"] = 0

    # Diplomacy pairs — from_nation / to_nation
    touched["diplomacy_from"] = await _migrate_field(db.diplomacy, "from_nation")
    touched["diplomacy_to"] = await _migrate_field(db.diplomacy, "to_nation")

    # Print summary
    total = sum(touched.values())
    print(f"[migrate] Rename {OLD_SLUG} → {NEW_SLUG} — {total} rows touched.")
    for k, v in touched.items():
        if v:
            print(f"  {k}: {v}")
    if total == 0:
        print("  (already migrated — no rows had the old slug)")


if __name__ == "__main__":
    asyncio.run(main())
