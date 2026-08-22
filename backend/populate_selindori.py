"""
Populate Selindori - Kingdom of the First Elves
The most ancient of elven realms where Seren's divine touch is felt in every stone and tree.

Structure:
- Yillhone (Capital) - 6 Districts
- Helior Vale - Solarath + 2 towns
- Verdanthold Wilds - Thalenroot + 3 towns
- Veilwater Coasts - Nal'Theris + 3 towns
- Frostward Reach - Isenfell + 2 towns
- Skyriven Isles - Aer'Cyr

Total: ~19 Cities/Districts, ~10 Towns, ~94 Locations
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
# YILLHONE - THE CRYSTAL CITY (6 Districts)
# ============================================================================
YILLHONE_DISTRICTS = [
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "aurelion-spires",
        "name": "Aurelion Spires",
        "region": "Yillhone - The Crystal City",
        "description": "White-gold crystal towers bathed in eternal dawn. Home to the Sun Elves, the divine nobility of Selindori.",
        "lore": "The Aurelion Spires represent the pinnacle of Sun Elf culture - radiant, beautiful, and utterly convinced of their divine right to rule. Here, streets are paved with sun-kissed crystal and the air itself seems to glow with Seren's blessing.",
        "faction": "Sun Elf Nobility",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "verdant-crescent",
        "name": "Verdant Crescent",
        "region": "Yillhone - The Crystal City",
        "description": "Living terraces woven into crystal-rooted trees. The Forest Elves' district pulses with natural energy.",
        "lore": "Where crystal meets living wood, the Verdant Crescent thrives. Forest Elves here maintain their connection to nature even within the city walls, growing homes from the trees themselves.",
        "faction": "Forest Elf Wardens",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "veilwater-quarter",
        "name": "Veilwater Quarter",
        "region": "Yillhone - The Crystal City",
        "description": "Canals, mist bridges, and reflective glass-stone. The Mist Elves dwell here, watched but indispensable.",
        "lore": "The Veilwater Quarter is a place of quiet beauty and quiet suspicion. Mist Elves control the city's water supply, making them essential yet feared. Their mastery of water magic is both respected and distrusted.",
        "faction": "Mist Elf Keepers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "frostmere-enclave",
        "name": "Frostmere Enclave",
        "region": "Yillhone - The Crystal City",
        "description": "Cool marble halls and frost-veined crystal. The Snow Elves' scholarly enclave within the Crystal City.",
        "lore": "A place of quiet contemplation and ancient knowledge, Frostmere Enclave houses the Snow Elves who chose city life over mountain solitude. Their healing arts and scholarly pursuits are valued, if not their opinions.",
        "faction": "Snow Elf Scholars",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "gilded-underway",
        "name": "The Gilded Underway",
        "region": "Yillhone - The Crystal City",
        "description": "Subterranean labor district—officially 'decommissioned' but still inhabited by Mountain Elves in shadow.",
        "lore": "Officially erased from records, the Gilded Underway persists in the depths beneath Yillhone. Mountain Elves labor here in conditions the surface elves prefer to forget exist. The name is a cruel irony.",
        "faction": "Mountain Elf Laborers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "crystal-heart",
        "name": "Crystal Heart",
        "region": "Yillhone - The Crystal City",
        "description": "The central district of Yillhone where all races may walk, though never as equals. Seat of the High Synod.",
        "lore": "At the very center of Yillhone lies the Crystal Heart, where Seren's touch first blessed the earth. Here stands the High Synod's chambers, the Grand Temple of Seren, and the markets where all elves may trade—but only Sun Elves may rule.",
        "faction": "High Synod",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# REGIONAL CITIES
# ============================================================================
SELINDORI_CITIES = [
    # Helior Vale
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "solarath",
        "name": "Solarath",
        "region": "Helior Vale",
        "description": "City of Divine Mandate. A place of absolute hierarchy and ceremonial grandeur where the Sun Elves reign supreme.",
        "lore": "Solarath embodies everything the Sun Elves believe themselves to be: radiant, powerful, and divinely ordained. Its towers catch the first light of dawn and the last rays of dusk, never truly knowing darkness.",
        "faction": "Sun Elf Theocracy",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Verdanthold Wilds
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "thalenroot",
        "name": "Thalenroot",
        "region": "Verdanthold Wilds",
        "description": "City of Living Stone. Military heart of the Forest Elves, where nature and warfare intertwine.",
        "lore": "Built into and around ancient trees whose roots grip living stone, Thalenroot serves as the military headquarters of Selindori's armies. It was here that the invasion of Dhor-Kuldor was repelled in the year 640.",
        "faction": "Forest Elf Military",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Veilwater Coasts
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "nal-theris",
        "name": "Nal'Theris",
        "region": "Veilwater Coasts",
        "description": "City of Still Waters. An isolationist settlement of ritual purity where Mist Elves practice their ancient ways.",
        "lore": "Nal'Theris exists in perpetual mist, its inhabitants preferring the veil between themselves and the judgmental eyes of other elves. Here, the pact with the Spirit King of Water is renewed each generation.",
        "faction": "Mist Elf Ritualists",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Frostward Reach
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "isenfell",
        "name": "Isenfell",
        "region": "Frostward Reach",
        "description": "City of Quiet Endurance. A stoic Snow Elf settlement dedicated to scholarship and the healing arts.",
        "lore": "Isenfell's inhabitants embody the Snow Elf virtues of humility, discipline, and endurance. Their libraries contain knowledge others have forgotten, and their healers can mend wounds both physical and spiritual.",
        "faction": "Snow Elf Healers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Skyriven Isles
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "aer-cyr",
        "name": "Aer'Cyr",
        "region": "Skyriven Isles",
        "description": "City Above the World. The mysterious floating capital of the Sky Elves and their dragon companions.",
        "lore": "Few have seen Aer'Cyr and lived to speak of it clearly. The Sky Elves' floating city drifts among the clouds, its inhabitants riding upon dragons and commanding the very winds. Their true power remains unknown.",
        "faction": "Sky Elf Dragonriders",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# TOWNS
# ============================================================================
SELINDORI_TOWNS = [
    # Helior Vale Towns
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "aurenviel",
        "name": "Aurenviel",
        "region": "Helior Vale",
        "description": "Clerical estate town serving Solarath's religious needs.",
        "lore": "Aurenviel houses the lesser priests and acolytes who maintain Solarath's countless shrines. Life here is prayer, study, and absolute obedience to the divine hierarchy.",
        "faction": "Sun Elf Clergy",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "heliospan",
        "name": "Heliospan",
        "region": "Helior Vale",
        "description": "Agricultural settlement worked by enslaved lower elves under Sun Elf overseers.",
        "lore": "The golden fields of Heliospan are tended not by Sun Elves, but by those beneath them. The beauty of the harvest masks the cruelty of its cultivation.",
        "faction": "Sun Elf Overseers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Verdanthold Towns
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "oakspire",
        "name": "Oakspire",
        "region": "Verdanthold Wilds",
        "description": "Military village where Forest Elf children are trained from youth.",
        "lore": "In Oakspire, childhood ends early. The settlement exists to produce warriors for Thalenroot, and every child learns to fight before they learn to read.",
        "faction": "Forest Elf Trainers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "greenwatch",
        "name": "Greenwatch",
        "region": "Verdanthold Wilds",
        "description": "Sentinel outpost on the forest border, slowly being abandoned.",
        "lore": "Greenwatch once guarded against Blood Elf incursions. With that threat seemingly ended, the settlement withers, its purpose forgotten by those who no longer fear the mountains.",
        "faction": "Forest Elf Sentinels",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "barkhollow",
        "name": "Barkhollow",
        "region": "Verdanthold Wilds",
        "description": "Artisan village producing living armor and nature-crafted equipment.",
        "lore": "Barkhollow's craftsmen grow armor from living wood and weave weapons from thorns. Their creations are prized across Selindori, yet they receive little recognition from Sun Elf masters.",
        "faction": "Forest Elf Artisans",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Veilwater Towns
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "silverflow",
        "name": "Silverflow",
        "region": "Veilwater Coasts",
        "description": "Fishing village where Mist Elves harvest the sea's bounty.",
        "lore": "The waters around Silverflow are said to be blessed by Devdan himself. Mist Elves here commune with the sea, drawing forth fish that shimmer like moonlight.",
        "faction": "Mist Elf Fishers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "reedhaven",
        "name": "Reedhaven",
        "region": "Veilwater Coasts",
        "description": "Secluded settlement built among the marshes, hidden from outsiders.",
        "lore": "Reedhaven exists because the Mist Elves wished to disappear. The settlement is nearly impossible to find without a guide, protected by natural mazes and water magic.",
        "faction": "Mist Elf Isolationists",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "lowmist",
        "name": "Lowmist",
        "region": "Veilwater Coasts",
        "description": "Trading post where Mist Elves reluctantly interact with other races.",
        "lore": "Lowmist serves as the Mist Elves' face to the outside world—a necessary compromise. Trade happens here, but trust does not.",
        "faction": "Mist Elf Traders",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Frostward Towns
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "snowmere",
        "name": "Snowmere",
        "region": "Frostward Reach",
        "description": "Resource town producing ice-glass and housing exiled scholars.",
        "lore": "Snowmere's ice-glass is prized throughout Selindori, but assignment here is considered punishment. Scholars who displease their superiors are 'relocated' to its frozen halls.",
        "faction": "Snow Elf Exiles",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "selindori",
        "slug": "thawpoint",
        "name": "Thawpoint",
        "region": "Frostward Reach",
        "description": "Diplomatic outpost where rare meetings with Mist Elves occur.",
        "lore": "At the boundary where frost meets mist, Thawpoint maintains a fragile peace between Snow and Mist Elves. Conversations here are careful, measured, and never quite honest.",
        "faction": "Snow Elf Diplomats",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# LOCATIONS
# ============================================================================

def generate_locations():
    """Generate all locations for Selindori"""
    locations = []
    
    # ===== AURELION SPIRES LOCATIONS =====
    aurelion_locations = [
        ("aurelion-spires", "The Solar Basilica", "Temple", "Seren's grand temple where the Sun Elves worship their goddess in ceremonies of blinding radiance."),
        ("aurelion-spires", "Hall of the First King", "Throne Chamber", "The legendary throne room of Suneh, first king of the elves, preserved in eternal golden light."),
        ("aurelion-spires", "The Auric Archive", "Vault", "Sacred bloodline vaults where Sun Elf genealogies are kept, determining who may rule and who may not."),
        ("aurelion-spires", "Dawnward Promenade", "Street", "The main avenue of the Sun Elf district, lined with statues of legendary rulers."),
        ("aurelion-spires", "The Radiant Chalice", "Inn", "Exclusive lodging for Sun Elf nobles, where even the servants wear gold."),
        ("aurelion-spires", "House Illumar", "Diplomatic Estate", "Where foreign dignitaries are housed—and watched carefully."),
    ]
    
    # ===== VERDANT CRESCENT LOCATIONS =====
    verdant_locations = [
        ("verdant-crescent", "The Grove of Fen", "Sacred Grove", "Ancient grove where Fen first spoke with the Earth, now a place of pilgrimage for Forest Elves."),
        ("verdant-crescent", "The Living Armory", "Arsenal", "Weapons grown rather than forged, maintained by master nature-shapers."),
        ("verdant-crescent", "Emerald Warhall", "Military Hall", "Where Forest Elf commanders plan the defense of Selindori."),
        ("verdant-crescent", "Rootsong Walk", "Street", "Winding paths between tree-homes where the roots themselves sing with magic."),
        ("verdant-crescent", "The Bark & Blade", "Tavern", "Rough tavern where warriors share stories and scars."),
        ("verdant-crescent", "Sapfire Hall", "Gathering Hall", "Community hall where Forest Elves debate and celebrate."),
    ]
    
    # ===== VEILWATER QUARTER LOCATIONS =====
    veilwater_locations = [
        ("veilwater-quarter", "The Silent Basin", "Sacred Pool", "Still waters that reflect truths the viewer may not wish to see."),
        ("veilwater-quarter", "Watershrine of Devdan", "Shrine", "Where the pact with the Spirit King of Water is honored and renewed."),
        ("veilwater-quarter", "Rippleway", "Canal Street", "Main waterway through the quarter, traveled by elegant glass boats."),
        ("veilwater-quarter", "Devdan's Crossing", "Bridge", "Mist-shrouded bridge where important oaths are sworn."),
        ("veilwater-quarter", "The Drifting Reed", "Inn", "Floating inn that moves slowly through the quarter's canals."),
        ("veilwater-quarter", "Mistbound Rest", "Tavern", "Quiet establishment where conversations vanish into the fog."),
    ]
    
    # ===== FROSTMERE ENCLAVE LOCATIONS =====
    frostmere_locations = [
        ("frostmere-enclave", "The White Archive", "Library", "Repository of Snow Elf knowledge, kept at temperatures that preserve ancient texts."),
        ("frostmere-enclave", "Chamber of Thaw", "Healing Hall", "Where Snow Elf healers practice their restorative arts."),
        ("frostmere-enclave", "Frost-Veined Hall", "Gathering Place", "Central hall where the enclave's inhabitants meet and study."),
        ("frostmere-enclave", "The Crystalline Study", "Research Chamber", "Private chambers for advanced magical research."),
    ]
    
    # ===== GILDED UNDERWAY LOCATIONS =====
    underway_locations = [
        ("gilded-underway", "The Forgotten Depths", "Labor Hall", "Vast underground chamber where Mountain Elves work in darkness."),
        ("gilded-underway", "Ironbound Quarters", "Housing", "Cramped living spaces for those who build Yillhone's foundations."),
        ("gilded-underway", "The Hidden Shrine", "Secret Temple", "Concealed place of worship where Mountain Elves pray in secret."),
        ("gilded-underway", "Shadowmark Tunnel", "Passage", "Unofficial passage used to move goods and people unseen."),
    ]
    
    # ===== CRYSTAL HEART LOCATIONS =====
    heart_locations = [
        ("crystal-heart", "High Synod Chambers", "Government", "Where the ruling council of Selindori makes decisions that affect all elves."),
        ("crystal-heart", "Grand Temple of Seren", "Temple", "The central temple where all elves may worship—in their designated sections."),
        ("crystal-heart", "The Prismatic Market", "Marketplace", "Great market where goods from all districts are traded."),
        ("crystal-heart", "Seren's Touch", "Monument", "The exact spot where Seren's divine touch created the Crystal City."),
    ]
    
    # ===== SOLARATH LOCATIONS =====
    solarath_locations = [
        ("solarath", "Crownward Ring", "Noble District", "Where the highest Sun Elf families maintain their estates."),
        ("solarath", "Pilgrim's Halo", "Religious District", "Ring of temples and shrines surrounding the city's sacred center."),
        ("solarath", "The Blinding Courts", "Legal District", "Where Sun Elf justice is dispensed—swift and absolute."),
        ("solarath", "The Gilded Hymn", "Tavern", "Elite establishment where politics and pleasure intertwine."),
    ]
    
    # ===== THALENROOT LOCATIONS =====
    thalenroot_locations = [
        ("thalenroot", "Fen's Bastion", "Fortress", "Central military fortress grown from a single ancient tree."),
        ("thalenroot", "The Verdant Crucible", "Training Ground", "Where Forest Elf warriors are forged through brutal training."),
        ("thalenroot", "Warden-Commander's Hall", "Command Center", "Military headquarters where campaigns are planned."),
        ("thalenroot", "The Thornwatch Tavern", "Tavern", "Where off-duty soldiers drink and remember the fallen."),
    ]
    
    # ===== NAL'THERIS LOCATIONS =====
    naltheris_locations = [
        ("nal-theris", "The Tidemirror", "Sacred Site", "Perfectly still pool that reflects the Spirit King's will."),
        ("nal-theris", "Devdan's Wake", "Memorial", "Monument to the first Mist Elf who forged the water pact."),
        ("nal-theris", "Ritual Pools", "Ceremonial Site", "Where purification rituals cleanse body and spirit."),
        ("nal-theris", "The Veiled Sanctuary", "Temple", "Hidden temple accessible only to initiated Mist Elves."),
    ]
    
    # ===== ISENFELL LOCATIONS =====
    isenfell_locations = [
        ("isenfell", "Hall of Winter Psalms", "Temple", "Where Snow Elves honor the heavens that saved them from famine."),
        ("isenfell", "Frostward Athenaeum", "Library", "Great library containing millennia of accumulated knowledge."),
        ("isenfell", "The Healing Springs", "Hospital", "Warm springs infused with healing magic."),
        ("isenfell", "Winterheart Inn", "Inn", "Welcoming establishment offering warmth to travelers."),
    ]
    
    # ===== AER'CYR LOCATIONS =====
    aercyr_locations = [
        ("aer-cyr", "The Eyrie of Dragons", "Dragon Roost", "Where Sky Elf dragons rest between flights through the clouds."),
        ("aer-cyr", "The Zephyr Throne", "Throne Room", "Seat of power for the mysterious Sky Elf rulers."),
        ("aer-cyr", "Windweaver's Sanctuary", "Magic Academy", "Where Sky Elves learn to command the winds."),
        ("aer-cyr", "The Cloudwalk Markets", "Marketplace", "Trading platforms suspended between floating islands."),
        ("aer-cyr", "Storm's Edge Lookout", "Watchtower", "Highest point in Aer'Cyr, watching all below."),
        ("aer-cyr", "The Skyborn Roost", "Residential", "Where Sky Elf families make their homes among the clouds."),
        ("aer-cyr", "Temple of the Four Winds", "Temple", "Sacred site honoring the elemental forces Sky Elves command."),
        ("aer-cyr", "The Aether Archives", "Library", "Repository of Sky Elf knowledge, hidden from the world below."),
    ]
    
    # ===== TOWN LOCATIONS =====
    # Aurenviel
    aurenviel_locations = [
        ("aurenviel", "The Lesser Sanctum", "Temple", "Where acolytes perform their daily devotions."),
        ("aurenviel", "Shrine Keeper's Hall", "Administrative", "Coordinating the maintenance of countless holy sites."),
        ("aurenviel", "The Penitent's Walk", "Pilgrimage Route", "Path walked by those seeking absolution."),
    ]
    
    # Heliospan
    heliospan_locations = [
        ("heliospan", "The Golden Fields", "Farmland", "Vast agricultural terraces tended by enslaved elves."),
        ("heliospan", "Overseer's Tower", "Administration", "Where Sun Elf masters watch their workers."),
        ("heliospan", "The Harvest Temple", "Shrine", "Small temple blessing each year's crop—and those who died growing it."),
    ]
    
    # Oakspire
    oakspire_locations = [
        ("oakspire", "Youth Training Grounds", "Training Area", "Where children learn combat before they learn letters."),
        ("oakspire", "The Proving Oak", "Ceremonial Site", "Ancient tree where young warriors prove their worth."),
        ("oakspire", "Warrior's Rest", "Barracks", "Dormitories for trainees and their instructors."),
    ]
    
    # Greenwatch
    greenwatch_locations = [
        ("greenwatch", "The Watchwood Tower", "Watchtower", "Abandoned lookout post slowly being reclaimed by forest."),
        ("greenwatch", "Old Garrison", "Military Outpost", "Former military center, now home to a skeleton crew."),
        ("greenwatch", "Memorial Stones", "Monument", "Stones marking those who fell defending against Blood Elves."),
    ]
    
    # Barkhollow
    barkhollow_locations = [
        ("barkhollow", "Living Armor Workshop", "Craftshop", "Where master artisans grow armor from living wood."),
        ("barkhollow", "The Thorn Smithy", "Forge", "Creating weapons from nature's deadliest materials."),
        ("barkhollow", "Artisan's Grove", "Marketplace", "Where finished creations are displayed and sold."),
    ]
    
    # Silverflow
    silverflow_locations = [
        ("silverflow", "The Moonlit Docks", "Harbor", "Where fishing boats depart under Devdan's blessing."),
        ("silverflow", "The Silver Catch", "Market", "Daily fish market where the sea's bounty is sold."),
        ("silverflow", "Fishers' Shrine", "Shrine", "Small temple honoring the Spirit King of Water."),
    ]
    
    # Reedhaven
    reedhaven_locations = [
        ("reedhaven", "The Hidden Paths", "Maze", "Waterways designed to confuse and lose outsiders."),
        ("reedhaven", "Sanctuary Hall", "Community Center", "Heart of the hidden settlement."),
        ("reedhaven", "The Reed Weavers", "Craftshop", "Artisans who create from the marsh's bounty."),
    ]
    
    # Lowmist
    lowmist_locations = [
        ("lowmist", "The Trading Post", "Marketplace", "Where necessary commerce occurs with minimum trust."),
        ("lowmist", "Visitor's Quarters", "Inn", "Sparse accommodations for outsiders."),
        ("lowmist", "The Watcher's Lodge", "Guardhouse", "Where Mist Elves monitor all who enter."),
    ]
    
    # Snowmere
    snowmere_locations = [
        ("snowmere", "Ice-Glass Foundry", "Factory", "Where frozen beauty is crafted into art."),
        ("snowmere", "The Exile's Library", "Library", "Collection of works by scholars sent here in disgrace."),
        ("snowmere", "Frostbound Inn", "Inn", "Cold comfort for a cold place."),
    ]
    
    # Thawpoint
    thawpoint_locations = [
        ("thawpoint", "The Meeting Hall", "Diplomatic Center", "Neutral ground for delicate negotiations."),
        ("thawpoint", "Boundary Shrine", "Shrine", "Marking where frost meets mist."),
        ("thawpoint", "The Careful Tongue", "Inn", "Where diplomats rest between difficult conversations."),
    ]
    
    # Combine all location data
    all_location_data = (
        aurelion_locations + verdant_locations + veilwater_locations +
        frostmere_locations + underway_locations + heart_locations +
        solarath_locations + thalenroot_locations + naltheris_locations +
        isenfell_locations + aercyr_locations + aurenviel_locations +
        heliospan_locations + oakspire_locations + greenwatch_locations +
        barkhollow_locations + silverflow_locations + reedhaven_locations +
        lowmist_locations + snowmere_locations + thawpoint_locations
    )
    
    for city_slug, name, loc_type, desc in all_location_data:
        locations.append({
            "id": str(uuid4()),
            "nation": "selindori",
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


async def populate_selindori_data():
    """Populate Selindori nation data into the database."""
    print("🌿 Starting Selindori data population...")
    print("=" * 70)
    print("Kingdom of the First Elves - Where Seren's touch blessed the earth")
    print("=" * 70)
    
    locations = generate_locations()
    
    # Insert Yillhone districts
    print(f"\n🏛️ Inserting {len(YILLHONE_DISTRICTS)} Yillhone districts...")
    for district in YILLHONE_DISTRICTS:
        existing = await db.cities.find_one({"nation": district["nation"], "slug": district["slug"]})
        if existing:
            print(f"  ⏭️  District '{district['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(district)
            print(f"  ✅ Created district: {district['name']}")
    
    # Insert regional cities
    print(f"\n🏰 Inserting {len(SELINDORI_CITIES)} regional cities...")
    for city in SELINDORI_CITIES:
        existing = await db.cities.find_one({"nation": city["nation"], "slug": city["slug"]})
        if existing:
            print(f"  ⏭️  City '{city['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(city)
            print(f"  ✅ Created city: {city['name']}")
    
    # Insert towns
    print(f"\n🏘️ Inserting {len(SELINDORI_TOWNS)} towns...")
    for town in SELINDORI_TOWNS:
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
    
    total_cities = len(YILLHONE_DISTRICTS) + len(SELINDORI_CITIES) + len(SELINDORI_TOWNS)
    
    print("\n" + "=" * 70)
    print("✨ Selindori data population complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  - {len(YILLHONE_DISTRICTS)} Yillhone districts")
    print(f"  - {len(SELINDORI_CITIES)} regional cities")
    print(f"  - {len(SELINDORI_TOWNS)} towns")
    print(f"  - {len(locations)} locations")
    print(f"  - Total settlements: {total_cities}")


if __name__ == "__main__":
    asyncio.run(populate_selindori_data())
