"""Producers + trade companies — end-to-end integration tests.

Uses a scoped Motor client per test so we don't need pytest-asyncio.
"""
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

from producers_service import (  # noqa: E402
    CITY_PRODUCERS_SEED,
    EconomyProducers,
    OWNER_CITY,
    OWNER_FACTION,
)
from trade_companies_service import (  # noqa: E402
    CHARTER_FEE,
    SHARE_PRICE,
    TradeCompanyService,
    run_trade_ticks,
)


def _run(async_fn):
    async def _outer():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbname = f"producers_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


# ── producer tests ───────────────────────────────────────────────

def test_seed_is_idempotent_and_covers_all_realms():
    async def _(db):
        first = await EconomyProducers(db).seed_city_producers()
        assert first["inserted"] == len(CITY_PRODUCERS_SEED)
        second = await EconomyProducers(db).seed_city_producers()
        assert second["inserted"] == 0
        assert second["updated"] == len(CITY_PRODUCERS_SEED)
        # All five realms covered
        realms = await db.city_producers.distinct("nation")
        for expected in ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]:
            assert expected in realms, f"Missing realm: {expected}"
    _run(_)


def test_run_tick_fills_city_inventory():
    async def _(db):
        prods = EconomyProducers(db)
        await prods.seed_city_producers()
        summary = await prods.run_tick(source="test")
        assert summary["producers_run"] >= len(CITY_PRODUCERS_SEED)
        assert summary["units_produced"] > 0
        stock = await prods.get_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft", good_slug="grain",
        )
        # Duncroft grain producer emits 95/tick
        assert stock == 95
    _run(_)


def test_warehouse_cap_prevents_overflow():
    async def _(db):
        prods = EconomyProducers(db)
        await prods.seed_city_producers()
        # Force a low cap on grain producer
        await db.city_producers.update_one(
            {"nation": "ammeonon", "city_slug": "duncroft", "good_slug": "grain"},
            {"$set": {"warehouse_cap": 100, "units_per_tick": 95}},
        )
        # Two ticks — second one should clamp
        await prods.run_tick(source="test")
        await prods.run_tick(source="test")
        stock = await prods.get_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft", good_slug="grain",
        )
        assert stock == 100
    _run(_)


def test_maybe_run_tick_respects_6h_window():
    async def _(db):
        prods = EconomyProducers(db)
        await prods.seed_city_producers()
        # First call — no prior tick, so it runs.
        first = await prods.maybe_run_tick()
        assert first is not None
        # Immediate second call — must be a no-op.
        second = await prods.maybe_run_tick()
        assert second is None
    _run(_)


def test_draw_from_inventory_atomic():
    async def _(db):
        prods = EconomyProducers(db)
        await prods.seed_city_producers()
        await prods.run_tick(source="test")
        # Duncroft has 95 grain — try to draw 100, must fail
        ok = await prods.draw_from_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft",
            nation="ammeonon", good_slug="grain", units=100,
        )
        assert ok is False
        # Draw 50 → succeeds
        ok = await prods.draw_from_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft",
            nation="ammeonon", good_slug="grain", units=50,
        )
        assert ok is True
        remaining = await prods.get_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft", good_slug="grain",
        )
        assert remaining == 45
    _run(_)


def test_faction_specialties_feed_faction_inventory():
    async def _(db):
        # Seed a fake faction + specialty
        faction_id = str(uuid.uuid4())
        await db.factions.insert_one({
            "id": faction_id, "slug": "test-guild", "name": "Test Guild",
            "nation_home": "ammeonon", "is_active": True,
        })
        await db.faction_specialties.insert_one({
            "id": str(uuid.uuid4()), "faction_id": faction_id,
            "faction_slug": "test-guild", "good_slug": "iron-ingots",
            "base_cost": 50, "capacity": 40, "description": "test",
        })
        prods = EconomyProducers(db)
        await prods.run_tick(source="test")
        stock = await prods.get_inventory(
            owner_type=OWNER_FACTION, owner_key="test-guild", good_slug="iron-ingots",
        )
        assert stock == 40
    _run(_)


# ── trade-company tests ─────────────────────────────────────────

async def _mk_user_with_gold(db, gold=10000):
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid, "username": f"u_{uid[:6]}", "email": f"{uid[:6]}@t",
        "currency": gold, "status": "active", "role": "member",
    })
    return await db.users.find_one({"id": uid}, {"_id": 0})


async def _mk_char(db, user_id, name="Aiven"):
    cid = str(uuid.uuid4())
    await db.characters.insert_one({
        "id": cid, "user_id": user_id, "name": name,
        "race": "elf", "character_class": "ranger", "nation": "Ammeonon",
    })
    return await db.characters.find_one({"id": cid}, {"_id": 0})


def test_charter_debits_founder_and_grants_shares():
    async def _(db):
        user = await _mk_user_with_gold(db, gold=5000)
        ch = await _mk_char(db, user["id"])
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=user, founder_character=ch,
            name="Test Co", motto="TT", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        # Founder wallet -2500
        u2 = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        assert u2["currency"] == 5000 - CHARTER_FEE
        # Treasury has fee
        assert co["treasury"] == CHARTER_FEE
        # Founder holds CHARTER_FEE / SHARE_PRICE shares
        holders = await svc.list_shareholders(co["id"])
        assert len(holders) == 1
        assert holders[0]["shares"] == CHARTER_FEE // SHARE_PRICE
    _run(_)


def test_charter_rejects_when_broke():
    async def _(db):
        user = await _mk_user_with_gold(db, gold=100)
        ch = await _mk_char(db, user["id"])
        svc = TradeCompanyService(db)
        try:
            await svc.charter(
                founder_user=user, founder_character=ch,
                name="Broke Co", motto="", home_nation="ammeonon",
                sigil="coins", color="#f59e0b",
            )
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "need" in str(e).lower() or "charter" in str(e).lower()
    _run(_)


def test_route_run_updates_treasury_and_stock():
    async def _(db):
        # Seed goods so buy/sell math works
        await db.goods.insert_one({
            "slug": "grain", "name": "Grain", "category": "food",
            "unit": "per bushel", "default_base_cost": 4, "is_service": False, "tags": ["food"],
        })
        prods = EconomyProducers(db)
        await prods.seed_city_producers()
        await prods.run_tick(source="test")

        user = await _mk_user_with_gold(db, gold=10000)
        ch = await _mk_char(db, user["id"])
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=user, founder_character=ch,
            name="Grain Co", motto="", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        await svc.add_route(
            company_id=co["id"], user_id=user["id"],
            source_nation="ammeonon", source_city_slug="duncroft",
            dest_nation="ammeonon", dest_city_slug="wymroost",
            good_slug="grain", units_per_run=20,
        )
        stock_before = await prods.get_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft", good_slug="grain",
        )
        summary = await run_trade_ticks(db, tick_id="t1", tick_at="2026-01-01T00:00:00Z")
        assert summary["routes_completed"] == 1
        assert summary["total_profit"] > 0
        stock_after = await prods.get_inventory(
            owner_type=OWNER_CITY, owner_key="ammeonon:duncroft", good_slug="grain",
        )
        assert stock_after == stock_before - 20
        co2 = await svc.get_company(co["id"])
        assert co2["treasury"] > CHARTER_FEE
        assert co2["period_revenue"] > 0
        assert co2["period_costs"] > 0
    _run(_)


def test_route_skips_when_source_has_no_stock():
    async def _(db):
        await db.goods.insert_one({
            "slug": "grain", "name": "Grain", "category": "food",
            "unit": "per bushel", "default_base_cost": 4, "is_service": False, "tags": ["food"],
        })
        user = await _mk_user_with_gold(db, gold=10000)
        ch = await _mk_char(db, user["id"])
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=user, founder_character=ch,
            name="Empty Route Co", motto="", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        # No producers seeded, no stock exists
        await svc.add_route(
            company_id=co["id"], user_id=user["id"],
            source_nation="ammeonon", source_city_slug="duncroft",
            dest_nation="ammeonon", dest_city_slug="wymroost",
            good_slug="grain", units_per_run=20,
        )
        summary = await run_trade_ticks(db, tick_id="t2", tick_at="2026-01-01T00:00:00Z")
        assert summary["routes_completed"] == 0
        assert summary["routes_failed"] == 1
        # Treasury unchanged
        co2 = await svc.get_company(co["id"])
        assert co2["treasury"] == CHARTER_FEE
    _run(_)


def test_invest_grants_shares_and_credits_treasury():
    async def _(db):
        founder = await _mk_user_with_gold(db, gold=5000)
        founder_ch = await _mk_char(db, founder["id"])
        investor = await _mk_user_with_gold(db, gold=2000)
        investor_ch = await _mk_char(db, investor["id"], name="Bel")
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=founder, founder_character=founder_ch,
            name="Invest Co", motto="", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        await svc.invest(
            company_id=co["id"], user_id=investor["id"],
            character_id=investor_ch["id"], gold=500,
        )
        co2 = await svc.get_company(co["id"])
        assert co2["treasury"] == CHARTER_FEE + 500
        holders = await svc.list_shareholders(co["id"])
        assert len(holders) == 2
        inv_row = next(h for h in holders if h["user_id"] == investor["id"])
        assert inv_row["shares"] == 500 // SHARE_PRICE
        u2 = await db.users.find_one({"id": investor["id"]}, {"_id": 0})
        assert u2["currency"] == 1500
    _run(_)


def test_dissolve_refunds_proportionally():
    async def _(db):
        founder = await _mk_user_with_gold(db, gold=5000)
        founder_ch = await _mk_char(db, founder["id"])
        investor = await _mk_user_with_gold(db, gold=2000)
        investor_ch = await _mk_char(db, investor["id"], name="Bel")
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=founder, founder_character=founder_ch,
            name="D Co", motto="", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        await svc.invest(
            company_id=co["id"], user_id=investor["id"],
            character_id=investor_ch["id"], gold=500,
        )
        # Founder has 25 shares, investor has 5 → 25/30 vs 5/30 of a treasury of 3000
        r = await svc.dissolve(company_id=co["id"], user_id=founder["id"])
        assert r["status"] == "dissolved"
        # Founder refund: (25/30)*3000 = 2500
        u_f = await db.users.find_one({"id": founder["id"]}, {"_id": 0})
        assert u_f["currency"] == 5000 - CHARTER_FEE + 2500
        # Investor refund: (5/30)*3000 = 500
        u_i = await db.users.find_one({"id": investor["id"]}, {"_id": 0})
        assert u_i["currency"] == 2000 - 500 + 500  # net-neutral, gets it back
    _run(_)


def test_non_founder_cannot_add_route_or_dissolve():
    async def _(db):
        founder = await _mk_user_with_gold(db, gold=5000)
        founder_ch = await _mk_char(db, founder["id"])
        other = await _mk_user_with_gold(db, gold=5000)
        svc = TradeCompanyService(db)
        co = await svc.charter(
            founder_user=founder, founder_character=founder_ch,
            name="Sole Co", motto="", home_nation="ammeonon",
            sigil="coins", color="#f59e0b",
        )
        await db.goods.insert_one({
            "slug": "grain", "name": "Grain", "category": "food",
            "unit": "per bushel", "default_base_cost": 4, "is_service": False, "tags": [],
        })
        try:
            await svc.add_route(
                company_id=co["id"], user_id=other["id"],
                source_nation="ammeonon", source_city_slug="duncroft",
                dest_nation="ammeonon", dest_city_slug="wymroost",
                good_slug="grain", units_per_run=20,
            )
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "founder" in str(e).lower()
        try:
            await svc.dissolve(company_id=co["id"], user_id=other["id"])
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "founder" in str(e).lower()
    _run(_)
