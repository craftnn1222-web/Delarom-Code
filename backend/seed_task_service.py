"""
Seed Task Service — background-task runner with status polling.

Wraps the existing `run_full_seed()` from seed_database.py with an in-memory
progress tracker so the admin UI can poll a single endpoint and show live
status without blocking the request thread.
"""
from typing import Dict, Optional
from datetime import datetime, timezone
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SeedTaskManager:
    """Single-task manager — only one seed runs at a time."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._state: Dict = {
            "task_id": None,
            "status": "idle",  # idle | running | completed | failed
            "phase": None,
            "started_at": None,
            "finished_at": None,
            "progress": 0,  # 0-100 coarse estimate
            "message": "",
            "results": None,
            "error": None,
        }

    def status(self) -> Dict:
        return dict(self._state)

    def is_running(self) -> bool:
        return self._state["status"] == "running"

    def _update(self, **kwargs):
        self._state.update(kwargs)

    async def start(self, db, with_images: bool = True) -> Dict:
        if self.is_running():
            return self.status()

        task_id = str(uuid.uuid4())
        self._state = {
            "task_id": task_id,
            "status": "running",
            "phase": "starting",
            "started_at": _now_iso(),
            "finished_at": None,
            "progress": 0,
            "message": "Initialising seeding…",
            "results": None,
            "error": None,
        }

        # Fire-and-forget background task
        self._task = asyncio.create_task(self._run(db, with_images))
        return self.status()

    async def _run(self, db, with_images: bool):
        try:
            from seed_database import (
                set_database, init_image_generator,
                seed_nations, seed_cities, seed_locations,
            )

            set_database(db)
            results = {"nations": 0, "cities": 0, "locations": 0,
                       "nation_images": 0, "city_images": 0, "location_images": 0,
                       "errors": []}

            if with_images:
                self._update(phase="image_generator", message="Initialising image generator…", progress=5)
                if not init_image_generator():
                    results["errors"].append("Image generator not available — continuing without images")
                    with_images = False

            # Phase 1 — Nations
            self._update(phase="nations", message="Seeding nations…", progress=10)
            try:
                nation_result = await seed_nations(with_images=with_images)
                results["nations"] = nation_result["created"]
                results["nation_images"] = nation_result["images"]
            except Exception as e:
                results["errors"].append(f"Nations: {e}")
                logger.error(f"Seed nations failed: {e}")

            # Phase 2 — Cities
            self._update(phase="cities", message="Seeding cities (this may take a few minutes if generating images)…", progress=35)
            try:
                city_result = await seed_cities(with_images=with_images)
                results["cities"] = city_result["created"]
                results["city_images"] = city_result["images"]
            except Exception as e:
                results["errors"].append(f"Cities: {e}")
                logger.error(f"Seed cities failed: {e}")

            # Phase 3 — Locations
            self._update(phase="locations", message="Seeding locations…", progress=70)
            try:
                location_result = await seed_locations(with_images=with_images)
                results["locations"] = location_result["created"]
                results["location_images"] = location_result["images"]
            except Exception as e:
                results["errors"].append(f"Locations: {e}")
                logger.error(f"Seed locations failed: {e}")

            self._update(
                phase="done",
                status="completed",
                progress=100,
                finished_at=_now_iso(),
                message=(
                    f"Seeded {results['nations']} nations, {results['cities']} cities, "
                    f"{results['locations']} locations."
                ),
                results=results,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Seed task crashed")
            self._update(
                status="failed",
                finished_at=_now_iso(),
                error=str(e),
                message=f"Seeding failed: {e}",
            )


# Module-level singleton
seed_task_manager = SeedTaskManager()
