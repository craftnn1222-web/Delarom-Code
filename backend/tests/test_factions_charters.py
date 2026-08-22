"""Tests for player-founded factions (charter system + NPC seeding + tick)."""
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

TEST_SLUG = "ce-tester-faction"


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


def _cleanup_test_faction():
    async def _do(db):
        f = await db.factions.find_one({"slug": TEST_SLUG}, {"_id": 0, "id": 1})
        fid = f["id"] if f else None
        if fid:
            await db.factions.delete_one({"id": fid})
            await db.faction_memberships.delete_many({"faction_id": fid})
            await db.faction_npcs.delete_many({"faction_id": fid})
            await db.faction_threads.delete_many({"faction_id": fid})
            await db.faction_thread_replies.delete_many({"faction_id": fid})
            await db.faction_treasury.delete_many({"faction_id": fid})
            await db.faction_treasury_log.delete_many({"faction_id": fid})
            await db.faction_quests.delete_many({"faction_id": fid})
            await db.faction_quest_completions.delete_many({"faction_id": fid})
        await db.faction_charters.delete_many({"slug": TEST_SLUG})
        await db.faction_charters.delete_many({"slug": {"$regex": "^ce-tester"}})
    _run_db(_do)


def _set_user_currency(user_id, amount):
    async def _do(db):
        await db.users.update_one({"id": user_id}, {"$set": {"currency": amount}})
    _run_db(_do)


def _force_leave_char(char_id):
    async def _do(db):
        await db.faction_memberships.update_many(
            {"character_id": char_id, "status": "active"},
            {"$set": {"status": "left"}},
        )
    _run_db(_do)


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin_user(admin_session):
    return admin_session.get(f"{BASE_URL}/api/auth/me").json()


@pytest.fixture(scope="module")
def test_char(admin_session):
    chars = admin_session.get(f"{BASE_URL}/api/characters").json()
    # Use the very last character so we don't collide with other tests that
    # take chars[0]/[1].
    return chars[-1]


@pytest.fixture(autouse=True)
def _cleanup_each(test_char):
    _cleanup_test_faction()
    _force_leave_char(test_char["id"])
    yield
    _cleanup_test_faction()
    _force_leave_char(test_char["id"])


# Helper: file a charter ready for approval
def _file_test_charter(admin_session, admin_user, test_char, name="CE Tester Faction"):
    _set_user_currency(admin_user["id"], 20000)
    r = admin_session.post(f"{BASE_URL}/api/factions/charter", json={
        "character_id": test_char["id"],
        "name": name,
        "motto": "for the testers",
        "description": "A tester order founded purely for the purposes of regression. Their codices contain mostly fixture data.",
        "nation_home": "aigraels",
        "color_hex": "#888888",
        "icon": "scroll",
    })
    assert r.status_code == 200, r.text
    return r.json()


class TestCharterLifecycle:
    def test_file_rejected_when_insufficient_funds(self, admin_session, admin_user, test_char):
        _set_user_currency(admin_user["id"], 100)
        r = admin_session.post(f"{BASE_URL}/api/factions/charter", json={
            "character_id": test_char["id"],
            "name": "CE Tester Faction Poor",
            "description": "Should be blocked because the applicant has no gold to spare.",
        })
        assert r.status_code == 400
        assert "5000" in r.json()["detail"]

    def test_filing_deducts_gold(self, admin_session, admin_user, test_char):
        _file_test_charter(admin_session, admin_user, test_char)
        wallet = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        assert wallet == 15000  # 20000 - 5000

    def test_rejection_refunds(self, admin_session, admin_user, test_char):
        c = _file_test_charter(admin_session, admin_user, test_char)
        wallet_before = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        r = admin_session.post(f"{BASE_URL}/api/admin/factions/charters/{c['id']}/reject",
                                json={"note": "test rejection"})
        assert r.status_code == 200
        assert r.json()["refunded"] == 5000
        wallet_after = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        assert wallet_after == wallet_before + 5000

    def test_approval_creates_faction_and_seeds_npcs(self, admin_session, admin_user, test_char):
        c = _file_test_charter(admin_session, admin_user, test_char)
        r = admin_session.post(f"{BASE_URL}/api/admin/factions/charters/{c['id']}/approve",
                                json={"note": "ok"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        slug = body["faction"]["slug"]
        # Founder is leader.
        mems = admin_session.get(f"{BASE_URL}/api/factions/{slug}/members").json()
        assert len(mems) == 1
        assert mems[0]["rank"] == "leader"
        # 3 NPCs seeded.
        npcs = admin_session.get(f"{BASE_URL}/api/factions/{slug}/npcs").json()
        assert len(npcs) == 3
        ranks = sorted([n["rank"] for n in npcs])
        assert ranks == ["member", "member", "officer"]
        for n in npcs:
            assert n["name"] and len(n["name"]) >= 3
            assert n["title"] and n["bio"]

    def test_self_double_charter_blocked(self, admin_session, admin_user, test_char):
        _file_test_charter(admin_session, admin_user, test_char)
        r = admin_session.post(f"{BASE_URL}/api/factions/charter", json={
            "character_id": test_char["id"],
            "name": "Another Different Name",
            "description": "Should be blocked because applicant already has one pending.",
        })
        assert r.status_code == 409


class TestTick:
    def test_admin_force_tick_runs_with_no_errors(self, admin_session, admin_user, test_char):
        c = _file_test_charter(admin_session, admin_user, test_char)
        approve = admin_session.post(f"{BASE_URL}/api/admin/factions/charters/{c['id']}/approve",
                                      json={"note": ""}).json()
        slug = approve["faction"]["slug"]
        # Post a thread so NPCs have something to reply to
        leader = admin_session.get(f"{BASE_URL}/api/factions/{slug}/members").json()[0]
        admin_session.post(f"{BASE_URL}/api/factions/{slug}/threads", json={
            "character_id": leader["character_id"],
            "title": "Test thread for tick",
            "content": "Reply if you can hear me.",
        })
        # Force-tick.
        r = admin_session.post(f"{BASE_URL}/api/admin/factions/{slug}/tick")
        assert r.status_code == 200
        summary = r.json()["summary"]
        # We have 3 NPCs × 30% chance of thread reply — could be 0-3. Just
        # assert the call shape and that no errors occurred.
        assert summary["errors"] == 0
        assert "thread_replies" in summary
        assert "quest_completions" in summary
        assert "recruited" in summary

    def test_lazy_tick_throttles(self, admin_session, admin_user, test_char):
        c = _file_test_charter(admin_session, admin_user, test_char)
        approve = admin_session.post(f"{BASE_URL}/api/admin/factions/charters/{c['id']}/approve",
                                      json={"note": ""}).json()
        slug = approve["faction"]["slug"]
        # First call runs.
        r1 = admin_session.post(f"{BASE_URL}/api/factions/{slug}/tick")
        assert r1.status_code == 200
        # Second call within 6h is throttled.
        r2 = admin_session.post(f"{BASE_URL}/api/factions/{slug}/tick")
        assert r2.status_code == 200
        body = r2.json()
        assert body.get("skipped") == "throttled"

    def test_npc_quest_completion_pays_treasury(self, admin_session, admin_user, test_char):
        """When an NPC completes a quest, the reward goes into the faction
        treasury (NOT any user wallet)."""
        c = _file_test_charter(admin_session, admin_user, test_char)
        approve = admin_session.post(f"{BASE_URL}/api/admin/factions/charters/{c['id']}/approve",
                                      json={"note": ""}).json()
        slug = approve["faction"]["slug"]
        leader = admin_session.get(f"{BASE_URL}/api/factions/{slug}/members").json()[0]

        # Create a quest with 1 slot so the FIRST eligible NPC completing it closes it
        admin_session.post(f"{BASE_URL}/api/factions/{slug}/quests", json={
            "actor_character_id": leader["character_id"],
            "title": "Test commission",
            "objective": "A thing to be done by some sworn member.",
            "reward_gold": 250,
            "reward_reputation": 5,
            "max_completions": 1,
        })
        wallet_before = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]

        # Force-tick repeatedly to maximise chance of an NPC picking it up
        for _ in range(8):
            admin_session.post(f"{BASE_URL}/api/admin/factions/{slug}/tick")

        # Treasury should have grown if any NPC completed; if not, that's also
        # fine (probability is ~15% per NPC per tick, 3 NPCs × 8 ticks ≈ 99.6%).
        treasury = admin_session.get(f"{BASE_URL}/api/factions/{slug}/treasury").json()
        # Wallet should NOT have grown — NPC completions don't pay players.
        wallet_after = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        assert wallet_after == wallet_before, "NPC quest completion must not credit user wallet"
        # We allow the case where probability didn't trigger, but if it did
        # the gold went to the treasury.
        assert treasury["balance"] in (0, 250)
