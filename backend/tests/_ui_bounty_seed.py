"""Reseed bounty rows for frontend smoke test. Removes them after."""
import asyncio, os, sys
sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient
from law_service import LawService

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

TAG = "TEST_BB_UI_SEED"

async def main(mode):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    law = LawService(db)
    if mode == "seed":
        await law.record_crime(
            perpetrator_type="npc",
            perpetrator_id="npc-ui-amme",
            perpetrator_name="UI Test Fugitive Amme",
            nation="ammeonon", location="wymroost",
            crime_type="banditry", severity="major",
            victim_name="merchant", victim_importance="notable",
            description=TAG,
        )
        await law.record_crime(
            perpetrator_type="npc",
            perpetrator_id="npc-ui-seli",
            perpetrator_name="UI Test Outlaw Seli",
            nation="selindori", location="silver-bay",
            crime_type="murder", severity="capital",
            victim_name="captain", victim_importance="notable",
            description=TAG,
        )
        print("Seeded UI bounties.")
    elif mode == "clean":
        await db.crimes.delete_many({"description": TAG})
        await db.bounties.delete_many({"perpetrator_id": {"$in": ["npc-ui-amme", "npc-ui-seli"]}})
        print("Cleaned UI bounties.")
    client.close()

asyncio.run(main(sys.argv[1]))
