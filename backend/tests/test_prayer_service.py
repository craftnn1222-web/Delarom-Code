"""Tier 2a — Prayer System tests (uses _run() pattern; no pytest-asyncio)."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prayer_service import GODS, PrayerService, _race_match, list_gods  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeCollection:
    def __init__(self):
        self._docs: list = []

    def _matches(self, doc, query):
        for key, val in query.items():
            if isinstance(val, dict):
                actual = doc.get(key)
                for op, op_val in val.items():
                    if op == "$gt":
                        if actual is None or not (actual > op_val):
                            return False
                    elif op == "$gte":
                        if actual is None or not (actual >= op_val):
                            return False
                    elif op == "$in":
                        if actual not in op_val:
                            return False
                    elif op == "$exists":
                        present = (key in doc) and doc[key] is not None
                        if present != op_val:
                            return False
                    else:
                        return False
            else:
                if doc.get(key) != val:
                    return False
        return True

    async def find_one(self, query=None, projection=None, sort=None):
        query = query or {}
        results = [d for d in self._docs if self._matches(d, query)]
        if sort:
            for field, direction in reversed(sort):
                results.sort(key=lambda d: d.get(field) or "", reverse=(direction == -1))
        return results[0] if results else None

    async def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("Res", (), {"inserted_id": "fake"})()

    def find(self, query=None, projection=None):
        query = query or {}
        rows = [d for d in self._docs if self._matches(d, query)]
        return _FakeCursor(rows)


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, field, direction=1):
        self._rows.sort(key=lambda d: d.get(field) or "", reverse=(direction == -1))
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    async def to_list(self, length=None):
        return list(self._rows[:length] if length else self._rows)


class _FakeDb:
    def __init__(self):
        self.prayers = _FakeCollection()


def test_list_gods_returns_four_canonical_gods():
    keys = {g["key"] for g in list_gods()}
    assert keys == {"seren", "yros", "uesis", "ehena"}


def test_race_match_seren_loves_elves():
    assert _race_match("seren", "Sun Elf") is True
    assert _race_match("seren", "Half-Elf") is True
    assert _race_match("seren", "Human") is False


def test_race_match_yros_loves_dwarves():
    assert _race_match("yros", "Mountain Dwarf") is True
    assert _race_match("yros", "Elf") is False


def test_race_match_ehena_is_universal_no_race_bias():
    assert _race_match("ehena", "Human") is False
    assert _race_match("ehena", "Elf") is False


def test_canonical_god_palette_contains_voice_keys():
    for _key, god in GODS.items():
        assert god["name"] and god["title"] and god["domain"] and god["voice"]
        assert isinstance(god["race_affinity"], list)
        assert god["blessing_palette"] and god["silence_palette"]


def test_submit_prayer_persists_and_returns_record():
    db = _FakeDb()
    svc = PrayerService(db)
    character = {"id": "char-1", "user_id": "u-1", "name": "Aelyn", "race": "Sun Elf"}

    async def fake_judge(self, **_kw):
        return {"verdict": "blessing", "narration": "Warmth.", "boon_text": "Light.",
                "judgement_reason": "ok", "affinity_match": True}
    with patch.object(PrayerService, "_judge_prayer", fake_judge):
        rec = _run(svc.submit_prayer(
            character=character, god_key="seren",
            prayer_text="Mother Seren, bless my hands as I tend the wounded.",
        ))
    assert rec["verdict"] == "blessing"
    assert rec["god_name"] == "Seren"
    assert rec["expires_at"] is not None
    assert len(db.prayers._docs) == 1


def test_cooldown_enforces_24h_per_god():
    db = _FakeDb()
    svc = PrayerService(db)
    character = {"id": "char-1", "user_id": "u-1", "race": "Sun Elf"}

    async def fake_judge(self, **_kw):
        return {"verdict": "silence", "narration": "Hush.", "boon_text": "",
                "judgement_reason": "ok", "affinity_match": True}
    with patch.object(PrayerService, "_judge_prayer", fake_judge):
        _run(svc.submit_prayer(character=character, god_key="seren",
                               prayer_text="I pray for guidance from Seren."))
        with pytest.raises(ValueError) as exc_info:
            _run(svc.submit_prayer(character=character, god_key="seren",
                                   prayer_text="Please answer me, Mother Seren."))
        assert "already prayed to Seren recently" in str(exc_info.value)


def test_cooldown_is_per_god_not_global():
    db = _FakeDb()
    svc = PrayerService(db)
    character = {"id": "char-1", "user_id": "u-1", "race": "Sun Elf"}

    async def fake_judge(self, **_kw):
        return {"verdict": "silence", "narration": "Hush.", "boon_text": "",
                "judgement_reason": "ok", "affinity_match": False}
    with patch.object(PrayerService, "_judge_prayer", fake_judge):
        _run(svc.submit_prayer(character=character, god_key="seren",
                               prayer_text="A prayer to Seren of life."))
        rec2 = _run(svc.submit_prayer(character=character, god_key="yros",
                                       prayer_text="Yros, lend me your steady hand."))
        assert rec2["god"] == "yros"


def test_existing_blessing_flag_passed_for_downgrade():
    db = _FakeDb()
    _run(db.prayers.insert_one({
        "id": "p-old", "character_id": "char-1", "god": "seren",
        "god_name": "Seren", "verdict": "blessing", "boon_text": "Old.",
        "prayed_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
        "narration": "...", "judgement_reason": "", "affinity_match": True,
    }))
    captured: dict = {}

    async def fake_judge(self, *, god_key, character, prayer_text, existing_blessing_active):
        captured["flag"] = existing_blessing_active
        return {"verdict": "flicker", "narration": "A warmth.", "boon_text": "flicker",
                "judgement_reason": "downgrade", "affinity_match": True}

    svc = PrayerService(db)
    character = {"id": "char-1", "user_id": "u-1", "race": "Sun Elf"}
    with patch.object(PrayerService, "_judge_prayer", fake_judge):
        rec = _run(svc.submit_prayer(character=character, god_key="seren",
                                      prayer_text="Mother Seren, hear me again."))
    assert captured["flag"] is True
    assert rec["verdict"] == "flicker"


def test_get_active_blessings_excludes_expired():
    db = _FakeDb()
    _run(db.prayers.insert_one({
        "id": "p-active", "character_id": "char-1", "god": "seren",
        "god_name": "Seren", "verdict": "blessing", "boon_text": "Active.",
        "prayed_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "narration": "...", "judgement_reason": "", "affinity_match": True,
    }))
    _run(db.prayers.insert_one({
        "id": "p-expired", "character_id": "char-1", "god": "yros",
        "god_name": "Yros", "verdict": "blessing", "boon_text": "Old.",
        "prayed_at": (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat(),
        "expires_at": (datetime.now(timezone.utc) - timedelta(hours=14)).isoformat(),
        "narration": "...", "judgement_reason": "", "affinity_match": False,
    }))
    svc = PrayerService(db)
    active = _run(svc.get_active_blessings("char-1"))
    keys = {b["god"] for b in active}
    assert "seren" in keys
    assert "yros" not in keys


def test_validation_rejects_short_prayer():
    svc = PrayerService(_FakeDb())
    character = {"id": "char-1", "user_id": "u-1", "race": "Sun Elf"}
    with pytest.raises(ValueError):
        _run(svc.submit_prayer(character=character, god_key="seren", prayer_text="hi"))


def test_validation_rejects_unknown_god():
    svc = PrayerService(_FakeDb())
    character = {"id": "char-1", "user_id": "u-1", "race": "Sun Elf"}
    with pytest.raises(ValueError):
        _run(svc.submit_prayer(character=character, god_key="loki",
                                prayer_text="A prayer to a god who does not walk Delarom."))
