"""One-off + resumable migration: move image bytes out of MongoDB (BSON Binary
in `image_blobs.data`) into Emergent object storage.

For each blob that still has an inline `data` field: upload the bytes to object
storage, set `storage_path` + `size`, and unset `data`. Idempotent and
resumable — safe to re-run; it only touches docs that still hold `data`.

Run:  INTEGRATION_PROXY_URL=... python migrate_images_to_objstore.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import object_storage as ob  # noqa: E402

QUERY = {"data": {"$exists": True}}


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    coll = db.image_blobs
    total = await coll.count_documents(QUERY)
    print(f"[migrate] {total} blobs to move", flush=True)
    ob.init_storage()

    migrated = 0
    failed = 0
    cursor = coll.find(QUERY, {"id": 1, "mime_type": 1, "data": 1})
    async for doc in cursor:
        image_id = doc.get("id")
        data = doc.get("data")
        mime = doc.get("mime_type", "image/png")
        if not image_id or not data:
            continue
        try:
            ext = ob.ext_for_mime(mime)
            path = f"{ob.APP_NAME}/images/{image_id}.{ext}"
            result = await asyncio.to_thread(ob.put_object, path, bytes(data), mime)
            await coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"storage_path": result["path"], "size": result.get("size", len(data))},
                 "$unset": {"data": ""}},
            )
            migrated += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[migrate] FAILED {image_id}: {e}", flush=True)
        if (migrated + failed) % 50 == 0:
            print(f"[migrate] progress: migrated={migrated} failed={failed}", flush=True)

    remaining = await coll.count_documents(QUERY)
    print(f"[migrate] DONE migrated={migrated} failed={failed} remaining={remaining}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
