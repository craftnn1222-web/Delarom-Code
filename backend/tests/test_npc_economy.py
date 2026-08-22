"""NPC economy tests — trade rivals seeding + shop-customer simulation."""
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

from npc_economy import (  # noqa: E402
    NPC_TRADE_RIVALS,
    seed_npc_trade_rivals,
    simulate_npc_customers_for_shops,
    recent_shop_customers,
)


def _run(async_fn):
    async def _outer():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        dbname = f"npc_test_{uuid.uuid4().hex[:8]}"
        db = client[dbname]
        try:
            return await async_fn(db)
        finally:
            await client.drop_database(dbname)
            client.close()
    asyncio.run(_outer())


# ── NPC trade rivals ────────────────────────────────────────────

def test_seed_npc_rivals_is_idempotent():
    async def _(db):
        first = await seed_npc_trade_rivals(db)
        assert first["inserted"] == len(NPC_TRADE_RIVALS)
        assert first["routes_added"] > 0
        second = await seed_npc_trade_rivals(db)
        assert second["inserted"] == 0
        assert second["skipped"] == len(NPC_TRADE_RIVALS)
        # NPC companies are correctly flagged
        n = await db.trade_companies.count_documents({"is_npc": True})
        assert n == len(NPC_TRADE_RIVALS)
        # Every NPC has at least one route
        for c in await db.trade_companies.find({"is_npc": True}, {"_id": 0, "id": 1}).to_list(50):
            rc = await db.trade_company_routes.count_documents({"company_id": c["id"]})
            assert rc >= 1
    _run(_)


def test_npc_rivals_cover_all_realms():
    async def _(db):
        await seed_npc_trade_rivals(db)
        realms = await db.trade_companies.distinct("home_nation", {"is_npc": True})
        for expected in ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]:
            assert expected in realms, f"No NPC rival in {expected}"
    _run(_)


# ── NPC walk-in customers ───────────────────────────────────────


async def _mk_shop_with_item(db, price=50, stock=10):
    owner_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": owner_id, "username": f"u_{owner_id[:6]}",
        "currency": 0, "status": "active", "role": "member",
    })
    shop_id = str(uuid.uuid4())
    await db.shops.insert_one({
        "id": shop_id, "owner_id": owner_id, "owner_username": "u",
        "name": "Test Shop", "description": "test", "nation": "Ammeonon",
    })
    item_id = str(uuid.uuid4())
    await db.items.insert_one({
        "id": item_id, "shop_id": shop_id, "name": "Bread Loaf",
        "description": "d", "price": price, "stock": stock,
        "item_type": "consumable", "equipment_slot": None,
    })
    return owner_id, shop_id, item_id


def test_simulate_npc_customers_credits_owner_and_decrements_stock():
    async def _(db):
        owner_id, shop_id, item_id = await _mk_shop_with_item(db, price=50, stock=10)
        # Run the sim a few times to smooth out RNG
        agg_gold = 0
        for _i in range(5):
            r = await simulate_npc_customers_for_shops(db)
            agg_gold += r["gold_moved"]
        # Owner currency matches total gold moved
        user = await db.users.find_one({"id": owner_id}, {"_id": 0})
        assert user["currency"] == agg_gold > 0
        # Item stock dropped by number of purchases (from shop_customers table)
        purchases = await db.shop_customers.find({"shop_id": shop_id}, {"_id": 0}).to_list(200)
        units_bought = sum(p["units"] for p in purchases)
        item = await db.items.find_one({"id": item_id}, {"_id": 0})
        assert item["stock"] == max(0, 10 - units_bought)
        # transactions have buyer_type='npc'
        for t in await db.transactions.find({"user_id": owner_id}, {"_id": 0}).to_list(200):
            assert t.get("buyer_type") == "npc"
            assert t.get("buyer_name")
    _run(_)


def test_simulate_skips_shops_with_no_stock():
    async def _(db):
        owner_id, shop_id, item_id = await _mk_shop_with_item(db, price=50, stock=0)
        r = await simulate_npc_customers_for_shops(db)
        assert r["shops_visited"] == 0
        assert r["purchases"] == 0
    _run(_)


def test_simulate_skips_luxury_items():
    async def _(db):
        # price above MAX_ITEM_PRICE_GOLD (400) — should be skipped
        owner_id, shop_id, item_id = await _mk_shop_with_item(db, price=1000, stock=10)
        r = await simulate_npc_customers_for_shops(db)
        assert r["purchases"] == 0
        user = await db.users.find_one({"id": owner_id}, {"_id": 0})
        assert user["currency"] == 0
    _run(_)


def test_simulate_skips_npc_owned_shops():
    async def _(db):
        # A shop owned by NPC:foo should NOT be visited (NPCs don't buy from NPCs)
        await db.users.insert_one({
            "id": "NPC:npc-shopkeeper", "username": "npc",
            "currency": 0, "status": "active", "role": "member",
        })
        shop_id = str(uuid.uuid4())
        await db.shops.insert_one({
            "id": shop_id, "owner_id": "NPC:npc-shopkeeper",
            "owner_username": "npc-shopkeeper",
            "name": "NPC Shop", "description": "d", "nation": "Ammeonon",
        })
        item_id = str(uuid.uuid4())
        await db.items.insert_one({
            "id": item_id, "shop_id": shop_id, "name": "Trinket",
            "description": "d", "price": 20, "stock": 50,
            "item_type": "consumable", "equipment_slot": None,
        })
        r = await simulate_npc_customers_for_shops(db)
        assert r["shops_visited"] == 0
    _run(_)


def test_recent_shop_customers_returns_desc_order():
    async def _(db):
        owner_id, shop_id, item_id = await _mk_shop_with_item(db, price=25, stock=50)
        # Populate a few purchases
        for _ in range(3):
            await simulate_npc_customers_for_shops(db)
        rows = await recent_shop_customers(db, shop_id, limit=100)
        assert len(rows) > 0
        # Sorted descending by 'at'
        ats = [r["at"] for r in rows]
        assert ats == sorted(ats, reverse=True)
    _run(_)
