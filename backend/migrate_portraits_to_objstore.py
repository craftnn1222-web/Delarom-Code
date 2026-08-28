"""One-shot migration: move legacy base64 character portraits out of MongoDB.

Historically, `POST /characters/{id}/upload-image` stored the uploaded image as
a `data:image/...;base64,...` string directly on the character document. That
inflated any list endpoint returning portraits (notably the member directory)
to multiple megabytes, saturating the backend behind the production proxy.

This script rewrites each such portrait to object storage and replaces the
`portrait_url` with a short `/api/image/{id}` reference. Idempotent: characters
whose portrait is already a short URL are skipped.

Run: `python /app/backend/migrate_portraits_to_objstore.py`
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

import object_storage  # noqa: E402
from image_service import ImageService  # noqa: E402


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    object_storage.init_storage()
    img_service = ImageService(db)

    cursor = db.characters.find(
        {"portrait_url": {"$regex": "^data:"}},
        {"id": 1, "name": 1, "portrait_url": 1},
    )
    migrated = 0
    failed = 0
    async for char in cursor:
        data_url = char.get("portrait_url")
        image_id = await img_service.store_from_data_url(data_url)
        if image_id:
            await db.characters.update_one(
                {"id": char["id"]},
                {"$set": {"portrait_url": f"/api/image/{image_id}", "image_id": image_id}},
            )
            migrated += 1
            print(f"migrated: {char.get('name')} ({char['id']}) -> /api/image/{image_id}")
        else:
            failed += 1
            print(f"FAILED to decode portrait for {char.get('name')} ({char['id']})")

    remaining = await db.characters.count_documents({"portrait_url": {"$regex": "^data:"}})
    print(f"\nDONE. migrated={migrated} failed={failed} remaining_base64={remaining}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
