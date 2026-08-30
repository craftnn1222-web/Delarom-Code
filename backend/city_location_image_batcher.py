"""Server-side batch image generator for cities and locations missing images.

Drives `gpt-image-1` via the Emergent LLM key. Two modes:

  • **Single-batch mode** (`auto_continue=False`): processes one batch of
    up to `batch_size` entities (default 25) as a background task, then
    stops. Admin polls status + re-clicks.

  • **Run-until-done mode** (`auto_continue=True`): the background task
    loops batch-after-batch until the survey reports zero missing entities
    (or a safety cap of MAX_ITERATIONS is hit). Tolerant of transient
    failures — keeps going as long as forward progress is being made. The
    admin UI can be closed and the server keeps grinding.

**Durability** (fixes iteration_23 CRITICAL): Job state is persisted to
`image_batch_state` Mongo collection on every batch. On server startup,
`resume_if_needed` checks the persisted state — if it was `is_running=True`
with `auto_continue=True` when the process died AND there is still
missing work, the batcher auto-resumes. This survives uvicorn hot reloads
(any backend .py edit) and Kubernetes pod restarts.

**Migration-aware missing query** (fixes iteration_23 HIGH money-burn):
The `image_service` layer lazily migrates `image_url` blobs into a
separate `image_blobs` collection referenced by `image_id`, then $unsets
the parent's `image_url`. The batcher's "missing" query MUST also treat
a doc with `image_id` as "has image," or every viewed city gets
regenerated at $0.04/image and the backlog never converges.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional

from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
from pymongo.errors import PyMongoError

from image_service import ImageService

logger = logging.getLogger(__name__)


async def _retry_db(coro_factory: Callable[[], Awaitable], *, attempts: int = 3,
                    base_delay: float = 0.5, what: str = "db op"):
    """Run a Mongo op with retries on transient PyMongo errors (network / read
    timeouts, auto-reconnect). Prevents a single blip from crashing an entire
    auto-continue batch run. `coro_factory` MUST return a fresh coroutine each
    call — a coroutine/cursor cannot be awaited twice."""
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except PyMongoError as e:
            last_exc = e
            logger.warning(f"{what} failed (attempt {i + 1}/{attempts}): {e}")
            if i < attempts - 1:
                await asyncio.sleep(base_delay * (2 ** i))
    raise last_exc

# Safety cap for run-until-done mode. 60 iterations × 25 batch = 1500 max
# items per kick-off.
MAX_ITERATIONS = 60

# Gentle throttle between individual image generations. Keeps a manual batch run
# from pinning the event loop / hammering Atlas + the LLM (which previously
# starved login requests). Configurable via env; default 0.75s.
IMAGE_BATCH_THROTTLE_SECONDS = float(os.environ.get("IMAGE_BATCH_THROTTLE_SECONDS", "0.75"))

# Mongo collection + doc id for persisting the batch state.
STATE_COLL = "image_batch_state"
STATE_DOC_ID = "singleton"

# A doc with `image_id` set is considered "has image" — the blob has been
# migrated to image_blobs. Excluding these from the missing query prevents
# regeneration of already-generated art.
MISSING_QUERY = {
    "$and": [
        {"$or": [{"image_url": None}, {"image_url": ""}, {"image_url": {"$exists": False}}]},
        {"$or": [{"image_id": None}, {"image_id": ""}, {"image_id": {"$exists": False}}]},
    ],
}


class _BatchJobState:
    def __init__(self):
        self.is_running: bool = False
        self.auto_continue: bool = False
        self.should_stop: bool = False
        self.started_at: Optional[str] = None
        self.target_count: int = 0
        self.generated: int = 0
        self.failed: int = 0
        self.iterations_run: int = 0
        self.last_error: Optional[str] = None
        self.last_completed_at: Optional[str] = None
        self.last_results: List[Dict] = []
        self.stopped_reason: Optional[str] = None
        # Heartbeat — bumped after every image. Used by resume_if_needed
        # to detect "orphaned" state (a run that was killed mid-flight).
        self.heartbeat_at: Optional[str] = None

    def snapshot(self) -> Dict:
        return {
            "is_running": self.is_running,
            "auto_continue": self.auto_continue,
            "should_stop": self.should_stop,
            "started_at": self.started_at,
            "target_count": self.target_count,
            "generated": self.generated,
            "failed": self.failed,
            "iterations_run": self.iterations_run,
            "last_error": self.last_error,
            "last_completed_at": self.last_completed_at,
            "stopped_reason": self.stopped_reason,
            "heartbeat_at": self.heartbeat_at,
            "last_results": list(self.last_results[-100:]),
        }

    def _mongo_payload(self) -> Dict:
        """Snapshot minus the noisy last_results list, for persistence."""
        s = self.snapshot()
        s.pop("last_results", None)
        return s

    def restore_from(self, doc: Dict) -> None:
        """Rehydrate transient state from a persisted Mongo doc (best-effort)."""
        for field in ("auto_continue", "should_stop", "started_at",
                      "target_count", "generated", "failed", "iterations_run",
                      "last_error", "last_completed_at", "stopped_reason",
                      "heartbeat_at"):
            if field in doc:
                setattr(self, field, doc[field])
        # is_running is deliberately re-computed by the caller — a fresh
        # process must never inherit is_running=True from a dead run.
        self.is_running = False


_JOB_STATE = _BatchJobState()


NATION_AESTHETIC = {
    "ammeonon":      "human kingdom, gothic-classical architecture, pearl-and-amber palette, coastal trade-port culture, airship moorings against cliff faces",
    "aigraels":      "war-torn human empire, dark stone walls, scarred banners of three rival factions, perpetual siege-time atmosphere",
    "dhor-kuldor":   "dwarven realm, carved-mountain halls, runic engravings, torchlit hewn-stone passages, gold and iron everywhere",
    "selindori":     "ancient elven kingdom, crystal spires, gardens woven into architecture, golden-and-emerald palette, time-slowed light",
    "veiled-realms": "mysterious external elven kingdoms — moonlit terraces, shadow-bound obsidian halls, or singing memory-crystals depending on the kingdom",
}

LOCATION_TYPE_AESTHETIC = {
    "tavern":      "cozy interior, hearth fire, wooden beams or stone arches, lit lanterns, atmosphere of welcome",
    "market":      "bustling stalls, hung wares, colorful awnings, merchants and shoppers, daylight or torchlight",
    "temple":      "high vaulted sanctuary, altar at the focal point, votive candles, ambient sacred light",
    "shop":        "specialty workshop, tools and finished wares displayed, craftsman's quarters in back",
    "courthouse":  "imposing chamber of justice, magistrate's bench raised, columns and inscribed law-stones",
    "prison":      "stone cell block, barred doors, dim guttering torches, austere stonework",
    "sacred-site": "numinous location of power, ancient relic at center, otherworldly lighting, sense of held breath",
    "noble-house": "ornate mansion exterior or grand entry hall, family heraldry, manicured grounds",
    "library":     "rows of shelving, codices and scrolls, reading desks with lamps, hush of study",
    "academy":     "classroom or training hall, learning paraphernalia, students at work",
    "forge":       "blazing forge fires, anvils, hammers, hanging weapons-in-progress, sparks",
    "guild":       "guildhall meeting room, banners, polished long table, professional tools displayed",
    "park":        "civic garden, fountains, paths, statuary, public gathering space",
    "harbor":      "stone quays, ships at berth, cargo cranes, sea-wind atmosphere",
    "landmark":    "iconic civic monument or geographic feature, dramatic vantage, the city visible behind",
}


def _build_city_prompt(c: Dict) -> str:
    nation_style = NATION_AESTHETIC.get(c.get("nation"), "epic fantasy realm")
    parts: List[str] = [
        f"Fantasy city/town establishing shot: {c.get('name')}, in {c.get('nation','an unknown realm')}.",
        f"Setting: {nation_style}.",
    ]
    if c.get("description"):
        parts.append(f"Brief: {c['description']}")
    if c.get("lore"):
        parts.append(f"Lore hooks: {c['lore'][:300]}")
    if c.get("is_capital"):
        parts.append("This is the realm's capital — grander scale, throne quarter visible.")
    if c.get("is_ruined"):
        parts.append("RUINED city — crumbling walls, abandoned, shadowed and overgrown.")
    if c.get("is_contested"):
        parts.append("Contested city — barricades, scorch-marks, multiple faction banners.")
    if c.get("hold"):
        parts.append(f"Part of the {c['hold']} Hold (Dhor-Kuldor).")
    parts.append("Style: epic fantasy illustration, cinematic wide establishing shot, atmospheric lighting, detailed architecture, high quality digital art, NO TEXT in image.")
    return "\n".join(parts)


def _build_location_prompt(loc: Dict) -> str:
    nation_style = NATION_AESTHETIC.get(loc.get("nation"), "epic fantasy realm")
    type_style = LOCATION_TYPE_AESTHETIC.get(loc.get("location_type") or "", "fantasy interior or exterior scene")
    parts: List[str] = [
        f"Fantasy {loc.get('location_type','location')} scene: {loc.get('name','unnamed location')}, in {loc.get('city','an unknown city')}, {loc.get('nation','unknown realm')}.",
        f"Realm setting: {nation_style}.",
        f"Type aesthetic: {type_style}.",
    ]
    if loc.get("description"):
        parts.append(f"Description: {loc['description'][:280]}")
    if loc.get("lore"):
        parts.append(f"Lore: {loc['lore'][:280]}")
    if loc.get("is_sacred") or loc.get("tongue_of_yros"):
        parts.append("This is a SACRED SITE of immense significance — otherworldly atmosphere, numinous lighting.")
    parts.append("Style: epic fantasy illustration, atmospheric, detailed, high quality digital art, NO TEXT in image.")
    return "\n".join(parts)


class CityLocationImageBatcher:
    """Generates images for cities + locations missing them, batch by batch."""

    def __init__(self, db, batch_size: int = 25):
        self.db = db
        self.batch_size = max(1, min(batch_size, 50))
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise RuntimeError("EMERGENT_LLM_KEY missing from environment.")
        self.image_gen = OpenAIImageGeneration(api_key=api_key)
        self.img_service = ImageService(db)

    async def _generate_image_id(self, prompt: str) -> Optional[str]:
        """Generate one image and persist it to the `image_blobs` collection.
        Returns the new `image_id` (a short UUID) or None on failure.

        IMPORTANT: the image is stored in image_blobs and referenced by
        image_id — we do NOT embed the base64 blob in the parent
        city/location document. Embedding bloated every doc to megabytes,
        which made the "missing images" survey COLLSCAN slow enough to hit
        MongoDB's socket read timeout and crash the whole run after only a
        handful of images.
        """
        try:
            # `generate_images` is awaitable but its underlying HTTP client blocks
            # the event loop for the full ~10-15s of a generation. On the single
            # worker that froze concurrent requests (a login spiked to ~14s during
            # a batch). Run it in a worker thread (own event loop) so the main loop
            # stays responsive while the image is generated.
            def _run_generation():
                return asyncio.run(self.image_gen.generate_images(
                    prompt=prompt,
                    model="gpt-image-1",
                    number_of_images=1,
                ))
            images = await asyncio.to_thread(_run_generation)
        except Exception as e:
            logger.warning(f"Image gen failed: {e}")
            return None
        if not images:
            return None
        try:
            return await self.img_service.store_bytes(images[0], mime_type="image/png")
        except PyMongoError as e:
            logger.warning(f"Image blob store failed: {e}")
            return None

    async def survey(self) -> Dict:
        cities_missing = await _retry_db(
            lambda: self.db.cities.count_documents(MISSING_QUERY),
            what="cities survey count",
        )
        locations_missing = await _retry_db(
            lambda: self.db.locations.count_documents(MISSING_QUERY),
            what="locations survey count",
        )
        return {
            "cities_missing": cities_missing,
            "locations_missing": locations_missing,
            "total_missing": cities_missing + locations_missing,
            "batch_size": self.batch_size,
        }

    async def generate_batch_sync(self) -> Dict:
        results: List[Dict] = []
        generated = 0
        failed = 0

        cities_to_do = await _retry_db(
            lambda: self.db.cities.find(
                MISSING_QUERY,
                {"_id": 0, "id": 1, "slug": 1, "name": 1, "nation": 1, "region": 1,
                 "description": 1, "lore": 1, "is_capital": 1, "is_ruined": 1,
                 "is_contested": 1, "hold": 1},
            ).limit(self.batch_size).to_list(length=self.batch_size),
            what="cities batch find",
        )

        remaining_slots = self.batch_size - len(cities_to_do)
        locations_to_do: List[Dict] = []
        if remaining_slots > 0:
            locations_to_do = await _retry_db(
                lambda: self.db.locations.find(
                    MISSING_QUERY,
                    {"_id": 0, "id": 1, "slug": 1, "name": 1, "nation": 1, "city": 1,
                     "location_type": 1, "description": 1, "lore": 1, "is_sacred": 1,
                     "tongue_of_yros": 1},
                ).limit(remaining_slots).to_list(length=remaining_slots),
                what="locations batch find",
            )

        for c in cities_to_do:
            if _JOB_STATE.should_stop:
                break
            prompt = _build_city_prompt(c)
            if IMAGE_BATCH_THROTTLE_SECONDS > 0:
                await asyncio.sleep(IMAGE_BATCH_THROTTLE_SECONDS)
            img_id = await self._generate_image_id(prompt)
            if img_id:
                await _retry_db(
                    lambda cid=c["id"], iid=img_id: self.db.cities.update_one(
                        {"id": cid},
                        {"$set": {"image_id": iid}, "$unset": {"image_url": ""}},
                    ),
                    what="city image write",
                )
                generated += 1
                _JOB_STATE.generated += 1
                results.append({"kind": "city", "slug": c.get("slug"), "name": c.get("name"), "ok": True})
                _JOB_STATE.last_results.append(results[-1])
            else:
                failed += 1
                _JOB_STATE.failed += 1
                results.append({"kind": "city", "slug": c.get("slug"), "name": c.get("name"), "ok": False})
                _JOB_STATE.last_results.append(results[-1])

        for loc in locations_to_do:
            if _JOB_STATE.should_stop:
                break
            prompt = _build_location_prompt(loc)
            if IMAGE_BATCH_THROTTLE_SECONDS > 0:
                await asyncio.sleep(IMAGE_BATCH_THROTTLE_SECONDS)
            img_id = await self._generate_image_id(prompt)
            if img_id:
                await _retry_db(
                    lambda lid=loc["id"], iid=img_id: self.db.locations.update_one(
                        {"id": lid},
                        {"$set": {"image_id": iid}, "$unset": {"image_url": ""}},
                    ),
                    what="location image write",
                )
                generated += 1
                _JOB_STATE.generated += 1
                results.append({"kind": "location", "slug": loc.get("slug"), "name": loc.get("name"), "ok": True})
                _JOB_STATE.last_results.append(results[-1])
            else:
                failed += 1
                _JOB_STATE.failed += 1
                results.append({"kind": "location", "slug": loc.get("slug"), "name": loc.get("name"), "ok": False})
                _JOB_STATE.last_results.append(results[-1])

        remaining = await self.survey()
        # Persist heartbeat + counters after each batch so a killed process
        # can rehydrate accurately on the next boot.
        _JOB_STATE.heartbeat_at = datetime.now(timezone.utc).isoformat()
        await self._persist_state()
        return {
            "generated": generated,
            "failed": failed,
            "batch_size": self.batch_size,
            "remaining": remaining,
            "results": results,
        }

    async def _persist_state(self) -> None:
        """Upsert the current job state to Mongo. Best-effort; a persist
        failure never aborts the batch itself."""
        try:
            await self.db[STATE_COLL].update_one(
                {"_id": STATE_DOC_ID},
                {"$set": _JOB_STATE._mongo_payload()},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"image_batch state persist failed: {e}")

    def kick_off_background_batch(self, auto_continue: bool = False) -> Dict:
        if _JOB_STATE.is_running:
            return {
                "started": False,
                "reason": "A batch is already in progress. Poll /admin/image-batch/status until it completes.",
                "state": _JOB_STATE.snapshot(),
            }
        _JOB_STATE.is_running = True
        _JOB_STATE.auto_continue = bool(auto_continue)
        _JOB_STATE.should_stop = False
        _JOB_STATE.started_at = datetime.now(timezone.utc).isoformat()
        _JOB_STATE.target_count = self.batch_size
        _JOB_STATE.generated = 0
        _JOB_STATE.failed = 0
        _JOB_STATE.iterations_run = 0
        _JOB_STATE.last_error = None
        _JOB_STATE.stopped_reason = None
        _JOB_STATE.last_results = []
        _JOB_STATE.heartbeat_at = _JOB_STATE.started_at

        async def _runner():
            try:
                # Persist initial "running" state so a crash/reload can be
                # detected and auto-resumed.
                await self._persist_state()
                if auto_continue:
                    last_total_missing: Optional[int] = None
                    for iteration in range(MAX_ITERATIONS):
                        if _JOB_STATE.should_stop:
                            _JOB_STATE.stopped_reason = "Stopped by admin request."
                            break
                        survey_before = await self.survey()
                        if survey_before["total_missing"] == 0:
                            _JOB_STATE.stopped_reason = "All images generated."
                            break
                        if last_total_missing is not None and last_total_missing == survey_before["total_missing"]:
                            _JOB_STATE.stopped_reason = (
                                f"No progress in iteration {iteration} — halting to avoid runaway failures. "
                                f"Inspect last_error / failed count and resume manually."
                            )
                            break
                        last_total_missing = survey_before["total_missing"]
                        await self.generate_batch_sync()
                        _JOB_STATE.iterations_run = iteration + 1
                        await asyncio.sleep(1.0)
                    else:
                        _JOB_STATE.stopped_reason = f"Hit MAX_ITERATIONS ({MAX_ITERATIONS}). Re-kick to continue."
                else:
                    await self.generate_batch_sync()
                    _JOB_STATE.iterations_run = 1
                    # If the admin hit /stop during the batch, honour that
                    # over the generic "batch complete" reason — otherwise
                    # they can't tell a truncated run from a completed one.
                    if _JOB_STATE.should_stop:
                        _JOB_STATE.stopped_reason = "Stopped by admin request."
                    else:
                        _JOB_STATE.stopped_reason = "Single-batch run complete."
            except Exception as e:
                logger.exception(f"Image batch failed: {e}")
                _JOB_STATE.last_error = str(e)[:400]
                _JOB_STATE.stopped_reason = "Crashed — see last_error."
            finally:
                _JOB_STATE.is_running = False
                _JOB_STATE.last_completed_at = datetime.now(timezone.utc).isoformat()
                # Final persist so status endpoints reflect the completed run
                # and any next server boot can decide whether to resume.
                await self._persist_state()

        asyncio.create_task(_runner())
        return {
            "started": True,
            "auto_continue": bool(auto_continue),
            "state": _JOB_STATE.snapshot(),
        }

    @staticmethod
    def get_status() -> Dict:
        return _JOB_STATE.snapshot()

    @staticmethod
    def request_stop() -> Dict:
        if not _JOB_STATE.is_running:
            return {"stopped": False, "reason": "No batch is currently running.", "state": _JOB_STATE.snapshot()}
        _JOB_STATE.should_stop = True
        return {"stopped": True, "state": _JOB_STATE.snapshot()}

    @staticmethod
    async def resume_if_needed(db) -> Dict:
        """Called once at server startup (from server.py). If the last
        persisted job state was `is_running=True` AND `auto_continue=True`
        AND there is still missing work, the batch was killed mid-run —
        auto-resume it. Returns a small dict describing what happened.

        This is the CRITICAL fix for the "batch never finishes across
        sessions" bug: uvicorn --reload and Kubernetes pod restarts both
        kill the in-memory asyncio task without any warning. Without this,
        the batcher only makes forward progress while the admin actively
        polls status.
        """
        try:
            doc = await db[STATE_COLL].find_one({"_id": STATE_DOC_ID})
        except Exception as e:
            logger.warning(f"resume_if_needed: state lookup failed: {e}")
            return {"resumed": False, "reason": f"state lookup failed: {e}"}
        if not doc:
            return {"resumed": False, "reason": "no prior state"}

        # Rehydrate transient state (counters, timestamps) from disk.
        _JOB_STATE.restore_from(doc)

        # Only auto-resume if:
        #   1. The previous run was on auto_continue (otherwise the admin
        #      explicitly chose single-batch; don't second-guess).
        #   2. The previous run was mid-flight when the process died.
        #   3. There's still missing work.
        was_orphaned = bool(doc.get("is_running") and doc.get("auto_continue"))
        if not was_orphaned:
            return {"resumed": False, "reason": "prior run completed cleanly"}

        batcher = CityLocationImageBatcher(db, batch_size=25)
        survey = await batcher.survey()
        if survey["total_missing"] <= 0:
            return {"resumed": False, "reason": "nothing to do"}

        result = batcher.kick_off_background_batch(auto_continue=True)
        logger.info(f"image_batch auto-resumed on startup: {survey['total_missing']} missing")
        return {
            "resumed": True,
            "missing_before_resume": survey["total_missing"],
            "kickoff": result,
        }
