"""P2 Faction Membership — Round 2 backend tests.

Covers:
  - Reputation init (5 rows, score=0 per nation, NATIONS order)
  - Admin grant + clamps at REPUTATION_MAX/MIN
  - Admin-only grant (403 for non-admin)
  - Reputation history rows
  - Law hook: character crime cascades to faction reputation
    (moderate=-15, major=-50, history reason text)
  - NPC crimes do NOT cascade
  - Faction-only threads access control (public list strips content, full thread
    requires membership or admin)
  - Thread + reply require membership
  - replies_count auto-increments
  - Admin seed-leaders sets rank=leader + leader_character_id
"""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

# Allow direct import of LawService for the cascade test
sys.path.insert(0, "/app/backend")
from law_service import LawService  # noqa: E402

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com"
).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

NATIONS = ["ammeonon", "selindori", "dhor-kuldor", "aigraels", "veiled-realms"]

SLUG_FORGE = "forgemasters-guild"   # clean rep test
SLUG_LORE = "loremasters-guild"     # law-hook test
SLUG_ARDENT = "ardent-legion"       # threads/seed-leaders test


# ---------------------- helpers ----------------------


def _run_db(coro_factory):
    async def _wrap():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            return await coro_factory(client[DB_NAME])
        finally:
            client.close()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_wrap())
    finally:
        loop.close()


def _reset_reputation(slug):
    async def _do(db):
        f = await db.factions.find_one({"slug": slug}, {"_id": 0, "id": 1})
        if not f:
            return
        await db.faction_reputation.delete_many({"faction_id": f["id"]})
        await db.faction_reputation_history.delete_many({"faction_id": f["id"]})
    _run_db(_do)


def _force_leave(char_ids):
    async def _do(db):
        now = datetime.now(timezone.utc).isoformat()
        ids = list(set(char_ids))
        async for mem in db.faction_memberships.find({"character_id": {"$in": ids}, "status": "active"}):
            fid = mem["faction_id"]
            await db.faction_memberships.update_one({"id": mem["id"]}, {"$set": {"status": "left", "left_at": now}})
            cnt = await db.faction_memberships.count_documents({"faction_id": fid, "status": "active"})
            await db.factions.update_one({"id": fid}, {"$set": {"member_count": cnt}})
    _run_db(_do)


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
    assert r.status_code == 200
    chars = r.json()
    assert len(chars) >= 3
    return chars


@pytest.fixture(scope="module")
def nonadmin_session():
    """Pre-seeded approved non-admin user (rep_tester_round2)."""
    s = requests.Session()
    email = "rep_tester_round2@delarom.com"
    password = "Testpass123!"
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        pytest.skip(f"non-admin login failed: {r.status_code} {r.text}")
    return s


# ---------------------- Reputation init / grant / clamps ----------------------


class TestReputation:
    def test_reputation_initial_state_five_rows(self):
        _reset_reputation(SLUG_FORGE)
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 5
        # Order matches NATIONS constant
        assert [row["nation"] for row in data] == NATIONS
        for row in data:
            assert row["score"] == 0

    def test_admin_grant_and_history(self, admin_session):
        _reset_reputation(SLUG_FORGE)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation/grant",
            json={"nation": "dhor-kuldor", "delta": 300, "reason": "TEST grant"},
        )
        assert r.status_code == 200, r.text
        row = r.json()
        assert row["nation"] == "dhor-kuldor"
        assert row["score"] == 300

        # Verify GET shows it; other 4 still 0
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation").json()
        by_n = {r_["nation"]: r_["score"] for r_ in rows}
        assert by_n["dhor-kuldor"] == 300
        for n in NATIONS:
            if n != "dhor-kuldor":
                assert by_n[n] == 0

        # History
        hist = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation/history").json()
        assert len(hist) >= 1
        first = next(h for h in hist if h["nation"] == "dhor-kuldor")
        assert first["delta"] == 300
        assert "TEST grant" in first["reason"]

    def test_reputation_clamps_positive_and_negative(self, admin_session):
        _reset_reputation(SLUG_FORGE)
        # Push positive: 500, 500, 500 → clamp at 1000
        for _ in range(3):
            r = admin_session.post(
                f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation/grant",
                json={"nation": "ammeonon", "delta": 500, "reason": "TEST clamp"},
            )
            assert r.status_code == 200
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation").json()
        amm = next(r_ for r_ in rows if r_["nation"] == "ammeonon")
        assert amm["score"] == 1000, f"expected clamp at +1000, got {amm['score']}"

        # Negative side on a different nation
        for _ in range(3):
            r = admin_session.post(
                f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation/grant",
                json={"nation": "selindori", "delta": -500, "reason": "TEST neg-clamp"},
            )
            assert r.status_code == 200
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation").json()
        sel = next(r_ for r_ in rows if r_["nation"] == "selindori")
        assert sel["score"] == -1000, f"expected clamp at -1000, got {sel['score']}"

    def test_grant_requires_admin(self, nonadmin_session):
        r = nonadmin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation/grant",
            json={"nation": "aigraels", "delta": 50, "reason": "should be blocked"},
        )
        assert r.status_code == 403, r.text


# ---------------------- LAW HOOK ----------------------


class TestLawCrimeHook:
    def test_character_crime_cascades_moderate_then_major(self, admin_session, admin_chars):
        """Use LawService directly (no admin record-crime HTTP endpoint exists).

        NOTE: law_service.SEVERITY_TIERS = {petty, minor, major, capital, regicide}
        BUT  factions.REPUTATION_CRIME_DELTA keys = {minor, moderate, major, grievous, regicide}.
        'moderate' is NOT a valid law severity — record_crime normalizes it to 'minor' (-5)
        BEFORE the hook is invoked. The PRD asks for moderate=-15 which the current
        wiring cannot deliver. We assert PRD expectation; if it fails, that's the bug.
        """
        char = admin_chars[0]
        _force_leave([char["id"]])
        _reset_reputation(SLUG_LORE)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_LORE}/join",
            json={"character_id": char["id"], "pitch": "TEST hook"},
        )
        assert r.status_code == 200, r.text

        async def _do_moderate(db):
            law = LawService(db)
            return await law.record_crime(
                character_id=char["id"],
                character_name=char["name"],
                user_id="test-user",
                nation="aigraels",
                location="Test Plaza",
                crime_type="theft",
                severity="moderate",
                description="TEST moderate crime hook",
            )
        crime1 = _run_db(_do_moderate)
        assert crime1["perpetrator_type"] == "character"

        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation").json()
        aig = next(r_ for r_ in rows if r_["nation"] == "aigraels")
        # PRD expects -15; current code returns -5 due to severity vocab mismatch
        assert aig["score"] == -15, (
            f"PRD expects moderate→-15 BUT got {aig['score']}. "
            f"Root cause: law_service.SEVERITY_TIERS lacks 'moderate'; severity is "
            f"normalized to 'minor' BEFORE apply_crime_to_faction runs."
        )

        # Major in same nation
        async def _do_major(db):
            law = LawService(db)
            return await law.record_crime(
                character_id=char["id"],
                character_name=char["name"],
                user_id="test-user",
                nation="aigraels",
                location="Test Plaza",
                crime_type="arson",
                severity="major",
                description="TEST major crime hook",
            )
        _run_db(_do_major)

        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation").json()
        aig = next(r_ for r_ in rows if r_["nation"] == "aigraels")
        assert aig["score"] == -65, f"expected -65 (-15 + -50), got {aig['score']}"

        hist = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation/history").json()
        aig_hist = [h for h in hist if h["nation"] == "aigraels"]
        assert len(aig_hist) >= 2
        reasons = " | ".join(h["reason"].lower() for h in aig_hist)
        assert "moderate crime" in reasons
        assert "major crime" in reasons
        assert char["name"].lower() in reasons

        _force_leave([char["id"]])

    def test_character_major_crime_cascades_correctly(self, admin_session, admin_chars):
        """Sanity-check version using a severity that exists in BOTH vocabularies.
        Confirms the hook itself is wired correctly when severity vocab matches.
        """
        char = admin_chars[0]
        _force_leave([char["id"]])
        _reset_reputation(SLUG_LORE)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_LORE}/join",
            json={"character_id": char["id"], "pitch": "TEST hook major-only"},
        )
        assert r.status_code == 200, r.text

        async def _do_major(db):
            law = LawService(db)
            return await law.record_crime(
                character_id=char["id"],
                character_name=char["name"],
                user_id="test-user",
                nation="aigraels",
                location="Test Plaza",
                crime_type="arson",
                severity="major",
                description="TEST major-only hook",
            )
        _run_db(_do_major)
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation").json()
        aig = next(r_ for r_ in rows if r_["nation"] == "aigraels")
        assert aig["score"] == -50

        # History reason contains 'major crime' + char name
        hist = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation/history").json()
        match = [h for h in hist if h["nation"] == "aigraels" and "major crime" in h["reason"].lower()]
        assert match, f"no major-crime history row found: {hist}"
        assert char["name"].lower() in match[0]["reason"].lower()

        _force_leave([char["id"]])

    def test_npc_crime_does_not_cascade(self):
        _reset_reputation(SLUG_LORE)

        # Snapshot rep
        before = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation").json()
        before_scores = {r["nation"]: r["score"] for r in before}

        async def _do_npc(db):
            law = LawService(db)
            return await law.record_crime(
                nation="aigraels",
                location="Test Alley",
                crime_type="murder",
                severity="major",
                description="TEST npc cascade should be a no-op",
                perpetrator_type="npc",
                perpetrator_id=f"npc-{uuid.uuid4()}",
                perpetrator_name="Test NPC",
            )
        _run_db(_do_npc)

        after = requests.get(f"{BASE_URL}/api/factions/{SLUG_LORE}/reputation").json()
        after_scores = {r["nation"]: r["score"] for r in after}
        assert before_scores == after_scores, f"NPC crime should not change rep. before={before_scores} after={after_scores}"


# ---------------------- Faction-only threads ----------------------


class TestFactionThreads:
    def test_threads_list_is_public_and_strips_content(self, admin_session, admin_chars):
        """Create a thread (as a member) then verify public list has no content field."""
        char = admin_chars[0]
        _force_leave([char["id"]])
        # Join Ardent
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_ARDENT}/join",
            json={"character_id": char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200

        # Create thread
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads",
            json={"character_id": char["id"], "title": "TEST thread title", "content": "TEST secret body"},
        )
        assert r.status_code == 200, r.text
        thread = r.json()
        tid = thread["id"]
        assert thread["replies_count"] == 0

        # Public list — no auth needed; content must be stripped
        r2 = requests.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads")
        assert r2.status_code == 200
        lst = r2.json()
        match = next((t for t in lst if t["id"] == tid), None)
        assert match is not None
        assert "content" not in match, f"Public peek should strip content, got keys={list(match.keys())}"

        # Save for downstream tests
        TestFactionThreads.thread_id = tid
        TestFactionThreads.test_char_id = char["id"]

    def test_get_full_thread_requires_auth(self):
        tid = getattr(TestFactionThreads, "thread_id", None)
        assert tid, "Run test_threads_list_is_public_and_strips_content first"
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}")
        assert r.status_code in (401, 403)

    def test_nonmember_user_is_forbidden(self, nonadmin_session):
        tid = getattr(TestFactionThreads, "thread_id", None)
        assert tid
        r = nonadmin_session.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}")
        assert r.status_code == 403, r.text
        assert "members only" in r.json().get("detail", "").lower()

    def test_member_can_read_full_thread_with_replies(self, admin_session):
        tid = getattr(TestFactionThreads, "thread_id", None)
        assert tid
        r = admin_session.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "thread" in body and "replies" in body
        assert body["thread"]["content"] == "TEST secret body"

    def test_thread_create_requires_membership(self, admin_session, admin_chars):
        # Pick a different char NOT in Ardent
        other = admin_chars[1]
        _force_leave([other["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads",
            json={"character_id": other["id"], "title": "TEST title", "content": "yy"},
        )
        assert r.status_code == 403, r.text

    def test_reply_requires_membership_and_increments_count(self, admin_session, admin_chars):
        tid = getattr(TestFactionThreads, "thread_id", None)
        char_id = getattr(TestFactionThreads, "test_char_id", None)
        assert tid and char_id

        # Non-member char attempt
        other = admin_chars[1]
        _force_leave([other["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}/replies",
            json={"character_id": other["id"], "content": "should fail"},
        )
        assert r.status_code == 403

        # Member reply succeeds
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}/replies",
            json={"character_id": char_id, "content": "TEST reply body"},
        )
        assert r.status_code == 200, r.text

        # replies_count incremented in list
        lst = requests.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads").json()
        match = next(t for t in lst if t["id"] == tid)
        assert match["replies_count"] >= 1

    def test_admin_override_can_view_thread_without_membership(self, admin_session, admin_chars):
        """After leaving, admin user should still see the thread (admin override)."""
        tid = getattr(TestFactionThreads, "thread_id", None)
        char_id = getattr(TestFactionThreads, "test_char_id", None)
        assert tid and char_id
        # Make admin a non-member by leaving with the only member char
        _force_leave([char_id])
        # Now admin owns no member in Ardent — but is admin role.
        r = admin_session.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/threads/{tid}")
        assert r.status_code == 200, f"admin override should work: {r.status_code} {r.text}"


# ---------------------- Admin seed-leaders ----------------------


class TestSeedLeaders:
    def test_seed_leaders_assigns_rank_and_leader_id(self, admin_session, admin_chars):
        char = admin_chars[2]
        slug = SLUG_FORGE  # use a less-noisy faction
        _force_leave([char["id"]])
        # Clear any existing leader on this faction in mongo (for idempotence)
        async def _clear_leader(db):
            await db.factions.update_one({"slug": slug}, {"$set": {"leader_character_id": None}})
            # Demote any existing leaders so this faction has none
            await db.faction_memberships.update_many(
                {"faction_slug": slug, "status": "active", "rank": "leader"},
                {"$set": {"rank": "officer", "rank_index": 2}},
            )
        _run_db(_clear_leader)

        # Join as member
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{slug}/join",
            json={"character_id": char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200, r.text

        # Seed-leaders
        r = admin_session.post(
            f"{BASE_URL}/api/factions/admin/seed-leaders",
            json={"assignments": {slug: char["id"]}},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body[slug]["ok"] is True
        assert body[slug]["leader"] == char["name"]

        # Members list shows rank=leader
        members = requests.get(f"{BASE_URL}/api/factions/{slug}/members").json()
        me = next(m for m in members if m["character_id"] == char["id"])
        assert me["rank"] == "leader"

        # Faction doc has leader_character_id set
        det = requests.get(f"{BASE_URL}/api/factions/{slug}").json()
        assert det["leader_character_id"] == char["id"]

        # Cleanup: demote leader so they can leave; then force-leave
        async def _cleanup(db):
            await db.faction_memberships.update_many(
                {"character_id": char["id"], "status": "active"},
                {"$set": {"rank": "officer", "rank_index": 2}},
            )
            await db.factions.update_one({"slug": slug}, {"$set": {"leader_character_id": None}})
        _run_db(_cleanup)
        _force_leave([char["id"]])
