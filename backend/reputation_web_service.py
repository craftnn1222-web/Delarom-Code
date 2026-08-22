"""Reputation Web — city / faction / Elder-God axes.

Extends the existing per-nation `character_reputation` layer with three
new axes so the world can react to WHO you are at every scale:

    axis="city"    key=<city_slug>       (Wymroost renown)
    axis="faction" key=<faction_slug>    (Amber Consortium standing)
    axis="god"     key=<god_key>         (Seren favour, Yros favour, …)

Each row lives in `character_reputation_web` with the same shape as the
nation-level one:  {score:-100..+100, label, drivers[], last_updated}.

Consequences the service exposes today:
    • `shop_price_modifier(char_id, city_slug)`  → 0.75-1.25 multiplier
    • `god_favour_bias(char_id, god_key)`        → +/- verdict points
    • `guard_stance(char_id, city_slug)`         → salute | ignore | eye | arrest

Downstream code (shops, prayers, MoC scene state) calls these instead of
poking `character_reputation_web` directly.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


VALID_AXES = ("city", "faction", "god")

# Score → label bands (shared by every axis for a consistent UX).
_BANDS: List[Tuple[int, int, str]] = [
    (-100, -76, "Hunted"),
    (-75,  -41, "Reviled"),
    (-40,  -11, "Disliked"),
    (-10,   10, "Nobody"),
    (11,    40, "Known"),
    (41,    75, "Respected"),
    (76,   100, "Legend"),
]

MAX_DELTA = 30       # single-step cap
MAX_DRIVERS = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def label_for(score: int) -> str:
    for low, high, label in _BANDS:
        if low <= score <= high:
            return label
    return "Nobody"


def _validate(axis: str, key: str) -> Tuple[str, str]:
    axis = (axis or "").strip().lower()
    key = (key or "").strip().lower()
    if axis not in VALID_AXES:
        raise ValueError(f"axis must be one of {VALID_AXES}, got '{axis}'.")
    if not key:
        raise ValueError("axis key cannot be empty.")
    return axis, key


class ReputationWebService:
    def __init__(self, db):
        self.db = db

    async def get_axis(
        self, character_id: str, axis: str, key: str,
    ) -> Dict:
        axis, key = _validate(axis, key)
        row = await self.db.character_reputation_web.find_one(
            {"character_id": character_id, "axis": axis, "key": key},
            {"_id": 0},
        )
        if row:
            return row
        return {
            "character_id": character_id,
            "axis": axis,
            "key": key,
            "score": 0,
            "label": label_for(0),
            "drivers": [],
            "last_updated": None,
        }

    async def list_for_character(self, character_id: str) -> Dict:
        cursor = self.db.character_reputation_web.find(
            {"character_id": character_id}, {"_id": 0},
        )
        rows = await cursor.to_list(500)
        out: Dict[str, List[Dict]] = {a: [] for a in VALID_AXES}
        for r in rows:
            out.setdefault(r["axis"], []).append(r)
        # Sort each axis by absolute score desc (loudest first)
        for a in out:
            out[a].sort(key=lambda x: -abs(int(x.get("score", 0))))
        return out

    async def adjust(
        self,
        character_id: str,
        axis: str,
        key: str,
        delta: int,
        reason: str = "",
    ) -> Dict:
        axis, key = _validate(axis, key)
        if not character_id or delta == 0:
            return await self.get_axis(character_id, axis, key)
        delta = max(-MAX_DELTA, min(MAX_DELTA, int(delta)))
        current = await self.get_axis(character_id, axis, key)
        new_score = max(-100, min(100, int(current.get("score", 0)) + delta))
        drivers = current.get("drivers") or []
        drivers.append({
            "at": _now_iso(),
            "delta": delta,
            "reason": (reason or "")[:200],
        })
        drivers = drivers[-MAX_DRIVERS:]
        doc = {
            "character_id": character_id,
            "axis": axis,
            "key": key,
            "score": new_score,
            "label": label_for(new_score),
            "drivers": drivers,
            "last_updated": _now_iso(),
        }
        await self.db.character_reputation_web.update_one(
            {"character_id": character_id, "axis": axis, "key": key},
            {"$set": doc},
            upsert=True,
        )
        return doc

    # ── consequences ─────────────────────────────────────────

    async def shop_price_modifier(
        self, character_id: Optional[str], city_slug: str,
    ) -> float:
        """0.75-1.25 multiplier. Legend gets a friend's price; the Hunted
        pay dearly (if the shop even sells)."""
        if not character_id or not city_slug:
            return 1.0
        row = await self.get_axis(character_id, "city", city_slug)
        score = int(row.get("score", 0))
        # Linear: -100 → +25% (1.25); +100 → -25% (0.75)
        return max(0.75, min(1.25, 1.0 - (score / 400.0)))

    async def god_favour_bias(
        self, character_id: Optional[str], god_key: str,
    ) -> int:
        """Bias applied to prayer verdict rolls. Range roughly -25 .. +25."""
        if not character_id or not god_key:
            return 0
        row = await self.get_axis(character_id, "god", god_key)
        score = int(row.get("score", 0))
        # Quarter of the raw score, capped
        return max(-25, min(25, score // 4))

    async def guard_stance(
        self, character_id: Optional[str], city_slug: str,
    ) -> str:
        """Simple guard reaction band for MoC scene injection."""
        if not character_id or not city_slug:
            return "ignore"
        row = await self.get_axis(character_id, "city", city_slug)
        score = int(row.get("score", 0))
        if score >= 60:
            return "salute"
        if score >= 20:
            return "nod"
        if score >= -20:
            return "ignore"
        if score >= -60:
            return "eye"
        return "arrest"

    # ── scene-state helper for the MoC ────────────────────────

    async def scene_summary(
        self, character_id: str, city_slug: Optional[str] = None,
    ) -> Dict:
        """Compact payload for `scene_state.reputation_web`. Injected into
        every RP turn so the MoC can colour NPC / shopkeeper / guard
        behaviour without extra prompting."""
        axes = await self.list_for_character(character_id)
        top: Dict = {}
        for a, rows in axes.items():
            if rows:
                r = rows[0]
                top[a] = {"key": r["key"], "score": r["score"], "label": r["label"]}
        payload = {"top": top}
        if city_slug:
            payload["current_city"] = {
                "city_slug": city_slug,
                "guard_stance": await self.guard_stance(character_id, city_slug),
                "shop_price_pct": int(round(
                    (await self.shop_price_modifier(character_id, city_slug) - 1.0) * 100
                )),
            }
        return payload
