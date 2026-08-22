"""Party service tests — party lifecycle, join/leave, turn rotation.

Uses a real Motor client scoped to a throw-away DB namespace so we do not
need pytest-asyncio. Each test wraps its own coroutine in `asyncio.run`
so the Motor client is bound to a fresh event loop.

The MoC LLM call is monkey-patched to a deterministic stub so tests do
not hit OpenAI.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

from dotenv import load_dotenv

# Load backend .env so MONGO_URL is available even under pytest.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from party_service import (  # noqa: E402
    STATUS_ACTIVE,
    STATUS_FINISHED,
    STATUS_RECRUITING,
    PartyService,
)


def _mk_user(username="host"):
    return {"id": str(uuid.uuid4()), "username": username}


def _mk_char(user_id, name="Aiven"):
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "race": "elf",
        "character_class": "ranger",
    }


def _stub_svc(svc):
    async def _fake(system_message, user_payload, *, session_key):  # noqa: ARG001
        return f"[MOC-STUB] {session_key}"
    svc._call_llm = _fake  # type: ignore[assignment]
    return svc


def _run_with_db(async_fn):
    """Bind a fresh Motor client to the same loop the test runs in."""
    async def _outer():
        mongo_url = os.environ["MONGO_URL"]
        client = AsyncIOMotorClient(mongo_url)
        dbname = f"party_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


# ── tests ────────────────────────────────────────────────────────────

def test_create_party_seeds_host_as_first_turn():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user()
        host_char = _mk_char(host["id"])
        party = await svc.create_party(
            host_user=host, host_character=host_char,
            name="A Night in Selincoast",
            scene_description="The lantern-lit dock at midnight, wharf-hands calling out.",
            location="Selincoast, Selindori",
            max_members=4,
        )
        assert party["status"] == STATUS_RECRUITING
        assert party["host_user_id"] == host["id"]
        assert party["turn_order"] == [host_char["id"]]
        assert party["current_turn_index"] == 0
        assert len(party["members"]) == 1
        assert party["members"][0]["role"] == "host"
    _run_with_db(_)


def test_join_appends_to_turn_order_and_members():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host, other = _mk_user("host"), _mk_user("other")
        hc, oc = _mk_char(host["id"]), _mk_char(other["id"], name="Rhosa")
        party = await svc.create_party(
            host_user=host, host_character=hc,
            name="Test", scene_description="A quiet inn by the crossroads.",
            location="Ammeonon crossroads",
        )
        party = await svc.join_party(party_id=party["id"], user=other, character=oc)
        assert len(party["members"]) == 2
        assert party["turn_order"] == [hc["id"], oc["id"]]
    _run_with_db(_)


def test_join_rejects_full_and_duplicate():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"])
        party = await svc.create_party(
            host_user=host, host_character=hc,
            name="Small", scene_description="A cramped tavern back-room, one lantern.",
            location="Yerelan", max_members=2,
        )
        b, c = _mk_user("b"), _mk_user("c")
        bc = _mk_char(b["id"], name="Bel")
        cc = _mk_char(c["id"], name="Cel")
        await svc.join_party(party_id=party["id"], user=b, character=bc)
        try:
            await svc.join_party(party_id=party["id"], user=c, character=cc)
            raise AssertionError("expected ValueError for full party")
        except ValueError as e:
            assert "full" in str(e)
        try:
            await svc.join_party(party_id=party["id"], user=host, character=hc)
            raise AssertionError("expected ValueError for duplicate host join")
        except ValueError as e:
            assert "already in this party" in str(e)
    _run_with_db(_)


def test_leave_removes_from_turn_order():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"], name="Aiven")
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="A moonlit shore where the tide keeps time.",
            location="Yr'sivan",
        )
        b = _mk_user("b")
        bc = _mk_char(b["id"], name="Bel")
        await svc.join_party(party_id=p["id"], user=b, character=bc)
        await svc.start_party(party_id=p["id"], user_id=host["id"])
        await db.parties.update_one({"id": p["id"]}, {"$set": {"current_turn_index": 1}})
        p = await svc.leave_party(party_id=p["id"], user_id=b["id"])
        assert bc["id"] not in p["turn_order"]
        assert p["turn_order"] == [hc["id"]]
        assert p["current_turn_index"] == 0
    _run_with_db(_)


def test_leave_host_forbidden():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"])
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="An empty road under the eclipse.",
            location="Y",
        )
        try:
            await svc.leave_party(party_id=p["id"], user_id=host["id"])
            raise AssertionError("expected ValueError for host leaving")
        except ValueError as e:
            assert "host cannot leave" in str(e).lower()
    _run_with_db(_)


def test_start_writes_opening_narration():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"])
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="A tavern at closing time.",
            location="Y",
        )
        p = await svc.start_party(party_id=p["id"], user_id=host["id"])
        assert p["status"] == STATUS_ACTIVE
        actions = await svc.get_actions(p["id"])
        assert len(actions) == 1
        assert actions[0]["turn_number"] == 0
        assert actions[0]["actor_character_name"] == "Master of Ceremonies"
    _run_with_db(_)


def test_start_only_by_host():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"])
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="A lantern-lit alley just after rain.",
            location="Y",
        )
        b = _mk_user("b")
        bc = _mk_char(b["id"])
        await svc.join_party(party_id=p["id"], user=b, character=bc)
        try:
            await svc.start_party(party_id=p["id"], user_id=b["id"])
            raise AssertionError("expected ValueError for non-host start")
        except ValueError as e:
            assert "host" in str(e).lower()
    _run_with_db(_)


def test_submit_action_rejects_not_your_turn():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"], name="Aiven")
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="An inn hearth where the fire is dying.",
            location="Y",
        )
        b = _mk_user("b")
        bc = _mk_char(b["id"], name="Bel")
        await svc.join_party(party_id=p["id"], user=b, character=bc)
        await svc.start_party(party_id=p["id"], user_id=host["id"])
        try:
            await svc.submit_action(
                party_id=p["id"], user_id=b["id"], action_text="I speak.",
            )
            raise AssertionError("expected ValueError for wrong-turn action")
        except ValueError as e:
            assert "not your turn" in str(e).lower()
    _run_with_db(_)


def test_submit_action_advances_turn():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"], name="Aiven")
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="A cliffside where seabirds argue.",
            location="Y",
        )
        b = _mk_user("b")
        bc = _mk_char(b["id"], name="Bel")
        await svc.join_party(party_id=p["id"], user=b, character=bc)
        await svc.start_party(party_id=p["id"], user_id=host["id"])
        r = await svc.submit_action(
            party_id=p["id"], user_id=host["id"], action_text="I step forward.",
        )
        assert r["actor_character_name"] == "Aiven"
        p2 = await svc.get_party(p["id"])
        assert p2["current_turn_index"] == 1
        r = await svc.submit_action(
            party_id=p["id"], user_id=b["id"], action_text="I speak up.",
        )
        assert r["actor_character_name"] == "Bel"
        p2 = await svc.get_party(p["id"])
        assert p2["current_turn_index"] == 0
        actions = await svc.get_actions(p["id"])
        assert len(actions) == 3  # opening + 2 turns
    _run_with_db(_)


def test_finish_prevents_further_actions():
    async def _(db):
        svc = _stub_svc(PartyService(db))
        host = _mk_user("host")
        hc = _mk_char(host["id"])
        p = await svc.create_party(
            host_user=host, host_character=hc,
            name="X", scene_description="A shrine on a mountainside.",
            location="Y",
        )
        await svc.start_party(party_id=p["id"], user_id=host["id"])
        p = await svc.finish_party(party_id=p["id"], user_id=host["id"])
        assert p["status"] == STATUS_FINISHED
        try:
            await svc.submit_action(
                party_id=p["id"], user_id=host["id"], action_text="I look around.",
            )
            raise AssertionError("expected ValueError for action on finished party")
        except ValueError as e:
            assert "not currently active" in str(e).lower()
    _run_with_db(_)
