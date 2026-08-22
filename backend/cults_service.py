"""Cults & Forbidden Faiths — one-way pacts with real mechanical bite.

Design:
    • Four canonical cults, each with a home lore, a founder-figure,
      and a small set of RITUALS with mechanical effects on other
      players' economies.
    • Joining is one-way in this iteration — no un-cult mechanic. Cost
      on join: -50 Favour with EVERY Elder God (Seren, Yros, Uesis,
      Ehena). This is catastrophic and irrecoverable in the short term.
    • Rituals cost gold + a per-cult cooldown (in world days). Each has
      a real world side-effect:
        - "curse-shop"  → the target shop refuses NPC walk-in customers
                           for 3 world days
        - "drain-city"  → every city producer's output halves for 3
                           world days (all players see it)
        - "unseen-hand" → the caster's next 2 RP actions cannot generate
                           new crimes (witnesses "look away")
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


CULTS = [
    {
        "slug": "forsaken-court",
        "name": "The Forsaken Court",
        "seat": "Noctyss Vale, Aigraels",
        "founder": "The Empress-in-Grief",
        "lore": (
            "A necromantic court of old nobility whose bones the world was "
            "meant to forget. They keep letters from the dead in gilded "
            "boxes and read them at dusk. Joining means the Elder Gods "
            "close their doors to you."
        ),
        "color": "#7c3aed",
        "sigil": "moon",
    },
    {
        "slug": "ashen-titan",
        "name": "The Ashen Titan",
        "seat": "wandering — the pyres move",
        "founder": "the Cinder-Prophet",
        "lore": (
            "Titan-worshippers who believe the Elder Gods stole the world's "
            "true fire. They burn shrines and mark their own skin with ash. "
            "Their nights end in prayer to something the four Gods forbade."
        ),
        "color": "#dc2626",
        "sigil": "flame",
    },
    {
        "slug": "silver-veil",
        "name": "The Silver Veil",
        "seat": "Rakesh, Veiled Realms",
        "founder": "the Unnamed Moon-Sister",
        "lore": (
            "A shadow-cult of moon-elf splinter mages who bind memory into "
            "silver and gold. Members swear an oath that anything they see "
            "may be sold. The Elder Gods will not hear a prayer with the "
            "taste of silver on the tongue."
        ),
        "color": "#94a3b8",
        "sigil": "moon",
    },
    {
        "slug": "devouring-root",
        "name": "The Devouring Root",
        "seat": "under Thalenroot, Selindori",
        "founder": "the Root-Speaker",
        "lore": (
            "A shadow-druid splinter that feeds the deep woods with debts, "
            "not offerings. They tap sap that hums with something older "
            "than the wood. The four Gods count this as poison in the "
            "world's veins."
        ),
        "color": "#059669",
        "sigil": "feather",
    },
]

RITUALS = {
    "curse-shop": {
        "name": "The Cursing of the Counter",
        "cost_gold": 400,
        "cooldown_world_days": 3,
        "target": "shop_id",
        "effect": "shop_refuses_npc_customers_3d",
        "description": "The chosen shop draws no NPC customers for 3 world days.",
    },
    "drain-city": {
        "name": "The Root-Draught",
        "cost_gold": 800,
        "cooldown_world_days": 5,
        "target": "city_slug",
        "effect": "city_production_halved_3d",
        "description": "Every producer in the city yields half for 3 world days.",
    },
    "unseen-hand": {
        "name": "The Unseen Hand",
        "cost_gold": 300,
        "cooldown_world_days": 2,
        "target": None,
        "effect": "caster_unwitnessed_2_actions",
        "description": "Your next 2 RP actions cannot generate new crimes.",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _real_seconds_for_world_days(n: int) -> int:
    try:
        from world_calendar_service import real_seconds_until_world_days
        return int(real_seconds_until_world_days(n))
    except Exception:
        return int(n * (7 / 30) * 86400)


class CultService:
    def __init__(self, db):
        self.db = db

    # ── seed ──────────────────────────────────────────────

    async def seed_cults(self) -> Dict:
        inserted = 0
        for c in CULTS:
            existing = await self.db.cults.find_one({"slug": c["slug"]}, {"_id": 0, "id": 1})
            if existing:
                continue
            await self.db.cults.insert_one({
                "id": str(uuid.uuid4()),
                **c,
                "created_at": _now_iso(),
            })
            inserted += 1
        return {"inserted": inserted, "total": len(CULTS)}

    # ── read ──────────────────────────────────────────────

    async def list_cults(self) -> List[Dict]:
        return await self.db.cults.find({}, {"_id": 0}).sort("slug", 1).to_list(20)

    async def get_membership(self, character_id: str) -> Optional[Dict]:
        return await self.db.cult_memberships.find_one(
            {"character_id": character_id, "active": True}, {"_id": 0},
        )

    async def list_rituals(self) -> Dict:
        return RITUALS

    # ── join (one-way in this iteration) ─────────────────

    async def join_cult(
        self, *, character_id: str, cult_slug: str,
    ) -> Dict:
        cult = await self.db.cults.find_one({"slug": cult_slug}, {"_id": 0})
        if not cult:
            raise ValueError("Cult not found.")
        existing = await self.get_membership(character_id)
        if existing:
            raise ValueError("You already keep a forbidden oath. There is no room for two.")
        # Catastrophic Elder-God cost
        try:
            from reputation_web_service import ReputationWebService
            rep = ReputationWebService(self.db)
            for god in ("seren", "yros", "uesis", "ehena"):
                # -50 total across 2 nudges (MAX_DELTA cap = 30)
                await rep.adjust(character_id, "god", god, -30, f"Sworn to {cult['name']}")
                await rep.adjust(character_id, "god", god, -20, f"Sworn to {cult['name']}")
        except Exception as e:
            logger.warning(f"cult join rep debit failed: {e}")

        membership = {
            "id": str(uuid.uuid4()),
            "character_id": character_id,
            "cult_slug": cult_slug,
            "cult_name": cult["name"],
            "active": True,
            "joined_at": _now_iso(),
            "cooldowns": {},        # ritual_slug -> real-utc-iso
        }
        await self.db.cult_memberships.insert_one(dict(membership))
        return membership

    # ── ritual ────────────────────────────────────────────

    async def cast_ritual(
        self,
        *,
        character_id: str,
        user_id: str,
        ritual_slug: str,
        target_ref: Optional[str] = None,
    ) -> Dict:
        if ritual_slug not in RITUALS:
            raise ValueError("Unknown ritual.")
        ritual = RITUALS[ritual_slug]
        mem = await self.get_membership(character_id)
        if not mem:
            raise ValueError("Only cult-members may cast forbidden rituals.")
        cooldowns = mem.get("cooldowns") or {}
        cd_iso = cooldowns.get(ritual_slug)
        if cd_iso:
            try:
                cd = datetime.fromisoformat(cd_iso.replace("Z", "+00:00"))
                if cd > _now():
                    raise ValueError(f"{ritual['name']} is not yet ready.")
            except ValueError:
                raise
            except Exception:
                pass
        # Gold cost
        u = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        if int((u or {}).get("currency", 0)) < int(ritual["cost_gold"]):
            raise ValueError(f"You cannot pay the ritual's cost ({ritual['cost_gold']}g).")
        await self.db.users.update_one(
            {"id": user_id}, {"$inc": {"currency": -int(ritual["cost_gold"])}},
        )

        # Apply effect
        effect_id = str(uuid.uuid4())
        effect_ends_iso = (
            _now() + timedelta(seconds=_real_seconds_for_world_days(3))
        ).isoformat()

        if ritual["effect"] == "shop_refuses_npc_customers_3d":
            if not target_ref:
                raise ValueError("This ritual requires a target shop_id.")
            shop = await self.db.shops.find_one({"id": target_ref}, {"_id": 0, "id": 1})
            if not shop:
                raise ValueError("Target shop not found.")
            await self.db.cult_effects.insert_one({
                "id": effect_id,
                "effect": ritual["effect"],
                "target_ref": target_ref,
                "caster_character_id": character_id,
                "cult_slug": mem["cult_slug"],
                "starts_at": _now_iso(),
                "ends_at": effect_ends_iso,
            })
        elif ritual["effect"] == "city_production_halved_3d":
            if not target_ref:
                raise ValueError("This ritual requires a target city_slug.")
            await self.db.cult_effects.insert_one({
                "id": effect_id,
                "effect": ritual["effect"],
                "target_ref": target_ref.lower(),
                "caster_character_id": character_id,
                "cult_slug": mem["cult_slug"],
                "starts_at": _now_iso(),
                "ends_at": effect_ends_iso,
            })
        elif ritual["effect"] == "caster_unwitnessed_2_actions":
            await self.db.cult_effects.insert_one({
                "id": effect_id,
                "effect": ritual["effect"],
                "target_ref": character_id,
                "caster_character_id": character_id,
                "cult_slug": mem["cult_slug"],
                "starts_at": _now_iso(),
                "ends_at": None,          # counter-based
                "uses_remaining": 2,
            })

        # Cooldown
        new_cd = (
            _now() + timedelta(seconds=_real_seconds_for_world_days(int(ritual["cooldown_world_days"])))
        ).isoformat()
        cooldowns[ritual_slug] = new_cd
        await self.db.cult_memberships.update_one(
            {"id": mem["id"]}, {"$set": {"cooldowns": cooldowns}},
        )
        return {
            "effect_id": effect_id,
            "ritual": ritual_slug,
            "target": target_ref,
            "ends_at": effect_ends_iso,
        }

    # ── effect lookups (used by tick + witnesses) ─────────

    async def is_shop_cursed(self, shop_id: str) -> bool:
        row = await self.db.cult_effects.find_one({
            "effect": "shop_refuses_npc_customers_3d",
            "target_ref": shop_id,
            "ends_at": {"$gt": _now_iso()},
        }, {"_id": 0, "id": 1})
        return bool(row)

    async def is_city_drained(self, city_slug: str) -> bool:
        row = await self.db.cult_effects.find_one({
            "effect": "city_production_halved_3d",
            "target_ref": (city_slug or "").lower(),
            "ends_at": {"$gt": _now_iso()},
        }, {"_id": 0, "id": 1})
        return bool(row)

    async def consume_unseen_hand(self, character_id: str) -> bool:
        """Called when a crime would be witnessed. Returns True if the
        witness "looks away" (charge consumed)."""
        row = await self.db.cult_effects.find_one({
            "effect": "caster_unwitnessed_2_actions",
            "target_ref": character_id,
            "uses_remaining": {"$gt": 0},
        }, {"_id": 0})
        if not row:
            return False
        new_uses = int(row.get("uses_remaining", 0)) - 1
        if new_uses <= 0:
            await self.db.cult_effects.delete_one({"id": row["id"]})
        else:
            await self.db.cult_effects.update_one(
                {"id": row["id"]}, {"$set": {"uses_remaining": new_uses}},
            )
        return True
