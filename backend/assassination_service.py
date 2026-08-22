"""Assassination Contract Service — anonymous player-vs-player hits.

Mechanics (Iteration B):

    • Any character in a city posts a contract on any target character
      for a gold bounty. The buyer's identity is redacted from the
      board — only the target's name, the reward, and the city are
      shown. The MoC learns the buyer's identity but never leaks it
      to the target.

    • 30% of the reward is burnt upfront as a fixer's fee (goes to the
      "shadow_fixer_treasury" — currently just discarded). 70% is
      held in escrow on the contract and paid to the assassin on kill.

    • Any OTHER character (not the buyer, not the target) may claim
      the contract. Only one accepted contract on a given target at a
      time — first come first served.

    • Once accepted, the assassin has a fixed window (default 14 world
      days) to fire an `attempt`. Each attempt is a contested AGI roll
      with a small bonus for higher Renown in the city (assassins with
      infamy find better paths). Success → target retires; the
      assassin's Renown in the city is nudged only slightly (the world
      never confirms it was them, only that death happened).

    • The target sees ONLY the attempt narration on their next scene —
      whether it lands, wounds, or misses. They never see the buyer.
"""
from __future__ import annotations

import logging
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


CONTRACT_STATUS_OPEN = "open"
CONTRACT_STATUS_ACCEPTED = "accepted"
CONTRACT_STATUS_COMPLETED = "completed"
CONTRACT_STATUS_FAILED = "failed"
CONTRACT_STATUS_EXPIRED = "expired"

FIXER_FEE_PCT = 0.30
MIN_BOUNTY = 250
DEFAULT_EXPIRY_WORLD_DAYS = 14
MAX_ATTEMPTS_PER_CONTRACT = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(contract: Dict) -> Dict:
    """Strip the buyer's identity from a contract payload."""
    if not contract:
        return contract
    safe = {k: v for k, v in contract.items() if k != "_id"}
    safe["buyer_user_id"] = None
    safe["buyer_character_id"] = None
    safe["buyer_character_name"] = None
    return safe


class AssassinationService:
    def __init__(self, db):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    # ── post ───────────────────────────────────────────────

    async def post_contract(
        self,
        *,
        buyer_user: Dict,
        buyer_character: Dict,
        target_character_id: str,
        city_slug: str,
        reward_gold: int,
        note: str = "",
    ) -> Dict:
        if target_character_id == buyer_character["id"]:
            raise ValueError("You cannot contract your own death.")
        reward_gold = int(reward_gold)
        if reward_gold < MIN_BOUNTY:
            raise ValueError(f"Minimum contract reward is {MIN_BOUNTY}g.")
        u = await self.db.users.find_one({"id": buyer_user["id"]}, {"_id": 0})
        if int((u or {}).get("currency", 0)) < reward_gold:
            raise ValueError(f"You cannot cover a {reward_gold}g reward.")

        target = await self.db.characters.find_one(
            {"id": target_character_id}, {"_id": 0},
        )
        if not target:
            raise ValueError("Target character not found.")
        if (target.get("status") or "").lower() == "fallen":
            raise ValueError("That character is already dead.")

        # Prevent double-open on same target in same city
        existing = await self.db.assassination_contracts.find_one({
            "target_character_id": target_character_id,
            "city_slug": (city_slug or "").lower(),
            "status": {"$in": [CONTRACT_STATUS_OPEN, CONTRACT_STATUS_ACCEPTED]},
        }, {"_id": 0, "id": 1})
        if existing:
            raise ValueError("A contract on this target in this city is already active.")

        # Debit buyer immediately — the fixer takes their fee no matter what.
        await self.db.users.update_one(
            {"id": buyer_user["id"]}, {"$inc": {"currency": -reward_gold}},
        )
        fixer_fee = int(round(reward_gold * FIXER_FEE_PCT))
        escrow = reward_gold - fixer_fee

        # World-days-based expiry (real UTC iso) — computed via calendar
        try:
            from world_calendar_service import add_world_days
            expires_at = add_world_days(_now_iso(), DEFAULT_EXPIRY_WORLD_DAYS)
        except Exception:
            expires_at = None

        contract = {
            "id": str(uuid.uuid4()),
            "buyer_user_id": buyer_user["id"],
            "buyer_character_id": buyer_character["id"],
            "buyer_character_name": buyer_character.get("name", ""),
            "target_character_id": target_character_id,
            "target_character_name": target.get("name", ""),
            "target_user_id": target.get("user_id"),
            "city_slug": (city_slug or "").lower(),
            "reward_gold": reward_gold,
            "fixer_fee": fixer_fee,
            "escrow_gold": escrow,
            "note": (note or "")[:400],
            "status": CONTRACT_STATUS_OPEN,
            "accepted_by_user_id": None,
            "accepted_by_character_id": None,
            "accepted_by_character_name": None,
            "attempts": [],
            "created_at": _now_iso(),
            "expires_at": expires_at,
            "resolved_at": None,
        }
        await self.db.assassination_contracts.insert_one(dict(contract))
        return contract

    # ── accept ─────────────────────────────────────────────

    async def accept_contract(
        self,
        *,
        contract_id: str,
        assassin_user: Dict,
        assassin_character: Dict,
    ) -> Dict:
        c = await self.get(contract_id)
        if not c:
            raise ValueError("Contract not found.")
        if c["status"] != CONTRACT_STATUS_OPEN:
            raise ValueError("This contract is no longer open.")
        if c["target_character_id"] == assassin_character["id"]:
            raise ValueError("You cannot accept a contract on yourself.")
        if c["buyer_character_id"] == assassin_character["id"]:
            raise ValueError("You cannot accept your own contract.")
        await self.db.assassination_contracts.update_one(
            {"id": contract_id},
            {"$set": {
                "status": CONTRACT_STATUS_ACCEPTED,
                "accepted_by_user_id": assassin_user["id"],
                "accepted_by_character_id": assassin_character["id"],
                "accepted_by_character_name": assassin_character.get("name", ""),
                "accepted_at": _now_iso(),
            }},
        )
        return await self.get(contract_id)

    # ── attempt ────────────────────────────────────────────

    async def attempt(
        self,
        *,
        contract_id: str,
        assassin_user: Dict,
    ) -> Dict:
        c = await self.get(contract_id)
        if not c:
            raise ValueError("Contract not found.")
        if c["status"] != CONTRACT_STATUS_ACCEPTED:
            raise ValueError("Contract must be accepted before an attempt.")
        if c["accepted_by_user_id"] != assassin_user["id"]:
            raise ValueError("Only the accepting assassin may attempt.")
        if len(c.get("attempts", [])) >= MAX_ATTEMPTS_PER_CONTRACT:
            raise ValueError("You have exhausted your attempts on this contract.")

        assassin = await self.db.characters.find_one(
            {"id": c["accepted_by_character_id"]}, {"_id": 0},
        )
        target = await self.db.characters.find_one(
            {"id": c["target_character_id"]}, {"_id": 0},
        )
        if not assassin or not target:
            raise ValueError("Combatants missing.")

        # Contested roll: AGI + city Renown/10 bonus for the assassin
        assassin_renown = 0
        try:
            from reputation_web_service import ReputationWebService
            rep = ReputationWebService(self.db)
            row = await rep.get_axis(assassin["id"], "city", c["city_slug"])
            assassin_renown = int(row.get("score", 0)) // 10  # ±10 max
        except Exception:
            pass
        a_roll = random.randint(1, 20) + int(assassin.get("agility", 10)) + assassin_renown
        t_roll = random.randint(1, 20) + int(target.get("agility", 10))
        succeeded = a_roll >= t_roll

        # MoC narration — TARGET's viewpoint (they see the attempt, not the buyer)
        narration = await self._narrate_attempt(
            city_slug=c["city_slug"],
            assassin=assassin,
            target=target,
            succeeded=succeeded,
            a_roll=a_roll,
            t_roll=t_roll,
        )
        attempt = {
            "id": str(uuid.uuid4()),
            "at": _now_iso(),
            "assassin_roll": a_roll,
            "target_roll": t_roll,
            "succeeded": succeeded,
            "narration_to_target": narration,
        }
        await self.db.assassination_contracts.update_one(
            {"id": contract_id},
            {"$push": {"attempts": attempt}},
        )

        if succeeded:
            await self._settle_success(c, assassin_user["id"], attempt)
            return await self.get(contract_id)

        # If we've hit max attempts, contract fails
        if len(c.get("attempts", [])) + 1 >= MAX_ATTEMPTS_PER_CONTRACT:
            await self._settle_failure(c)
            return await self.get(contract_id)
        return await self.get(contract_id)

    # ── settlements ────────────────────────────────────────

    async def _settle_success(self, c: Dict, assassin_user_id: str, attempt: Dict) -> None:
        # Pay escrow to the assassin
        await self.db.users.update_one(
            {"id": assassin_user_id}, {"$inc": {"currency": int(c["escrow_gold"])}},
        )
        # Retire the target
        await self.db.characters.update_one(
            {"id": c["target_character_id"]},
            {"$set": {
                "status": "fallen",
                "fallen_at": _now_iso(),
                "fallen_reason": f"Struck down in {c['city_slug']} — the streets say a shadow.",
            }},
        )
        # City Renown for the target drops (rumours), assassin's rises slightly
        try:
            from reputation_web_service import ReputationWebService
            rep = ReputationWebService(self.db)
            await rep.adjust(
                c["target_character_id"], "city", c["city_slug"],
                delta=-10,
                reason="Rumours of a violent end circulate the alleys",
            )
            await rep.adjust(
                c["accepted_by_character_id"], "city", c["city_slug"],
                delta=+3,
                reason="Whispers of competence, unnamed",
            )
        except Exception as e:  # pragma: no cover
            logger.warning(f"assassination rep swing failed: {e}")
        await self.db.assassination_contracts.update_one(
            {"id": c["id"]},
            {"$set": {"status": CONTRACT_STATUS_COMPLETED, "resolved_at": _now_iso()}},
        )

    async def _settle_failure(self, c: Dict) -> None:
        # Return escrow to the buyer (fixer fee is NOT refunded)
        await self.db.users.update_one(
            {"id": c["buyer_user_id"]}, {"$inc": {"currency": int(c["escrow_gold"])}},
        )
        await self.db.assassination_contracts.update_one(
            {"id": c["id"]},
            {"$set": {"status": CONTRACT_STATUS_FAILED, "resolved_at": _now_iso()}},
        )

    # ── reads ──────────────────────────────────────────────

    async def get(self, contract_id: str) -> Optional[Dict]:
        return await self.db.assassination_contracts.find_one(
            {"id": contract_id}, {"_id": 0},
        )

    async def list_board(self, city_slug: Optional[str] = None) -> List[Dict]:
        """Public board — buyer info stripped."""
        q: Dict = {"status": {"$in": [CONTRACT_STATUS_OPEN, CONTRACT_STATUS_ACCEPTED]}}
        if city_slug:
            q["city_slug"] = city_slug.lower()
        rows = await self.db.assassination_contracts.find(
            q, {"_id": 0},
        ).sort("created_at", -1).to_list(200)
        return [_redact(r) for r in rows]

    async def list_posted_by_user(self, user_id: str) -> List[Dict]:
        rows = await self.db.assassination_contracts.find(
            {"buyer_user_id": user_id}, {"_id": 0},
        ).sort("created_at", -1).to_list(50)
        return rows  # buyer sees their own — no redact

    async def list_attempts_on_target(
        self, target_character_id: str,
    ) -> List[Dict]:
        """The target's view — sees attempts, never the buyer."""
        rows = await self.db.assassination_contracts.find(
            {"target_character_id": target_character_id}, {"_id": 0},
        ).sort("created_at", -1).to_list(50)
        return [_redact(r) for r in rows]

    # ── narration ──────────────────────────────────────────

    async def _narrate_attempt(
        self, *, city_slug: str, assassin: Dict, target: Dict,
        succeeded: bool, a_roll: int, t_roll: int,
    ) -> str:
        try:
            system = (
                "You are the Master of Ceremonies narrating an assassination "
                "attempt in the world of Delarom. Narrate in the SECOND "
                "PERSON from the TARGET's viewpoint. English only. Never "
                "name or describe the attacker; the target sees only glimpses "
                "(a blade in the alley, a poisoned cup, a voice in the crowd). "
                "Two short paragraphs. Sensory, tight. End on a decisive beat "
                f"— the attempt {'lands, and darkness closes in' if succeeded else 'fails, the shadow slips away'}.\n"
                f"Location: {city_slug}. Target: {target.get('name','?')} "
                f"({target.get('race','?')} {target.get('character_class','?')})."
            )
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"assn_{uuid.uuid4().hex[:8]}",
                system_message=system,
            ).with_model("openai", "gpt-4o")
            resp = await chat.send_message(UserMessage(
                text="Narrate the attempt as the target experiences it.",
            ))
            return (resp or "").strip() or self._fallback(succeeded)
        except Exception as e:
            logger.warning(f"assassination narration failed: {e}")
            return self._fallback(succeeded)

    @staticmethod
    def _fallback(succeeded: bool) -> str:
        if succeeded:
            return (
                "A shape peels from a doorway. You feel the strike before you "
                "see it — cold, precise, final. Somewhere a bell begins to toll."
            )
        return (
            "Something moves at the edge of your vision. Metal glances off "
            "your ribs; a boot scuffs stone. When you turn — no one. Only "
            "the taste of iron and the certainty that this is not over."
        )
