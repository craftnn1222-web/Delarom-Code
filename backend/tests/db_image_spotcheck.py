"""Direct DB spot-check for city/location artwork state."""
import asyncio
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    for coll in ("cities", "locations"):
        c = db[coll]
        total = await c.count_documents({})
        with_url = await c.count_documents({"image_url": {"$regex": "^data:image/"}})
        with_id = await c.count_documents({"image_id": {"$exists": True, "$ne": None, "$nin": [""]}})
        migrated_no_url = await c.count_documents({
            "image_id": {"$exists": True, "$ne": None, "$nin": [""]},
            "$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}],
        })
        missing_url = await c.count_documents({
            "$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}]
        })
        print(f"{coll}: total={total} data_url={with_url} image_id={with_id} "
              f"image_id_but_no_url(REGEN RISK)={migrated_no_url} survey_missing={missing_url}")
    blobs = await db.image_blobs.count_documents({})
    print("image_blobs:", blobs)
    sample = await db.cities.find_one({"image_url": {"$regex": "^data:image/"}}, {"_id": 0, "name": 1, "image_url": 1})
    if sample:
        print(f"sample city={sample['name']} bytes={len(sample['image_url'])} prefix={sample['image_url'][:30]}")
    client.close()


asyncio.run(main())
