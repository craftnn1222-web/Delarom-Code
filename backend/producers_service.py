"""Real Delarom producers — city + faction production ticks.

Backfills the missing "actual production" half of the economy. Previously
we had prices and contracts but nothing was actually being *made*. This
module introduces:

    • city_producers    — every canonical city declares 1-3 goods it
                          natively produces, with a per-tick output rate
                          and a warehouse cap.
    • producer_inventory
                        — persistent stockpiles keyed by (owner_type,
                          owner_key, good_slug). Owners are cities or
                          factions. Trade companies and caravans draw
                          from here; shops don't yet, but the plumbing
                          is in place.
    • economy_state     — singleton doc tracking last tick timestamps.
    • production_tick_log
                        — one row per tick with summary counts.

Tick cadence
------------
The user's spec is "every 6 in-world hours". In Delarom the world clock
is a pure derivation from real UTC (see `world_clock_service.py`) so
"6 in-world hours" is exactly 6 real UTC hours. `maybe_run_tick()`
compares `economy_state.last_tick_at` against `now - 6h` and only
runs if due. `run_tick(force=True)` is the admin escape hatch.

Idempotency
-----------
Seeding is a full upsert on (nation, city_slug, good_slug). Reseeding
never duplicates a producer; it will overwrite units_per_tick /
warehouse_cap so admins can rebalance. Faction specialties are treated
as their own producers implicitly — when a tick runs, each active
faction specialty adds `capacity` units to the faction's inventory
under owner_type="faction".
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


TICK_HOURS = 6                # canonical cadence
DEFAULT_WAREHOUSE_CAP = 500   # units — prevents runaway hoarding
OWNER_CITY = "city"
OWNER_FACTION = "faction"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Motor returns strings with 'Z' or offset — handle both
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Canonical hand-authored seed ─────────────────────────────────────
# Each entry: (nation, city_slug, good_slug, units_per_tick, warehouse_cap, description)
# Cities are drawn from the Tier-1 FULL canon (see seed_all_realms_canon.py).
# Goods are drawn from starter_economy.CANONICAL_GOODS.
CITY_PRODUCERS_SEED: List[Tuple[str, str, str, int, int, str]] = [
    # ── Ammeonon (human heartland) ─────────────────────────────
    ("ammeonon", "wymroost",           "silken-cloth",    12, 200, "Wymroost's dye-houses spin fine silks for the Empress's court."),
    ("ammeonon", "wymroost",           "spiced-wine",     18, 260, "Vintners of the Wymroost hills bottle spiced court reds."),
    ("ammeonon", "wymroost",           "tanned-leather",  22, 300, "The old tanners' quarter along the Wym river."),
    ("ammeonon", "amberport",          "salted-fish",     60, 800, "The salt-flats and fishing fleets of Amberport bay."),
    ("ammeonon", "amberport",          "cured-meats",     14, 220, "Smokehouses along the docks."),
    ("ammeonon", "duncroft",           "grain",           95, 1400, "Duncroft's terraced fields feed half of Ammeonon."),
    ("ammeonon", "duncroft",           "wool-bolts",      26, 340, "Highland sheep and cottage looms."),
    ("ammeonon", "duncroft",           "hard-tack",       30, 400, "Barracks-loaves baked for garrison contracts."),
    ("ammeonon", "invrasil",           "arcane-reagents", 10, 140, "Reagents distilled at the Titan of Wind's mage-halls."),
    ("ammeonon", "invrasil",           "rune-scrolls",     4,  60, "Warded scrolls copied under Invrasil's wind-lamps."),
    ("ammeonon", "invrasil",           "mountain-herbs",  20, 260, "Foraged from the wind-shorn slopes above the city."),
    ("ammeonon", "hielgcrom-old-town", "cured-meats",     10, 160, "The old town's smokehouses run day and night."),
    ("ammeonon", "hielgcrom-old-town", "hard-tack",       26, 380, "Garrison-pattern rations."),

    # ── Dhor-Kuldor (dwarven holds) ───────────────────────────
    ("dhor-kuldor", "irondeep",          "iron-ore",     140, 1800, "Irondeep's clan-veins run miles beneath the Kuldor peaks."),
    ("dhor-kuldor", "irondeep",          "iron-ingots",   55,  620, "Smelters in the Under-town churn ingots by the score."),
    ("dhor-kuldor", "gloomstone",        "iron-ore",      80, 1100, "The Gloomstone shafts, deep and lightless."),
    ("dhor-kuldor", "gloomstone",        "uncut-gems",     5,   80, "Rough gems chipped from the deep seams."),
    ("dhor-kuldor", "stonehaven",        "stone-blocks",  70, 1000, "The great quarries above Stonehaven Hold."),
    ("dhor-kuldor", "stonehaven",        "stonework",     10,  140, "Master stone-carvers of Stonehearth Hold."),
    ("dhor-kuldor", "emberhold",         "steel-ingots",  36,  460, "Emberhold's blast-forges — the finest steel in the realm."),
    ("dhor-kuldor", "emberhold",         "iron-swords",   16,  220, "Guild-marked infantry blades."),
    ("dhor-kuldor", "magmathal",         "iron-ingots",   45,  520, "Magmathal's lava-heated ingot-lines."),
    ("dhor-kuldor", "magmathal",         "steel-ingots",  18,  240, "Under-city crucibles."),
    ("dhor-kuldor", "frosthold",         "cured-meats",   22,  320, "Frostpeak game salted and smoked at height."),
    ("dhor-kuldor", "frosthold",         "iron-swords",    9,  120, "Frostpeak-issued short-swords."),
    ("dhor-kuldor", "icehammer-bastion", "steel-armor",    3,   40, "Fortress-forged plate — the pride of the bastion."),
    ("dhor-kuldor", "icehammer-bastion", "iron-swords",   11,  160, "Long-blades pattern-welded on the ramparts."),
    ("dhor-kuldor", "thal-karrak",       "stonework",      8,  120, "Tomb-quarter carvings and reliquary work."),
    ("dhor-kuldor", "thal-karrak",       "fine-jewelry",   5,   80, "Consecrated pieces for the Rite of Y'ros."),
    ("dhor-kuldor", "ancestor-hall",     "gold-bullion",   2,   40, "The High King's mint — crown-stamped bullion."),
    ("dhor-kuldor", "ancestor-hall",     "silver-bullion", 9,  160, "Royal silver, taxation-grade."),
    ("dhor-kuldor", "ancestor-hall",     "fine-jewelry",   4,   70, "Regalia and heirloom pieces for the great families."),

    # ── Selindori (elven realms) ──────────────────────────────
    ("selindori", "aurelion-spires", "arcane-reagents", 16, 220, "Sun-crystal reagents refined in the high spires."),
    ("selindori", "aurelion-spires", "silken-cloth",    16, 220, "Aurelion silks — pale gold, worn only by the court."),
    ("selindori", "aurelion-spires", "fine-jewelry",     6,  90, "Sun-Elf goldsmiths, working the Aurelion motifs."),
    ("selindori", "thalenroot",      "mountain-herbs",  56, 720, "Wood-Elf gatherers of the deep glades."),
    ("selindori", "thalenroot",      "healing-service", 18, 240, "Circle-healers taking house-calls across Selindori."),
    ("selindori", "thalenroot",      "wool-bolts",      22, 300, "Understory sheep and low-loom weaves."),
    ("selindori", "nal-theris",      "salted-fish",     74, 980, "Tide-Elf fisheries along the reef-shores."),
    ("selindori", "nal-theris",      "uncut-gems",       5,  80, "Pearls and reef-gems from the shallows."),
    ("selindori", "nal-theris",      "silken-cloth",    11, 160, "Sea-silks dyed with tide-mordants."),
    ("selindori", "isenfell",        "stone-blocks",    58, 780, "Mountain-Elf quarries in the crag-passes."),
    ("selindori", "isenfell",        "stonework",        8, 120, "Stone-singers of Isenfell."),
    ("selindori", "aer-cyr",         "arcane-reagents",  8, 120, "Sky-realm reagents wind-caught in the eyries."),
    ("selindori", "aer-cyr",         "rune-scrolls",     3,  50, "Eyrie-scribes' wind-warded scrolls."),

    # ── Aigraels (contested triumvirate) ──────────────────────
    ("aigraels", "ironhold",     "steel-armor",     4,  60, "Ardent Legion pattern-plate."),
    ("aigraels", "ironhold",     "iron-swords",    20, 280, "Legion-issue short-swords."),
    ("aigraels", "ironhold",     "tanned-leather", 28, 360, "Banner-leather in Legion colours."),
    ("aigraels", "noctyss-vale", "arcane-reagents", 9, 140, "Forsaken Court alchemy — provenance unclear."),
    ("aigraels", "noctyss-vale", "spiced-wine",    11, 160, "Old-noble vintages smuggled through the vale."),
    ("aigraels", "noctyss-vale", "uncut-gems",      4,  60, "Salvaged gemstones from sacked estates."),
    ("aigraels", "astra-lun",    "healing-service",26, 340, "Elderborn druids and old-blood healers."),
    ("aigraels", "astra-lun",    "mountain-herbs", 36, 480, "Sacred-grove reagents, hand-foraged."),
    ("aigraels", "astra-lun",    "scribing-service",14, 200, "Elderborn scribes preserving old lore."),
    ("aigraels", "vargath",      "mountain-herbs", 18, 240, "Vargath weeds — bitter, potent, contested."),
    ("aigraels", "vargath",      "tanned-leather", 13, 180, "Rough tanning-yards under a Titan-tainted sky."),

    # ── Veiled Realms (elven shadow-schools) ──────────────────
    ("veiled-realms", "rakesh",        "silver-bullion", 7, 100, "Moon-Elf lunomantic silverwork."),
    ("veiled-realms", "rakesh",        "arcane-reagents",11, 160, "Rakesh reagents drawn under moonlight."),
    ("veiled-realms", "yaksha-shi",    "silken-cloth",    9, 140, "Shadow-Elf umbrasilks — jet, indigo, void-black."),
    ("veiled-realms", "yaksha-shi",    "uncut-gems",      4,  70, "Umbral gems — cut only in absolute dark."),
    ("veiled-realms", "yaksha-shi",    "rune-scrolls",    2,  40, "Shadow-inked wardings."),
    ("veiled-realms", "serant-kresh",  "fine-jewelry",    6, 100, "Crystal-Elf memory-work in gold and star-quartz."),
    ("veiled-realms", "serant-kresh",  "arcane-reagents", 9, 140, "Memory-binding reagents."),
    ("veiled-realms", "serant-kresh",  "silken-cloth",    7, 120, "Crystal-Elf cloths woven with silver thread."),
]


class EconomyProducers:
    """Producer + inventory + tick engine."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # ── seed ─────────────────────────────────────────────────

    async def seed_city_producers(self) -> Dict:
        """Idempotent upsert of every canonical (city, good) tuple in
        `CITY_PRODUCERS_SEED`. Returns how many were inserted vs updated."""
        inserted = 0
        updated = 0
        for nation, city_slug, good_slug, per_tick, cap, desc in CITY_PRODUCERS_SEED:
            payload = {
                "nation": nation,
                "city_slug": city_slug,
                "good_slug": good_slug,
                "units_per_tick": int(per_tick),
                "warehouse_cap": int(cap),
                "description": desc,
                "is_active": True,
                "source": "seed",
                "updated_at": _now_iso(),
            }
            existing = await self.db.city_producers.find_one(
                {"nation": nation, "city_slug": city_slug, "good_slug": good_slug},
                {"_id": 0, "id": 1},
            )
            if existing:
                await self.db.city_producers.update_one(
                    {"id": existing["id"]},
                    {"$set": payload},
                )
                updated += 1
            else:
                await self.db.city_producers.insert_one({
                    "id": str(uuid.uuid4()),
                    "created_at": _now_iso(),
                    **payload,
                })
                inserted += 1
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}

    # ── inventory helpers ────────────────────────────────────

    async def get_inventory(
        self, *, owner_type: str, owner_key: str, good_slug: str,
    ) -> int:
        row = await self.db.producer_inventory.find_one(
            {"owner_type": owner_type, "owner_key": owner_key, "good_slug": good_slug},
            {"_id": 0, "units": 1},
        )
        return int(row["units"]) if row and row.get("units") is not None else 0

    async def _add_to_inventory(
        self,
        *,
        owner_type: str,
        owner_key: str,
        nation: str,
        good_slug: str,
        delta: int,
        cap: Optional[int] = None,
    ) -> int:
        """Add (or subtract via negative delta) units to a stockpile.
        Returns the resulting stock. If `cap` is provided, clamps the
        result at `cap`. Never lets stock go negative."""
        current = await self.get_inventory(
            owner_type=owner_type, owner_key=owner_key, good_slug=good_slug,
        )
        new_units = max(0, current + int(delta))
        if cap is not None and cap > 0:
            new_units = min(new_units, int(cap))
        payload = {
            "owner_type": owner_type,
            "owner_key": owner_key,
            "nation": nation,
            "good_slug": good_slug,
            "units": new_units,
            "updated_at": _now_iso(),
        }
        existing = await self.db.producer_inventory.find_one(
            {"owner_type": owner_type, "owner_key": owner_key, "good_slug": good_slug},
            {"_id": 0, "id": 1},
        )
        if existing:
            await self.db.producer_inventory.update_one(
                {"id": existing["id"]},
                {"$set": payload},
            )
        else:
            await self.db.producer_inventory.insert_one({
                "id": str(uuid.uuid4()),
                **payload,
            })
        return new_units

    async def draw_from_inventory(
        self,
        *,
        owner_type: str,
        owner_key: str,
        nation: str,
        good_slug: str,
        units: int,
    ) -> bool:
        """Try to draw `units` from a stockpile. Returns True on success,
        False if there wasn't enough stock. Atomic-ish: only writes if the
        precondition holds."""
        if units <= 0:
            return True
        current = await self.get_inventory(
            owner_type=owner_type, owner_key=owner_key, good_slug=good_slug,
        )
        if current < units:
            return False
        await self._add_to_inventory(
            owner_type=owner_type, owner_key=owner_key,
            nation=nation, good_slug=good_slug, delta=-units,
        )
        return True

    async def get_city_stock(self, nation: str, city_slug: str) -> List[Dict]:
        """List every good and its current stock for a city."""
        rows = await self.db.producer_inventory.find(
            {"owner_type": OWNER_CITY, "owner_key": f"{nation}:{city_slug}"},
            {"_id": 0},
        ).to_list(200)
        return rows

    async def list_city_producers(self, nation: str, city_slug: str) -> List[Dict]:
        return await self.db.city_producers.find(
            {"nation": nation, "city_slug": city_slug}, {"_id": 0},
        ).sort("good_slug", 1).to_list(50)

    # ── ticks ────────────────────────────────────────────────

    async def _get_state(self) -> Dict:
        state = await self.db.economy_state.find_one({"key": "singleton"}, {"_id": 0})
        if not state:
            state = {
                "key": "singleton",
                "last_tick_at": None,
                "tick_hours": TICK_HOURS,
                "tick_count": 0,
                "created_at": _now_iso(),
            }
            await self.db.economy_state.insert_one(state)
        return state

    async def _due_for_tick(self) -> bool:
        state = await self._get_state()
        last = _parse_iso(state.get("last_tick_at") or "")
        if last is None:
            return True
        threshold = _now() - timedelta(hours=int(state.get("tick_hours") or TICK_HOURS))
        return last <= threshold

    async def maybe_run_tick(self) -> Optional[Dict]:
        """Fire a production tick if 6h have passed since the last one.
        Safe to call from request handlers — returns None if not due."""
        if not await self._due_for_tick():
            return None
        return await self.run_tick(source="auto")

    async def run_tick(self, *, source: str = "manual") -> Dict:
        """Force a production tick. Called by the admin endpoint or by
        maybe_run_tick(). Runs every active producer + folds faction
        specialties into faction inventory."""
        tick_id = str(uuid.uuid4())
        tick_at = _now_iso()
        producers_run = 0
        units_produced = 0

        # City producers → city inventory
        # Check cult "drain-city" effects: halve output for cursed cities.
        drained_cities: set = set()
        try:
            from cults_service import CultService
            cults = CultService(self.db)
            async for eff in self.db.cult_effects.find(
                {"effect": "city_production_halved_3d", "ends_at": {"$gt": tick_at}},
                {"_id": 0, "target_ref": 1},
            ):
                drained_cities.add((eff.get("target_ref") or "").lower())
        except Exception:  # pragma: no cover
            pass

        async for p in self.db.city_producers.find(
            {"is_active": True}, {"_id": 0},
        ):
            per = int(p.get("units_per_tick", 0))
            if per <= 0:
                continue
            # Cult curse halves output
            if (p.get("city_slug") or "").lower() in drained_cities:
                per = per // 2
                if per <= 0:
                    continue
            cap = int(p.get("warehouse_cap", DEFAULT_WAREHOUSE_CAP))
            owner_key = f"{p['nation']}:{p['city_slug']}"
            before = await self.get_inventory(
                owner_type=OWNER_CITY, owner_key=owner_key, good_slug=p["good_slug"],
            )
            after = await self._add_to_inventory(
                owner_type=OWNER_CITY,
                owner_key=owner_key,
                nation=p["nation"],
                good_slug=p["good_slug"],
                delta=per,
                cap=cap,
            )
            producers_run += 1
            units_produced += (after - before)

        # Faction specialties → faction inventory (owner_key = faction_slug)
        async for spec in self.db.faction_specialties.find({}, {"_id": 0}):
            per = int(spec.get("capacity", 0))
            if per <= 0:
                continue
            faction = await self.db.factions.find_one(
                {"slug": spec.get("faction_slug"), "is_active": True},
                {"_id": 0, "slug": 1, "nation_home": 1},
            )
            if not faction:
                continue
            # Warehouse cap = capacity × 6 (rough — factions can hold weeks of stock)
            cap = per * 6
            before = await self.get_inventory(
                owner_type=OWNER_FACTION, owner_key=faction["slug"], good_slug=spec["good_slug"],
            )
            after = await self._add_to_inventory(
                owner_type=OWNER_FACTION,
                owner_key=faction["slug"],
                nation=faction.get("nation_home", ""),
                good_slug=spec["good_slug"],
                delta=per,
                cap=cap,
            )
            producers_run += 1
            units_produced += (after - before)

        # Update state
        await self.db.economy_state.update_one(
            {"key": "singleton"},
            {"$set": {"last_tick_at": tick_at, "updated_at": tick_at},
             "$inc": {"tick_count": 1}},
            upsert=True,
        )

        # Log the tick
        summary = {
            "id": tick_id,
            "tick_at": tick_at,
            "source": source,
            "producers_run": producers_run,
            "units_produced": units_produced,
        }
        await self.db.production_tick_log.insert_one(dict(summary))

        # Fire route runs for any active trade companies (deferred import
        # to avoid a hard dependency cycle — trade companies build on top).
        try:
            from trade_companies_service import run_trade_ticks
            trade_summary = await run_trade_ticks(self.db, tick_id=tick_id, tick_at=tick_at)
            summary["trade"] = trade_summary
        except Exception as e:  # pragma: no cover — trade tick is best-effort
            logger.warning(f"Trade tick failed during production tick: {e}")

        # NPC walk-in customers visit every active player shop on the same tick.
        try:
            from npc_economy import simulate_npc_customers_for_shops
            npc_summary = await simulate_npc_customers_for_shops(self.db)
            summary["npc_shop_customers"] = npc_summary
        except Exception as e:  # pragma: no cover — best-effort side-effect
            logger.warning(f"NPC shop-customer simulation failed: {e}")

        return summary

    async def recent_tick_log(self, limit: int = 20) -> List[Dict]:
        return await self.db.production_tick_log.find(
            {}, {"_id": 0},
        ).sort("tick_at", -1).limit(max(1, min(200, limit))).to_list(limit)

    async def get_state(self) -> Dict:
        s = await self._get_state()
        return {
            "last_tick_at": s.get("last_tick_at"),
            "tick_hours": int(s.get("tick_hours") or TICK_HOURS),
            "tick_count": int(s.get("tick_count", 0)),
            "next_due_at": self._next_due_iso(s.get("last_tick_at")),
        }

    @staticmethod
    def _next_due_iso(last_iso: Optional[str]) -> Optional[str]:
        last = _parse_iso(last_iso or "")
        if not last:
            return _now_iso()
        return (last + timedelta(hours=TICK_HOURS)).isoformat()
