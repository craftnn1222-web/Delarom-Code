"""
Generate AI images for Dhor-Kuldor holds, cities, towns, and locations.
This script uses the OpenAI gpt-image-1 model via Emergent LLM key.

Due to the large number of images (~400+), this script is designed to:
1. Be idempotent - skip entities that already have images
2. Generate images in batches with progress tracking
3. Handle timeouts gracefully - can be re-run to continue

Expected images:
- 8 holds (major fortress-cities)
- 24 cities
- 48 towns
- ~320 locations
- Total: ~400 images
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

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


def get_dwarven_style(entity_type, name, slug, description, faction=None, region=None):
    """Generate a dwarven-themed style prompt based on the entity."""
    
    base_style = "epic dwarven fantasy, carved stone halls, mountain fortress, underground kingdom, torchlit passages, runic inscriptions, majestic stonework"
    
    # Hold-specific styles
    hold_styles = {
        "karak-vorn": "Grand throne room carved into mountain heart, eternal runefires, echoing halls of ancient kings, massive stone pillars with gold inlay",
        "kazad-drung": "Massive forge complex, rivers of molten metal, towering furnaces, red-hot iron, billowing smoke, master smiths at work",
        "barak-varr": "Coastal cliff fortress, ironclad ships in harbor caves, sea-carved docks, naval architecture, salt spray and iron",
        "zhufbar": "Steam-powered engineering hub, clockwork mechanisms, gyrocopters, brass pipes and gears, innovation and industry",
        "karak-azul": "Gem-encrusted halls, crystal formations, mythril veins, treasure vaults, precious stones catching light",
        "karak-kadrin": "Warrior's fortress, orange-crested slayers, trophy halls of monsters, battle scars and honor",
        "karaz-a-karak": "Ancient library halls, thousand carved pillars, sacred tomes, ancestral knowledge preserved",
        "karak-norn": "Frozen mountain watchtower, ice-covered battlements, snow-swept passes, vigilant wardens",
    }
    
    # General location type styles
    type_styles = {
        "forge": "blazing forges, molten metal, anvils and hammers, sparks flying, heat distortion",
        "mine": "deep underground tunnels, ore veins glinting, minecarts, pickaxes, torchlight",
        "tavern": "cozy dwarven tavern, ale barrels, stone hearth, rowdy atmosphere, wooden beams",
        "guild": "professional guild hall, banners and emblems, meeting chambers, craftsman tools",
        "market": "underground market cavern, merchant stalls, goods displayed, busy commerce",
        "temple": "sacred dwarven temple, ancestor shrines, runic altars, divine light through stone",
        "barracks": "military quarters, weapon racks, armor stands, discipline and order",
        "workshop": "craftsman workshop, tools organized, works in progress, master craftsmanship",
        "vault": "secure treasure vault, massive doors, gold and gems, heavy locks",
        "archive": "library with stone shelves, ancient scrolls, recorded history, candlelight",
        "port": "underground harbor, ironclad ships, sea caves, nautical equipment",
        "training": "combat training area, sparring dwarves, practice weapons, determination",
    }
    
    # Check for hold-specific style
    if slug in hold_styles:
        return f"{base_style}, {hold_styles[slug]}"
    
    # Check description and slug for type hints
    desc_lower = description.lower()
    slug_lower = slug.lower()
    
    for keyword, style in type_styles.items():
        if keyword in desc_lower or keyword in slug_lower:
            return f"{base_style}, {style}"
    
    # Faction-specific additions
    faction_styles = {
        "High King's Court": "royal grandeur, gold and silver, ceremonial splendor",
        "Forgemaster's Guild": "industrial might, eternal flames, master craftsmanship",
        "Admiral's Council": "naval power, maritime strength, sea command",
        "Engineers Guild": "mechanical innovation, steam and brass, inventive genius",
        "Gem Lords": "crystalline beauty, precious wealth, refined elegance",
        "Slayer Cult": "warrior honor, death-seeking valor, battle readiness",
        "Loremaster's Guild": "ancient wisdom, preserved knowledge, scholarly pursuit",
        "Warden's Watch": "eternal vigilance, defensive strength, guardian duty",
    }
    
    if faction and faction in faction_styles:
        return f"{base_style}, {faction_styles[faction]}"
    
    return base_style


async def generate_hold_images():
    """Generate images for the 8 major holds."""
    print("\n🏔️ Generating HOLD images (8 major fortress-cities)...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    holds = await db.cities.find({
        "nation": "dhor-kuldor",
        "region": {"$exists": True, "$not": {"$regex": "^Near"}}
    }, {"_id": 0}).to_list(100)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for hold in holds:
        if hold.get('image_url'):
            print(f"  ⏭️  {hold['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 Generating image for {hold['name']}...")
        
        style = get_dwarven_style("hold", hold['name'], hold['slug'], hold['description'], hold.get('faction'), hold.get('region'))
        
        prompt = f"""
Epic dwarven mountain fortress: {hold['name']}
{hold['description']}
{hold.get('lore', '')}
Region: {hold.get('region', 'Mountain Hold')}

Style: {style}
Massive underground city carved into mountain, grand entrance gates, towering stone halls.
Cinematic wide shot, dramatic torch lighting, detailed stonework, immersive fantasy scene.
High quality digital art, Warhammer/Lord of the Rings dwarven aesthetic.
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
                    {"id": hold["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {hold['name']}")
                generated += 1
            else:
                print(f"  ❌ Failed to generate image for {hold['name']}")
                failed += 1
        except Exception as e:
            print(f"  ❌ Error generating image for {hold['name']}: {e}")
            failed += 1
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def generate_city_images():
    """Generate images for all cities (24 total)."""
    print("\n🏛️ Generating CITY images (24 cities)...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    # Cities have "Near <Hold>" in region but are entity_type "City"
    cities = await db.cities.find({
        "nation": "dhor-kuldor",
        "region": {"$regex": "^Near"},
        "entity_type": "City"
    }, {"_id": 0}).to_list(100)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for city in cities:
        if city.get('image_url'):
            print(f"  ⏭️  {city['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 Generating image for {city['name']}...")
        
        style = get_dwarven_style("city", city['name'], city['slug'], city['description'], city.get('faction'), city.get('region'))
        
        prompt = f"""
Dwarven city district: {city['name']}
{city['description']}
{city.get('lore', '')}
Located: {city.get('region', 'Near a major Hold')}

Style: {style}
Underground city section, carved stone architecture, dwarven craftsmanship.
Cinematic view, warm torch lighting, atmospheric, immersive fantasy.
High quality digital art, epic dwarven aesthetic.
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


async def generate_town_images():
    """Generate images for all towns (48 total)."""
    print("\n🏘️ Generating TOWN images (48 towns)...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    towns = await db.cities.find({
        "nation": "dhor-kuldor",
        "entity_type": "Town"
    }, {"_id": 0}).to_list(100)
    
    generated = 0
    skipped = 0
    failed = 0
    
    for town in towns:
        if town.get('image_url'):
            print(f"  ⏭️  {town['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        print(f"  🎨 Generating image for {town['name']}...")
        
        style = get_dwarven_style("town", town['name'], town['slug'], town['description'], town.get('faction'), town.get('region'))
        
        prompt = f"""
Dwarven town: {town['name']}
{town['description']}
{town.get('lore', '')}

Style: {style}
Smaller underground settlement, specialized dwarven community, functional architecture.
Cozy but industrious atmosphere, warm lighting, dwarven craftsmanship.
High quality digital art, fantasy dwarven aesthetic.
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
                    {"id": town["id"]},
                    {"$set": {"image_url": image_url}}
                )
                print(f"  ✅ Generated image for {town['name']}")
                generated += 1
            else:
                print(f"  ❌ Failed to generate image for {town['name']}")
                failed += 1
        except Exception as e:
            print(f"  ❌ Error generating image for {town['name']}: {e}")
            failed += 1
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def generate_location_images():
    """Generate images for all locations (~320 total)."""
    print("\n📍 Generating LOCATION images (~320 locations)...")
    print("-" * 50)
    
    image_gen = ImageGenerator()
    locations = await db.locations.find({"nation": "dhor-kuldor"}, {"_id": 0}).to_list(500)
    
    generated = 0
    skipped = 0
    failed = 0
    total = len(locations)
    
    for i, location in enumerate(locations):
        if location.get('image_url'):
            print(f"  ⏭️  [{i+1}/{total}] {location['name']} already has an image, skipping...")
            skipped += 1
            continue
        
        # Skip locations without a city field (legacy data)
        if 'city' not in location:
            print(f"  ⚠️  [{i+1}/{total}] Skipping {location['name']} - no city field")
            skipped += 1
            continue
        
        print(f"  🎨 [{i+1}/{total}] Generating image for {location['name']}...")
        
        # Get parent city for context
        city = await db.cities.find_one({"nation": "dhor-kuldor", "slug": location['city']}, {"_id": 0})
        faction = city.get('faction', 'Dwarven') if city else 'Dwarven'
        
        style = get_dwarven_style(
            "location", 
            location['name'], 
            location['slug'], 
            location['description'], 
            faction,
            None
        )
        
        prompt = f"""
Dwarven location: {location['name']}
Type: {location.get('location_type', 'Location')}
{location['description']}
Part of: {location.get('city', 'Unknown').replace('-', ' ').title()}

Style: {style}
Detailed interior or focused scene, dwarven architecture and design.
Atmospheric lighting, immersive environment, rich detail.
High quality digital art, epic dwarven fantasy aesthetic.
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
        
        # Progress checkpoint every 50 images
        if (i + 1) % 50 == 0:
            print(f"\n  📊 Progress: {i+1}/{total} processed ({generated} generated, {skipped} skipped, {failed} failed)")
            print(f"     Continuing...\n")
    
    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")
    return generated, skipped, failed


async def main():
    """Main function to generate all images."""
    print("=" * 70)
    print("🎨 DHOR-KULDOR IMAGE GENERATION")
    print("=" * 70)
    print("\nThis will generate approximately 400 images:")
    print("  - 8 hold images")
    print("  - 24 city images")
    print("  - 48 town images")
    print("  - ~320 location images")
    print("\nEstimated cost: $35.00 - $45.00")
    print("Estimated time: 2-3 hours")
    print("\nThe script is idempotent - re-run to continue if interrupted.")
    print("\nStarting generation...\n")
    
    total_generated = 0
    total_skipped = 0
    total_failed = 0
    
    # Generate holds first (most important)
    g, s, f = await generate_hold_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    # Then cities
    g, s, f = await generate_city_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    # Then towns
    g, s, f = await generate_town_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    # Finally locations (largest batch)
    g, s, f = await generate_location_images()
    total_generated += g
    total_skipped += s
    total_failed += f
    
    print("\n" + "=" * 70)
    print("✨ IMAGE GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Final Summary:")
    print(f"  - Generated: {total_generated}")
    print(f"  - Skipped (already had images): {total_skipped}")
    print(f"  - Failed: {total_failed}")
    print(f"  - Total processed: {total_generated + total_skipped + total_failed}")
    print("\nNavigate to Dhor-Kuldor in the app to see the results!")
    
    if total_failed > 0:
        print(f"\n⚠️  {total_failed} images failed to generate. Re-run the script to retry.")


async def generate_holds_only():
    """Quick function to generate only hold images."""
    print("Generating HOLD images only...")
    await generate_hold_images()
    print("Done!")


async def generate_cities_only():
    """Quick function to generate only city images."""
    print("Generating CITY images only...")
    await generate_city_images()
    print("Done!")


async def generate_towns_only():
    """Quick function to generate only town images."""
    print("Generating TOWN images only...")
    await generate_town_images()
    print("Done!")


async def generate_locations_only():
    """Quick function to generate only location images."""
    print("Generating LOCATION images only...")
    await generate_location_images()
    print("Done!")


if __name__ == "__main__":
    # Check for command line argument to run specific batch
    if len(sys.argv) > 1:
        batch = sys.argv[1].lower()
        if batch == "holds":
            asyncio.run(generate_holds_only())
        elif batch == "cities":
            asyncio.run(generate_cities_only())
        elif batch == "towns":
            asyncio.run(generate_towns_only())
        elif batch == "locations":
            asyncio.run(generate_locations_only())
        else:
            print(f"Unknown batch: {batch}")
            print("Usage: python generate_dhor_kuldor_images.py [holds|cities|towns|locations]")
    else:
        asyncio.run(main())
