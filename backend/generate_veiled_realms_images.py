"""
Generate AI images for The Veiled Realms - Hidden Ancient Kingdoms
Three distinct kingdoms with unique aesthetics:
- Rakesh (Moon Elves): Lunar, ethereal, floating islands
- Yaksha-Shi (Shadow Elves): Dark, mysterious, obsidian
- Serant-Kresh (Crystal Elves): Crystal caverns, light refraction, memory

Expected images:
- 9 cities
- 9 towns
- 66 locations
- Total: ~84 images
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import sys
import base64
sys.path.append('/app/backend')
from image_generator import ImageGenerator

load_dotenv()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


def get_veiled_style(entity_name, slug, description, faction=None, region=None):
    """Generate style prompt based on which hidden kingdom the entity belongs to."""
    
    region_lower = (region or "").lower()
    desc_lower = description.lower()
    
    # Rakesh - Moon Elves
    if "rakesh" in region_lower or any(word in desc_lower for word in ["moon", "lunar", "crescent", "twilight"]):
        return "ethereal lunar fantasy, silver moonlight, floating islands, soft glowing orbs, celestial architecture, pearl and silver palette, serene and mystical atmosphere, moon phases, starlit sky"
    
    # Yaksha-Shi - Shadow Elves
    elif "yaksha" in region_lower or any(word in desc_lower for word in ["shadow", "dark", "umbral", "black", "obsidian"]):
        return "dark fantasy, obsidian architecture, perpetual twilight, deep shadows with hints of violet light, mysterious fog, angular gothic design, hidden passages, ominous beauty"
    
    # Serant-Kresh - Crystal Elves
    elif "serant" in region_lower or any(word in desc_lower for word in ["crystal", "prism", "resonance", "memory", "shard"]):
        return "crystalline fantasy, prismatic light refraction, singing crystals, memory-infused architecture, rainbow light effects, geometric precision, luminescent caverns, ethereal glow"
    
    # Default mysterious ancient style
    return "ancient hidden realm, magical barrier, mysterious elven architecture, forbidden knowledge, timeless beauty"


async def generate_city_images():
    """Generate images for all Veiled Realms cities."""
    print("\n🏛️ Generating CITY images...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    cities = await db.cities.find({"nation": "veiled-realms"}, {"_id": 0}).to_list(100)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for city in cities:
        if city.get('image_url'):
            print(f"  ⏭️  {city['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 Generating image for {city['name']}...")
        
        style = get_veiled_style(city['name'], city['slug'], city['description'], city.get('faction'), city.get('region'))
        
        prompt = f"""
Hidden elven {city.get('entity_type', 'City').lower()}: {city['name']}
{city['description']}
{city.get('lore', '')}
Kingdom: {city.get('region', 'The Veiled Realms')}

Style: {style}
Ancient hidden city, protected by powerful magic, breathtaking architecture.
Cinematic wide shot, mystical atmosphere, detailed fantasy art.
High quality digital art, otherworldly elven aesthetic.
"""
        
        try:
            images = await image_gen.image_gen.generate_images(
                prompt=prompt.strip(),
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                await db.cities.update_one(
                    {"id": city["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {city['name']}")
                generated += 1
            else:
                print(f"  ❌ Failed to generate image for {city['name']}")
                failed += 1
        except Exception as e:
            print(f"  ❌ Error generating image for {city['name']}: {e}")
            failed += 1
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def generate_location_images():
    """Generate images for all Veiled Realms locations."""
    print("\n📍 Generating LOCATION images...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    locations = await db.locations.find({"nation": "veiled-realms"}, {"_id": 0}).to_list(500)
    
    generated = 0
    skipped = 0
    failed = 0
    total = len(locations)
    
    for i, location in enumerate(locations):
        if location.get('image_url'):
            print(f"  ⏭️  [{i+1}/{total}] {location['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 [{i+1}/{total}] Generating image for {location['name']}...")
        
        # Get parent city for context
        city = await db.cities.find_one({"nation": "veiled-realms", "slug": location.get('city', '')}, {"_id": 0})
        faction = city.get('faction', 'Ancient Elven') if city else 'Ancient Elven'
        region = city.get('region', 'The Veiled Realms') if city else 'The Veiled Realms'
        
        style = get_veiled_style(location['name'], location['slug'], location['description'], faction, region)
        
        prompt = f"""
Hidden realm location: {location['name']}
Type: {location.get('location_type', 'Location')}
{location['description']}
Part of: {location.get('city', 'Unknown').replace('-', ' ').title()}

Style: {style}
Detailed interior or scene from a hidden ancient kingdom.
Mystical atmosphere, otherworldly beauty, fantasy art.
High quality digital art, unique elven aesthetic.
"""
        
        try:
            images = await image_gen.image_gen.generate_images(
                prompt=prompt.strip(),
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                await db.locations.update_one(
                    {"id": location["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ [{i+1}/{total}] Generated image for {location['name']}")
                generated += 1
            else:
                print(f"  ❌ [{i+1}/{total}] Failed to generate image for {location['name']}")
                failed += 1
        except Exception as e:
            print(f"  ❌ [{i+1}/{total}] Error generating image for {location['name']}: {e}")
            failed += 1
        
        if (i + 1) % 20 == 0:
            print(f"\n  📊 Progress: {i+1}/{total} ({generated} generated, {skipped} skipped, {failed} failed)\n")
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def main():
    """Main function to generate all Veiled Realms images."""
    print("=" * 70)
    print("🌙 VEILED REALMS IMAGE GENERATION")
    print("The Hidden Ancient Kingdoms")
    print("=" * 70)
    
    total_generated = 0
    total_skipped = 0
    total_failed = 0
    
    g, s, f = await generate_city_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    g, s, f = await generate_location_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    print("\n" + "=" * 70)
    print("✨ VEILED REALMS IMAGE GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Final Summary:")
    print(f"  - Generated: {total_generated}")
    print(f"  - Skipped: {total_skipped}")
    print(f"  - Failed: {total_failed}")


async def generate_cities_only():
    """Generate only city images."""
    await generate_city_images()

async def generate_locations_only():
    """Generate only location images."""
    await generate_location_images()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        batch = sys.argv[1].lower()
        if batch == "cities":
            asyncio.run(generate_cities_only())
        elif batch == "locations":
            asyncio.run(generate_locations_only())
        else:
            print(f"Unknown batch: {batch}")
    else:
        asyncio.run(main())
