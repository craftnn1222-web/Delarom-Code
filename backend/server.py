from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Request, Body
from fastapi.responses import Response as FastAPIResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from enum import Enum
from quest_master_ai import QuestMasterAI
from npc_memory_service import NPCMemoryService
from world_state_service import WorldStateService
from image_service import ImageService
from law_service import LawService, law_system_enabled
import base64
import shutil

ROOT_DIR = Path(__file__).parent
MUSIC_DIR = ROOT_DIR / 'static' / 'music'
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
# Explicit timeouts + retryable reads/writes. socketTimeoutMS is generous so a
# slow COLLSCAN can't wedge; retryReads/Writes recover from transient Atlas
# blips instead of crashing long-running background jobs (image batcher).
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=120000,
    retryReads=True,
    retryWrites=True,
    maxPoolSize=50,
)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = 'delarom-dev-secret-key'  # Fallback for development only
    logging.warning("JWT_SECRET_KEY not set in environment. Using insecure default for development.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging — initialised early so any module-level code (incl. route factories) can use it.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mount static files directory for music - mount at /api/static to work with ingress routing
app.mount("/api/static", StaticFiles(directory=str(ROOT_DIR / 'static')), name="static")

# Health check endpoint for Kubernetes
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy"}


@app.get("/api/db-status")
async def public_db_status():
    """Public endpoint to check database status."""
    nations = await db.nations.count_documents({})
    cities = await db.cities.count_documents({})
    locations = await db.locations.count_documents({})
    users = await db.users.count_documents({})
    
    # Check for sample data
    sample_nation = await db.nations.find_one({}, {"_id": 0, "image_url": 0})
    sample_city = await db.cities.find_one({}, {"_id": 0, "image_url": 0})
    sample_location = await db.locations.find_one({}, {"_id": 0, "image_url": 0})
    
    return {
        "counts": {
            "nations": nations,
            "cities": cities,
            "locations": locations,
            "users": users
        },
        "samples": {
            "nation": sample_nation,
            "city": sample_city,
            "location": sample_location
        }
    }


@app.get("/api/reset-and-seed")
async def reset_and_seed():
    """
    DANGER: Deletes all nations, cities, locations and re-seeds them.
    Use this if the data is corrupted or has wrong structure.
    """
    # Delete existing data
    await db.nations.delete_many({})
    await db.cities.delete_many({})
    await db.locations.delete_many({})
    
    # Ensure admin user
    await ensure_default_admin_user()
    
    # Re-seed without images
    from seed_database import run_full_seed, set_database
    set_database(db)
    seed_results = await run_full_seed(with_images=False)
    
    return {
        "message": "Database reset and re-seeded!",
        "nations": seed_results["nations"],
        "cities": seed_results["cities"],
        "locations": seed_results["locations"],
        "next_step": "/api/initialize/nations-images"
    }


@app.get("/api/populate-full/{nation}")
async def populate_full_nation(nation: str):
    """
    Populate FULL data for a specific nation.
    This runs the populate script which adds all cities, towns, and locations.
    """
    valid_nations = ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]
    
    if nation not in valid_nations:
        return {"error": f"Invalid nation. Valid options: {valid_nations}"}
    
    try:
        # Import the data directly from populate scripts
        if nation == "ammeonon":
            from populate_ammeonon import AMMEONON_CITIES, AMMEONON_TOWNS
            cities_data = AMMEONON_CITIES
            towns_data = AMMEONON_TOWNS
        elif nation == "dhor-kuldor":
            from populate_dhor_kuldor import DHOR_KHULDOR_HOLDS, DHOR_KHULDOR_CITIES, DHOR_KHULDOR_TOWNS
            cities_data = DHOR_KHULDOR_HOLDS + DHOR_KHULDOR_CITIES
            towns_data = DHOR_KHULDOR_TOWNS
        elif nation == "selindori":
            from populate_selindori import YILLHONE_DISTRICTS, SELINDORI_CITIES, SELINDORI_TOWNS
            cities_data = YILLHONE_DISTRICTS + SELINDORI_CITIES
            towns_data = SELINDORI_TOWNS
        elif nation == "aigraels":
            from populate_aigraels import AIGRAELS_CITIES
            cities_data = AIGRAELS_CITIES
            towns_data = []
        elif nation == "veiled-realms":
            from populate_veiled_realms import RAKESH_CITIES, RAKESH_TOWNS, YAKSHASHI_CITIES, YAKSHASHI_TOWNS, SERANTKRESH_CITIES, SERANTKRESH_TOWNS
            cities_data = RAKESH_CITIES + YAKSHASHI_CITIES + SERANTKRESH_CITIES
            towns_data = RAKESH_TOWNS + YAKSHASHI_TOWNS + SERANTKRESH_TOWNS
        else:
            return {"error": "Unknown nation"}
        
        # Insert cities
        cities_inserted = 0
        for city in cities_data:
            existing = await db.cities.find_one({"slug": city["slug"], "nation": city["nation"]})
            if not existing:
                await db.cities.insert_one(city)
                cities_inserted += 1
        
        # Insert towns
        towns_inserted = 0
        for town in towns_data:
            existing = await db.cities.find_one({"slug": town["slug"], "nation": town["nation"]})
            if not existing:
                await db.cities.insert_one(town)
                towns_inserted += 1
        
        return {
            "nation": nation,
            "message": f"Successfully populated {nation}!",
            "cities_inserted": cities_inserted,
            "towns_inserted": towns_inserted,
            "next": f"/api/populate-locations/{nation}"
        }
    except Exception as e:
        import traceback
        return {
            "nation": nation,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/api/populate-locations/{nation}")
async def populate_locations_for_nation(nation: str):
    """
    Populate locations for a specific nation.
    Call this after populating cities/towns.
    """
    try:
        if nation == "ammeonon":
            from populate_ammeonon import CITY_LOCATIONS, TOWN_LOCATIONS
            locations = CITY_LOCATIONS + TOWN_LOCATIONS
        elif nation == "dhor-kuldor":
            from populate_dhor_kuldor import generate_hold_locations, generate_city_locations, generate_town_locations
            locations = generate_hold_locations() + generate_city_locations() + generate_town_locations()
        elif nation == "selindori":
            from populate_selindori import generate_locations
            locations = generate_locations()
        elif nation == "aigraels":
            from populate_aigraels import AIGRAELS_LOCATIONS
            locations = AIGRAELS_LOCATIONS
        elif nation == "veiled-realms":
            from populate_veiled_realms import generate_veiled_locations
            locations = generate_veiled_locations()
        else:
            return {"error": "Unknown nation"}
        
        # Insert locations in batches
        inserted = 0
        for loc in locations:
            existing = await db.locations.find_one({"id": loc.get("id")})
            if not existing:
                await db.locations.insert_one(loc)
                inserted += 1
        
        return {
            "nation": nation,
            "locations_inserted": inserted,
            "total_locations": len(locations),
            "message": f"Inserted {inserted} locations for {nation}"
        }
    except Exception as e:
        import traceback
        return {
            "nation": nation,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/api/populate-all-nations")
async def populate_all_nations():
    """
    Populate ALL nations with full data. This may take a while.
    Runs each nation's populate script in sequence.
    """
    results = {}
    
    # First ensure nations exist in nations collection
    from seed_database import NATIONS_SEED, set_database
    set_database(db)
    for nation_data in NATIONS_SEED:
        existing = await db.nations.find_one({"slug": nation_data["slug"]})
        if not existing:
            await db.nations.insert_one({
                "slug": nation_data["slug"],
                "name": nation_data["name"],
                "description": nation_data["description"],
                "image_url": None
            })
    
    # Populate each nation. Module names are hardcoded (not user-controlled);
    # the explicit allowlist below makes that guarantee visible to security scanners.
    nations_to_populate = [
        ("ammeonon", "populate_ammeonon", "populate_ammeonon_data"),
        ("aigraels", "populate_aigraels", "populate_aigraels_data"),
        ("dhor-kuldor", "populate_dhor_kuldor", "populate_dhor_kuldor_data"),
        ("selindori", "populate_selindori", "populate_selindori_data"),
        ("veiled-realms", "populate_veiled_realms", "populate_veiled_realms_data"),
    ]
    _ALLOWED_POPULATORS = {n[1] for n in nations_to_populate}

    for nation, module_name, func_name in nations_to_populate:
        if module_name not in _ALLOWED_POPULATORS:
            results[nation] = {"status": "error", "error": "module not allowlisted"}
            continue
        try:
            module = __import__(module_name)
            func = getattr(module, func_name)
            result = await func()
            results[nation] = {"status": "success", "result": result}
        except Exception as e:
            results[nation] = {"status": "error", "error": str(e)}
    
    # Ensure admin user exists
    await ensure_default_admin_user()
    
    return {
        "message": "Populated all nations!",
        "results": results,
        "next_step": "/api/initialize/nations-images for images"
    }


# Public initialization endpoint (for first-time setup)
@app.get("/api/initialize")
async def initialize_database():
    """
    Quick initialization - creates admin user and basic data WITHOUT images.
    Use /api/initialize/images after this to generate images.
    """
    results = {
        "admin_user": "unknown",
        "nations": 0,
        "cities": 0,
        "locations": 0,
        "message": ""
    }
    
    try:
        # First, ensure admin user exists
        await ensure_default_admin_user()
        results["admin_user"] = "created or verified"
        
        # Seed database WITHOUT images (fast)
        from seed_database import run_full_seed, set_database
        set_database(db)
        seed_results = await run_full_seed(with_images=False)
        
        results["nations"] = seed_results["nations"]
        results["cities"] = seed_results["cities"]
        results["locations"] = seed_results["locations"]
        results["message"] = "Database initialized! Now visit /api/initialize/nations-images to add nation images."
        
        if seed_results["errors"]:
            results["errors"] = seed_results["errors"]
            
    except Exception as e:
        results["message"] = f"Error during initialization: {str(e)}"
        results["error"] = str(e)
    
    return results


@app.get("/api/initialize/nations-images")
async def generate_nation_images():
    """Generate images for all nations (5 images, ~1-2 min)"""
    from seed_database import set_database, init_image_generator, generate_image, NATIONS_SEED
    set_database(db)
    
    if not init_image_generator():
        return {"error": "Image generator not available", "message": "Check EMERGENT_LLM_KEY"}
    
    images_created = 0
    for nation in NATIONS_SEED:
        existing = await db.nations.find_one({"slug": nation["slug"]})
        if existing and not existing.get("image_url"):
            print(f"Generating image for {nation['name']}...")
            image_url = await generate_image(nation["image_prompt"])
            if image_url:
                await db.nations.update_one(
                    {"slug": nation["slug"]},
                    {"$set": {"image_url": image_url}}
                )
                images_created += 1
    
    return {
        "images_created": images_created,
        "message": f"Created {images_created} nation images. Next: /api/initialize/city-images/ammeonon"
    }


@app.get("/api/initialize/city-images/{nation_slug}")
async def generate_city_images(nation_slug: str):
    """Generate images for cities in a specific nation (call per nation)"""
    from seed_database import set_database, init_image_generator, generate_image
    set_database(db)
    
    if not init_image_generator():
        return {"error": "Image generator not available"}
    
    cities = await db.cities.find({"nation": nation_slug, "image_url": {"$in": [None, ""]}}).to_list(100)
    
    images_created = 0
    for city in cities:
        prompt = f"Epic fantasy {city.get('entity_type', 'city')}: {city['name']}. {city.get('description', '')} Fantasy landscape, cinematic, detailed. High quality digital art."
        print(f"Generating image for {city['name']}...")
        image_url = await generate_image(prompt)
        if image_url:
            await db.cities.update_one(
                {"slug": city["slug"], "nation": nation_slug},
                {"$set": {"image_url": image_url}}
            )
            images_created += 1
        await asyncio.sleep(0.5)
    
    nations = ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]
    try:
        next_nation = nations[nations.index(nation_slug) + 1]
        next_step = f"/api/initialize/city-images/{next_nation}"
    except (ValueError, IndexError):
        next_step = "/api/initialize/location-images/ammeonon"
    
    return {
        "nation": nation_slug,
        "images_created": images_created,
        "message": f"Created {images_created} city images for {nation_slug}. Next: {next_step}"
    }


@app.get("/api/initialize/location-images/{nation_slug}")
async def generate_location_images(nation_slug: str, batch_size: int = 10):
    """Generate images for locations in a specific nation (batch processing)"""
    from seed_database import set_database, init_image_generator, generate_image
    set_database(db)
    
    if not init_image_generator():
        return {"error": "Image generator not available"}
    
    # Find locations without images
    locations = await db.locations.find({
        "nation": nation_slug, 
        "$or": [
            {"image_url": None},
            {"image_url": ""},
            {"image_url": {"$exists": False}}
        ]
    }).to_list(batch_size)
    
    if not locations:
        return {
            "nation": nation_slug,
            "images_created": 0,
            "remaining": 0,
            "message": f"No locations need images in {nation_slug}."
        }
    
    images_created = 0
    for loc in locations:
        prompt = f"Fantasy interior: {loc['name']}, a {loc.get('location_type', 'location')}. {loc.get('description', '')} Medieval fantasy, atmospheric. High quality digital art."
        print(f"Generating image for {loc['name']}...")
        image_url = await generate_image(prompt)
        if image_url:
            await db.locations.update_one(
                {"id": loc["id"]},
                {"$set": {"image_url": image_url}}
            )
            images_created += 1
        await asyncio.sleep(0.5)
    
    # Count remaining
    remaining = await db.locations.count_documents({
        "nation": nation_slug,
        "$or": [
            {"image_url": None},
            {"image_url": ""},
            {"image_url": {"$exists": False}}
        ]
    })
    
    return {
        "nation": nation_slug,
        "images_created": images_created,
        "remaining": remaining,
        "message": f"Created {images_created} images. {remaining} still need images. Call again to continue."
    }

# Initialize AI Quest Master
quest_master = QuestMasterAI()

# Initialize Image Generator (optional)
try:
    from image_generator import ImageGenerator
    image_gen = ImageGenerator()
except Exception as e:
    print(f"Image generator not available: {e}")
    image_gen = None

# ==================== ENUMS ====================
class QuestDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    LEGENDARY = "legendary"

class QuestState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Nation(str, Enum):
    AMMEONON = "Ammeonon"
    SELINDORI = "Selindori"
    DHOR_KHULDOR = "Dhor-Kuldor"
    AIGRAELS = "Aigraels"

class TransactionType(str, Enum):
    QUEST_REWARD = "quest_reward"
    SHOP_PURCHASE = "shop_purchase"
    SHOP_SALE = "shop_sale"
    INITIAL_BALANCE = "initial_balance"

# ==================== MODELS ====================

# User Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    application_text: str  # Why they want to join

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    currency: int = 1000
    role: str = "member"  # "admin", "moderator", "member"
    status: str = "pending"  # "pending", "active", "suspended", "banned"
    application_text: Optional[str] = None
    approved_by: Optional[str] = None  # User ID of admin who approved
    approved_at: Optional[datetime] = None
    suspended_until: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    ban_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    currency: int
    role: str
    status: str
    created_at: datetime

# Character Models
class CharacterCreate(BaseModel):
    name: str
    race: str  # Freeform - can be anything!
    character_class: str
    backstory: str
    powers: str
    appearance: str
    nation: Nation
    # Optional initial stat allocation (total 60 points)
    strength: int = 10
    magic: int = 10
    agility: int = 10
    endurance: int = 10
    charisma: int = 10
    luck: int = 10

class Character(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    race: str
    character_class: str
    backstory: str
    powers: str
    appearance: str
    nation: str
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    # Base Stats
    strength: int = 10
    magic: int = 10
    agility: int = 10
    endurance: int = 10
    charisma: int = 10
    luck: int = 10
    # Equipment System (8 slots)
    equipped: dict = Field(default_factory=lambda: {
        "weapon": None,
        "head": None,
        "chest": None,
        "legs": None,
        "boots": None,
        "gloves": None,
        "ring": None,
        "necklace": None
    })
    inventory: list = Field(default_factory=list)  # List of item objects
    # Portrait
    portrait_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Quest Models
class QuestCreate(BaseModel):
    title: str
    description: str
    difficulty: QuestDifficulty
    reward_currency: int
    reward_xp: Optional[int] = None  # Auto-calculated based on difficulty if not provided
    reward_items: list = Field(default_factory=list)  # List of item reward objects
    nation: Nation
    category: str
    max_acceptors: int = 10

class Quest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    creator_username: str
    title: str
    description: str
    difficulty: str
    reward_currency: int
    reward_xp: int = 50  # Default XP reward
    reward_items: list = Field(default_factory=list)  # List of item reward objects
    nation: str
    category: str
    max_acceptors: int
    current_acceptors: int = 0
    status: str = "open"
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QuestAcceptance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quest_id: str
    user_id: str
    character_id: str
    status: str = "accepted"
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

# ==================== STARTUP HOOKS ====================

@app.on_event("startup")
async def resume_image_batch_if_orphaned() -> None:
    """CRITICAL fix for the 'image batch never finishes across sessions'
    bug (iteration_23 report). uvicorn --reload and Kubernetes pod
    restarts silently kill the in-memory asyncio task. On every boot,
    check the persisted job state — if the last run was `is_running` +
    `auto_continue` when the process died AND there's still work to do,
    auto-resume the batch."""
    try:
        from city_location_image_batcher import CityLocationImageBatcher
        result = await CityLocationImageBatcher.resume_if_needed(db)
        if result.get("resumed"):
            logger.info(
                f"image_batch auto-resumed on startup — "
                f"{result.get('missing_before_resume')} items pending"
            )
    except Exception as e:
        logger.warning(f"image_batch resume_if_needed failed on startup: {e}")


@app.on_event("startup")
async def ensure_default_admin_user() -> None:
    """Ensure a default admin user exists in the configured database.

    This is primarily to keep dev and deployed environments in sync so that
    the known admin credentials work everywhere. In production, you can
    override these via ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_USERNAME
    environment variables.
    """
    admin_email = os.environ.get("ADMIN_EMAIL", "craftnn1222@gmail.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin_username = os.environ.get("ADMIN_USERNAME", "Ausar Veltraus")

    # If env vars are explicitly disabled, skip seeding
    if not admin_email or not admin_password:
        return

    existing = await db.users.find_one({"email": admin_email})
    password_hash = hash_password(admin_password)
    now = datetime.now(timezone.utc).isoformat()

    if existing:
        # Ensure existing user is an active admin and reset password so known
        # credentials work consistently across environments.
        update_fields = {
            "role": "admin",
            "status": "active",
            "password_hash": password_hash,
        }
        if not existing.get("approved_by"):
            update_fields["approved_by"] = "system"
        if not existing.get("approved_at"):
            update_fields["approved_at"] = now

        await db.users.update_one({"email": admin_email}, {"$set": update_fields})
        return

    # Create new admin user with the configured/default credentials
    admin_id = str(uuid.uuid4())

    user_doc = {
        "id": admin_id,
        "username": admin_username,
        "email": admin_email,
        "password_hash": password_hash,
        "currency": 1000,
        "role": "admin",
        "status": "active",
        "application_text": "Site Owner & Administrator",
        "approved_by": "system",
        "approved_at": now,
        "suspended_until": None,
        "suspension_reason": None,
        "ban_reason": None,
        "created_at": now,
    }

    await db.users.insert_one(user_doc)

    # Seed initial transaction for the admin user
    transaction = Transaction(
        user_id=admin_id,
        amount=1000,
        transaction_type=TransactionType.INITIAL_BALANCE,
        description="Welcome to Delarom! Starting balance.",
    )
    trans_doc = transaction.model_dump()
    trans_doc["created_at"] = trans_doc["created_at"].isoformat()
    await db.transactions.insert_one(trans_doc)


# Quest Action Models (for AI roleplay)
class QuestActionCreate(BaseModel):
    action_text: str

class QuestAction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quest_id: str
    user_id: str
    character_id: str
    character_name: str
    character_race: str
    character_class: str
    action_text: str
    ai_response: Optional[str] = None
    is_valid_t1: bool = True
    t1_feedback: Optional[str] = None
    turn_number: int
    # Dice roll data
    dice_roll: Optional[int] = None  # D20 result
    modifier: Optional[int] = None  # Stat modifier applied
    total_roll: Optional[int] = None  # dice_roll + modifier
    was_critical: bool = False  # Natural 20
    was_fumble: bool = False  # Natural 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QuestParticipationModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quest_id: str
    user_id: str
    character_id: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

# Shop Models
class ShopCreate(BaseModel):
    name: str
    description: str
    nation: Nation

class Shop(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    owner_username: str
    name: str
    description: str
    nation: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ItemCreate(BaseModel):
    name: str
    description: str
    price: int
    stock: int
    category: str
    item_type: str = "equipment"
    equipment_slot: Optional[str] = None
    stat_bonuses: dict = Field(default_factory=dict)
    # Economy-sourced auto-pricing (2026-02-14). Optional; legacy items leave
    # `is_auto_priced=False` and stay manually priced.
    source_good_slug: Optional[str] = None
    source_city_slug: Optional[str] = None
    source_nation: Optional[str] = None
    markup_pct: Optional[int] = None
    is_auto_priced: bool = False

class Item(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shop_id: str
    name: str
    description: str
    price: int
    stock: int
    category: str
    # Equipment Properties
    item_type: str = "equipment"  # "equipment" or "consumable"
    equipment_slot: Optional[str] = None  # "weapon", "head", "chest", "legs", "boots", "gloves", "ring", "necklace"
    stat_bonuses: dict = Field(default_factory=dict)  # {"strength": 5, "magic": 10, etc.}
    # Economy-sourced auto-pricing fields. When `is_auto_priced=True` and the
    # source_* fields are set, `price` is recomputed from the goods catalogue
    # rather than typed manually. Owners can refresh via /items/{id}/refresh-price.
    source_good_slug: Optional[str] = None
    source_city_slug: Optional[str] = None
    source_nation: Optional[str] = None
    markup_pct: Optional[int] = None
    is_auto_priced: bool = False
    last_repriced_at: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Transaction Model
class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: int
    transaction_type: str
    description: str
    related_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Location Roleplay Models
class LocationRPCreate(BaseModel):
    action_text: str

class LocationRP(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nation: str
    location: str  # City/place name
    user_id: str
    character_id: str
    character_name: str
    action_text: str
    ai_response: Optional[str] = None
    dice_roll: Optional[int] = None
    modifier: Optional[int] = None
    total_roll: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============ NPC Memory / Scene Event Models ============

class NPCCreatePayload(BaseModel):
    name: str
    race: Optional[str] = "Unknown"
    role: Optional[str] = "Local"
    appearance: Optional[str] = ""
    personality: Optional[str] = ""
    motivation: Optional[str] = ""
    background: Optional[str] = ""
    quirks: Optional[str] = ""
    importance: Optional[str] = "commoner"
    overall_mood: Optional[str] = "neutral"
    mood_score: Optional[int] = 0
    status: Optional[str] = "alive"
    status_note: Optional[str] = ""


class NPCUpdatePayload(BaseModel):
    name: Optional[str] = None
    race: Optional[str] = None
    role: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    background: Optional[str] = None
    quirks: Optional[str] = None
    importance: Optional[str] = None
    overall_mood: Optional[str] = None
    mood_score: Optional[int] = None
    status: Optional[str] = None
    status_note: Optional[str] = None


class LocationEventCreatePayload(BaseModel):
    event_type: str
    summary: str
    description: Optional[str] = ""
    intensity: Optional[str] = "moderate"
    participants: Optional[List[str]] = None
    npc_participants: Optional[List[str]] = None


class LocationEventStatusPayload(BaseModel):
    status: str  # active | resolved | decayed
    resolution_note: Optional[str] = None


class NationRelationPayload(BaseModel):
    nation_a: str
    nation_b: str
    score: int
    reason: Optional[str] = "admin update"


class NationRelationDeltaPayload(BaseModel):
    nation_a: str
    nation_b: str
    delta: int
    reason: Optional[str] = "admin adjustment"


class WorldEventCreatePayload(BaseModel):
    event_type: str
    scope: Optional[str] = "world"  # world | diplomatic | local
    summary: str
    details: Optional[str] = ""
    nations: Optional[List[str]] = None


# Location Management Models
class LocationAreaBase(BaseModel):
    nation: str  # URL slug, e.g. "ammeonon", "dhor-kuldor"
    city: Optional[str] = None  # City slug, e.g. "vargath", "astra-lun"
    slug: str    # Location slug used in URLs, e.g. "wymroost"
    name: str    # Display name
    location_type: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    is_active: bool = True
    is_rp_enabled: bool = True


class LocationArea(LocationAreaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LocationAreaUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_rp_enabled: Optional[bool] = None


# Lightweight location model for list responses (excludes large image_url field)
class LocationAreaListItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    nation: str
    city: Optional[str] = None
    slug: str
    name: str
    location_type: Optional[str] = None
    description: str
    is_active: bool = True
    is_rp_enabled: bool = True
    has_image: bool = False  # Indicates if an image exists without sending it
    # Contested Cities — siege / control state
    controlling_faction_slug: Optional[str] = None
    controlling_faction_name: Optional[str] = None
    siege_state: Optional[dict] = None


# City Models
class CityBase(BaseModel):
    nation: str  # URL slug, e.g. "aigraels"
    slug: str    # City slug, e.g. "vargath", "astra-lun"
    name: str    # Display name
    region: Optional[str] = None  # Region name (e.g., "Vargath Region", "Lysanthea Region")
    description: str
    lore: Optional[str] = None
    faction: Optional[str] = None  # For Aigraels: "Ardent Legion", "Forsaken Court", etc.
    image_url: Optional[str] = None
    is_active: bool = True


class City(CityBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Lightweight city model for list responses (excludes large image_url field)
class CityListItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    nation: str
    slug: str
    name: str
    region: Optional[str] = None
    description: str
    lore: Optional[str] = None
    faction: Optional[str] = None
    entity_type: Optional[str] = None
    is_active: bool = True
    has_image: bool = False  # Indicates if an image exists without sending it


# Nation Models
class NationInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str
    name: str
    image_url: Optional[str] = None


class CityUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    lore: Optional[str] = None
    faction: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class CreatorCompleteRequest(BaseModel):
    acceptance_id: str



# Payload models for flexible parameter handling
class QuestAcceptRequest(BaseModel):
    character_id: str


class PurchaseRequest(BaseModel):
    character_id: str


class EquipRequest(BaseModel):
    inventory_item_id: str


class UnequipRequest(BaseModel):
    equipment_slot: str


class ForumPostCreate(BaseModel):
    title: str
    content: str
    category: str
    nation: Nation
    character_id: str

class ForumPost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    username: str
    character_id: str
    character_name: str
    title: str
    content: str
    category: str
    nation: str
    replies_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ForumReplyCreate(BaseModel):
    content: str
    character_id: str

class ForumReply(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    post_id: str
    user_id: str
    username: str
    character_id: str
    character_name: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== AUTH UTILITIES ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


# ==================== TIER 2b — ESSENCE AFFINITY HINTING ====================

_ESSENCE_KEYWORDS = {
    "fire":     ("fire", "flame", "burn", "ember", "ignite", "pyromancy", "scorch", "blaze", "infernal"),
    "water":    ("water", "tide", "ocean", "sea", "wave", "hydromancy", "river", "rain"),
    "frost":    ("frost", "ice", "freeze", "cold", "snow", "winter", "glacial", "rime"),
    "earth":    ("earth", "stone", "rock", "tremor", "quake", "mountain", "iron", "metal", "geomancy"),
    "air":      ("air", "wind", "gust", "breeze", "aero", "skyborn", "aeromancy"),
    "lightning":("lightning", "thunder", "storm", "spark", "shock", "voltaic", "electric"),
    "light":    ("light", "radiant", "solar", "sun", "luminous", "dawn", "blessed"),
    "shadow":   ("shadow", "umbral", "dark", "void", "nightshade", "obsidian", "shade", "necro"),
    "life":     ("heal", "mend", "restore", "verdant", "growth", "life", "bloom"),
    "astral":   ("astral", "chakra", "starlight", "celestial", "moon", "aether"),
}


def _scan_essence_hints(*, powers: str = "", char_class: str = "", race: str = "") -> list:
    """Lightweight keyword scanner. Infers up to 3 likely essence affinities
    from a character's freeform powers, class, and race. Passed to the AI
    only as HINTS — the final spell judgement remains the AI's."""
    haystack = " ".join([powers or "", char_class or "", race or ""]).lower()
    if not haystack.strip():
        return []
    matches: list = []
    for essence, keywords in _ESSENCE_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            matches.append(essence)
    race_lc = (race or "").lower()
    if "fire elf" in race_lc and "fire" not in matches: matches.insert(0, "fire")
    if "sun elf" in race_lc and "light" not in matches: matches.insert(0, "light")
    if "moon elf" in race_lc and "shadow" not in matches: matches.insert(0, "shadow")
    if "shadow elf" in race_lc and "shadow" not in matches: matches.insert(0, "shadow")
    if "wood elf" in race_lc and "life" not in matches:   matches.insert(0, "life")
    if "tide elf" in race_lc and "water" not in matches:  matches.insert(0, "water")
    if "dwarf" in race_lc and "earth" not in matches:     matches.append("earth")
    return matches[:3]


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ------------------------------------------------------------------
# httpOnly cookie helpers
# ------------------------------------------------------------------
# We store the JWT in an httpOnly cookie so it cannot be exfiltrated by XSS.
# The Authorization: Bearer header path is still accepted as a fallback so
# server-to-server scripts / curl / Postman keep working unchanged.

COOKIE_NAME = "access_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")
COOKIE_MAX_AGE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60


def set_auth_cookie(response: FastAPIResponse, token: str) -> None:
    """Attach the JWT to the response as an httpOnly cookie."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE_SECONDS,
        path="/",
    )


def clear_auth_cookie(response: FastAPIResponse) -> None:
    """Remove the JWT cookie from the client (Max-Age=0)."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        httponly=True,
    )


def _extract_token(request: Request) -> Optional[str]:
    """Return the JWT — preferring the httpOnly cookie, falling back to the
    `Authorization: Bearer <token>` header for back-compat with scripts and
    any in-flight clients during cutover."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip() or None
    return None


async def get_current_user(request: Request) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user_doc is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Parse datetime fields
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    if isinstance(user_doc.get('approved_at'), str):
        user_doc['approved_at'] = datetime.fromisoformat(user_doc['approved_at'])
    if isinstance(user_doc.get('suspended_until'), str):
        user_doc['suspended_until'] = datetime.fromisoformat(user_doc['suspended_until'])
    
    user = User(**user_doc)
    
    # Check if user is banned or suspended
    if user.status == "banned":
        raise HTTPException(status_code=403, detail="Account is banned")
    if user.status == "suspended":
        if user.suspended_until and user.suspended_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Account is suspended")
    if user.status == "pending":
        raise HTTPException(status_code=403, detail="Account pending approval")
    
    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user is admin"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if user is admin or moderator"""
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Moderator access required")
    return current_user

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=dict)
async def register(user_data: UserRegister, request: Request, response: FastAPIResponse):
    # Get client IP address
    client_ip = request.client.host if request.client else None
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Check if IP is banned
    if client_ip:
        ip_ban = await db.ip_bans.find_one({"ip_address": client_ip, "is_active": True})
        if ip_ban:
            raise HTTPException(
                status_code=403, 
                detail=f"Registration denied. Your IP address has been banned. Reason: {ip_ban.get('reason', 'Violation of platform rules')}"
            )
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user with pending status (requires admin approval)
    user = User(
        username=user_data.username,
        email=user_data.email,
        currency=1000,
        role="member",
        status="pending",  # Pending admin approval
        application_text=user_data.application_text
    )
    
    user_doc = user.model_dump()
    user_doc['password_hash'] = hash_password(user_data.password)
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    if user_doc.get('approved_at'):
        user_doc['approved_at'] = user_doc['approved_at'].isoformat()
    if user_doc.get('suspended_until'):
        user_doc['suspended_until'] = user_doc['suspended_until'].isoformat()
    
    # Track registration IP
    if client_ip:
        user_doc['registration_ip'] = client_ip
        user_doc['last_ip_address'] = client_ip
    
    await db.users.insert_one(user_doc)
    
    # Create initial transaction
    transaction = Transaction(
        user_id=user.id,
        amount=1000,
        transaction_type=TransactionType.INITIAL_BALANCE,
        description="Welcome to Delarom! Starting balance."
    )
    trans_doc = transaction.model_dump()
    trans_doc['created_at'] = trans_doc['created_at'].isoformat()
    await db.transactions.insert_one(trans_doc)
    
    # Create token + set httpOnly cookie
    access_token = create_access_token({"sub": user.id})
    set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user.model_dump())
    }

@api_router.post("/auth/login", response_model=dict)
async def login(user_data: UserLogin, request: Request, response: FastAPIResponse):
    # Get client IP address
    client_ip = request.client.host if request.client else None
    # Check for forwarded IP (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Check if IP is banned
    if client_ip:
        ip_ban = await db.ip_bans.find_one({"ip_address": client_ip, "is_active": True})
        if ip_ban:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Your IP address has been banned. Reason: {ip_ban.get('reason', 'Violation of platform rules')}"
            )
    
    user_doc = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user_data.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Normalize legacy users that predate the application system
    update_fields: dict = {}
    if not user_doc.get('status'):
        user_doc['status'] = 'active'
        update_fields['status'] = 'active'
    if not user_doc.get('role'):
        user_doc['role'] = 'member'
        update_fields['role'] = 'member'
    
    # Track IP address
    if client_ip:
        update_fields['last_ip_address'] = client_ip
        update_fields['last_login_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_fields:
        await db.users.update_one({"id": user_doc["id"]}, {"$set": update_fields})
        # Update local copy for response
        user_doc.update(update_fields)
    
    # Parse datetime fields
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    if isinstance(user_doc.get('approved_at'), str):
        user_doc['approved_at'] = datetime.fromisoformat(user_doc['approved_at'])
    if isinstance(user_doc.get('suspended_until'), str):
        user_doc['suspended_until'] = datetime.fromisoformat(user_doc['suspended_until'])
    
    user = User(**user_doc)
    
    # Check user status
    if user.status == "banned":
        raise HTTPException(status_code=403, detail=f"Account banned. Reason: {user.ban_reason or 'No reason provided'}")
    
    if user.status == "suspended":
        if user.suspended_until and user.suspended_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail=f"Account suspended until {user.suspended_until.strftime('%Y-%m-%d %H:%M')}. Reason: {user.suspension_reason or 'No reason provided'}")
        else:
            # Suspension expired, reactivate
            await db.users.update_one(
                {"id": user.id},
                {"$set": {"status": "active", "suspended_until": None, "suspension_reason": None}}
            )
            user.status = "active"
    
    # Only treat users as pending if they actually have an application_text
    if user.status == "pending" and user.application_text:
        raise HTTPException(status_code=403, detail="Your application is pending admin approval. Please wait for approval before logging in.")
    
    access_token = create_access_token({"sub": user.id})
    set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user.model_dump())
    }

@api_router.post("/auth/logout")
async def logout(response: FastAPIResponse):
    """Clear the httpOnly auth cookie. Always 200 — idempotent."""
    clear_auth_cookie(response)
    return {"ok": True}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.model_dump())


# ==================== WORLD CLOCK + FESTIVALS ====================
# Phase 1 of the Atmospheric Foundations sprint (2026-05-30).
from routes.world_clock import attach_world_clock_routes
attach_world_clock_routes(api_router, db=db)


# ==================== PHASE 2: PLAYER-TO-PLAYER COMMUNICATION ====================
# Letters / Tavern Boards / Sworn Bonds (2026-05-30).
# Note: these need `_resolve_character_for_user`, which is defined later in this
# file. We register them just below that helper (search for "PHASE 2 ROUTES").


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, description="Min 6 characters")


@api_router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """Let a logged-in user change their own password.

    Verifies `current_password` against the stored bcrypt hash, then stores
    a fresh hash of `new_password`. Returns `{ok: true}` on success.
    """
    user_doc = await db.users.find_one({"id": current_user.id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user_doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    new_hash = hash_password(payload.new_password)
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password_hash": new_hash}},
    )
    return {"ok": True, "message": "Password updated successfully"}


# ==================== ADMIN / MODERATION ROUTES ====================
# Extracted to routes/admin.py (2026-05-30 refactor).
from routes.admin import attach_admin_routes
attach_admin_routes(
    api_router,
    db=db, User=User, UserResponse=UserResponse,
    require_admin=require_admin, require_moderator=require_moderator,
    hash_password=hash_password,
    logger=logger,
)



# ==================== PUBLIC MEMBER DIRECTORY ROUTE ====================

@api_router.get("/public/members-directory")
async def get_members_directory():
    """Public-facing member directory: lists active users and their characters.

    Only exposes safe fields: username, role, and basic character bios.
    """
    # Fetch all active users (approved members)
    users = await db.users.find(
        {"status": "active"},
        {"_id": 0, "password_hash": 0, "application_text": 0, "ban_reason": 0,
         "suspension_reason": 0, "suspended_until": 0, "currency": 0, "approved_by": 0,
         "approved_at": 0, "email": 0}
    ).to_list(1000)

    # Map user_id -> user info
    user_map = {u["id"]: u for u in users}
    user_ids = list(user_map.keys())

    if not user_ids:
        return []

    # Fetch characters belonging to these users
    characters = await db.characters.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "inventory": 0, "equipped": 0}
    ).to_list(5000)

    # Group characters by user_id
    for u in users:
        u["characters"] = []

    for char in characters:
        uid = char.get("user_id")
        if uid in user_map:
            # Keep only fields useful for the directory
            char_slim = {
                "id": char.get("id"),
                "name": char.get("name"),
                "nation": char.get("nation"),
                "race": char.get("race"),
                "character_class": char.get("character_class"),
                "backstory": char.get("backstory"),
                "appearance": char.get("appearance"),
                "portrait_url": char.get("portrait_url"),
            }
            user_map[uid].setdefault("characters", []).append(char_slim)

    # Return as a list (order by username for consistency)
    directory = sorted(user_map.values(), key=lambda u: u.get("username", ""))
    return directory



# ==================== CHARACTER ROUTES ====================
# Extracted to routes/characters.py (2026-05-30 refactor).
from routes.characters import attach_character_routes
attach_character_routes(
    api_router,
    db=db, User=User, get_current_user=get_current_user,
    Character=Character, CharacterCreate=CharacterCreate,
)


# ==================== QUEST + T1 JUDGE ROUTES ====================
# Extracted to routes/quests.py (2026-05-30 refactor).
from routes.quests import attach_quest_routes
attach_quest_routes(
    api_router,
    db=db, User=User, get_current_user=get_current_user, require_moderator=require_moderator,
    Quest=Quest, QuestCreate=QuestCreate,
    QuestAcceptance=QuestAcceptance, QuestAcceptRequest=QuestAcceptRequest,
    QuestAction=QuestAction, QuestActionCreate=QuestActionCreate,
    Transaction=Transaction, TransactionType=TransactionType,
    quest_master=quest_master, logger=logger,
)

# ==================== WALLET + SHOP + ITEM + EQUIPMENT ROUTES ====================
# Extracted to routes/shops.py (2026-05-30 refactor).
from routes.shops import attach_shop_routes
attach_shop_routes(
    api_router,
    db=db, User=User, get_current_user=get_current_user,
    Shop=Shop, ShopCreate=ShopCreate, Item=Item, ItemCreate=ItemCreate,
    Transaction=Transaction, TransactionType=TransactionType,
    EquipRequest=EquipRequest, UnequipRequest=UnequipRequest, PurchaseRequest=PurchaseRequest,
)


# ==================== IMAGE GENERATION ROUTES ====================
# Extracted to routes/image_gen.py (2026-05-30 refactor).
from routes.image_gen import attach_image_gen_routes
attach_image_gen_routes(api_router, db=db, User=User, get_current_user=get_current_user, image_gen=image_gen, logger=logger)


# ==================== LOCATION ROLEPLAY ROUTES ====================


async def _auto_arrest_and_imprison(
    *,
    db,
    law_service,
    world_service,
    character_id: str,
    character_name: str,
    user_id: str,
    nation: str,
    location: str,
    arrest_reason: str,
) -> Optional[Dict]:
    """Triggered when the AI's narration shows the player visibly subdued.

    Starts a COURTROOM TRIAL — the player is moved to the city's courthouse
    and may defend themselves before the verdict. If no open crimes exist,
    seeds a `resisting_authority` minor crime so the trial has something to
    consider. Returns the trial payload (incl. courthouse location + judge +
    witnesses), or None on hard failure.
    """
    from courtroom_service import CourtroomService
    from routes.courtroom import create_trial_from_open_crimes

    crt = CourtroomService(db)
    if await crt.get_active_trial(character_id):
        # Already on trial — don't stack.
        return None

    open_crimes = await law_service.list_open_crimes_in_nation(character_id, nation, limit=10)
    if not open_crimes:
        # AI flagged an arrest but no crime is on file — log a public-disorder
        # crime so the trial has something to chew on. The PHYSICAL-TOUCH rule
        # in the prompt is the most common trigger for this branch.
        try:
            await law_service.record_crime(
                character_id=character_id,
                character_name=character_name,
                user_id=user_id,
                nation=nation,
                location=location,
                crime_type="resisting_authority",
                severity="minor",
                victim_name="The Watch",
                victim_importance="notable",
                description=(arrest_reason or "Subdued by lawful authority.")[:200],
            )
        except Exception as crime_err:
            logger.error(f"Auto-arrest seed-crime insert failed: {crime_err}")
            return None

    try:
        result = await create_trial_from_open_crimes(
            db=db,
            law_service=law_service,
            character_id=character_id,
            character_name=character_name,
            user_id=user_id,
            nation=nation,
            origin_location=location,
            logger=logger,
        )
    except Exception as trial_err:
        logger.error(f"Auto-arrest trial creation failed: {trial_err}")
        return None
    if not result:
        return None

    return {
        "arrest_executed": True,
        "arrest_reason": arrest_reason,
        "trial": result["trial"],
        "courthouse_nation": nation,
        "courthouse_location": result["courthouse_location"],
        "judge_name": result.get("judge_name"),
        "prosecutor_name": result.get("prosecutor_name"),
        "witnesses": result.get("witnesses", []),
    }


@api_router.post("/locations/{nation}/{location}/roleplay")
async def submit_location_rp(
    nation: str,
    location: str,
    rp_data: LocationRPCreate,
    current_user: User = Depends(get_current_user)
):
    """Submit a roleplay action in a specific location"""
    # Get user's characters
    characters = await db.characters.find({"user_id": current_user.id}, {"_id": 0}).to_list(10)
    if not characters:
        raise HTTPException(status_code=400, detail="You need to create a character first")
    
    # Use first character
    char = characters[0]
    
    # Prepare character bio for AI context (no stats/levels)
    character_bio = {
        'name': char.get('name', ''),
        'race': char.get('race', ''),
        'class': char.get('character_class', ''),
        'backstory': char.get('backstory', ''),
        'powers': char.get('powers', ''),
        'appearance': char.get('appearance', '')
    }
    
    # Get recent actions for context
    recent_actions = await db.location_rp.find(
        {"nation": nation, "location": location},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Format recent actions for AI
    formatted_history = []
    for action in reversed(recent_actions[-5:]):
        formatted_history.append({
            'player_text': f"{action['character_name']}: {action['action_text']}",
            'npc_response': action.get('ai_response', '')
        })

    # Build persistent world-state for this scene (NPCs + active events)
    npc_service = NPCMemoryService(db)
    world_service = WorldStateService(db)
    law_service = LawService(db)

    # LAW SYSTEM: enforce imprisonment — locked characters can only roleplay
    # from inside their jail. Any RP action at a different location is rejected.
    imprisonment = None
    active_trial = None
    if law_system_enabled():
        try:
            imprisonment = await law_service.get_active_imprisonment(char['id'])
        except Exception as law_err:
            logger.error(f"Imprisonment lookup failed: {law_err}")
            imprisonment = None
        if imprisonment and (imprisonment.get("jail_location") != location
                              or imprisonment.get("nation") != nation):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"{char['name']} is imprisoned in "
                    f"{imprisonment.get('jail_location')} ({imprisonment.get('nation')}). "
                    "Roleplay is restricted to that location until sentence is served, "
                    "escape succeeds, or pardon is granted."
                ),
            )

        # COURTROOM TRIAL: while a trial is in session, the player can ONLY
        # roleplay from inside the assigned courthouse. Free-form RP is
        # disabled there — they must use the dedicated trial defence flow
        # (POST /api/characters/{id}/trial/defend or /trial/rest-case).
        try:
            from courtroom_service import CourtroomService
            active_trial = await CourtroomService(db).get_active_trial(char['id'])
        except Exception as trial_err:
            logger.error(f"Active-trial lookup failed: {trial_err}")
            active_trial = None
        if active_trial:
            ch_loc = active_trial.get("courthouse_location")
            ch_nation = active_trial.get("nation")
            if ch_loc != location or ch_nation != nation:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"{char['name']} stands trial in {ch_loc} ({ch_nation}). "
                        "Free RP is disabled until the verdict is delivered — defend yourself "
                        "in the courtroom or rest your case."
                    ),
                )
            raise HTTPException(
                status_code=409,
                detail=(
                    "Free-form RP is paused while a trial is in session. Use the courtroom "
                    "defence panel to argue your case, or rest your case to receive the verdict."
                ),
            )

    # Process any pending cascades that have matured and target this location/nation
    try:
        await world_service.process_due_cascades_for_location(nation, location, npc_service)
    except Exception as cascade_err:
        logger.error(f"Cascade processing failed: {cascade_err}")

    try:
        scene_state = await npc_service.build_scene_state(nation, location, char['id'])
    except Exception as scene_err:
        logger.error(f"Failed to build scene state: {scene_err}")
        scene_state = {"npcs": [], "events": []}

    # Reputation + diplomacy + hostility hint for the AI prompt (all HIDDEN from player)
    try:
        reputation = await world_service.get_reputation(char['id'], nation)
        all_relations = await world_service.list_nation_relations()
        hostility = await world_service.check_hostility_trigger(char['id'], nation)
        scene_state["reputation"] = reputation
        scene_state["diplomacy"] = all_relations
        scene_state["hostility"] = hostility
    except Exception as world_err:
        logger.error(f"Failed to build world-state extras: {world_err}")
        scene_state.setdefault("reputation", {})
        scene_state.setdefault("diplomacy", [])
        scene_state.setdefault("hostility", {})

    # LAW SYSTEM: inject criminal record + bounty into scene state so the AI
    # makes guards / NPCs react appropriately. Bounded at 5 most recent crimes
    # in this nation only to keep prompt size in check.
    if law_system_enabled():
        try:
            open_crimes_here = await law_service.list_open_crimes_in_nation(
                char['id'], nation, limit=5
            )
            bounty_here = await law_service.get_bounty(char['id'], nation)
            scene_state["criminal_record_here"] = open_crimes_here
            scene_state["bounty_here"] = bounty_here
            scene_state["criminal_record_text"] = LawService.format_record_for_prompt(
                open_crimes_here, bounty_here
            )
            scene_state["imprisonment"] = imprisonment
        except Exception as law_err:
            logger.error(f"Failed to fetch criminal record: {law_err}")
            scene_state.setdefault("criminal_record_here", [])
            scene_state.setdefault("bounty_here", None)
            scene_state.setdefault("criminal_record_text", "")
            scene_state.setdefault("imprisonment", None)
    else:
        scene_state.setdefault("criminal_record_here", [])
        scene_state.setdefault("bounty_here", None)
        scene_state.setdefault("criminal_record_text", "")
        scene_state.setdefault("imprisonment", None)

    # World clock + active festivals — atmospheric injection (Phase 1, 2026-05-30).
    # Best-effort; never blocks the scene if anything goes wrong.
    try:
        from world_clock_service import get_world_clock
        from festival_service import FestivalService
        clock = get_world_clock()
        scene_state["world_time"] = clock["time_of_day"]
        scene_state["delarom_date"] = clock["delarom_date"]
        # ── Iteration A: full in-world calendar (year advances) ─────
        # `clock.calendar` is populated by world_clock_service → world_calendar_service.
        # Format for the MoC: "the 12th of Frostmere, 217 A.E."
        calendar = clock.get("calendar") or {}
        if calendar:
            scene_state["world_date"] = calendar.get("formatted")
            scene_state["world_year"] = calendar.get("year")
            scene_state["world_year_label"] = calendar.get("year_label")
            scene_state["world_month_name"] = calendar.get("month_name")
        active = await FestivalService(db).get_active(nation=nation)
        scene_state["active_festivals"] = active
    except Exception as clock_err:
        logger.error(f"Failed to fetch world clock: {clock_err}")
        scene_state.setdefault("world_time", None)
        scene_state.setdefault("active_festivals", [])

    # FAMILY & BLOODLINE — inject acting character's declared relatives so the
    # AI may reference them (Phase 3, 2026-05-30). Best-effort.
    try:
        scene_state["character_relatives"] = (char or {}).get("relatives", []) or []
    except Exception:
        scene_state["character_relatives"] = []

    # WHISPERED RUMORS — pull recent active rumors for this nation so NPCs
    # may reference them in chatter (Phase 5, 2026-05-30). Best-effort, bounded.
    try:
        from datetime import datetime as _dt, timezone as _tz
        now_iso = _dt.now(_tz.utc).isoformat()
        rumor_cursor = db.rumors.find(
            {"nation": nation, "expires_at": {"$gt": now_iso}},
            {"_id": 0, "text": 1, "subject_name": 1, "subject_kind": 1, "judgement": 1},
        ).sort("planted_at", -1)
        rumors = await rumor_cursor.to_list(5)
        scene_state["active_rumors"] = rumors
    except Exception:
        scene_state["active_rumors"] = []

    # PROPHECY — inject the character's prophecy (if any) so the AI may foreshadow.
    try:
        prophecy = (char or {}).get("prophecy") or None
        scene_state["prophecy"] = prophecy
    except Exception:
        scene_state["prophecy"] = None

    # TIER 2a — ACTIVE BLESSINGS from the Four Elder Gods prayer system.
    # Blessings/flickers persist ~6h and subtly colour every subsequent scene.
    try:
        from prayer_service import PrayerService
        scene_state["active_blessings"] = await PrayerService(db).get_active_blessings(char["id"])
    except Exception as _blessing_err:
        logger.warning(f"active blessings fetch failed: {_blessing_err}")
        scene_state["active_blessings"] = []

    # ELDER-GODS FESTIVAL — if today is a canonical festival day, surface
    # the atmosphere so the AI can weave it into every scene (streamers,
    # processions, temple crowds, weekly minor rites). Best-effort.
    try:
        from elder_gods_festivals import get_active_festival
        scene_state["active_elder_festival"] = get_active_festival()
    except Exception as _fest_err:
        logger.warning(f"elder festival lookup failed: {_fest_err}")
        scene_state["active_elder_festival"] = None

    # TIER 2b — ACT MAGIC PROFILE. Surface the character's magic stat,
    # freeform powers description, race, and nation so the prompt can judge
    # spell attempts realistically.
    try:
        scene_state["character_magic_stat"] = (char or {}).get("magic", 0) or 0
        scene_state["character_powers"] = (char or {}).get("powers", "") or ""
        scene_state["character_race"] = (char or {}).get("race", "") or ""
        scene_state["nation"] = nation
        scene_state["has_tongue_of_yros"] = bool((char or {}).get("has_tongue_of_yros"))
        # Essence-affinity hints (keyword scan of powers + class + race).
        scene_state["character_essence_hints"] = _scan_essence_hints(
            powers=(char or {}).get("powers", ""),
            char_class=(char or {}).get("character_class", ""),
            race=(char or {}).get("race", ""),
        )
    except Exception as _magic_err:
        logger.warning(f"ACT magic scene injection failed: {_magic_err}")
        scene_state.setdefault("character_magic_stat", 0)
        scene_state.setdefault("character_powers", "")
        scene_state.setdefault("character_race", "")
        scene_state.setdefault("character_essence_hints", [])
        scene_state.setdefault("has_tongue_of_yros", False)

    # ── ECONOMY TICK (6h in-world) ────────────────────────────────
    # Any RP action is an opportunity to advance the economy — if 6h
    # have passed since the last tick, run production + trade-company
    # routes in the background. Best-effort; never blocks the scene.
    try:
        from producers_service import EconomyProducers
        await EconomyProducers(db).maybe_run_tick()
    except Exception as _econ_err:
        logger.warning(f"Economy tick check failed: {_econ_err}")

    # TIER 2d — TITAN SACRED SITES. If the current location sits on a
    # Titan-themed sacred site, the AI weaves the themed atmosphere.
    try:
        loc_doc = await db.locations.find_one(
            {"nation": nation, "slug": location},
            {"_id": 0, "titan_sacred_site": 1, "is_sacred": 1, "tongue_of_yros": 1, "name": 1},
        )
        if loc_doc:
            site = (loc_doc.get("titan_sacred_site") or "").strip().lower() or None
            scene_state["titan_sacred_site"] = site if site else None
            scene_state["is_sacred_location"] = bool(loc_doc.get("is_sacred") or loc_doc.get("tongue_of_yros"))
        else:
            scene_state["titan_sacred_site"] = None
            scene_state["is_sacred_location"] = False
    except Exception as _titan_err:
        logger.warning(f"titan sacred site lookup failed: {_titan_err}")
        scene_state["titan_sacred_site"] = None
        scene_state["is_sacred_location"] = False

    # PERSONA / DISGUISE — when active, the AI sees the persona name + race
    # instead of the real character, and the criminal/bounty blocks are
    # hidden so the disguise actually works. (Phase 4, 2026-05-30.)
    persona = (char or {}).get("persona") or None
    if persona and persona.get("active"):
        scene_state["persona_active"] = True
        scene_state["persona_name"] = persona.get("name") or "a stranger"
        scene_state["persona_race"] = persona.get("race") or ""
        scene_state["persona_background"] = persona.get("background") or ""
        # Heuristic: how infamous is the REAL character? The AI uses this to
        # decide whether an observant NPC pierces the veil. We pass a coarse
        # difficulty rather than the underlying numbers.
        try:
            ls = LawService(db)
            total_bounty = 0
            bounty_doc = await ls.get_bounty(char["id"], nation)
            if bounty_doc:
                total_bounty = bounty_doc.get("total_bounty", 0) or 0
            if total_bounty >= 1000:
                difficulty = "very high — they are notorious in this nation"
            elif total_bounty >= 250:
                difficulty = "high — guards may have heard descriptions"
            elif total_bounty > 0:
                difficulty = "low — the disguise is likely to hold"
            else:
                difficulty = "none — they are unknown here"
            scene_state["disguise_recognition_risk"] = difficulty
        except Exception:
            scene_state["disguise_recognition_risk"] = "none"
        # CRITICAL: hide the real criminal record + bounty from the prompt.
        # The internal law detection still happens against the real char_id.
        scene_state["criminal_record_here"] = []
        scene_state["bounty_here"] = None
        scene_state["criminal_record_text"] = ""
    else:
        scene_state["persona_active"] = False

    # FACTION ALLEGIANCE + ACTIVE RIVALRIES — NPCs in a rival faction's home
    # nation should probe a stranger for affiliation (questions, signs, tells)
    # rather than magically know who they ride with. The block is suppressed
    # entirely when a persona is active — the disguise hides faction colours
    # too. (Round 3 of Faction Membership, 2026-05-30.)
    if not scene_state.get("persona_active"):
        try:
            mem = await db.faction_memberships.find_one(
                {"character_id": char["id"], "status": "active"},
                {"_id": 0},
            )
            if mem:
                faction = await db.factions.find_one(
                    {"id": mem["faction_id"]},
                    {"_id": 0, "name": 1, "motto": 1, "nation_home": 1, "icon": 1},
                )
                scene_state["player_faction"] = {
                    "name":         mem.get("faction_name") or (faction or {}).get("name") or "",
                    "rank":         mem.get("rank") or "initiate",
                    "motto":        (faction or {}).get("motto") or "",
                    "nation_home":  (faction or {}).get("nation_home") or "",
                    "icon":         (faction or {}).get("icon") or "shield",
                }

                rivalry_rows = await db.faction_rivalries.find(
                    {"$or": [{"faction_a_id": mem["faction_id"]}, {"faction_b_id": mem["faction_id"]}],
                     "intensity": {"$gt": 0}},
                    {"_id": 0},
                ).sort("intensity", -1).to_list(length=None)
                rivalries = []
                for r in rivalry_rows:
                    other_id = r["faction_b_id"] if r["faction_a_id"] == mem["faction_id"] else r["faction_a_id"]
                    other = await db.factions.find_one(
                        {"id": other_id},
                        {"_id": 0, "name": 1, "nation_home": 1, "motto": 1},
                    )
                    if not other:
                        continue
                    rivalries.append({
                        "name":        other.get("name") or "a rival faction",
                        "nation_home": other.get("nation_home") or "",
                        "motto":       other.get("motto") or "",
                        "intensity":   r.get("intensity", 0),
                        "status":      r.get("status", "dormant"),
                        # Is the CURRENT scene in this rival's territory?
                        "in_their_territory": (other.get("nation_home") or "") == nation,
                    })
                scene_state["faction_rivalries"] = rivalries
            else:
                scene_state["player_faction"] = None
                scene_state["faction_rivalries"] = []
        except Exception as faction_err:
            logger.warning(f"scene-state faction injection failed: {faction_err}")
            scene_state["player_faction"] = None
            scene_state["faction_rivalries"] = []
    else:
        # Persona masking — the world should not see the player's banner.
        scene_state["player_faction"] = None
        scene_state["faction_rivalries"] = []

    # Gather every OTHER player character recently active in this location
    # (last 50 actions, dedup by character_id). The T1 guard needs all of
    # them so the AI cannot puppeteer ANY player's character — not just the
    # one taking the current turn. This is the multi-player T1 hardening.
    other_player_characters: list = []
    try:
        seen_other_ids = set()
        async for past_action in db.location_rp.find(
            {"nation": nation, "location": location, "character_id": {"$ne": char["id"]}},
            {"_id": 0, "character_id": 1, "character_name": 1},
        ).sort("created_at", -1).limit(50):
            cid = past_action.get("character_id")
            if not cid or cid in seen_other_ids:
                continue
            seen_other_ids.add(cid)
            other_char = await db.characters.find_one(
                {"id": cid},
                {"_id": 0, "name": 1, "race": 1, "character_class": 1, "nation": 1},
            )
            if other_char and other_char.get("name"):
                other_player_characters.append(other_char)
        # Cap to a sensible number — a busy tavern won't have more than ~8
        # active player characters, and the prompt has to stay readable.
        other_player_characters = other_player_characters[:8]
    except Exception as multi_pc_err:
        logger.warning(f"Multi-PC gather failed: {multi_pc_err}")

    # Generate AI response using new T1 system (bio-based) with world state injected
    try:
        from quest_master_ai import QuestMasterAI
        ai = QuestMasterAI()
        
        scene_data = {
            'id': f"{nation}_{location}",
            'title': f"Free Roleplay in {location}",
            'description': f"You are in {location}, {nation}. A place for free-form roleplay.",
            'nation': nation,
            'location': location,
            'setting': 'Open roleplay'
        }
        
        ai_response = await ai.respond_to_player_action(
            scene_data,
            formatted_history,
            rp_data.action_text,
            character_bio,
            scene_state=scene_state,
            other_player_characters=other_player_characters,
        )

        # Companion banter — short in-character beats from any companions present.
        # Cheap (gpt-4o-mini) and best-effort; failures never block the main response.
        try:
            companions_in_scene = [n for n in scene_state.get("npcs", []) if n.get("is_companion")]
            if companions_in_scene:
                banter = await ai.generate_companion_banter(
                    companions=companions_in_scene,
                    nation=nation,
                    location=location,
                    player_action=rp_data.action_text,
                    active_events=scene_state.get("events", []),
                )
                if banter:
                    ai_response = banter + "\n\n" + ai_response
        except Exception as banter_err:
            logger.error(f"Companion banter failed: {banter_err}")

        # If the player explicitly asks for NPCs/people to interact with, force at least
        # one NPC introduction so the scene never feels empty.
        lowered_action = rp_data.action_text.lower()
        npc_trigger_phrases = [
            "generate npc",
            "generate npcs",
            "introduce npc",
            "introduce npcs",
            "meet someone",
            "meet people",
            "anyone here",
            "anyone around",
            "any patrons",
            "any villagers",
            "any guards",
        ]
        # Only force a stranger NPC if no persistent NPCs are present
        if any(phrase in lowered_action for phrase in npc_trigger_phrases) and not scene_state.get("npcs"):
            try:
                npc_data = await ai.generate_npc("local", location)
                npc_intro = (
                    f"A nearby figure takes notice of you. "
                    f"{npc_data.get('name', 'A stranger')} is {npc_data.get('appearance', 'hard to make out')} "
                    f"and seems {npc_data.get('personality', 'difficult to read')}. "
                    f"They are driven by {npc_data.get('motivation', 'their own private reasons')} and step toward you to engage."
                )
                # Prepend the forced NPC intro so there is always at least one NPC hook
                ai_response = npc_intro + "\n\n" + ai_response
            except Exception as npc_err:
                logger.error(f"NPC generation failed in location RP: {npc_err}")

    except Exception as e:
        # Log the FULL traceback so production logs reveal whether this is
        # an LLM-key issue, network/timeout, or a code bug. The user-visible
        # fallback is intentionally generic to stay in-character, but the
        # underlying cause MUST be visible in the server logs.
        import traceback as _tb
        logger.error(
            "AI error in location RP (%s/%s) for char=%s: %s\n%s",
            nation, location, char.get('name'), e, _tb.format_exc(),
        )
        ai_response = f"*The atmosphere of {location} surrounds you as you take action...*"

    # Run world-state analysis (best effort — never block the response)
    auto_arrest_payload: Optional[Dict] = None
    try:
        analysis = await ai.analyze_interaction(
            nation=nation,
            location=location,
            character_name=char['name'],
            player_action=rp_data.action_text,
            ai_response=ai_response,
            present_npcs=scene_state.get("npcs", []),
            active_events=scene_state.get("events", []),
        )
        await npc_service.apply_analysis(
            analysis=analysis,
            nation=nation,
            location=location,
            character_id=char['id'],
            user_id=current_user.id,
            character_name=char['name'],
        )

        # Butterfly-effect propagation for every NPC sentiment change
        character_home_nation = char.get('nation', '')
        for upd in (analysis.get('npc_updates') or []):
            try:
                target_npc_id = upd.get('npc_id')
                if not target_npc_id:
                    continue
                target_npc = await npc_service.get_npc(target_npc_id)
                if not target_npc:
                    continue
                sentiment = int(upd.get('sentiment_delta', 0) or 0)
                if sentiment == 0:
                    continue
                await world_service.schedule_butterfly_from_npc_update(
                    npc=target_npc,
                    character_id=char['id'],
                    sentiment_delta=sentiment,
                    memory_text=upd.get('memory') or '',
                    character_home_nation=character_home_nation,
                )
            except Exception as butterfly_err:
                logger.error(f"Butterfly propagation failed for NPC update: {butterfly_err}")
        # Also propagate first impressions from newly created NPCs in this scene
        for new_npc_payload in (analysis.get('new_npcs') or []):
            try:
                sentiment = int(new_npc_payload.get('sentiment_delta', 0) or 0)
                if sentiment == 0:
                    continue
                # Find the freshly-created NPC by matching name + location (most recent)
                fresh = await db.npcs.find_one(
                    {"name": new_npc_payload.get('name'), "nation": nation, "location": location},
                    {"_id": 0},
                    sort=[("created_at", -1)],
                )
                if not fresh:
                    continue
                await world_service.schedule_butterfly_from_npc_update(
                    npc=fresh,
                    character_id=char['id'],
                    sentiment_delta=sentiment,
                    memory_text=new_npc_payload.get('memory') or '',
                    character_home_nation=character_home_nation,
                )
            except Exception as butterfly_err:
                logger.error(f"Butterfly propagation failed for new NPC: {butterfly_err}")

        # LAW SYSTEM: record any crimes the AI detected in this exchange.
        # Also propagate capital+ crimes as Butterfly-Effect cascades.
        if law_system_enabled():
            try:
                law_result = await law_service.apply_law_analysis(
                    analysis,
                    character_id=char['id'],
                    character_name=char['name'],
                    user_id=current_user.id,
                    nation=nation,
                    location=location,
                    present_npcs=scene_state.get("npcs", []),
                )
                # Credit any bounty payouts from successfully hunted NPCs.
                if law_result.get("total_payout"):
                    try:
                        await db.users.update_one(
                            {"id": current_user.id},
                            {"$inc": {"currency": law_result["total_payout"]}},
                        )
                    except Exception as pay_err:
                        logger.error(f"Bounty payout credit failed: {pay_err}")
                if law_result["crimes_recorded"] and law_result["max_severity"] in ("capital", "regicide"):
                    # Surface as a world event so all members see it on the Chronicle.
                    try:
                        for crime in law_result["recorded"]:
                            await world_service.record_world_event({
                                "event_type": "crime",
                                "scope": "regional",
                                "summary": (
                                    f"{char['name']} stands accused of {crime['crime_type']} "
                                    f"in {location}. A bounty of {crime['bounty']}g is posted."
                                ),
                                "details": crime.get("description", ""),
                                "nations": [nation],
                                "involved_characters": [char['id']],
                            })
                    except Exception as chronicle_err:
                        logger.error(f"Crime chronicle publish failed: {chronicle_err}")

                # AUTO-ARREST: if the AI's narration shows the player visibly
                # subdued (manacled / knocked out / hauled away), automatically
                # run a magistrate's trial and route them to the city's jail.
                # The player can still attempt escape from the jail panel.
                if analysis.get("arrest_executed") and not imprisonment:
                    try:
                        auto_arrest_payload = await _auto_arrest_and_imprison(
                            db=db,
                            law_service=law_service,
                            world_service=world_service,
                            character_id=char['id'],
                            character_name=char['name'],
                            user_id=current_user.id,
                            nation=nation,
                            location=location,
                            arrest_reason=analysis.get("arrest_reason", "") or "Subdued by lawful authority.",
                        )
                    except Exception as auto_err:
                        logger.error(f"Auto-arrest flow failed: {auto_err}")
                        auto_arrest_payload = None
            except Exception as law_apply_err:
                logger.error(f"Law analysis failed: {law_apply_err}")

        # LAW SYSTEM: if the character is currently imprisoned, count this turn
        # toward the sentence. The frontend will see the updated counter on the
        # next scene-state fetch.
        if law_system_enabled() and imprisonment:
            try:
                await law_service.increment_turn(imprisonment["id"])
            except Exception as turn_err:
                logger.error(f"Imprisonment turn increment failed: {turn_err}")
    except Exception as analysis_err:
        logger.error(f"Interaction analysis failed: {analysis_err}")
    
    # Save action (with duplicate prevention)
    location_rp = LocationRP(
        nation=nation,
        location=location,
        user_id=current_user.id,
        character_id=char['id'],
        character_name=char['name'],
        action_text=rp_data.action_text,
        ai_response=ai_response,
        dice_roll=None,
        modifier=None,
        total_roll=None
    )
    
    # Check for duplicate submission (same content within last 30 seconds)
    recent_duplicate = await db.location_rp.find_one({
        "nation": nation,
        "location": location,
        "user_id": current_user.id,
        "action_text": rp_data.action_text,
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()}
    })
    
    if recent_duplicate:
        # Return the existing post instead of creating a duplicate
        return {
            "rp_id": recent_duplicate.get("id"),
            "ai_response": recent_duplicate.get("ai_response"),
            "message": "Post already submitted"
        }
    
    rp_doc = location_rp.model_dump()
    rp_doc['created_at'] = rp_doc['created_at'].isoformat()
    await db.location_rp.insert_one(rp_doc)
    
    response_payload = {
        "rp_id": location_rp.id,
        "ai_response": ai_response,
    }
    if auto_arrest_payload:
        response_payload["auto_arrest"] = auto_arrest_payload
    return response_payload


# ==================== NPC MEMORY & SCENE STATE ROUTES ====================

@api_router.get("/locations/{nation}/{location}/scene-state")
async def get_scene_state(
    nation: str,
    location: str,
    current_user: User = Depends(get_current_user),
):
    """Returns the persistent NPCs and active environmental events in a location.

    The data is filtered for the calling user's primary character so the
    relationship score reflects how THIS character knows each NPC.
    """
    characters = await db.characters.find({"user_id": current_user.id}, {"_id": 0}).to_list(10)
    char_id = characters[0]["id"] if characters else "anonymous"
    npc_service = NPCMemoryService(db)
    state = await npc_service.build_scene_state(nation, location, char_id)
    # Inject world clock + active festivals so the player UI can show them
    try:
        from world_clock_service import get_world_clock
        from festival_service import FestivalService
        clock = get_world_clock()
        state["world_time"] = clock["time_of_day"]
        state["delarom_date"] = clock["delarom_date"]
        state["active_festivals"] = await FestivalService(db).get_active(nation=nation)
    except Exception as clock_err:
        logger.error(f"scene-state world clock fetch failed: {clock_err}")
        state["world_time"] = None
        state["active_festivals"] = []

    # Faction allegiance + rivalry hints for the UI sidebar (Round 3 mirror of
    # the same injection used by the POST /location-rp pipeline). Stripped of
    # internal IDs; UI uses this only to show pills like "You stand in rival
    # territory" — actual NPC behaviour rules live in the AI prompt.
    state["player_faction"] = None
    state["faction_rivalries"] = []
    try:
        if char_id != "anonymous":
            mem = await db.faction_memberships.find_one(
                {"character_id": char_id, "status": "active"}, {"_id": 0},
            )
            if mem:
                faction = await db.factions.find_one(
                    {"id": mem["faction_id"]},
                    {"_id": 0, "name": 1, "motto": 1, "nation_home": 1, "icon": 1, "color_hex": 1, "slug": 1},
                )
                state["player_faction"] = {
                    "name":         mem.get("faction_name") or (faction or {}).get("name") or "",
                    "rank":         mem.get("rank") or "initiate",
                    "motto":        (faction or {}).get("motto") or "",
                    "nation_home":  (faction or {}).get("nation_home") or "",
                    "icon":         (faction or {}).get("icon") or "shield",
                    "color_hex":    (faction or {}).get("color_hex") or "#a855f7",
                    "slug":         (faction or {}).get("slug") or "",
                }
                rivalry_rows = await db.faction_rivalries.find(
                    {"$or": [{"faction_a_id": mem["faction_id"]}, {"faction_b_id": mem["faction_id"]}],
                     "intensity": {"$gte": 25}},
                    {"_id": 0},
                ).sort("intensity", -1).to_list(length=None)
                rivalries = []
                for r in rivalry_rows:
                    other_id = r["faction_b_id"] if r["faction_a_id"] == mem["faction_id"] else r["faction_a_id"]
                    other = await db.factions.find_one(
                        {"id": other_id},
                        {"_id": 0, "name": 1, "nation_home": 1, "slug": 1, "color_hex": 1, "icon": 1},
                    )
                    if not other:
                        continue
                    rivalries.append({
                        "name":               other.get("name") or "",
                        "slug":               other.get("slug") or "",
                        "nation_home":        other.get("nation_home") or "",
                        "color_hex":          other.get("color_hex") or "#888",
                        "icon":               other.get("icon") or "swords",
                        "intensity":          r.get("intensity", 0),
                        "status":             r.get("status", "tense"),
                        "in_their_territory": (other.get("nation_home") or "") == nation,
                    })
                state["faction_rivalries"] = rivalries
    except Exception as faction_err:
        logger.warning(f"scene-state faction sidebar injection failed: {faction_err}")

    return state


# ============================================================
# NPC Companions — bond / dismiss / list for a character
# ============================================================

async def _resolve_character_for_user(character_id: str, user: User) -> Dict:
    """Look up a character and ensure it belongs to the calling user.

    Returns the character doc, raises HTTPException(404|403) otherwise.
    """
    char = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.get("user_id") != user.id and user.role not in ("admin", "moderator"):
        raise HTTPException(status_code=403, detail="That character is not yours")
    return char


# ==================== PHASE 2 ROUTES ====================
# Letters / Tavern Boards / Sworn Bonds. Registered here because they need
# `_resolve_character_for_user` defined above.
from routes.letters import attach_letter_routes
from routes.bulletin_board import attach_bulletin_routes
from routes.bonds import attach_bond_routes

_phase2_kwargs = dict(
    db=db,
    User=User,
    get_current_user=get_current_user,
    resolve_character_for_user=_resolve_character_for_user,
)
attach_letter_routes(api_router, **_phase2_kwargs)
attach_bulletin_routes(api_router, **_phase2_kwargs)
attach_bond_routes(api_router, **_phase2_kwargs)

# Faction Membership (foundation — Round 1 of the HEAVY-scope plan)
from routes.factions import attach_faction_routes
attach_faction_routes(
    api_router,
    db=db, User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
    resolve_character_for_user=_resolve_character_for_user,
)


# ==================== PHASE 3 ROUTES ====================
# Ballads / Family & Bloodline / Memorial Hall (2026-05-30).
from routes.ballads import attach_ballad_routes
from routes.family import attach_family_routes
from routes.memorial import attach_memorial_routes

attach_ballad_routes(
    api_router,
    db=db, User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
    resolve_character_for_user=_resolve_character_for_user,
)
attach_family_routes(api_router, **_phase2_kwargs)
attach_memorial_routes(
    api_router,
    db=db, User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
    resolve_character_for_user=_resolve_character_for_user,
)


# ==================== TIER 2a — FOUR ELDER GODS PRAYER SYSTEM ====================
# Players may pray to Seren / Yros / Uesis / Ehena. The AI judges each prayer
# as the god itself; blessings persist ~6h and colour subsequent scenes.
from routes.prayers import attach_prayer_routes
attach_prayer_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== TONGUE OF Y'ROS TRIAL ====================
# Deep in Thal'Karrak (Thalgrer's Tomb, Stonehearth Hold), a stone blade
# consecrated to Yros waits. ONLY a dwarf may draw it, and even then only
# if their attempt honours the god. One bearer realm-wide at a time.
from routes.tongue_of_yros import attach_tongue_of_yros_routes
attach_tongue_of_yros_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== PARTY QUESTS (Phase 2 — multi-player RP) ====================
# Small (2-6) shared roleplay sessions with a rotating turn order. A Master
# of Ceremonies (AI) narrates each turn's outcome and cues the next actor.
from routes.parties import attach_party_routes
attach_party_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== PRODUCERS (Phase A — real economy) ====================
# Cities and factions now actually produce goods every 6h. Producer +
# inventory + tick engine lives in `producers_service.py`.
from routes.producers import attach_producer_routes
attach_producer_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
)


# ==================== TRADE COMPANIES (Phase B — player-owned) ==============
# Chartered trading houses with routes, shareholders, and weekly dividends.
# Routes execute automatically on each 6h economy tick.
from routes.trade_companies import attach_trade_company_routes
attach_trade_company_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== ITERATION A — Time, Reputation, Duels, Bounties ========
# World calendar (215+ A.E. year advances 1 world month per real week),
# per-city/faction/god reputation web, formal duel service, and player-vs-
# player bounty claims.
from routes.iteration_a import attach_iteration_a_routes
attach_iteration_a_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== ITERATION B — Shadow & Fire =============================
# Anonymous assassination contracts, one-way cult pacts with forbidden
# rituals, and a black-market smuggling layer that upgrades ordinary
# routes into 3× profit / 30% seizure gambles when the good is banned in
# the destination nation.
from routes.iteration_b import attach_iteration_b_routes
attach_iteration_b_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== CONTESTED CITIES — Sieges ==============================
# Faction-vs-faction seizure of neutral landmarks. A siege runs for a fixed
# in-world duration; contributions from any character on either side decide
# the outcome. Seized locations gain a `controlling_faction_slug`.
from routes.siege import attach_siege_routes
attach_siege_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
)


# ==================== PHASE 4 ROUTES ====================
# Dreams / Prophecies / Personas (2026-05-30).
from routes.dreams import attach_dream_routes
from routes.prophecy import attach_prophecy_routes
from routes.persona import attach_persona_routes

attach_dream_routes(api_router, **_phase2_kwargs)
attach_prophecy_routes(api_router, **_phase2_kwargs)
attach_persona_routes(api_router, **_phase2_kwargs)


# ==================== PHASE 5 ROUTES ====================
# Wanted Posters / Whispered Rumors / Apprenticeships (2026-05-30).
from routes.wanted_posters import attach_wanted_poster_routes
from routes.rumors import attach_rumor_routes
from routes.apprenticeships import attach_apprenticeship_routes

attach_wanted_poster_routes(
    api_router,
    db=db, User=User,
    get_current_user=get_current_user,
    logger=logger,
)
attach_rumor_routes(api_router, **_phase2_kwargs)
attach_apprenticeship_routes(api_router, **_phase2_kwargs)


# ==================== COMPANION + OWNED-NPC ROUTES ====================
# Extracted to routes/companions.py (2026-05-30 refactor).
from routes.companions import attach_companion_routes
attach_companion_routes(
    api_router,
    db=db, User=User, get_current_user=get_current_user,
    resolve_character_for_user=_resolve_character_for_user,
    logger=logger,
)



# ============================================================
# LAW SYSTEM — crimes, bounties, trials, imprisonment, escapes
# Extracted to routes/law.py (2026-05-30 refactor).
# ============================================================
from routes.law import attach_law_routes
attach_law_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
    resolve_character_for_user=_resolve_character_for_user,
    logger=logger,
)


# ============================================================
# ECONOMY — goods, faction specialties, trade contracts, markets (2026-02-07).
# Hooks into world events so wars / festivals / disasters move prices.
# ============================================================
from routes.economy import attach_economy_routes
attach_economy_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
    require_admin=require_admin,
)


# ============================================================
# COURTROOM — multi-turn trial scene (2026-02-07).
# Mounted right after the law routes so the trial endpoints share the same
# `_resolve_character_for_user` helper.
# ============================================================
from routes.courtroom import attach_courtroom_routes
attach_courtroom_routes(
    api_router,
    db=db,
    User=User,
    get_current_user=get_current_user,
    resolve_character_for_user=_resolve_character_for_user,
    logger=logger,
)



# ==================== ADMIN NPC + SCENE EVENT ROUTES ====================
# Extracted to routes/admin_npcs.py (2026-05-30 refactor).
from routes.admin_npcs import attach_admin_npc_routes
attach_admin_npc_routes(
    api_router,
    db=db, User=User, require_admin=require_admin,
    NPCCreatePayload=NPCCreatePayload,
    NPCUpdatePayload=NPCUpdatePayload,
    LocationEventCreatePayload=LocationEventCreatePayload,
    LocationEventStatusPayload=LocationEventStatusPayload,
)


# ==================== CITIES + LOCATIONS CRUD ====================
# Extracted to routes/cities_locations.py (2026-05-31 refactor) to slim
# server.py down. Pure code-move — surface unchanged. The roleplay-engine
# routes (/locations/{nation}/{location}/roleplay, scene-state) stay in
# server.py because they integrate with the AI tick loop and scene state.
from routes.cities_locations import attach_cities_locations_routes
attach_cities_locations_routes(
    api_router,
    db=db, User=User,
    City=City, CityBase=CityBase, CityUpdate=CityUpdate, CityListItem=CityListItem,
    LocationArea=LocationArea, LocationAreaBase=LocationAreaBase,
    LocationAreaUpdate=LocationAreaUpdate, LocationAreaListItem=LocationAreaListItem,
    ImageService=ImageService,
    require_moderator=require_moderator,
)



# ==================== WORLD STATE / BUTTERFLY-EFFECT / CHRONICLE ROUTES ====================
# Extracted to routes/world.py (2026-05-30 refactor).
from routes.world import attach_world_routes
attach_world_routes(
    api_router,
    db=db, User=User, require_admin=require_admin,
    NationRelationPayload=NationRelationPayload,
    NationRelationDeltaPayload=NationRelationDeltaPayload,
    WorldEventCreatePayload=WorldEventCreatePayload,
)


# ==================== LOCATION MANAGEMENT ROUTES ====================

@api_router.api_route("/image/{image_id}", methods=["GET", "HEAD"])
async def get_image_blob(image_id: str, request: Request):
    """Serve a stored image as raw bytes with proper Content-Type and Cache-Control.

    Images live in the `image_blobs` collection. This endpoint is browser-cached
    for a day. Supports HEAD so CDNs/browsers can do cheap conditional fetches.
    Image IDs are immutable UUIDs, so we mark responses as immutable.
    """
    img_service = ImageService(db)
    doc = await img_service.get(image_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    data = doc.get("data")
    if not data:
        raise HTTPException(status_code=404, detail="Image data missing")
    etag = f'"{image_id}"'
    headers = {
        "Cache-Control": "public, max-age=86400, immutable",
        "ETag": etag,
    }
    # Honour If-None-Match for 304 cache hits
    if request.headers.get("if-none-match") == etag:
        return FastAPIResponse(status_code=304, headers=headers)
    # HEAD: return headers only (no body)
    body = b"" if request.method == "HEAD" else bytes(data)
    return FastAPIResponse(
        content=body,
        media_type=doc.get("mime_type", "image/png"),
        headers=headers,
    )


def _make_image_url(request: Request, image_id: Optional[str]) -> Optional[str]:
    """Build a relative `/api/image/{id}` URL the frontend can drop into <img src>."""
    if not image_id:
        return None
    # Relative URL — the frontend already prefixes REACT_APP_BACKEND_URL via axios.
    # We keep it relative so the same value works in dev and prod.
    return f"/api/image/{image_id}"


# ==================== NATION ENDPOINTS ====================

@api_router.get("/nations/images", response_model=List[NationInfo])
async def get_nation_images(request: Request):
    """Get all nations with their image URLs (short refs, not base64).

    Legacy `image_url` base64 data is lazily migrated to the `image_blobs`
    collection on first access. Subsequent calls return a small `/api/image/{id}`
    URL instead.
    """
    nations = await db.nations.find({}, {"_id": 0}).to_list(100)
    img_service = ImageService(db)
    out: List[NationInfo] = []
    for n in nations:
        image_id = n.get("image_id")
        if not image_id and n.get("image_url"):
            # One-shot lazy migration
            image_id = await img_service.ensure_migrated("nations", {"slug": n["slug"]})
        out.append(NationInfo(
            slug=n["slug"],
            name=n["name"],
            image_url=_make_image_url(request, image_id),
        ))
    return out


@api_router.get("/nations/{nation_slug}/image")
async def get_nation_image(nation_slug: str, request: Request):
    """Get a specific nation's image URL."""
    nation = await db.nations.find_one({"slug": nation_slug}, {"_id": 0, "image_id": 1, "image_url": 1, "name": 1})
    if not nation:
        raise HTTPException(status_code=404, detail="Nation not found")
    img_service = ImageService(db)
    image_id = nation.get("image_id")
    if not image_id and nation.get("image_url"):
        image_id = await img_service.ensure_migrated("nations", {"slug": nation_slug})
    return NationInfo(slug=nation_slug, name=nation.get("name", ""), image_url=_make_image_url(request, image_id))


@api_router.get("/locations/{nation}/{location}/roleplay")
async def get_location_rp(nation: str, location: str, limit: int = 50):
    """Get roleplay history for a location"""
    actions = await db.location_rp.find(
        {"nation": nation, "location": location},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for action in actions:
        if isinstance(action.get('created_at'), str):
            action['created_at'] = datetime.fromisoformat(action['created_at'])
    
    return list(reversed(actions))


@api_router.delete("/locations/{nation}/{location}/roleplay/{rp_id}")
async def delete_location_rp(
    nation: str, 
    location: str, 
    rp_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Delete a roleplay post.
    
    Permissions:
    - Admins and Moderators can delete any post
    - Users can delete their own posts
    """
    # Find the post
    post = await db.location_rp.find_one({
        "id": rp_id,
        "nation": nation,
        "location": location
    })
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check permissions
    is_admin_or_mod = current_user.role in ["admin", "moderator"]
    is_owner = post.get("user_id") == current_user.id
    
    if not is_admin_or_mod and not is_owner:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to delete this post"
        )
    
    # Delete the post
    result = await db.location_rp.delete_one({"id": rp_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete post")
    
    return {
        "message": "Post deleted successfully",
        "deleted_id": rp_id,
        "deleted_by": "admin/moderator" if is_admin_or_mod and not is_owner else "owner"
    }

# ==================== FORUM ROUTES ====================
# Extracted to routes/forums.py (2026-05-30 refactor).
from routes.forums import attach_forum_routes
attach_forum_routes(
    api_router,
    db=db, User=User, get_current_user=get_current_user,
    ForumPost=ForumPost, ForumPostCreate=ForumPostCreate,
    ForumReply=ForumReply, ForumReplyCreate=ForumReplyCreate,
)


# ==================== HEALTH CHECK ====================

@api_router.get("/")
async def root():
    return {"message": "Welcome to Continents of Delarom API", "status": "operational"}


# ==================== MUSIC UPLOAD ====================
# Extracted to routes/music.py (2026-05-30 refactor).
from routes.music import attach_music_routes
attach_music_routes(api_router, User=User, get_current_user=get_current_user, MUSIC_DIR=MUSIC_DIR)



# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging is initialised at the top of the file (right after `app = FastAPI()`).

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()# forced reload Fri Aug 21 15:05:28 UTC 2026
