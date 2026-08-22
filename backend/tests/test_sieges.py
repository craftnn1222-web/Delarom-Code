"""Contested Cities — siege service tests."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from siege_service import (  # noqa: E402
    SiegeService, DECLARATION_COST,
    STATUS_ACTIVE, STATUS_RESOLVED, STATUS_ABANDONED,
    RESOLUTION_SEIZED, RESOLUTION_REPELLED, RESOLUTION_ABANDONED,
    SIDE_ATTACKER, SIDE_DEFENDER,
)


def _run(async_fn):
    async def _outer():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbname = f"siege_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


async def _mk_user(db, gold=5000):
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid, "username": f"u_{uid[:6]}", "email": f"{uid[:6]}@t",
        "currency": gold, "status": "active", "role": "member",
    })
    return await db.users.find_one({"id": uid}, {"_id": 0})


async def _mk_char(db, user_id, name="Ausar"):
    cid = str(uuid.uuid4())
    await db.characters.insert_one({
        "id": cid, "user_id": user_id, "name": name,
        "race": "human", "character_class": "warrior",
        "strength": 10, "agility": 10, "magic": 5, "endurance": 10,
        "inventory": [],
    })
    return await db.characters.find_one({"id": cid}, {"_id": 0})


async def _mk_faction(db, name, slug, status="approved"):
    fid = str(uuid.uuid4())
    await db.factions.insert_one({
        "id": fid, "slug": slug, "name": name, "status": status,
        "is_active": True, "member_count": 0,
    })
    return await db.factions.find_one({"id": fid}, {"_id": 0})


async def _mk_membership(db, char_id, faction_id, rank="leader"):
    mid = str(uuid.uuid4())
    await db.faction_memberships.insert_one({
        "id": mid, "character_id": char_id, "faction_id": faction_id,
        "rank": rank, "status": "active",
    })


async def _mk_location(db, name="Grand Cathedral", slug="grand-cathedral",
                       nation="ammeonon", city="wymroost"):
    lid = str(uuid.uuid4())
    await db.locations.insert_one({
        "id": lid, "name": name, "slug": slug, "nation": nation, "city": city,
        "location_type": "landmark", "is_active": True,
    })
    return await db.locations.find_one({"id": lid}, {"_id": 0})


async def _mk_city(db, slug="wymroost", nation="ammeonon"):
    cid = str(uuid.uuid4())
    await db.cities.insert_one({
        "id": cid, "slug": slug, "nation": nation, "name": slug.title(),
        "is_active": True,
    })


# ── declaration ─────────────────────────────────────────────────────────

def test_declare_charges_500_and_creates_active_siege():
    async def _(db):
        u = await _mk_user(db, gold=2000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Ardent Legion", "ardent-legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        await _mk_city(db)

        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="ardent-legion",
        )
        assert s["status"] == STATUS_ACTIVE
        assert s["attacker_faction_slug"] == "ardent-legion"
        assert s["target_location_id"] == loc["id"]
        # 500g moved
        u2 = await db.users.find_one({"id": u["id"]}, {"_id": 0})
        assert u2["currency"] == 2000 - DECLARATION_COST
        # location siege_state stamped
        loc2 = await db.locations.find_one({"id": loc["id"]}, {"_id": 0})
        assert loc2["siege_state"]["siege_id"] == s["id"]
    _run(_)


def test_declare_requires_officer_or_leader_rank():
    async def _(db):
        u = await _mk_user(db)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Wolves", "wolves")
        await _mk_membership(db, c["id"], fac["id"], rank="initiate")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        try:
            await svc.declare_siege(
                user=u, character=c, location_id=loc["id"],
                attacker_faction_slug="wolves",
            )
            assert False, "expected ValueError"
        except ValueError as e:
            assert "Officer or Leader" in str(e)
    _run(_)


def test_declare_rejects_if_already_controlled():
    async def _(db):
        u = await _mk_user(db)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        await db.locations.update_one(
            {"id": loc["id"]},
            {"$set": {"controlling_faction_slug": "other-faction"}},
        )
        svc = SiegeService(db)
        try:
            await svc.declare_siege(
                user=u, character=c, location_id=loc["id"],
                attacker_faction_slug="legion",
            )
            assert False
        except ValueError as e:
            assert "already controlled" in str(e).lower()
    _run(_)


def test_declare_rejects_if_broke():
    async def _(db):
        u = await _mk_user(db, gold=100)   # < 500
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Broke Faction", "broke")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        try:
            await svc.declare_siege(
                user=u, character=c, location_id=loc["id"],
                attacker_faction_slug="broke",
            )
            assert False
        except ValueError as e:
            assert "500" in str(e) or "coffers" in str(e).lower()
    _run(_)


def test_declare_rejects_duplicate_siege():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        # Second declaration → conflict
        u = await db.users.find_one({"id": u["id"]}, {"_id": 0})
        try:
            await svc.declare_siege(
                user=u, character=c, location_id=loc["id"],
                attacker_faction_slug="legion",
            )
            assert False
        except ValueError as e:
            assert "already active" in str(e).lower()
    _run(_)


# ── counter-claim ───────────────────────────────────────────────────────

def test_counter_claim_records_defender():
    async def _(db):
        u1 = await _mk_user(db, gold=5000)
        c1 = await _mk_char(db, u1["id"], name="Ausar")
        f1 = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c1["id"], f1["id"], rank="leader")

        u2 = await _mk_user(db, gold=5000)
        c2 = await _mk_char(db, u2["id"], name="Elin")
        f2 = await _mk_faction(db, "Guardians", "guardians")
        await _mk_membership(db, c2["id"], f2["id"], rank="officer")

        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u1, character=c1, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        s2 = await svc.counter_claim(
            user=u2, character=c2, siege_id=s["id"],
            defender_faction_slug="guardians",
        )
        assert s2["defender_faction_slug"] == "guardians"
        assert s2["defender_faction_name"] == "Guardians"
    _run(_)


def test_counter_claim_rejects_self_defence():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        try:
            await svc.counter_claim(
                user=u, character=c, siege_id=s["id"],
                defender_faction_slug="legion",
            )
            assert False
        except ValueError as e:
            assert "against itself" in str(e).lower()
    _run(_)


def test_counter_claim_rejects_second_defender():
    async def _(db):
        u1 = await _mk_user(db, gold=5000)
        c1 = await _mk_char(db, u1["id"])
        f1 = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c1["id"], f1["id"], rank="leader")

        u2 = await _mk_user(db)
        c2 = await _mk_char(db, u2["id"])
        f2 = await _mk_faction(db, "Guardians", "guardians")
        await _mk_membership(db, c2["id"], f2["id"], rank="leader")

        u3 = await _mk_user(db)
        c3 = await _mk_char(db, u3["id"])
        f3 = await _mk_faction(db, "Watch", "watch")
        await _mk_membership(db, c3["id"], f3["id"], rank="leader")

        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u1, character=c1, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        await svc.counter_claim(
            user=u2, character=c2, siege_id=s["id"],
            defender_faction_slug="guardians",
        )
        try:
            await svc.counter_claim(
                user=u3, character=c3, siege_id=s["id"],
                defender_faction_slug="watch",
            )
            assert False
        except ValueError as e:
            assert "already answered" in str(e).lower()
    _run(_)


# ── contributions ───────────────────────────────────────────────────────

def test_contribute_increments_correct_side():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        u2 = await _mk_user(db)
        c2 = await _mk_char(db, u2["id"], name="Rally")
        r = await svc.contribute(
            user=u2, character=c2, siege_id=s["id"],
            side=SIDE_ATTACKER,
            action_text="I rally the townsfolk to the banner and hold the gate against the guards.",
        )
        assert r["siege"]["attacker_contribution_count"] == 1
        assert r["siege"]["defender_contribution_count"] == 0
    _run(_)


def test_contribute_rejects_dupes():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        await svc.contribute(
            user=u, character=c, siege_id=s["id"],
            side=SIDE_ATTACKER,
            action_text="I lift the banner and march at the head of the column into the square.",
        )
        try:
            await svc.contribute(
                user=u, character=c, siege_id=s["id"],
                side=SIDE_ATTACKER,
                action_text="I raise the banner again and march into the square once more.",
            )
            assert False
        except ValueError as e:
            assert "already committed" in str(e).lower()
    _run(_)


def test_contribute_min_length_enforced():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        try:
            await svc.contribute(
                user=u, character=c, siege_id=s["id"],
                side=SIDE_ATTACKER,
                action_text="short.",
            )
            assert False
        except ValueError as e:
            assert "20 characters" in str(e).lower()
    _run(_)


# ── resolution ──────────────────────────────────────────────────────────

def test_force_resolve_seized_when_attacker_leads():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        await _mk_city(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        u2 = await _mk_user(db)
        c2 = await _mk_char(db, u2["id"], name="Ally")
        await svc.contribute(
            user=u2, character=c2, siege_id=s["id"],
            side=SIDE_ATTACKER,
            action_text="I bar the eastern gate so no guards can flank the column.",
        )
        # No defender contributions → attacker seizes
        resolved = await svc.force_resolve(s["id"])
        assert resolved["status"] == STATUS_RESOLVED
        assert resolved["resolution"] == RESOLUTION_SEIZED
        assert resolved["winner_side"] == SIDE_ATTACKER
        loc2 = await db.locations.find_one({"id": loc["id"]}, {"_id": 0})
        assert loc2["controlling_faction_slug"] == "legion"
        assert loc2.get("siege_state") is None
    _run(_)


def test_force_resolve_repelled_when_defender_leads():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")

        u2 = await _mk_user(db)
        c2 = await _mk_char(db, u2["id"], name="Defender-Lead")
        f2 = await _mk_faction(db, "Guardians", "guardians")
        await _mk_membership(db, c2["id"], f2["id"], rank="officer")

        loc = await _mk_location(db)
        await _mk_city(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        await svc.counter_claim(
            user=u2, character=c2, siege_id=s["id"],
            defender_faction_slug="guardians",
        )
        u3 = await _mk_user(db)
        c3 = await _mk_char(db, u3["id"], name="Villager1")
        c4 = await _mk_char(db, u3["id"], name="Villager2")
        await svc.contribute(
            user=u3, character=c3, siege_id=s["id"],
            side=SIDE_DEFENDER,
            action_text="I lock the cathedral doors from within and light the alarm braziers.",
        )
        await svc.contribute(
            user=u3, character=c4, siege_id=s["id"],
            side=SIDE_DEFENDER,
            action_text="I lead the townsfolk to bar the courtyard and repel the attackers.",
        )
        resolved = await svc.force_resolve(s["id"])
        assert resolved["resolution"] == RESOLUTION_REPELLED
        loc2 = await db.locations.find_one({"id": loc["id"]}, {"_id": 0})
        assert loc2.get("controlling_faction_slug") is None
    _run(_)


def test_force_resolve_abandoned_when_no_contributions():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        resolved = await svc.force_resolve(s["id"])
        assert resolved["status"] == STATUS_ABANDONED
        assert resolved["resolution"] == RESOLUTION_ABANDONED
        loc2 = await db.locations.find_one({"id": loc["id"]}, {"_id": 0})
        assert loc2.get("controlling_faction_slug") is None
    _run(_)


def test_resolve_if_due_no_op_before_expiry():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        r = await svc.resolve_if_due(s["id"])
        assert r["status"] == STATUS_ACTIVE
    _run(_)


def test_resolve_if_due_resolves_past_expiry():
    async def _(db):
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc = await _mk_location(db)
        svc = SiegeService(db)
        s = await svc.declare_siege(
            user=u, character=c, location_id=loc["id"],
            attacker_faction_slug="legion",
        )
        # Rewind expires_at to the past
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        await db.sieges.update_one({"id": s["id"]}, {"$set": {"expires_at": past}})
        r = await svc.resolve_if_due(s["id"])
        assert r["status"] in (STATUS_RESOLVED, STATUS_ABANDONED)
    _run(_)


def test_sweep_due_batch_resolves_multiple():
    async def _(db):
        # Two sieges — one past expiry, one still active
        u = await _mk_user(db, gold=5000)
        c = await _mk_char(db, u["id"])
        fac = await _mk_faction(db, "Legion", "legion")
        await _mk_membership(db, c["id"], fac["id"], rank="leader")
        loc_a = await _mk_location(db, name="A", slug="a")
        loc_b = await _mk_location(db, name="B", slug="b")
        svc = SiegeService(db)
        s_a = await svc.declare_siege(
            user=u, character=c, location_id=loc_a["id"],
            attacker_faction_slug="legion",
        )
        u = await db.users.find_one({"id": u["id"]}, {"_id": 0})
        s_b = await svc.declare_siege(
            user=u, character=c, location_id=loc_b["id"],
            attacker_faction_slug="legion",
        )
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        await db.sieges.update_one({"id": s_a["id"]}, {"$set": {"expires_at": past}})
        report = await svc.sweep_due()
        assert report["resolved"] == 1
        b = await db.sieges.find_one({"id": s_b["id"]}, {"_id": 0})
        assert b["status"] == STATUS_ACTIVE
    _run(_)
