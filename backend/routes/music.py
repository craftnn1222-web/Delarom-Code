"""Music routes — playlists per theme, multi-file upload, chunked upload
for large files, and per-track delete.

Registered from server.py via `attach_music_routes(...)`.

Storage
-------
New uploads are streamed to **Emergent object storage** (the pod filesystem is
ephemeral on deployed apps, so uploaded files must not live on disk). Each track
keeps a small metadata document in the ``music_tracks`` Mongo collection::

    { id, theme, name, filename, size, mime, storage_path, created_at }

and is served back through ``GET /api/music/stream/{track_id}`` (with HTTP Range
support so the player can seek).

Legacy files that shipped on disk under ``MUSIC_DIR`` (e.g. ``global.mp3``) are
still listed and served read-only via the ``/api/static`` mount, so nothing
already present is lost.
"""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

import object_storage


AUDIO_EXTS = (".mp3", ".ogg", ".wav", ".m4a")
VALID_THEMES = (
    "global", "ammeonon", "selindori", "dhor-kuldor",
    "aigraels", "veiled-realms", "tavern",
)

CHUNK_LIMIT_BYTES = 4 * 1024 * 1024      # 4MB per chunk — safely under most ingress limits
MAX_TRACK_BYTES = 200 * 1024 * 1024      # 200MB per assembled file
MAX_UPLOADS_ACTIVE = 20                  # concurrent chunked upload sessions
CHUNK_TTL_SECONDS = 60 * 60              # abandoned sessions scrubbed after 1h

_AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}

# In-memory assembly buffers for chunked uploads: {upload_id: {...}}. The pod
# filesystem is ephemeral, so we never touch disk — bounded by MAX_TRACK_BYTES
# per session and MAX_UPLOADS_ACTIVE concurrent sessions.
_CHUNK_SESSIONS: Dict[str, dict] = {}

# Tiny LRU-ish byte cache so repeated Range requests for the same track don't
# re-fetch the whole object from storage every seek.
_STREAM_CACHE: Dict[str, tuple] = {}      # {track_id: (bytes, mime)}
_STREAM_CACHE_MAX = 4


class FinalizePayload(BaseModel):
    upload_id: str
    theme: str
    filename: str


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


def _safe_filename(raw: str) -> str:
    """Strip unsafe characters and keep it short."""
    import os
    base = os.path.basename(raw or "").strip() or "track"
    base = _SAFE_NAME_RE.sub("_", base)
    return base[:120]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mime_for(filename: str) -> str:
    return _AUDIO_MIME.get(Path(filename).suffix.lower(), "audio/mpeg")


def _validate_theme_ext(theme: str, filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail=f"Only audio files allowed ({', '.join(AUDIO_EXTS)}).")
    if theme not in VALID_THEMES:
        raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
    return ext


def _reap_stale_sessions() -> None:
    now = time.time()
    for uid in list(_CHUNK_SESSIONS.keys()):
        sess = _CHUNK_SESSIONS.get(uid)
        if not sess or (now - sess.get("created_at", now)) > CHUNK_TTL_SECONDS:
            _CHUNK_SESSIONS.pop(uid, None)


async def _store_track(db, *, theme: str, filename: str, data: bytes) -> dict:
    """Persist raw bytes to object storage + a metadata doc in Mongo."""
    ext = _validate_theme_ext(theme, filename)
    if len(data) > MAX_TRACK_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large — max {MAX_TRACK_BYTES // (1024*1024)}MB per track.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    tid = uuid.uuid4().hex[:8]
    safe = _safe_filename(filename)
    mime = _AUDIO_MIME.get(ext, "audio/mpeg")
    stored_name = f"{tid}__{safe}"
    path = f"{object_storage.APP_NAME}/music/{tid}{ext}"
    result = await asyncio.to_thread(object_storage.put_object, path, data, mime)
    doc = {
        "id": tid,
        "theme": theme,
        "name": safe,
        "filename": stored_name,
        "size": result.get("size", len(data)),
        "mime": mime,
        "storage_path": result["path"],
        "created_at": _now_iso(),
    }
    await db.music_tracks.insert_one(dict(doc))
    doc.pop("_id", None)
    return {
        "id": tid,
        "theme": theme,
        "filename": stored_name,
        "name": safe,
        "size": doc["size"],
        "url": f"/api/music/stream/{tid}",
    }


def _scan_legacy_disk(music_dir: Path, theme: str) -> List[dict]:
    """Read-only listing of legacy on-disk files for a theme (no writes)."""
    tracks: List[dict] = []
    tdir = music_dir / theme
    if tdir.exists() and tdir.is_dir():
        for f in sorted(tdir.iterdir(), key=lambda p: p.name.lower()):
            if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
                continue
            tid, sep, base = f.name.partition("__")
            display = base if sep else f.name
            tracks.append({
                "id": tid if sep else f.stem,
                "theme": theme,
                "filename": f.name,
                "name": display,
                "size": f.stat().st_size,
                "url": f"/api/static/music/{theme}/{f.name}",
            })
    for ext in AUDIO_EXTS:
        legacy = music_dir / f"{theme}{ext}"
        if legacy.exists() and legacy.is_file():
            tracks.append({
                "id": f"legacy-{theme}",
                "theme": theme,
                "filename": legacy.name,
                "name": legacy.name,
                "size": legacy.stat().st_size,
                "url": f"/api/static/music/{legacy.name}",
                "legacy": True,
            })
    return tracks


def attach_music_routes(
    api_router: APIRouter,
    *,
    User,
    get_current_user,
    MUSIC_DIR: Path,
    db,
):
    def _require_admin(current_user) -> None:
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")

    # ─────────────────────────────────────────── LIST ────────────

    @api_router.get("/music/list")
    async def list_music():
        """All tracks grouped by theme + a flat array, plus a legacy list."""
        by_theme: dict = {}
        for theme in VALID_THEMES:
            rows = _scan_legacy_disk(MUSIC_DIR, theme)
            uploaded = await db.music_tracks.find({"theme": theme}, {"_id": 0}).sort("created_at", 1).to_list(500)
            for u in uploaded:
                rows.append({
                    "id": u["id"],
                    "theme": theme,
                    "filename": u.get("filename"),
                    "name": u.get("name") or u.get("filename"),
                    "size": u.get("size", 0),
                    "url": f"/api/music/stream/{u['id']}",
                })
            by_theme[theme] = rows
        flat: List[dict] = []
        for _, rows in by_theme.items():
            flat.extend(rows)
        legacy_flat = [
            {"theme": r["theme"], "filename": r["filename"], "url": r["url"]}
            for r in flat if r.get("legacy")
        ]
        return {"themes": by_theme, "all": flat, "tracks": legacy_flat}

    # ─────────────────────────────────────────── STREAM ──────────

    @api_router.api_route("/music/stream/{track_id}", methods=["GET", "HEAD"])
    async def stream_music(track_id: str, request: Request):
        """Serve an uploaded track from object storage, with HTTP Range support."""
        cached = _STREAM_CACHE.get(track_id)
        if cached:
            data, mime = cached
        else:
            doc = await db.music_tracks.find_one({"id": track_id}, {"_id": 0})
            if not doc or not doc.get("storage_path"):
                raise HTTPException(status_code=404, detail="Track not found")
            data, ctype = await asyncio.to_thread(object_storage.get_object, doc["storage_path"])
            mime = doc.get("mime") or ctype or "audio/mpeg"
            if len(_STREAM_CACHE) >= _STREAM_CACHE_MAX:
                _STREAM_CACHE.pop(next(iter(_STREAM_CACHE)))
            _STREAM_CACHE[track_id] = (data, mime)

        total = len(data)
        base_headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        }
        range_header = request.headers.get("range")
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                start = int(m.group(1)) if m.group(1) else 0
                end = int(m.group(2)) if m.group(2) else total - 1
                start = max(0, start)
                end = min(end, total - 1)
                if start > end:
                    return Response(status_code=416, headers={"Content-Range": f"bytes */{total}"})
                body = b"" if request.method == "HEAD" else data[start:end + 1]
                headers = {
                    **base_headers,
                    "Content-Range": f"bytes {start}-{end}/{total}",
                    "Content-Length": str(end - start + 1),
                }
                return Response(content=body, status_code=206, media_type=mime, headers=headers)

        body = b"" if request.method == "HEAD" else data
        headers = {**base_headers, "Content-Length": str(total)}
        return Response(content=body, media_type=mime, headers=headers)

    # ─────────────────────────────────────────── UPLOAD ──────────

    @api_router.post("/admin/music/upload")
    async def upload_music(
        file: UploadFile = File(...),
        theme: str = Form("global"),
        current_user: User = Depends(get_current_user),
    ):
        """Upload a single audio file (small ≤ ~4MB via direct POST)."""
        _require_admin(current_user)
        data = await file.read()
        rec = await _store_track(db, theme=theme, filename=file.filename or "track", data=data)
        return {"success": True, **rec, "message": f"Uploaded {rec['name']} to {theme}."}

    @api_router.post("/admin/music/upload-many")
    async def upload_music_many(
        files: List[UploadFile] = File(...),
        theme: str = Form("global"),
        current_user: User = Depends(get_current_user),
    ):
        """Upload several audio files at once (folder-drop, small files)."""
        _require_admin(current_user)
        added: List[dict] = []
        skipped: List[dict] = []
        for f in files:
            try:
                data = await f.read()
                added.append(await _store_track(db, theme=theme, filename=f.filename or "track", data=data))
            except HTTPException as he:
                skipped.append({"filename": f.filename, "reason": he.detail})
        return {
            "success": True,
            "theme": theme,
            "added": added,
            "skipped": skipped,
            "message": f"{len(added)} added, {len(skipped)} skipped.",
        }

    # ─────────────────────────────────────────── CHUNKED UPLOAD ──

    @api_router.post("/admin/music/chunk/init")
    async def chunk_init(
        theme: str = Form(...),
        filename: str = Form(...),
        size: int = Form(0),
        current_user: User = Depends(get_current_user),
    ):
        """Begin a chunked upload session. Returns `upload_id`."""
        _require_admin(current_user)
        _validate_theme_ext(theme, filename)
        if size and size > MAX_TRACK_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large — max {MAX_TRACK_BYTES // (1024*1024)}MB per track.")
        _reap_stale_sessions()
        if len(_CHUNK_SESSIONS) >= MAX_UPLOADS_ACTIVE:
            raise HTTPException(status_code=429, detail="Too many active uploads. Try again shortly.")
        upload_id = uuid.uuid4().hex
        _CHUNK_SESSIONS[upload_id] = {
            "theme": theme,
            "filename": _safe_filename(filename),
            "buf": bytearray(),
            "created_at": time.time(),
        }
        return {"upload_id": upload_id, "chunk_limit": CHUNK_LIMIT_BYTES}

    @api_router.post("/admin/music/chunk/append")
    async def chunk_append(
        upload_id: str = Form(...),
        chunk: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
    ):
        """Append the next chunk of bytes to an existing upload session."""
        _require_admin(current_user)
        sess = _CHUNK_SESSIONS.get(upload_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Upload session not found (may have expired).")
        buf = await chunk.read()
        if len(buf) > CHUNK_LIMIT_BYTES + 1024:
            raise HTTPException(status_code=413, detail=f"Chunk too large — keep chunks ≤ {CHUNK_LIMIT_BYTES // (1024*1024)}MB.")
        if len(sess["buf"]) + len(buf) > MAX_TRACK_BYTES:
            _CHUNK_SESSIONS.pop(upload_id, None)
            raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_TRACK_BYTES // (1024*1024)}MB limit.")
        sess["buf"].extend(buf)
        return {"received": len(buf), "total": len(sess["buf"])}

    @api_router.post("/admin/music/chunk/finalize")
    async def chunk_finalize(
        payload: FinalizePayload,
        current_user: User = Depends(get_current_user),
    ):
        """Assemble a chunked upload into its final playlist slot."""
        _require_admin(current_user)
        sess = _CHUNK_SESSIONS.get(payload.upload_id)
        if not sess:
            raise HTTPException(status_code=404, detail="Upload session not found.")
        data = bytes(sess["buf"])
        if not data:
            _CHUNK_SESSIONS.pop(payload.upload_id, None)
            raise HTTPException(status_code=400, detail="No bytes uploaded for this session.")
        try:
            rec = await _store_track(db, theme=payload.theme, filename=payload.filename, data=data)
        finally:
            _CHUNK_SESSIONS.pop(payload.upload_id, None)
        return {
            "success": True,
            **rec,
            "message": f"Uploaded {rec['name']} to {payload.theme}.",
        }

    @api_router.post("/admin/music/chunk/abort")
    async def chunk_abort(
        upload_id: str = Form(...),
        current_user: User = Depends(get_current_user),
    ):
        """Discard a chunked upload session."""
        _require_admin(current_user)
        _CHUNK_SESSIONS.pop(upload_id, None)
        return {"aborted": True}

    # ─────────────────────────────────────────── DELETE ──────────

    @api_router.delete("/admin/music/theme/{theme}")
    async def wipe_theme(
        theme: str,
        current_user: User = Depends(get_current_user),
    ):
        """Wipe all tracks for a theme (uploaded + legacy disk)."""
        _require_admin(current_user)
        if theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        # Uploaded tracks in object storage + Mongo
        uploaded = await db.music_tracks.find({"theme": theme}, {"_id": 0, "storage_path": 1, "id": 1}).to_list(500)
        for u in uploaded:
            if u.get("storage_path"):
                try:
                    await asyncio.to_thread(object_storage.delete_object, u["storage_path"])
                except Exception:
                    pass
            _STREAM_CACHE.pop(u.get("id"), None)
        res = await db.music_tracks.delete_many({"theme": theme})
        removed = res.deleted_count
        # Legacy disk files (read+unlink; not an upload write)
        tdir = MUSIC_DIR / theme
        if tdir.exists() and tdir.is_dir():
            for f in list(tdir.iterdir()):
                if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
                    f.unlink()
                    removed += 1
        for ext in AUDIO_EXTS:
            legacy = MUSIC_DIR / f"{theme}{ext}"
            if legacy.exists():
                legacy.unlink()
                removed += 1
        return {"deleted": removed, "theme": theme}

    @api_router.delete("/admin/music/{theme}/{filename}")
    async def delete_music(
        theme: str,
        filename: str,
        current_user: User = Depends(get_current_user),
    ):
        """Delete a single track from a theme (uploaded or legacy disk)."""
        _require_admin(current_user)
        if theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        safe = _safe_filename(filename)
        # Uploaded track match (by stored filename)
        doc = await db.music_tracks.find_one({"theme": theme, "filename": safe}, {"_id": 0})
        if not doc:
            doc = await db.music_tracks.find_one({"theme": theme, "filename": filename}, {"_id": 0})
        if doc:
            if doc.get("storage_path"):
                try:
                    await asyncio.to_thread(object_storage.delete_object, doc["storage_path"])
                except Exception:
                    pass
            _STREAM_CACHE.pop(doc.get("id"), None)
            await db.music_tracks.delete_one({"id": doc["id"]})
            return {"deleted": True, "theme": theme, "filename": doc.get("filename")}
        # Legacy disk file (read+unlink)
        theme_root = (MUSIC_DIR / theme).resolve()
        candidate = (MUSIC_DIR / theme / safe).resolve()
        if candidate.parent != theme_root:
            raise HTTPException(status_code=400, detail="Illegal filename.")
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            return {"deleted": True, "theme": theme, "filename": safe}
        legacy = (MUSIC_DIR / safe).resolve()
        if legacy.parent == MUSIC_DIR.resolve() and legacy.exists() and legacy.is_file():
            legacy.unlink()
            return {"deleted": True, "legacy": True}
        raise HTTPException(status_code=404, detail="Track not found.")
