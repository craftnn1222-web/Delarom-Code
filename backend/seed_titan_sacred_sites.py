"""Tier 2d — Seven Titans Sacred Sites Seeder.

The Seven Titans were slain by Ausar at the dawn of the Astral Era. Even
in defeat, their essence still seeps from the places where the great
battles took place. This seed annotates a curated list of canonical
locations with a `titan_sacred_site` field tying them to one of the seven
themed essences.

The seed is purely ADDITIVE — it never creates new locations. It walks
the catalogue by (nation, slug), finds each row, and sets the field.
Re-running is idempotent.
"""
from __future__ import annotations

from typing import Dict, List


TITAN_SITES: List[Dict] = [
    # ── TITAN OF DECAY ──
    {"nation": "aigraels", "slug": "vargath",   "titan": "decay",
     "rationale": "The contested city; decay seeps from its scarred streets."},

    # ── TITAN OF FROST ──
    {"nation": "dhor-kuldor", "slug": "frosthold", "titan": "frost",
     "rationale": "Capital of Frostpeak Hold; the frost essence is ancestral here."},
    {"nation": "dhor-kuldor", "slug": "icehammer-bastion", "titan": "frost",
     "rationale": "An iron fortress of the Frostpeak Hold, half-buried in glacier."},

    # ── TITAN OF FLAME ──
    {"nation": "dhor-kuldor", "slug": "emberhold", "titan": "flame",
     "rationale": "Capital of Emberdeep Hold; molten heart of the dwarven realms."},
    {"nation": "dhor-kuldor", "slug": "magmathal", "titan": "flame",
     "rationale": "Surface-volcanic forge-city of Emberdeep Hold."},

    # ── TITAN OF STONE ──
    {"nation": "dhor-kuldor", "slug": "stonehaven", "titan": "stone",
     "rationale": "Capital of Stonehearth Hold; the bones of the earth."},
    {"nation": "dhor-kuldor", "slug": "thal-karrak", "titan": "stone",
     "rationale": "Thalgrer's Tomb. The Tongue of Y'ros itself rests here."},

    # ── TITAN OF WIND ──
    {"nation": "ammeonon", "slug": "invrasil", "titan": "wind",
     "rationale": "City of Mages; home to Stormrider, Stormweaver, lightning affinities."},
    {"nation": "selindori", "slug": "aer-cyr", "titan": "wind",
     "rationale": "The sky-realm of the Mountain Elves; Eyrie Cohort patrols."},

    # ── TITAN OF TIDE ──
    {"nation": "ammeonon", "slug": "wymroost", "titan": "tide",
     "rationale": "The largest port in Delarom; tide essence is woven into the city's bones."},
    {"nation": "selindori", "slug": "nal-theris", "titan": "tide",
     "rationale": "Capital of the Tide Elves; eternal cathedral of waves."},

    # ── TITAN OF SHADOW ──
    {"nation": "veiled-realms", "slug": "moonfall",          "titan": "shadow",
     "rationale": "Moon Elf city; lunar/umbral essence saturates the moonlit terraces."},
    {"nation": "veiled-realms", "slug": "selunes-rest",      "titan": "shadow",
     "rationale": "Moon Elf sacred-rest city; Lunomancy practiced here."},
    {"nation": "veiled-realms", "slug": "twilight-citadel",  "titan": "shadow",
     "rationale": "Shadow Elf seat of power; the Umbral arts originate here."},
]


async def seed_titan_sacred_sites(db) -> Dict:
    """Annotates canonical locations with `titan_sacred_site` field."""
    annotated = 0
    already_annotated = 0
    not_found_slugs: List[Dict] = []
    site_results: List[Dict] = []

    for entry in TITAN_SITES:
        nation = entry["nation"]
        slug = entry["slug"]
        titan = entry["titan"]
        # Try locations collection first, then cities.
        loc_doc = await db.locations.find_one({"nation": nation, "slug": slug})
        target_collection = "locations"
        if not loc_doc:
            city_doc = await db.cities.find_one({"nation": nation, "slug": slug})
            if city_doc:
                loc_doc = city_doc
                target_collection = "cities"
        if not loc_doc:
            not_found_slugs.append({"nation": nation, "slug": slug})
            continue

        existing = (loc_doc.get("titan_sacred_site") or "").strip().lower()
        if existing == titan:
            already_annotated += 1
            site_results.append({
                "nation": nation, "slug": slug, "titan": titan,
                "collection": target_collection, "status": "already-annotated",
            })
            continue

        await db[target_collection].update_one(
            {"id": loc_doc["id"]},
            {"$set": {"titan_sacred_site": titan, "is_sacred": True}},
        )
        annotated += 1
        site_results.append({
            "nation": nation, "slug": slug, "titan": titan,
            "collection": target_collection, "status": "annotated",
        })

    return {
        "annotated": annotated,
        "already_annotated": already_annotated,
        "not_found_count": len(not_found_slugs),
        "not_found": not_found_slugs,
        "sites": site_results,
    }
