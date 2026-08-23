"""NPC economy — trade rivals + walk-in shop customers.

Two independent lore-driven layers on top of the existing player economy:

    1. NPC Trade Rivals
       — canonical lore houses (e.g. "The Amber Consortium", "House
         Vardis of Duncroft") seeded as `is_npc=True` trade_companies
         with 2-4 pre-configured routes each. The existing 6h tick
         engine treats them identically to player companies: routes
         draw from city stockpiles, treasuries grow, no dividends.
       — surfaces in `/trade-companies` alongside real players so the
         board never feels empty.

    2. NPC Walk-in Customers
       — every 6h tick, each active player shop attracts 2-5 NPC
         customers. Each picks an in-stock item they can plausibly
         afford, buys ONE unit, and the shop owner is credited. A
         transaction row is appended with `buyer_type='npc'` and a
         randomised lore-flavoured name. Shop owners can see the
         feed via `GET /api/shops/{id}/customers`.
"""
from __future__ import annotations

import logging
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── NPC trade-rivals seed ────────────────────────────────────────
# (nation, name, motto, sigil, color, routes[(src_city, dst_city, good, units)])
NPC_TRADE_RIVALS: List[Dict] = [
    # Ammeonon — human trade heartland
    {
        "nation": "ammeonon",
        "name": "The Amber Consortium",
        "motto": "Salt, silk, and safe harbour.",
        "sigil": "anchor",
        "color": "#d97706",
        "founder": "Master Merchant Iselwyn Amber",
        "routes": [
            ("ammeonon", "amberport", "ammeonon", "wymroost", "salted-fish", 40),
            ("ammeonon", "wymroost", "ammeonon", "duncroft", "silken-cloth", 15),
        ],
    },
    {
        "nation": "ammeonon",
        "name": "House Vardis of Duncroft",
        "motto": "From the fields, all wealth flows.",
        "sigil": "wagon",
        "color": "#a16207",
        "founder": "Baron Halvar Vardis",
        "routes": [
            ("ammeonon", "duncroft", "ammeonon", "wymroost", "grain", 60),
            ("ammeonon", "duncroft", "ammeonon", "invrasil", "wool-bolts", 25),
            ("ammeonon", "duncroft", "ammeonon", "hielgcrom-old-town", "hard-tack", 30),
        ],
    },
    # Dhor-Kuldor — dwarven metal-trade
    {
        "nation": "dhor-kuldor",
        "name": "Steelvein & Sons",
        "motto": "Iron in the blood, gold in the ledger.",
        "sigil": "hammer",
        "color": "#71717a",
        "founder": "Guildmaster Thorick Steelvein",
        "routes": [
            ("dhor-kuldor", "irondeep", "dhor-kuldor", "emberhold", "iron-ore", 100),
            ("dhor-kuldor", "emberhold", "ammeonon", "wymroost", "iron-swords", 15),
        ],
    },
    {
        "nation": "dhor-kuldor",
        "name": "The Ancestor-Mint Cartel",
        "motto": "Struck true, struck for the crown.",
        "sigil": "crown",
        "color": "#facc15",
        "founder": "Highmint Durgan Karrak",
        "routes": [
            ("dhor-kuldor", "ancestor-hall", "ammeonon", "wymroost", "silver-bullion", 8),
            ("dhor-kuldor", "ancestor-hall", "selindori", "aurelion-spires", "fine-jewelry", 4),
        ],
    },
    # Selindori — elven prestige-trade
    {
        "nation": "selindori",
        "name": "Aurelion Silks & Sun-Stones",
        "motto": "Only the light knows our price.",
        "sigil": "sun",
        "color": "#fbbf24",
        "founder": "Ambassador Lythien Aureol",
        "routes": [
            ("selindori", "aurelion-spires", "ammeonon", "wymroost", "silken-cloth", 12),
            ("selindori", "aurelion-spires", "dhor-kuldor", "ancestor-hall", "arcane-reagents", 10),
        ],
    },
    {
        "nation": "selindori",
        "name": "Thalenroot Herb-Circle",
        "motto": "What the wood gives, it may take back.",
        "sigil": "feather",
        "color": "#059669",
        "founder": "Circle-Speaker Nelori Thal",
        "routes": [
            ("selindori", "thalenroot", "aigraels", "astra-lun", "mountain-herbs", 40),
            ("selindori", "thalenroot", "ammeonon", "invrasil", "healing-service", 10),
        ],
    },
    # Aigraels — contested triumvirate
    {
        "nation": "aigraels",
        "name": "The Ironhold Legion Supply",
        "motto": "Every legion eats before it marches.",
        "sigil": "shield",
        "color": "#b91c1c",
        "founder": "Quartermaster-Ardent Kestrel Vane",
        "routes": [
            ("aigraels", "ironhold", "ammeonon", "duncroft", "iron-swords", 12),
            ("aigraels", "ironhold", "dhor-kuldor", "emberhold", "tanned-leather", 20),
        ],
    },
    {
        "nation": "aigraels",
        "name": "House Noctyss Wine & Coin",
        "motto": "A bottle at every table, a coin at every hand.",
        "sigil": "moon",
        "color": "#7c3aed",
        "founder": "Marquessa Aleide Noctyss",
        "routes": [
            ("aigraels", "noctyss-vale", "ammeonon", "wymroost", "spiced-wine", 10),
            ("aigraels", "noctyss-vale", "selindori", "aurelion-spires", "arcane-reagents", 8),
        ],
    },
    # Veiled Realms — moon/shadow trade
    {
        "nation": "veiled-realms",
        "name": "Rakesh Moon-Silver Guild",
        "motto": "Weighed by moonlight, paid by moonlight.",
        "sigil": "moon",
        "color": "#94a3b8",
        "founder": "Silvermistress Selys Rakesh",
        "routes": [
            ("veiled-realms", "rakesh", "selindori", "aurelion-spires", "silver-bullion", 6),
            ("veiled-realms", "rakesh", "ammeonon", "invrasil", "arcane-reagents", 10),
        ],
    },
    {
        "nation": "veiled-realms",
        "name": "Serant-Kresh Memory Cartel",
        "motto": "We remember what the world forgets.",
        "sigil": "gem",
        "color": "#a855f7",
        "founder": "Loremaster Vessyn Kresh",
        "routes": [
            ("veiled-realms", "serant-kresh", "aigraels", "astra-lun", "arcane-reagents", 8),
            ("veiled-realms", "serant-kresh", "selindori", "thalenroot", "fine-jewelry", 4),
        ],
    },
]


# ── NPC customer name generator ──────────────────────────────────

_NPC_TITLES = [
    "Traveller", "Merchant", "Sailor", "Farmhand", "Legionnaire",
    "Pilgrim", "Scribe", "Alewife", "Watchman", "Cartwright",
    "Fisherwife", "Tinker", "Herbalist", "Journeyman", "Novice",
    "Master", "Goodwife", "Freeman", "Sergeant", "Chapman",
]

_NPC_GIVEN = [
    # Ammeonon (human) — Latinate / Blackburn / Nalviem
    "Iselwyn", "Halvar", "Torren", "Mira", "Rhosa", "Cael", "Bel",
    "Wenna", "Alden", "Osric", "Fenwyn", "Mairin", "Corvin", "Ellisa",
    "Torvin", "Nell", "Bram", "Sula", "Perrin", "Vardis",
    # Dhor-Kuldor (dwarven)
    "Thorick", "Durgan", "Balin", "Kova", "Grimwar", "Dagna", "Rurik",
    "Brenna", "Karrak",
    # Selindori (elven) — flowing
    "Lythien", "Nelori", "Aeryss", "Selys", "Vessyn", "Aureol",
    "Faelith", "Isren", "Cyrelith",
    # Aigraels (mixed) — hard consonants
    "Kestrel", "Aleide", "Marek", "Vane",
    # Veiled Realms — soft, silver, veiled
    "Selys", "Umbrel", "Nyra", "Yssen",
]

_NPC_SURNAMES = [
    "Amber", "Vardis", "Steelvein", "Karrak", "Aureol", "Thal",
    "Kresh", "Noctyss", "Rakesh", "Nen", "Ostwyn", "of Duncroft",
    "of Wymroost", "of Amberport", "Ironshod", "Stonehand", "Silvertongue",
    "the Elder", "the Younger", "of the Vale",
]


def _npc_customer_name() -> str:
    return (
        f"{random.choice(_NPC_TITLES)} "
        f"{random.choice(_NPC_GIVEN)} {random.choice(_NPC_SURNAMES)}"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60] or f"npc-{uuid.uuid4().hex[:8]}"


# ── seeding NPC trade rivals ─────────────────────────────────────


async def seed_npc_trade_rivals(db) -> Dict:
    """Idempotent seed of the NPC trade-rivals table. Returns counts.

    NPC companies are created with `is_npc=True`, a synthetic
    `founder_user_id` ("NPC:<slug>"), and their routes are inserted
    once (subsequent runs skip if the company already exists).
    """
    inserted = 0
    skipped = 0
    routes_added = 0

    for rec in NPC_TRADE_RIVALS:
        slug = _slugify(rec["name"])
        existing = await db.trade_companies.find_one({"slug": slug}, {"_id": 0, "id": 1})
        if existing:
            skipped += 1
            continue
        company_id = str(uuid.uuid4())
        now = _now_iso()
        doc = {
            "id": company_id,
            "slug": slug,
            "name": rec["name"],
            "motto": rec["motto"],
            "home_nation": rec["nation"],
            "sigil": rec.get("sigil", "coins"),
            "color": rec.get("color", "#f59e0b"),
            "founder_user_id": f"NPC:{slug}",
            "founder_character_id": f"NPC:{slug}",
            "founder_character_name": rec["founder"],
            "is_npc": True,
            "treasury": 5000,     # NPC houses start with working capital
            "status": "active",
            "created_at": now,
            "dissolved_at": None,
            "period_start": now,
            "next_ledger_at": None,   # NPCs don't run weekly ledgers
            "period_revenue": 0,
            "period_costs": 0,
            "period_dividends_paid": 0,
            "lifetime_revenue": 0,
            "lifetime_costs": 0,
            "lifetime_dividends_paid": 0,
        }
        await db.trade_companies.insert_one(doc)
        # Also add a synthetic shareholder row so the roster panel isn't empty
        await db.trade_company_shareholders.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "user_id": f"NPC:{slug}",
            "character_id": f"NPC:{slug}",
            "shares": 100,
            "invested_gold": 5000,
            "joined_at": now,
        })
        # Routes
        for src_nation, src_city, dst_nation, dst_city, good, units in rec["routes"]:
            await db.trade_company_routes.insert_one({
                "id": str(uuid.uuid4()),
                "company_id": company_id,
                "source_nation": src_nation,
                "source_city_slug": src_city,
                "dest_nation": dst_nation,
                "dest_city_slug": dst_city,
                "good_slug": good,
                "units_per_run": units,
                "is_active": True,
                "last_run_at": None,
                "last_run_result": None,
                "runs_total": 0,
                "created_at": now,
            })
            routes_added += 1
        # Charter activity
        await db.trade_company_activity.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "kind": "charter",
            "at": now,
            "meta": {"founder": rec["founder"], "npc": True},
        })
        inserted += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "routes_added": routes_added,
        "total_rivals": len(NPC_TRADE_RIVALS),
    }


# ── NPC walk-in shop customers ───────────────────────────────────


CUSTOMERS_PER_SHOP_MIN = 1
CUSTOMERS_PER_SHOP_MAX = 4
MAX_UNITS_PER_PURCHASE = 2
MAX_ITEM_PRICE_GOLD = 400            # NPCs don't blow the bank on luxury items


async def simulate_npc_customers_for_shops(db) -> Dict:
    """Simulate NPC walk-in customers visiting every active player shop.

    Called from the 6h economy tick. For each shop with at least one
    in-stock item priced ≤ MAX_ITEM_PRICE_GOLD, sample N random NPC
    visitors. Each visitor buys ONE unit of one item, credits the shop
    owner, and appends a `TransactionType.SHOP_SALE` row + a compact
    `shop_customers` entry (used by the shop-owner dashboard feed).
    """
    shops = await db.shops.find({}, {"_id": 0}).to_list(500)
    if not shops:
        return {"shops_visited": 0, "purchases": 0, "gold_moved": 0}

    total_purchases = 0
    total_gold = 0
    shops_visited = 0

    for shop in shops:
        # Skip NPC-owned shops (owner_id starts with NPC:)
        owner_id = shop.get("owner_id", "")
        if owner_id.startswith("NPC:"):
            continue
        # Skip cult-cursed shops (no NPC walk-ins for 3 world days)
        try:
            from cults_service import CultService
            if await CultService(db).is_shop_cursed(shop["id"]):
                continue
        except Exception:  # pragma: no cover
            pass
        items = await db.items.find(
            {"shop_id": shop["id"], "stock": {"$gt": 0}, "price": {"$lte": MAX_ITEM_PRICE_GOLD}},
            {"_id": 0},
        ).to_list(200)
        if not items:
            continue

        visitors = random.randint(CUSTOMERS_PER_SHOP_MIN, CUSTOMERS_PER_SHOP_MAX)
        purchased_this_shop = 0
        gold_this_shop = 0

        for _ in range(visitors):
            # Re-check items each iteration since stock drops
            available = [i for i in items if i["stock"] > 0]
            if not available:
                break
            item = random.choice(available)
            units = min(item["stock"], random.randint(1, MAX_UNITS_PER_PURCHASE))
            price_total = int(item["price"]) * units
            customer_name = _npc_customer_name()

            # Decrement stock in-memory + in DB
            new_stock = int(item["stock"]) - units
            await db.items.update_one(
                {"id": item["id"]}, {"$set": {"stock": new_stock}},
            )
            item["stock"] = new_stock
            # Low-stock alert for the owner when a walk-in clears the shelf.
            if new_stock <= 0:
                await _emit_out_of_stock_alert(db, shop["id"], item["id"], item["name"])

            # Credit shop owner
            await db.users.update_one(
                {"id": shop["owner_id"]},
                {"$inc": {"currency": price_total}},
            )

            # Transaction record — mirrors the schema `Transaction` uses
            await db.transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": shop["owner_id"],
                "amount": price_total,
                "transaction_type": "shop_sale",
                "description": f"{customer_name} bought {units}× {item['name']} at your shop.",
                "related_id": item["id"],
                "created_at": _now_iso(),
                "buyer_type": "npc",
                "buyer_name": customer_name,
            })
            # Compact per-shop feed
            await db.shop_customers.insert_one({
                "id": str(uuid.uuid4()),
                "shop_id": shop["id"],
                "customer_name": customer_name,
                "item_id": item["id"],
                "item_name": item["name"],
                "units": units,
                "price_total": price_total,
                "at": _now_iso(),
            })

            purchased_this_shop += 1
            gold_this_shop += price_total

        if purchased_this_shop > 0:
            shops_visited += 1
            total_purchases += purchased_this_shop
            total_gold += gold_this_shop

    return {
        "shops_visited": shops_visited,
        "purchases": total_purchases,
        "gold_moved": total_gold,
    }


async def recent_shop_customers(db, shop_id: str, limit: int = 30) -> List[Dict]:
    """Feed of recent NPC customers for a shop owner's dashboard."""
    return await db.shop_customers.find(
        {"shop_id": shop_id}, {"_id": 0},
    ).sort("at", -1).limit(max(1, min(200, limit))).to_list(limit)



# ── Auto-restock player shops ────────────────────────────────────

RESTOCK_COST_PCT = 20  # owners pay 20% of item price per unit refilled


async def _emit_out_of_stock_alert(db, shop_id: str, item_id: str, item_name: str) -> None:
    """Record an in-app 'sold out' alert for the shop owner. De-duplicated:
    won't stack another unseen alert for the same item."""
    existing = await db.shop_alerts.find_one(
        {"item_id": item_id, "type": "out_of_stock", "seen": False}, {"_id": 0, "id": 1},
    )
    if existing:
        return
    await db.shop_alerts.insert_one({
        "id": str(uuid.uuid4()),
        "shop_id": shop_id,
        "item_id": item_id,
        "item_name": item_name,
        "type": "out_of_stock",
        "seen": False,
        "created_at": _now_iso(),
    })


async def restock_player_shops(db) -> Dict:
    """Auto-restock: top every opted-in item back up to its `restock_target`,
    charging the owner a wholesale fee (20% of price per unit). If the owner
    can't afford the full refill this cycle, the item is left as-is (no debt).

    Called from the same 6h economy tick as NPC walk-in customers, AFTER them,
    so an owner always finds their shelves refilled between cycles.
    """
    now = _now_iso()
    topped = 0
    gold_spent = 0
    skipped_unaffordable = 0
    shop_owner: Dict[str, str] = {}
    cur = db.items.find(
        {"auto_restock": True},
        {"_id": 0, "id": 1, "name": 1, "stock": 1, "restock_target": 1, "price": 1, "shop_id": 1},
    )
    async for it in cur:
        try:
            target = int(it.get("restock_target"))
        except (TypeError, ValueError):
            continue
        if target <= 0:
            continue
        stock = int(it.get("stock", 0))
        if stock >= target:
            continue
        units = target - stock
        price = int(it.get("price", 0) or 0)
        # ceil(price * 20%) per unit, without float rounding surprises.
        fee = ((price * RESTOCK_COST_PCT + 99) // 100) * units
        shop_id = it.get("shop_id")

        owner_id = shop_owner.get(shop_id)
        if owner_id is None:
            shop = await db.shops.find_one({"id": shop_id}, {"_id": 0, "owner_id": 1})
            owner_id = (shop or {}).get("owner_id") or ""
            shop_owner[shop_id] = owner_id

        # NPC-owned shops (or ownerless) refill free — nobody to bill.
        if not owner_id or owner_id.startswith("NPC:"):
            await db.items.update_one(
                {"id": it["id"]}, {"$set": {"stock": target, "last_restocked_at": now}},
            )
            topped += 1
            continue

        if fee > 0:
            owner = await db.users.find_one({"id": owner_id}, {"_id": 0, "currency": 1})
            if not owner or int(owner.get("currency", 0)) < fee:
                skipped_unaffordable += 1
                continue
            await db.users.update_one({"id": owner_id}, {"$inc": {"currency": -fee}})
            await db.transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": owner_id,
                "amount": -fee,
                "transaction_type": "shop_restock",
                "description": f"Auto-restocked {units}× {it.get('name', 'item')} (wholesale).",
                "related_id": it["id"],
                "created_at": now,
            })
            gold_spent += fee

        await db.items.update_one(
            {"id": it["id"]}, {"$set": {"stock": target, "last_restocked_at": now}},
        )
        topped += 1

    return {
        "items_restocked": topped,
        "gold_spent": gold_spent,
        "skipped_unaffordable": skipped_unaffordable,
    }
