"""Direct-Mongo observation probe for the image batch durability + missing-query fixes.

Not a pytest suite — a read-only observation script (run repeatedly to watch progress).
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

MISSING_NEW = {
    "$and": [
        {"$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}]},
        {"$or": [{"image_id": None}, {"image_id": ""}, {"image_id": {"$exists": False}}]},
    ],
}
MISSING_OLD = {"$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}]}

ONLY_IMAGE_ID = {
    "$and": [
        {"$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}]},
        {"image_id": {"$nin": [None, ""]}},
    ],
}


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    doc = await db.image_batch_state.find_one({"_id": "singleton"})
    out = {"state_doc": doc}

    for coll in ("cities", "locations"):
        out[f"{coll}_missing_new"] = await db[coll].count_documents(MISSING_NEW)
        out[f"{coll}_missing_old"] = await db[coll].count_documents(MISSING_OLD)
        out[f"{coll}_only_image_id"] = await db[coll].count_documents(ONLY_IMAGE_ID)

    out["total_missing_new"] = out["cities_missing_new"] + out["locations_missing_new"]
    out["total_missing_old"] = out["cities_missing_old"] + out["locations_missing_old"]

    names = await db.cities.find(ONLY_IMAGE_ID, {"_id": 0, "name": 1, "slug": 1}).limit(15).to_list(15)
    out["cities_only_image_id_sample"] = names

    # Are the only-image_id cities excluded by the NEW query?
    slugs = [c.get("slug") for c in names if c.get("slug")]
    if slugs:
        leak = await db.cities.count_documents({"$and": [MISSING_NEW, {"slug": {"$in": slugs}}]})
        out["only_image_id_leaking_into_new_query"] = leak

    print(json.dumps(out, indent=2, default=str))
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
