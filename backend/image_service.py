"""Image storage service.

Centralizes binary storage so the rest of the app doesn't have to think about
where images live. Images live in their own `image_blobs` collection and are
referenced by a short `image_id` string. Parent documents (city, nation, NPC,
etc.) store only that ID — keeping their payloads tiny.

This is a strict improvement over the legacy pattern of embedding
`data:image/...;base64,…` strings directly in parent documents, which inflated
every list endpoint to many megabytes.
"""

from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from bson.binary import Binary
from motor.motor_asyncio import AsyncIOMotorDatabase


# data:<mime>;base64,<payload>
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w/+.\-]+);base64,(?P<data>.+)$", re.DOTALL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ImageService:
    """Tiny wrapper over the `image_blobs` collection.

    Keeps the model simple: one collection, raw BSON Binary blobs, indexed by
    a UUID `id`. We do not put images on disk because the pod's filesystem is
    ephemeral — Mongo persists across restarts.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.coll = db.image_blobs

    @staticmethod
    def parse_data_url(data_url: str) -> Optional[Tuple[str, bytes]]:
        """Decode a `data:image/...;base64,XXX` string. Returns (mime, bytes) or None."""
        if not data_url or not isinstance(data_url, str):
            return None
        m = _DATA_URL_RE.match(data_url.strip())
        if not m:
            return None
        raw = None
        try:
            raw = base64.b64decode(m.group("data"))
        except Exception:
            return None
        if raw is None:
            return None
        return m.group("mime"), raw

    async def get(self, image_id: str) -> Optional[dict]:
        if not image_id:
            return None
        return await self.coll.find_one({"id": image_id}, {"_id": 0})

    async def store_bytes(self, raw: bytes, mime_type: str = "image/png") -> str:
        """Persist raw bytes and return the new image_id."""
        image_id = str(uuid.uuid4())
        await self.coll.insert_one({
            "id": image_id,
            "mime_type": mime_type,
            "data": Binary(raw),
            "size": len(raw),
            "created_at": _now_iso(),
        })
        return image_id

    async def store_from_data_url(self, data_url: str) -> Optional[str]:
        """Convenience: decode a data: URL and persist. Returns image_id or None."""
        parsed = self.parse_data_url(data_url)
        if not parsed:
            return None
        mime, raw = parsed
        return await self.store_bytes(raw, mime_type=mime)

    async def delete(self, image_id: str) -> None:
        if not image_id:
            return
        await self.coll.delete_one({"id": image_id})

    # ---------- Lazy migration helpers ----------

    async def ensure_migrated(
        self,
        collection_name: str,
        match_query: dict,
    ) -> Optional[str]:
        """If a document in `collection_name` matching `match_query` still has a
        legacy `image_url` base64 string, migrate it to image_blobs in-place
        and return the new `image_id`. If the doc already has an `image_id`,
        return it unchanged. Returns None if the doc has no image at all.

        This lets us migrate the existing seeded data lazily as endpoints are
        hit, without a separate migration script.
        """
        coll = self.db[collection_name]
        doc = await coll.find_one(match_query, {"_id": 0, "image_id": 1, "image_url": 1})
        if not doc:
            return None
        if doc.get("image_id"):
            return doc["image_id"]
        legacy = doc.get("image_url")
        if not legacy:
            return None
        new_id = await self.store_from_data_url(legacy)
        if not new_id:
            return None
        await coll.update_one(
            match_query,
            {"$set": {"image_id": new_id}, "$unset": {"image_url": ""}},
        )
        return new_id
