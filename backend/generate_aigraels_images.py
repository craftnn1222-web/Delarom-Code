"""
Generate AI images for Aigraels cities and locations.
This script uses the OpenAI gpt-image-1 model via Emergent LLM key.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import sys
sys.path.append('/app/backend')
from image_generator import ImageGenerator

load_dotenv()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


async def generate_city_images():
    """Generate images for all Aigraels cities."""
    print("🏙️ Generating city images...")
    
    image_gen = ImageGenerator()
    cities = await db.cities.find({"nation": "aigraels"}, {"_id": 0}).to_list(100)
    
    for city in cities:
        if city.get('image_url'):
            print(f"  ⏭️  {city['name']} already has an image, skipping...")
            continue
        
        print(f"  🎨 Generating image for {city['name']}...")
        
        prompt = f"""
Fantasy city in Aigraels: {city['name']}.
{city['description']}
Faction: {city.get('faction', 'Neutral')}.
{city.get('lore', '')}

Style: Epic fantasy cityscape, cinematic wide shot, dramatic lighting, detailed architecture.
{get_faction_style(city.get('faction'))}
High quality digital art, immersive fantasy scene.
"""
        
        try:
            images = await image_gen.image_gen.generate_images(
                prompt=prompt.strip(),
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                import base64
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                await db.cities.update_one(
                    {"id": city["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {city['name']}")
            else:
                print(f"  ❌ Failed to generate image for {city['name']}")
        except Exception as e:
            print(f"  ❌ Error generating image for {city['name']}: {e}")


async def generate_location_images():
    """Generate images for all Aigraels locations."""
    print("\n📌 Generating location images...")
    
    image_gen = ImageGenerator()
    locations = await db.locations.find({"nation": "aigraels"}, {"_id": 0}).to_list(200)
    
    for location in locations:
        if location.get('image_url'):
            print(f"  ⏭️  {location['name']} already has an image, skipping...")
            continue
        
        print(f"  🎨 Generating image for {location['name']}...")
        
        # Get city info for context
        city = await db.cities.find_one({"nation": "aigraels", "slug": location['city']}, {"_id": 0})
        faction = city.get('faction', 'Neutral') if city else 'Neutral'
        
        prompt = f"""
Fantasy location in Aigraels: {location['name']}.
Type: {location.get('location_type', 'Area')}.
{location['description']}
Faction influence: {faction}.

Style: {get_location_style(location.get('location_type'))}
Epic fantasy scene, detailed, atmospheric lighting, cinematic.
High quality digital art.
"""
        
        try:
            images = await image_gen.image_gen.generate_images(
                prompt=prompt.strip(),
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                import base64
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                await db.locations.update_one(
                    {"id": location["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {location['name']}")
            else:
                print(f"  ❌ Failed to generate image for {location['name']}")
        except Exception as e:
            print(f"  ❌ Error generating image for {location['name']}: {e}")


def get_faction_style(faction):
    """Get visual style based on faction."""
    styles = {
        "Ardent Legion": "Military architecture, black stone, iron reinforcements, banners and standards, fortress design.",
        "Forsaken Court": "Gothic architecture, shadowy atmosphere, fog, veiled elegance, mysterious ambiance.",
        "Elderborn Alliance": "Magical architecture, glowing runes, crystal spires, astral light, ethereal beauty.",
        "Contested": "Mixed architectural styles, war-torn, battle damage, multiple banners, chaotic.",
    }
    return styles.get(faction, "Fantasy medieval architecture.")


def get_location_style(location_type):
    """Get visual style based on location type."""
    styles = {
        "Palace Ruins": "Ruined grand palace, broken throne, crumbling walls, dramatic lighting.",
        "Trade Ward": "Busy marketplace, merchant stalls, crowds, goods and wares.",
        "Fortifications": "Ancient walls, guard towers, battlements, weathered stone.",
        "Spy District": "Dark alleys, shadowy figures, hidden passages, mysterious atmosphere.",
        "Public Square": "Open plaza, gathering place, public monuments, diverse crowd.",
        "Command Citadel": "Military headquarters, war room, strategic maps, commanding presence.",
        "Memorial": "Solemn monument, banners, tributes, respectful atmosphere.",
        "Training Ground": "Combat arena, training dummies, weapons racks, disciplined environment.",
        "Forges": "Blazing forges, molten metal, anvils, sparks flying, industrial heat.",
        "Court Headquarters": "Elegant chambers, masked figures, political intrigue, veiled luxury.",
        "Theater": "Grand stage, ornate seating, dramatic lighting, performance space.",
        "Black Market": "Hidden bazaar, secretive deals, mysterious vendors, illicit goods.",
        "Tombs": "Ancient crypts, stone sarcophagi, eerie atmosphere, memorial candles.",
        "Diplomatic Chamber": "Council room, negotiation table, neutral ground, peaceful ambiance.",
        "Archive": "Library halls, ancient tomes, magical records, scholarly atmosphere.",
        "Training Site": "Magical training grounds, mystical energies, focused students.",
        "Astral Nexus": "Swirling cosmic energies, reality-bending visuals, otherworldly beauty.",
    }
    return styles.get(location_type, "Fantasy interior scene, detailed and atmospheric.")


async def main():
    """Main function to generate all images."""
    print("=" * 60)
    print("🎨 AIGRAELS IMAGE GENERATION")
    print("=" * 60)
    print("\nThis will generate approximately 21 images:")
    print("  - 4 city images")
    print("  - 17 location images")
    print("\nEstimated cost: $2.40 - $4.80 (depending on image sizes)")
    print("\nStarting generation...\n")
    
    await generate_city_images()
    await generate_location_images()
    
    print("\n" + "=" * 60)
    print("✨ IMAGE GENERATION COMPLETE!")
    print("=" * 60)
    print("\nAll images have been generated and stored in the database.")
    print("Navigate to Aigraels to see the results!")


if __name__ == "__main__":
    asyncio.run(main())
