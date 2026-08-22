"""
Generate representative images for each nation in Tyrandria.
These will be used on the main Nations page.
"""
import asyncio
import os
import base64
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Image generator
api_key = os.environ.get('EMERGENT_LLM_KEY')
image_gen = OpenAIImageGeneration(api_key=api_key)

# Nation data with detailed descriptions for image generation
NATIONS = [
    {
        "slug": "ammeonon",
        "name": "Ammeonon",
        "prompt": """
Epic fantasy landscape of Ammeonon, the Human Empire.
A vast kingdom with grand cities, towering castle spires reaching toward the sky.
The capital Wymroost dominates the scene with its majestic palace of the Astral King.
Rolling hills, fertile farmlands, and bustling roads connect prosperous settlements.
Banners bearing the royal crest flutter in the wind.
Medieval fantasy architecture with Gothic influences, stone walls, and grand cathedrals.

Style: Epic fantasy landscape, cinematic wide shot, golden hour lighting, 
detailed architecture, high quality digital art, majestic and powerful atmosphere.
"""
    },
    {
        "slug": "dhor-kuldor",
        "name": "Dhor-Kuldor",
        "prompt": """
Epic fantasy landscape of Dhor-Kuldor, the Dwarven Realm.
Massive mountain holds carved into towering peaks, with grand stone gates and runic carvings.
The great hold of Karaz-a-Karak stands as the crown jewel, with forges glowing deep within.
Ancient stone bridges span deep chasms, underground rivers of molten gold visible below.
Dwarf statues of ancestor kings guard the mountain passes.
Steam rises from forge chimneys, the mountains alive with industry and ancient craft.

Style: Epic fantasy landscape, dramatic mountain scenery, warm forge glow against cold stone,
cinematic wide shot, detailed dwarven architecture, high quality digital art.
"""
    },
    {
        "slug": "selindori",
        "name": "Selindori",
        "prompt": """
Epic fantasy landscape of Selindori, Kingdom of the First Elves.
Yillhone, the Crystal City, rises in ethereal splendor with towers of living crystal.
Ancient trees with silver bark and golden leaves form a sacred forest.
Elegant spires reach toward the heavens, connected by bridges of light.
Magical aurora dances in the sky, reflecting off crystalline structures.
Gardens of impossible flowers bloom in perpetual beauty.
Six distinct elven architectural styles blend in harmony.

Style: Epic fantasy landscape, ethereal and magical atmosphere, soft glowing light,
elegant elven architecture, high quality digital art, otherworldly beauty.
"""
    },
    {
        "slug": "aigraels",
        "name": "Aigraels",
        "prompt": """
Epic fantasy landscape of Aigraels, a land of shifting power.
Three distinct regions visible: the Noble Houses' grand estates, the Merchant Guilds' 
bustling trade cities, and the frontier wilderness where factions clash.
Storm clouds gather over contested territories while other areas bask in prosperity.
Varied architecture shows the influence of competing powers.
Roads converge on central strongholds where political intrigue unfolds.
A land of opportunity and danger, where fortunes rise and fall.

Style: Epic fantasy landscape, dramatic contrasting lighting, political tension visible,
varied architecture, cinematic composition, high quality digital art.
"""
    },
    {
        "slug": "veiled-realms",
        "name": "The Veiled Realms",
        "prompt": """
Epic fantasy landscape of The Veiled Realms, the Hidden Ancient Kingdoms.
Three mystical realms glimpsed through shimmering magical barriers:
Rakesh of the Moon Elves - silver towers under an eternal twilight sky.
Yaksha-Shi of the Shadow Elves - dark spires rising from misty valleys.
Serant-Kresh of the Crystalborn - geometric crystal formations pulsing with inner light.
Powerful barrier magic ripples like aurora between the realms and the outside world.
Ancient and mysterious, these kingdoms have remained hidden for millennia.

Style: Epic fantasy landscape, mystical and secretive atmosphere, magical barriers visible,
three distinct regions, ethereal lighting, high quality digital art, sense of ancient mystery.
"""
    }
]

async def generate_nation_image(nation_data: dict) -> str:
    """Generate an image for a nation and return base64 encoded string"""
    print(f"Generating image for {nation_data['name']}...")
    
    try:
        images = await image_gen.generate_images(
            prompt=nation_data['prompt'],
            model="gpt-image-1",
            number_of_images=1
        )
        
        if images and len(images) > 0:
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
        else:
            print(f"No image generated for {nation_data['name']}")
            return None
    except Exception as e:
        print(f"Error generating image for {nation_data['name']}: {e}")
        return None

async def main():
    print("=" * 60)
    print("GENERATING NATION IMAGES")
    print("=" * 60)
    
    # Check if nations collection exists, create if not
    collections = await db.list_collection_names()
    if 'nations' not in collections:
        print("Creating 'nations' collection...")
    
    for nation_data in NATIONS:
        # Check if nation already has an image
        existing = await db.nations.find_one({"slug": nation_data['slug']})
        
        if existing and existing.get('image_url'):
            print(f"✓ {nation_data['name']} already has an image, skipping...")
            continue
        
        # Generate the image
        image_url = await generate_nation_image(nation_data)
        
        if image_url:
            # Upsert nation document with image
            await db.nations.update_one(
                {"slug": nation_data['slug']},
                {
                    "$set": {
                        "slug": nation_data['slug'],
                        "name": nation_data['name'],
                        "image_url": image_url
                    }
                },
                upsert=True
            )
            print(f"✓ Saved image for {nation_data['name']}")
        else:
            print(f"✗ Failed to generate image for {nation_data['name']}")
        
        # Small delay between generations
        await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print("NATION IMAGE GENERATION COMPLETE")
    print("=" * 60)
    
    # Show summary
    count = await db.nations.count_documents({})
    with_images = await db.nations.count_documents({"image_url": {"$exists": True, "$ne": None}})
    print(f"Total nations: {count}")
    print(f"Nations with images: {with_images}")

if __name__ == "__main__":
    asyncio.run(main())
