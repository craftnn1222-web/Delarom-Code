"""
Faction Membership endpoints.

The 42 HTTP endpoints that drive faction membership, threads, charters,
quests, treasury, rivalries and admin ticks live here. The data shapes,
constants, pure helpers and DB-bound helpers were extracted to
`routes/_factions_lib.py` (2026-05-31 refactor) so this file can focus on
HTTP surface only. Importing `attach_faction_routes` from this module
still works; importing `apply_crime_to_faction` from `routes.factions`
also still works thanks to the re-export below.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes._factions_lib import (
    # Constants
    RANKS, RANK_LABELS, NATIONS,
    REPUTATION_MIN, REPUTATION_MAX, REPUTATION_CRIME_DELTA,
    FACTION_CHARTER_COST_GOLD, ALLOWED_FACTION_ICONS,
    RIVALRY_STATUSES, RIVALRY_MAX_INTENSITY, RIVALRY_CRIME_DELTA,
    # Pure helpers
    _rank_index, _can_manage, _now_iso, _slugify,
    _rivalry_status, _rivalry_pair,
    # Pydantic models
    JoinFactionBody, RankChangeBody, CreateFactionBody,
    CreateThreadBody, CreateThreadReplyBody,
    ReputationGrantBody, SeedLeadersBody,
    FileCharterBody, CharterReviewBody,
    CreateQuestBody, AiGenerateQuestBody, CompleteQuestBody,
    DonateBody, DeclareRivalryBody, EscalateRivalryBody,
    # Async DB helpers
    _get_faction, _get_membership, _refresh_member_count,
    _get_or_init_reputation, _apply_reputation_delta,
    _auto_escalate_rivalries_for_crime,
    # Public re-export — law_service.py imports this from routes.factions.
    apply_crime_to_faction,
)


def attach_faction_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
    resolve_character_for_user,
):
    """Mount faction routes on the api router.

    Required collaborators (passed from server.py):
      - db: AsyncIOMotorDatabase
      - User: the Pydantic model used by `get_current_user`
      - get_current_user / require_admin: existing auth deps
      - resolve_character_for_user: helper that validates a character_id
        belongs to the current user and returns the character document
    """

    # ------------ Public reads ------------

    @api_router.get("/factions/ranks")
    async def list_ranks():
        return {"ranks": RANKS, "labels": RANK_LABELS}

    # ------------ Visibility helpers (badges) ------------

    async def _lightweight_faction(mem: dict) -> Optional[dict]:
        """Builds the small payload used by faction badges in the UI."""
        f = await db.factions.find_one(
            {"id": mem["faction_id"]},
            {"_id": 0, "name": 1, "slug": 1, "icon": 1, "color_hex": 1, "motto": 1, "nation_home": 1},
        )
        if not f:
            return None
        return {
            "faction_name": f.get("name") or "",
            "faction_slug": f.get("slug") or "",
            "icon":         f.get("icon") or "shield",
            "color_hex":    f.get("color_hex") or "#888",
            "motto":        f.get("motto") or "",
            "nation_home":  f.get("nation_home") or "",
            "rank":         mem.get("rank", "initiate"),
        }

    @api_router.get("/characters/{character_id}/faction")
    async def get_character_faction(character_id: str):
        """Lightweight: returns the single active faction membership for a
        character, decorated with display fields. Returns null when the
        character has no active faction. Used wherever a single badge is
        rendered (profile pages, RP scene participant rows)."""
        mem = await db.faction_memberships.find_one(
            {"character_id": character_id, "status": "active"}, {"_id": 0},
        )
        if not mem:
            return None
        return await _lightweight_faction(mem)

    class CharacterIdsBatchBody(BaseModel):
        character_ids: list[str]

    @api_router.post("/characters/factions/batch")
    async def get_factions_for_characters_batch(body: CharacterIdsBatchBody):
        """Batch version of /characters/{id}/faction. Returns a dict
        keyed by character_id; characters with no active membership map to
        null. Hard-capped at 500 ids per call to keep MongoDB happy."""
        ids = [cid for cid in (body.character_ids or []) if cid][:500]
        if not ids:
            return {}
        memberships = await db.faction_memberships.find(
            {"character_id": {"$in": ids}, "status": "active"},
            {"_id": 0, "character_id": 1, "faction_id": 1, "rank": 1},
        ).to_list(length=None)
        faction_ids = list({m["faction_id"] for m in memberships})
        faction_rows = (
            await db.factions.find(
                {"id": {"$in": faction_ids}},
                {"_id": 0, "id": 1, "name": 1, "slug": 1, "icon": 1, "color_hex": 1, "motto": 1, "nation_home": 1},
            ).to_list(length=None)
            if faction_ids else []
        )
        by_fid = {f["id"]: f for f in faction_rows}
        result: dict = {cid: None for cid in ids}
        for m in memberships:
            f = by_fid.get(m["faction_id"])
            if not f:
                continue
            result[m["character_id"]] = {
                "faction_name": f.get("name") or "",
                "faction_slug": f.get("slug") or "",
                "icon":         f.get("icon") or "shield",
                "color_hex":    f.get("color_hex") or "#888",
                "motto":        f.get("motto") or "",
                "nation_home":  f.get("nation_home") or "",
                "rank":         m.get("rank", "initiate"),
            }
        return result

    @api_router.get("/factions")
    async def list_factions(nation: Optional[str] = None, limit: int = 50):
        """Public list of all active, non-secret factions."""
        q = {"is_active": True, "is_secret": {"$ne": True}}
        if nation:
            q["nation_home"] = nation
        cursor = db.factions.find(q, {"_id": 0}).sort("member_count", -1).limit(min(limit, 200))
        return await cursor.to_list(length=None)

    @api_router.get("/factions/{slug}")
    async def get_faction(slug: str):
        f = await _get_faction(db, slug)
        return f

    @api_router.get("/factions/{slug}/members")
    async def list_members(slug: str, limit: int = 200):
        f = await _get_faction(db, slug)
        cursor = (
            db.faction_memberships
            .find({"faction_id": f["id"], "status": "active"}, {"_id": 0})
            .sort([("rank_index", -1), ("joined_at", 1)])
            .limit(min(limit, 500))
        )
        members = await cursor.to_list(length=None)
        # Sort by rank seniority descending, then by tenure ascending.
        members.sort(key=lambda m: (-_rank_index(m.get("rank", "initiate")), m.get("joined_at", "")))
        return members

    # ------------ Per-user reads ------------

    @api_router.get("/factions/my/membership")
    async def my_memberships(current_user: User = Depends(get_current_user)):
        """Every active membership held by any of MY characters."""
        # Pull this user's characters first.
        chars = await db.characters.find({"user_id": current_user.id}, {"_id": 0, "id": 1, "name": 1}).to_list(length=None)
        char_ids = [c["id"] for c in chars]
        if not char_ids:
            return []
        rows = await db.faction_memberships.find(
            {"character_id": {"$in": char_ids}, "status": "active"},
            {"_id": 0},
        ).to_list(length=None)
        return rows

    # ------------ Join / Leave ------------

    @api_router.post("/factions/{slug}/join")
    async def join_faction(
        slug: str,
        body: JoinFactionBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        char = await resolve_character_for_user(body.character_id, current_user)

        existing = await _get_membership(db, char["id"])
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"{char['name']} already belongs to a faction. Leave the current one first.",
            )

        rank = "initiate"
        doc = {
            "id": str(uuid.uuid4()),
            "character_id": char["id"],
            "character_name": char.get("name", ""),
            "user_id": current_user.id,
            "faction_id": f["id"],
            "faction_slug": f["slug"],
            "faction_name": f["name"],
            "rank": rank,
            "rank_index": _rank_index(rank),
            "pitch": (body.pitch or "").strip()[:600],
            "joined_at": _now_iso(),
            "left_at": None,
            "status": "active",  # active | left | expelled
            "reputation_contribution": 0,
        }
        await db.faction_memberships.insert_one(dict(doc))
        await _refresh_member_count(db, f["id"])
        return doc

    @api_router.post("/factions/{slug}/leave")
    async def leave_faction(
        slug: str,
        body: JoinFactionBody,  # reuses character_id field; pitch ignored
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        char = await resolve_character_for_user(body.character_id, current_user)

        membership = await _get_membership(db, char["id"])
        if not membership or membership["faction_id"] != f["id"]:
            raise HTTPException(status_code=404, detail=f"{char['name']} is not a member of {f['name']}.")
        # Leaders cannot leave directly — they must transfer first.
        if membership["rank"] == "leader":
            raise HTTPException(
                status_code=409,
                detail="The Leader cannot abandon their faction. Promote a successor first, or dissolve the faction.",
            )

        await db.faction_memberships.update_one(
            {"id": membership["id"]},
            {"$set": {"status": "left", "left_at": _now_iso()}},
        )
        await _refresh_member_count(db, f["id"])
        return {"ok": True, "left": f["name"]}

    # ------------ Rank changes (officer+/leader-only) ------------

    async def _authorize_rank_change(
        f: dict, actor_character_id: str, target_membership: dict, current_user
    ) -> dict:
        actor_mem = await _get_membership(db, actor_character_id)
        if not actor_mem or actor_mem["faction_id"] != f["id"]:
            raise HTTPException(status_code=403, detail="Your character is not in this faction.")
        # Ownership check — the actor character must belong to the calling user.
        if actor_mem["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own that character.")
        if not _can_manage(actor_mem["rank"], target_membership["rank"]):
            raise HTTPException(
                status_code=403,
                detail="You do not have authority over that member's rank.",
            )
        return actor_mem

    @api_router.post("/factions/{slug}/promote/{target_char_id}")
    async def promote_member(
        slug: str,
        target_char_id: str,
        body: RankChangeBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        target = await _get_membership(db, target_char_id)
        if not target or target["faction_id"] != f["id"]:
            raise HTTPException(status_code=404, detail="Target character is not in this faction.")

        await _authorize_rank_change(f, body.actor_character_id, target, current_user)

        new_idx = _rank_index(target["rank"]) + 1
        # Leaders are a singleton — cannot promote into Leader.
        if new_idx >= _rank_index("leader"):
            raise HTTPException(
                status_code=409,
                detail="Promotion to Leader requires a leadership transfer, not a routine promotion.",
            )
        new_rank = RANKS[new_idx]
        await db.faction_memberships.update_one(
            {"id": target["id"]},
            {"$set": {"rank": new_rank, "rank_index": new_idx}},
        )
        return {"ok": True, "rank": new_rank}

    @api_router.post("/factions/{slug}/demote/{target_char_id}")
    async def demote_member(
        slug: str,
        target_char_id: str,
        body: RankChangeBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        target = await _get_membership(db, target_char_id)
        if not target or target["faction_id"] != f["id"]:
            raise HTTPException(status_code=404, detail="Target character is not in this faction.")

        await _authorize_rank_change(f, body.actor_character_id, target, current_user)

        new_idx = _rank_index(target["rank"]) - 1
        if new_idx < 0:
            raise HTTPException(status_code=409, detail="An Initiate cannot be demoted further.")
        new_rank = RANKS[new_idx]
        await db.faction_memberships.update_one(
            {"id": target["id"]},
            {"$set": {"rank": new_rank, "rank_index": new_idx}},
        )
        return {"ok": True, "rank": new_rank}

    @api_router.post("/factions/{slug}/expel/{target_char_id}")
    async def expel_member(
        slug: str,
        target_char_id: str,
        body: RankChangeBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        target = await _get_membership(db, target_char_id)
        if not target or target["faction_id"] != f["id"]:
            raise HTTPException(status_code=404, detail="Target character is not in this faction.")

        # Only Leaders may expel; can never expel a leader (singleton).
        actor_mem = await _get_membership(db, body.actor_character_id)
        if not actor_mem or actor_mem["faction_id"] != f["id"] or actor_mem["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Your character is not in this faction.")
        if actor_mem["rank"] != "leader":
            raise HTTPException(status_code=403, detail="Only the Leader may expel a member.")
        if target["rank"] == "leader":
            raise HTTPException(status_code=409, detail="The Leader cannot be expelled.")

        await db.faction_memberships.update_one(
            {"id": target["id"]},
            {"$set": {"status": "expelled", "left_at": _now_iso()}},
        )
        await _refresh_member_count(db, f["id"])
        return {"ok": True, "expelled": target["character_name"]}

    # ------------ Faction-only Forum Threads (Round 2) ------------

    async def _require_active_membership(slug: str, character_id: str, current_user) -> tuple[dict, dict]:
        f = await _get_faction(db, slug)
        char = await resolve_character_for_user(character_id, current_user)
        mem = await _get_membership(db, char["id"])
        if not mem or mem["faction_id"] != f["id"]:
            raise HTTPException(
                status_code=403,
                detail=f"{char['name']} is not a member of {f['name']}.",
            )
        return f, mem

    @api_router.get("/factions/{slug}/threads")
    async def list_faction_threads(slug: str, limit: int = 80):
        """Public — but content body is intentionally short here; full content
        is gated below."""
        f = await _get_faction(db, slug)
        cursor = (
            db.faction_threads
            .find(
                {"faction_id": f["id"], "is_active": True},
                {"_id": 0, "content": 0},  # strip body from list — peek only
            )
            .sort("created_at", -1)
            .limit(min(limit, 200))
        )
        return await cursor.to_list(length=None)

    @api_router.get("/factions/{slug}/threads/{thread_id}")
    async def get_faction_thread(
        slug: str,
        thread_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Full thread + replies. The viewer must be an active member of the
        faction (any rank). Replies fetched alongside for one round-trip."""
        f = await _get_faction(db, slug)
        thread = await db.faction_threads.find_one(
            {"id": thread_id, "faction_id": f["id"], "is_active": True},
            {"_id": 0},
        )
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Membership check — any of the caller's characters in this faction?
        chars = await db.characters.find(
            {"user_id": current_user.id}, {"_id": 0, "id": 1}
        ).to_list(length=None)
        char_ids = [c["id"] for c in chars]
        is_member = await db.faction_memberships.count_documents({
            "character_id": {"$in": char_ids},
            "faction_id": f["id"],
            "status": "active",
        })
        # Admins always see; otherwise members only.
        is_admin = getattr(current_user, "role", "") == "admin"
        if not is_member and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="This thread is for faction members only.",
            )

        replies = await (
            db.faction_thread_replies
            .find({"thread_id": thread_id}, {"_id": 0})
            .sort("created_at", 1)
            .to_list(length=None)
        )
        return {"thread": thread, "replies": replies}

    @api_router.post("/factions/{slug}/threads")
    async def create_faction_thread(
        slug: str,
        body: CreateThreadBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_active_membership(slug, body.character_id, current_user)

        doc = {
            "id": str(uuid.uuid4()),
            "faction_id": f["id"],
            "faction_slug": f["slug"],
            "character_id": mem["character_id"],
            "character_name": mem["character_name"],
            "author_rank": mem["rank"],
            "title": body.title.strip()[:160],
            "content": body.content.strip()[:8000],
            "min_rank": body.min_rank if body.min_rank in RANKS else "initiate",
            "is_active": True,
            "replies_count": 0,
            "created_at": _now_iso(),
        }
        await db.faction_threads.insert_one(dict(doc))
        return doc

    @api_router.post("/factions/{slug}/threads/{thread_id}/replies")
    async def reply_to_thread(
        slug: str,
        thread_id: str,
        body: CreateThreadReplyBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_active_membership(slug, body.character_id, current_user)
        thread = await db.faction_threads.find_one(
            {"id": thread_id, "faction_id": f["id"], "is_active": True},
            {"_id": 0, "id": 1},
        )
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        doc = {
            "id": str(uuid.uuid4()),
            "thread_id": thread_id,
            "faction_id": f["id"],
            "character_id": mem["character_id"],
            "character_name": mem["character_name"],
            "author_rank": mem["rank"],
            "content": body.content.strip()[:4000],
            "created_at": _now_iso(),
        }
        await db.faction_thread_replies.insert_one(dict(doc))
        await db.faction_threads.update_one(
            {"id": thread_id}, {"$inc": {"replies_count": 1}}
        )
        return doc

    # ------------ Reputation (Round 2) ------------

    @api_router.get("/factions/{slug}/reputation")
    async def get_faction_reputation(slug: str):
        """Public — returns the faction's standing in each of the 5 nations.
        Missing rows are returned as score=0 (neutral). Always 5 rows."""
        f = await _get_faction(db, slug)
        existing = await (
            db.faction_reputation
            .find({"faction_id": f["id"]}, {"_id": 0})
            .to_list(length=None)
        )
        by_nation = {r["nation"]: r for r in existing}
        return [
            by_nation.get(n, {
                "faction_id": f["id"],
                "nation": n,
                "score": 0,
                "updated_at": None,
            })
            for n in NATIONS
        ]

    @api_router.post("/factions/{slug}/reputation/grant")
    async def admin_grant_reputation(
        slug: str,
        body: ReputationGrantBody,
        current_user: User = Depends(require_admin),
    ):
        if body.nation not in NATIONS:
            raise HTTPException(status_code=400, detail=f"Unknown nation: {body.nation}")
        f = await _get_faction(db, slug)
        row = await _apply_reputation_delta(
            db,
            faction_id=f["id"],
            nation=body.nation,
            delta=body.delta,
            reason=body.reason or f"Admin grant by {current_user.username}",
        )
        return row

    @api_router.get("/factions/{slug}/reputation/history")
    async def reputation_history(slug: str, limit: int = 30):
        f = await _get_faction(db, slug)
        cursor = (
            db.faction_reputation_history
            .find({"faction_id": f["id"]}, {"_id": 0})
            .sort("created_at", -1)
            .limit(min(limit, 200))
        )
        return await cursor.to_list(length=None)

    # ------------ Admin: create / deactivate ------------

    @api_router.post("/factions/admin/create")
    async def admin_create_faction(
        body: CreateFactionBody,
        current_user: User = Depends(require_admin),
    ):
        existing = await db.factions.find_one({"slug": body.slug}, {"_id": 0, "id": 1})
        if existing:
            raise HTTPException(status_code=409, detail=f"Faction slug '{body.slug}' already exists.")
        doc = {
            "id": str(uuid.uuid4()),
            "slug": body.slug,
            "name": body.name,
            "description": body.description.strip()[:2000],
            "motto": (body.motto or "").strip()[:200],
            "nation_home": (body.nation_home or "").strip()[:64],
            "color_hex": body.color_hex or "#a855f7",
            "icon": body.icon or "shield",
            "is_secret": body.is_secret,
            "is_active": True,
            "member_count": 0,
            "leader_character_id": None,
            "founded_at": _now_iso(),
        }
        await db.factions.insert_one(dict(doc))
        return doc

    @api_router.post("/factions/admin/seed-starter")
    async def admin_seed_starter_factions(_: User = Depends(require_admin)):
        """Idempotent: insert the 6 canonical starter factions if missing,
        otherwise refresh their copy. Also ensures each starter faction has
        a seeded NPC roster (6 NPCs: 2 officers + 4 members) and a starting
        treasury of 1,000,000 gold so they feel established.

        Safe to call repeatedly — NPC seeding skips factions that already
        have starter-source NPCs, and the treasury is only initialised when
        the balance is below the starting endowment.
        """
        from starter_factions import STARTER_FACTIONS
        from faction_npcs import seed_starter_npcs
        STARTER_TREASURY_GOLD = 1_000_000
        now = _now_iso()
        results = {
            "inserted": [],
            "updated": [],
            "npcs_seeded": {},
            "treasuries_initialised": [],
            "total": len(STARTER_FACTIONS),
        }
        for f in STARTER_FACTIONS:
            existing = await db.factions.find_one({"slug": f["slug"]}, {"_id": 0, "id": 1})
            base = {
                **f,
                "is_active": True,
                "is_secret": False,
                "leader_character_id": None,
            }
            if existing:
                update_doc = {k: v for k, v in base.items() if k != "id"}
                await db.factions.update_one({"id": existing["id"]}, {"$set": update_doc})
                results["updated"].append(f["slug"])
                faction_id = existing["id"]
            else:
                base["id"] = str(uuid.uuid4())
                base["founded_at"] = now
                base["member_count"] = 0
                await db.factions.insert_one(dict(base))
                results["inserted"].append(f["slug"])
                faction_id = base["id"]

            # Re-read the canonical doc — we need the id for NPC seed + treasury.
            faction = await db.factions.find_one({"id": faction_id}, {"_id": 0})

            # NPC roster — only seeds if no starter-source NPCs exist yet.
            seeded = await seed_starter_npcs(db, faction=faction, count=6)
            if seeded:
                results["npcs_seeded"][f["slug"]] = len(seeded)

            # Treasury — initialise only when below the starter endowment.
            treasury = await db.faction_treasury.find_one(
                {"faction_id": faction_id}, {"_id": 0},
            )
            if not treasury:
                await db.faction_treasury.insert_one({
                    "id": str(uuid.uuid4()),
                    "faction_id": faction_id,
                    "balance": STARTER_TREASURY_GOLD,
                    "total_donated": STARTER_TREASURY_GOLD,
                    "updated_at": now,
                })
                await db.faction_treasury_log.insert_one({
                    "id": str(uuid.uuid4()),
                    "faction_id": faction_id,
                    "kind": "starter_endowment",
                    "amount": STARTER_TREASURY_GOLD,
                    "character_id": None,
                    "character_name": "The Realm",
                    "created_at": now,
                })
                results["treasuries_initialised"].append(f["slug"])
            elif treasury.get("balance", 0) < STARTER_TREASURY_GOLD:
                # Top-up: only fill the gap, don't reset abundant treasuries.
                topup = STARTER_TREASURY_GOLD - treasury["balance"]
                await db.faction_treasury.update_one(
                    {"faction_id": faction_id},
                    {"$inc": {"balance": topup, "total_donated": topup},
                     "$set": {"updated_at": now}},
                )
                await db.faction_treasury_log.insert_one({
                    "id": str(uuid.uuid4()),
                    "faction_id": faction_id,
                    "kind": "starter_topup",
                    "amount": topup,
                    "character_id": None,
                    "character_name": "The Realm",
                    "created_at": now,
                })
                results["treasuries_initialised"].append(f["slug"])
        return results

    # ------------ Player-founded faction charter system ------------

    async def _faction_slug_exists(slug: str) -> bool:
        """True if a faction OR a pending charter is already using this slug."""
        if await db.factions.find_one({"slug": slug}, {"_id": 0, "id": 1}):
            return True
        existing = await db.faction_charters.find_one(
            {"slug": slug, "status": "pending"}, {"_id": 0, "id": 1},
        )
        return existing is not None

    @api_router.post("/factions/charter")
    async def file_faction_charter(
        body: FileCharterBody,
        current_user: User = Depends(get_current_user),
    ):
        """A player submits a charter to found a new faction. Costs 5000 gold
        up-front (refunded if rejected). Character must belong to the
        applicant and not already be in another faction. Goes to admin review.
        """
        # Validate the character belongs to this user.
        char = await resolve_character_for_user(body.character_id, current_user)
        # That character must not already be in any active faction (Leader-conflict).
        active = await db.faction_memberships.find_one(
            {"character_id": char["id"], "status": "active"}, {"_id": 0, "id": 1},
        )
        if active:
            raise HTTPException(
                status_code=409,
                detail=f"{char['name']} is already a member of another faction. Leave it before founding a new one.",
            )
        # Already has a pending charter?
        pending = await db.faction_charters.find_one(
            {"applicant_user_id": current_user.id, "status": "pending"}, {"_id": 0, "id": 1},
        )
        if pending:
            raise HTTPException(status_code=409, detail="You already have a charter under admin review.")
        # Icon must be in allowed set.
        icon = body.icon if body.icon in ALLOWED_FACTION_ICONS else "shield"
        # Slug
        slug = _slugify(body.name)
        if not slug or len(slug) < 3:
            raise HTTPException(status_code=400, detail="Faction name produces an invalid slug. Try a different name.")
        if await _faction_slug_exists(slug):
            raise HTTPException(status_code=409, detail=f"A faction or pending charter already uses the slug '{slug}'.")
        # Funds
        if (current_user.currency or 0) < FACTION_CHARTER_COST_GOLD:
            raise HTTPException(
                status_code=400,
                detail=f"Founding a faction costs {FACTION_CHARTER_COST_GOLD} gold. You hold {current_user.currency}.",
            )

        # Validate offered goods (if any) up-front so we don't take the gold
        # for a charter doomed by a bad good_slug.
        offered_goods_payload = []
        if body.offered_goods:
            for og in body.offered_goods:
                good = await db.goods.find_one({"slug": og.good_slug}, {"_id": 0, "slug": 1})
                if not good:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Good '{og.good_slug}' is not in the realm's catalogue. Pick from /api/economy/goods.",
                    )
                offered_goods_payload.append({
                    "good_slug": og.good_slug,
                    "base_cost": int(og.base_cost),
                    "capacity": int(og.capacity),
                    "description": (og.description or "")[:400],
                })

        # Debit gold (refunded on rejection by the review endpoint).
        await db.users.update_one(
            {"id": current_user.id}, {"$inc": {"currency": -FACTION_CHARTER_COST_GOLD}},
        )

        doc = {
            "id": str(uuid.uuid4()),
            "applicant_user_id": current_user.id,
            "applicant_username": current_user.username,
            "character_id": char["id"],
            "character_name": char.get("name", ""),
            "name": body.name.strip()[:80],
            "slug": slug,
            "motto": (body.motto or "").strip()[:200],
            "description": body.description.strip()[:2000],
            "nation_home": (body.nation_home or "").strip()[:64],
            "color_hex": (body.color_hex or "#a855f7")[:9],
            "icon": icon,
            "offered_goods": offered_goods_payload,
            "status": "pending",
            "cost_paid": FACTION_CHARTER_COST_GOLD,
            "created_at": _now_iso(),
            "reviewed_at": None,
            "reviewed_by": None,
            "review_note": "",
        }
        await db.faction_charters.insert_one(dict(doc))
        return doc

    @api_router.get("/factions/charter/mine")
    async def get_my_charters(current_user: User = Depends(get_current_user)):
        """Recent charters this user has filed (any status)."""
        rows = await db.faction_charters.find(
            {"applicant_user_id": current_user.id}, {"_id": 0},
        ).sort("created_at", -1).limit(20).to_list(length=None)
        return rows

    @api_router.get("/admin/factions/charters")
    async def admin_list_charters(
        status: str = "pending",
        _: User = Depends(require_admin),
    ):
        """List charters by status (pending|approved|rejected|all)."""
        q = {} if status == "all" else {"status": status}
        rows = await db.faction_charters.find(q, {"_id": 0}).sort("created_at", -1).to_list(length=None)
        return rows

    @api_router.post("/admin/factions/charters/{charter_id}/approve")
    async def admin_approve_charter(
        charter_id: str,
        body: CharterReviewBody,
        current_user: User = Depends(require_admin),
    ):
        """Approve a pending charter. Creates the faction, makes the applicant's
        character its Leader, and seeds founding NPC members."""
        c = await db.faction_charters.find_one({"id": charter_id}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Charter not found.")
        if c["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Charter is already {c['status']}.")

        slug = body.slug_override or c["slug"]
        slug = _slugify(slug)
        if not slug:
            raise HTTPException(status_code=400, detail="Slug is invalid.")
        # Allow the charter's own slug to pass through; collide only with
        # OTHER factions or OTHER pending charters.
        clash = await db.factions.find_one({"slug": slug}, {"_id": 0, "id": 1})
        if not clash:
            clash = await db.faction_charters.find_one(
                {"slug": slug, "status": "pending", "id": {"$ne": c["id"]}}, {"_id": 0, "id": 1},
            )
        if clash:
            raise HTTPException(status_code=409, detail=f"Slug '{slug}' is taken.")

        # Create the faction.
        faction_id = str(uuid.uuid4())
        faction_doc = {
            "id": faction_id,
            "slug": slug,
            "name": c["name"],
            "description": c["description"],
            "motto": c.get("motto") or "",
            "nation_home": c.get("nation_home") or "",
            "color_hex": c.get("color_hex") or "#a855f7",
            "icon": c.get("icon") or "shield",
            "is_secret": False,
            "is_active": True,
            "member_count": 0,
            "leader_character_id": c["character_id"],
            "founded_at": _now_iso(),
            "founded_by_user_id": c["applicant_user_id"],
            "founded_by_charter_id": c["id"],
        }
        await db.factions.insert_one(dict(faction_doc))

        # Make the applicant's character the Leader.
        membership = {
            "id": str(uuid.uuid4()),
            "character_id": c["character_id"],
            "character_name": c["character_name"],
            "user_id": c["applicant_user_id"],
            "faction_id": faction_id,
            "faction_name": c["name"],
            "faction_slug": slug,
            "rank": "leader",
            "rank_index": _rank_index("leader"),
            "status": "active",
            "joined_at": _now_iso(),
            "left_at": None,
            "pitch": "Founder",
            "reputation_contribution": 0,
        }
        await db.faction_memberships.insert_one(dict(membership))
        await db.factions.update_one({"id": faction_id}, {"$set": {"member_count": 1}})

        # Mark the charter approved.
        await db.faction_charters.update_one(
            {"id": charter_id},
            {"$set": {
                "status": "approved",
                "reviewed_at": _now_iso(),
                "reviewed_by": current_user.id,
                "review_note": (body.note or "").strip()[:400],
                "faction_id": faction_id,
                "faction_slug": slug,
            }},
        )

        # Seed founding NPC members (Phase C — fire-and-forget; soft-fail).
        try:
            from faction_npcs import seed_founding_npcs
            await seed_founding_npcs(db, faction=faction_doc, count=3)
        except Exception as npc_err:
            import logging
            logging.getLogger(__name__).warning(f"NPC seeding failed (non-fatal): {npc_err}")

        # Seed declared offerings into the economy specialties table. The
        # applicant declared these at charter-filing time; on approval they
        # become the founding "lineup" of what this faction produces and at
        # what price. Soft-fail — never block approval on an economy hiccup.
        try:
            from economy_service import EconomyService
            offered = c.get("offered_goods") or []
            if offered:
                es = EconomyService(db)
                for og in offered:
                    await es.upsert_specialty(
                        faction_id=faction_id,
                        faction_slug=slug,
                        good_slug=og.get("good_slug", ""),
                        base_cost=int(og.get("base_cost", 50)),
                        capacity=int(og.get("capacity", 50)),
                        description=og.get("description", ""),
                        reason="Declared in founding charter",
                    )
        except Exception as econ_err:
            import logging
            logging.getLogger(__name__).warning(f"Charter offered_goods seed failed (non-fatal): {econ_err}")

        return {"ok": True, "faction": faction_doc}

    @api_router.post("/admin/factions/charters/{charter_id}/reject")
    async def admin_reject_charter(
        charter_id: str,
        body: CharterReviewBody,
        current_user: User = Depends(require_admin),
    ):
        """Reject a pending charter and refund the cost to the applicant."""
        c = await db.faction_charters.find_one({"id": charter_id}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Charter not found.")
        if c["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Charter is already {c['status']}.")

        # Refund.
        refund = c.get("cost_paid", FACTION_CHARTER_COST_GOLD)
        if refund > 0:
            await db.users.update_one(
                {"id": c["applicant_user_id"]}, {"$inc": {"currency": refund}},
            )

        await db.faction_charters.update_one(
            {"id": charter_id},
            {"$set": {
                "status": "rejected",
                "reviewed_at": _now_iso(),
                "reviewed_by": current_user.id,
                "review_note": (body.note or "").strip()[:400],
                "refunded": refund,
            }},
        )
        return {"ok": True, "refunded": refund}

    @api_router.post("/factions/admin/seed-leaders")
    async def admin_seed_leaders(
        body: SeedLeadersBody,
        current_user: User = Depends(require_admin),
    ):
        """Promote a chosen character to Leader of each named faction.
        The character must already be an active member of that faction.
        Idempotent — re-running just re-sets the same character to Leader."""
        results = {}
        for fac_slug, char_id in body.assignments.items():
            f = await db.factions.find_one({"slug": fac_slug, "is_active": True}, {"_id": 0})
            if not f:
                results[fac_slug] = {"ok": False, "error": "faction not found"}
                continue
            mem = await db.faction_memberships.find_one(
                {"character_id": char_id, "faction_id": f["id"], "status": "active"},
                {"_id": 0},
            )
            if not mem:
                results[fac_slug] = {"ok": False, "error": "character is not an active member"}
                continue
            await db.faction_memberships.update_one(
                {"id": mem["id"]},
                {"$set": {"rank": "leader", "rank_index": _rank_index("leader")}},
            )
            await db.factions.update_one(
                {"id": f["id"]},
                {"$set": {"leader_character_id": char_id}},
            )
            results[fac_slug] = {"ok": True, "leader": mem["character_name"]}
        return results

    # ============================================================
    # Round 3 — Faction Quests, Treasury, Rivalry
    # ============================================================

    # ---- Authorisation helpers (Round 3 specific) ----
    async def _require_officer_plus(slug: str, actor_character_id: str, current_user) -> tuple[dict, dict]:
        f = await _get_faction(db, slug)
        mem = await _get_membership(db, actor_character_id)
        if not mem or mem["faction_id"] != f["id"]:
            raise HTTPException(status_code=403, detail="Your character is not in this faction.")
        if mem["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own that character.")
        if _rank_index(mem["rank"]) < _rank_index("officer"):
            raise HTTPException(status_code=403, detail="Only Officers and the Leader may take this action.")
        return f, mem

    async def _require_leader(slug: str, actor_character_id: str, current_user) -> tuple[dict, dict]:
        f, mem = await _require_officer_plus(slug, actor_character_id, current_user)
        if mem["rank"] != "leader":
            raise HTTPException(status_code=403, detail="Only the Leader may take this action.")
        return f, mem

    # ---- Treasury ----
    async def _get_or_init_treasury(faction_id: str) -> dict:
        row = await db.faction_treasury.find_one({"faction_id": faction_id}, {"_id": 0})
        if row:
            return row
        fresh = {
            "id": str(uuid.uuid4()),
            "faction_id": faction_id,
            "balance": 0,
            "total_donated": 0,
            "updated_at": _now_iso(),
        }
        await db.faction_treasury.insert_one(dict(fresh))
        return fresh

    @api_router.get("/factions/{slug}/treasury")
    async def get_treasury(slug: str):
        f = await _get_faction(db, slug)
        return await _get_or_init_treasury(f["id"])

    @api_router.post("/factions/{slug}/treasury/donate")
    async def donate_to_treasury(
        slug: str,
        body: DonateBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        char = await resolve_character_for_user(body.character_id, current_user)
        # Must be active member.
        mem = await _get_membership(db, char["id"])
        if not mem or mem["faction_id"] != f["id"]:
            raise HTTPException(status_code=403, detail=f"{char['name']} is not a member of {f['name']}.")
        # Donor must have the gold (currency lives on USER, not character).
        if (current_user.currency or 0) < body.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient gold. You hold {current_user.currency}.")

        # Atomically move the gold: user -1, treasury +1.
        await db.users.update_one({"id": current_user.id}, {"$inc": {"currency": -body.amount}})
        await _get_or_init_treasury(f["id"])
        await db.faction_treasury.update_one(
            {"faction_id": f["id"]},
            {
                "$inc": {"balance": body.amount, "total_donated": body.amount},
                "$set": {"updated_at": _now_iso()},
            },
        )
        await db.faction_treasury_log.insert_one({
            "id": str(uuid.uuid4()),
            "faction_id": f["id"],
            "kind": "donation",
            "character_id": char["id"],
            "character_name": char.get("name", ""),
            "amount": body.amount,
            "created_at": _now_iso(),
        })
        treasury = await db.faction_treasury.find_one({"faction_id": f["id"]}, {"_id": 0})
        return {"ok": True, "treasury": treasury}

    # ---- Quests ----
    async def _build_quest_doc(
        f: dict, author_mem: dict, *, title: str, objective: str, flavour: str,
        reward_gold: int, reward_reputation: int, max_completions: int, source: str,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "faction_id": f["id"],
            "faction_slug": f["slug"],
            "title": title.strip()[:120],
            "objective": objective.strip()[:600],
            "flavour": (flavour or "").strip()[:200],
            "reward_gold": reward_gold,
            "reward_reputation": reward_reputation,
            "max_completions": max_completions,
            "completion_count": 0,
            "is_active": True,
            "source": source,  # 'manual' or 'ai'
            "issued_by_character_id": author_mem["character_id"],
            "issued_by_character_name": author_mem["character_name"],
            "issued_by_rank": author_mem["rank"],
            "created_at": _now_iso(),
        }

    @api_router.get("/factions/{slug}/quests")
    async def list_faction_quests(slug: str, include_closed: bool = False, limit: int = 60):
        f = await _get_faction(db, slug)
        q: dict = {"faction_id": f["id"]}
        if not include_closed:
            q["is_active"] = True
        cursor = (
            db.faction_quests.find(q, {"_id": 0})
            .sort("created_at", -1)
            .limit(min(limit, 200))
        )
        return await cursor.to_list(length=None)

    @api_router.post("/factions/{slug}/quests")
    async def create_faction_quest(
        slug: str,
        body: CreateQuestBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_officer_plus(slug, body.actor_character_id, current_user)
        doc = await _build_quest_doc(
            f, mem,
            title=body.title, objective=body.objective, flavour=body.flavour or "",
            reward_gold=body.reward_gold, reward_reputation=body.reward_reputation,
            max_completions=body.max_completions, source="manual",
        )
        await db.faction_quests.insert_one(dict(doc))
        return doc

    @api_router.post("/factions/{slug}/quests/ai-generate")
    async def ai_generate_faction_quest(
        slug: str,
        body: AiGenerateQuestBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_officer_plus(slug, body.actor_character_id, current_user)

        # Pull the strongest rivalry (if any) to spice the prompt.
        rival_name: Optional[str] = None
        top_rival = await db.faction_rivalries.find_one(
            {"$or": [{"faction_a_id": f["id"]}, {"faction_b_id": f["id"]}]},
            {"_id": 0},
            sort=[("intensity", -1)],
        )
        if top_rival and top_rival.get("intensity", 0) >= 25:
            rival_id = (
                top_rival["faction_b_id"] if top_rival["faction_a_id"] == f["id"]
                else top_rival["faction_a_id"]
            )
            rival = await db.factions.find_one({"id": rival_id}, {"_id": 0, "name": 1})
            if rival:
                rival_name = rival["name"]

        from faction_ai import generate_faction_quest
        ai = await generate_faction_quest(f, rival_name=rival_name)
        doc = await _build_quest_doc(
            f, mem,
            title=ai["title"], objective=ai["objective"], flavour=ai["flavour"],
            reward_gold=body.reward_gold, reward_reputation=body.reward_reputation,
            max_completions=body.max_completions, source="ai",
        )
        await db.faction_quests.insert_one(dict(doc))
        return doc

    @api_router.post("/factions/{slug}/quests/{quest_id}/complete")
    async def complete_faction_quest(
        slug: str,
        quest_id: str,
        body: CompleteQuestBody,
        current_user: User = Depends(get_current_user),
    ):
        f = await _get_faction(db, slug)
        char = await resolve_character_for_user(body.character_id, current_user)
        mem = await _get_membership(db, char["id"])
        if not mem or mem["faction_id"] != f["id"]:
            raise HTTPException(status_code=403, detail=f"{char['name']} is not a member of {f['name']}.")

        quest = await db.faction_quests.find_one(
            {"id": quest_id, "faction_id": f["id"], "is_active": True}, {"_id": 0}
        )
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found or already closed.")

        # One completion per character per quest.
        already = await db.faction_quest_completions.find_one(
            {"quest_id": quest_id, "character_id": char["id"]}, {"_id": 0, "id": 1}
        )
        if already:
            raise HTTPException(status_code=409, detail="Your character has already completed this quest.")
        if quest["completion_count"] >= quest["max_completions"]:
            raise HTTPException(status_code=409, detail="This quest has already been completed in full.")

        # Reward: gold to user wallet, +rep to faction in faction's home nation, +rep contribution on membership.
        completion = {
            "id": str(uuid.uuid4()),
            "quest_id": quest_id,
            "faction_id": f["id"],
            "character_id": char["id"],
            "character_name": char.get("name", ""),
            "user_id": current_user.id,
            "proof": (body.proof or "").strip()[:600],
            "gold_paid": quest["reward_gold"],
            "reputation_paid": quest["reward_reputation"],
            "completed_at": _now_iso(),
        }
        await db.faction_quest_completions.insert_one(dict(completion))

        new_count = quest["completion_count"] + 1
        updates = {"$inc": {"completion_count": 1}}
        if new_count >= quest["max_completions"]:
            updates["$set"] = {"is_active": False, "closed_at": _now_iso()}
        await db.faction_quests.update_one({"id": quest_id}, updates)

        if quest["reward_gold"] > 0:
            await db.users.update_one({"id": current_user.id}, {"$inc": {"currency": quest["reward_gold"]}})
        if quest["reward_reputation"] > 0 and f.get("nation_home"):
            await _apply_reputation_delta(
                db,
                faction_id=f["id"],
                nation=f["nation_home"],
                delta=quest["reward_reputation"],
                reason=f"Quest «{quest['title']}» completed by {char.get('name', '')}.",
            )
        await db.faction_memberships.update_one(
            {"id": mem["id"]},
            {"$inc": {"reputation_contribution": quest["reward_reputation"]}},
        )
        return {"ok": True, "completion": completion, "quest_closed": new_count >= quest["max_completions"]}

    @api_router.post("/factions/{slug}/quests/{quest_id}/close")
    async def close_faction_quest(
        slug: str,
        quest_id: str,
        body: RankChangeBody,
        current_user: User = Depends(get_current_user),
    ):
        f, _mem = await _require_officer_plus(slug, body.actor_character_id, current_user)
        quest = await db.faction_quests.find_one({"id": quest_id, "faction_id": f["id"]}, {"_id": 0, "id": 1})
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found.")
        await db.faction_quests.update_one(
            {"id": quest_id},
            {"$set": {"is_active": False, "closed_at": _now_iso()}},
        )
        return {"ok": True}

    # ---- Rivalries ----
    async def _find_rivalry(faction_a_id: str, faction_b_id: str) -> Optional[dict]:
        pair = _rivalry_pair(faction_a_id, faction_b_id)
        return await db.faction_rivalries.find_one(
            {"faction_a_id": pair[0], "faction_b_id": pair[1]}, {"_id": 0}
        )

    @api_router.get("/factions/{slug}/rivalries")
    async def list_rivalries(slug: str):
        f = await _get_faction(db, slug)
        rows = await db.faction_rivalries.find(
            {"$or": [{"faction_a_id": f["id"]}, {"faction_b_id": f["id"]}]},
            {"_id": 0},
        ).sort("intensity", -1).to_list(length=None)
        # Decorate with the *other* faction's identity so the UI doesn't need a 2nd round-trip.
        for r in rows:
            other_id = r["faction_b_id"] if r["faction_a_id"] == f["id"] else r["faction_a_id"]
            other = await db.factions.find_one(
                {"id": other_id},
                {"_id": 0, "id": 1, "slug": 1, "name": 1, "icon": 1, "color_hex": 1, "nation_home": 1},
            )
            r["rival"] = other or {"id": other_id, "name": "Unknown faction"}
        return rows

    @api_router.post("/factions/{slug}/rivalries/declare")
    async def declare_rivalry(
        slug: str,
        body: DeclareRivalryBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_leader(slug, body.actor_character_id, current_user)
        if body.target_slug == slug:
            raise HTTPException(status_code=400, detail="A faction cannot be its own rival.")
        target = await _get_faction(db, body.target_slug)

        existing = await _find_rivalry(f["id"], target["id"])
        if existing and existing.get("intensity", 0) >= 25:
            raise HTTPException(status_code=409, detail=f"A rivalry with {target['name']} is already in play.")

        intensity = 25  # 'declared' tier
        pair = _rivalry_pair(f["id"], target["id"])
        now = _now_iso()
        if existing:
            await db.faction_rivalries.update_one(
                {"id": existing["id"]},
                {
                    "$set": {
                        "intensity": intensity,
                        "status": _rivalry_status(intensity),
                        "last_escalated_at": now,
                    },
                    "$push": {"history": {
                        "id": str(uuid.uuid4()),
                        "delta": intensity - (existing.get("intensity", 0) or 0),
                        "intensity_after": intensity,
                        "reason": (body.reason or f"Declared by {mem['character_name']}")[:300],
                        "kind": "declare",
                        "created_at": now,
                    }},
                },
            )
            return await db.faction_rivalries.find_one({"id": existing["id"]}, {"_id": 0})

        doc = {
            "id": str(uuid.uuid4()),
            "faction_a_id": pair[0],
            "faction_b_id": pair[1],
            "declared_by_faction_id": f["id"],
            "declared_by_character_id": mem["character_id"],
            "declared_by_character_name": mem["character_name"],
            "reason": (body.reason or "").strip()[:400],
            "intensity": intensity,
            "status": _rivalry_status(intensity),
            "created_at": now,
            "last_escalated_at": now,
            "history": [{
                "id": str(uuid.uuid4()),
                "delta": intensity,
                "intensity_after": intensity,
                "reason": f"Declared by {mem['character_name']}.",
                "kind": "declare",
                "created_at": now,
            }],
        }
        await db.faction_rivalries.insert_one(dict(doc))
        return doc

    @api_router.post("/factions/{slug}/rivalries/{rivalry_id}/escalate")
    async def escalate_rivalry(
        slug: str,
        rivalry_id: str,
        body: EscalateRivalryBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_leader(slug, body.actor_character_id, current_user)
        r = await db.faction_rivalries.find_one({"id": rivalry_id}, {"_id": 0})
        if not r or f["id"] not in (r["faction_a_id"], r["faction_b_id"]):
            raise HTTPException(status_code=404, detail="Rivalry not found.")

        old_intensity = (r.get("intensity", 0) or 0)
        new_intensity = min(RIVALRY_MAX_INTENSITY, old_intensity + body.delta)
        await db.faction_rivalries.update_one(
            {"id": rivalry_id},
            {
                "$set": {
                    "intensity": new_intensity,
                    "status": _rivalry_status(new_intensity),
                    "last_escalated_at": _now_iso(),
                },
                "$push": {"history": {
                    "id": str(uuid.uuid4()),
                    "delta": body.delta,
                    "intensity_after": new_intensity,
                    "reason": (body.reason or f"Escalated by {mem['character_name']}")[:300],
                    "kind": "escalate",
                    "created_at": _now_iso(),
                }},
            },
        )
        # P1.5 — Economy hook: leader-driven escalation can also tip the
        # rivalry into hostile territory; break any standing contracts.
        from routes._factions_lib import _maybe_break_contracts_on_hostility
        await _maybe_break_contracts_on_hostility(
            db,
            faction_a_id=r["faction_a_id"],
            faction_b_id=r["faction_b_id"],
            old_intensity=old_intensity,
            new_intensity=new_intensity,
            reason=(body.reason or f"Leader escalation by {mem['character_name']}")[:160],
        )
        return await db.faction_rivalries.find_one({"id": rivalry_id}, {"_id": 0})

    @api_router.post("/factions/{slug}/rivalries/{rivalry_id}/sue-for-peace")
    async def sue_for_peace(
        slug: str,
        rivalry_id: str,
        body: RankChangeBody,
        current_user: User = Depends(get_current_user),
    ):
        f, mem = await _require_leader(slug, body.actor_character_id, current_user)
        r = await db.faction_rivalries.find_one({"id": rivalry_id}, {"_id": 0})
        if not r or f["id"] not in (r["faction_a_id"], r["faction_b_id"]):
            raise HTTPException(status_code=404, detail="Rivalry not found.")

        await db.faction_rivalries.update_one(
            {"id": rivalry_id},
            {
                "$set": {
                    "intensity": 0,
                    "status": "dormant",
                    "last_escalated_at": _now_iso(),
                },
                "$push": {"history": {
                    "id": str(uuid.uuid4()),
                    "delta": -(r.get("intensity", 0) or 0),
                    "intensity_after": 0,
                    "reason": f"Peace sued by {mem['character_name']} of {f['name']}.",
                    "kind": "peace",
                    "created_at": _now_iso(),
                }},
            },
        )
        return await db.faction_rivalries.find_one({"id": rivalry_id}, {"_id": 0})

    @api_router.get("/admin/factions/rivalries")
    async def admin_list_all_rivalries(_: User = Depends(require_admin)):
        rows = await db.faction_rivalries.find({}, {"_id": 0}).sort("intensity", -1).to_list(length=None)
        # Decorate with both faction names for admin readability.
        for r in rows:
            for key, target_field in (("faction_a_id", "faction_a"), ("faction_b_id", "faction_b")):
                fdoc = await db.factions.find_one(
                    {"id": r[key]}, {"_id": 0, "id": 1, "slug": 1, "name": 1, "icon": 1, "color_hex": 1},
                )
                r[target_field] = fdoc or {"id": r[key], "name": "Unknown"}
        return rows

    # ------------ NPC roster (Phase C of player-founded factions) ------------

    @api_router.get("/factions/{slug}/npcs")
    async def list_faction_npcs(slug: str):
        """Public list of all active NPC members of this faction."""
        f = await _get_faction(db, slug)
        rows = await db.faction_npcs.find(
            {"faction_id": f["id"], "is_active": True}, {"_id": 0},
        ).sort("joined_at", 1).to_list(length=None)
        return rows

    @api_router.post("/factions/{slug}/tick")
    async def faction_tick_lazy(slug: str):
        """Lazy world-tick — invoked opportunistically from the faction detail
        page load. Self-throttles to once every 6h per faction. Public (any
        visitor can trigger), but the throttle keeps the cost bounded."""
        f = await _get_faction(db, slug)
        last = f.get("npc_tick_at")
        if last:
            try:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - last_dt < timedelta(hours=6):
                    return {"ok": True, "skipped": "throttled"}
            except Exception:
                pass
        from faction_npcs import tick_faction
        summary = await tick_faction(db, faction=f)
        return {"ok": True, "summary": summary}

    @api_router.post("/admin/factions/{slug}/tick")
    async def admin_force_tick(slug: str, _: User = Depends(require_admin)):
        """Admin-only: force an immediate world-tick on a faction, bypassing
        the 6-hour throttle. Useful for testing and for manually nudging
        sleepy player-founded factions."""
        f = await _get_faction(db, slug)
        from faction_npcs import tick_faction
        summary = await tick_faction(db, faction=f)
        return {"ok": True, "summary": summary}

