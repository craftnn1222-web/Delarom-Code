"""Image batch — durability + migration-awareness tests (iteration_23 fixes).

Covers the two follow-on bugs the testing agent surfaced:
  1. Auto-resume on startup: after a persisted state with is_running=True +
     auto_continue=True + missing work, resume_if_needed re-kicks the batch.
  2. Migration-aware missing query: a doc with image_id but no image_url is
     NOT counted as missing (avoiding regeneration of already-generated art).
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from city_location_image_batcher import (  # noqa: E402
    MISSING_QUERY,
    STATE_COLL,
    STATE_DOC_ID,
    CityLocationImageBatcher,
    _JOB_STATE,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeCollection:
    """Tiny Mongo-shaped shim — only the ops the batcher uses."""

    def __init__(self):
        self._docs: list = []

    def _matches(self, doc, query):
        # Only the exact operators the batcher uses are supported here.
        def _match_leaf(actual, cond):
            if isinstance(cond, dict):
                for op, op_val in cond.items():
                    if op == "$exists":
                        present = actual is not None
                        if present != op_val:
                            return False
                    elif op == "$in":
                        if actual not in op_val:
                            return False
                    elif op == "$or":  # nested — shouldn't happen here
                        return False
                    else:
                        return False
                return True
            return actual == cond

        for key, val in query.items():
            if key == "$and":
                if not all(self._matches(doc, sub) for sub in val):
                    return False
            elif key == "$or":
                if not any(self._matches(doc, sub) for sub in val):
                    return False
            else:
                if not _match_leaf(doc.get(key), val):
                    return False
        return True

    async def count_documents(self, query):
        return sum(1 for d in self._docs if self._matches(d, query))

    async def find_one(self, query, projection=None):
        for d in self._docs:
            if self._matches(d, query):
                return d
        return None

    async def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("Res", (), {"inserted_id": "fake"})()

    async def update_one(self, query, update, upsert=False):
        for d in self._docs:
            if self._matches(d, query):
                d.update(update.get("$set", {}))
                return
        if upsert:
            merged = dict(query)
            merged.update(update.get("$set", {}))
            self._docs.append(merged)

    def find(self, query=None, projection=None):
        rows = [d for d in self._docs if self._matches(d, query or {})]
        return _FakeCursor(rows)


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    async def to_list(self, length=None):
        return list(self._rows[:length] if length else self._rows)


class _FakeDb:
    def __init__(self):
        self.cities = _FakeCollection()
        self.locations = _FakeCollection()
        self.image_batch_state = _FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name.replace("-", "_"))


def _reset_state():
    _JOB_STATE.is_running = False
    _JOB_STATE.auto_continue = False
    _JOB_STATE.should_stop = False
    _JOB_STATE.generated = 0
    _JOB_STATE.failed = 0
    _JOB_STATE.iterations_run = 0
    _JOB_STATE.last_error = None
    _JOB_STATE.stopped_reason = None
    _JOB_STATE.last_results = []
    _JOB_STATE.heartbeat_at = None


# ─── Migration-aware missing query ───────────────────────────────────


def test_missing_query_treats_image_id_as_has_image():
    """A doc with image_id but no image_url MUST be counted as HAS image."""
    db = _FakeDb()

    async def _seed():
        # 1) has image_url — has image
        await db.cities.insert_one({"id": "c1", "slug": "a", "image_url": "data:image/png;base64,X"})
        # 2) has image_id but $unset image_url — still has image (migrated)
        await db.cities.insert_one({"id": "c2", "slug": "b", "image_id": "blob-1"})
        # 3) has neither — genuinely missing
        await db.cities.insert_one({"id": "c3", "slug": "c"})
        # 4) has both null (defensive)
        await db.cities.insert_one({"id": "c4", "slug": "d", "image_url": None, "image_id": None})
        return await db.cities.count_documents(MISSING_QUERY)

    missing = _run(_seed())
    assert missing == 2, f"only c3 and c4 should be missing (got {missing})"


# ─── Auto-resume on startup ─────────────────────────────────────────


def test_resume_if_needed_no_prior_state_returns_not_resumed():
    _reset_state()
    db = _FakeDb()
    out = _run(CityLocationImageBatcher.resume_if_needed(db))
    assert out["resumed"] is False
    assert "no prior state" in out["reason"]


def test_resume_if_needed_skips_when_prior_completed_cleanly():
    _reset_state()
    db = _FakeDb()

    async def _seed():
        await db.image_batch_state.insert_one({
            "_id": STATE_DOC_ID,
            "is_running": False,
            "auto_continue": True,
            "stopped_reason": "All images generated.",
        })
        await db.cities.insert_one({"id": "c1", "slug": "a"})  # would be missing
        return await CityLocationImageBatcher.resume_if_needed(db)

    out = _run(_seed())
    assert out["resumed"] is False
    assert "completed cleanly" in out["reason"]


def test_resume_if_needed_re_kicks_when_orphaned():
    """The core case: previous run was killed mid-batch with unfinished work.
    resume_if_needed must call kick_off_background_batch."""
    _reset_state()
    db = _FakeDb()

    async def _seed():
        await db.image_batch_state.insert_one({
            "_id": STATE_DOC_ID,
            "is_running": True,       # killed mid-flight
            "auto_continue": True,    # user wanted run-until-done
            "generated": 12,
            "failed": 0,
            "iterations_run": 0,
        })
        # Some work still to do so survey() > 0
        await db.cities.insert_one({"id": "c1", "slug": "a"})

    _run(_seed())

    kicked = {}

    def _fake_kick(self, auto_continue=False):
        kicked["auto_continue"] = auto_continue
        kicked["called"] = True
        return {"started": True, "state": {}}

    with patch.dict(os.environ, {"EMERGENT_LLM_KEY": "test-key"}, clear=False), \
         patch.object(CityLocationImageBatcher, "kick_off_background_batch", _fake_kick):
        out = _run(CityLocationImageBatcher.resume_if_needed(db))

    assert out["resumed"] is True
    assert kicked.get("called") is True
    assert kicked.get("auto_continue") is True
    assert out["missing_before_resume"] == 1


def test_resume_if_needed_skips_when_nothing_left_to_do():
    """Orphaned run but survey shows 0 missing → don't re-kick."""
    _reset_state()
    db = _FakeDb()

    async def _seed():
        await db.image_batch_state.insert_one({
            "_id": STATE_DOC_ID,
            "is_running": True,
            "auto_continue": True,
        })
        # No missing docs — survey() returns 0
        await db.cities.insert_one({"id": "c1", "slug": "a", "image_url": "data:image/png;base64,X"})

    _run(_seed())

    with patch.dict(os.environ, {"EMERGENT_LLM_KEY": "test-key"}, clear=False):
        out = _run(CityLocationImageBatcher.resume_if_needed(db))

    assert out["resumed"] is False
    assert "nothing to do" in out["reason"]


# ─── State persistence writes to Mongo ──────────────────────────────


def test_persist_state_upserts_singleton():
    _reset_state()
    db = _FakeDb()

    with patch.dict(os.environ, {"EMERGENT_LLM_KEY": "test-key"}, clear=False):
        batcher = CityLocationImageBatcher(db, batch_size=25)

    _JOB_STATE.generated = 42
    _JOB_STATE.auto_continue = True
    _run(batcher._persist_state())
    doc = _run(db.image_batch_state.find_one({"_id": STATE_DOC_ID}))
    assert doc is not None
    assert doc["generated"] == 42
    assert doc["auto_continue"] is True


def test_restore_from_never_inherits_is_running():
    """Fresh process must never inherit is_running=True from an orphan."""
    _reset_state()
    _JOB_STATE.restore_from({"is_running": True, "generated": 7, "auto_continue": True})
    assert _JOB_STATE.is_running is False
    assert _JOB_STATE.generated == 7
    assert _JOB_STATE.auto_continue is True


# suppress the unused import in some environments
_ = AsyncMock
