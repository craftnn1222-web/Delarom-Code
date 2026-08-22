"""Tests for the starter-factions seeder — verifies the endpoint also seeds
the 6-NPC roster and the 1,000,000 gold treasury, and that those side
effects are idempotent on repeated calls."""
import asyncio
import os
import sys
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

STARTER_SLUGS = [
    "ardent-legion", "forsaken-court", "elderborn-alliance",
    "forgemasters-guild", "high-kings-court", "loremasters-guild",
]
STARTER_GOLD = 1_000_000


def _run_db(factory):
    async def _wrap():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            return await factory(c[DB_NAME])
        finally:
            c.close()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_wrap())
    finally:
        loop.close()


def _reset_starter_side_effects():
    """Wipe starter NPCs + treasury so the seeder has work to do."""
    async def _do(db):
        rows = await db.factions.find(
            {"slug": {"$in": STARTER_SLUGS}}, {"_id": 0, "id": 1},
        ).to_list(length=None)
        fids = [r["id"] for r in rows]
        await db.faction_npcs.delete_many({"faction_id": {"$in": fids}})
        await db.faction_treasury.delete_many({"faction_id": {"$in": fids}})
        await db.faction_treasury_log.delete_many({
            "faction_id": {"$in": fids},
            "kind": {"$in": ["starter_endowment", "starter_topup"]},
        })
    _run_db(_do)


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


class TestStarterSeed:
    def test_seed_creates_npcs_and_treasury(self, admin_session):
        _reset_starter_side_effects()
        r = admin_session.post(f"{BASE_URL}/api/factions/admin/seed-starter")
        assert r.status_code == 200, r.text
        body = r.json()
        # All 6 should receive both NPCs and treasury this round.
        for slug in STARTER_SLUGS:
            assert body["npcs_seeded"].get(slug) == 6, body["npcs_seeded"]
            assert slug in body["treasuries_initialised"]
        # Verify each one ended up with 6 NPCs and 1,000,000 gold.
        for slug in STARTER_SLUGS:
            npcs = admin_session.get(f"{BASE_URL}/api/factions/{slug}/npcs").json()
            assert len(npcs) == 6, f"{slug} should have 6 NPCs, got {len(npcs)}"
            officers = [n for n in npcs if n["rank"] == "officer"]
            members = [n for n in npcs if n["rank"] == "member"]
            assert len(officers) == 2, f"{slug} expected 2 officers, got {len(officers)}"
            assert len(members) == 4, f"{slug} expected 4 members, got {len(members)}"
            for n in npcs:
                assert n["source"] == "starter"
                assert n["name"] and len(n["name"]) >= 3
                assert n["title"]
            t = admin_session.get(f"{BASE_URL}/api/factions/{slug}/treasury").json()
            assert t["balance"] == STARTER_GOLD, f"{slug}: balance {t['balance']}"

    def test_seed_is_idempotent(self, admin_session):
        # Don't reset — run AGAIN on top of the previous test's result.
        r = admin_session.post(f"{BASE_URL}/api/factions/admin/seed-starter")
        assert r.status_code == 200
        body = r.json()
        assert body["npcs_seeded"] == {}, "no new NPCs should be seeded on repeat"
        assert body["treasuries_initialised"] == [], "no treasuries should be touched"
        # NPC count unchanged.
        for slug in STARTER_SLUGS:
            npcs = admin_session.get(f"{BASE_URL}/api/factions/{slug}/npcs").json()
            assert len(npcs) == 6

    def test_seed_topup_partial_treasury(self, admin_session):
        """If a starter faction's treasury was drained below the endowment
        (e.g., a leader donated coin out via some future feature), the
        next seed call tops it back up to STARTER_GOLD — without resetting
        treasuries that are already full or over-funded."""
        # Drain forgemasters to 100k.
        async def _drain(db):
            f = await db.factions.find_one({"slug": "forgemasters-guild"}, {"_id": 0, "id": 1})
            await db.faction_treasury.update_one(
                {"faction_id": f["id"]}, {"$set": {"balance": 100_000}},
            )
        _run_db(_drain)
        r = admin_session.post(f"{BASE_URL}/api/factions/admin/seed-starter")
        body = r.json()
        assert "forgemasters-guild" in body["treasuries_initialised"]
        t = admin_session.get(f"{BASE_URL}/api/factions/forgemasters-guild/treasury").json()
        assert t["balance"] == STARTER_GOLD
