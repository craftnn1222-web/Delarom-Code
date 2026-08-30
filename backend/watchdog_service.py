"""Operational watchdog.

A background loop that periodically inspects the app's health (database, disk,
the image-generation batch, data integrity, recent server errors), takes a small
set of SAFE auto-remediations, and records incidents. The admin Health page reads
the latest snapshot + incident log.

Design notes:
- Every check is wrapped so one failing probe never crashes the loop.
- Auto-remediation is intentionally limited to a known, safe playbook:
  (1) relaunch the image batch if it stalled with work remaining;
  (2) stop the image batch if disk is critically full (protects the DB).
- Human-in-the-loop for everything else: we log an incident, we do not touch code.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 120
DISK_WARN_PCT = 80.0
DISK_CRITICAL_PCT = 92.0
BATCH_HEARTBEAT_STALE_SECONDS = 420  # 7 min without a heartbeat while "running"


def _image_batch_autorun_enabled() -> bool:
    """Whether the watchdog may auto-(re)launch the image batch. Default OFF so
    the batch can NEVER wedge the single production worker / hammer Atlas on its
    own. Admins start it deliberately from the Health dashboard when desired."""
    return os.environ.get("ENABLE_IMAGE_BATCH_AUTORUN", "false").strip().lower() == "true"

# ---- in-memory state ----
_latest: Optional[dict] = None
_error_count = 0
_started = False
_prev_status: dict = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _now().isoformat()


def record_error() -> None:
    """Called by the HTTP middleware on any 5xx / unhandled exception."""
    global _error_count
    _error_count += 1


def _pop_errors() -> int:
    global _error_count
    n = _error_count
    _error_count = 0
    return n


def _age_seconds(iso_ts: Optional[str]) -> Optional[float]:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (_now() - dt).total_seconds()
    except Exception:
        return None


async def _log_incident(db, severity: str, category: str, message: str, action: str = "") -> None:
    try:
        await db.health_incidents.insert_one({
            "id": str(uuid.uuid4()),
            "ts": _iso(),
            "severity": severity,          # info | warning | critical
            "category": category,
            "message": message,
            "action_taken": action,
        })
    except Exception as e:  # pragma: no cover
        logger.warning(f"watchdog: could not log incident: {e}")


# ---- individual probes ----

async def _check_database(db) -> dict:
    out = {"status": "ok", "detail": "", "disk_pct": None, "data_mb": None, "storage_mb": None}
    try:
        await db.command("ping")
    except Exception as e:
        out["status"] = "critical"
        out["detail"] = f"MongoDB unreachable: {e}"
        return out
    try:
        ds = await db.command("dbstats")
        out["data_mb"] = round(ds.get("dataSize", 0) / 1048576, 1)
        out["storage_mb"] = round(ds.get("storageSize", 0) / 1048576, 1)
        fs_total = ds.get("fsTotalSize") or 0
        fs_used = ds.get("fsUsedSize") or 0
        if fs_total:
            pct = round(fs_used / fs_total * 100, 1)
            out["disk_pct"] = pct
            if pct >= DISK_CRITICAL_PCT:
                out["status"] = "critical"
                out["detail"] = f"Disk {pct}% full"
            elif pct >= DISK_WARN_PCT:
                out["status"] = "warning"
                out["detail"] = f"Disk {pct}% full"
    except Exception as e:
        out["status"] = "warning"
        out["detail"] = f"dbstats failed: {e}"
    return out


async def _check_image_batch(db) -> dict:
    out = {"status": "ok", "detail": "", "running": False, "remaining": None, "auto_continue": False, "stalled": False}
    try:
        from city_location_image_batcher import CityLocationImageBatcher
        status = CityLocationImageBatcher.get_status()
        survey = await CityLocationImageBatcher(db, batch_size=25).survey()
        remaining = survey.get("total_missing", 0)
        running = bool(status.get("is_running"))
        should_stop = bool(status.get("should_stop"))
        hb_age = _age_seconds(status.get("heartbeat_at"))
        out.update({
            "running": running,
            "remaining": remaining,
            "auto_continue": bool(status.get("auto_continue")),
        })
        # Stalled = there's work to do but the loop isn't running and wasn't
        # deliberately stopped by an admin; OR it claims running but the
        # heartbeat is stale.
        idle_with_work = (not running) and remaining > 0 and (not should_stop)
        heartbeat_dead = running and hb_age is not None and hb_age > BATCH_HEARTBEAT_STALE_SECONDS
        if idle_with_work or heartbeat_dead:
            out["stalled"] = True
            out["status"] = "warning"
            out["detail"] = "Batch stalled with images remaining"
        elif remaining == 0:
            out["detail"] = "All images generated"
        elif running:
            out["detail"] = f"Generating ({remaining} left)"
        else:
            out["detail"] = "Paused"
    except Exception as e:
        out["status"] = "warning"
        out["detail"] = f"batch probe failed: {e}"
    return out


async def _check_data_integrity(db) -> dict:
    out = {"status": "ok", "detail": "", "orphan_shops": 0, "images_in_db": 0}
    try:
        # Shops whose owner no longer exists.
        user_ids = set(await db.users.distinct("id"))
        orphans = 0
        async for s in db.shops.find({}, {"owner_id": 1}):
            oid = s.get("owner_id", "")
            if oid and not oid.startswith("NPC:") and oid not in user_ids:
                orphans += 1
        out["orphan_shops"] = orphans
        # Regression signal: image bytes should live in object storage, not Mongo.
        out["images_in_db"] = await db.image_blobs.count_documents({"data": {"$exists": True}})
        issues = []
        if orphans:
            issues.append(f"{orphans} orphaned shop(s)")
        if out["images_in_db"]:
            issues.append(f"{out['images_in_db']} image(s) still in DB")
        if issues:
            out["status"] = "warning"
            out["detail"] = ", ".join(issues)
    except Exception as e:
        out["status"] = "warning"
        out["detail"] = f"integrity probe failed: {e}"
    return out


def _rollup(*statuses: str) -> str:
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    return "ok"


async def run_health_checks(db, *, remediate: bool = True, reset_errors: bool = False) -> dict:
    """Run all probes once, optionally auto-remediate, and return a snapshot.

    Only the scheduled loop passes reset_errors=True — read-only/manual checks
    must not zero the 5xx counter, or they'd mask spikes from the next cycle."""
    global _latest
    errors = _pop_errors() if reset_errors else _error_count
    database = await _check_database(db)
    image_batch = await _check_image_batch(db)
    integrity = await _check_data_integrity(db)

    errors_status = "warning" if errors >= 10 else "ok"
    actions = []

    if remediate:
        # (1) Relaunch a stalled batch that still has work — ONLY when auto-run
        # is explicitly enabled. Default OFF: an unattended relaunch loop was
        # saturating the single production worker (COLLSCAN surveys timing out
        # against Atlas) and causing Cloudflare 520s on login.
        if image_batch.get("stalled") and not image_batch.get("running"):
            if _image_batch_autorun_enabled():
                try:
                    from city_location_image_batcher import CityLocationImageBatcher
                    CityLocationImageBatcher(db, batch_size=25).kick_off_background_batch(auto_continue=True)
                    msg = f"Relaunched stalled image batch ({image_batch.get('remaining')} images remaining)"
                    actions.append(msg)
                    await _log_incident(db, "warning", "image_batch", msg, action="relaunched")
                    image_batch["status"] = "ok"
                    image_batch["detail"] = "Auto-relaunched by watchdog"
                except Exception as e:
                    await _log_incident(db, "critical", "image_batch", f"Failed to relaunch batch: {e}")
            else:
                image_batch["detail"] = "Stalled with work remaining — auto-relaunch disabled (start manually)."
        # (2) Protect the DB: stop the batch if disk is critical.
        if database.get("status") == "critical" and image_batch.get("running"):
            try:
                from city_location_image_batcher import CityLocationImageBatcher
                CityLocationImageBatcher.request_stop()
                msg = f"Disk critical ({database.get('disk_pct')}%) — stopped image batch to protect the database"
                actions.append(msg)
                await _log_incident(db, "critical", "database", msg, action="stopped_batch")
            except Exception as e:
                await _log_incident(db, "critical", "database", f"Failed to stop batch on critical disk: {e}")
        # Log warnings/criticals — but only on a status transition, so a
        # persistent condition doesn't spam the incident log every cycle.
        for cat, status_val, detail in (
            ("database", database["status"], database.get("detail", "")),
            ("data_integrity", integrity["status"], integrity.get("detail", "")),
            ("errors", errors_status, f"{errors} server errors since last check"),
        ):
            if status_val in ("warning", "critical") and _prev_status.get(cat) != status_val:
                await _log_incident(db, status_val, cat, detail)
            _prev_status[cat] = status_val

    overall = _rollup(database["status"], image_batch["status"], integrity["status"], errors_status)
    snapshot = {
        "overall": overall,
        "checked_at": _iso(),
        "services": {
            "backend": {"status": "ok", "detail": "Responding"},
            "database": database,
            "image_batch": image_batch,
            "data_integrity": integrity,
            "errors": {"status": errors_status, "detail": f"{errors} server error(s) since last check", "count": errors},
        },
        "actions_taken": actions,
    }
    _latest = snapshot
    return snapshot


async def get_health(db) -> dict:
    """For the admin endpoint — return the latest snapshot, or compute one
    on demand (read-only, no remediation) if the loop hasn't run yet."""
    if _latest is not None:
        return _latest
    return await run_health_checks(db, remediate=False)


async def get_incidents(db, limit: int = 50) -> list:
    return await db.health_incidents.find({}, {"_id": 0}).sort("ts", -1).to_list(min(int(limit), 200))


async def watchdog_loop(db) -> None:
    global _started
    if _started:
        return
    _started = True
    logger.info("watchdog loop started")
    while True:
        try:
            snap = await run_health_checks(db, remediate=True, reset_errors=True)
            if snap["overall"] != "ok":
                logger.info(f"watchdog: overall={snap['overall']} actions={snap['actions_taken']}")
        except Exception as e:  # pragma: no cover
            logger.warning(f"watchdog cycle failed: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
