"""
Populate Aigraels cities and locations into the database.
Run this script to add all Aigraels content.
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

# Aigraels Cities Data
AIGRAELS_CITIES = [
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "slug": "vargath",
        "name": "Vargath",
        "region": "Vargath Region",
        "description": "The Fractured Throne City - the ever-contested capital of Aigraels. Whoever holds Vargath rules Aigraels... until they don't.",
        "lore": "Vargath is the original capital of the Aerdrath Kingdom, built atop ancient foundations. The city is divided into fortified districts, each able to be defended independently—making total control nearly impossible.",
        "faction": "Contested",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "slug": "ironhold",
        "name": "Ironhold",
        "region": "Northern Highlands",
        "description": "Bastion of the Ardent Legion - a fortress city where every street doubles as a kill corridor and every building serves the Legion's doctrine.",
        "lore": "Ironhold is not merely a city—it is a war engine. Built from black stone with iron reinforcements, it embodies the Ardent Legion's philosophy: peace through victory.",
        "faction": "Ardent Legion",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "slug": "noctyss-vale",
        "name": "Noctyss Vale",
        "region": "Velmourne Region",
        "description": "City of Masks and Whispered Rule - hidden political capital of the Forsaken Court where nothing is as it seems.",
        "lore": "Noctyss Vale does not appear on most maps. Streets loop intentionally, towers block sightlines, and even residents rarely know the city's full layout.",
        "faction": "Forsaken Court",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "slug": "astra-lun",
        "name": "Astra'Lun",
        "region": "Lysanthea Region",
        "description": "The City of Living Memory - stronghold of the Elderborn Alliance, built with magic and designed to endure centuries.",
        "lore": "Astra'Lun is built to endure centuries. Every structure is layered with astral wards and memory anchors. Light behaves strangely here, and time feels slower near the upper spires.",
        "faction": "Elderborn Alliance",
        "image_url": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

# Aigraels Locations Data
AIGRAELS_LOCATIONS = [
    # Vargath Locations
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "vargath",
        "slug": "crownspire",
        "name": "Crownspire",
        "location_type": "Palace Ruins",
        "description": "The ruined royal palace atop Vargath. Whoever holds this spire claims legitimacy to rule Aigraels.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "vargath",
        "slug": "ashmarket",
        "name": "Ashmarket",
        "location_type": "Trade Ward",
        "description": "A blackened trade ward where arms, relics, and secrets are bought and sold in the shadows.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "vargath",
        "slug": "old-bastions",
        "name": "The Old Bastions",
        "location_type": "Fortifications",
        "description": "Aerdrath-era fortifications, now partially collapsed and haunted by memories of past battles.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "vargath",
        "slug": "veilward",
        "name": "Veilward",
        "location_type": "Spy District",
        "description": "A district notorious for spies, assassinations, and false banners. Trust no one here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "vargath",
        "slug": "broken-forum",
        "name": "The Broken Forum",
        "location_type": "Public Square",
        "description": "Where proclamations are made—and frequently overturned. The center of political chaos in Vargath.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Ironhold Locations
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "ironhold",
        "slug": "iron-ascendant",
        "name": "The Iron Ascendant",
        "location_type": "Command Citadel",
        "description": "Legion command citadel where General Serus Valthar directs the Ardent Legion's campaigns.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "ironhold",
        "slug": "field-of-standards",
        "name": "Field of Standards",
        "location_type": "Memorial",
        "description": "Where banners of defeated enemies are mounted as trophies. A grim reminder of the Legion's victories.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "ironhold",
        "slug": "forge-of-names",
        "name": "The Forge of Names",
        "location_type": "Training Ground",
        "description": "Where Legion soldiers earn new names after great victories. Honor is forged here.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "ironhold",
        "slug": "crucible-yards",
        "name": "The Crucible Yards",
        "location_type": "Forges",
        "description": "Where war machines and weapons are forged. The heat never dies, and the hammers never stop.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Noctyss Vale Locations
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "noctyss-vale",
        "slug": "house-of-veils",
        "name": "House of Veils",
        "location_type": "Court Headquarters",
        "description": "The true seat of the Forsaken Court, where Lady Selene Valthos holds court behind silver masks.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "noctyss-vale",
        "slug": "silent-opera",
        "name": "The Silent Opera",
        "location_type": "Theater",
        "description": "Messages are encoded in performance here. Every gesture, every note carries hidden meaning.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "noctyss-vale",
        "slug": "gloom-exchange",
        "name": "The Gloom Exchange",
        "location_type": "Black Market",
        "description": "A black market of secrets where information is currency and loyalty is bought and sold.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "noctyss-vale",
        "slug": "mirror-crypts",
        "name": "The Mirror Crypts",
        "location_type": "Tombs",
        "description": "Ancestral tombs rumored to whisper advice to those who dare listen. Many enter, few return unchanged.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    
    # Astra'Lun Locations
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "astra-lun",
        "slug": "astral-forum",
        "name": "The Astral Forum",
        "location_type": "Diplomatic Chamber",
        "description": "Where the Elderborn Alliance conducts diplomacy and attempts to broker peace between the warring factions.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "astra-lun",
        "slug": "memory-wells",
        "name": "Memory Wells",
        "location_type": "Archive",
        "description": "Pools containing recorded history. Gaze into them and witness the past as if you were there.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "astra-lun",
        "slug": "quiet-spire",
        "name": "The Quiet Spire",
        "location_type": "Training Site",
        "description": "Where astral mages train in silence, learning to manipulate the very fabric of reality.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid4()),
        "nation": "aigraels",
        "city": "astra-lun",
        "slug": "starwell",
        "name": "The Starwell",
        "location_type": "Astral Nexus",
        "description": "A deep astral nexus where the boundaries between worlds grow thin. Dangerous and beautiful.",
        "image_url": None,
        "is_active": True,
        "is_rp_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]


async def populate_aigraels_data():
    """Populate Aigraels cities and locations into the database."""
    print("🏛️ Starting Aigraels data population...")
    
    # Insert cities
    print(f"\n📍 Inserting {len(AIGRAELS_CITIES)} cities...")
    for city in AIGRAELS_CITIES:
        existing = await db.cities.find_one({"nation": city["nation"], "slug": city["slug"]})
        if existing:
            print(f"  ⏭️  City '{city['name']}' already exists, skipping...")
        else:
            await db.cities.insert_one(city)
            print(f"  ✅ Created city: {city['name']}")
    
    # Insert locations
    print(f"\n📌 Inserting {len(AIGRAELS_LOCATIONS)} locations...")
    for location in AIGRAELS_LOCATIONS:
        existing = await db.locations.find_one({"nation": location["nation"], "slug": location["slug"]})
        if existing:
            print(f"  ⏭️  Location '{location['name']}' already exists, skipping...")
        else:
            await db.locations.insert_one(location)
            print(f"  ✅ Created location: {location['name']} in {location['city']}")
    
    print("\n✨ Aigraels data population complete!")
    print("\nNext steps:")
    print("  1. Generate images for cities and locations")
    print("  2. Test navigation: Nations → Cities → Locations")
    print("  3. Test roleplay in new locations")


if __name__ == "__main__":
    asyncio.run(populate_aigraels_data())
