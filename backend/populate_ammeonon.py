"""
Populate Ammeonon cities, towns, and locations into the database.
Run this script to add all Ammeonon content.
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

# Ammeonon Cities Data
AMMEONON_CITIES = [
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "wymroost",
        "name": "Wymroost",
        "region": "Central Coast",
        "description": "The largest port city on the continent, capable of housing 150 trading vessels. A bustling hub of trade, magic, and culinary delights.",
        "lore": "Founded as Hielgcrom by King Quentin Blackburn in 1200, Wymroost has evolved into a majestic port city. Its expansive docks connect Ammeonon to distant lands, while vibrant markets overflow with exotic goods from every corner of the continent.",
        "faction": "Vritra Clan",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "invrasil",
        "name": "Invrasil",
        "region": "Southern Border",
        "description": "The City of Mages - home to the prestigious Wemorth and Ofeline Academies. The strongest mages on the continent reside here.",
        "lore": "Invrasil stands as a testament to magical prowess. Its streets are filled with arcane wonders, and the annual Magic Competition at Veneficus Stadium draws spellcasters from across the realm. Hastburn Alley offers rare magical artifacts to those who seek them.",
        "faction": "Mage Councils",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "crares",
        "name": "Crares",
        "region": "Eastern Coast",
        "description": "The Shimmering Bastion - a coastal trade city known for sea-silk, glasswork, and architecture that gleams like precious gems.",
        "lore": "Ruled by a Merchant-Consulate of seven trade lords, Crares dominates maritime commerce. Its buildings shimmer with enchanted sea-glass tiles, and the Sapphire Oath privateers enforce sea law across the eastern waters.",
        "faction": "Merchant-Consulate",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "plia",
        "name": "Plia",
        "region": "Western Forests",
        "description": "The Verdant Heart - a forest city built into massive ancient trees. Haven of druids, herbalists, and nature magic.",
        "lore": "Led by the Circle of Nine Roots, Plia is a living city where homes grow from tree hollows and streets are woven moss paths. The Bloomwatch rangers protect its borders, while the Heartgrove Conclave guides all matters of life and balance.",
        "faction": "Circle of Nine Roots",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "folis",
        "name": "Folis",
        "region": "Northern Mountains",
        "description": "The Ember-Forged City - a mountainous forge-city built near magma vents. Home to master blacksmiths, mercenaries, and fire mages.",
        "lore": "Ruled by the Forge Council, Folis is where the greatest weapons in Ammeonon are crafted. Lava channels provide heat and light, while the Crucible Spire channels elemental flame. The legendary Firelord's Anvil is said to be blessed by a fire titan.",
        "faction": "Forge Council",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "yhul",
        "name": "Yhul",
        "region": "Far North",
        "description": "City of Moon and Memory - a snow-covered city of marble known for moon rituals, divination, and dream studies.",
        "lore": "Governed by the Moon-Synod, Yhul is where dreams are studied and memories preserved. The Dreambinders patrol nightmares, while the Vault of Echoes stores recorded dreams of generations past. Time here is measured not by clocks, but by moon phases.",
        "faction": "Moon-Synod",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# Ammeonon Towns Data
AMMEONON_TOWNS = [
    # Wymroost Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "skooma",
        "name": "Skooma",
        "region": "Near Wymroost",
        "description": "The Brewer's Haven - renowned for exceptional ales, meads, and spirits. Home to master brewers whose craft dates back centuries.",
        "lore": "Located 15 miles from Wymroost, Skooma's brewing traditions are legendary. The annual Brewfest draws beer enthusiasts from across the continent. The town's strategic location near Wymroost allows its brews to be shipped worldwide.",
        "faction": "Brewer's Guild",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "azure",
        "name": "Azure",
        "region": "Near Wymroost",
        "description": "The Town of Flowers - a picturesque town renowned for its vibrant floral cultivation and the grand annual Flower Festival.",
        "lore": "Named after the azure blue river flowing through its center, this town is a haven of color and fragrance. The Azurians are master horticulturists, cultivating everything from delicate roses to exotic orchids.",
        "faction": "Flower Cultivators",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Invrasil Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "xynnar",
        "name": "Xynnar",
        "region": "Near Invrasil",
        "description": "A hidden gem of arcane research and runecraft. Streets glow with magical energy and floating crystals.",
        "lore": "Ruled by arcane scholars, Xynnar is a sanctuary for mages seeking knowledge of lost civilizations. Runesmiths craft enchanted sigils, and floating lanterns light streets filled with mystical portals.",
        "faction": "Arcane Scholars",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "naporia",
        "name": "Naporia",
        "region": "Near Invrasil",
        "description": "Home to the largest library in the land, preserving histories, poetry, and arcane lore spanning millennia.",
        "lore": "A haven for scholars, Naporia's towering libraries contain countless ancient tomes. Illuminators craft stunning manuscripts while scribes work tirelessly to preserve forgotten knowledge.",
        "faction": "Scholar's Assembly",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Crares Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "kellamoor",
        "name": "Kellamoor",
        "region": "Near Crares",
        "description": "A fishing village famous for harvesting enchanted coral used in magical crafting and jewelry.",
        "lore": "Kellamoor's divers brave dangerous waters to retrieve rare coral that glows with inner light. These materials are highly sought after by enchanters and artisans throughout Ammeonon.",
        "faction": "Coral Divers Guild",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "mirelight",
        "name": "Mirelight",
        "region": "Near Crares",
        "description": "A swampy outpost known for rare alchemical herbs that grow nowhere else in the realm.",
        "lore": "Despite its murky surroundings, Mirelight produces the most potent alchemical ingredients. Herbalists brave the marshes to collect plants with extraordinary healing and magical properties.",
        "faction": "Herbalist Collective",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Plia Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "lindleaf",
        "name": "Lindleaf",
        "region": "Near Plia",
        "description": "Known for weaving exquisite silks from treeworms. Their fabrics shimmer with natural magic.",
        "lore": "Lindleaf's weavers have perfected the art of harvesting silk from rare treeworms. The resulting fabric is prized by nobles and mages alike for its beauty and magical conductivity.",
        "faction": "Silk Weavers",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "oakmarsh",
        "name": "Oakmarsh",
        "region": "Near Plia",
        "description": "Produces rare incense from rotwood trees, used in sacred rituals and meditation.",
        "lore": "Oakmarsh specializes in crafting incense from ancient rotwood. The smoke is said to open minds to spiritual visions and enhance druidic rituals throughout the forest realm.",
        "faction": "Incense Crafters",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Folis Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "dravuns-pike",
        "name": "Dravun's Pike",
        "region": "Near Folis",
        "description": "A dwarfhold mine producing soul-iron, a rare metal capable of holding enchantments indefinitely.",
        "lore": "Deep beneath the mountains, dwarven miners extract soul-iron from ancient veins. This precious metal is essential for crafting the most powerful magical weapons and armor.",
        "faction": "Dwarven Miners",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "corthmill",
        "name": "Corthmill",
        "region": "Near Folis",
        "description": "Specializes in enchanted rivets and clockwork parts used in advanced machinery and constructs.",
        "lore": "Corthmill's tinkers create the tiny components that power golems and mechanical wonders. Their precision work is essential to artificers throughout Ammeonon.",
        "faction": "Artificer's Workshop",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Yhul Towns
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "mistren",
        "name": "Mistren",
        "region": "Near Yhul",
        "description": "A town known for taming and training frost elk, magnificent creatures adapted to the frozen north.",
        "lore": "Mistren's tamers have a mystical bond with frost elk. These majestic animals serve as mounts, companions, and symbols of the northern wilderness.",
        "faction": "Elk Tamers",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "slug": "hollowend",
        "name": "Hollowend",
        "region": "Near Yhul",
        "description": "Guards an ancient dream rift where reality and the dream realm blur. Home to brave wardens.",
        "lore": "Hollowend sits at the edge of a tear between worlds. Dream-wardens stand eternal vigil, preventing nightmares from spilling into reality while studying the rift's mysteries.",
        "faction": "Dream Wardens",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# City Locations
CITY_LOCATIONS = [
    # Wymroost Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "wymroost",
        "slug": "grand-docks",
        "name": "The Grand Docks",
        "location_type": "Port District",
        "description": "Expansive docks capable of housing 150 trading vessels. The constant arrival of ships from distant lands creates a vibrant, bustling atmosphere.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "wymroost",
        "slug": "central-marketplace",
        "name": "Central Marketplace",
        "location_type": "Trade District",
        "description": "Thousands of vendors sell goods from every corner of the continent. A feast for the senses with vibrant colors, exotic scents, and constant haggling.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "wymroost",
        "slug": "golden-tavern-district",
        "name": "Golden Tavern District",
        "location_type": "Entertainment Quarter",
        "description": "A lively district filled with taverns, inns, and clubs. Raucous laughter, merry songs, and clinking glasses echo through the night.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "wymroost",
        "slug": "magical-marketplace",
        "name": "Magical Marketplace",
        "location_type": "Arcane District",
        "description": "Enchanting items, spell books, and mystical artifacts are readily available. Renowned enchanters share their knowledge with those willing to pay.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Invrasil Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "invrasil",
        "slug": "wemorth-academy",
        "name": "Wemorth Academy",
        "location_type": "Magical School",
        "description": "Grand stone walls and ancient libraries dedicated to elemental magic. One of the most prestigious arcane schools on the continent.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "invrasil",
        "slug": "ofeline-academy",
        "name": "Ofeline Academy",
        "location_type": "Magical School",
        "description": "Nestled in lush gardens and tranquil courtyards, this academy specializes in illusion and enchantment magic.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "invrasil",
        "slug": "veneficus-stadium",
        "name": "Veneficus Stadium",
        "location_type": "Arena",
        "description": "A breathtaking arena with gleaming towers and shimmering domes. The annual Magic Competition showcases the most skilled spellcasters.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "invrasil",
        "slug": "hastburn-alley",
        "name": "Hastburn Alley",
        "location_type": "Market Street",
        "description": "A bustling market street filled with magical artifacts, potions, spellbooks, and enchanted trinkets. Every mage's dream marketplace.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Crares Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "crares",
        "slug": "pearlstrand-promenade",
        "name": "Pearlstrand Promenade",
        "location_type": "Waterfront",
        "description": "A waterfront boulevard lit by enchanted lanterns. The perfect place for evening strolls and watching ships sail under starlight.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "crares",
        "slug": "salty-jewel",
        "name": "The Salty Jewel",
        "location_type": "Tavern",
        "description": "A nautical tavern with live sea shanties and imported rum. Frequented by sailors, merchants, and those seeking tales of the high seas.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "crares",
        "slug": "aquarith-vaults",
        "name": "The Aquarith Vaults",
        "location_type": "Underwater Archive",
        "description": "Magical water archives beneath the sea containing ancient knowledge and oceanic secrets preserved for millennia.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "crares",
        "slug": "maritime-guild",
        "name": "Crares Maritime Guild",
        "location_type": "Guild Hall",
        "description": "Center of naval commerce and privateering contracts. Where merchants and captains negotiate deals that shape maritime trade.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Plia Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "plia",
        "slug": "rootspire-spiral",
        "name": "Rootspire Spiral",
        "location_type": "Vertical Avenue",
        "description": "A vertical avenue winding around the Great Tree. Shops and homes built into the massive trunk create a unique spiral city.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "plia",
        "slug": "drunken-dryad",
        "name": "The Drunken Dryad",
        "location_type": "Tavern",
        "description": "Famous for wildberry wine and enchanted performances. The tree itself seems to sway with the music.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "plia",
        "slug": "heartgrove-conclave",
        "name": "Heartgrove Conclave",
        "location_type": "Druidic Council",
        "description": "The druidic council chamber grown from a living tree. Here the Circle of Nine Roots makes decisions that affect all of Plia.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "plia",
        "slug": "glade-of-whispers",
        "name": "Glade of Whispers",
        "location_type": "Sacred Grove",
        "description": "A mystical forest clearing where secrets can be heard on the wind. Druids come here to commune with nature spirits.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Folis Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "folis",
        "slug": "cinderforge-lane",
        "name": "Cinderforge Lane",
        "location_type": "Forge District",
        "description": "Central blacksmithing and arms district. The air is thick with smoke and the sound of hammers on anvils echoes constantly.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "folis",
        "slug": "molten-mutt",
        "name": "The Molten Mutt",
        "location_type": "Tavern",
        "description": "A rowdy tavern where mercenaries brawl and sing over scorched ale. The heat from nearby forges keeps it perpetually warm.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "folis",
        "slug": "crucible-spire",
        "name": "The Crucible Spire",
        "location_type": "Mage-Forge",
        "description": "A towering structure channeling elemental flame. Fire mages and smiths work together to create legendary weapons.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "folis",
        "slug": "firelords-anvil",
        "name": "Firelord's Anvil",
        "location_type": "Mythic Forge",
        "description": "A legendary forge said to be blessed by a fire titan. Only the greatest smiths are permitted to work here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Yhul Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "yhul",
        "slug": "moonmirror-sanctum",
        "name": "The Moonmirror Sanctum",
        "location_type": "Observatory Temple",
        "description": "An observatory and temple for moon rites. Seers study celestial movements and divine the future from lunar patterns.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "yhul",
        "slug": "waning-wolf",
        "name": "The Waning Wolf",
        "location_type": "Tavern",
        "description": "A rustic tavern serving hot cider and moonglow mead. A warm respite from the eternal snows outside.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "yhul",
        "slug": "vault-of-echoes",
        "name": "Vault of Echoes",
        "location_type": "Memory Archive",
        "description": "An underground chamber storing recorded dreams and ancestral memories. To enter is to witness the past as if you lived it.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "yhul",
        "slug": "yhul-academy",
        "name": "Yhul Academy of Oneirics",
        "location_type": "Dream School",
        "description": "Renowned school of dream-magic and mental defense. Students learn to navigate the dream realm and protect minds from nightmares.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# Town Locations (4 per town)
TOWN_LOCATIONS = [
    # Skooma Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "skooma",
        "slug": "brewers-guild-hall",
        "name": "Brewer's Guild Hall",
        "location_type": "Guild Hall",
        "description": "A grand structure serving as the epicenter of Skooma's brewing community. Brewers gather to exchange knowledge and celebrate their craft.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "skooma",
        "slug": "brewfest-square",
        "name": "Brewfest Square",
        "location_type": "Festival Grounds",
        "description": "The town square where the annual Brewfest is held. During harvest season, it fills with beer enthusiasts from across the continent.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "skooma",
        "slug": "golden-keg-tavern",
        "name": "The Golden Keg",
        "location_type": "Tavern",
        "description": "The finest tavern in Skooma, offering tastings of the town's most exceptional brews. A must-visit for any ale connoisseur.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "skooma",
        "slug": "hopfields",
        "name": "The Hopfields",
        "location_type": "Fields",
        "description": "Rolling fields of hops and barley that provide ingredients for Skooma's legendary brews. Picturesque and fragrant.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Azure Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "azure",
        "slug": "flower-market",
        "name": "The Flower Market",
        "location_type": "Market",
        "description": "A bustling hub where locals and travelers gather to admire and purchase the finest blooms Azure has to offer.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "azure",
        "slug": "azure-castle",
        "name": "Azure Castle",
        "location_type": "Castle",
        "description": "A majestic fortress with Gothic and Renaissance architecture. It has withstood centuries and serves as a symbol of the town's resilience.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "azure",
        "slug": "azure-river-gardens",
        "name": "Azure River Gardens",
        "location_type": "Gardens",
        "description": "Beautiful gardens along the azure blue river. A serene place where rare flowers bloom year-round.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "azure",
        "slug": "botanical-workshop",
        "name": "Botanical Workshop",
        "location_type": "Workshop",
        "description": "Where Azurians create exquisite bouquets and intricate floral arrangements prized throughout the kingdom.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Xynnar Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "xynnar",
        "slug": "runecraft-plaza",
        "name": "Runecraft Plaza",
        "location_type": "Plaza",
        "description": "A central square where runesmiths display their enchanted sigils. Floating crystals illuminate the area with arcane light.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "xynnar",
        "slug": "portal-chamber",
        "name": "The Portal Chamber",
        "location_type": "Magical Site",
        "description": "A mysterious chamber containing ancient portals that hum with magical energy. Only the most skilled mages dare use them.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "xynnar",
        "slug": "scholars-sanctum",
        "name": "Scholar's Sanctum",
        "location_type": "Study Hall",
        "description": "Where arcane scholars gather to study scrolls and artifacts of lost civilizations. Knowledge seekers find refuge here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "xynnar",
        "slug": "floating-lantern-street",
        "name": "Floating Lantern Street",
        "location_type": "Street",
        "description": "A street lined with floating magical lanterns that never dim. The constant glow creates an ethereal atmosphere.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Naporia Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "naporia",
        "slug": "grand-archives",
        "name": "The Grand Archives",
        "location_type": "Library",
        "description": "The largest library in the land, with towering shelves containing countless ancient tomes and manuscripts.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "naporia",
        "slug": "illuminators-workshop",
        "name": "Illuminator's Workshop",
        "location_type": "Workshop",
        "description": "Where skilled illuminators craft stunning manuscripts with gold leaf and vibrant inks.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "naporia",
        "slug": "candlelit-study-hall",
        "name": "Candlelit Study Hall",
        "location_type": "Study Hall",
        "description": "A quiet hall lit by hundreds of candles where scholars read and debate philosophy late into the night.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "naporia",
        "slug": "scribe-quarters",
        "name": "Scribe Quarters",
        "location_type": "Living Quarters",
        "description": "Where dedicated scribes live and work, tirelessly transcribing forgotten knowledge onto fresh parchment.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Kellamoor Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "kellamoor",
        "slug": "coral-docks",
        "name": "Coral Docks",
        "location_type": "Docks",
        "description": "Docks where fishing vessels return with hauls of enchanted coral. The coral glows softly even out of water.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "kellamoor",
        "slug": "divers-guild",
        "name": "Diver's Guild",
        "location_type": "Guild Hall",
        "description": "Where brave coral divers plan their expeditions into dangerous waters. Only the skilled survive these dives.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "kellamoor",
        "slug": "lighthouse-tavern",
        "name": "The Lighthouse Tavern",
        "location_type": "Tavern",
        "description": "A cozy tavern in an old lighthouse offering warm food and tales of the deep sea.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "kellamoor",
        "slug": "coral-crafters-workshop",
        "name": "Coral Crafter's Workshop",
        "location_type": "Workshop",
        "description": "Artisans shape enchanted coral into beautiful jewelry and magical components.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Mirelight Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mirelight",
        "slug": "swamp-market",
        "name": "Swamp Market",
        "location_type": "Market",
        "description": "A market built on stilts above the swamp where rare herbs and alchemical ingredients are sold.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mirelight",
        "slug": "herbalists-hut",
        "name": "Herbalist's Hut",
        "location_type": "Shop",
        "description": "A weathered hut where the town's most skilled herbalist creates potent remedies from marsh plants.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mirelight",
        "slug": "murky-depths-tavern",
        "name": "Murky Depths Tavern",
        "location_type": "Tavern",
        "description": "A rustic tavern serving swamp-brewed spirits and hearty stews. Locals gather here to share marsh tales.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mirelight",
        "slug": "glowing-bog",
        "name": "The Glowing Bog",
        "location_type": "Natural Site",
        "description": "A section of swamp where bioluminescent plants create an otherworldly glow at night. Rare ingredients grow here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Lindleaf Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "lindleaf",
        "slug": "silk-weavers-hall",
        "name": "Silk Weaver's Hall",
        "location_type": "Workshop",
        "description": "Where master weavers create shimmering silk from treeworm cocoons. The fabric practically glows with magic.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "lindleaf",
        "slug": "treeworm-groves",
        "name": "Treeworm Groves",
        "location_type": "Groves",
        "description": "Carefully tended groves where rare treeworms are cultivated. Weavers harvest silk with great reverence.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "lindleaf",
        "slug": "shimmer-boutique",
        "name": "The Shimmer Boutique",
        "location_type": "Shop",
        "description": "An upscale shop selling finished silks to nobles and mages. Each piece is a work of art.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "lindleaf",
        "slug": "weavers-rest",
        "name": "Weaver's Rest Inn",
        "location_type": "Inn",
        "description": "A comfortable inn where traveling merchants stay when purchasing Lindleaf's famous silk.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Oakmarsh Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "oakmarsh",
        "slug": "incense-workshop",
        "name": "Incense Workshop",
        "location_type": "Workshop",
        "description": "Where crafters prepare sacred incense from ancient rotwood. The aroma is intoxicating and spiritual.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "oakmarsh",
        "slug": "rotwood-grove",
        "name": "Rotwood Grove",
        "location_type": "Grove",
        "description": "A sacred grove of ancient, decomposing trees. Despite their appearance, they produce valuable aromatic wood.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "oakmarsh",
        "slug": "meditation-temple",
        "name": "Meditation Temple",
        "location_type": "Temple",
        "description": "A quiet temple where druids and monks meditate surrounded by the scent of Oakmarsh incense.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "oakmarsh",
        "slug": "aromatic-market",
        "name": "Aromatic Market",
        "location_type": "Market",
        "description": "A market specializing in incense, oils, and scented candles. The air itself seems to shimmer with fragrance.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Dravun's Pike Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "dravuns-pike",
        "slug": "soul-iron-mines",
        "name": "Soul-Iron Mines",
        "location_type": "Mines",
        "description": "Deep underground mines where dwarven workers extract the rare soul-iron from ancient veins.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "dravuns-pike",
        "slug": "dwarven-hall",
        "name": "Dwarven Hall",
        "location_type": "Great Hall",
        "description": "A grand hall carved from stone where dwarven miners gather for feasts and to share mining tales.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "dravuns-pike",
        "slug": "stone-anvil-forge",
        "name": "Stone Anvil Forge",
        "location_type": "Forge",
        "description": "A specialized forge where soul-iron is shaped into weapons and armor of legendary quality.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "dravuns-pike",
        "slug": "miners-tavern",
        "name": "The Miner's Respite",
        "location_type": "Tavern",
        "description": "A hearty tavern serving strong dwarven ale and hot meals to miners after long shifts underground.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Corthmill Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "corthmill",
        "slug": "clockwork-workshop",
        "name": "Clockwork Workshop",
        "location_type": "Workshop",
        "description": "Where artificers create intricate clockwork parts and enchanted rivets for golems and constructs.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "corthmill",
        "slug": "gear-market",
        "name": "Gear Market",
        "location_type": "Market",
        "description": "A market selling precision components, gears, and magical machine parts. Tinkerers' paradise.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "corthmill",
        "slug": "artificers-guildhall",
        "name": "Artificer's Guildhall",
        "location_type": "Guild Hall",
        "description": "Where artificers meet to share designs and innovations. The building itself contains moving walls and mechanical wonders.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "corthmill",
        "slug": "copper-cog-inn",
        "name": "The Copper Cog Inn",
        "location_type": "Inn",
        "description": "An inn decorated with brass and copper mechanisms. Clockwork servants attend to guests' needs.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Mistren Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mistren",
        "slug": "elk-stables",
        "name": "Elk Stables",
        "location_type": "Stables",
        "description": "Where magnificent frost elk are housed and trained. These creatures bond deeply with their handlers.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mistren",
        "slug": "tamers-lodge",
        "name": "Tamer's Lodge",
        "location_type": "Lodge",
        "description": "Home to the elk tamers who possess mystical bonds with the frost elk. Outsiders are rarely welcomed.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mistren",
        "slug": "winter-meadow",
        "name": "Winter Meadow",
        "location_type": "Meadow",
        "description": "A snowy meadow where frost elk graze on hardy winter plants. A peaceful, pristine scene.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "mistren",
        "slug": "frosthorn-tavern",
        "name": "The Frosthorn Tavern",
        "location_type": "Tavern",
        "description": "A warm tavern with a roaring fire, serving hot drinks and meals to cold travelers.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Hollowend Locations
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "hollowend",
        "slug": "dream-rift",
        "name": "The Dream Rift",
        "location_type": "Mystical Site",
        "description": "An ancient tear between worlds where reality and dreams blur. Guarded constantly by wardens.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "hollowend",
        "slug": "warden-tower",
        "name": "Warden Tower",
        "location_type": "Tower",
        "description": "A fortified tower where dream-wardens stand eternal vigil, preventing nightmares from escaping the rift.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "hollowend",
        "slug": "rift-research-hall",
        "name": "Rift Research Hall",
        "location_type": "Research Facility",
        "description": "Where scholars study the dream rift's properties, hoping to understand the nature of dreams and reality.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "ammeonon",
        "city": "hollowend",
        "slug": "twilight-inn",
        "name": "Twilight Inn",
        "location_type": "Inn",
        "description": "An inn where visitors sometimes experience prophetic dreams. Some say the rift's influence reaches even here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]


async def populate_ammeonon_data():
    """Populate Ammeonon cities, towns, and locations into the database."""
    print("🏛️ Starting Ammeonon data population...")
    
    # Insert cities
    print(f"\n📍 Inserting {len(AMMEONON_CITIES)} cities...")
    for city in AMMEONON_CITIES:
        existing = await db.cities.find_one({"nation": city["nation"], "slug": city["slug"]})
        if existing:
            print(f"  ⏭️  City '{city['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(city)
            print(f"  ✅ Created city: {city['name']}")
    
    # Insert towns
    print(f"\n🏘️ Inserting {len(AMMEONON_TOWNS)} towns...")
    for town in AMMEONON_TOWNS:
        existing = await db.cities.find_one({"nation": town["nation"], "slug": town["slug"]})
        if existing:
            print(f"  ⏭️  Town '{town['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(town)
            print(f"  ✅ Created town: {town['name']}")
    
    # Insert city locations
    print(f"\n📌 Inserting {len(CITY_LOCATIONS)} city locations...")
    for location in CITY_LOCATIONS:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    # Insert town locations
    print(f"\n📌 Inserting {len(TOWN_LOCATIONS)} town locations...")
    for location in TOWN_LOCATIONS:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    print("\n✨ Ammeonon data population complete!")
    print(f"\n📊 Summary:")
    print(f"  - {len(AMMEONON_CITIES)} cities")
    print(f"  - {len(AMMEONON_TOWNS)} towns")
    print(f"  - {len(CITY_LOCATIONS)} city locations")
    print(f"  - {len(TOWN_LOCATIONS)} town locations")
    print(f"  - Total: {len(AMMEONON_CITIES) + len(AMMEONON_TOWNS)} entities, {len(CITY_LOCATIONS) + len(TOWN_LOCATIONS)} locations")
    print("\nNext steps:")
    print("  1. Generate images for cities, towns, and locations")
    print("  2. Test navigation: Nations → Ammeonon → Cities/Towns → Locations")
    print("  3. Test roleplay in new locations")


if __name__ == "__main__":
    asyncio.run(populate_ammeonon_data())
