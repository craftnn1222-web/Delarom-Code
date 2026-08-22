"""Iteration B tests — assassinations, cults, black market."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from assassination_service import (  # noqa: E402
    AssassinationService,
    CONTRACT_STATUS_ACCEPTED, CONTRACT_STATUS_COMPLETED, CONTRACT_STATUS_FAILED,
    FIXER_FEE_PCT, MIN_BOUNTY,
)
from cults_service import CultService, CULTS, RITUALS  # noqa: E402
from black_market import BANNED_GOODS_BY_NATION, evaluate_route, is_contraband  # noqa: E402


def _run(async_fn):
    async def _outer():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbname = f"iter_b_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


async def _mk_user(db, gold=10000):
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid, "username": f"u_{uid[:6]}", "email": f"{uid[:6]}@t",
        "currency": gold, "status": "active", "role": "member",
    })
    return await db.users.find_one({"id": uid}, {"_id": 0})


async def _mk_char(db, user_id, name="Aiven", agi=10):
    cid = str(uuid.uuid4())
    await db.characters.insert_one({
        "id": cid, "user_id": user_id, "name": name,
        "race": "human", "character_class": "rogue",
        "strength": 10, "agility": agi, "magic": 5, "endurance": 10,
        "inventory": [],
    })
    return await db.characters.find_one({"id": cid}, {"_id": 0})


# ── Assassinations ───────────────────────────────────────────────

def test_post_contract_debits_and_holds_escrow():
    async def _(db):
        buyer = await _mk_user(db, gold=5000)
        buyer_ch = await _mk_char(db, buyer["id"])
        target_user = await _mk_user(db, gold=100)
        target = await _mk_char(db, target_user["id"], name="Bel")
        svc = AssassinationService(db)
        c = await svc.post_contract(
            buyer_user=buyer, buyer_character=buyer_ch,
            target_character_id=target["id"], city_slug="wymroost",
            reward_gold=1000, note="quiet, please",
        )
        assert c["fixer_fee"] == int(1000 * FIXER_FEE_PCT)
        assert c["escrow_gold"] == 1000 - c["fixer_fee"]
        u = await db.users.find_one({"id": buyer["id"]}, {"_id": 0})
        assert u["currency"] == 5000 - 1000
    _run(_)


def test_post_contract_rejects_below_min():
    async def _(db):
        buyer = await _mk_user(db, gold=5000)
        buyer_ch = await _mk_char(db, buyer["id"])
        target_user = await _mk_user(db)
        target = await _mk_char(db, target_user["id"], name="Bel")
        svc = AssassinationService(db)
        try:
            await svc.post_contract(
                buyer_user=buyer, buyer_character=buyer_ch,
                target_character_id=target["id"], city_slug="wymroost",
                reward_gold=MIN_BOUNTY - 1,
            )
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "minimum" in str(e).lower()
    _run(_)


def test_post_contract_rejects_self():
    async def _(db):
        buyer = await _mk_user(db, gold=5000)
        ch = await _mk_char(db, buyer["id"])
        svc = AssassinationService(db)
        try:
            await svc.post_contract(
                buyer_user=buyer, buyer_character=ch,
                target_character_id=ch["id"], city_slug="wymroost",
                reward_gold=500,
            )
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "own death" in str(e).lower()
    _run(_)


def test_attempt_success_settles_correctly():
    async def _(db):
        buyer = await _mk_user(db, gold=5000)
        buyer_ch = await _mk_char(db, buyer["id"])
        assn_user = await _mk_user(db, gold=100)
        assn_ch = await _mk_char(db, assn_user["id"], name="Blade", agi=99)  # guaranteed win
        target_user = await _mk_user(db)
        target_ch = await _mk_char(db, target_user["id"], name="Mark", agi=0)
        svc = AssassinationService(db)

        async def _fake_narrate(**kw):
            return "[STUB]"
        svc._narrate_attempt = _fake_narrate  # type: ignore[assignment]

        c = await svc.post_contract(
            buyer_user=buyer, buyer_character=buyer_ch,
            target_character_id=target_ch["id"], city_slug="wymroost",
            reward_gold=1000,
        )
        await svc.accept_contract(
            contract_id=c["id"],
            assassin_user=assn_user, assassin_character=assn_ch,
        )
        r = await svc.attempt(contract_id=c["id"], assassin_user=assn_user)
        assert r["status"] == CONTRACT_STATUS_COMPLETED
        # Escrow paid to assassin
        a = await db.users.find_one({"id": assn_user["id"]}, {"_id": 0})
        assert a["currency"] == 100 + int(1000 - 1000 * FIXER_FEE_PCT)
        # Target retired
        t = await db.characters.find_one({"id": target_ch["id"]}, {"_id": 0})
        assert t["status"] == "fallen"
    _run(_)


def test_board_redacts_buyer():
    async def _(db):
        buyer = await _mk_user(db, gold=5000)
        buyer_ch = await _mk_char(db, buyer["id"])
        target = await _mk_char(db, (await _mk_user(db))["id"], name="Bel")
        svc = AssassinationService(db)
        await svc.post_contract(
            buyer_user=buyer, buyer_character=buyer_ch,
            target_character_id=target["id"], city_slug="wymroost",
            reward_gold=500,
        )
        board = await svc.list_board()
        assert len(board) == 1
        row = board[0]
        assert row["buyer_user_id"] is None
        assert row["buyer_character_id"] is None
        assert row["buyer_character_name"] is None
    _run(_)


# ── Cults ────────────────────────────────────────────────────────

def test_seed_cults_idempotent():
    async def _(db):
        svc = CultService(db)
        first = await svc.seed_cults()
        assert first["inserted"] == len(CULTS)
        second = await svc.seed_cults()
        assert second["inserted"] == 0
    _run(_)


def test_join_cult_debits_all_four_gods():
    async def _(db):
        svc = CultService(db)
        await svc.seed_cults()
        char = await _mk_char(db, (await _mk_user(db))["id"])
        mem = await svc.join_cult(character_id=char["id"], cult_slug="forsaken-court")
        assert mem["cult_slug"] == "forsaken-court"
        # Every Elder God takes a -50 hit
        from reputation_web_service import ReputationWebService
        rep = ReputationWebService(db)
        for god in ("seren", "yros", "uesis", "ehena"):
            row = await rep.get_axis(char["id"], "god", god)
            assert row["score"] == -50
    _run(_)


def test_join_cult_twice_rejected():
    async def _(db):
        svc = CultService(db)
        await svc.seed_cults()
        char = await _mk_char(db, (await _mk_user(db))["id"])
        await svc.join_cult(character_id=char["id"], cult_slug="forsaken-court")
        try:
            await svc.join_cult(character_id=char["id"], cult_slug="ashen-titan")
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "already keep" in str(e).lower() or "forbidden oath" in str(e).lower()
    _run(_)


def test_curse_shop_ritual_marks_effect():
    async def _(db):
        svc = CultService(db)
        await svc.seed_cults()
        user = await _mk_user(db, gold=1000)
        char = await _mk_char(db, user["id"])
        await svc.join_cult(character_id=char["id"], cult_slug="forsaken-court")
        # Seed a target shop
        shop_id = str(uuid.uuid4())
        await db.shops.insert_one({"id": shop_id, "owner_id": "victim", "name": "V", "description": "d", "nation": "Ammeonon"})
        r = await svc.cast_ritual(
            character_id=char["id"], user_id=user["id"],
            ritual_slug="curse-shop", target_ref=shop_id,
        )
        assert r["ritual"] == "curse-shop"
        assert await svc.is_shop_cursed(shop_id) is True
        # Gold debited
        u2 = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        assert u2["currency"] == 1000 - RITUALS["curse-shop"]["cost_gold"]
    _run(_)


def test_ritual_requires_cult_membership():
    async def _(db):
        svc = CultService(db)
        await svc.seed_cults()
        user = await _mk_user(db, gold=1000)
        char = await _mk_char(db, user["id"])
        try:
            await svc.cast_ritual(
                character_id=char["id"], user_id=user["id"],
                ritual_slug="unseen-hand",
            )
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "cult-member" in str(e).lower() or "forbidden" in str(e).lower()
    _run(_)


# ── Black Market ────────────────────────────────────────────────

def test_is_contraband_table():
    # Selindori bans iron-swords; Ammeonon doesn't
    assert is_contraband("selindori", "iron-swords") is True
    assert is_contraband("ammeonon", "iron-swords") is False
    assert is_contraband("dhor-kuldor", "silken-cloth") is True
    assert is_contraband("aigraels", "iron-swords") is False


def test_evaluate_route_returns_none_for_legal_good():
    async def _(db):
        company = {"id": "c", "treasury": 5000}
        route = {
            "id": "r", "source_nation": "ammeonon", "source_city_slug": "duncroft",
            "dest_nation": "ammeonon", "dest_city_slug": "wymroost",
            "good_slug": "grain", "units_per_run": 20,
        }
        r = await evaluate_route(db, company, route)
        assert r is None
    _run(_)
