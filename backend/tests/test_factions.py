"""
P2 Faction Membership — Round 1 backend tests.

Covers:
  - Public reads (list / detail / members / ranks)
  - Join + duplicate-faction 409 + member_count refresh
  - Leave + idempotent 404 + leader cannot-leave 409
  - Promote / Demote chain + authorization edges
  - Expel only by leader
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

SLUG_A = "ardent-legion"
SLUG_B = "forsaken-court"
SLUG_C = "elderborn-alliance"


# ---------------------- fixtures ----------------------


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_chars(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/characters")
    assert r.status_code == 200, r.text
    chars = r.json()
    assert isinstance(chars, list) and len(chars) >= 3, f"Admin needs >=3 characters (got {len(chars)})"
    return chars


def _safe_leave(session, slug, char_id):
    """Best-effort leave to clean state. Ignores 404 / 409."""
    try:
        session.post(f"{BASE_URL}/api/factions/{slug}/leave", json={"character_id": char_id})
    except Exception:
        pass


def _run_db(coro_factory):
    """Run a fresh motor client inside its own event loop to avoid cross-loop futures."""
    async def _wrap():
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        client = AsyncIOMotorClient(mongo_url)
        try:
            return await coro_factory(client[db_name])
        finally:
            client.close()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_wrap())
    finally:
        loop.close()


# ---------------------- Public reads ----------------------


class TestFactionPublicReads:
    def test_list_factions(self):
        r = requests.get(f"{BASE_URL}/api/factions")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 6, f"Expected 6 seeded factions, got {len(data)}"
        slugs = {f["slug"] for f in data}
        for needed in ["ardent-legion", "forsaken-court", "elderborn-alliance", "forgemasters-guild", "high-kings-court", "loremasters-guild"]:
            assert needed in slugs, f"Missing seeded faction {needed}"
        # Spot-check field shape on Ardent Legion
        al = next(f for f in data if f["slug"] == "ardent-legion")
        for key in ("id", "name", "motto", "description", "color_hex", "icon", "member_count", "is_active"):
            assert key in al, f"Missing field {key} on faction doc"

    def test_get_faction_detail(self):
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_A}")
        assert r.status_code == 200
        f = r.json()
        assert f["slug"] == SLUG_A
        assert f["name"] == "The Ardent Legion"
        assert "Through Fire" in f["motto"]

    def test_get_faction_404(self):
        r = requests.get(f"{BASE_URL}/api/factions/this-faction-does-not-exist")
        assert r.status_code == 404

    def test_list_members(self):
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_A}/members")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ranks_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/factions/ranks")
        assert r.status_code == 200
        body = r.json()
        assert body["ranks"] == ["initiate", "member", "officer", "leader"]
        assert body["labels"]["leader"] == "Leader"


# ---------------------- Auth-gated reads ----------------------


class TestMyMembership:
    def test_my_membership_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/factions/my/membership")
        # 401 (no cookie) or 403 depending on auth dep
        assert r.status_code in (401, 403)

    def test_my_membership_authed_returns_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/factions/my/membership")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------------- Join / Leave ----------------------


class TestJoinLeaveFlow:
    def test_join_requires_auth(self, admin_chars):
        r = requests.post(
            f"{BASE_URL}/api/factions/{SLUG_A}/join",
            json={"character_id": admin_chars[0]["id"], "pitch": "test"},
        )
        assert r.status_code in (401, 403)

    def test_join_then_leave_happy_path(self, admin_session, admin_chars):
        char = admin_chars[0]
        # Force-clean any prior active membership on this character via direct DB
        async def _force_clean(db):
            now = datetime.now(timezone.utc).isoformat()
            faction_ids = set()
            async for mem in db.faction_memberships.find(
                {"character_id": char["id"], "status": "active"}
            ):
                faction_ids.add(mem["faction_id"])
            await db.faction_memberships.update_many(
                {"character_id": char["id"], "status": "active"},
                {"$set": {"status": "left", "left_at": now}},
            )
            for fid in faction_ids:
                cnt = await db.faction_memberships.count_documents({"faction_id": fid, "status": "active"})
                await db.factions.update_one({"id": fid}, {"$set": {"member_count": cnt}})
        _run_db(_force_clean)

        # Join Ardent Legion
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_A}/join",
            json={"character_id": char["id"], "pitch": "TEST pledge"},
        )
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["rank"] == "initiate"
        assert m["rank_index"] == 0
        assert m["status"] == "active"
        assert m["faction_slug"] == SLUG_A
        assert m["character_id"] == char["id"]

        # Member list should include the character now
        members = admin_session.get(f"{BASE_URL}/api/factions/{SLUG_A}/members").json()
        ids = {x["character_id"] for x in members}
        assert char["id"] in ids

        # member_count must reflect at least 1
        det = admin_session.get(f"{BASE_URL}/api/factions/{SLUG_A}").json()
        assert det["member_count"] >= 1

        # Duplicate-faction guard: posting to a DIFFERENT slug must 409
        r2 = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_B}/join",
            json={"character_id": char["id"], "pitch": ""},
        )
        assert r2.status_code == 409
        assert "already belongs to a faction" in r2.json().get("detail", "").lower()

        # Leave returns ok + faction name
        r3 = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_A}/leave",
            json={"character_id": char["id"]},
        )
        assert r3.status_code == 200, r3.text
        body = r3.json()
        assert body["ok"] is True
        assert body["left"] == "The Ardent Legion"

        # Roster no longer contains the character
        members2 = admin_session.get(f"{BASE_URL}/api/factions/{SLUG_A}/members").json()
        ids2 = {x["character_id"] for x in members2}
        assert char["id"] not in ids2

        # Trying to leave again is 404
        r4 = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_A}/leave",
            json={"character_id": char["id"]},
        )
        assert r4.status_code == 404


# ---------------------- Rank changes ----------------------


class TestRankChanges:
    """We need TWO admin-owned characters in the SAME faction.
       Then we'll DB-promote one to officer / leader to test edges.
    """

    def test_promote_demote_chain_and_edges(self, admin_session, admin_chars):
        actor = admin_chars[1]
        target = admin_chars[2]
        slug = SLUG_C  # use a non-noisy faction

        # Clean — leave any active membership these characters might be in
        async def _force_clean(db):
            now = datetime.now(timezone.utc).isoformat()
            faction_ids = set()
            async for mem in db.faction_memberships.find(
                {"character_id": {"$in": [actor["id"], target["id"]]}, "status": "active"}
            ):
                faction_ids.add(mem["faction_id"])
            await db.faction_memberships.update_many(
                {"character_id": {"$in": [actor["id"], target["id"]]}, "status": "active"},
                {"$set": {"status": "left", "left_at": now}},
            )
            for fid in faction_ids:
                cnt = await db.faction_memberships.count_documents({"faction_id": fid, "status": "active"})
                await db.factions.update_one({"id": fid}, {"$set": {"member_count": cnt}})
        _run_db(_force_clean)

        # Both join Elderborn
        for c in (actor, target):
            r = admin_session.post(
                f"{BASE_URL}/api/factions/{slug}/join",
                json={"character_id": c["id"], "pitch": "TEST"},
            )
            assert r.status_code == 200, r.text

        # Initiate cannot manage another initiate → 403 (authority check)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 403
        assert "authority" in r.json().get("detail", "").lower()

        # Bump actor to officer directly in Mongo (simulate prior promotion ladder)
        async def _set_officer(db):
            await db.faction_memberships.update_one(
                {"character_id": actor["id"], "status": "active"},
                {"$set": {"rank": "officer", "rank_index": 2}},
            )
        _run_db(_set_officer)

        # Officer can promote target initiate → member
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["rank"] == "member"

        # member → officer (officer promoting target to officer = equal rank, should 403 (can_manage requires actor > target))
        # First promote member → officer
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        # Now target is at rank 'member' (idx 1), actor is officer (idx 2) → can_manage True → promote to officer (idx 2)
        assert r.status_code == 200, r.text
        assert r.json()["rank"] == "officer"

        # Now both are officers; promoting an equal-rank target → 403
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 403, r.text

        # Demote target officer → member (actor still officer, equal rank → 403 by _can_manage)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/demote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 403

        # Bump actor to leader; now demote target officer→member→initiate
        async def _set_leader(db):
            await db.faction_memberships.update_one(
                {"character_id": actor["id"], "status": "active"},
                {"$set": {"rank": "leader", "rank_index": 3}},
            )
        _run_db(_set_leader)

        # Leader demotes officer → member
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/demote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 200
        assert r.json()["rank"] == "member"

        # member → initiate
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/demote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 200
        assert r.json()["rank"] == "initiate"

        # initiate → cannot be demoted further → 409
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/demote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 409
        assert "demoted further" in r.json().get("detail", "").lower()

        # Leader cannot leave → 409
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/leave",
            json={"character_id": actor["id"]},
        )
        assert r.status_code == 409
        assert "abandon" in r.json().get("detail", "").lower()

        # Promote target to officer, then officer (target idx 2) → leader requires leadership transfer → 409
        # First promote actor's manage-power is fine since leader manages all
        for _ in range(2):
            r = admin_session.post(
                f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
                json={"actor_character_id": actor["id"]},
            )
            assert r.status_code == 200
        # target now officer; further promote → 409 leadership-transfer
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/promote/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 409
        assert "leadership transfer" in r.json().get("detail", "").lower()

        # Expel: only leader may expel. Actor is leader → expel target succeeds
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/expel/{target['id']}",
            json={"actor_character_id": actor["id"]},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # Cleanup: reset memberships state
        async def _cleanup(db):
            await db.faction_memberships.update_many(
                {"character_id": {"$in": [actor["id"], target["id"]]}, "status": "active"},
                {"$set": {"status": "left", "left_at": datetime.now(timezone.utc).isoformat()}},
            )
            f = await db.factions.find_one({"slug": slug})
            if f:
                cnt = await db.faction_memberships.count_documents({"faction_id": f["id"], "status": "active"})
                await db.factions.update_one({"id": f["id"]}, {"$set": {"member_count": cnt}})
        _run_db(_cleanup)
