"""
Generate AI images for Ammeonon cities, towns, and locations.
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
    """Generate images for all Ammeonon cities."""
    print("🏙️ Generating city images...")
    
    image_gen = ImageGenerator()
    cities = await db.cities.find({"nation": "ammeonon", "region": {"$exists": True, "$ne": "Near Wymroost"}}, {"_id": 0}).to_list(100)
    
    for city in cities:
        if city.get('image_url'):
            print(f"  ⏭️  {city['name']} already has an image, skipping...")
            continue
        
        print(f"  🎨 Generating image for {city['name']}...")
        
        prompt = f"""
Epic fantasy city in Ammeonon: {city['name']}.
Region: {city.get('region', 'Unknown')}.
{city['description']}
Faction: {city.get('faction', 'Independent')}.
{city.get('lore', '')}

Style: {get_city_style(city['slug'])}
Cinematic wide shot, dramatic lighting, detailed architecture, immersive fantasy scene.
High quality digital art, medieval fantasy aesthetic.
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


async def generate_town_images():
    """Generate images for all Ammeonon towns."""
    print("\n🏘️ Generating town images...")
    
    image_gen = ImageGenerator()
    towns = await db.cities.find({"nation": "ammeonon", "region": {"$regex": "^Near"}}, {"_id": 0}).to_list(100)
    
    for town in towns:
        if town.get('image_url'):
            print(f"  ⏭️  {town['name']} already has an image, skipping...")
            continue
        
        print(f"  🎨 Generating image for {town['name']}...")
        
        prompt = f"""
Fantasy town in Ammeonon: {town['name']}.
{town['description']}
{town.get('lore', '')}

Style: Medieval fantasy town, {get_town_style(town['slug'])}, charming atmosphere, detailed buildings.
Cinematic view, warm lighting, inviting scene.
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
                
                await db.cities.update_one(
                    {"id": town["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {town['name']}")
            else:
                print(f"  ❌ Failed to generate image for {town['name']}")
        except Exception as e:
            print(f"  ❌ Error generating image for {town['name']}: {e}")


async def generate_location_images():
    """Generate images for all Ammeonon locations."""
    print("\n📌 Generating location images...")
    
    image_gen = ImageGenerator()
    locations = await db.locations.find({"nation": "ammeonon"}, {"_id": 0}).to_list(200)
    
    for location in locations:
        if location.get('image_url'):
            print(f"  ⏭️  {location['name']} already has an image, skipping...")
            continue
        
        # Skip locations without a city field (likely test data)
        if 'city' not in location:
            print(f"  ⚠️  Skipping {location['name']} - no city field")
            continue
        
        print(f"  🎨 Generating image for {location['name']}...")
        
        # Get city/town info for context
        city = await db.cities.find_one({"nation": "ammeonon", "slug": location['city']}, {"_id": 0})
        faction = city.get('faction', 'Independent') if city else 'Independent'
        
        prompt = f"""
Fantasy location in Ammeonon: {location['name']}.
Type: {location.get('location_type', 'Area')}.
{location['description']}
Associated with: {faction}.

Style: {get_location_style(location.get('location_type'), location['slug'])}
Epic fantasy scene, detailed, atmospheric lighting, immersive environment.
High quality digital art, medieval fantasy aesthetic.
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


def get_city_style(city_slug):
    """Get visual style based on city."""
    styles = {
        "wymroost": "Massive port city with 150 ships, bustling docks, grand merchant buildings, diverse architecture, coastal fortress.",
        "invrasil": "Magical city with towering wizard academies, floating runes, glowing spires, arcane energy, scholarly atmosphere.",
        "crares": "Shimmering coastal city with sea-glass architecture, iridescent buildings, maritime elegance, enchanted structures.",
        "plia": "Forest city built into massive ancient trees, wooden platforms, rope bridges, living architecture, verdant canopy.",
        "folis": "Mountainous forge-city with lava channels, black stone, glowing forges, smoke and flames, industrial grandeur.",
        "yhul": "Snow-covered city of marble and crystal, frost-covered spires, moonlit beauty, ethereal glow, peaceful serenity.",
    }
    return styles.get(city_slug, "Medieval fantasy city with diverse architecture.")


def get_town_style(town_slug):
    """Get visual style based on town specialization."""
    styles = {
        "skooma": "brewing town with barrels, hop fields, taverns, rustic charm",
        "azure": "flower town with vibrant gardens, colorful blooms, pastoral beauty",
        "xynnar": "arcane research town with floating crystals, glowing runes, magical portals",
        "naporia": "library town with towering bookshelves, scholars, ancient tomes",
        "kellamoor": "fishing village with coral displays, seaside charm, boats and nets",
        "mirelight": "swampy outpost with stilts, murky waters, mystical herbs",
        "lindleaf": "silk-weaving town with looms, shimmering fabrics, craftsman workshops",
        "oakmarsh": "incense-crafting town with smoke wisps, sacred atmosphere, forest setting",
        "dravuns-pike": "dwarven mining town with stone halls, forges, mountain tunnels",
        "corthmill": "clockwork town with gears, mechanical devices, inventor workshops",
        "mistren": "northern town with frost elk, snowy meadows, taming grounds",
        "hollowend": "dream-rift settlement with mystical towers, otherworldly atmosphere, wardens",
    }
    return styles.get(town_slug, "charming medieval town")


def get_location_style(location_type, location_slug):
    """Get visual style based on location type."""
    # Special cases based on slug
    if "docks" in location_slug or "port" in location_slug:
        return "Bustling docks with ships, sailors, cargo, maritime activity."
    if "market" in location_slug or "marketplace" in location_slug:
        return "Vibrant marketplace with merchant stalls, colorful goods, busy crowds."
    if "tavern" in location_slug:
        return "Cozy tavern interior with warm lighting, patrons, ale mugs, rustic furniture."
    if "academy" in location_slug or "school" in location_slug:
        return "Grand magical academy with students, spellbooks, arcane symbols, scholarly atmosphere."
    if "stadium" in location_slug or "arena" in location_slug:
        return "Magnificent arena with crowds, magical displays, grand architecture."
    if "forge" in location_slug or "anvil" in location_slug:
        return "Blazing forge with molten metal, anvils, sparks, master smiths at work."
    if "guild" in location_slug:
        return "Guild hall with professionals, meeting chambers, emblems and banners."
    if "grove" in location_slug or "glade" in location_slug:
        return "Sacred forest grove with ancient trees, mystical atmosphere, dappled sunlight."
    if "vault" in location_slug or "archive" in location_slug:
        return "Ancient vault or archive with artifacts, scrolls, protective magic."
    if "sanctum" in location_slug or "temple" in location_slug:
        return "Sacred temple with altars, holy symbols, reverential atmosphere, divine light."
    if "mines" in location_slug or "mining" in location_slug:
        return "Deep underground mines with ore veins, mining equipment, torchlight, dwarven workers."
    if "rift" in location_slug:
        return "Mystical rift between worlds, swirling energies, reality-bending visuals, otherworldly."
    
    # General types
    type_styles = {
        "Port District": "Busy port with ships, docks, maritime commerce.",
        "Trade District": "Marketplace with diverse goods, merchant activity.",
        "Entertainment Quarter": "Lively district with taverns, music, celebration.",
        "Arcane District": "Magical district with enchantments, glowing artifacts.",
        "Magical School": "Academy with students, spellcasting, libraries.",
        "Arena": "Grand arena with spectators, combat, dramatic events.",
        "Market Street": "Street lined with shops, colorful displays, bustling activity.",
        "Waterfront": "Scenic waterfront with ocean views, peaceful atmosphere.",
        "Tavern": "Warm tavern with ale, music, camaraderie.",
        "Underwater Archive": "Underwater structure with magical water, preserved knowledge.",
        "Guild Hall": "Professional guild building with meeting spaces, emblems.",
        "Vertical Avenue": "Unique vertical street winding around massive tree.",
        "Druidic Council": "Natural council chamber grown from living trees.",
        "Sacred Grove": "Mystical forest clearing with spiritual presence.",
        "Forge District": "Industrial forge area with metalworking, heat, smoke.",
        "Mage-Forge": "Fusion of magic and smithing, elemental flames, enchanting.",
        "Observatory Temple": "Temple with celestial observatory, star charts, moon worship.",
        "Memory Archive": "Archive preserving memories and dreams, ethereal atmosphere.",
        "Dream School": "School for dream magic, surreal atmosphere, mental training.",
    }
    return type_styles.get(location_type, "Medieval fantasy scene, atmospheric and detailed.")


async def main():
    """Main function to generate all images."""
    print("=" * 70)
    print("🎨 AMMEONON IMAGE GENERATION")
    print("=" * 70)
    print("\nThis will generate approximately 90 images:")
    print("  - 6 city images")
    print("  - 12 town images")
    print("  - 72 location images (24 city + 48 town locations)")
    print("\nEstimated cost: $7.00 - $10.00")
    print("\nStarting generation...\n")
    
    await generate_city_images()
    await generate_town_images()
    await generate_location_images()
    
    print("\n" + "=" * 70)
    print("✨ IMAGE GENERATION COMPLETE!")
    print("=" * 70)
    print("\nAll images have been generated and stored in the database.")
    print("Navigate to Ammeonon to see the results!")


if __name__ == "__main__":
    asyncio.run(main())
