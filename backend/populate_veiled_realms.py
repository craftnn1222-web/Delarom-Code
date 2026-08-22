"""
Populate The Veiled Realms - Hidden Ancient Elven Kingdoms
Protected by ancient barrier magic - those who enter uninvited face confusion, madness, and death.

Kingdoms:
- Rakesh (Moon Elves) - Niratha + 2 cities + 3 towns
- Yaksha-Shi (Shadow Elves) - Twilight Citadel + 2 cities + 3 towns  
- Serant-Kresh (Crystal Elves) - Kreshmar + 2 cities + 3 towns

Total: ~9 Cities, ~9 Towns, ~66 Locations
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# ============================================================================
# RAKESH - KINGDOM OF THE MOON ELVES
# ============================================================================
RAKESH_CITIES = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "niratha",
        "name": "Niratha",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "The City of a Thousand Moons. Capital of Rakesh, built on floating terraces illuminated by orbiting lunar shards.",
        "lore": "Niratha changes subtly with each moon phase, its architecture seeming to breathe with the lunar cycle. The Moon Queen rules from here, guided by the whispers of celestial forces.",
        "faction": "Lunar Court",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "moonfall",
        "name": "Moonfall",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "A city built for loss. Used during eclipses, it houses exiles, the ill, and the forgotten.",
        "lore": "When the moon hides, power fades. Moonfall exists for those whose connection to lunar magic has broken. Here, the powerless find refuge—or oblivion.",
        "faction": "House of Fading",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "crescent-reach",
        "name": "Crescent Reach",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "Trade city connecting Rakesh to other realms. Heavily ritualized, where no weapons are allowed.",
        "lore": "Diplomacy in Crescent Reach follows ancient protocols. Every word is weighed, every gesture meaningful. Violence here would shatter centuries of carefully maintained peace.",
        "faction": "Diplomatic Corps",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

RAKESH_TOWNS = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "duskmere",
        "name": "Duskmere",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "Agricultural settlement in perpetual twilight, cultivating lunar herbs and moon-fed crops.",
        "lore": "Duskmere bears Rakesh's burden. When moons fail, Duskmere starves first. Children born here often become seers—or never awaken their magic at all.",
        "faction": "Twilight Farmers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "selunes-rest",
        "name": "Selune's Rest",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "Pilgrimage and mourning sanctuary for those who have lost their connection to the moon.",
        "lore": "Former queens, broken seers, and disgraced nobles come to Selune's Rest to fade peacefully. It is a place of endings, honored but sorrowful.",
        "faction": "Order of Fading Light",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "lowtide-spire",
        "name": "Lowtide Spire",
        "region": "Rakesh - Kingdom of Moon Elves",
        "description": "Astral observation and defense outpost at the edge of the Lunar Veil.",
        "lore": "Lowtide Spire's inhabitants see things no other elves do—and are sworn never to speak of them. They watch for cosmic intrusion, ever vigilant.",
        "faction": "Starwatchers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# YAKSHA-SHI - KINGDOM OF THE SHADOW ELVES
# ============================================================================
YAKSHASHI_CITIES = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "twilight-citadel",
        "name": "Twilight Citadel",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Capital and living fortress of the Shadow Elves, carved into obsidian cliffs in the Penumbral Deep.",
        "lore": "Always half-lit, half-dark, the Twilight Citadel was built to disappear if needed. The Night Regent rules from the Eclipsed Spire, guided by whispers from the dark entity they worship.",
        "faction": "Night Assembly",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "blackgrove",
        "name": "Blackgrove",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Training city hidden beneath living roots where Shadow Elves master the arts of darkness.",
        "lore": "In Blackgrove, light is the enemy. Initiates learn to move without sound, kill without being seen, and disappear without a trace. Those who fail do not leave.",
        "faction": "Shadow Academy",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "veilcross",
        "name": "Veilcross",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Trade and intelligence exchange hub where information is the most valuable currency.",
        "lore": "Veilcross is where secrets are bought and sold. The Shadow Elves trade in knowledge—truths that can topple kingdoms, lies that can start wars.",
        "faction": "Information Brokers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

YAKSHASHI_TOWNS = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "duskwatch",
        "name": "Duskwatch",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Border surveillance settlement watching Selindori—not for invasion, but collapse.",
        "lore": "Many in Duskwatch are former Sun Elf agents who defected. They watch their old homeland with bitter patience, waiting for the hierarchy to crumble.",
        "faction": "Border Observers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "gravepine",
        "name": "Gravepine",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Burial settlement where dead Shadow Elves are interred beneath memory-absorbing pines.",
        "lore": "The pines of Gravepine absorb the memories of the dead, preventing necromantic exploitation. The trees remember everything—and whisper to those who listen.",
        "faction": "Death Keepers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "silent-hollow",
        "name": "Silent Hollow",
        "region": "Yaksha-Shi - Kingdom of Shadow Elves",
        "description": "Lightless ravine settlement for those who failed the Shadow trials but were not executed.",
        "lore": "Silent Hollow is where the broken live—silent, watched, forgotten. They failed to become true Shadow Elves, but death was deemed too merciful.",
        "faction": "The Forgotten",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# SERANT-KRESH - KINGDOM OF THE CRYSTAL ELVES
# ============================================================================
SERANTKRESH_CITIES = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "kreshmar",
        "name": "Kreshmar",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "The Living Archive. Capital grown from memory-crystals, where streets hum and walls replay history.",
        "lore": "Kreshmar is memory made manifest. The crystals that form its structure remember everything that happened within their sight. History cannot be erased here—only witnessed.",
        "faction": "Archivist Council",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "prismhold",
        "name": "Prismhold",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "Defensive city guarding the Prismatic Vale, where light itself becomes a weapon.",
        "lore": "Prismhold's defenders wield light refracted through crystal into devastating beams. No army has breached its walls, for the very air burns those who approach uninvited.",
        "faction": "Prism Guard",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "lumenshaft",
        "name": "Lumenshaft",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "Industrial-mystic city focused on artifact crafting deep within the crystal caverns.",
        "lore": "In Lumenshaft, artisans craft artifacts of incredible power from the living crystals. Each creation carries memories—some beautiful, some terrible.",
        "faction": "Artificer Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

SERANTKRESH_TOWNS = [
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "glimmerdeep",
        "name": "Glimmerdeep",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "Mining settlement in the lower crystal caverns where emotional echoes linger.",
        "lore": "Miners in Glimmerdeep often absorb fragments of memories from the crystals they harvest. Some gain wisdom; others go mad from experiences not their own.",
        "faction": "Crystal Miners",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "facetmere",
        "name": "Facetmere",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "Trade and diplomacy settlement bridging Serant-Kresh with the outside world.",
        "lore": "Every trade in Facetmere is recorded in crystal. Every lie remembered. The merchants here are scrupulously honest—they have no choice.",
        "faction": "Crystal Merchants",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "veiled-realms",
        "slug": "shardfall",
        "name": "Shardfall",
        "region": "Serant-Kresh - Kingdom of Crystal Elves",
        "description": "Disposal settlement in a crystal canyon where dangerous memories are sealed away.",
        "lore": "Crystals deemed too dangerous are cast into Shardfall, where they fracture endlessly but never truly die. The canyon echoes with forgotten screams.",
        "faction": "Memory Wardens",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# LOCATIONS
# ============================================================================

def generate_veiled_locations():
    """Generate all locations for the Veiled Realms"""
    locations = []
    
    # ===== NIRATHA LOCATIONS =====
    niratha_locations = [
        ("niratha", "The Moon Queen's Throne", "Throne Room", "Seat of power for Rakesh, where the Moon Queen interprets celestial will."),
        ("niratha", "The Orrery of Fate", "Observatory", "Massive celestial model that predicts the movements of moon and stars."),
        ("niratha", "Temple of the Three Phases", "Temple", "Sacred site honoring the waxing, full, and waning moon."),
        ("niratha", "The Crescent Crown", "Palace District", "Where the Moon Queen and her court reside."),
        ("niratha", "Moonweaver's Reach", "Academy District", "Where mage-scholars study Lunomancy."),
        ("niratha", "The Tidal Steps", "Trade District", "Markets and diplomatic halls."),
        ("niratha", "The Waning Ward", "Quiet District", "Where power fades during dark moons."),
        ("niratha", "The Waxing Chalice", "Tavern", "Establishment for philosophy and prophecy discussion."),
    ]
    
    # ===== MOONFALL LOCATIONS =====
    moonfall_locations = [
        ("moonfall", "The Hall of Last Light", "Sanctuary", "Where those who've lost their lunar connection find peace."),
        ("moonfall", "Eclipse Hospice", "Hospital", "Care for those whose magic has faded."),
        ("moonfall", "The Fading Gardens", "Gardens", "Plants that bloom only in darkness."),
        ("moonfall", "Remembrance Hall", "Memorial", "Honoring those who once shone bright."),
    ]
    
    # ===== CRESCENT REACH LOCATIONS =====
    crescent_locations = [
        ("crescent-reach", "The Accord Chamber", "Diplomatic Hall", "Where treaties are negotiated in ritualized silence."),
        ("crescent-reach", "Neutral Ground Market", "Marketplace", "Trading without weapons or deception."),
        ("crescent-reach", "Embassy Row", "Diplomatic Quarter", "Residences for foreign dignitaries."),
        ("crescent-reach", "The Quiet Apogee", "Observatory Bar", "Silent establishment with stunning celestial views."),
    ]
    
    # ===== RAKESH TOWN LOCATIONS =====
    duskmere_locations = [
        ("duskmere", "The Silver Fields", "Farmland", "Moon-fed terraces producing lunar herbs."),
        ("duskmere", "Shrine of Waning Breath", "Shrine", "For dying Lunomancers to make peace."),
    ]
    
    selunes_rest_locations = [
        ("selunes-rest", "The Stillwater Basin", "Sacred Pool", "Where fading elves contemplate eternity."),
        ("selunes-rest", "Hall of Last Names", "Memorial", "Recording those who chose to fade."),
    ]
    
    lowtide_locations = [
        ("lowtide-spire", "The Starfall Lattice", "Observatory", "Detecting cosmic anomalies."),
        ("lowtide-spire", "The Observatory of Silence", "Watchtower", "Where watchers see what cannot be spoken."),
    ]
    
    # ===== TWILIGHT CITADEL LOCATIONS =====
    twilight_locations = [
        ("twilight-citadel", "The Umbral Throne", "Throne Room", "Seat of the Night Regent, half in light, half in shadow."),
        ("twilight-citadel", "Hall of Blades Unseen", "Arsenal", "Weapons that exist only when needed."),
        ("twilight-citadel", "The Memory Vault", "Archive", "Secrets too dangerous for ordinary storage."),
        ("twilight-citadel", "The Veiled Ascents", "Training District", "Where shadows are mastered."),
        ("twilight-citadel", "Blackroot Ward", "Civilian District", "Where Shadow Elf families live."),
        ("twilight-citadel", "The Silent Crucible", "Court", "Where trials and executions occur in darkness."),
        ("twilight-citadel", "Whisperfall Path", "Street", "Where secrets are exchanged."),
        ("twilight-citadel", "The Last Shadow", "Tavern", "Sparse, quiet establishment for the elite."),
    ]
    
    # ===== BLACKGROVE LOCATIONS =====
    blackgrove_locations = [
        ("blackgrove", "The Lightless Halls", "Training Center", "Where initiates learn to see without light."),
        ("blackgrove", "Shadow Binding Chamber", "Ritual Room", "Connecting students to their shadow selves."),
        ("blackgrove", "The Trial Maze", "Testing Ground", "Deadly labyrinth for final examinations."),
        ("blackgrove", "Instructor's Sanctum", "Administration", "Where masters plan the curriculum of darkness."),
    ]
    
    # ===== VEILCROSS LOCATIONS =====
    veilcross_locations = [
        ("veilcross", "The Information Exchange", "Marketplace", "Where secrets are the only currency."),
        ("veilcross", "Whisperer's Gallery", "Meeting Hall", "Private rooms for sensitive negotiations."),
        ("veilcross", "The Blind Eye Inn", "Inn", "Lodging where no one sees anything."),
        ("veilcross", "Contract Hall", "Legal", "Where deals are sealed in shadow."),
    ]
    
    # ===== YAKSHA-SHI TOWN LOCATIONS =====
    duskwatch_locations = [
        ("duskwatch", "The Thousand-Lens Tower", "Watchtower", "Observing Selindori through magical scrying."),
        ("duskwatch", "The Listening Roots", "Intelligence Center", "Processing information from the trees themselves."),
    ]
    
    gravepine_locations = [
        ("gravepine", "The Rootbound Vault", "Cemetery", "Where the dead sleep beneath whispering pines."),
        ("gravepine", "The Black Sap Pool", "Sacred Site", "Where memories are given to the trees."),
    ]
    
    silent_hollow_locations = [
        ("silent-hollow", "The Broken Hall", "Community Center", "Where the failed gather in silence."),
        ("silent-hollow", "The Null Shrine", "Shrine", "Honoring what could have been."),
    ]
    
    # ===== KRESHMAR LOCATIONS =====
    kreshmar_locations = [
        ("kreshmar", "The Grand Archive", "Library", "Repository of all recorded memory-crystals."),
        ("kreshmar", "Chamber of Shattered Names", "Memorial", "Crystals holding memories of those erased from Selindori's history."),
        ("kreshmar", "The Resonance Engine", "Artifact", "Ancient device that amplifies crystal magic."),
        ("kreshmar", "The Resonant Core", "Central District", "Heart of Kreshmar where the oldest crystals sing."),
        ("kreshmar", "Shardward District", "Residential", "Where Crystal Elf families live among memory-stones."),
        ("kreshmar", "The Silent Galleries", "Museum", "Displaying history as the crystals remember it."),
        ("kreshmar", "The Fractured Lens", "Tavern", "Where memories flow as freely as drinks."),
        ("kreshmar", "Stillmemory Hall", "Meditation Center", "For processing absorbed memories."),
    ]
    
    # ===== PRISMHOLD LOCATIONS =====
    prismhold_locations = [
        ("prismhold", "The Light Batteries", "Defensive Installation", "Crystal arrays that focus sunlight into weapons."),
        ("prismhold", "Guardian Barracks", "Military Base", "Housing the Prism Guard."),
        ("prismhold", "The Refraction Chamber", "War Room", "Planning defense through light manipulation."),
        ("prismhold", "Beacon Tower", "Watchtower", "Warning system for the entire kingdom."),
    ]
    
    # ===== LUMENSHAFT LOCATIONS =====
    lumenshaft_locations = [
        ("lumenshaft", "The Deep Forges", "Workshop", "Where artifacts are crafted from living crystal."),
        ("lumenshaft", "Memory Infusion Chamber", "Ritual Room", "Binding experiences into crystalline form."),
        ("lumenshaft", "Artificer's Gallery", "Showroom", "Displaying completed works of crystal magic."),
        ("lumenshaft", "The Crystal Gardens", "Growing Chamber", "Where new crystals are cultivated."),
    ]
    
    # ===== SERANT-KRESH TOWN LOCATIONS =====
    glimmerdeep_locations = [
        ("glimmerdeep", "The Weeping Veins", "Mine", "Crystal deposits rich with emotional residue."),
        ("glimmerdeep", "Chamber of Echoing Names", "Processing", "Sorting memories from raw crystal."),
    ]
    
    facetmere_locations = [
        ("facetmere", "The Accord Mirror", "Diplomatic Hall", "Where truth is impossible to hide."),
        ("facetmere", "The Prism Gate", "Entry Point", "Gateway to the hidden kingdom."),
    ]
    
    shardfall_locations = [
        ("shardfall", "The Endless Fracture", "Canyon", "Where dangerous crystals fall forever."),
        ("shardfall", "Ward of Unremembering", "Containment", "Sealing memories too terrible to keep."),
    ]
    
    # Combine all location data
    all_location_data = (
        niratha_locations + moonfall_locations + crescent_locations +
        duskmere_locations + selunes_rest_locations + lowtide_locations +
        twilight_locations + blackgrove_locations + veilcross_locations +
        duskwatch_locations + gravepine_locations + silent_hollow_locations +
        kreshmar_locations + prismhold_locations + lumenshaft_locations +
        glimmerdeep_locations + facetmere_locations + shardfall_locations
    )
    
    for city_slug, name, loc_type, desc in all_location_data:
        locations.append({
            "id": str(uuid4()),
            "nation": "veiled-realms",
            "city": city_slug,
            "slug": name.lower().replace(" ", "-").replace("'", ""),
            "name": name,
            "location_type": loc_type,
            "description": desc,
            "image_url": None,
            "is_active": True,
            "is_rp_enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return locations


async def populate_veiled_realms_data():
    """Populate Veiled Realms nation data into the database."""
    print("🌙 Starting Veiled Realms data population...")
    print("=" * 70)
    print("The Hidden Ancient Kingdoms - Protected by barrier magic")
    print("=" * 70)
    
    locations = generate_veiled_locations()
    
    all_cities = RAKESH_CITIES + YAKSHASHI_CITIES + SERANTKRESH_CITIES
    all_towns = RAKESH_TOWNS + YAKSHASHI_TOWNS + SERANTKRESH_TOWNS
    
    # Insert cities
    print(f"\n🏛️ Inserting {len(all_cities)} cities...")
    for city in all_cities:
        existing = await db.cities.find_one({"nation": city["nation"], "slug": city["slug"]})
        if existing:
            print(f"  ⏭️  City '{city['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(city)
            print(f"  ✅ Created city: {city['name']}")
    
    # Insert towns
    print(f"\n🏘️ Inserting {len(all_towns)} towns...")
    for town in all_towns:
        existing = await db.cities.find_one({"nation": town["nation"], "slug": town["slug"]})
        if existing:
            print(f"  ⏭️  Town '{town['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(town)
            print(f"  ✅ Created town: {town['name']}")
    
    # Insert locations
    print(f"\n📍 Inserting {len(locations)} locations...")
    for location in locations:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    print("\n" + "=" * 70)
    print("✨ Veiled Realms data population complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  - Rakesh (Moon Elves): {len(RAKESH_CITIES)} cities, {len(RAKESH_TOWNS)} towns")
    print(f"  - Yaksha-Shi (Shadow Elves): {len(YAKSHASHI_CITIES)} cities, {len(YAKSHASHI_TOWNS)} towns")
    print(f"  - Serant-Kresh (Crystal Elves): {len(SERANTKRESH_CITIES)} cities, {len(SERANTKRESH_TOWNS)} towns")
    print(f"  - Total locations: {len(locations)}")


if __name__ == "__main__":
    asyncio.run(populate_veiled_realms_data())
