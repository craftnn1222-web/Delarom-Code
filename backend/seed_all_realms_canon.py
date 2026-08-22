"""Tier 1 (FULL) — Canonical Realms Seed for Tyrandria (215 A.E.).

Extends the earlier Dhor-Kuldor min-viable seed to cover every canonical
city named in the quest_master_ai.py lore blocks, across all five realms:

  • AMMEONON (human kingdom under the Vritra Clan)
  • SELINDORI (elven kingdom — Sun/Wood/Tide/Mountain/Sky sub-realms)
  • DHOR-KULDOR (dwarven realm — 8 holds; canon capitals seeded)
  • AIGRAELS (three-way civil war — Triumvirate faction capitals)
  • VEILED REALMS (mysterious external elven kingdoms — Moon/Shadow/Crystal)

The seed is IDEMPOTENT: for each canonical city, if a row already exists
with the same (nation, slug) tuple, it's updated in place with the
canonical name/description/lore/hold fields; otherwise it's inserted
fresh with a new UUID. Re-running is safe and moves rows from
`inserted` → `updated` on the second pass.

After running this, POST `/api/admin/seed-titan-sacred-sites` will bind
all 14 Titan-themed sites with `not_found_count = 0`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════════════
# AMMEONON — Human kingdom, Vritra Clan rule under Ausar (215 A.E.)
# ═══════════════════════════════════════════════════════════════════════
AMMEONON_CITIES: List[Dict] = [
    {
        "slug": "wymroost", "name": "Wymroost", "nation": "ammeonon",
        "region": "The Amber Coast — Capital", "is_capital": True,
        "description": (
            "Capital of Ammeonon and the largest port city in all of Tyrandria. "
            "Wymroost's harbor swallows a hundred ships at anchor, its airship "
            "moorings crown the cliffs above, and gothic-classical spires of "
            "pearl-and-amber stone rise in tiers from the sea. Once called "
            "Hielgcrom in the Blackburn era, renamed under the Nalviem Dynasty."
        ),
        "lore": (
            "Founded in 1200 by King Quentin Blackburn atop a natural deep-water "
            "harbor. Under the Vritra Clan (post-5088 / Astral Era) Wymroost has "
            "become the trade heart of the continent — dwarven iron flows in, "
            "elven silks flow out, and airships from every realm ride the "
            "coastal thermals. Ausar the Astral King holds court here in the "
            "Pearl Throne."
        ),
    },
    {
        "slug": "invrasil", "name": "Invrasil", "nation": "ammeonon",
        "region": "The Storm Heights — City of Mages", "is_capital": False,
        "description": (
            "A high-altitude city built into the shoulders of Mount Verrand, "
            "reached only by long switchback trails or by airship. Home to the "
            "Six Generals of the Storm — Stormrider, Stormweaver, and their "
            "lightning-touched siblings — and to more registered mages per "
            "capita than any other Ammeonon city."
        ),
        "lore": (
            "The Titan of Wind was slain in the peaks above Invrasil; its "
            "essence still charges the storms that never quite leave the "
            "summit. Invrasil's Academy of Astral Winds teaches Air and "
            "Lightning essence work to any student with the mana for it — "
            "commoner or noble — a genuinely meritocratic institution rare "
            "for Ammeonon."
        ),
    },
    {
        "slug": "hielgcrom-old-town", "name": "Hielgcrom Old Town",
        "nation": "ammeonon", "region": "Wymroost — Ancient Quarter",
        "is_capital": False,
        "description": (
            "The pre-Nalviem original settlement of what became Wymroost — a "
            "walled quarter of the modern capital, preserved by royal decree. "
            "The oldest inns, the founding house of the Blackburn line, and "
            "the buried tomb of Quentin Blackburn are all here."
        ),
        "lore": (
            "Historians say if you know where to knock on the right wall in "
            "Hielgcrom Old Town, you can still find the tunnels the Blackburn "
            "smugglers used before the Nalviem crown made trade legal."
        ),
    },
    {
        "slug": "amberport", "name": "Amberport", "nation": "ammeonon",
        "region": "The Amber Coast — Southern Trade Hub", "is_capital": False,
        "description": (
            "A prosperous secondary port south of Wymroost, specialised in "
            "the amber trade (fossilised sap from the Thalenroot borderwoods) "
            "and in Selindori luxury imports that don't warrant the capital's "
            "tariff scrutiny."
        ),
        "lore": (
            "Amberport's House Vollery has held the customs franchise for six "
            "generations. Nothing moves through Amberport that House Vollery "
            "hasn't taken a cut of — and every merchant in Ammeonon knows it."
        ),
    },
    {
        "slug": "duncroft", "name": "Duncroft", "nation": "ammeonon",
        "region": "The Green Marches — Agrarian Capital", "is_capital": False,
        "description": (
            "The breadbasket city of Ammeonon — surrounded by wheat and "
            "orchards, its granaries feed both Wymroost and the northern "
            "border. Politically the seat of the Farmers' Council, an "
            "unglamorous but powerful body under the Vritra Clan."
        ),
        "lore": (
            "The saying goes: 'When Duncroft strikes, the crown goes hungry.' "
            "The Farmers' Council has broken exactly one king in Ammeonon "
            "history — Nalviem VI, who tried to double the harvest tithe."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════
# SELINDORI — Elven kingdom (isolationist, "Mother Race" per Seren)
# ═══════════════════════════════════════════════════════════════════════
SELINDORI_CITIES: List[Dict] = [
    {
        "slug": "aurelion-spires", "name": "Aurelion Spires", "nation": "selindori",
        "region": "Selindori — Sun Elf Capital / High Seat", "is_capital": True,
        "elf_race": "sun elf",
        "description": (
            "Capital of Selindori, high seat of the Elven Council. Aurelion's "
            "seven crystal spires catch the dawn and refract it into gold "
            "cascades that light the city for hours after sunrise. The "
            "Council Chamber rises inside the tallest spire — approach is "
            "by aerial bridge only, and no non-elf has crossed it in living "
            "memory."
        ),
        "lore": (
            "The Aurelion Spires were sung into being at the founding — Sun "
            "Elf artisan-mages spent three centuries channelling Solar Light "
            "essence into raw crystal until it took the shape their queen "
            "dreamed. The city is the finest expression of Solar Channelling "
            "magic in the realm."
        ),
    },
    {
        "slug": "thalenroot", "name": "Thalenroot", "nation": "selindori",
        "region": "Selindori — Wood Elf Realm-City", "is_capital": False,
        "elf_race": "wood elf",
        "description": (
            "A living city grown from a single ancient oak the size of a "
            "mountain. Homes are woven into the branches; balconies grow "
            "from the trunk on demand; the palace is a hollow crown of "
            "canopy at the very top. Home of the Wood Elves and the "
            "Verdant Weaving magic school."
        ),
        "lore": (
            "The Great Oak of Thalenroot is roughly six thousand years old — "
            "older than Ammeonon by five millennia. It has three known "
            "graftings from the sacred groves of the founding, and no "
            "outsider knows where any of the seed-stock came from."
        ),
    },
    {
        "slug": "nal-theris", "name": "Nal'theris", "nation": "selindori",
        "region": "Selindori — Tide Elf Realm-City", "is_capital": False,
        "elf_race": "tide elf",
        "description": (
            "Half-submerged cathedral-city of the Tide Elves, built on a "
            "coral shelf where the seafloor rises within a few feet of the "
            "surface. Streets flood and drain twice a day; the population "
            "moves through them either on foot or by shallow-draft skiff. "
            "Home of Tidal Reflection magic."
        ),
        "lore": (
            "Nal'theris was consecrated to the Titan of Tide long before "
            "the founding of the Astral Era — the Titan's essence still "
            "runs through the deep coral. Tide Elf casters can pull water "
            "here that Sun Elves in Aurelion could not shift with an "
            "afternoon's effort."
        ),
    },
    {
        "slug": "isenfell", "name": "Isenfell", "nation": "selindori",
        "region": "Selindori — Mountain Elf Realm-City", "is_capital": False,
        "elf_race": "mountain elf",
        "description": (
            "The Mountain Elf city — carved down into a granite valley, "
            "half stone-wrought and half stone-grown. Isenfell's Mountain "
            "Elves practice Stone-Singing, a magic that persuades stone to "
            "reshape itself without breaking. Every home has grown into a "
            "slightly different shape."
        ),
        "lore": (
            "Isenfell has stood, in one form or another, since before the "
            "dwarves of Dhor-Kuldor took up their hammers. The two peoples "
            "have an uneasy respect: dwarves work stone by force, Mountain "
            "Elves by persuasion, and neither will admit the other's way "
            "produces the finer result."
        ),
    },
    {
        "slug": "aer-cyr", "name": "Aer'Cyr", "nation": "selindori",
        "region": "Selindori — Sky Realm / Eyrie Cohort", "is_capital": False,
        "elf_race": "mountain elf",
        "description": (
            "The Sky-Realm of the Eyrie Cohort — a cluster of aeries and "
            "cliff-terraces at altitude, reached only by griffon-riders and "
            "the occasional airship. The wind never stops here, and the "
            "Eyrie Cohort patrols the storm-ridges above the whole of "
            "Selindori from these heights."
        ),
        "lore": (
            "The Titan of Wind's essence lingers in the ridges around "
            "Aer'Cyr — the Eyrie Cohort's griffons are said to be able to "
            "read air currents that would kill any normal rider. Aer'Cyr "
            "is one of the very few Selindori cities that maintains any "
            "diplomatic relationship with Invrasil in Ammeonon; they trade "
            "wind-lore between the two Titan-of-Wind sites."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════
# DHOR-KULDOR — Dwarven realm (ancient, 8 holds; canon capitals only)
# ═══════════════════════════════════════════════════════════════════════
# NOTE: The min-viable Tier 1 seed already covered Stonehaven, Thal'Karrak,
# Emberhold, Magmathal, Frosthold, and Icehammer Bastion. This entry adds
# the remaining canonical entities named in the quest_master_ai lore block:
# Ancestor Hall (capital), Irondeep, Gloomstone.
DHOR_KULDOR_CITIES: List[Dict] = [
    {
        "slug": "ancestor-hall", "name": "Ancestor Hall", "nation": "dhor-kuldor",
        "region": "Ancestor Hold — High King's Capital", "hold": "ancestor",
        "is_capital": True,
        "description": (
            "Capital of Dhor-Kuldor and seat of the High King. Ancestor Hall "
            "is built into the flank of Mount Karvad-Vur; its throne room "
            "opens onto the Hall of Ancestors — a mile-long crypt-gallery "
            "housing the tombs of every High King since Durin the Deathless. "
            "The Council of Thanes meets here."
        ),
        "lore": (
            "Construction of Ancestor Hall began around 1200 by the "
            "surface calendar — the same year Ammeonon was founded. "
            "Where the humans built a young kingdom, the dwarves were "
            "adding the newest wing to an already-ancient civilisation "
            "eight thousand years deep."
        ),
    },
    {
        "slug": "irondeep", "name": "Irondeep", "nation": "dhor-kuldor",
        "region": "Irondeep Hold — Industrial Capital", "hold": "irondeep",
        "is_capital": False,
        "description": (
            "The industrial heart of Dhor-Kuldor. Irondeep's master forges "
            "produce the finest weapons and armour in Tyrandria — every "
            "royal armoury in every realm has at least one Irondeep piece "
            "in it. The city is a warren of workshops, arsenals, and "
            "apprentice-halls, all under the eye of the Forgemaster's Guild."
        ),
        "lore": (
            "Irondeep was founded during the Expansion Period (Years 100-500 "
            "of the First Era) as the dwarves learned to mine deeper. Its "
            "great forge-fires have not gone cold in over four thousand "
            "years — a claim no other city in Tyrandria can match."
        ),
    },
    {
        "slug": "gloomstone", "name": "Gloomstone", "nation": "dhor-kuldor",
        "region": "Gloomstone Hold — Mining Capital", "hold": "gloomstone",
        "is_capital": False,
        "description": (
            "The deepest mining city of Dhor-Kuldor and the only known "
            "source of the legendary Gloom Stone — the same mineral Durin "
            "the Deathless discovered when he founded the realm. Gloomstone's "
            "veins reach into strata that predate the mortal races."
        ),
        "lore": (
            "The Gloom Stone is dark, dense, and slightly warm to the "
            "touch — properties no scholar has satisfactorily explained. "
            "Every Dwarven artefact of the highest calibre incorporates "
            "at least a shaving of it. Export is forbidden by royal decree."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════
# AIGRAELS — Wartorn nation, three Triumvirate faction capitals
# ═══════════════════════════════════════════════════════════════════════
AIGRAELS_CITIES: List[Dict] = [
    {
        "slug": "ironhold", "name": "Ironhold", "nation": "aigraels",
        "region": "Ardent Legion Territory — Faction Capital",
        "triumvirate": "ardent-legion", "is_capital": False,
        "description": (
            "Fortress-city capital of the Ardent Legion. Every street is "
            "wide enough for a full troop column; the walls are three-tier "
            "curtain walls with kill-boxes between them; the civilian "
            "quarter is quite deliberately small. The Crucible Yards test "
            "new war machines every dawn."
        ),
        "lore": (
            "Ironhold was founded on the ruins of the previous kingdom's "
            "capital after the Ardent Legion took it in the second year of "
            "the Undying War. The Hall of Standards displays captured enemy "
            "banners — currently ninety-one of the Forsaken Court and "
            "sixty-three of the Elderborn Alliance. General Serus Valthar "
            "commands from the Iron Cathedra atop the citadel."
        ),
    },
    {
        "slug": "noctyss-vale", "name": "Noctyss Vale", "nation": "aigraels",
        "region": "Forsaken Court Territory — Hidden Faction Capital",
        "triumvirate": "forsaken-court", "is_capital": False,
        "description": (
            "The hidden city of the Forsaken Court. Noctyss Vale does not "
            "appear on any Aigraels map issued by any faction — its "
            "streets are labyrinthine, its houses windowless, its "
            "aristocracy masked. Lady Selene Valthos rules from the House "
            "of Veils; the Veiled Synod convenes in the Mirror Crypts, "
            "where every wall whispers back at speakers."
        ),
        "lore": (
            "Two Ardent Legion offensives have tried to find Noctyss Vale "
            "on the march. Neither returned. The Court's methods — "
            "assassination, subversion, engineered plague — are the reason "
            "no faction has been able to permanently push them out of "
            "Aigraels' politics despite their small territorial footprint."
        ),
    },
    {
        "slug": "astra-lun", "name": "Astra'Lun", "nation": "aigraels",
        "region": "Elderborn Alliance Territory — Scholar-Mage Capital",
        "triumvirate": "elderborn-alliance", "is_capital": False,
        "description": (
            "Capital of the Elderborn Alliance — a city shaped by magic "
            "rather than built by hand. Crystal architecture bends toward "
            "astral conduits; the Starwell at the city's heart pulls "
            "starlight down into a slow-turning nexus of raw astral "
            "essence. Education is mandatory; the Circle of "
            "Constellations governs by debate."
        ),
        "lore": (
            "Astra'Lun's Hall of Echoed Thought preserves the audio-spells "
            "of every major debate the Circle has ever held — thousands of "
            "years of political and magical argument, playable by any "
            "citizen with a library-token. High Sage Eloria Nyx rules by "
            "consensus rather than decree, which is why the Alliance is "
            "the slowest to move of the three factions — and the hardest "
            "to break."
        ),
    },
    {
        "slug": "vargath", "name": "Vargath", "nation": "aigraels",
        "region": "Contested — the Crimson Year city", "is_contested": True,
        "is_capital": False,
        "description": (
            "The most-contested city in Aigraels — Vargath has changed "
            "hands seven times in the last calendar year, once between "
            "sunrise and sunset. Barricades split its districts by "
            "banner; three different tax collectors work three different "
            "quarters; scorch-marks are older than the buildings."
        ),
        "lore": (
            "Vargath's civilian population has dropped by two-thirds in "
            "a decade. The Titan of Decay was slain in the fields west "
            "of the city; its essence saturates the ruins and — every "
            "war-mage in Tyrandria agrees — is why no faction has been "
            "able to hold the city more than a season."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════
# VEILED REALMS — three sub-realms of external elven kingdoms
# ═══════════════════════════════════════════════════════════════════════
VEILED_REALMS_CITIES: List[Dict] = [
    {
        "slug": "rakesh", "name": "Rakesh", "nation": "veiled-realms",
        "region": "Rakesh — Moon Elf Realm-Capital", "elf_race": "moon elf",
        "is_capital": True,
        "description": (
            "Realm-capital of the Moon Elves and the birthplace of "
            "Lunomancy. Rakesh's tiered moonlit terraces catch and "
            "amplify moonlight for use in magic; the city sleeps by day "
            "and works by night. The Silver Court gathers under the "
            "full moon only, and never speaks in daylight."
        ),
        "lore": (
            "The Titan of Shadow was slain in the mountains above Rakesh; "
            "Moon Elves consider its residual essence the source of their "
            "magic. Their relations with Selindori are cordial but "
            "distant — the Sun Elves consider Moon Elves 'lesser cousins,' "
            "which Moon Elves find both insulting and beneath response."
        ),
    },
    {
        "slug": "yaksha-shi", "name": "Yaksha-Shi", "nation": "veiled-realms",
        "region": "Yaksha-Shi — Shadow Elf Realm-Capital",
        "elf_race": "shadow elf", "is_capital": False,
        "description": (
            "Realm-capital of the Shadow Elves. Yaksha-Shi is built inside "
            "a series of natural cave-cathedrals where sunlight has never "
            "reached; the city is lit by bioluminescent moss and by the "
            "practiced Umbral Arts of its people. Homes are hewn into the "
            "obsidian walls; the palace occupies the deepest chamber."
        ),
        "lore": (
            "Shadow Elves are the most-feared and least-understood of the "
            "elven sub-races. Their Umbral Arts — magic that channels the "
            "*absence* of light rather than shadow-as-substance — are "
            "considered heretical in Selindori and forbidden to teach "
            "outside Yaksha-Shi. The rulers of Yaksha-Shi have not "
            "answered a diplomatic overture from Aurelion in a hundred years."
        ),
    },
    {
        "slug": "serant-kresh", "name": "Serant-Kresh", "nation": "veiled-realms",
        "region": "Serant-Kresh — Crystal Elf Realm-Capital",
        "elf_race": "crystal elf", "is_capital": False,
        "description": (
            "Realm-capital of the Crystal Elves — a city grown from a "
            "single vast quartz seed, with every home and passage a "
            "crystalline extension of the original stone. Crystal Elves "
            "practise Memory-Binding: they can etch a memory into a "
            "crystal-shard and share it with another exactly as it was "
            "experienced."
        ),
        "lore": (
            "Serant-Kresh's Vault of Kept Memory holds crystal-shards "
            "dating back to the founding of the Astral Era — every "
            "Crystal Elf ruler has committed their sight of a great "
            "event to the vault. Historians of every realm know Serant-"
            "Kresh is the single most-accurate historical archive in "
            "Tyrandria; none of them are allowed inside."
        ),
    },
    {
        "slug": "moonfall", "name": "Moonfall", "nation": "veiled-realms",
        "region": "Rakesh Environs — Sacred Moon-Terrace",
        "elf_race": "moon elf", "is_capital": False,
        "description": (
            "A satellite city of Rakesh, built on the eastern slope of "
            "the Silvered Peaks. Moonfall's Grand Terrace is the "
            "traditional site of the Moon Rites — Lunomancy ceremonies "
            "that only fire on the night the moon sets fullest against "
            "the city's namesake ridge."
        ),
        "lore": (
            "It is said in Rakesh that a Moon Elf who has not attended "
            "at least one Moon Rite at Moonfall does not truly know "
            "their own people. The city's population triples on those "
            "nights and empties again by dawn."
        ),
    },
    {
        "slug": "selunes-rest", "name": "Selune's Rest", "nation": "veiled-realms",
        "region": "Rakesh Environs — Moon Elf Rest-City",
        "elf_race": "moon elf", "is_capital": False,
        "description": (
            "A quieter sister-city to Rakesh, given over almost entirely "
            "to Lunomancers in retreat, memorial gardens, and the study "
            "of dreams. Selune's Rest lives at half-pace: everything "
            "here is quieter, slower, and lit by the low silver of the "
            "waning moon."
        ),
        "lore": (
            "Selune's Rest was founded by the first named Lunomancer as "
            "a place to die. The tradition has held — retiring Silver "
            "Court members withdraw here to spend their last years "
            "committing dream-memory to Crystal Elf shards, and the "
            "city's cemetery is one of the largest in all the Veiled "
            "Realms."
        ),
    },
    {
        "slug": "twilight-citadel", "name": "The Twilight Citadel",
        "nation": "veiled-realms",
        "region": "Yaksha-Shi Environs — Shadow Elf Seat of Power",
        "elf_race": "shadow elf", "is_capital": False,
        "description": (
            "The Twilight Citadel guards the only above-ground approach "
            "to Yaksha-Shi. Its towers are angled so that at every hour "
            "of the day, at least one is in shadow. The Shadow Guard "
            "who man it are said to be the finest close-quarters "
            "practitioners of Umbral Arts in any realm."
        ),
        "lore": (
            "No non-Shadow-Elf has entered the Twilight Citadel in "
            "recorded memory. The Umbral Arts practiced in its "
            "training halls include forms that erase the sound and the "
            "very memory of the practitioner from any witness within "
            "reach — an unsettling defence, and effective."
        ),
    },
]


# All realms bundled — the endpoint runs them all.
ALL_REALMS = {
    "ammeonon":      AMMEONON_CITIES,
    "selindori":     SELINDORI_CITIES,
    "dhor-kuldor":   DHOR_KULDOR_CITIES,
    "aigraels":      AIGRAELS_CITIES,
    "veiled-realms": VEILED_REALMS_CITIES,
}


async def _seed_one_realm(db, nation: str, cities: List[Dict]) -> Dict:
    inserted: List[str] = []
    updated: List[str] = []
    now = datetime.now(timezone.utc).isoformat()
    for entry in cities:
        existing = await db.cities.find_one({"nation": nation, "slug": entry["slug"]})
        payload = {**entry, "updated_at": now, "is_active": True}
        if existing:
            await db.cities.update_one(
                {"nation": nation, "slug": entry["slug"]},
                {"$set": payload},
            )
            updated.append(entry["slug"])
        else:
            payload["id"] = str(uuid.uuid4())
            payload["created_at"] = now
            await db.cities.insert_one(payload)
            inserted.append(entry["slug"])
    return {
        "inserted": inserted,
        "updated": updated,
        "total_processed": len(cities),
    }


async def seed_all_realms_canon(db) -> Dict:
    """Seeds every canonical city across all five realms. Idempotent."""
    results: Dict[str, Dict] = {}
    for nation, cities in ALL_REALMS.items():
        results[nation] = await _seed_one_realm(db, nation, cities)
    total_inserted = sum(len(r["inserted"]) for r in results.values())
    total_updated = sum(len(r["updated"]) for r in results.values())
    total_processed = sum(r["total_processed"] for r in results.values())
    return {
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "total_processed": total_processed,
        "by_realm": results,
    }
