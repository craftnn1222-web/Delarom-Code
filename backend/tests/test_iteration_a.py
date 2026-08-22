"""Iteration A tests — world calendar, reputation web, duels."""
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

from world_calendar_service import (  # noqa: E402
    ANCHOR_UTC, ANCHOR_YEAR, WORLD_DAYS_PER_REAL_DAY,
    add_world_days, get_world_calendar, world_days_since_anchor,
)
from reputation_web_service import ReputationWebService, label_for  # noqa: E402
from duel_service import DuelService, STATUS_RESOLVED, STATUS_DECLINED  # noqa: E402


def _run(async_fn):
    async def _outer():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbname = f"iter_a_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


# ── world calendar ───────────────────────────────────────────────

def test_anchor_is_215_ae_day_one():
    c = get_world_calendar(ANCHOR_UTC)
    assert c["year"] == 215
    assert c["month_index"] == 1
    assert c["day"] == 1
    assert c["compact"].endswith("215 A.E.")


def test_ratio_advances_one_month_per_real_week():
    # 7 real days after anchor → +1 world month
    dt = ANCHOR_UTC + timedelta(days=7)
    c = get_world_calendar(dt)
    assert c["year"] == 215
    assert c["month_index"] == 2  # from index 1 (Stormwane) → 2 (Greenwake)
    assert c["day"] == 1


def test_ratio_advances_one_year_per_twelve_weeks():
    # 12 real weeks (84 days) = 12 world months = +1 world year
    dt = ANCHOR_UTC + timedelta(days=84)
    c = get_world_calendar(dt)
    assert c["year"] == 216
    assert c["month_index"] == 1  # back to Stormwane


def test_world_days_ratio():
    # 1 real day == 30/7 world days ≈ 4.28
    days = world_days_since_anchor(ANCHOR_UTC + timedelta(days=7))
    assert days == 30
    assert abs(WORLD_DAYS_PER_REAL_DAY - 30 / 7) < 1e-9


def test_add_world_days_returns_real_iso():
    base = ANCHOR_UTC.isoformat()
    plus_30_world = add_world_days(base, 30)
    parsed = datetime.fromisoformat(plus_30_world.replace("Z", "+00:00"))
    # 30 world days == 7 real days
    delta = (parsed - ANCHOR_UTC).total_seconds()
    assert abs(delta - 7 * 86400) < 1.0


# ── reputation web ──────────────────────────────────────────────

def test_label_bands():
    assert label_for(0) == "Nobody"
    assert label_for(50) == "Respected"
    assert label_for(90) == "Legend"
    assert label_for(-60) == "Reviled"
    assert label_for(-100) == "Hunted"


def test_rep_adjust_creates_and_updates():
    async def _(db):
        rep = ReputationWebService(db)
        r = await rep.adjust("char1", "city", "wymroost", +25, "helped a merchant")
        assert r["score"] == 25
        assert r["label"] == "Known"
        assert len(r["drivers"]) == 1
        r = await rep.adjust("char1", "city", "wymroost", -10, "shortchanged a widow")
        assert r["score"] == 15
        assert len(r["drivers"]) == 2
    _run(_)


def test_rep_clamps_at_boundaries():
    async def _(db):
        rep = ReputationWebService(db)
        # Try to push past 100
        for _ in range(10):
            await rep.adjust("c", "god", "seren", +30, "prayer")
        r = await rep.get_axis("c", "god", "seren")
        assert r["score"] == 100
        assert r["label"] == "Legend"
    _run(_)


def test_price_modifier_shifts_correctly():
    async def _(db):
        rep = ReputationWebService(db)
        # Nobody → 1.0
        assert await rep.shop_price_modifier("c", "wymroost") == 1.0
        # Legend → 0.75 (need multiple pushes because MAX_DELTA=30 per adjust)
        for _ in range(5):
            await rep.adjust("c", "city", "wymroost", +30, "renown")
        assert (await rep.get_axis("c", "city", "wymroost"))["score"] == 100
        assert await rep.shop_price_modifier("c", "wymroost") == 0.75
        # Hunted → 1.25 (drive back down and then all the way to -100)
        for _ in range(10):
            await rep.adjust("c", "city", "wymroost", -30, "hated")
        assert (await rep.get_axis("c", "city", "wymroost"))["score"] == -100
        assert await rep.shop_price_modifier("c", "wymroost") == 1.25
    _run(_)


def test_guard_stance_bands():
    async def _(db):
        rep = ReputationWebService(db)
        assert await rep.guard_stance("c", "wymroost") == "ignore"
        for _ in range(2):
            await rep.adjust("c", "city", "wymroost", +30, "hero")
        assert await rep.guard_stance("c", "wymroost") in ("nod", "salute")
        for _ in range(5):
            await rep.adjust("c", "city", "wymroost", -30, "villain")
        assert await rep.guard_stance("c", "wymroost") == "arrest"
    _run(_)


def test_god_favour_bias():
    async def _(db):
        rep = ReputationWebService(db)
        assert await rep.god_favour_bias("c", "seren") == 0
        for _ in range(5):
            await rep.adjust("c", "god", "seren", +30, "faithful")
        assert (await rep.get_axis("c", "god", "seren"))["score"] == 100
        assert await rep.god_favour_bias("c", "seren") == 25
        for _ in range(10):
            await rep.adjust("c", "god", "seren", -30, "blasphemer")
        assert (await rep.get_axis("c", "god", "seren"))["score"] == -100
        assert await rep.god_favour_bias("c", "seren") == -25
    _run(_)


# ── duels ─────────────────────────────────────────────────────

async def _mk_char(db, user_id="u1", name="A", strength=10, agility=10, magic=10):
    cid = str(uuid.uuid4())
    await db.characters.insert_one({
        "id": cid, "user_id": user_id, "name": name,
        "race": "human", "character_class": "fighter",
        "strength": strength, "agility": agility, "magic": magic,
        "endurance": 10, "inventory": [],
    })
    return await db.characters.find_one({"id": cid}, {"_id": 0})


def test_challenge_rejects_self_duel():
    async def _(db):
        chal_user = {"id": "u1", "username": "u1"}
        chal = await _mk_char(db, "u1", "Aiven")
        svc = DuelService(db)
        try:
            await svc.challenge(
                challenger_user=chal_user, challenger_character=chal,
                target_character_id=chal["id"], city_slug="wymroost",
                weapon="blade", stakes="renown",
            )
            raise AssertionError("expected ValueError for self-duel")
        except ValueError as e:
            assert "yourself" in str(e).lower()
    _run(_)


def test_challenge_and_decline_penalises_target_renown():
    async def _(db):
        chal = await _mk_char(db, "u1", "Aiven")
        tgt = await _mk_char(db, "u2", "Bel")
        # Give target a base renown so we can see the drop
        await ReputationWebService(db).adjust(tgt["id"], "city", "wymroost", +30, "seed")
        svc = DuelService(db)
        duel = await svc.challenge(
            challenger_user={"id": "u1"}, challenger_character=chal,
            target_character_id=tgt["id"], city_slug="wymroost",
            weapon="blade", stakes="renown",
        )
        result = await svc.decline(duel_id=duel["id"], user_id="u2")
        assert result["status"] == STATUS_DECLINED
        # Target lost 5 Renown for cowardice
        rep = await ReputationWebService(db).get_axis(tgt["id"], "city", "wymroost")
        assert rep["score"] == 25
    _run(_)


def test_accept_and_resolve_settles_gold_and_renown(monkeypatch):
    async def _(db):
        # Give both players starting gold
        await db.users.insert_one({"id": "u1", "username": "u1", "currency": 500, "role": "member", "status": "active"})
        await db.users.insert_one({"id": "u2", "username": "u2", "currency": 500, "role": "member", "status": "active"})
        # Stack the deck so the challenger clearly wins (huge strength diff)
        chal = await _mk_char(db, "u1", "Aiven", strength=50)
        tgt = await _mk_char(db, "u2", "Bel", strength=0)
        svc = DuelService(db)
        # Stub the LLM
        async def _fake_narrate(**kwargs):
            return "[DUEL-STUB]"
        svc._narrate = _fake_narrate  # type: ignore[assignment]

        duel = await svc.challenge(
            challenger_user={"id": "u1"}, challenger_character=chal,
            target_character_id=tgt["id"], city_slug="wymroost",
            weapon="blade", stakes="gold", wager_gold=100,
        )
        result = await svc.accept_and_resolve(duel_id=duel["id"], user_id="u2")
        assert result["status"] == STATUS_RESOLVED
        assert result["winner_character_id"] == chal["id"]
        # Gold transferred
        u1 = await db.users.find_one({"id": "u1"}, {"_id": 0})
        u2 = await db.users.find_one({"id": "u2"}, {"_id": 0})
        assert u1["currency"] == 600
        assert u2["currency"] == 400
        # Renown swung
        chal_rep = await ReputationWebService(db).get_axis(chal["id"], "city", "wymroost")
        tgt_rep = await ReputationWebService(db).get_axis(tgt["id"], "city", "wymroost")
        assert chal_rep["score"] == 8
        assert tgt_rep["score"] == -8
    _run(_)


def test_death_duel_retires_loser():
    async def _(db):
        await db.users.insert_one({"id": "u1", "username": "u1", "currency": 500, "role": "member", "status": "active"})
        await db.users.insert_one({"id": "u2", "username": "u2", "currency": 500, "role": "member", "status": "active"})
        chal = await _mk_char(db, "u1", "Aiven", strength=50)
        tgt = await _mk_char(db, "u2", "Bel", strength=0)
        svc = DuelService(db)
        async def _fake_narrate(**kwargs):
            return "[DUEL-STUB]"
        svc._narrate = _fake_narrate  # type: ignore[assignment]
        duel = await svc.challenge(
            challenger_user={"id": "u1"}, challenger_character=chal,
            target_character_id=tgt["id"], city_slug="wymroost",
            weapon="blade", stakes="death",
        )
        await svc.accept_and_resolve(duel_id=duel["id"], user_id="u2")
        loser = await db.characters.find_one({"id": tgt["id"]}, {"_id": 0})
        assert loser["status"] == "fallen"
        assert loser.get("fallen_reason")
    _run(_)
