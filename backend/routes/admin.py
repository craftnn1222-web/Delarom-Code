"""Admin / Moderation routes.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_admin_routes(api_router, ...)`.
"""
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request


def attach_admin_routes(
    api_router: APIRouter,
    *,
    db, User, UserResponse,
    require_admin, require_moderator,
    hash_password,
    logger,
):
    # ==================== ADMIN/MODERATION ROUTES ====================

    @api_router.get("/admin/applications")
    async def get_pending_applications(admin: User = Depends(require_admin)):
        """Get all pending user applications"""
        applications = await db.users.find(
            {"status": "pending"},
            {"_id": 0, "password_hash": 0}
        ).sort("created_at", -1).to_list(100)
    
        return {"applications": applications}

    @api_router.post("/admin/applications/{user_id}/approve")
    async def approve_application(user_id: str, admin: User = Depends(require_admin)):
        """Approve a pending user application"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        if user_doc['status'] != "pending":
            raise HTTPException(status_code=400, detail="User is not pending approval")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "status": "active",
                "approved_by": admin.id,
                "approved_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
        return {"message": f"User {user_doc['username']} approved successfully"}

    @api_router.post("/admin/applications/{user_id}/reject")
    async def reject_application(user_id: str, reason: str, admin: User = Depends(require_admin)):
        """Reject a pending user application (deletes the user)"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        if user_doc['status'] != "pending":
            raise HTTPException(status_code=400, detail="User is not pending approval")
    
        # Delete the user completely
        await db.users.delete_one({"id": user_id})
    
        return {"message": f"Application from {user_doc['username']} rejected and deleted"}

    @api_router.get("/admin/users")
    async def get_all_users(moderator: User = Depends(require_moderator)):
        """Get all users (for moderation)"""
        users = await db.users.find(
            {"status": {"$ne": "pending"}},
            {"_id": 0, "password_hash": 0}
        ).sort("created_at", -1).to_list(1000)
    
        return {"users": users}

    @api_router.post("/admin/users/{user_id}/ban")
    async def ban_user(user_id: str, reason: str, moderator: User = Depends(require_moderator)):
        """Ban a user permanently"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        # Normalize legacy users missing role/status
        update_fields: dict = {}
        if not user_doc.get("role"):
            user_doc["role"] = "member"
            update_fields["role"] = "member"
        if not user_doc.get("status"):
            user_doc["status"] = "active"
            update_fields["status"] = "active"
        if update_fields:
            await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
        if user_doc['role'] in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="Cannot ban admin or moderator")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "status": "banned",
                "ban_reason": reason
            }}
        )
    
        return {"message": f"User {user_doc['username']} has been banned"}

    @api_router.post("/admin/users/{user_id}/unban")
    async def unban_user(user_id: str, moderator: User = Depends(require_moderator)):
        """Unban a user"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "status": "active",
                "ban_reason": None
            }}
        )
    
        return {"message": f"User {user_doc['username']} has been unbanned"}


    # ==================== DATABASE SEEDING ====================

    @api_router.post("/admin/seed-database")
    async def seed_database(admin: User = Depends(require_admin)):
        """
        Seed the database with all nations, cities, and locations.
        This is an admin-only endpoint for populating empty production databases.
        """
        from seed_database import run_full_seed, set_database
    
        # Pass the database connection to the seeder
        set_database(db)
    
        # Run the seeding process
        results = await run_full_seed()
    
        return {
            "message": "Database seeding complete!",
            "created": {
                "nations": results["nations"],
                "cities": results["cities"],
                "locations": results["locations"]
            },
            "errors": results["errors"] if results["errors"] else None
        }


    @api_router.post("/admin/start-full-seed")
    async def start_full_seed(with_images: bool = True, admin: User = Depends(require_admin)):
        """Kick off the full seeding process as a background task. Returns a task_id
        immediately. Poll `/admin/seed-status` for progress."""
        from seed_task_service import seed_task_manager
        if seed_task_manager.is_running():
            return {"already_running": True, **seed_task_manager.status()}
        state = await seed_task_manager.start(db, with_images=with_images)
        return state


    @api_router.get("/admin/seed-status")
    async def get_seed_status(admin: User = Depends(require_admin)):
        """Poll-friendly status for the most recent background seeding task."""
        from seed_task_service import seed_task_manager
        return seed_task_manager.status()


    @api_router.get("/admin/database-status")
    async def get_database_status(admin: User = Depends(require_admin)):
        """Get the current status of database collections."""
        nations_count = await db.nations.count_documents({})
        cities_count = await db.cities.count_documents({})
        locations_count = await db.locations.count_documents({})
        users_count = await db.users.count_documents({})
    
        return {
            "nations": nations_count,
            "cities": cities_count,
            "locations": locations_count,
            "users": users_count,
            "is_empty": nations_count == 0 and cities_count == 0
        }


    @api_router.get("/admin/cleanup-duplicate-locations")
    async def cleanup_duplicate_locations(admin: User = Depends(require_admin)):
        """Clean up duplicate locations - keeps the one with an image, or the first one if none have images."""
    
        # Get all locations with pagination to avoid memory issues
        all_locations = await db.locations.find({}, {"_id": 1, "nation": 1, "city": 1, "slug": 1, "image_url": 1}).to_list(10000)
    
        # Group by (nation, city, slug)
        from collections import defaultdict
        groups = defaultdict(list)
        for loc in all_locations:
            key = (loc.get("nation"), loc.get("city"), loc.get("slug"))
            groups[key].append(loc)
    
        deleted_count = 0
        kept_count = 0
    
        # Collect all IDs to delete for batch operation
        ids_to_delete = []
    
        for key, locs in groups.items():
            if len(locs) > 1:
                # Sort: prefer ones with images first
                locs_sorted = sorted(locs, key=lambda x: (bool(x.get("image_url")), str(x.get("_id"))), reverse=True)
                # Keep the first (best) one, collect IDs to delete (all except the first)
                for loc in locs_sorted[1:]:
                    ids_to_delete.append(loc["_id"])
                    deleted_count += 1
                kept_count += 1
            else:
                kept_count += 1
    
        # Batch delete all duplicates in one query
        if ids_to_delete:
            await db.locations.delete_many({"_id": {"$in": ids_to_delete}})
    
        return {
            "message": f"Cleanup complete. Deleted {deleted_count} duplicate locations.",
            "unique_locations": kept_count,
            "deleted": deleted_count
        }


    @api_router.get("/admin/locations-status")
    async def get_locations_status(admin: User = Depends(require_admin)):
        """Get detailed status of locations per nation - how many have images."""
    
        nations = ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]
        status = {}
    
        for nation in nations:
            total = await db.locations.count_documents({"nation": nation})
            # Count locations that have a non-empty, non-null image_url
            with_images = await db.locations.count_documents({
                "nation": nation, 
                "image_url": {"$exists": True, "$nin": [None, "", "null"]}
            })
            status[nation] = {
                "total": total,
                "with_images": with_images,
                "missing_images": total - with_images
            }
    
        return status


    @api_router.post("/admin/repair-world-locations")
    async def repair_world_locations(admin: User = Depends(require_admin)):
        """Repair the 'some cities show no locations' regression.

        Idempotent & additive:
        - normalises the outlier `dhor-khuldor` nation slug to `dhor-kuldor`.
        - seeds a small starter set of RP locations for any city that has none.
        Safe to run repeatedly; never edits hand-authored locations.
        """
        from repair_world_data import repair_world_data
        return await repair_world_data(db)


    class AdminPasswordResetRequest(BaseModel):
        new_password: str = Field(min_length=6, description="New password (min 6 characters)")


    @api_router.post("/admin/users/{user_id}/reset-password")
    async def admin_reset_user_password(
        user_id: str, 
        request: AdminPasswordResetRequest,
        admin: User = Depends(require_admin)
    ):
        """Reset a user's password (Admin only).
    
        This allows admins to set a new password for users who have forgotten their login.
        """
        # Find the user
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        # Hash the new password
        new_password_hash = hash_password(request.new_password)
    
        # Update the password
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": {"password_hash": new_password_hash}}
        )
    
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update password")
    
        return {
            "message": f"Password reset successfully for user {user_doc.get('email')}",
            "user_id": user_id,
            "email": user_doc.get('email')
        }


    @api_router.get("/admin/users")
    async def list_all_users(admin: User = Depends(require_admin)):
        """Get all users (Admin only) - for password reset functionality."""
        users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
        return users


    @api_router.post("/admin/users/{user_id}/suspend")
    async def suspend_user(user_id: str, days: int, reason: str, moderator: User = Depends(require_moderator)):
        """Suspend a user for a specified number of days"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        # Normalize legacy users missing role/status
        update_fields: dict = {}
        if not user_doc.get("role"):
            user_doc["role"] = "member"
            update_fields["role"] = "member"
        if not user_doc.get("status"):
            user_doc["status"] = "active"
            update_fields["status"] = "active"
        if update_fields:
            await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
        if user_doc['role'] in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="Cannot suspend admin or moderator")
    
        suspended_until = datetime.now(timezone.utc) + timedelta(days=days)
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "status": "suspended",
                "suspended_until": suspended_until.isoformat(),
                "suspension_reason": reason
            }}
        )
    
        return {"message": f"User {user_doc['username']} suspended for {days} days"}

    @api_router.post("/admin/users/{user_id}/unsuspend")
    async def unsuspend_user(user_id: str, moderator: User = Depends(require_moderator)):
        """Remove suspension from a user"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "status": "active",
                "suspended_until": None,
                "suspension_reason": None
            }}
        )
    
        return {"message": f"User {user_doc['username']} suspension removed"}

    @api_router.post("/admin/users/{user_id}/promote-moderator")
    async def promote_to_moderator(user_id: str, admin: User = Depends(require_admin)):
        """Promote a user to moderator (admin only)"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        # Normalize legacy users missing role/status
        update_fields: dict = {}
        if not user_doc.get("role"):
            user_doc["role"] = "member"
            update_fields["role"] = "member"
        if not user_doc.get("status"):
            user_doc["status"] = "active"
            update_fields["status"] = "active"
        if update_fields:
            await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
        if user_doc['role'] == "moderator":
            raise HTTPException(status_code=400, detail="User is already a moderator")
    
        if user_doc['role'] == "admin":
            raise HTTPException(status_code=400, detail="User is already an admin")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"role": "moderator"}}
        )
    
        return {"message": f"User {user_doc['username']} promoted to moderator"}

    @api_router.post("/admin/users/{user_id}/demote-moderator")
    async def demote_from_moderator(user_id: str, admin: User = Depends(require_admin)):
        """Demote a moderator back to member (admin only)"""
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        if user_doc['role'] != "moderator":
            raise HTTPException(status_code=400, detail="User is not a moderator")
    
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"role": "member"}}
        )
    
        return {"message": f"User {user_doc['username']} demoted to member"}


    # ==================== IP BAN MANAGEMENT ====================

    class IPBanRequest(BaseModel):
        ip_address: str
        reason: str = "Violation of platform rules"
        associated_user_id: Optional[str] = None

    @api_router.get("/admin/ip-bans")
    async def get_ip_bans(admin: User = Depends(require_admin)):
        """Get all IP bans (Admin only)."""
        bans = await db.ip_bans.find({}, {"_id": 0}).to_list(1000)
        return bans

    @api_router.post("/admin/ip-bans")
    async def add_ip_ban(request: IPBanRequest, admin: User = Depends(require_admin)):
        """Add an IP to the ban list (Admin only)."""
        # Check if IP is already banned
        existing = await db.ip_bans.find_one({"ip_address": request.ip_address})
        if existing:
            raise HTTPException(status_code=400, detail="IP address is already banned")
    
        ban_doc = {
            "id": str(uuid.uuid4()),
            "ip_address": request.ip_address,
            "reason": request.reason,
            "associated_user_id": request.associated_user_id,
            "banned_by": admin.id,
            "banned_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }
    
        await db.ip_bans.insert_one(ban_doc)
    
        return {"message": f"IP {request.ip_address} has been banned", "ban": {k: v for k, v in ban_doc.items() if k != "_id"}}

    @api_router.delete("/admin/ip-bans/{ban_id}")
    async def remove_ip_ban(ban_id: str, admin: User = Depends(require_admin)):
        """Remove an IP ban (Admin only)."""
        result = await db.ip_bans.delete_one({"id": ban_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="IP ban not found")
        return {"message": "IP ban removed successfully"}


    # ==================== ACCOUNT REMOVAL ====================

    @api_router.delete("/admin/users/{user_id}/remove")
    async def remove_user_account(
        user_id: str, 
        ban_ip: bool = False,
        admin: User = Depends(require_admin)
    ):
        """
        Permanently remove a user account and all associated data (Admin only).
    
        This will delete:
        - User account
        - All characters
        - All forum posts
        - All roleplay posts
        - All quest acceptances
        - All shop items
        - All transactions
    
        Optionally ban their IP address to prevent re-registration.
        """
        # Find the user
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        # Cannot remove admin accounts
        if user_doc.get('role') == 'admin':
            raise HTTPException(status_code=403, detail="Cannot remove admin accounts")
    
        username = user_doc.get('username', 'Unknown')
        email = user_doc.get('email', 'Unknown')
        last_ip = user_doc.get('last_ip_address')
    
        # Ban IP if requested and we have one on record
        if ban_ip and last_ip:
            existing_ban = await db.ip_bans.find_one({"ip_address": last_ip})
            if not existing_ban:
                ban_doc = {
                    "id": str(uuid.uuid4()),
                    "ip_address": last_ip,
                    "reason": f"Account removal - User: {username} ({email})",
                    "associated_user_id": user_id,
                    "banned_by": admin.id,
                    "banned_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                }
                await db.ip_bans.insert_one(ban_doc)
    
        # Delete all associated data
        deleted_counts = {
            "characters": 0,
            "forum_posts": 0,
            "roleplay_posts": 0,
            "quest_acceptances": 0,
            "shop_items": 0,
            "transactions": 0
        }
    
        # Delete characters
        result = await db.characters.delete_many({"user_id": user_id})
        deleted_counts["characters"] = result.deleted_count
    
        # Delete forum posts
        result = await db.forum_posts.delete_many({"author_id": user_id})
        deleted_counts["forum_posts"] = result.deleted_count
    
        # Delete roleplay posts
        result = await db.location_rp.delete_many({"user_id": user_id})
        deleted_counts["roleplay_posts"] = result.deleted_count
    
        # Delete quest acceptances
        result = await db.quest_acceptances.delete_many({"user_id": user_id})
        deleted_counts["quest_acceptances"] = result.deleted_count
    
        # Delete shop items
        result = await db.shop_items.delete_many({"owner_id": user_id})
        deleted_counts["shop_items"] = result.deleted_count
    
        # Delete transactions
        result = await db.transactions.delete_many({"user_id": user_id})
        deleted_counts["transactions"] = result.deleted_count
    
        # Finally, delete the user account
        await db.users.delete_one({"id": user_id})
    
        return {
            "message": f"User {username} ({email}) has been permanently removed",
            "deleted_data": deleted_counts,
            "ip_banned": ban_ip and last_ip is not None
        }


    @api_router.get("/admin/users/{user_id}/details")
    async def get_user_details(user_id: str, admin: User = Depends(require_admin)):
        """Get detailed user information including IP address (Admin only)."""
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
    
        # Get counts of associated data
        char_count = await db.characters.count_documents({"user_id": user_id})
        post_count = await db.forum_posts.count_documents({"author_id": user_id})
        rp_count = await db.location_rp.count_documents({"user_id": user_id})
    
        user_doc["data_counts"] = {
            "characters": char_count,
            "forum_posts": post_count,
            "roleplay_posts": rp_count
        }
    
        return user_doc

    # ==================== NPC SEEDING ====================

    @api_router.post("/admin/seed-royals-and-nobles")
    async def admin_seed_royals_and_nobles(admin: User = Depends(require_admin)):
        """Idempotent — seed the 5 hand-authored royals + 15 capital nobles.

        See `seed_royals_and_nobles.py` for the canon. Skips any (name,
        nation) pair already present so it's safe to re-run.
        """
        from seed_royals_and_nobles import seed_royals_and_nobles
        return await seed_royals_and_nobles(db)

    @api_router.post("/admin/populate-cities-ai")
    async def admin_populate_cities_ai(
        max_cities: int = 5,
        admin: User = Depends(require_admin),
    ):
        """AI-populate the next `max_cities` (default 5) most-empty cities.

        Each city receives 4 commoners + 2 notables generated by gpt-4o-mini
        and tagged `created_by: "seed:ai_population"` so admins can filter
        and refine them. Skips cities already at ≥ 4 residents. Capped per
        call so admins can pace cost; call repeatedly to cover the whole
        realm. See `seed_ai_population.py`.
        """
        from seed_ai_population import populate_cities
        # Clamp to a sane range — bulk AI calls are not free.
        max_cities = max(1, min(int(max_cities), 25))
        return await populate_cities(db, max_cities=max_cities)

    @api_router.post("/admin/cleanup-geo-data")
    async def admin_cleanup_geo_data(admin: User = Depends(require_admin)):
        """Dedupe duplicate cities & locations, then add the unique indexes
        that should have always existed.

        Why this exists: the `populate_*.py` scripts are re-runnable seeds
        that simply `insert_one` — without a unique constraint, every re-run
        adds another copy of every location. Production accumulated up to
        ten copies of some locations. This endpoint collapses each
        (nation, city, slug) group to its oldest row (`created_at`) and
        adds the unique indexes so it cannot happen again.
        """
        from db_maintenance import run_full_cleanup
        return await run_full_cleanup(db)


    # ================== IMAGE BATCHER (gpt-image-1) ==================

    @api_router.get("/admin/image-batch/survey")
    async def admin_image_batch_survey(admin: User = Depends(require_admin)):
        """Counts cities + locations missing images. Never generates."""
        from city_location_image_batcher import CityLocationImageBatcher
        return await CityLocationImageBatcher(db, batch_size=25).survey()

    @api_router.get("/admin/image-batch/status")
    async def admin_image_batch_status(admin: User = Depends(require_admin)):
        """Current batch job state (process-local; resets on server restart)."""
        from city_location_image_batcher import CityLocationImageBatcher
        return CityLocationImageBatcher.get_status()

    @api_router.post("/admin/image-batch/generate")
    async def admin_image_batch_generate(
        auto_continue: bool = False,
        admin: User = Depends(require_admin),
    ):
        """Kick off a background batch of 25 missing-image generations via
        gpt-image-1. Returns immediately. Cities prioritised over locations.
        Query param `auto_continue=true` makes the server loop batch-after-batch
        until every missing image is generated (or MAX_ITERATIONS is hit)."""
        from city_location_image_batcher import CityLocationImageBatcher
        return CityLocationImageBatcher(db, batch_size=25).kick_off_background_batch(
            auto_continue=auto_continue,
        )

    @api_router.post("/admin/image-batch/stop")
    async def admin_image_batch_stop(admin: User = Depends(require_admin)):
        """Request the running batch loop to stop after the current image."""
        from city_location_image_batcher import CityLocationImageBatcher
        return CityLocationImageBatcher.request_stop()

    @api_router.post("/admin/seed-titan-sacred-sites")
    async def admin_seed_titan_sacred_sites(admin: User = Depends(require_admin)):
        """Tier 2d — Annotate canonical locations with `titan_sacred_site`
        flags tying them to one of the Seven Titans Ausar slew. Purely
        additive; never creates new locations. Idempotent."""
        from seed_titan_sacred_sites import seed_titan_sacred_sites
        return await seed_titan_sacred_sites(db)

    @api_router.post("/admin/seed-dhor-kuldor-canon")
    async def admin_seed_dhor_kuldor_canon(admin: User = Depends(require_admin)):
        """Tier 1 (min viable) — Insert or update the canonical Dhor-Kuldor
        hold-capital cities that the lore + Titan Sacred Sites depend on.
        Idempotent."""
        from seed_dhor_kuldor_canon import seed_dhor_kuldor_canon
        return await seed_dhor_kuldor_canon(db)

    @api_router.post("/admin/seed-all-realms-canon")
    async def admin_seed_all_realms_canon(admin: User = Depends(require_admin)):
        """Tier 1 (FULL) — Seed every canonical city across all five realms
        (Ammeonon, Selindori, Dhor-Kuldor, Aigraels, Veiled Realms).
        Idempotent — safe to re-run; existing cities are updated in place."""
        from seed_all_realms_canon import seed_all_realms_canon
        return await seed_all_realms_canon(db)

