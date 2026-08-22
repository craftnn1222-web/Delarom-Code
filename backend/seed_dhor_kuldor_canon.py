"""Tier 1 (minimum viable) — Canonical Dhor-Kuldor hold-capital seed.

Adds the six canonical dwarven hold-capital cities that the lore + Titan
Sacred Sites depend on. Idempotent: cities already present are updated
in-place (name / description / hold), never re-inserted.

The full canonical seed is 8 dwarven holds × ~6 cities each = ~48 rows;
this seed handles just the 6 hold-capitals plus 2 satellite cities that
the Titan-site catalogue names. Extending to the full 48 is a future
batch — the schema and seeding pattern are identical.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List


CANONICAL_CITIES: List[Dict] = [
    # ── STONEHEARTH HOLD (Titan of Stone) ──
    {
        "slug": "stonehaven",
        "name": "Stonehaven",
        "nation": "dhor-kuldor",
        "region": "Stonehearth Hold — Capital",
        "hold": "stonehearth",
        "is_capital": True,
        "description": (
            "Capital of Stonehearth Hold — the oldest of the eight dwarven "
            "holds, and by tradition the seat of the Council of Anvils. Built "
            "directly into the granite face of Mount Karvad, its throne hall "
            "is a single unbroken slab of stone the size of a war-galley."
        ),
        "lore": (
            "The Stonehearth Hold is where the first hammer struck the first "
            "anvil in Delarom's history. Every dwarven oath-ring in the realm "
            "traces its lineage back to a Stonehearth forge. Y'ros is patron "
            "here — the sanctuary of Thal'Karrak lies at the hold's deepest "
            "chamber."
        ),
    },
    {
        "slug": "thal-karrak",
        "name": "Thal'Karrak",
        "nation": "dhor-kuldor",
        "region": "Stonehearth Hold — Sacred Site",
        "hold": "stonehearth",
        "is_capital": False,
        "description": (
            "Thalgrer's Tomb — an ancient underground sanctuary carved by the "
            "first dwarven king. At its heart, half-buried in the altar, rests "
            "the Tongue of Y'ros — a stone blade consecrated to the God of "
            "Earth. Only a dwarf may draw it, and only when Y'ros deems them "
            "worthy."
        ),
        "lore": (
            "Thal'Karrak was sealed for four centuries after the last bearer "
            "of the Tongue fell in the Frostwar. The blade returned itself to "
            "the stone; the tomb reopened only when the Vritra Clan took the "
            "throne in 5088. Since then, no one has drawn it — dwarves make "
            "the pilgrimage anyway, to prove themselves before Y'ros."
        ),
    },

    # ── EMBERDEEP HOLD (Titan of Flame) ──
    {
        "slug": "emberhold",
        "name": "Emberhold",
        "nation": "dhor-kuldor",
        "region": "Emberdeep Hold — Capital",
        "hold": "emberdeep",
        "is_capital": True,
        "description": (
            "Capital of Emberdeep Hold — a city built around the mouth of an "
            "active volcanic vent. Its forges run on natural magma-heat and "
            "have not gone cold in six centuries. The Emberdeep dwarves are "
            "the finest weapon-smiths in Delarom, and their steel commands "
            "double the price of any other hold's."
        ),
        "lore": (
            "The Titan of Flame was cast down into the caldera beneath "
            "Emberhold by Ausar in the founding of the Astral Era. Its essence "
            "still leaks from the deep vents — Emberdeep smiths swear the "
            "best blades sing when the wind carries the smell of ash."
        ),
    },
    {
        "slug": "magmathal",
        "name": "Magmathal",
        "nation": "dhor-kuldor",
        "region": "Emberdeep Hold — Surface Forge-City",
        "hold": "emberdeep",
        "is_capital": False,
        "description": (
            "A surface-volcanic city on the flanks of Mount Verrun. Where "
            "Emberhold buries its forges deep, Magmathal builds its foundries "
            "into the open cones — chimneys the height of towers, molten iron "
            "cascading down channels in the black rock."
        ),
        "lore": (
            "Magmathal's smiths took the first oath of the Emberdeep at the "
            "surface, refusing to descend even when the deep vents beckoned. "
            "They say the sky's heat honours Yros as truly as the deep's."
        ),
    },

    # ── FROSTPEAK HOLD (Titan of Frost) ──
    {
        "slug": "frosthold",
        "name": "Frosthold",
        "nation": "dhor-kuldor",
        "region": "Frostpeak Hold — Capital",
        "hold": "frostpeak",
        "is_capital": True,
        "description": (
            "Capital of Frostpeak Hold — a mountain-city carved into a peak "
            "that never thaws. The Frostpeak dwarves are the tallest and "
            "palest of their kind, and their eyes are famously colour-shifted "
            "toward blue after generations of ancestral cold."
        ),
        "lore": (
            "Frosthold guards the northern approach to Dhor-Kuldor. When the "
            "Titan of Frost was slain in the founding, its essence sank into "
            "the peaks around Frosthold and never left. The hold's forges use "
            "ice-quenching techniques no other hold has ever managed to "
            "replicate — Frostpeak steel is prized for holding an edge "
            "through the coldest winters."
        ),
    },
    {
        "slug": "icehammer-bastion",
        "name": "Icehammer Bastion",
        "nation": "dhor-kuldor",
        "region": "Frostpeak Hold — Fortress",
        "hold": "frostpeak",
        "is_capital": False,
        "description": (
            "An iron fortress of the Frostpeak Hold, half-buried in the "
            "eternal glacier of Vor'krak. Its walls are cased in glacier-ice "
            "so thick it does not melt even in the great forge-halls within. "
            "Home to the Icehammer Guard, sworn to hold the northern pass "
            "against any incursion from beyond the Frostwaste."
        ),
        "lore": (
            "The Icehammer Bastion has never fallen. Twice it has been "
            "besieged for over a year; both times the attackers broke camp "
            "before the walls did. The dwarves say Y'ros himself froze the "
            "second army's throats when they mocked his name."
        ),
    },
]


async def seed_dhor_kuldor_canon(db) -> Dict:
    """Insert or update the canonical hold-capital cities. Idempotent."""
    inserted: List[str] = []
    updated: List[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for entry in CANONICAL_CITIES:
        existing = await db.cities.find_one({"nation": entry["nation"], "slug": entry["slug"]})
        payload = {**entry, "updated_at": now, "is_active": True}
        if existing:
            await db.cities.update_one(
                {"nation": entry["nation"], "slug": entry["slug"]},
                {"$set": payload},
            )
            updated.append(entry["slug"])
        else:
            payload["id"] = str(uuid.uuid4())
            payload["created_at"] = now
            await db.cities.insert_one(payload)
            inserted.append(entry["slug"])

    return {
        "cities": {
            "inserted": inserted,
            "updated": updated,
            "total_processed": len(CANONICAL_CITIES),
        },
    }
