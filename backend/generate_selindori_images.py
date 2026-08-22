"""
Generate AI images for Selindori - Kingdom of the First Elves
Elven aesthetic: Crystal spires, ethereal light, nature-infused architecture

Expected images:
- 6 Yillhone districts
- 5 regional cities  
- 10 towns
- 84 locations
- Total: ~105 images
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


def get_elven_style(entity_name, slug, description, faction=None, region=None):
    """Generate elven-themed style prompt based on the entity."""
    
    base_style = "ethereal elven fantasy, crystal architecture, magical luminescence, elegant spires, nature-infused design"
    
    # Race-specific styles
    race_styles = {
        "sun": "golden radiance, divine light, white-gold crystals, eternal dawn, celestial beauty",
        "forest": "living wood, green magic, tree-woven architecture, verdant growth, nature spirits",
        "mist": "water reflections, fog and mist, glass and crystal, flowing canals, serene pools",
        "snow": "frost-touched marble, ice crystals, cool blue light, winter elegance, frozen beauty",
        "mountain": "underground chambers, dim lighting, hidden spaces, rough-hewn stone, shadows",
        "sky": "floating islands, clouds and wind, dragon roosts, open sky, aerial architecture",
    }
    
    # Check for race indicators in slug, faction, or region
    desc_lower = description.lower()
    slug_lower = slug.lower()
    faction_lower = (faction or "").lower()
    region_lower = (region or "").lower()
    
    combined = f"{desc_lower} {slug_lower} {faction_lower} {region_lower}"
    
    if any(word in combined for word in ["sun", "aurelion", "solar", "dawn", "golden", "radiant"]):
        return f"{base_style}, {race_styles['sun']}"
    elif any(word in combined for word in ["forest", "verdant", "green", "fen", "root", "bark", "oak"]):
        return f"{base_style}, {race_styles['forest']}"
    elif any(word in combined for word in ["mist", "water", "veil", "devdan", "canal", "reed", "silver"]):
        return f"{base_style}, {race_styles['mist']}"
    elif any(word in combined for word in ["snow", "frost", "ice", "winter", "cold", "white archive"]):
        return f"{base_style}, {race_styles['snow']}"
    elif any(word in combined for word in ["mountain", "gilded underway", "hidden", "underground", "shadow"]):
        return f"{base_style}, {race_styles['mountain']}"
    elif any(word in combined for word in ["sky", "aer", "cloud", "wind", "dragon", "float"]):
        return f"{base_style}, {race_styles['sky']}"
    
    # Default crystal city style
    return f"{base_style}, prismatic light, divine architecture, Seren's blessing"


async def generate_city_images():
    """Generate images for all Selindori cities and districts."""
    print("\n🏛️ Generating CITY/DISTRICT images...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    cities = await db.cities.find({"nation": "selindori"}, {"_id": 0}).to_list(100)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for city in cities:
        if city.get('image_url'):
            print(f"  ⏭️  {city['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 Generating image for {city['name']}...")
        
        style = get_elven_style(city['name'], city['slug'], city['description'], city.get('faction'), city.get('region'))
        
        prompt = f"""
Elven {city.get('entity_type', 'City').lower()}: {city['name']}
{city['description']}
{city.get('lore', '')}
Region: {city.get('region', 'Selindori')}

Style: {style}
Majestic elven architecture, crystal spires, magical ambiance.
Cinematic wide shot, ethereal lighting, detailed fantasy art.
High quality digital art, elegant elven aesthetic.
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
    """Generate images for all Selindori locations."""
    print("\n📍 Generating LOCATION images...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    locations = await db.locations.find({"nation": "selindori"}, {"_id": 0}).to_list(500)
    
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
        city = await db.cities.find_one({"nation": "selindori", "slug": location.get('city', '')}, {"_id": 0})
        faction = city.get('faction', 'Elven') if city else 'Elven'
        region = city.get('region', 'Selindori') if city else 'Selindori'
        
        style = get_elven_style(location['name'], location['slug'], location['description'], faction, region)
        
        prompt = f"""
Elven location: {location['name']}
Type: {location.get('location_type', 'Location')}
{location['description']}
Part of: {location.get('city', 'Selindori').replace('-', ' ').title()}

Style: {style}
Detailed elven interior or scene, magical atmosphere.
Ethereal lighting, elegant design, fantasy art.
High quality digital art, elven aesthetic.
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
        
        if (i + 1) % 25 == 0:
            print(f"\n  📊 Progress: {i+1}/{total} ({generated} generated, {skipped} skipped, {failed} failed)\n")
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def main():
    """Main function to generate all Selindori images."""
    print("=" * 70)
    print("🌿 SELINDORI IMAGE GENERATION")
    print("Kingdom of the First Elves")
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
    print("✨ SELINDORI IMAGE GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Final Summary:")
    print(f"  - Generated: {total_generated}")
    print(f"  - Skipped: {total_skipped}")
    print(f"  - Failed: {total_failed}")


async def generate_cities_only():
    """Generate only city/district images."""
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
