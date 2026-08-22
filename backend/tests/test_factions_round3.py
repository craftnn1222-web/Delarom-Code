"""P2 Faction Membership — Round 3 backend tests.

Covers:
  - Treasury: init, donate (moves gold from user → coffer + log),
    rejects non-member, rejects insufficient funds.
  - Quests: officer/leader can create manual, AI-generate (falls back to
    template when LLM unavailable), members can complete once (rep + gold + treasury hooks
    fire), max_completions auto-closes, officer can manually close.
    Non-member cannot complete; double-complete is 409.
  - Rivalries: leader declares (intensity 25, status='declared'),
    duplicate declare is 409, escalate bumps + status changes, sue-for-peace
    zeros it, auto-escalation hook fires when a member commits a crime in
    rival's home nation.
"""
import os
import sys
import asyncio
import uuid
import pytest
import requests
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
from law_service import LawService  # noqa: E402

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com"
).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

# Two factions with home nations: Forgemasters (dhor-kuldor) vs Ardent Legion (aigraels).
SLUG_FORGE = "forgemasters-guild"
SLUG_ARDENT = "ardent-legion"
SLUG_LORE = "loremasters-guild"


# ----------------------------- helpers -----------------------------


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


def _wipe_round3(slug):
    """Delete this faction's quests, treasury, and rivalries so tests start clean."""
    async def _do(db):
        f = await db.factions.find_one({"slug": slug}, {"_id": 0, "id": 1})
        if not f:
            return
        fid = f["id"]
        await db.faction_quests.delete_many({"faction_id": fid})
        await db.faction_quest_completions.delete_many({"faction_id": fid})
        await db.faction_treasury.delete_many({"faction_id": fid})
        await db.faction_treasury_log.delete_many({"faction_id": fid})
        await db.faction_rivalries.delete_many({"$or": [{"faction_a_id": fid}, {"faction_b_id": fid}]})
        await db.faction_reputation.delete_many({"faction_id": fid})
        await db.faction_reputation_history.delete_many({"faction_id": fid})
    _run_db(_do)


def _promote_to_leader(slug, character_id):
    async def _do(db):
        f = await db.factions.find_one({"slug": slug}, {"_id": 0, "id": 1})
        if not f:
            return
        await db.faction_memberships.update_many(
            {"faction_id": f["id"], "status": "active", "rank": "leader"},
            {"$set": {"rank": "officer", "rank_index": 2}},
        )
        await db.faction_memberships.update_one(
            {"character_id": character_id, "faction_id": f["id"], "status": "active"},
            {"$set": {"rank": "leader", "rank_index": 3}},
        )
        await db.factions.update_one({"id": f["id"]}, {"$set": {"leader_character_id": character_id}})
    _run_db(_do)


def _set_user_currency(user_id, amount):
    async def _do(db):
        await db.users.update_one({"id": user_id}, {"$set": {"currency": amount}})
    _run_db(_do)


# ----------------------------- fixtures -----------------------------


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_user(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def admin_chars(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/characters")
    assert r.status_code == 200
    chars = r.json()
    assert len(chars) >= 3
    return chars


# ----------------------------- Treasury -----------------------------


class TestTreasury:
    def test_treasury_initial_state(self):
        _wipe_round3(SLUG_FORGE)
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/treasury")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["balance"] == 0
        assert t["total_donated"] == 0

    def test_donate_requires_membership(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        char = admin_chars[0]
        _force_leave([char["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/treasury/donate",
            json={"character_id": char["id"], "amount": 10},
        )
        assert r.status_code == 403, r.text

    def test_donate_moves_gold_and_logs(self, admin_session, admin_chars, admin_user):
        _wipe_round3(SLUG_FORGE)
        char = admin_chars[0]
        _force_leave([char["id"]])
        _set_user_currency(admin_user["id"], 5000)

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": char["id"], "pitch": "TEST treasury"},
        )
        assert r.status_code == 200

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/treasury/donate",
            json={"character_id": char["id"], "amount": 120},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["treasury"]["balance"] == 120
        assert body["treasury"]["total_donated"] == 120

        # User's wallet was debited.
        r = admin_session.get(f"{BASE_URL}/api/wallet")
        assert r.status_code == 200
        assert r.json()["balance"] == 4880

        _force_leave([char["id"]])

    def test_donate_rejects_insufficient_funds(self, admin_session, admin_chars, admin_user):
        _wipe_round3(SLUG_FORGE)
        char = admin_chars[0]
        _force_leave([char["id"]])
        _set_user_currency(admin_user["id"], 50)
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/treasury/donate",
            json={"character_id": char["id"], "amount": 500},
        )
        assert r.status_code == 400, r.text
        assert "insufficient" in r.json().get("detail", "").lower()
        _force_leave([char["id"]])


# ----------------------------- Quests -----------------------------


class TestQuests:
    def test_create_requires_officer_plus(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        char = admin_chars[0]
        _force_leave([char["id"]])
        # Initiate may NOT create.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests",
            json={
                "actor_character_id": char["id"],
                "title": "should be blocked",
                "objective": "n/a",
            },
        )
        assert r.status_code == 403
        _force_leave([char["id"]])

    def test_full_quest_lifecycle(self, admin_session, admin_chars, admin_user):
        """Officer creates → member completes → rep + gold + treasury hooks fire.

        Uses TWO different characters so officer-create + member-complete don't conflict.
        """
        _wipe_round3(SLUG_FORGE)
        officer_char = admin_chars[0]
        member_char = admin_chars[1]
        _force_leave([officer_char["id"], member_char["id"]])
        _set_user_currency(admin_user["id"], 1000)

        # Officer joins + is promoted to leader.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": officer_char["id"], "pitch": "leader"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, officer_char["id"])

        # 2nd character joins.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": member_char["id"], "pitch": "member"},
        )
        assert r.status_code == 200

        # Leader issues quest with 1 slot.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests",
            json={
                "actor_character_id": officer_char["id"],
                "title": "Walk the wall at dawn",
                "objective": "Patrol the upper bastion until sunrise and report what you see.",
                "flavour": "Carry no banner.",
                "reward_gold": 200,
                "reward_reputation": 25,
                "max_completions": 1,
            },
        )
        assert r.status_code == 200, r.text
        quest = r.json()
        assert quest["source"] == "manual"
        assert quest["completion_count"] == 0
        qid = quest["id"]

        # Public list shows it.
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests")
        assert r.status_code == 200
        assert any(q["id"] == qid for q in r.json())

        # Member completes.
        wallet_before = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests/{qid}/complete",
            json={"character_id": member_char["id"], "proof": "Walked it. Saw lanterns."},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["quest_closed"] is True

        # Gold paid out.
        wallet_after = admin_session.get(f"{BASE_URL}/api/wallet").json()["balance"]
        assert wallet_after == wallet_before + 200, f"Expected +200 gold, got {wallet_after - wallet_before}"

        # Reputation in faction's home (dhor-kuldor) increased by 25.
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/reputation").json()
        dhor = next(r_ for r_ in rows if r_["nation"] == "dhor-kuldor")
        assert dhor["score"] == 25

        # Quest now is_active=false (1/1 done).
        r = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests", params={"include_closed": True})
        q = next(qq for qq in r.json() if qq["id"] == qid)
        assert q["is_active"] is False
        assert q["completion_count"] == 1

        # Double-completion blocked.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests/{qid}/complete",
            json={"character_id": member_char["id"]},
        )
        assert r.status_code in (404, 409)

        _force_leave([officer_char["id"], member_char["id"]])

    def test_nonmember_cannot_complete(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        leader_char = admin_chars[0]
        outsider = admin_chars[2]
        _force_leave([leader_char["id"], outsider["id"]])

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, leader_char["id"])

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests",
            json={
                "actor_character_id": leader_char["id"],
                "title": "Members only", "objective": "Members only objective.",
                "reward_gold": 10, "reward_reputation": 1,
                "max_completions": 5,
            },
        )
        qid = r.json()["id"]

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests/{qid}/complete",
            json={"character_id": outsider["id"]},
        )
        assert r.status_code == 403
        _force_leave([leader_char["id"], outsider["id"]])

    def test_ai_generate_returns_quest(self, admin_session, admin_chars):
        """AI generation MUST produce a usable quest even if the LLM is unreachable
        (faction_ai uses a hand-rolled fallback when EMERGENT_LLM_KEY is missing
        or budget-capped)."""
        _wipe_round3(SLUG_FORGE)
        leader_char = admin_chars[0]
        _force_leave([leader_char["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, leader_char["id"])

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests/ai-generate",
            json={"actor_character_id": leader_char["id"], "reward_gold": 75, "reward_reputation": 15, "max_completions": 5},
        )
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["source"] == "ai"
        assert q["title"] and q["objective"]
        assert q["reward_gold"] == 75
        assert q["is_active"] is True

        _force_leave([leader_char["id"]])

    def test_officer_close_quest(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        leader_char = admin_chars[0]
        _force_leave([leader_char["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, leader_char["id"])

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests",
            json={
                "actor_character_id": leader_char["id"],
                "title": "Will be closed", "objective": "Patrol the upper wall.",
                "reward_gold": 0, "reward_reputation": 0, "max_completions": 5,
            },
        )
        qid = r.json()["id"]

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests/{qid}/close",
            json={"actor_character_id": leader_char["id"]},
        )
        assert r.status_code == 200

        # No longer in active list.
        active = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/quests").json()
        assert all(q["id"] != qid for q in active)
        _force_leave([leader_char["id"]])


# ----------------------------- Rivalries -----------------------------


class TestRivalries:
    def test_declare_requires_leader(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        _wipe_round3(SLUG_ARDENT)
        char = admin_chars[0]
        _force_leave([char["id"]])
        # Initiate-only — should fail.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200

        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={
                "actor_character_id": char["id"],
                "target_slug": SLUG_ARDENT,
                "reason": "TEST should be blocked",
            },
        )
        assert r.status_code == 403, r.text
        _force_leave([char["id"]])

    def test_leader_declares_and_escalates(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        _wipe_round3(SLUG_ARDENT)
        leader_char = admin_chars[0]
        _force_leave([leader_char["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, leader_char["id"])

        # Declare.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={
                "actor_character_id": leader_char["id"],
                "target_slug": SLUG_ARDENT,
                "reason": "TEST declared by Forge",
            },
        )
        assert r.status_code == 200, r.text
        riv = r.json()
        rivalry_id = riv["id"]
        assert riv["intensity"] == 25
        assert riv["status"] == "declared"

        # Duplicate declare blocked.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={"actor_character_id": leader_char["id"], "target_slug": SLUG_ARDENT},
        )
        assert r.status_code == 409

        # Escalate +30 → 55, status 'escalated'.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/{rivalry_id}/escalate",
            json={"actor_character_id": leader_char["id"], "delta": 30, "reason": "TEST esc"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["intensity"] == 55
        assert body["status"] == "escalated"

        # Visible on rival faction's side too.
        rows = requests.get(f"{BASE_URL}/api/factions/{SLUG_ARDENT}/rivalries").json()
        match = next((r_ for r_ in rows if r_["id"] == rivalry_id), None)
        assert match is not None
        assert match["rival"]["slug"] == SLUG_FORGE

        # Sue for peace.
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/{rivalry_id}/sue-for-peace",
            json={"actor_character_id": leader_char["id"]},
        )
        assert r.status_code == 200
        assert r.json()["intensity"] == 0
        assert r.json()["status"] == "dormant"

        _force_leave([leader_char["id"]])

    def test_self_rivalry_rejected(self, admin_session, admin_chars):
        _wipe_round3(SLUG_FORGE)
        leader_char = admin_chars[0]
        _force_leave([leader_char["id"]])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "TEST"},
        )
        assert r.status_code == 200
        _promote_to_leader(SLUG_FORGE, leader_char["id"])
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={
                "actor_character_id": leader_char["id"],
                "target_slug": SLUG_FORGE,
            },
        )
        assert r.status_code == 400
        _force_leave([leader_char["id"]])

    def test_crime_auto_escalates_rivalry_in_rival_home_nation(self, admin_session, admin_chars):
        """Member of Forgemasters (home: dhor-kuldor) commits a major crime in
        aigraels (Ardent Legion's home). The active Forge↔Ardent rivalry should
        auto-bump by RIVALRY_CRIME_DELTA['major'] = 8."""
        _wipe_round3(SLUG_FORGE)
        _wipe_round3(SLUG_ARDENT)
        leader_char = admin_chars[0]
        member_char = admin_chars[1]
        _force_leave([leader_char["id"], member_char["id"]])

        # Setup: leader_char leads Forge, member_char is a regular member.
        admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        _promote_to_leader(SLUG_FORGE, leader_char["id"])
        admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": member_char["id"], "pitch": "member"},
        )

        # Declare rivalry on Ardent (aigraels).
        r = admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={
                "actor_character_id": leader_char["id"],
                "target_slug": SLUG_ARDENT,
                "reason": "TEST auto-escalation",
            },
        )
        assert r.status_code == 200
        rivalry_id = r.json()["id"]

        # Member commits a major crime in aigraels.
        async def _do_major(db):
            return await LawService(db).record_crime(
                character_id=member_char["id"],
                character_name=member_char["name"],
                user_id="test-user",
                nation="aigraels",
                location="Test Plaza",
                crime_type="arson",
                severity="major",
                description="TEST auto-escalation crime",
            )
        _run_db(_do_major)

        # Rivalry intensity should be 25 + 8 = 33.
        rivs = requests.get(f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries").json()
        match = next(r_ for r_ in rivs if r_["id"] == rivalry_id)
        assert match["intensity"] == 33, f"expected 33 (25 declared + 8 major auto), got {match['intensity']}"
        # 33 sits in the 25-49 'declared' band; needs ≥50 for 'escalated'.
        assert match["status"] == "declared"

        # History should have an 'auto' entry.
        kinds = [h["kind"] for h in match.get("history", [])]
        assert "auto" in kinds

        _force_leave([leader_char["id"], member_char["id"]])

    def test_admin_rivalries_list(self, admin_session, admin_chars):
        """Admin endpoint returns rivalries decorated with both faction names."""
        _wipe_round3(SLUG_FORGE)
        _wipe_round3(SLUG_ARDENT)
        leader_char = admin_chars[0]
        _force_leave([leader_char["id"]])
        admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/join",
            json={"character_id": leader_char["id"], "pitch": "leader"},
        )
        _promote_to_leader(SLUG_FORGE, leader_char["id"])
        admin_session.post(
            f"{BASE_URL}/api/factions/{SLUG_FORGE}/rivalries/declare",
            json={"actor_character_id": leader_char["id"], "target_slug": SLUG_ARDENT, "reason": "TEST admin list"},
        )
        r = admin_session.get(f"{BASE_URL}/api/admin/factions/rivalries")
        assert r.status_code == 200, r.text
        rows = r.json()
        # find the pair
        match = next(
            (r_ for r_ in rows if r_["faction_a"]["slug"] in (SLUG_FORGE, SLUG_ARDENT)
             and r_["faction_b"]["slug"] in (SLUG_FORGE, SLUG_ARDENT)),
            None,
        )
        assert match is not None
        _force_leave([leader_char["id"]])
