"""Formal Duel Service — MoC-narrated contested combat with real wagers.

MVP mechanics (Iteration A):

    • Challenger picks a target character (player or NPC), a weapon-style
      (blade / bow / spell), and a wager (gold amount, item, or a Renown
      stake).
    • Target accepts or declines. Declining a duel is legal but costs
      Renown in the challenger's city — cowardice is punished by rumour.
    • On accept, `resolve_duel()` fires: the MoC narrates three
      exchanges. Each exchange is a contested d20-ish roll against the
      relevant primary stat (STR / AGI / MAG) plus small equipment /
      Renown modifiers.
    • Best-of-three wins the match. Wager transfers to the victor;
      the loser's Renown drops in the duel's city.
    • Death duels are OPT-IN via `stakes='death'` and permanently retire
      the loser character (`status='fallen'`), booking a Chronicles entry.
"""
from __future__ import annotations

import logging
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"      # transient — flips to resolved immediately after narration
STATUS_RESOLVED = "resolved"
STATUS_DECLINED = "declined"
STATUS_CANCELLED = "cancelled"

WEAPON_STAT = {
    "blade": "strength",
    "bow":   "agility",
    "spell": "magic",
    "fist":  "endurance",
}
VALID_WEAPONS = tuple(WEAPON_STAT.keys())

STAKES_GOLD = "gold"
STAKES_ITEM = "item"
STAKES_RENOWN = "renown"
STAKES_DEATH = "death"
VALID_STAKES = (STAKES_GOLD, STAKES_ITEM, STAKES_RENOWN, STAKES_DEATH)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DuelService:
    def __init__(self, db):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    # ── challenge lifecycle ─────────────────────────────────

    async def challenge(
        self,
        *,
        challenger_user: Dict,
        challenger_character: Dict,
        target_character_id: str,
        city_slug: str,
        weapon: str = "blade",
        stakes: str = STAKES_GOLD,
        wager_gold: int = 100,
        wager_item_id: Optional[str] = None,
    ) -> Dict:
        weapon = (weapon or "blade").strip().lower()
        if weapon not in VALID_WEAPONS:
            raise ValueError(f"weapon must be one of {VALID_WEAPONS}.")
        if stakes not in VALID_STAKES:
            raise ValueError(f"stakes must be one of {VALID_STAKES}.")
        if challenger_character["id"] == target_character_id:
            raise ValueError("You cannot duel yourself.")

        target = await self.db.characters.find_one(
            {"id": target_character_id}, {"_id": 0},
        )
        if not target:
            raise ValueError("Target character not found.")
        if (target.get("status") or "").lower() == "fallen":
            raise ValueError("That character has already fallen.")

        # Money check for gold wagers
        if stakes == STAKES_GOLD:
            wager_gold = max(1, int(wager_gold))
            u = await self.db.users.find_one({"id": challenger_user["id"]}, {"_id": 0})
            if int((u or {}).get("currency", 0)) < wager_gold:
                raise ValueError(f"You cannot cover a {wager_gold}g wager.")
        elif stakes == STAKES_ITEM:
            if not wager_item_id:
                raise ValueError("wager_item_id is required for item stakes.")
            inv = challenger_character.get("inventory") or []
            if not any((it.get("id") == wager_item_id) for it in inv):
                raise ValueError("You don't own that item.")
        elif stakes == STAKES_DEATH:
            wager_gold = 0
            wager_item_id = None
        elif stakes == STAKES_RENOWN:
            wager_gold = 0
            wager_item_id = None

        duel_id = str(uuid.uuid4())
        duel = {
            "id": duel_id,
            "city_slug": (city_slug or "").lower(),
            "weapon": weapon,
            "stakes": stakes,
            "wager_gold": wager_gold if stakes == STAKES_GOLD else 0,
            "wager_item_id": wager_item_id if stakes == STAKES_ITEM else None,
            "challenger_user_id": challenger_user["id"],
            "challenger_character_id": challenger_character["id"],
            "challenger_character_name": challenger_character.get("name", ""),
            "target_character_id": target_character_id,
            "target_character_name": target.get("name", ""),
            "target_user_id": target.get("user_id"),
            "status": STATUS_PENDING,
            "created_at": _now_iso(),
            "resolved_at": None,
            "winner_character_id": None,
            "narration": None,
            "exchanges": [],
        }
        await self.db.duels.insert_one(dict(duel))
        return duel

    async def decline(self, *, duel_id: str, user_id: str) -> Dict:
        d = await self._require(duel_id)
        if d["status"] != STATUS_PENDING:
            raise ValueError("This duel is no longer open.")
        if d.get("target_user_id") and d["target_user_id"] != user_id:
            raise ValueError("Only the challenged character may decline.")
        await self.db.duels.update_one(
            {"id": duel_id},
            {"$set": {"status": STATUS_DECLINED, "resolved_at": _now_iso()}},
        )
        # Renown penalty for cowardice — in the challenger's city
        try:
            from reputation_web_service import ReputationWebService
            await ReputationWebService(self.db).adjust(
                d["target_character_id"], "city", d["city_slug"] or "unknown",
                delta=-5,
                reason=f"Declined a duel with {d['challenger_character_name']}",
            )
        except Exception as e:  # pragma: no cover — best-effort
            logger.warning(f"decline rep-penalty failed: {e}")
        return await self.get(duel_id)

    async def accept_and_resolve(
        self, *, duel_id: str, user_id: str,
    ) -> Dict:
        d = await self._require(duel_id)
        if d["status"] != STATUS_PENDING:
            raise ValueError("This duel is no longer open.")
        if d.get("target_user_id") and d["target_user_id"] != user_id:
            raise ValueError("Only the challenged character may accept.")

        chal = await self.db.characters.find_one(
            {"id": d["challenger_character_id"]}, {"_id": 0},
        )
        tgt = await self.db.characters.find_one(
            {"id": d["target_character_id"]}, {"_id": 0},
        )
        if not chal or not tgt:
            raise ValueError("Combatants missing.")

        # ── contested rolls (best-of-3) ─────────────────────
        stat = WEAPON_STAT[d["weapon"]]
        exchanges = []
        chal_wins = 0
        tgt_wins = 0
        for i in range(3):
            chal_roll = random.randint(1, 20) + int(chal.get(stat, 10))
            tgt_roll = random.randint(1, 20) + int(tgt.get(stat, 10))
            winner = "challenger" if chal_roll > tgt_roll else "target" if tgt_roll > chal_roll else "draw"
            if winner == "challenger":
                chal_wins += 1
            elif winner == "target":
                tgt_wins += 1
            exchanges.append({
                "round": i + 1,
                "challenger_roll": chal_roll,
                "target_roll": tgt_roll,
                "winner": winner,
            })
            if chal_wins == 2 or tgt_wins == 2:
                break
        winner_side = "challenger" if chal_wins > tgt_wins else "target"
        winner_char_id = d["challenger_character_id"] if winner_side == "challenger" else d["target_character_id"]
        loser_char_id = d["target_character_id"] if winner_side == "challenger" else d["challenger_character_id"]
        winner_name = d["challenger_character_name"] if winner_side == "challenger" else d["target_character_name"]
        loser_name = d["target_character_name"] if winner_side == "challenger" else d["challenger_character_name"]

        narration = await self._narrate(
            weapon=d["weapon"],
            city_slug=d["city_slug"] or "an unnamed square",
            stakes=d["stakes"],
            exchanges=exchanges,
            challenger=chal,
            target=tgt,
            winner_name=winner_name,
            loser_name=loser_name,
        )

        # ── settlement ──────────────────────────────────────
        await self._settle(d, winner_side, winner_char_id, loser_char_id, exchanges)

        await self.db.duels.update_one(
            {"id": duel_id},
            {"$set": {
                "status": STATUS_RESOLVED,
                "resolved_at": _now_iso(),
                "winner_character_id": winner_char_id,
                "narration": narration,
                "exchanges": exchanges,
            }},
        )
        return await self.get(duel_id)

    # ── settlement helpers ──────────────────────────────────

    async def _settle(self, d, winner_side, winner_char_id, loser_char_id, exchanges):
        stakes = d["stakes"]
        # Wager transfer
        if stakes == STAKES_GOLD and int(d.get("wager_gold", 0)) > 0:
            gold = int(d["wager_gold"])
            winner_user = await self._user_of(winner_char_id)
            loser_user = await self._user_of(loser_char_id)
            if loser_user and winner_user:
                await self.db.users.update_one(
                    {"id": loser_user}, {"$inc": {"currency": -gold}},
                )
                await self.db.users.update_one(
                    {"id": winner_user}, {"$inc": {"currency": gold}},
                )
        elif stakes == STAKES_ITEM and d.get("wager_item_id"):
            challenger_char_id = d["challenger_character_id"]
            # Item begins in challenger's inventory; on target's win it moves to target.
            src_char_id = challenger_char_id
            dst_char_id = winner_char_id if winner_char_id != src_char_id else d["target_character_id"] if winner_side == "challenger" else challenger_char_id
            # Simplify: whoever wins gets the item; if challenger wins, item stays; if target wins, transfer it.
            if winner_side == "target":
                src = await self.db.characters.find_one({"id": src_char_id}, {"_id": 0})
                inv = src.get("inventory") or []
                new_inv = [it for it in inv if it.get("id") != d["wager_item_id"]]
                item = next((it for it in inv if it.get("id") == d["wager_item_id"]), None)
                await self.db.characters.update_one(
                    {"id": src_char_id}, {"$set": {"inventory": new_inv}},
                )
                if item:
                    await self.db.characters.update_one(
                        {"id": dst_char_id}, {"$push": {"inventory": item}},
                    )

        # Renown swing in the duel's city (loser loses, winner gains)
        try:
            from reputation_web_service import ReputationWebService
            rep = ReputationWebService(self.db)
            city = d["city_slug"] or "unknown"
            await rep.adjust(winner_char_id, "city", city, delta=+8,
                             reason=f"Won a duel over {d.get('target_character_name','')}")
            await rep.adjust(loser_char_id, "city", city, delta=-8,
                             reason=f"Lost a duel to {d.get('challenger_character_name','')}")
        except Exception as e:  # pragma: no cover
            logger.warning(f"duel rep swing failed: {e}")

        # Death duel — loser character retires
        if stakes == STAKES_DEATH:
            await self.db.characters.update_one(
                {"id": loser_char_id},
                {"$set": {"status": "fallen", "fallen_at": _now_iso(),
                          "fallen_reason": f"Died in a duel with {d.get('challenger_character_name','')}"}},
            )

    async def _user_of(self, character_id: str) -> Optional[str]:
        c = await self.db.characters.find_one({"id": character_id}, {"_id": 0, "user_id": 1})
        return (c or {}).get("user_id")

    async def _require(self, duel_id: str) -> Dict:
        d = await self.db.duels.find_one({"id": duel_id}, {"_id": 0})
        if not d:
            raise ValueError("Duel not found.")
        return d

    # ── reads ───────────────────────────────────────────────

    async def get(self, duel_id: str) -> Optional[Dict]:
        return await self.db.duels.find_one({"id": duel_id}, {"_id": 0})

    async def list_recent(self, limit: int = 25) -> list:
        return await self.db.duels.find({}, {"_id": 0}).sort(
            "created_at", -1,
        ).limit(max(1, min(200, limit))).to_list(limit)

    async def list_for_character(self, character_id: str, limit: int = 25) -> list:
        return await self.db.duels.find({
            "$or": [
                {"challenger_character_id": character_id},
                {"target_character_id": character_id},
            ],
        }, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)

    # ── MoC narration ───────────────────────────────────────

    async def _narrate(
        self, *, weapon: str, city_slug: str, stakes: str,
        exchanges: list, challenger: Dict, target: Dict,
        winner_name: str, loser_name: str,
    ) -> str:
        try:
            system = (
                "You are the Master of Ceremonies narrating a formal duel "
                "in the world of Delarom (215+ A.E.). Narrate in the "
                "second person from the CHALLENGER's viewpoint. Keep it "
                "tight — 2 short paragraphs, sensory (steel, breath, dust). "
                "Never break canon (no dice, no HP, no XP). English only.\n\n"
                f"Location: {city_slug}. Weapon-style: {weapon}. Stakes: {stakes}.\n"
                f"Challenger: {challenger.get('name','?')} ({challenger.get('race','?')} "
                f"{challenger.get('character_class','?')}).\n"
                f"Target: {target.get('name','?')} ({target.get('race','?')} "
                f"{target.get('character_class','?')}).\n"
                f"Exchange results (do not mention numbers — narrate FROM them):\n"
            )
            for ex in exchanges:
                who = "you gain the upper hand" if ex["winner"] == "challenger" else (
                    "they gain the upper hand" if ex["winner"] == "target" else "the exchange is even")
                system += f"  round {ex['round']}: {who}.\n"
            system += f"Victor: {winner_name}. Loser: {loser_name}.\n"
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"duel_{uuid.uuid4().hex[:8]}",
                system_message=system,
            ).with_model("openai", "gpt-4o")
            resp = await chat.send_message(UserMessage(
                text="Narrate the duel in 2 paragraphs.",
            ))
            return (resp or "").strip() or self._fallback(winner_name, loser_name)
        except Exception as e:
            logger.warning(f"duel narration failed: {e}")
            return self._fallback(winner_name, loser_name)

    @staticmethod
    def _fallback(winner_name: str, loser_name: str) -> str:
        return (
            f"Steel meets steel across the ring of onlookers. The exchange is "
            f"quick, bitter, and decisive — {winner_name} stands over "
            f"{loser_name}, blade lowered, breath ragged, victory taken."
        )
