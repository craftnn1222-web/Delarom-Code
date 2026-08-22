"""Tier 1 (FULL) — Realms canon seed tests.

Unit tests against the seed_all_realms_canon module using a lightweight
in-memory Mongo shim. Verifies:
  - Every realm has at least one canonical city
  - Idempotency: two consecutive seed runs move rows from inserted → updated
  - Canonical slugs required by seed_titan_sacred_sites are present
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_all_realms_canon import (  # noqa: E402
    ALL_REALMS,
    seed_all_realms_canon,
)
from seed_titan_sacred_sites import TITAN_SITES  # noqa: E402


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeCollection:
    def __init__(self):
        self._docs: list = []

    async def find_one(self, query):
        for d in self._docs:
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None

    async def insert_one(self, doc):
        self._docs.append(dict(doc))
        return type("Res", (), {"inserted_id": "fake"})()

    async def update_one(self, query, update):
        for d in self._docs:
            if all(d.get(k) == v for k, v in query.items()):
                d.update(update.get("$set", {}))
                return


class _FakeDb:
    def __init__(self):
        self.cities = _FakeCollection()


def test_all_five_realms_present():
    assert set(ALL_REALMS) == {"ammeonon", "selindori", "dhor-kuldor", "aigraels", "veiled-realms"}


def test_every_realm_has_at_least_one_capital():
    for nation, cities in ALL_REALMS.items():
        # Each realm should have at least one canonical city defined.
        assert len(cities) >= 1, f"{nation} has no canonical cities"


def test_ammeonon_capital_is_wymroost():
    ammeonon = ALL_REALMS["ammeonon"]
    capitals = [c for c in ammeonon if c.get("is_capital")]
    assert len(capitals) == 1
    assert capitals[0]["slug"] == "wymroost"


def test_selindori_capital_is_aurelion_spires():
    selindori = ALL_REALMS["selindori"]
    capitals = [c for c in selindori if c.get("is_capital")]
    assert len(capitals) == 1
    assert capitals[0]["slug"] == "aurelion-spires"


def test_dhor_kuldor_capital_is_ancestor_hall():
    kuldor = ALL_REALMS["dhor-kuldor"]
    capitals = [c for c in kuldor if c.get("is_capital")]
    assert len(capitals) == 1
    assert capitals[0]["slug"] == "ancestor-hall"


def test_aigraels_has_three_triumvirate_faction_cities():
    aigraels = ALL_REALMS["aigraels"]
    triumvirate_cities = [c for c in aigraels if c.get("triumvirate")]
    factions = {c["triumvirate"] for c in triumvirate_cities}
    assert factions == {"ardent-legion", "forsaken-court", "elderborn-alliance"}


def test_veiled_realms_has_three_sub_race_capitals():
    veiled = ALL_REALMS["veiled-realms"]
    races = {c.get("elf_race") for c in veiled if c.get("is_capital")}
    assert "moon elf" in races
    # Shadow Elf and Crystal Elf are realm-capitals of their sub-realms even
    # without the is_capital flag; verify their slugs are present.
    all_slugs = {c["slug"] for c in veiled}
    assert {"rakesh", "yaksha-shi", "serant-kresh"} <= all_slugs


def test_seed_is_idempotent():
    """Two consecutive seed runs should move all rows from inserted → updated."""
    db = _FakeDb()
    first = _run(seed_all_realms_canon(db))
    second = _run(seed_all_realms_canon(db))
    assert first["total_inserted"] > 0
    assert first["total_updated"] == 0
    assert second["total_inserted"] == 0
    assert second["total_updated"] == first["total_inserted"]


def test_every_titan_site_target_is_in_the_canon_seed():
    """Every (nation, slug) referenced by TITAN_SITES must exist in the
    canon seed OR the earlier Dhor-Kuldor min-viable seed."""
    from seed_dhor_kuldor_canon import CANONICAL_CITIES as KULDOR_MIN
    kuldor_slugs = {c["slug"] for c in KULDOR_MIN}

    seed_index: dict = {}
    for nation, cities in ALL_REALMS.items():
        seed_index[nation] = {c["slug"] for c in cities}
    seed_index["dhor-kuldor"] = seed_index.get("dhor-kuldor", set()) | kuldor_slugs

    missing: list = []
    for site in TITAN_SITES:
        available = seed_index.get(site["nation"], set())
        if site["slug"] not in available:
            missing.append((site["nation"], site["slug"]))
    assert not missing, f"Titan sites without a canonical city: {missing}"


def test_canon_covers_all_elven_school_home_realms():
    """quest_master_ai.py's ELVEN_SCHOOLS map needs matching realm-cities in
    the canon so the race-specific school block can fire."""
    # This is a soft check — the block matches by sub-race token inside the
    # (nation, city) pair, so we just verify the key elven realm-cities exist.
    selindori_slugs = {c["slug"] for c in ALL_REALMS["selindori"]}
    veiled_slugs = {c["slug"] for c in ALL_REALMS["veiled-realms"]}
    required_selindori = {"aurelion-spires", "thalenroot", "nal-theris", "isenfell", "aer-cyr"}
    required_veiled = {"rakesh", "yaksha-shi", "serant-kresh"}
    assert required_selindori <= selindori_slugs
    assert required_veiled <= veiled_slugs
