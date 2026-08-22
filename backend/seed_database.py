"""
Database Seeder for Continents of Delarom
This module contains all the seed data and functions to populate the production database.
Can be triggered via the admin dashboard with a single button click.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
import base64

# This will be set by the caller
db = None
image_gen = None

def set_database(database):
    """Set the database connection"""
    global db
    db = database

def init_image_generator():
    """Initialize the image generator"""
    global image_gen
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if api_key:
            image_gen = OpenAIImageGeneration(api_key=api_key)
            return True
    except Exception as e:
        print(f"Could not initialize image generator: {e}")
    return False

async def generate_image(prompt: str) -> str:
    """Generate an image and return as base64 data URL"""
    global image_gen
    if not image_gen:
        return None
    
    try:
        images = await image_gen.generate_images(
            prompt=prompt,
            model="gpt-image-1",
            number_of_images=1
        )
        if images and len(images) > 0:
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
    except Exception as e:
        print(f"Image generation error: {e}")
    return None

# ==================== NATION SEED DATA ====================
NATIONS_SEED = [
    {
        "slug": "ammeonon",
        "name": "Ammeonon",
        "description": "The human empire, founded 1200 years ago by King Quentin Blackburn. Now ruled by the Vritra Clan under Astral King Ausar in the year 215 A.E.",
        "image_prompt": "Epic fantasy landscape of Ammeonon, a vast human empire with grand castle spires, medieval cities, rolling hills, fertile farmlands, banners in the wind. Gothic architecture, stone walls, cathedrals. Cinematic wide shot, golden hour, majestic atmosphere. High quality digital art."
    },
    {
        "slug": "dhor-kuldor", 
        "name": "Dhor-Kuldor",
        "description": "Eight mighty dwarven holds carved into the mountains. Masters of smithing, mining, and ancient runecraft.",
        "image_prompt": "Epic fantasy dwarven mountain kingdom, massive stone gates with runic carvings, forges glowing deep within mountains, ancient stone bridges over chasms, dwarf statues of ancestor kings, steam from forge chimneys. Dramatic mountain scenery, warm forge glow. High quality digital art."
    },
    {
        "slug": "selindori",
        "name": "Selindori",
        "description": "Kingdom of the First Elves, where Seren's divine touch blessed the earth. Six elven races dwell within Yillhone, the Crystal City.",
        "image_prompt": "Epic fantasy elven kingdom, crystal city with towers of living crystal, ancient silver-bark trees with golden leaves, elegant spires connected by bridges of light, magical aurora in sky, gardens of impossible flowers. Ethereal, magical atmosphere, soft glowing light. High quality digital art."
    },
    {
        "slug": "aigraels",
        "name": "Aigraels",
        "description": "A land of shifting power where three factions vie for control. The throne changes hands like the wind.",
        "image_prompt": "Epic fantasy contested kingdom, three distinct regions visible - noble estates, merchant trade cities, frontier wilderness. Storm clouds over contested territories, varied architecture showing competing powers, roads converging on strongholds. Dramatic contrasting lighting. High quality digital art."
    },
    {
        "slug": "veiled-realms",
        "name": "The Veiled Realms",
        "description": "The Hidden Ancient Kingdoms—protected by powerful barrier magic. Rakesh, Yaksha-Shi, and Serant-Kresh await those who can pierce the veil.",
        "image_prompt": "Epic fantasy hidden kingdoms glimpsed through shimmering magical barriers - silver towers under twilight, dark spires in misty valleys, geometric crystal formations. Powerful aurora-like barrier magic between realms. Ancient, mysterious, ethereal lighting. High quality digital art."
    }
]

# ==================== AMMEONON CITIES ====================
AMMEONON_CITIES = [
    {"slug": "wymroost", "name": "Wymroost", "nation": "ammeonon", "region": "Central Ammeonon", "entity_type": "city",
     "description": "The grand capital of Ammeonon, seat of Astral King Ausar and the Vritra Clan.",
     "lore": "Founded by King Quentin Blackburn himself, Wymroost has stood as the heart of human civilization for over a millennium."},
    {"slug": "invrasil", "name": "Invrasil", "nation": "ammeonon", "region": "Eastern Ammeonon", "entity_type": "city",
     "description": "A major trade hub known for its vast markets and diverse population.",
     "lore": "Invrasil grew from a small trading post to become the commercial heart of the empire."},
    {"slug": "khastead", "name": "Khastead", "nation": "ammeonon", "region": "Northern Ammeonon", "entity_type": "city",
     "description": "A fortress city guarding the northern borders.",
     "lore": "Built to defend against threats from the mountains, Khastead has never fallen to siege."},
    {"slug": "plia", "name": "Plia", "nation": "ammeonon", "region": "Western Ammeonon", "entity_type": "city",
     "description": "A coastal city famous for its naval fleet and fishing industry.",
     "lore": "Plia's sailors are said to know every current and wind pattern in the western seas."},
    {"slug": "folis", "name": "Folis", "nation": "ammeonon", "region": "Southern Ammeonon", "entity_type": "city",
     "description": "A city of scholars and mages, home to the Grand Academy.",
     "lore": "The magical arts flourish in Folis, where the veil between worlds is thin."},
    {"slug": "crares", "name": "Crares", "nation": "ammeonon", "region": "Central Ammeonon", "entity_type": "city",
     "description": "An industrial city known for its smithies and craftsmen.",
     "lore": "Crares produces the finest steel in all of Ammeonon."},
    {"slug": "yhule", "name": "Yhule", "nation": "ammeonon", "region": "Eastern Ammeonon", "entity_type": "city",
     "description": "A religious center with temples to many gods.",
     "lore": "Pilgrims from across the realm journey to Yhule's sacred shrines."},
    {"slug": "azure", "name": "Azure", "nation": "ammeonon", "region": "Coastal Ammeonon", "entity_type": "town",
     "description": "A picturesque coastal town known for its blue-tiled roofs.",
     "lore": "Azure was founded by sailors seeking a peaceful retirement."},
    {"slug": "corthmill", "name": "Corthmill", "nation": "ammeonon", "region": "Rural Ammeonon", "entity_type": "town",
     "description": "A farming town that supplies grain to the capital.",
     "lore": "The windmills of Corthmill can be seen for miles around."},
]

# ==================== DHOR-KULDOR CITIES ====================
DHOR_KHULDOR_CITIES = [
    {"slug": "karaz-a-karak", "name": "Karaz-a-Karak", "nation": "dhor-kuldor", "region": "The Everpeak", "entity_type": "city",
     "description": "The greatest of all dwarven holds, capital of the Dhor-Kuldor realm.",
     "lore": "Known as the Everpeak, Karaz-a-Karak was the first hold founded and remains the seat of the High King."},
    {"slug": "karak-vorn", "name": "Karak Vorn", "nation": "dhor-kuldor", "region": "The Shadowdeep", "entity_type": "city",
     "description": "A hold known for its deep mines and shadow-touched halls.",
     "lore": "Karak Vorn delves deeper than any other hold, touching the roots of the mountains."},
    {"slug": "kazad-drung", "name": "Kazad Drung", "nation": "dhor-kuldor", "region": "Thunder Peak", "entity_type": "city",
     "description": "The hold of thunder, where storms perpetually rage around the peaks.",
     "lore": "The dwarves of Kazad Drung have harnessed lightning itself in their forges."},
    {"slug": "barak-varr", "name": "Barak Varr", "nation": "dhor-kuldor", "region": "Sea Gate", "entity_type": "city",
     "description": "The only dwarven port, gateway to the seas.",
     "lore": "Barak Varr's ironclad ships are the terror of pirates everywhere."},
    {"slug": "zhufbar", "name": "Zhufbar", "nation": "dhor-kuldor", "region": "Forge Valley", "entity_type": "city",
     "description": "The hold of the engineers, where innovation never sleeps.",
     "lore": "Zhufbar's workshops produce wonders of dwarven engineering."},
    {"slug": "karak-azul", "name": "Karak Azul", "nation": "dhor-kuldor", "region": "Iron Peak", "entity_type": "city",
     "description": "Known for its master smiths and legendary weapons.",
     "lore": "The runesmiths of Karak Azul craft weapons of unparalleled quality."},
    {"slug": "karak-kadrin", "name": "Karak Kadrin", "nation": "dhor-kuldor", "region": "Slayer Peak", "entity_type": "city",
     "description": "Home of the Slayer Cult, where dwarves seek honorable deaths.",
     "lore": "Karak Kadrin guards the pass against all who would threaten the realm."},
    {"slug": "karak-norn", "name": "Karak Norn", "nation": "dhor-kuldor", "region": "Grey Mountains", "entity_type": "city",
     "description": "A hold on the frontier, ever vigilant against threats.",
     "lore": "Karak Norn's rangers patrol the borders tirelessly."},
]

# ==================== SELINDORI CITIES ====================
SELINDORI_CITIES = [
    {"slug": "yillhone", "name": "Yillhone", "nation": "selindori", "region": "Crystal Heart", "entity_type": "city",
     "description": "The Crystal City, capital of the elven realm and seat of the High Council.",
     "lore": "Yillhone's spires of living crystal have stood since the dawn of the First Age."},
    {"slug": "solarath", "name": "Solarath", "nation": "selindori", "region": "Sunward Reaches", "entity_type": "city",
     "description": "City of the Sun Elves, bathed in eternal golden light.",
     "lore": "Solarath's towers catch the first and last rays of every sunrise and sunset."},
    {"slug": "thalenroot", "name": "Thalenroot", "nation": "selindori", "region": "Verdant Crescent", "entity_type": "city",
     "description": "Home of the Forest Elves, built within ancient living trees.",
     "lore": "The trees of Thalenroot are older than recorded history."},
    {"slug": "naltheris", "name": "Nal'Theris", "nation": "selindori", "region": "Veilwater Shores", "entity_type": "city",
     "description": "City of the Mist Elves, shrouded in perpetual fog.",
     "lore": "Nal'Theris exists partially in the spirit realm."},
    {"slug": "isenfell", "name": "Isenfell", "nation": "selindori", "region": "Frostmere Heights", "entity_type": "city",
     "description": "Stronghold of the Snow Elves in the frozen north.",
     "lore": "Isenfell's ice walls have never been breached."},
    {"slug": "aercyr", "name": "Aer'Cyr", "nation": "selindori", "region": "Gilded Underway", "entity_type": "city",
     "description": "Mountain home of the Mountain Elves, carved with precision.",
     "lore": "Aer'Cyr's halls rival even dwarven craftsmanship."},
]

# ==================== AIGRAELS CITIES ====================
AIGRAELS_CITIES = [
    {"slug": "astralun", "name": "Astra'Lun", "nation": "aigraels", "region": "Lysanthea Region", "entity_type": "city",
     "description": "A mystical city where starlight illuminates ancient towers.",
     "lore": "Astra'Lun was built where a star fell to earth in ages past."},
    {"slug": "ironhold", "name": "Ironhold", "nation": "aigraels", "region": "Vargath Region", "entity_type": "city",
     "description": "A fortress city controlled by the Ardent Legion.",
     "lore": "Ironhold's walls have withstood a hundred sieges."},
    {"slug": "noctyss-vale", "name": "Noctyss Vale", "nation": "aigraels", "region": "Shadowmere Region", "entity_type": "city",
     "description": "A city shrouded in eternal twilight, home to the Forsaken Court.",
     "lore": "The sun never fully rises over Noctyss Vale."},
    {"slug": "thornwick", "name": "Thornwick", "nation": "aigraels", "region": "Contested Lands", "entity_type": "city",
     "description": "A trade city that changes hands between factions regularly.",
     "lore": "Thornwick's markets never close, regardless of who rules."},
]

# ==================== VEILED REALMS CITIES ====================
VEILED_REALMS_CITIES = [
    {"slug": "niratha", "name": "Niratha", "nation": "veiled-realms", "region": "Rakesh", "entity_type": "city",
     "description": "Capital of Rakesh, the Moon Elf kingdom.",
     "lore": "Niratha's silver spires glow brightest under the full moon."},
    {"slug": "moonfall", "name": "Moonfall", "nation": "veiled-realms", "region": "Rakesh", "entity_type": "city",
     "description": "A sacred city where moonlight pools like water.",
     "lore": "The Moon Elves perform their most sacred rituals in Moonfall."},
    {"slug": "twilight-citadel", "name": "Twilight Citadel", "nation": "veiled-realms", "region": "Yaksha-Shi", "entity_type": "city",
     "description": "The dark heart of the Shadow Elf domain.",
     "lore": "The Twilight Citadel exists between light and darkness."},
    {"slug": "blackgrove", "name": "Blackgrove", "nation": "veiled-realms", "region": "Yaksha-Shi", "entity_type": "city",
     "description": "A city hidden within an ancient dark forest.",
     "lore": "The trees of Blackgrove drink shadow instead of sunlight."},
    {"slug": "kreshmar", "name": "Kreshmar", "nation": "veiled-realms", "region": "Serant-Kresh", "entity_type": "city",
     "description": "The crystalline capital of the Crystal Elves.",
     "lore": "Kreshmar's structures are grown from living crystal."},
    {"slug": "prismhold", "name": "Prismhold", "nation": "veiled-realms", "region": "Serant-Kresh", "entity_type": "city",
     "description": "A fortress of rainbow-hued crystal formations.",
     "lore": "Light itself bends to the will of Prismhold's guardians."},
]

# Combine all cities
ALL_CITIES = (
    AMMEONON_CITIES + 
    DHOR_KHULDOR_CITIES + 
    SELINDORI_CITIES + 
    AIGRAELS_CITIES + 
    VEILED_REALMS_CITIES
)

# ==================== SAMPLE LOCATIONS ====================
def generate_locations_for_city(city_slug, city_name, nation):
    """Generate sample locations for a city"""
    location_types = [
        ("tavern", "The {adj} {noun} Tavern", "A popular gathering place for adventurers and locals alike."),
        ("temple", "{deity} Temple", "A sacred place of worship and reflection."),
        ("market", "{adj} Market Square", "A bustling center of trade and commerce."),
        ("guild", "{profession} Guild Hall", "Headquarters for skilled practitioners."),
        ("tower", "The {adj} Tower", "A tall structure with mysterious purpose."),
    ]
    
    adjectives = ["Golden", "Silver", "Iron", "Crystal", "Shadow", "Ancient", "Royal", "Hidden"]
    nouns = ["Dragon", "Phoenix", "Crown", "Star", "Moon", "Sun", "Rose", "Lion"]
    deities = ["Seren", "Moradin", "Pelor", "Helm", "Tyr"]
    professions = ["Mage", "Warrior", "Merchant", "Smith", "Alchemist"]
    
    locations = []
    import random
    random.seed(hash(city_slug))  # Consistent randomization per city
    
    for i, (loc_type, name_template, desc) in enumerate(location_types[:3]):  # 3 locations per city
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        deity = random.choice(deities)
        prof = random.choice(professions)
        
        name = name_template.format(adj=adj, noun=noun, deity=deity, profession=prof)
        slug = name.lower().replace(" ", "-").replace("'", "")
        
        locations.append({
            "slug": slug,
            "name": name,
            "nation": nation,
            "city": city_slug,  # This is what the API expects
            "city_name": city_name,
            "location_type": loc_type,
            "description": desc,
            "lore": f"A notable landmark in {city_name}.",
            "is_active": True,
            "is_rp_enabled": True
        })
    
    return locations


async def seed_nations(with_images=True):
    """Seed the nations collection"""
    print("Seeding nations...")
    count = 0
    images_generated = 0
    
    for nation in NATIONS_SEED:
        existing = await db.nations.find_one({"slug": nation["slug"]})
        if not existing:
            nation_doc = {
                "slug": nation["slug"],
                "name": nation["name"],
                "description": nation["description"],
                "image_url": None
            }
            
            # Generate image if enabled
            if with_images and image_gen:
                print(f"  Generating image for {nation['name']}...")
                image_url = await generate_image(nation["image_prompt"])
                if image_url:
                    nation_doc["image_url"] = image_url
                    images_generated += 1
                    print(f"  ✓ Image generated for {nation['name']}")
                await asyncio.sleep(1)  # Rate limiting
            
            await db.nations.insert_one(nation_doc)
            count += 1
            print(f"  Created nation: {nation['name']}")
        else:
            # Update image if missing
            if with_images and image_gen and not existing.get("image_url"):
                print(f"  Generating missing image for {nation['name']}...")
                image_url = await generate_image(nation["image_prompt"])
                if image_url:
                    await db.nations.update_one(
                        {"slug": nation["slug"]},
                        {"$set": {"image_url": image_url}}
                    )
                    images_generated += 1
                    print(f"  ✓ Image added for {nation['name']}")
                await asyncio.sleep(1)
            else:
                print(f"  Nation exists: {nation['name']}")
    
    return {"created": count, "images": images_generated}


async def seed_cities(with_images=True):
    """Seed the cities collection"""
    print("Seeding cities...")
    count = 0
    images_generated = 0
    
    for city in ALL_CITIES:
        existing = await db.cities.find_one({"slug": city["slug"], "nation": city["nation"]})
        if not existing:
            # Generate image prompt based on city data
            image_prompt = f"Epic fantasy {city.get('entity_type', 'city')}: {city['name']} in {city['nation']}. {city['description']} {city.get('lore', '')} Style: Fantasy landscape, cinematic, detailed architecture, atmospheric. High quality digital art."
            
            city_doc = {
                **city,
                "id": city["slug"],
                "is_active": True,
                "image_url": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Generate image if enabled
            if with_images and image_gen:
                print(f"  Generating image for {city['name']}...")
                image_url = await generate_image(image_prompt)
                if image_url:
                    city_doc["image_url"] = image_url
                    images_generated += 1
                await asyncio.sleep(1)  # Rate limiting
            
            await db.cities.insert_one(city_doc)
            count += 1
            print(f"  Created city: {city['name']} ({city['nation']})")
        else:
            # Update image if missing
            if with_images and image_gen and not existing.get("image_url"):
                image_prompt = f"Epic fantasy {city.get('entity_type', 'city')}: {city['name']} in {city['nation']}. {city['description']} Style: Fantasy landscape, cinematic):, detailed. High quality digital art."
                print(f"  Generating missing image for {city['name']}...")
                image_url = await generate_image(image_prompt)
                if image_url:
                    await db.cities.update_one(
                        {"slug": city["slug"], "nation": city["nation"]},
                        {"$set": {"image_url": image_url}}
                    )
                    images_generated += 1
                await asyncio.sleep(1)
            else:
                print(f"  City exists: {city['name']}")
    
    return {"created": count, "images": images_generated}


async def seed_locations(with_images=True):
    """Seed locations for each city"""
    print("Seeding locations...")
    count = 0
    images_generated = 0
    
    for city in ALL_CITIES:
        locations = generate_locations_for_city(city["slug"], city["name"], city["nation"])
        for loc in locations:
            existing = await db.locations.find_one({"slug": loc["slug"], "city": loc["city"], "nation": loc["nation"]})
            if not existing:
                # Generate image prompt
                image_prompt = f"Fantasy interior scene: {loc['name']}, a {loc['location_type']} in {loc['city_name']}. {loc['description']} Medieval fantasy setting, atmospheric lighting, detailed interior. High quality digital art."
                
                loc_doc = {
                    **loc,
                    "id": f"{loc['city']}-{loc['slug']}",
                    "image_url": None,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Generate image if enabled
                if with_images and image_gen:
                    image_url = await generate_image(image_prompt)
                    if image_url:
                        loc_doc["image_url"] = image_url
                        images_generated += 1
                    await asyncio.sleep(1)  # Rate limiting
                
                await db.locations.insert_one(loc_doc)
                count += 1
    
    print(f"  Created {count} locations, {images_generated} images")
    return {"created": count, "images": images_generated}


async def run_full_seed(with_images=True):
    """Run the complete database seeding process"""
    results = {
        "nations": 0,
        "cities": 0,
        "locations": 0,
        "nation_images": 0,
        "city_images": 0,
        "location_images": 0,
        "errors": []
    }
    
    # Initialize image generator if images are requested
    if with_images:
        if init_image_generator():
            print("Image generator initialized")
        else:
            print("Image generator not available - seeding without images")
            results["errors"].append("Image generator not available")
    
    try:
        nation_result = await seed_nations(with_images=with_images)
        results["nations"] = nation_result["created"]
        results["nation_images"] = nation_result["images"]
    except Exception as e:
        results["errors"].append(f"Nations error: {str(e)}")
    
    try:
        city_result = await seed_cities(with_images=with_images)
        results["cities"] = city_result["created"]
        results["city_images"] = city_result["images"]
    except Exception as e:
        results["errors"].append(f"Cities error: {str(e)}")
    
    try:
        location_result = await seed_locations(with_images=with_images)
        results["locations"] = location_result["created"]
        results["location_images"] = location_result["images"]
    except Exception as e:
        results["errors"].append(f"Locations error: {str(e)}")
    
    return results
