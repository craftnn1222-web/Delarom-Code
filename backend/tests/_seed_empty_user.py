"""Seed a brand-new empty-state user for continue-dashboard testing.
Runs directly against local Mongo (bypasses admin-approval flow)."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

EMAIL = "TEST_continue_empty@delarom.com"
PWD = "Testpass123!"


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    existing = await db.users.find_one({"email": EMAIL})
    if existing:
        # Ensure it's active and has no RP/party links.
        await db.users.update_one(
            {"email": EMAIL},
            {"$set": {"status": "active", "role": "member"}},
        )
        # Clean any RP / party links in case a prior test polluted it
        await db.location_rp.delete_many({"user_id": existing["id"]})
        await db.parties.update_many(
            {"members.user_id": existing["id"]},
            {"$pull": {"members": {"user_id": existing["id"]}}},
        )
        print(f"UPDATED existing user id={existing['id']}")
        return

    uid = str(uuid.uuid4())
    ph = bcrypt.hashpw(PWD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    doc = {
        "id": uid,
        "email": EMAIL,
        "username": "TEST_continue_empty",
        "password_hash": ph,
        "role": "member",
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "active_character_id": None,
        "application_text": "seeded for iteration_33 empty-state continue test",
    }
    await db.users.insert_one(doc)
    print(f"CREATED user id={uid}")

    # Sanity: ensure no RP + no party
    n_rp = await db.location_rp.count_documents({"user_id": uid})
    n_party = await db.parties.count_documents({"members.user_id": uid})
    print(f"RP docs={n_rp}, party docs={n_party}")


asyncio.run(main())
