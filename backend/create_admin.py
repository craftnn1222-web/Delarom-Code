"""Script to create or upgrade the first admin user for Continents of Delarom."""
import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_admin_env() -> tuple[str, str, str]:
    """Read the admin identity from env. Raises if the password is missing."""
    username = os.environ.get("ADMIN_USERNAME", "Ausar Veltraus")
    email = os.environ.get("ADMIN_EMAIL", "craftnn1222@gmail.com")
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is required. "
            "Set it before running create_admin.py (e.g., export ADMIN_PASSWORD='your-strong-password')."
        )
    return username, email, password


async def _promote_existing(db, email: str, username: str) -> None:
    """Promote an existing account to admin + active."""
    await db.users.update_one(
        {"email": email},
        {"$set": {
            "role": "admin",
            "status": "active",
            "approved_by": "system",
            "approved_at": _utcnow_iso(),
        }},
    )
    print(f"✅ {username} updated to ADMIN with ACTIVE status")


async def _insert_new_admin(db, username: str, email: str, password: str) -> str:
    """Create a fresh admin user + welcome transaction. Returns the user_id."""
    user_id = str(uuid4())
    user_doc = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": pwd_context.hash(password),
        "currency": 1000,
        "role": "admin",
        "status": "active",
        "application_text": "Site Owner & Administrator",
        "approved_by": "system",
        "approved_at": _utcnow_iso(),
        "suspended_until": None,
        "suspension_reason": None,
        "ban_reason": None,
        "created_at": _utcnow_iso(),
    }
    await db.users.insert_one(user_doc)
    await db.transactions.insert_one({
        "id": str(uuid4()),
        "user_id": user_id,
        "amount": 1000,
        "transaction_type": "initial_balance",
        "description": "Welcome to Delarom! Starting balance.",
        "created_at": _utcnow_iso(),
    })
    print("✅ Admin account created successfully!")
    return user_id


def _print_summary(username: str, email: str, password: str) -> None:
    print("\n" + "=" * 60)
    print("🛡️  ADMIN CREDENTIALS")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print("Role: admin")
    print("Status: active")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Change your password after first login!")
    print("You can now login and access the Admin Dashboard at /admin\n")


async def create_admin() -> None:
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    username, email, password = _read_admin_env()
    print(f"Creating admin account for: {username} ({email})")

    existing = await db.users.find_one({"email": email})
    if existing:
        print("User already exists! Updating to admin...")
        await _promote_existing(db, email, username)
    else:
        print("Creating new admin user...")
        await _insert_new_admin(db, username, email, password)

    _print_summary(username, email, password)
    client.close()


if __name__ == "__main__":
    asyncio.run(create_admin())
