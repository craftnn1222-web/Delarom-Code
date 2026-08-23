"""Emergent-managed object storage client.

Stores binary assets (AI-generated images) outside MongoDB so the DB volume
stays tiny. All access is proxied through our backend — the storage service
issues no presigned/public URLs. See the integration playbook.

Blocking `requests` calls are wrapped with `asyncio.to_thread` by callers on
the async hot path (image serving) so the event loop is never blocked.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

APP_NAME = "continents-of-delarom"

_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

_storage_key: str | None = None


def _storage_url() -> str:
    # Read lazily: env (INTEGRATION_PROXY_URL, and .env-loaded keys) may not be
    # populated at import time. `or`, not default= — platform sets "" for empty.
    base = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
    return base.rstrip("/") + "/objstore/api/v1/storage"


def _emergent_key() -> str | None:
    return os.environ.get("EMERGENT_LLM_KEY")


def ext_for_mime(mime: str) -> str:
    return _MIME_EXT.get((mime or "").lower(), "png")


def init_storage(force: bool = False) -> str:
    """Mint (or reuse) a session-scoped storage key. Call once; re-init only to
    recover from an inactive key."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{_storage_url()}/init", json={"emergent_key": _emergent_key()}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes; returns {"path","size","etag"}. Retries once on a dead key."""
    key = init_storage()
    url = f"{_storage_url()}/objects/{path}"
    resp = requests.put(url, headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code in (403, 404):
        key = init_storage(force=True)
        resp = requests.put(url, headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    """Download bytes; returns (content, content_type). Retries once on a dead key."""
    key = init_storage()
    url = f"{_storage_url()}/objects/{path}"
    resp = requests.get(url, headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code in (403, 404):
        # Ambiguous 404 (missing path vs dead key): refresh key once and retry.
        key = init_storage(force=True)
        resp = requests.get(url, headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
