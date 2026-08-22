"""Seed starter factions for Continents of Delarom.

Each faction is drawn from existing world lore (Dhor Kuldor guilds,
Aigraels Triumvirate, etc.). Idempotent — re-running just updates the
copy without disturbing existing memberships.

The catalogue lives in `starter_factions.py` so the in-app admin
endpoint `POST /api/factions/admin/seed-starter` can use the same data.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from starter_factions import STARTER_FACTIONS


async def main() -> None:
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    now = datetime.now(timezone.utc).isoformat()
    inserted, updated = 0, 0

    for f in STARTER_FACTIONS:
        existing = await db.factions.find_one({"slug": f["slug"]}, {"_id": 0, "id": 1, "member_count": 1})
        doc = {
            **f,
            "is_active": True,
            "is_secret": False,
            "leader_character_id": None,
        }
        if existing:
            doc["id"] = existing["id"]
            doc["founded_at"] = None  # not overwriting; rely on the prior value
            await db.factions.update_one(
                {"id": existing["id"]},
                {"$set": {k: v for k, v in doc.items() if v is not None and k != "id"}},
            )
            updated += 1
            print(f"  • updated  {f['name']:30s}  ({f['slug']})")
        else:
            doc["id"] = str(uuid.uuid4())
            doc["founded_at"] = now
            doc["member_count"] = 0
            await db.factions.insert_one(doc)
            inserted += 1
            print(f"  + inserted {f['name']:30s}  ({f['slug']})")

    print(f"\nDone. {inserted} new · {updated} updated · {len(STARTER_FACTIONS)} total.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
