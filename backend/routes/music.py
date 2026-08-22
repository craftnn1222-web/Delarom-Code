"""Music routes — playlists per theme, multi-file upload, chunked upload
for large files, and per-track delete.

Registered from server.py via `attach_music_routes(...)`.

Storage layout
--------------
Files live at::

    MUSIC_DIR/
        {theme}/
            {track_id}__{safe-original-filename}

    _chunks/                            (transient)
        {upload_id}/
            .meta.json                  {theme, filename, size, ...}
            .part                       assembled bytes so far

Legacy files that used to sit directly under MUSIC_DIR (``global.mp3``,
``ammeonon.mp3``, ...) are still listed as a single-track playlist for
that theme so nothing already uploaded is lost.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel


AUDIO_EXTS = (".mp3", ".ogg", ".wav", ".m4a")
VALID_THEMES = (
    "global", "ammeonon", "selindori", "dhor-kuldor",
    "aigraels", "veiled-realms", "tavern",
)

CHUNK_LIMIT_BYTES = 4 * 1024 * 1024      # 4MB per chunk — safely under most ingress limits
MAX_TRACK_BYTES = 200 * 1024 * 1024      # 200MB per assembled file
MAX_UPLOADS_ACTIVE = 20                  # concurrent chunked upload sessions
CHUNK_TTL_SECONDS = 60 * 60              # abandoned sessions scrubbed after 1h


class FinalizePayload(BaseModel):
    upload_id: str
    theme: str
    filename: str


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


def _safe_filename(raw: str) -> str:
    """Strip unsafe characters and keep it short."""
    base = os.path.basename(raw or "").strip() or "track"
    base = _SAFE_NAME_RE.sub("_", base)
    return base[:120]


def _theme_dir(music_dir: Path, theme: str) -> Path:
    p = music_dir / theme
    p.mkdir(parents=True, exist_ok=True)
    return p


def _chunks_dir(music_dir: Path) -> Path:
    p = music_dir / "_chunks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reap_stale_chunks(music_dir: Path) -> None:
    root = _chunks_dir(music_dir)
    now = time.time()
    for d in list(root.iterdir()):
        try:
            if not d.is_dir():
                continue
            meta = d / ".meta.json"
            if not meta.exists() or (now - meta.stat().st_mtime) > CHUNK_TTL_SECONDS:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def _write_upload_to_theme(
    *, music_dir: Path, theme: str, upload: UploadFile,
) -> dict:
    """Stream an UploadFile to disk under the theme's directory."""
    if not upload.filename:
        raise HTTPException(status_code=400, detail="File has no name.")
    ext = Path(upload.filename).suffix.lower()
    if ext not in AUDIO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Only audio files allowed ({', '.join(AUDIO_EXTS)}).",
        )
    if theme not in VALID_THEMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}",
        )

    tid = uuid.uuid4().hex[:8]
    safe = _safe_filename(upload.filename)
    final = _theme_dir(music_dir, theme) / f"{tid}__{safe}"

    written = 0
    try:
        with open(final, "wb") as fp:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_TRACK_BYTES:
                    fp.close()
                    final.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large — max {MAX_TRACK_BYTES // (1024*1024)}MB per track.",
                    )
                fp.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        final.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    return {
        "id": tid,
        "theme": theme,
        "filename": final.name,
        "name": safe,
        "size": written,
        "url": f"/api/static/music/{theme}/{final.name}",
    }


def _scan_theme(music_dir: Path, theme: str) -> List[dict]:
    """Return tracks for a theme, including legacy top-level files."""
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
    # Legacy: MUSIC_DIR/{theme}.mp3 etc.
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
):
    # ─────────────────────────────────────────── LIST ────────────

    @api_router.get("/music/list")
    async def list_music():
        """All tracks grouped by theme + a flat array, plus a legacy list."""
        by_theme: dict = {t: _scan_theme(MUSIC_DIR, t) for t in VALID_THEMES}
        flat: List[dict] = []
        for _, rows in by_theme.items():
            flat.extend(rows)
        # Back-compat: only legacy top-level files were ever in this array.
        legacy_flat = [
            {"theme": r["theme"], "filename": r["filename"], "url": r["url"]}
            for r in flat if r.get("legacy")
        ]
        return {"themes": by_theme, "all": flat, "tracks": legacy_flat}

    # ─────────────────────────────────────────── UPLOAD ──────────

    @api_router.post("/admin/music/upload")
    async def upload_music(
        file: UploadFile = File(...),
        theme: str = Form("global"),
        current_user: User = Depends(get_current_user),
    ):
        """Upload a single audio file (small ≤ ~4MB via direct POST)."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        rec = _write_upload_to_theme(
            music_dir=MUSIC_DIR, theme=theme, upload=file,
        )
        return {"success": True, **rec, "message": f"Uploaded {rec['name']} to {theme}."}

    @api_router.post("/admin/music/upload-many")
    async def upload_music_many(
        files: List[UploadFile] = File(...),
        theme: str = Form("global"),
        current_user: User = Depends(get_current_user),
    ):
        """Upload several audio files at once (folder-drop, small files)."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        added: List[dict] = []
        skipped: List[dict] = []
        for f in files:
            try:
                added.append(_write_upload_to_theme(
                    music_dir=MUSIC_DIR, theme=theme, upload=f,
                ))
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
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        if theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        ext = Path(filename).suffix.lower()
        if ext not in AUDIO_EXTS:
            raise HTTPException(status_code=400, detail=f"Only audio files allowed ({', '.join(AUDIO_EXTS)}).")
        if size and size > MAX_TRACK_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large — max {MAX_TRACK_BYTES // (1024*1024)}MB per track.",
            )
        _reap_stale_chunks(MUSIC_DIR)
        root = _chunks_dir(MUSIC_DIR)
        active = sum(1 for _ in root.iterdir() if _.is_dir())
        if active >= MAX_UPLOADS_ACTIVE:
            raise HTTPException(status_code=429, detail="Too many active uploads. Try again shortly.")

        upload_id = uuid.uuid4().hex
        d = root / upload_id
        d.mkdir(parents=True, exist_ok=True)
        meta = {
            "theme": theme,
            "filename": _safe_filename(filename),
            "size_hint": int(size or 0),
            "created_at": time.time(),
        }
        (d / ".meta.json").write_text(json.dumps(meta))
        (d / ".part").touch()
        return {"upload_id": upload_id, "chunk_limit": CHUNK_LIMIT_BYTES}

    @api_router.post("/admin/music/chunk/append")
    async def chunk_append(
        upload_id: str = Form(...),
        chunk: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
    ):
        """Append the next chunk of bytes to an existing upload session."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        d = _chunks_dir(MUSIC_DIR) / upload_id
        meta_path = d / ".meta.json"
        part_path = d / ".part"
        if not meta_path.exists() or not part_path.exists():
            raise HTTPException(status_code=404, detail="Upload session not found (may have expired).")

        current_size = part_path.stat().st_size
        buf = await chunk.read()
        if len(buf) > CHUNK_LIMIT_BYTES + 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Chunk too large — keep chunks ≤ {CHUNK_LIMIT_BYTES // (1024*1024)}MB.",
            )
        if current_size + len(buf) > MAX_TRACK_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {MAX_TRACK_BYTES // (1024*1024)}MB limit.",
            )
        with open(part_path, "ab") as fp:
            fp.write(buf)
        return {"received": len(buf), "total": current_size + len(buf)}

    @api_router.post("/admin/music/chunk/finalize")
    async def chunk_finalize(
        payload: FinalizePayload,
        current_user: User = Depends(get_current_user),
    ):
        """Assemble a chunked upload into its final playlist slot."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        if payload.theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        ext = Path(payload.filename).suffix.lower()
        if ext not in AUDIO_EXTS:
            raise HTTPException(status_code=400, detail=f"Only audio files allowed ({', '.join(AUDIO_EXTS)}).")

        d = _chunks_dir(MUSIC_DIR) / payload.upload_id
        part = d / ".part"
        if not part.exists():
            raise HTTPException(status_code=404, detail="Upload session not found.")
        if part.stat().st_size == 0:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(status_code=400, detail="No bytes uploaded for this session.")

        tid = uuid.uuid4().hex[:8]
        safe = _safe_filename(payload.filename)
        final = _theme_dir(MUSIC_DIR, payload.theme) / f"{tid}__{safe}"
        shutil.move(str(part), str(final))
        shutil.rmtree(d, ignore_errors=True)
        return {
            "success": True,
            "id": tid,
            "theme": payload.theme,
            "filename": final.name,
            "name": safe,
            "size": final.stat().st_size,
            "url": f"/api/static/music/{payload.theme}/{final.name}",
            "message": f"Uploaded {safe} to {payload.theme}.",
        }

    @api_router.post("/admin/music/chunk/abort")
    async def chunk_abort(
        upload_id: str = Form(...),
        current_user: User = Depends(get_current_user),
    ):
        """Discard a chunked upload session."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        d = _chunks_dir(MUSIC_DIR) / upload_id
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        return {"aborted": True}

    # ─────────────────────────────────────────── DELETE ──────────

    @api_router.delete("/admin/music/theme/{theme}")
    async def wipe_theme(
        theme: str,
        current_user: User = Depends(get_current_user),
    ):
        """Wipe all tracks for a theme."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        if theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        removed = 0
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
        """Delete a single track file from a theme."""
        if getattr(current_user, "role", "") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        if theme not in VALID_THEMES:
            raise HTTPException(status_code=400, detail=f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
        safe = _safe_filename(filename)
        theme_root = (MUSIC_DIR / theme).resolve()
        candidate = (MUSIC_DIR / theme / safe).resolve()
        # Guard: no directory-escape
        if candidate.parent != theme_root:
            raise HTTPException(status_code=400, detail="Illegal filename.")
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            return {"deleted": True, "theme": theme, "filename": safe}
        # Legacy top-level file (e.g., global.mp3)
        legacy = (MUSIC_DIR / safe).resolve()
        if legacy.parent == MUSIC_DIR.resolve() and legacy.exists() and legacy.is_file():
            legacy.unlink()
            return {"deleted": True, "legacy": True}
        raise HTTPException(status_code=404, detail="Track not found.")
