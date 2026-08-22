"""
Festival Service.

Manages in-world festivals and holy days. Each festival has a fixed
`(start_month, start_day)`..`(end_month, end_day)` window on the Delarom
calendar — which maps 1:1 to real-world months. Festivals can wrap the
year boundary (e.g., Hollowfall 31 → Lanternlong 2).

Seeded on first access via `ensure_seeded()`. Idempotent.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict


SEED_FESTIVALS = [
    {
        "id": "fest-lanterns",
        "name": "The Festival of Lanterns",
        "nation": "ammeonon",
        "start_month": 11, "start_day": 1,
        "end_month": 11, "end_day": 3,
        "description": (
            "Every street, waterway, and rooftop in Ammeonon is hung with paper lanterns. "
            "Families set candle-boats afloat for the dead, and strangers exchange small "
            "lights as blessings for the year ahead."
        ),
    },
    {
        "id": "fest-stormwake",
        "name": "The Stormwake",
        "nation": "selindori",
        "start_month": 2, "start_day": 14,
        "end_month": 2, "end_day": 15,
        "description": (
            "Selindori honours the sea-god Vael with two nights of drumming on the docks. "
            "Sailors offer salt and wine to the tide; old grudges are formally drowned in "
            "the harbour and forgotten by dawn."
        ),
    },
    {
        "id": "fest-forging-days",
        "name": "The Forging Days",
        "nation": "dhor-kuldor",
        "start_month": 3, "start_day": 21,
        "end_month": 3, "end_day": 22,
        "description": (
            "Every smithy in Dhor Kuldor opens its doors. Master craftsmen demonstrate "
            "their finest work, apprentices are publicly named, and feuding clans cool "
            "their iron together in the great communal forge."
        ),
    },
    {
        "id": "fest-highsong",
        "name": "Highsong",
        "nation": "aigraels",
        "start_month": 5, "start_day": 1,
        "end_month": 5, "end_day": 1,
        "description": (
            "On a single day each year, every chorister in Aigraels gathers in the open "
            "amphitheatres to sing the long ballads of the founding. The song is said to "
            "carry as far as the foothills, and those who join uninvited are simply welcomed in."
        ),
    },
    {
        "id": "fest-veiling",
        "name": "The Veiling",
        "nation": "veiled-realms",
        "start_month": 10, "start_day": 31,
        "end_month": 11, "end_day": 1,
        "description": (
            "On the night the Veil between worlds is thinnest, every citizen of the "
            "Veiled Realms walks abroad masked. Identities are forgotten until dawn — "
            "monarchs share wine with thieves, and no secret told this night may be held "
            "against you in any court."
        ),
    },
]


def _is_active(fest: Dict, dt: datetime) -> bool:
    """True iff `dt` (date-only) falls inside the festival window.

    Handles wrap-around festivals where end_month < start_month
    (e.g., Yulewreath 28 → Frostmere 3).
    """
    cur = dt.month * 100 + dt.day
    start = fest["start_month"] * 100 + fest["start_day"]
    end = fest["end_month"] * 100 + fest["end_day"]
    if start <= end:
        return start <= cur <= end
    # Wraps the year boundary
    return cur >= start or cur <= end


class FestivalService:
    def __init__(self, db):
        self.db = db
        self.col = db.festivals

    async def ensure_seeded(self) -> None:
        """Insert the seed festivals if the collection is empty. Idempotent."""
        existing = await self.col.count_documents({})
        if existing == 0:
            await self.col.insert_many([{**f} for f in SEED_FESTIVALS])

    async def list_all(self) -> List[Dict]:
        await self.ensure_seeded()
        return await self.col.find({}, {"_id": 0}).to_list(200)

    async def get_active(
        self,
        nation: Optional[str] = None,
        dt: Optional[datetime] = None,
    ) -> List[Dict]:
        """Return festivals currently in their window. Filter by nation if given."""
        await self.ensure_seeded()
        dt = dt or datetime.now(timezone.utc)
        q = {"nation": nation} if nation else {}
        festivals = await self.col.find(q, {"_id": 0}).to_list(200)
        return [f for f in festivals if _is_active(f, dt)]
