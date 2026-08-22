"""
Populate Dhor-Kuldor holds, cities, towns, and locations into the database.
Dhor-Kuldor is the dwarven mountain kingdom - land of deep mines, mighty forges,
and ancient stone halls carved into the bones of the world.

Structure:
- 8 Holds (major fortress-cities, stored as 'City' entity_type)
- 24 Cities (3 per Hold)
- 48 Towns (2 per city/6 per Hold)
- ~288 Locations (4 per city + 4 per town = 12 per city area, ~36 per Hold)

Run this script to add all Dhor-Kuldor content.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# ============================================================================
# DHOR-KULDOR HOLDS (Major Fortress-Cities) - 8 Total
# ============================================================================
DHOR_KHULDOR_HOLDS = [
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "karak-vorn",
        "name": "Karak Vorn",
        "region": "The High Throne",
        "description": "The High King's Seat - greatest of all dwarven holds, carved into the heart of Mount Vornheim. Here sits the Throne of Ancestors.",
        "lore": "Karak Vorn is the oldest and most revered of all dwarven holds. Its halls stretch for miles beneath the mountain, illuminated by eternal runefires. The High King rules from the Chamber of Echoes, where the voices of all past kings whisper wisdom.",
        "faction": "High King's Court",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "kazad-drung",
        "name": "Kazad Drung",
        "region": "The Iron Deeps",
        "description": "The Iron Hold - master forges of Dhor-Kuldor where the finest weapons and armor are crafted. The air itself glows red from eternal furnaces.",
        "lore": "Kazad Drung sits atop the largest iron deposits ever discovered. Three great forges burn day and night: The Anvil of Kings, The Dragon's Breath, and The Runeforge. Master smiths here learn secrets passed down for ten thousand years.",
        "faction": "Forgemaster's Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "barak-varr",
        "name": "Barak Varr",
        "region": "The Sea Gate",
        "description": "The Sea Fortress - only dwarven port city, built into coastal cliffs. Ironclad ships patrol these waters, and the harbor is carved from living rock.",
        "lore": "Barak Varr defies dwarven tradition by embracing the sea. Its fleet of ironclad vessels dominates coastal trade. The harbor tunnels can shelter the entire fleet during storms or sieges.",
        "faction": "Admiral's Council",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "zhufbar",
        "name": "Zhufbar",
        "region": "The Engineer's Peak",
        "description": "The Engineer's Hold - center of dwarven innovation. Steam engines, clockwork mechanisms, and experimental weapons are developed here.",
        "lore": "Zhufbar is where tradition meets innovation. The Engineers Guild pushes boundaries while respecting ancestral knowledge. Gyrocopters were invented here, as were steam-powered drilling machines.",
        "faction": "Engineers Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "karak-azul",
        "name": "Karak Azul",
        "region": "The Gemstone Depths",
        "description": "The Jewel Hold - richest gem mines in all lands. Diamonds, rubies, and mythril veins snake through these tunnels.",
        "lore": "Karak Azul's wealth is legendary. The Gem Lords here control trade in precious stones across the continent. The Treasury of Ages contains jewels older than human civilization.",
        "faction": "Gem Lords",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "karak-kadrin",
        "name": "Karak Kadrin",
        "region": "The Slayer's Peak",
        "description": "The Slayer Keep - home of the Slayer Cult. Disgraced dwarves come here seeking honorable death against monsters.",
        "lore": "Karak Kadrin guards the most dangerous mountain pass. The Slayer King rules here, leading oath-bound warriors who seek redemption through glorious death in battle against the worst creatures of the deep.",
        "faction": "Slayer Cult",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "karaz-a-karak",
        "name": "Karaz-a-Karak",
        "region": "The Everpeak",
        "description": "The Eternal Hold - ancient repository of all dwarven knowledge. The Great Book of Grudges is kept here.",
        "lore": "Karaz-a-Karak is sacred to all dwarves. The Loremaster's Guild maintains records stretching back to the dawn age. The Hall of a Thousand Pillars contains carved histories of every dwarven clan.",
        "faction": "Loremaster's Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "karak-norn",
        "name": "Karak Norn",
        "region": "The Watchtower Mountains",
        "description": "The Warden Hold - fortress guarding the northern passes. Ever-vigilant against threats from the frozen wastes.",
        "lore": "Karak Norn stands eternal watch. Its rangers patrol the surface while deep garrisons guard against things that burrow from below. The Warning Bells can be heard across three mountain ranges.",
        "faction": "Warden's Watch",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# DHOR-KULDOR CITIES (3 per Hold) - 24 Total
# ============================================================================
DHOR_KHULDOR_CITIES = [
    # Karak Vorn Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "thronehall",
        "name": "Thronehall",
        "region": "Near Karak Vorn",
        "description": "Administrative center below the High King's chambers. Nobles and clan lords maintain residences here.",
        "lore": "Thronehall serves as the political heart of Dhor-Kuldor. Embassy halls from every hold line the Grand Avenue, and the Council of Clans meets in the Ancestor's Chamber.",
        "faction": "High King's Court",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "goldgate",
        "name": "Goldgate",
        "region": "Near Karak Vorn",
        "description": "Primary trading hub and entrance to the High Throne. Merchants from all nations pass through these gilded gates.",
        "lore": "Goldgate is where surface dwellers interact with dwarven society. The market caverns here stretch for miles, offering goods from every corner of the realm.",
        "faction": "Merchant Houses",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "deepwatch",
        "name": "Deepwatch",
        "region": "Near Karak Vorn",
        "description": "Military garrison protecting the lower depths. Elite warriors guard against threats from below.",
        "lore": "Deepwatch marks the boundary between civilized halls and the dangerous underdark. The Ironguard stationed here have held the line for three thousand years.",
        "faction": "Ironguard",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Kazad Drung Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "ironforge",
        "name": "Ironforge",
        "region": "Near Kazad Drung",
        "description": "The weapon-smithing district. Every blade destined for war is born in these fires.",
        "lore": "Ironforge produces the majority of Dhor-Kuldor's military equipment. The rhythmic hammering never ceases, and the glow of molten metal lights streets at all hours.",
        "faction": "Weaponsmiths Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "runehammer",
        "name": "Runehammer",
        "region": "Near Kazad Drung",
        "description": "Where runesmiths enchant weapons and armor. Magical forges burn with eldritch flames.",
        "lore": "Runehammer is where mundane metal becomes magical. Only those who have served fifty years as regular smiths may apply to learn runecraft here.",
        "faction": "Runesmiths",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "sootholm",
        "name": "Sootholm",
        "region": "Near Kazad Drung",
        "description": "Worker's district and ore processing center. The foundation upon which the forges depend.",
        "lore": "Sootholm processes raw ore into workable metal. Foundry workers here labor in shifts, feeding the insatiable appetite of the great forges above.",
        "faction": "Foundry Workers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Barak Varr Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "anchorhold",
        "name": "Anchorhold",
        "region": "Near Barak Varr",
        "description": "The shipyard district. Ironclad vessels are constructed and maintained in these sea caves.",
        "lore": "Anchorhold's dry docks can service twelve ironclads simultaneously. Engineers here combine dwarven metalwork with nautical engineering.",
        "faction": "Shipwrights Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "tidegate",
        "name": "Tidegate",
        "region": "Near Barak Varr",
        "description": "Customs and trade processing center. All goods entering by sea pass through here.",
        "lore": "Tidegate's inspectors are legendary for their thoroughness. Contraband rarely makes it past their scrutiny, and tariffs are calculated to the copper piece.",
        "faction": "Harbor Masters",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "saltstone",
        "name": "Saltstone",
        "region": "Near Barak Varr",
        "description": "Fishing and food processing district. The sea's bounty is preserved and distributed from here.",
        "lore": "Saltstone processes seafood for the entire kingdom. The preservation techniques developed here keep fish fresh for years in the deep holds.",
        "faction": "Fisher's Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Zhufbar Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "geartown",
        "name": "Geartown",
        "region": "Near Zhufbar",
        "description": "Center of clockwork innovation. Mechanical wonders are designed and built here.",
        "lore": "Geartown's workshops produce everything from pocket watches to mining automata. The clicking and whirring of machinery is constant.",
        "faction": "Clockworkers Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "steamhall",
        "name": "Steamhall",
        "region": "Near Zhufbar",
        "description": "Steam engine production and power generation. Great boilers drive the mountain's machinery.",
        "lore": "Steamhall's central boiler is the size of a small mountain. Steam pipes distribute power throughout the engineer's district.",
        "faction": "Steam Engineers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "sparkstone",
        "name": "Sparkstone",
        "region": "Near Zhufbar",
        "description": "Experimental weapons testing facility. New inventions are proved here before deployment.",
        "lore": "Sparkstone is technically a safe distance from other settlements - 'technically' because explosions still sometimes reach the lower tunnels.",
        "faction": "Weapons Testers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Azul Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "gemheart",
        "name": "Gemheart",
        "region": "Near Karak Azul",
        "description": "Gem cutting and jewelry district. Master jewelers create works of unmatched beauty.",
        "lore": "Gemheart's artisans can cut a diamond so perfectly it captures starlight. Their jewelry adorns royalty across every nation.",
        "faction": "Jeweler's Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "mythrildeep",
        "name": "Mythrildeep",
        "region": "Near Karak Azul",
        "description": "The mythril mines. Most precious metal in existence is extracted from these dangerous depths.",
        "lore": "Mythrildeep's miners work the most valuable and dangerous seams. Cave-ins and gas pockets make this work deadly, but the rewards are immense.",
        "faction": "Mythril Miners",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "vaultward",
        "name": "Vaultward",
        "region": "Near Karak Azul",
        "description": "Treasury and banking district. Wealth from across the kingdom is stored and managed here.",
        "lore": "Vaultward's banks hold accounts for nations. The Great Vault contains treasures accumulated over ten thousand years of dwarven prosperity.",
        "faction": "Vault Keepers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Kadrin Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "oathstone",
        "name": "Oathstone",
        "region": "Near Karak Kadrin",
        "description": "Where slayers take their oaths. The sacred stone has witnessed ten thousand vows of death.",
        "lore": "Oathstone is where dwarves come to become slayers. They shave their heads, dye their crests orange, and swear to seek death against the most terrible foes.",
        "faction": "Oath Keepers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "trollbane",
        "name": "Trollbane",
        "region": "Near Karak Kadrin",
        "description": "Forward operating base against mountain monsters. Hunting parties depart from here.",
        "lore": "Trollbane earned its name after a legendary battle against a troll horde. Trophy skulls from that battle still line the entrance hall.",
        "faction": "Monster Hunters",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "grimbrew",
        "name": "Grimbrew",
        "region": "Near Karak Kadrin",
        "description": "Famous for the strongest ales in Dhor-Kuldor. Slayers drink deep before their final quests.",
        "lore": "Grimbrew's ales can knock out an ogre. Slayers traditionally drink their fill here before embarking on their death-seeking quests.",
        "faction": "Brewmasters",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karaz-a-Karak Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "scrollheim",
        "name": "Scrollheim",
        "region": "Near Karaz-a-Karak",
        "description": "The great library district. Every dwarven record is copied and stored here.",
        "lore": "Scrollheim contains the largest collection of written works in Dhor-Kuldor. Scribes spend lifetimes copying and preserving ancient texts.",
        "faction": "Scribes Guild",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "grudgehold",
        "name": "Grudgehold",
        "region": "Near Karaz-a-Karak",
        "description": "Where grudges are recorded and tracked. The secondary Book of Grudges is maintained here.",
        "lore": "Grudgehold's clerks document every wrong done to dwarves. Some grudges here date back thousands of years, still waiting to be settled.",
        "faction": "Grudge Keepers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "ancestorhall",
        "name": "Ancestorhall",
        "region": "Near Karaz-a-Karak",
        "description": "Temple district honoring the ancestor gods. Priests commune with ancient spirits.",
        "lore": "Ancestorhall's temples echo with prayers to Grungni, Valaya, and Grimnir. The ancestor spirits are said to walk these halls during sacred festivals.",
        "faction": "Ancestor Priests",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Norn Cities
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "northgate",
        "name": "Northgate",
        "region": "Near Karak Norn",
        "description": "The first line of defense against northern threats. Massive gates seal the mountain passes.",
        "lore": "Northgate's defenses have never been breached. The gates themselves are ten feet thick, reinforced with runic wards against giants and trolls.",
        "faction": "Gate Wardens",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "frostwatch",
        "name": "Frostwatch",
        "region": "Near Karak Norn",
        "description": "Ranger outpost monitoring the frozen wastes. Early warning against invasions.",
        "lore": "Frostwatch's rangers can survive weeks in the frozen wilderness. Their reports have saved the kingdom from surprise attacks countless times.",
        "faction": "Frost Rangers",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "bellkeep",
        "name": "Bellkeep",
        "region": "Near Karak Norn",
        "description": "Houses the Warning Bells. When these ring, all Dhor-Kuldor mobilizes for war.",
        "lore": "Bellkeep's bells are enchanted to carry across mountain ranges. They have rung only three times in recorded history - each time heralding existential threats.",
        "faction": "Bell Wardens",
        "image_url": None,
        "entity_type": "City",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# DHOR-KULDOR TOWNS (2 per City) - 48 Total
# ============================================================================
DHOR_KHULDOR_TOWNS = [
    # Karak Vorn Towns (under Thronehall, Goldgate, Deepwatch)
    # Thronehall Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "clanmoot",
        "name": "Clanmoot",
        "region": "Near Thronehall",
        "description": "Where lesser clan lords maintain their residences and conduct business.",
        "lore": "Clanmoot hosts representatives from every minor clan. Political deals are made in smoky taverns and ancestral halls.",
        "faction": "Minor Clans",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "heraldsgate",
        "name": "Heraldsgate",
        "region": "Near Thronehall",
        "description": "Administrative center for royal announcements and census records.",
        "lore": "Every birth, death, marriage, and grudge in Dhor-Kuldor is ultimately recorded here. The bureaucracy is legendary.",
        "faction": "Royal Heralds",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Goldgate Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "copperway",
        "name": "Copperway",
        "region": "Near Goldgate",
        "description": "Lower market district for common goods and daily necessities.",
        "lore": "Copperway serves the everyday needs of the common dwarf. Food, tools, and household goods fill these bustling tunnels.",
        "faction": "Traders Union",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "foreignquarter",
        "name": "Foreignquarter",
        "region": "Near Goldgate",
        "description": "Where non-dwarven visitors reside and conduct business. Carefully watched.",
        "lore": "Foreignquarter is the only place outsiders are permitted to stay overnight. Human, elven, and halfling merchants maintain permanent offices here.",
        "faction": "Foreign Relations",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Deepwatch Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "shieldbreak",
        "name": "Shieldbreak",
        "region": "Near Deepwatch",
        "description": "Training grounds for Ironguard recruits. Harsh discipline forges elite warriors.",
        "lore": "Shieldbreak's drill sergeants are legendary for their cruelty. Those who survive training become the finest defenders in the realm.",
        "faction": "Ironguard Trainers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "darkdelve",
        "name": "Darkdelve",
        "region": "Near Deepwatch",
        "description": "Scout outpost monitoring underdark passages. First to encounter threats from below.",
        "lore": "Darkdelve's scouts venture into passages no sane dwarf would enter. They map the ever-changing tunnels and track monster movements.",
        "faction": "Deep Scouts",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Kazad Drung Towns (under Ironforge, Runehammer, Sootholm)
    # Ironforge Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "bladequarter",
        "name": "Bladequarter",
        "region": "Near Ironforge",
        "description": "Specialized in sword and axe production. Master bladesmiths work here.",
        "lore": "Bladequarter's smiths argue endlessly about the superiority of axes versus swords. The debate has lasted three thousand years.",
        "faction": "Bladesmiths",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "armordelve",
        "name": "Armordelve",
        "region": "Near Ironforge",
        "description": "Armor smithing district. Plate, chain, and scale armor are crafted here.",
        "lore": "Armordelve produces the heaviest armor in the known world. A dwarf in full plate from here can survive almost anything.",
        "faction": "Armorsmiths",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Runehammer Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "glyphhold",
        "name": "Glyphhold",
        "region": "Near Runehammer",
        "description": "Where apprentice runesmiths study the ancient craft of inscription.",
        "lore": "Glyphhold's students spend decades learning single runes. The craft requires patience beyond what most races possess.",
        "faction": "Rune Apprentices",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "emberquarter",
        "name": "Emberquarter",
        "region": "Near Runehammer",
        "description": "Produces magical fuel and maintains the runeforges' eternal flames.",
        "lore": "Emberquarter's workers handle materials that would incinerate lesser beings. Fire resistance is a job requirement.",
        "faction": "Flame Keepers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Sootholm Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "coalpit",
        "name": "Coalpit",
        "region": "Near Sootholm",
        "description": "Mining town extracting coal and other fuels for the forges.",
        "lore": "Coalpit's miners work in perpetual darkness, extracting the black gold that powers dwarven industry.",
        "faction": "Coal Miners",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "slagheap",
        "name": "Slagheap",
        "region": "Near Sootholm",
        "description": "Waste processing and metal reclamation center. Nothing is wasted.",
        "lore": "Slagheap extracts every usable bit of metal from foundry waste. Dwarven efficiency means nothing truly goes to waste.",
        "faction": "Reclamation Guild",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Barak Varr Towns (under Anchorhold, Tidegate, Saltstone)
    # Anchorhold Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "chainworks",
        "name": "Chainworks",
        "region": "Near Anchorhold",
        "description": "Produces anchors, chains, and heavy ship components.",
        "lore": "Chainworks' anchor chains can hold against kraken pulls. Each link is individually tested.",
        "faction": "Chain Forgers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "mast-hollow",
        "name": "Mast Hollow",
        "region": "Near Anchorhold",
        "description": "Where iron masts and rigging are constructed for the ironclad fleet.",
        "lore": "Mast Hollow's engineers have solved the puzzle of metal sails. Their designs make dwarven ships faster than wooden vessels.",
        "faction": "Mast Engineers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Tidegate Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "customshold",
        "name": "Customshold",
        "region": "Near Tidegate",
        "description": "Processing center for incoming cargo. Inspectors examine every crate.",
        "lore": "Customshold's inspectors have found contraband hidden in ways that defy belief. Their training takes decades.",
        "faction": "Customs Inspectors",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "weighstation",
        "name": "Weighstation",
        "region": "Near Tidegate",
        "description": "Where cargo is weighed and tariffs calculated with dwarven precision.",
        "lore": "Weighstation's scales are accurate to the grain. Merchants who dispute measurements rarely win.",
        "faction": "Weighmasters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Saltstone Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "netmenders",
        "name": "Netmenders",
        "region": "Near Saltstone",
        "description": "Crafts and repairs the massive nets used by the dwarven fishing fleet.",
        "lore": "Netmenders' nets can catch entire schools of fish. The weaving patterns are closely guarded secrets.",
        "faction": "Net Weavers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "brinecaves",
        "name": "Brinecaves",
        "region": "Near Saltstone",
        "description": "Natural salt caves used for food preservation on a massive scale.",
        "lore": "Brinecaves can preserve food for centuries. The natural salt content is perfect for keeping fish and meat.",
        "faction": "Preservers Guild",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Zhufbar Towns (under Geartown, Steamhall, Sparkstone)
    # Geartown Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "springworks",
        "name": "Springworks",
        "region": "Near Geartown",
        "description": "Produces springs, coils, and tension mechanisms for clockwork devices.",
        "lore": "Springworks' products range from watch springs to siege weapon tensioners. Precision is everything.",
        "faction": "Spring Crafters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "cogholm",
        "name": "Cogholm",
        "region": "Near Geartown",
        "description": "Specializes in gear production. Every size from fingernail to wagon wheel.",
        "lore": "Cogholm's gears mesh perfectly. A single tooth out of alignment is grounds for melting down the entire batch.",
        "faction": "Gear Cutters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Steamhall Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "pipetown",
        "name": "Pipetown",
        "region": "Near Steamhall",
        "description": "Maintains the vast network of steam pipes distributing power.",
        "lore": "Pipetown's workers can navigate miles of pipe networks by sound alone. A hissing leak is their constant enemy.",
        "faction": "Pipe Fitters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "boilerward",
        "name": "Boilerward",
        "region": "Near Steamhall",
        "description": "Where new boilers are constructed and old ones repaired.",
        "lore": "Boilerward's smiths specialize in pressure vessels. A failed boiler is a catastrophe, so quality is paramount.",
        "faction": "Boiler Smiths",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Sparkstone Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "boomtown",
        "name": "Boomtown",
        "region": "Near Sparkstone",
        "description": "Explosives testing and production. Built to contain catastrophic failures.",
        "lore": "Boomtown has been rebuilt seventeen times. Each reconstruction incorporates lessons from the previous explosion.",
        "faction": "Explosive Experts",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "targetrange",
        "name": "Targetrange",
        "region": "Near Sparkstone",
        "description": "Testing grounds for ranged weapons. The mountain itself serves as a backstop.",
        "lore": "Targetrange's testing has carved new caves into the mountain. Some weapons tested here should never have been invented.",
        "faction": "Weapons Testers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Azul Towns (under Gemheart, Mythrildeep, Vaultward)
    # Gemheart Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "cuttersrow",
        "name": "Cuttersrow",
        "region": "Near Gemheart",
        "description": "Where apprentice gem cutters learn their trade on lesser stones.",
        "lore": "Cuttersrow's training programs last decades. A master cutter can split a diamond along fault lines invisible to others.",
        "faction": "Gem Apprentices",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "polishers-hall",
        "name": "Polishers Hall",
        "region": "Near Gemheart",
        "description": "Final finishing of gems to perfect brilliance. The final step before sale.",
        "lore": "Polishers Hall's experts can make any gem shine like captured starlight. Their techniques are trade secrets.",
        "faction": "Gem Polishers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Mythrildeep Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "silverseam",
        "name": "Silverseam",
        "region": "Near Mythrildeep",
        "description": "Where silver and lesser precious metals are mined alongside mythril.",
        "lore": "Silverseam's miners often find mythril veins while following silver. The discovery bonus makes this dangerous work worthwhile.",
        "faction": "Silver Miners",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "gaslamp",
        "name": "Gaslamp",
        "region": "Near Mythrildeep",
        "description": "Safety station monitoring gas levels in the deep mines. Canaries are raised here.",
        "lore": "Gaslamp's warning systems have saved thousands of lives. Their gas-detecting canaries are specially bred for sensitivity.",
        "faction": "Gas Wardens",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Vaultward Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "countersdeep",
        "name": "Countersdeep",
        "region": "Near Vaultward",
        "description": "Where clerks count and verify currency. Every coin is examined.",
        "lore": "Countersdeep's clerks can spot counterfeit coins by weight and ring alone. Their accuracy is legendary.",
        "faction": "Coin Counters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "locksmith-lane",
        "name": "Locksmith Lane",
        "region": "Near Vaultward",
        "description": "Creates the complex locks protecting dwarven vaults. Impenetrable security.",
        "lore": "Locksmith Lane's products guard treasuries across the world. Breaking one is considered impossible.",
        "faction": "Locksmiths Guild",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Kadrin Towns (under Oathstone, Trollbane, Grimbrew)
    # Oathstone Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "shavershall",
        "name": "Shavershall",
        "region": "Near Oathstone",
        "description": "Where new slayers have their heads shaved and crests prepared.",
        "lore": "Shavershall's barbers use blessed razors. The shaving ceremony is sacred to the Slayer Cult.",
        "faction": "Cult Barbers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "dyeworks",
        "name": "Dyeworks",
        "region": "Near Oathstone",
        "description": "Produces the iconic orange dye for slayer crests. The recipe is secret.",
        "lore": "Dyeworks' orange dye never fades. The formula has been unchanged for five thousand years.",
        "faction": "Dye Masters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Trollbane Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "trophyhall",
        "name": "Trophyhall",
        "region": "Near Trollbane",
        "description": "Where monster trophies are prepared and displayed. Proof of kills.",
        "lore": "Trophyhall's taxidermists can preserve anything. Dragon heads and giant skulls line the walls.",
        "faction": "Trophy Keepers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "huntcamp",
        "name": "Huntcamp",
        "region": "Near Trollbane",
        "description": "Staging area for monster hunting expeditions. Supplies and planning.",
        "lore": "Huntcamp organizes hunts ranging from single trolls to dragon lairs. The planning is meticulous.",
        "faction": "Hunt Masters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Grimbrew Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "hopvault",
        "name": "Hopvault",
        "region": "Near Grimbrew",
        "description": "Storage for rare hops and brewing ingredients. Climate controlled caves.",
        "lore": "Hopvault stores ingredients from across the world. Some hops here are older than human civilizations.",
        "faction": "Hop Masters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "barrelwright",
        "name": "Barrelwright",
        "region": "Near Grimbrew",
        "description": "Where the massive ale barrels are constructed. Cooperage of legend.",
        "lore": "Barrelwright's coopers craft barrels that can age ale for centuries. The wood selection alone takes years.",
        "faction": "Coopers Guild",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karaz-a-Karak Towns (under Scrollheim, Grudgehold, Ancestorhall)
    # Scrollheim Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "inkwell",
        "name": "Inkwell",
        "region": "Near Scrollheim",
        "description": "Produces inks and writing materials. Special formulas last millennia.",
        "lore": "Inkwell's inks are guaranteed to remain legible for ten thousand years. The recipes are closely guarded.",
        "faction": "Ink Makers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "parchment-hall",
        "name": "Parchment Hall",
        "region": "Near Scrollheim",
        "description": "Creates and stores vast quantities of writing materials.",
        "lore": "Parchment Hall's vellum is made from cave-dwelling creatures. It resists decay better than surface materials.",
        "faction": "Parchment Makers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Grudgehold Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "witnessward",
        "name": "Witnessward",
        "region": "Near Grudgehold",
        "description": "Where witnesses are interviewed and grudges verified. Evidence is gathered here.",
        "lore": "Witnessward's interrogators extract truth without violence. Their techniques are psychological.",
        "faction": "Grudge Investigators",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "settlementsquare",
        "name": "Settlementsquare",
        "region": "Near Grudgehold",
        "description": "Where grudges are formally settled through combat or compensation.",
        "lore": "Settlementsquare has witnessed thousands of honor duels. The stones are stained with centuries of blood.",
        "faction": "Settlement Masters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Ancestorhall Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "tombward",
        "name": "Tombward",
        "region": "Near Ancestorhall",
        "description": "Maintains the vast catacombs where dwarven dead are interred.",
        "lore": "Tombward's caretakers know every tomb in the catacombs. Some families' crypts stretch for miles.",
        "faction": "Tomb Keepers",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "reliquary",
        "name": "Reliquary",
        "region": "Near Ancestorhall",
        "description": "Stores sacred relics and artifacts of the ancestor gods.",
        "lore": "Reliquary contains items touched by the ancestor gods themselves. Pilgrims come from every hold to pay respects.",
        "faction": "Relic Wardens",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Karak Norn Towns (under Northgate, Frostwatch, Bellkeep)
    # Northgate Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "wallwatch",
        "name": "Wallwatch",
        "region": "Near Northgate",
        "description": "Barracks for the gate garrison. Warriors rotate through constant watches.",
        "lore": "Wallwatch's soldiers serve year-long rotations. The isolation and cold make this a prestigious hardship posting.",
        "faction": "Gate Guards",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "warmstone",
        "name": "Warmstone",
        "region": "Near Northgate",
        "description": "Heated shelters for those traveling through the frozen passes.",
        "lore": "Warmstone's heated halls save hundreds of lives yearly. The geothermal vents are carefully maintained.",
        "faction": "Warming Guild",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Frostwatch Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "icehold",
        "name": "Icehold",
        "region": "Near Frostwatch",
        "description": "Supply depot for rangers operating in the frozen wastes.",
        "lore": "Icehold's supplies are specially preserved for extreme cold. Rangers resupply here before long patrols.",
        "faction": "Ranger Supply",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "signalpost",
        "name": "Signalpost",
        "region": "Near Frostwatch",
        "description": "Communication relay using mirrors and fires. Messages cross mountains.",
        "lore": "Signalpost's operators can relay messages across the entire mountain range in hours. The code is unbreakable.",
        "faction": "Signal Corps",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    # Bellkeep Towns
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "bellwright",
        "name": "Bellwright",
        "region": "Near Bellkeep",
        "description": "Where replacement bells are cast and maintained. Each is enchanted.",
        "lore": "Bellwright's craftsmen create bells that ring with magical resonance. The casting process takes years.",
        "faction": "Bell Casters",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "dhor-kuldor",
        "slug": "listenpost",
        "name": "Listenpost",
        "region": "Near Bellkeep",
        "description": "Where watchers monitor for signs of invasion. Early warning is critical.",
        "lore": "Listenpost's watchers train their senses to supernatural levels. They can hear armies marching from miles away.",
        "faction": "Listeners",
        "image_url": None,
        "entity_type": "Town",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# ============================================================================
# DHOR-KULDOR LOCATIONS - 4 per Hold, 4 per City, 4 per Town
# ============================================================================

def generate_hold_locations():
    """Generate locations for each Hold (4 per hold = 32 total)"""
    locations = []
    
    # Karak Vorn Hold Locations
    hold_locations = [
        ("karak-vorn", "Chamber of Echoes", "Throne Room", "The High King's throne room where the voices of all past kings whisper wisdom to the ruler."),
        ("karak-vorn", "Ancestor's Gate", "Great Gate", "The massive main entrance to Karak Vorn, carved with the faces of legendary kings."),
        ("karak-vorn", "Hall of Kings", "Royal Crypt", "Where all High Kings are entombed. Their stone likenesses line the endless corridor."),
        ("karak-vorn", "Runefire Beacon", "Lighthouse", "An eternal flame visible across the kingdom, symbol of dwarven unity and strength."),
        
        # Kazad Drung Hold Locations
        ("kazad-drung", "Anvil of Kings", "Master Forge", "The greatest forge in Dhor-Kuldor. Only masterwork weapons are crafted here."),
        ("kazad-drung", "Dragon's Breath", "Furnace Hall", "Massive furnaces hot enough to melt adamantine. The heat never dies."),
        ("kazad-drung", "The Runeforge", "Enchanting Forge", "Where runic weapons are bound with magical power. Ancient secrets are guarded here."),
        ("kazad-drung", "Ironmaster's Hall", "Guild Hall", "Where the Forgemaster's Guild conducts business and adjudicates quality disputes."),
        
        # Barak Varr Hold Locations
        ("barak-varr", "Admiral's Tower", "Command Center", "Overlooks the entire harbor. The Admiral's Council directs the fleet from here."),
        ("barak-varr", "Kraken Gate", "Sea Gate", "Massive sea doors that can seal the harbor against storms or enemy fleets."),
        ("barak-varr", "Ironclad Dock", "Primary Shipyard", "Where the mighty ironclad warships are constructed and launched."),
        ("barak-varr", "Navigator's Guild", "Guild Hall", "Charts, maps, and sailing knowledge accumulated over millennia are stored here."),
        
        # Zhufbar Hold Locations
        ("zhufbar", "Innovation Chamber", "Research Hall", "Where new inventions are proposed and debated. Many revolutionary devices began here."),
        ("zhufbar", "Gyrocopter Hangar", "Aircraft Facility", "Houses the dwarven air fleet. Pilots train and maintain their craft here."),
        ("zhufbar", "Patent Office", "Archive", "Every dwarven invention is registered here. Disputes over credit are common."),
        ("zhufbar", "Prototype Hall", "Workshop", "Active development of new devices. Explosions are not uncommon."),
        
        # Karak Azul Hold Locations
        ("karak-azul", "Treasury of Ages", "Vault", "The greatest collection of gems and precious metals in existence."),
        ("karak-azul", "Gem Throne", "Ceremonial Hall", "Where the Gem Lords conduct audiences. The throne is encrusted with diamonds."),
        ("karak-azul", "Crystal Caverns", "Natural Wonder", "Natural cave formations of stunning beauty. Some crystals glow with inner light."),
        ("karak-azul", "Appraisal Hall", "Trading Floor", "Where gems are valued and traded. Fortunes change hands daily."),
        
        # Karak Kadrin Hold Locations
        ("karak-kadrin", "Slayer Shrine", "Temple", "Sacred to Grimnir. Slayers pray here before seeking their doom."),
        ("karak-kadrin", "Hall of Doom", "Memorial", "Lists every slayer who has fallen. The names stretch back millennia."),
        ("karak-kadrin", "Monster Gate", "Exit Point", "The gate through which slayers depart to seek their deaths."),
        ("karak-kadrin", "Slayer King's Seat", "Throne Room", "Where the Slayer King holds court and approves new oath-takers."),
        
        # Karaz-a-Karak Hold Locations
        ("karaz-a-karak", "Great Book Chamber", "Archive", "Where the Great Book of Grudges is kept. Access is strictly controlled."),
        ("karaz-a-karak", "Hall of a Thousand Pillars", "History Hall", "Each pillar carved with the history of a dwarven clan."),
        ("karaz-a-karak", "Loremaster's Sanctum", "Library", "The personal chambers of the chief Loremaster. Knowledge beyond measure."),
        ("karaz-a-karak", "Memory Stone", "Artifact", "A massive stone said to contain the memories of the first dwarves."),
        
        # Karak Norn Hold Locations
        ("karak-norn", "Warning Bell Tower", "Watchtower", "Houses the great bells that can mobilize all Dhor-Kuldor for war."),
        ("karak-norn", "Northern Watch", "Observation Post", "Highest point in the hold. Watchers scan the frozen wastes constantly."),
        ("karak-norn", "Warden's Hall", "Command Center", "Where defense of the northern passes is coordinated."),
        ("karak-norn", "Ice Gate", "Defensive Structure", "The last line of defense against invasion from the frozen north."),
    ]
    
    for city_slug, name, loc_type, desc in hold_locations:
        locations.append({
            "id": str(uuid4()),
            "nation": "dhor-kuldor",
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

def generate_city_locations():
    """Generate locations for each city (4 per city = 96 total)"""
    locations = []
    
    city_locations = [
        # Thronehall (Near Karak Vorn)
        ("thronehall", "Council Chamber", "Meeting Hall", "Where the Council of Clans debates policy and disputes."),
        ("thronehall", "Embassy Row", "Diplomatic Quarter", "Foreign embassy halls for every major hold."),
        ("thronehall", "Noble's Promenade", "Avenue", "Where noble families display their wealth and status."),
        ("thronehall", "Petitioner's Hall", "Waiting Room", "Where those seeking audience with the High King wait, sometimes for years."),
        
        # Goldgate (Near Karak Vorn)
        ("goldgate", "Great Market", "Trading Hall", "Largest market in Dhor-Kuldor. Goods from across the world."),
        ("goldgate", "Money Changers", "Exchange", "Currency from every nation is exchanged here at fair rates."),
        ("goldgate", "Merchant's Lodge", "Inn", "Premium accommodations for wealthy traders."),
        ("goldgate", "Contract Hall", "Legal Office", "Where trade agreements are witnessed and sealed."),
        
        # Deepwatch (Near Karak Vorn)
        ("deepwatch", "Ironguard Barracks", "Military Base", "Houses the elite warriors guarding the lower depths."),
        ("deepwatch", "Armory of the Deep", "Arsenal", "Weapons and armor specifically designed for underdark combat."),
        ("deepwatch", "Watch Commander's Post", "Command Center", "Coordinates all patrols into the dangerous tunnels."),
        ("deepwatch", "Memorial Wall", "Monument", "Names of all who fell defending against threats from below."),
        
        # Ironforge (Near Kazad Drung)
        ("ironforge", "Master Smith's Hall", "Workshop", "Where the most skilled weapon smiths practice their craft."),
        ("ironforge", "Blade Testing Range", "Testing Facility", "Every weapon must pass rigorous testing here."),
        ("ironforge", "Steel Tempering Vats", "Industrial Facility", "Massive vats for quenching and tempering steel."),
        ("ironforge", "Apprentice Forges", "Training Area", "Where young smiths learn the fundamentals."),
        
        # Runehammer (Near Kazad Drung)
        ("runehammer", "Rune Library", "Archive", "Contains knowledge of every known rune and their combinations."),
        ("runehammer", "Master's Forge", "Enchanting Workshop", "Where master runesmiths create legendary weapons."),
        ("runehammer", "Testing Chamber", "Magical Testing", "Safely tests enchanted items before they leave the city."),
        ("runehammer", "Rune Vault", "Secure Storage", "Stores dangerous runes too powerful for normal use."),
        
        # Sootholm (Near Kazad Drung)
        ("sootholm", "Ore Processing Hall", "Refinery", "Where raw ore is separated and refined."),
        ("sootholm", "Worker's Canteen", "Dining Hall", "Feeds thousands of foundry workers daily."),
        ("sootholm", "Shift Master's Office", "Administration", "Coordinates the never-ending work rotations."),
        ("sootholm", "Medical Station", "Hospital", "Treats burns, injuries, and foundry-related ailments."),
        
        # Anchorhold (Near Barak Varr)
        ("anchorhold", "Dry Dock One", "Shipyard", "Can service the largest ironclads in the fleet."),
        ("anchorhold", "Fitting Hall", "Assembly", "Where ships receive their final equipment and weapons."),
        ("anchorhold", "Anchor Smithy", "Forge", "Produces the massive anchors for dwarven ships."),
        ("anchorhold", "Launch Ramp", "Harbor Feature", "Engineered slope for launching newly built vessels."),
        
        # Tidegate (Near Barak Varr)
        ("tidegate", "Inspector's Office", "Customs", "Where all incoming cargo is examined and taxed."),
        ("tidegate", "Quarantine Cave", "Medical", "Isolates potentially diseased cargo and passengers."),
        ("tidegate", "Tariff Hall", "Administration", "Calculates and collects import duties."),
        ("tidegate", "Contraband Vault", "Storage", "Confiscated illegal goods await judgment here."),
        
        # Saltstone (Near Barak Varr)
        ("saltstone", "Great Smokehouse", "Processing", "Smokes fish and meat for long-term preservation."),
        ("saltstone", "Ice Caves", "Cold Storage", "Natural caves kept frozen for fresh fish storage."),
        ("saltstone", "Fisher's Market", "Market", "Fresh catch sold directly to buyers."),
        ("saltstone", "Net Mending Hall", "Workshop", "Where damaged fishing equipment is repaired."),
        
        # Geartown (Near Zhufbar)
        ("geartown", "Precision Workshop", "Manufacturing", "Creates the most delicate clockwork components."),
        ("geartown", "Assembly Hall", "Factory", "Where complex mechanisms are put together."),
        ("geartown", "Quality Control", "Testing", "Every device is tested before leaving."),
        ("geartown", "Inventor's Quarter", "Research Area", "Where engineers develop new designs."),
        
        # Steamhall (Near Zhufbar)
        ("steamhall", "Central Boiler", "Power Generation", "The massive boiler powering the entire district."),
        ("steamhall", "Pressure Control", "Engineering", "Monitors and maintains safe steam pressure."),
        ("steamhall", "Turbine Hall", "Power Plant", "Converts steam to mechanical power."),
        ("steamhall", "Emergency Vents", "Safety System", "Can release pressure in case of emergency."),
        
        # Sparkstone (Near Zhufbar)
        ("sparkstone", "Blast Chamber", "Testing Facility", "Reinforced room for explosive testing."),
        ("sparkstone", "Observation Bunker", "Protected Viewing", "Safe location to watch tests."),
        ("sparkstone", "Recovery Ward", "Medical", "Treats injuries from testing accidents."),
        ("sparkstone", "Prototype Storage", "Secure Storage", "Dangerous devices awaiting testing."),
        
        # Gemheart (Near Karak Azul)
        ("gemheart", "Master Cutter's Studio", "Workshop", "Where the finest gems are cut."),
        ("gemheart", "Display Gallery", "Showroom", "Finished pieces displayed for wealthy buyers."),
        ("gemheart", "Sorting Room", "Processing", "Raw gems are categorized by quality."),
        ("gemheart", "Setting Workshop", "Jewelry Making", "Where gems are set into jewelry."),
        
        # Mythrildeep (Near Karak Azul)
        ("mythrildeep", "Primary Shaft", "Mine Entrance", "Main access to the mythril veins."),
        ("mythrildeep", "Rescue Station", "Emergency Services", "Prepared for cave-ins and accidents."),
        ("mythrildeep", "Ore Cart Terminal", "Transportation", "Where ore carts are loaded and dispatched."),
        ("mythrildeep", "Miner's Rest", "Recovery Area", "Where exhausted miners recuperate."),
        
        # Vaultward (Near Karak Azul)
        ("vaultward", "Central Bank", "Financial Institution", "Primary banking facility for all holds."),
        ("vaultward", "Deposit Hall", "Secure Storage", "Where wealth is deposited and withdrawn."),
        ("vaultward", "Auditor's Office", "Accounting", "Tracks every transaction in the realm."),
        ("vaultward", "Secure Transfer", "Transportation", "Handles movement of large wealth amounts."),
        
        # Oathstone (Near Karak Kadrin)
        ("oathstone", "Oath Circle", "Ceremonial Area", "Where slayer oaths are formally taken."),
        ("oathstone", "Witness Hall", "Ceremony Hall", "Where witnesses observe oath-taking."),
        ("oathstone", "Preparation Chamber", "Ritual Room", "Where initiates prepare for their oath."),
        ("oathstone", "Record Hall", "Archive", "Documents every oath ever taken."),
        
        # Trollbane (Near Karak Kadrin)
        ("trollbane", "Hunter's Hall", "Guild Hall", "Where hunting parties are organized."),
        ("trollbane", "Armory", "Weapons Storage", "Specialized weapons for different monsters."),
        ("trollbane", "Map Room", "Intelligence", "Charts monster territories and migration."),
        ("trollbane", "Trophy Display", "Exhibition", "Famous kills displayed for inspiration."),
        
        # Grimbrew (Near Karak Kadrin)
        ("grimbrew", "Master Brewer's Hall", "Brewery", "Where the strongest ales are crafted."),
        ("grimbrew", "Tasting Room", "Tavern", "Sample the latest brews before they're released."),
        ("grimbrew", "Aging Caverns", "Storage", "Where ales mature for decades."),
        ("grimbrew", "Ingredient Vault", "Secure Storage", "Rare brewing ingredients carefully preserved."),
        
        # Scrollheim (Near Karaz-a-Karak)
        ("scrollheim", "Grand Reading Room", "Library", "Scholars study ancient texts here."),
        ("scrollheim", "Copying Chamber", "Scriptorium", "Where scribes duplicate important works."),
        ("scrollheim", "Restoration Workshop", "Conservation", "Damaged documents are carefully repaired."),
        ("scrollheim", "Index Hall", "Catalog", "Master index of all known dwarven texts."),
        
        # Grudgehold (Near Karaz-a-Karak)
        ("grudgehold", "Recording Chamber", "Archive", "Where new grudges are formally entered."),
        ("grudgehold", "Evidence Vault", "Storage", "Proof supporting recorded grudges."),
        ("grudgehold", "Settlement Court", "Legal", "Where grudges are adjudicated."),
        ("grudgehold", "Satisfaction Hall", "Ceremony", "Where settled grudges are formally closed."),
        
        # Ancestorhall (Near Karaz-a-Karak)
        ("ancestorhall", "Temple of Grungni", "Temple", "Dedicated to the ancestor god of mining and smithing."),
        ("ancestorhall", "Shrine of Valaya", "Shrine", "Honors the protector goddess of hearth and healing."),
        ("ancestorhall", "Grimnir's Altar", "Altar", "Where warriors pray before battle."),
        ("ancestorhall", "Communion Chamber", "Ritual Room", "Priests communicate with ancestor spirits here."),
        
        # Northgate (Near Karak Norn)
        ("northgate", "Gate Control", "Command Post", "Controls the massive defensive gates."),
        ("northgate", "Arrow Galleries", "Defensive Position", "Positions for defenders to rain death on attackers."),
        ("northgate", "Murder Holes", "Defensive Feature", "Drop boiling oil and rocks on invaders."),
        ("northgate", "Rally Point", "Military", "Where defenders gather during attacks."),
        
        # Frostwatch (Near Karak Norn)
        ("frostwatch", "Ranger Headquarters", "Base", "Coordinates all ranger patrols."),
        ("frostwatch", "Weather Station", "Observatory", "Predicts dangerous storms."),
        ("frostwatch", "Survival Training", "Training Facility", "Teaches cold weather survival."),
        ("frostwatch", "Communication Hub", "Signals", "Relay point for messages across the wastes."),
        
        # Bellkeep (Near Karak Norn)
        ("bellkeep", "Bell Chamber", "Mechanism", "Houses the enchanted warning bells."),
        ("bellkeep", "Ringer's Quarters", "Living Quarters", "Where bell operators live and train."),
        ("bellkeep", "Maintenance Bay", "Workshop", "Keeps the bells in perfect condition."),
        ("bellkeep", "Sound Testing Room", "Testing", "Verifies bell acoustics regularly."),
    ]
    
    for city_slug, name, loc_type, desc in city_locations:
        locations.append({
            "id": str(uuid4()),
            "nation": "dhor-kuldor",
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

def generate_town_locations():
    """Generate locations for each town (4 per town = 192 total)"""
    locations = []
    
    # Define all town location data
    town_locations_data = [
        # Clanmoot (Near Thronehall)
        ("clanmoot", "Clan Hall", "Meeting Place", "Where minor clan representatives gather."),
        ("clanmoot", "Negotiation Rooms", "Private Chambers", "Soundproof rooms for sensitive discussions."),
        ("clanmoot", "Clan Registry", "Archive", "Records of every clan's history and membership."),
        ("clanmoot", "Hospitality Suite", "Lodging", "Accommodations for visiting clan lords."),
        
        # Heraldsgate (Near Thronehall)
        ("heraldsgate", "Census Office", "Records", "Tracks population across the kingdom."),
        ("heraldsgate", "Proclamation Hall", "Announcement", "Where royal decrees are read aloud."),
        ("heraldsgate", "Messenger Post", "Communication", "Dispatches official communications."),
        ("heraldsgate", "Archive Wing", "Storage", "Historical proclamations preserved."),
        
        # Copperway (Near Goldgate)
        ("copperway", "Food Hall", "Market", "Fresh provisions sold daily."),
        ("copperway", "Tool Vendors", "Market", "Quality tools for every trade."),
        ("copperway", "Common Goods", "Market", "Everyday items for common folk."),
        ("copperway", "Bargain Corner", "Market", "Discounted and second-hand items."),
        
        # Foreignquarter (Near Goldgate)
        ("foreignquarter", "Human Embassy", "Diplomatic", "Human merchants and diplomats reside here."),
        ("foreignquarter", "Elven Pavilion", "Diplomatic", "Rare elven visitors stay in this elegant space."),
        ("foreignquarter", "Mixed Tavern", "Inn", "One of few places where races mix freely."),
        ("foreignquarter", "Translation Office", "Services", "Interpreters for foreign visitors."),
        
        # Shieldbreak (Near Deepwatch)
        ("shieldbreak", "Training Yard", "Military", "Recruits drill endlessly here."),
        ("shieldbreak", "Obstacle Course", "Training", "Tests endurance and agility."),
        ("shieldbreak", "Combat Arena", "Training", "Sparring matches and qualification fights."),
        ("shieldbreak", "Barracks Hall", "Housing", "Bunks for trainees."),
        
        # Darkdelve (Near Deepwatch)
        ("darkdelve", "Scout Briefing", "Intelligence", "Pre-patrol briefings and debriefings."),
        ("darkdelve", "Equipment Store", "Supply", "Specialized gear for deep exploration."),
        ("darkdelve", "Recovery Station", "Medical", "Treatment for scout injuries."),
        ("darkdelve", "Map Archive", "Intelligence", "Constantly updated tunnel maps."),
        
        # Bladequarter (Near Ironforge)
        ("bladequarter", "Sword Masters Hall", "Workshop", "Elite sword smiths work here."),
        ("bladequarter", "Axe Smithy", "Workshop", "Traditional dwarven axes forged here."),
        ("bladequarter", "Display Room", "Showroom", "Masterwork weapons displayed."),
        ("bladequarter", "Testing Dummies", "Testing Area", "Weapons tested on armored targets."),
        
        # Armordelve (Near Ironforge)
        ("armordelve", "Plate Workshop", "Manufacturing", "Heavy plate armor production."),
        ("armordelve", "Chain Hall", "Manufacturing", "Chainmail crafted link by link."),
        ("armordelve", "Fitting Room", "Services", "Custom armor fitting."),
        ("armordelve", "Repair Station", "Services", "Battle-damaged armor restored."),
        
        # Glyphhold (Near Runehammer)
        ("glyphhold", "Student Quarters", "Housing", "Apprentice runesmiths live here."),
        ("glyphhold", "Practice Forges", "Training", "Safe forges for learning basic runes."),
        ("glyphhold", "Lecture Hall", "Education", "Master runesmiths teach here."),
        ("glyphhold", "Examination Room", "Testing", "Where advancement tests are given."),
        
        # Emberquarter (Near Runehammer)
        ("emberquarter", "Fuel Storage", "Storage", "Magical fuels safely contained."),
        ("emberquarter", "Mixing Chamber", "Production", "Alchemical fuels prepared here."),
        ("emberquarter", "Distribution Hub", "Logistics", "Fuel distributed to forges."),
        ("emberquarter", "Safety Station", "Emergency", "Fire suppression equipment."),
        
        # Coalpit (Near Sootholm)
        ("coalpit", "Mine Entrance", "Access", "Main shaft into the coal seams."),
        ("coalpit", "Cart Depot", "Transportation", "Ore carts loaded and dispatched."),
        ("coalpit", "Miner's Hall", "Rest Area", "Break room for coal miners."),
        ("coalpit", "Ventilation Control", "Safety", "Manages air flow in the mines."),
        
        # Slagheap (Near Sootholm)
        ("slagheap", "Sorting Facility", "Processing", "Waste separated for reclamation."),
        ("slagheap", "Remelting Furnace", "Processing", "Metal extracted from slag."),
        ("slagheap", "Disposal Chutes", "Waste Management", "True waste safely disposed."),
        ("slagheap", "Recovery Warehouse", "Storage", "Reclaimed materials stored."),
        
        # Chainworks (Near Anchorhold)
        ("chainworks", "Link Forges", "Manufacturing", "Individual chain links forged."),
        ("chainworks", "Assembly Floor", "Manufacturing", "Links joined into chains."),
        ("chainworks", "Testing Rig", "Quality Control", "Chains tested to breaking point."),
        ("chainworks", "Finished Goods", "Storage", "Completed chains await delivery."),
        
        # Mast Hollow (Near Anchorhold)
        ("mast-hollow", "Iron Mill", "Manufacturing", "Iron shaped into mast components."),
        ("mast-hollow", "Rigging Shop", "Manufacturing", "Metal rigging produced here."),
        ("mast-hollow", "Assembly Bay", "Construction", "Masts assembled and tested."),
        ("mast-hollow", "Design Office", "Engineering", "New mast designs developed."),
        
        # Customshold (Near Tidegate)
        ("customshold", "Inspection Hall", "Processing", "Cargo opened and examined."),
        ("customshold", "Documentation Office", "Administration", "Paperwork processed."),
        ("customshold", "Appeals Court", "Legal", "Disputes over tariffs resolved."),
        ("customshold", "Storage Caves", "Temporary Storage", "Goods awaiting clearance."),
        
        # Weighstation (Near Tidegate)
        ("weighstation", "Great Scales", "Equipment", "Massive scales for cargo."),
        ("weighstation", "Calculation Office", "Administration", "Tariffs computed precisely."),
        ("weighstation", "Witness Post", "Legal", "Third parties verify weights."),
        ("weighstation", "Calibration Lab", "Maintenance", "Scales kept perfectly accurate."),
        
        # Netmenders (Near Saltstone)
        ("netmenders", "Weaving Hall", "Manufacturing", "Nets created on huge looms."),
        ("netmenders", "Repair Workshop", "Services", "Damaged nets restored."),
        ("netmenders", "Material Storage", "Supply", "Rope and twine stored here."),
        ("netmenders", "Design Room", "Development", "New net patterns created."),
        
        # Brinecaves (Near Saltstone)
        ("brinecaves", "Salt Extraction", "Processing", "Natural salt harvested."),
        ("brinecaves", "Preservation Pools", "Processing", "Fish and meat preserved."),
        ("brinecaves", "Packing Station", "Processing", "Preserved food prepared for shipping."),
        ("brinecaves", "Quality Testing", "Quality Control", "Preservation verified."),
        
        # Springworks (Near Geartown)
        ("springworks", "Coiling Room", "Manufacturing", "Springs wound to specification."),
        ("springworks", "Tempering Furnace", "Processing", "Springs heat-treated."),
        ("springworks", "Testing Bench", "Quality Control", "Spring tension verified."),
        ("springworks", "Precision Store", "Storage", "Finished springs organized."),
        
        # Cogholm (Near Geartown)
        ("cogholm", "Cutting Floor", "Manufacturing", "Gears cut from metal blanks."),
        ("cogholm", "Finishing Room", "Processing", "Teeth precision ground."),
        ("cogholm", "Inspection Station", "Quality Control", "Every tooth measured."),
        ("cogholm", "Inventory Hall", "Storage", "Thousands of gear sizes stored."),
        
        # Pipetown (Near Steamhall)
        ("pipetown", "Pipe Storage", "Supply", "Miles of replacement pipe."),
        ("pipetown", "Repair Station", "Services", "Emergency pipe repair."),
        ("pipetown", "Pressure Monitors", "Control", "Tracks pressure throughout system."),
        ("pipetown", "Emergency Response", "Safety", "Quick response to leaks."),
        
        # Boilerward (Near Steamhall)
        ("boilerward", "Construction Hall", "Manufacturing", "New boilers built."),
        ("boilerward", "Repair Bay", "Services", "Boilers overhauled."),
        ("boilerward", "Testing Chamber", "Quality Control", "Pressure testing."),
        ("boilerward", "Parts Storage", "Supply", "Replacement components."),
        
        # Boomtown (Near Sparkstone)
        ("boomtown", "Mixing Lab", "Production", "Explosive compounds prepared."),
        ("boomtown", "Storage Bunkers", "Storage", "Explosives safely stored."),
        ("boomtown", "Blast Site", "Testing", "Controlled detonation area."),
        ("boomtown", "Safety Briefing", "Training", "Mandatory safety training."),
        
        # Targetrange (Near Sparkstone)
        ("targetrange", "Firing Positions", "Testing", "Where weapons are fired."),
        ("targetrange", "Target Field", "Testing", "Various targets at all ranges."),
        ("targetrange", "Observation Post", "Analysis", "Watch and record results."),
        ("targetrange", "Armory", "Storage", "Weapons awaiting testing."),
        
        # Cuttersrow (Near Gemheart)
        ("cuttersrow", "Practice Benches", "Training", "Apprentices learn basics."),
        ("cuttersrow", "Material Supply", "Supply", "Practice stones provided."),
        ("cuttersrow", "Instructor Offices", "Administration", "Master cutters teach."),
        ("cuttersrow", "Progress Hall", "Exhibition", "Best student work displayed."),
        
        # Polishers Hall (Near Gemheart)
        ("polishers-hall", "Polishing Stations", "Manufacturing", "Gems brought to brilliance."),
        ("polishers-hall", "Inspection Room", "Quality Control", "Final quality check."),
        ("polishers-hall", "Tool Maintenance", "Support", "Polishing equipment maintained."),
        ("polishers-hall", "Completion Office", "Administration", "Work orders finalized."),
        
        # Silverseam (Near Mythrildeep)
        ("silverseam", "Silver Shaft", "Mining", "Primary silver mine access."),
        ("silverseam", "Ore Sorting", "Processing", "Silver separated from rock."),
        ("silverseam", "Miner's Rest", "Rest Area", "Break area for miners."),
        ("silverseam", "Equipment Shed", "Supply", "Mining tools stored."),
        
        # Gaslamp (Near Mythrildeep)
        ("gaslamp", "Canary Cages", "Safety", "Gas-detecting birds housed."),
        ("gaslamp", "Monitoring Station", "Safety", "Gas levels tracked."),
        ("gaslamp", "Ventilation Control", "Safety", "Air flow managed."),
        ("gaslamp", "Emergency Equipment", "Safety", "Rescue gear ready."),
        
        # Countersdeep (Near Vaultward)
        ("countersdeep", "Counting Hall", "Operations", "Coins counted and verified."),
        ("countersdeep", "Verification Room", "Quality Control", "Authenticity confirmed."),
        ("countersdeep", "Secure Transport", "Logistics", "Counted funds moved safely."),
        ("countersdeep", "Clerk Quarters", "Housing", "Counters live on-site."),
        
        # Locksmith Lane (Near Vaultward)
        ("locksmith-lane", "Design Studio", "Development", "New lock designs created."),
        ("locksmith-lane", "Manufacturing Floor", "Production", "Locks assembled."),
        ("locksmith-lane", "Key Cutting", "Services", "Master keys created."),
        ("locksmith-lane", "Testing Vault", "Quality Control", "Locks tested against picking."),
        
        # Shavershall (Near Oathstone)
        ("shavershall", "Shaving Chairs", "Ceremonial", "Traditional head shaving."),
        ("shavershall", "Crest Styling", "Services", "Orange crests formed."),
        ("shavershall", "Preparation Room", "Ritual", "Mental preparation before oath."),
        ("shavershall", "Barber Quarters", "Housing", "Cult barbers reside here."),
        
        # Dyeworks (Near Oathstone)
        ("dyeworks", "Mixing Vats", "Production", "Sacred dye prepared."),
        ("dyeworks", "Color Testing", "Quality Control", "Shade verified."),
        ("dyeworks", "Application Room", "Services", "Dye applied to crests."),
        ("dyeworks", "Ingredient Vault", "Storage", "Secret ingredients secured."),
        
        # Trophyhall (Near Trollbane)
        ("trophyhall", "Preparation Room", "Processing", "Trophies cleaned and prepared."),
        ("trophyhall", "Mounting Workshop", "Services", "Trophies mounted for display."),
        ("trophyhall", "Display Gallery", "Exhibition", "Impressive kills on show."),
        ("trophyhall", "Record Office", "Archive", "Kill records maintained."),
        
        # Huntcamp (Near Trollbane)
        ("huntcamp", "Planning Room", "Operations", "Hunts strategized."),
        ("huntcamp", "Supply Depot", "Logistics", "Hunting gear issued."),
        ("huntcamp", "Departure Gate", "Access", "Hunters set out from here."),
        ("huntcamp", "Return Station", "Services", "Returning hunters processed."),
        
        # Hopvault (Near Grimbrew)
        ("hopvault", "Storage Caves", "Storage", "Temperature-controlled caves."),
        ("hopvault", "Inventory Office", "Management", "Tracks all ingredients."),
        ("hopvault", "Sampling Room", "Quality Control", "Ingredient quality checked."),
        ("hopvault", "Receiving Dock", "Logistics", "New ingredients arrive."),
        
        # Barrelwright (Near Grimbrew)
        ("barrelwright", "Stave Workshop", "Manufacturing", "Barrel staves cut and shaped."),
        ("barrelwright", "Assembly Floor", "Manufacturing", "Barrels constructed."),
        ("barrelwright", "Charring Station", "Processing", "Barrel interiors charred."),
        ("barrelwright", "Finished Goods", "Storage", "Completed barrels stored."),
        
        # Inkwell (Near Scrollheim)
        ("inkwell", "Mixing Lab", "Production", "Inks formulated."),
        ("inkwell", "Color Matching", "Quality Control", "Consistent shades ensured."),
        ("inkwell", "Bottling Station", "Packaging", "Ink bottled for use."),
        ("inkwell", "Ingredient Store", "Storage", "Rare pigments secured."),
        
        # Parchment Hall (Near Scrollheim)
        ("parchment-hall", "Processing Room", "Manufacturing", "Hides become parchment."),
        ("parchment-hall", "Drying Racks", "Processing", "Parchment dried."),
        ("parchment-hall", "Cutting Station", "Finishing", "Sheets cut to size."),
        ("parchment-hall", "Storage Vaults", "Storage", "Finished parchment stored."),
        
        # Witnessward (Near Grudgehold)
        ("witnessward", "Interview Rooms", "Investigation", "Witnesses questioned."),
        ("witnessward", "Waiting Hall", "Processing", "Witnesses wait their turn."),
        ("witnessward", "Record Room", "Archive", "Testimonies recorded."),
        ("witnessward", "Verification Office", "Investigation", "Statements cross-checked."),
        
        # Settlementsquare (Near Grudgehold)
        ("settlementsquare", "Duel Ring", "Arena", "Honor combat takes place."),
        ("settlementsquare", "Witness Stands", "Viewing", "Observers watch duels."),
        ("settlementsquare", "Medic Station", "Medical", "Wounds treated."),
        ("settlementsquare", "Settlement Office", "Administration", "Outcomes recorded."),
        
        # Tombward (Near Ancestorhall)
        ("tombward", "Entrance Hall", "Access", "Main catacomb entrance."),
        ("tombward", "Guide Station", "Services", "Escorts to specific tombs."),
        ("tombward", "Eternal Flames", "Maintenance", "Tomb lights maintained."),
        ("tombward", "Caretaker Quarters", "Housing", "Tomb keepers live here."),
        
        # Reliquary (Near Ancestorhall)
        ("reliquary", "Display Chamber", "Exhibition", "Sacred relics displayed."),
        ("reliquary", "Meditation Room", "Spiritual", "Pilgrims pray here."),
        ("reliquary", "Guardian Post", "Security", "Relics protected."),
        ("reliquary", "Offering Hall", "Ritual", "Gifts to ancestors left."),
        
        # Wallwatch (Near Northgate)
        ("wallwatch", "Guard Barracks", "Housing", "Gate guards live here."),
        ("wallwatch", "Duty Roster", "Administration", "Watch schedules managed."),
        ("wallwatch", "Equipment Issue", "Supply", "Gear distributed."),
        ("wallwatch", "Rest Hall", "Rest Area", "Off-duty relaxation."),
        
        # Warmstone (Near Northgate)
        ("warmstone", "Heated Halls", "Shelter", "Warm refuge for travelers."),
        ("warmstone", "Hot Springs", "Amenity", "Natural warm baths."),
        ("warmstone", "Meal Hall", "Services", "Hot food served."),
        ("warmstone", "Recovery Beds", "Medical", "Frostbite treatment."),
        
        # Icehold (Near Frostwatch)
        ("icehold", "Supply Warehouse", "Storage", "Cold-weather supplies."),
        ("icehold", "Equipment Issue", "Services", "Gear distributed to rangers."),
        ("icehold", "Warm Room", "Rest Area", "Heated space for rangers."),
        ("icehold", "Briefing Hall", "Operations", "Patrol briefings."),
        
        # Signalpost (Near Frostwatch)
        ("signalpost", "Mirror Array", "Communication", "Signal mirrors positioned."),
        ("signalpost", "Beacon Tower", "Communication", "Fire signals lit."),
        ("signalpost", "Code Room", "Operations", "Messages encoded/decoded."),
        ("signalpost", "Operator Quarters", "Housing", "Signal operators live here."),
        
        # Bellwright (Near Bellkeep)
        ("bellwright", "Casting Pit", "Manufacturing", "Bells cast from bronze."),
        ("bellwright", "Tuning Chamber", "Processing", "Bell tones perfected."),
        ("bellwright", "Enchanting Room", "Magic", "Bells given magical resonance."),
        ("bellwright", "Storage Hall", "Storage", "Completed bells stored."),
        
        # Listenpost (Near Bellkeep)
        ("listenpost", "Listening Chamber", "Operations", "Silence maintained for hearing."),
        ("listenpost", "Report Office", "Administration", "Observations recorded."),
        ("listenpost", "Training Room", "Training", "Listeners trained."),
        ("listenpost", "Rest Quarters", "Housing", "Listeners live here."),
    ]
    
    for city_slug, name, loc_type, desc in town_locations_data:
        locations.append({
            "id": str(uuid4()),
            "nation": "dhor-kuldor",
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


async def populate_dhor_kuldor_data():
    """Populate Dhor-Kuldor holds, cities, towns, and locations into the database."""
    print("⛏️ Starting Dhor-Kuldor data population...")
    print("=" * 70)
    
    # Generate all location data
    hold_locations = generate_hold_locations()
    city_locations = generate_city_locations()
    town_locations = generate_town_locations()
    
    # Insert holds
    print(f"\n🏔️ Inserting {len(DHOR_KHULDOR_HOLDS)} holds (major fortress-cities)...")
    for hold in DHOR_KHULDOR_HOLDS:
        existing = await db.cities.find_one({"nation": hold["nation"], "slug": hold["slug"]})
        if existing:
            print(f"  ⏭️  Hold '{hold['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(hold)
            print(f"  ✅ Created hold: {hold['name']}")
    
    # Insert cities
    print(f"\n🏛️ Inserting {len(DHOR_KHULDOR_CITIES)} cities...")
    for city in DHOR_KHULDOR_CITIES:
        existing = await db.cities.find_one({"nation": city["nation"], "slug": city["slug"]})
        if existing:
            print(f"  ⏭️  City '{city['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(city)
            print(f"  ✅ Created city: {city['name']}")
    
    # Insert towns
    print(f"\n🏘️ Inserting {len(DHOR_KHULDOR_TOWNS)} towns...")
    for town in DHOR_KHULDOR_TOWNS:
        existing = await db.cities.find_one({"nation": town["nation"], "slug": town["slug"]})
        if existing:
            print(f"  ⏭️  Town '{town['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(town)
            print(f"  ✅ Created town: {town['name']}")
    
    # Insert hold locations
    print(f"\n📍 Inserting {len(hold_locations)} hold locations...")
    for location in hold_locations:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    # Insert city locations
    print(f"\n📍 Inserting {len(city_locations)} city locations...")
    for location in city_locations:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    # Insert town locations
    print(f"\n📍 Inserting {len(town_locations)} town locations...")
    for location in town_locations:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    total_cities = len(DHOR_KHULDOR_HOLDS) + len(DHOR_KHULDOR_CITIES) + len(DHOR_KHULDOR_TOWNS)
    total_locations = len(hold_locations) + len(city_locations) + len(town_locations)
    
    print("\n" + "=" * 70)
    print("✨ Dhor-Kuldor data population complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  - {len(DHOR_KHULDOR_HOLDS)} holds (major fortress-cities)")
    print(f"  - {len(DHOR_KHULDOR_CITIES)} cities")
    print(f"  - {len(DHOR_KHULDOR_TOWNS)} towns")
    print(f"  - {len(hold_locations)} hold locations")
    print(f"  - {len(city_locations)} city locations")
    print(f"  - {len(town_locations)} town locations")
    print(f"  - Total entities: {total_cities}")
    print(f"  - Total locations: {total_locations}")
    print("\nNext steps:")
    print("  1. Generate images for holds, cities, towns, and locations")
    print("  2. Test navigation: Nations → Dhor-Kuldor → Cities/Towns → Locations")
    print("  3. Test roleplay in new locations")


if __name__ == "__main__":
    asyncio.run(populate_dhor_kuldor_data())
