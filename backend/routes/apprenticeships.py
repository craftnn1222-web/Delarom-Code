"""
Apprenticeships (Phase 5, 2026-05-30).

A character may apprentice under a master NPC of a specific craft. The
apprenticeship is tracked across scenes with three ranks
(initiate → journeyman → master) and a list of milestones the player or
mentor records as the relationship progresses.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException


CRAFTS = [
    "smith", "mage", "bard", "surgeon", "scribe", "alchemist",
    "ranger", "scholar", "duelist", "priest", "shadowblade", "navigator",
    "loremaster", "tailor", "huntsman", "courier",
]
RANKS = ["initiate", "journeyman", "master"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprenticeshipStart(BaseModel):
    character_id: str
    mentor_npc_id: str
    craft: str = Field(description="One of CRAFTS")
    intro_text: Optional[str] = Field(default="", max_length=400)


class MilestoneRecord(BaseModel):
    text: str = Field(min_length=3, max_length=300)


class RankBump(BaseModel):
    rank: str = Field(description="One of RANKS")


def attach_apprenticeship_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/apprenticeships/crafts")
    async def list_crafts():
        return {"crafts": CRAFTS, "ranks": RANKS}

    @api_router.post("/apprenticeships/admin/seed-masters")
    async def seed_masters(current_user: User = Depends(get_current_user)):
        """Admin-only — seed the 80 canonical master NPCs (16 crafts × 5 nations).

        Idempotent: skips any (name, nation) pair already present. Exists so
        production can be seeded from the admin Database panel without
        shell access. Mirrors the CLI runner at
        `python backend/seed_master_npcs.py`.
        """
        if current_user.role not in ("admin", "moderator"):
            raise HTTPException(status_code=403, detail="Admin only")
        # Imported lazily so the bulk MASTERS data only loads on demand.
        from seed_master_npcs import seed_master_npcs
        summary = await seed_master_npcs(db)
        return summary

    @api_router.get("/apprenticeships/featured-master")
    async def featured_master():
        """Public — return one master NPC, deterministic per ISO week.

        Used by the Quill & Coffer front page to surface a different master
        every week so apprenticeships feel like a living, rotating wonder of
        the realm rather than a static directory. Rotation is stable for the
        whole week (Mon-Sun) and reproducible across servers because the
        index is `(iso_year * 53 + iso_week) % count` after sorting by NPC
        id so the candidate list is stable across calls.
        """
        cursor = db.npcs.find(
            {"craft": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "race": 1, "role": 1,
             "nation": 1, "location": 1, "craft": 1, "quirks": 1,
             "personality": 1, "motivation": 1},
        ).sort("id", 1)
        masters = await cursor.to_list(1000)
        if not masters:
            raise HTTPException(status_code=404, detail="No master NPCs are seeded yet.")
        now = datetime.now(timezone.utc).isocalendar()
        idx = (now.year * 53 + now.week) % len(masters)
        chosen = masters[idx]
        # Compose a small "ISO week tag" so the client can show e.g. "2026-W22".
        chosen["iso_week"] = f"{now.year}-W{now.week:02d}"
        return chosen

    @api_router.get("/apprenticeships/mentors")
    async def search_mentors(
        q: Optional[str] = None,
        craft: Optional[str] = None,
        nation: Optional[str] = None,
        limit: int = 12,
    ):
        """Public — search master NPCs available as mentors.

        Only returns NPCs that have a `craft` field set (i.e. seeded as masters).
        Supports name substring (`q`), exact craft, and exact nation filtering.
        """
        query: Dict = {"craft": {"$exists": True, "$ne": None}}
        if craft:
            if craft not in CRAFTS:
                raise HTTPException(status_code=400, detail=f"Invalid craft. Choose one of {CRAFTS}")
            query["craft"] = craft
        if nation:
            # Nation slugs on NPCs are kebab/lowercase ("ammeonon",
            # "dhor-kuldor"), but character records store the display name
            # ("Ammeonon"). Match case-insensitively so both shapes resolve.
            query["nation"] = {"$regex": f"^{nation.strip()}$", "$options": "i"}
        if q and q.strip():
            # case-insensitive name substring
            query["name"] = {"$regex": q.strip(), "$options": "i"}
        cursor = db.npcs.find(
            query,
            {"_id": 0, "id": 1, "name": 1, "race": 1, "role": 1,
             "location": 1, "nation": 1, "craft": 1},
        ).limit(max(1, min(50, limit)))
        return await cursor.to_list(limit)

    @api_router.post("/apprenticeships")
    async def start_apprenticeship(
        payload: ApprenticeshipStart,
        current_user: User = Depends(get_current_user),
    ):
        if payload.craft not in CRAFTS:
            raise HTTPException(status_code=400, detail=f"Invalid craft. Choose one of {CRAFTS}")
        char = await resolve_character_for_user(payload.character_id, current_user)
        mentor = await db.npcs.find_one({"id": payload.mentor_npc_id}, {"_id": 0})
        if not mentor:
            raise HTTPException(status_code=404, detail="Mentor NPC not found")

        # One active apprenticeship per (character, craft).
        existing = await db.apprenticeships.find_one({
            "character_id": payload.character_id,
            "craft": payload.craft,
            "status": "active",
        })
        if existing:
            raise HTTPException(status_code=400, detail="You already have an active apprenticeship in this craft.")

        doc = {
            "id": str(uuid.uuid4()),
            "character_id": char["id"],
            "character_name": char.get("name", "Unknown"),
            "user_id": current_user.id,
            "mentor_npc_id": mentor["id"],
            "mentor_npc_name": mentor.get("name", "Unknown"),
            "craft": payload.craft,
            "rank": "initiate",
            "started_at": _now_iso(),
            "status": "active",
            "milestones": [{
                "id": str(uuid.uuid4()),
                "text": payload.intro_text or f"Apprenticed under {mentor.get('name','the master')}.",
                "recorded_at": _now_iso(),
                "rank_at_time": "initiate",
            }],
        }
        await db.apprenticeships.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def _resolve_apprenticeship(app_id: str, user: User) -> Dict:
        app = await db.apprenticeships.find_one({"id": app_id}, {"_id": 0})
        if not app:
            raise HTTPException(status_code=404, detail="Apprenticeship not found")
        if app.get("user_id") != user.id and user.role not in ("admin", "moderator"):
            raise HTTPException(status_code=403, detail="That apprenticeship is not yours")
        return app

    @api_router.get("/characters/{character_id}/apprenticeships")
    async def list_character_apprenticeships(character_id: str):
        """Public — apprenticeships are publicly known."""
        cursor = db.apprenticeships.find(
            {"character_id": character_id},
            {"_id": 0},
        ).sort("started_at", -1)
        return await cursor.to_list(50)

    @api_router.post("/apprenticeships/{app_id}/milestone")
    async def record_milestone(
        app_id: str,
        payload: MilestoneRecord,
        current_user: User = Depends(get_current_user),
    ):
        app = await _resolve_apprenticeship(app_id, current_user)
        if app.get("status") != "active":
            raise HTTPException(status_code=400, detail="This apprenticeship has ended.")
        milestone = {
            "id": str(uuid.uuid4()),
            "text": payload.text,
            "recorded_at": _now_iso(),
            "rank_at_time": app.get("rank", "initiate"),
        }
        await db.apprenticeships.update_one(
            {"id": app_id},
            {"$push": {"milestones": milestone}},
        )
        return milestone

    @api_router.post("/apprenticeships/{app_id}/promote")
    async def bump_rank(
        app_id: str,
        payload: RankBump,
        current_user: User = Depends(get_current_user),
    ):
        """Advance the apprentice's rank. Must be a valid rank, and only
        in one direction (initiate → journeyman → master)."""
        if payload.rank not in RANKS:
            raise HTTPException(status_code=400, detail=f"Invalid rank. Choose one of {RANKS}")
        app = await _resolve_apprenticeship(app_id, current_user)
        if app.get("status") != "active":
            raise HTTPException(status_code=400, detail="This apprenticeship has ended.")
        cur_idx = RANKS.index(app.get("rank", "initiate"))
        new_idx = RANKS.index(payload.rank)
        if new_idx <= cur_idx:
            raise HTTPException(status_code=400, detail="Rank can only be advanced.")
        await db.apprenticeships.update_one(
            {"id": app_id},
            {"$set": {"rank": payload.rank, f"promoted_to_{payload.rank}_at": _now_iso()}},
        )
        return {"ok": True, "rank": payload.rank}

    @api_router.post("/apprenticeships/{app_id}/graduate")
    async def graduate(
        app_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Mark an apprenticeship as completed (graduation as master). The
        apprentice must already be at master rank."""
        app = await _resolve_apprenticeship(app_id, current_user)
        if app.get("rank") != "master":
            raise HTTPException(status_code=400, detail="You must reach master rank before graduating.")
        if app.get("status") != "active":
            raise HTTPException(status_code=400, detail="Already graduated.")
        now = _now_iso()
        await db.apprenticeships.update_one(
            {"id": app_id},
            {"$set": {"status": "graduated", "graduated_at": now}},
        )
        return {"ok": True, "graduated_at": now}

    @api_router.post("/apprenticeships/{app_id}/abandon")
    async def abandon(
        app_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Walk away from an apprenticeship. Permanent — but a new one in the
        same craft may be started later."""
        app = await _resolve_apprenticeship(app_id, current_user)
        if app.get("status") != "active":
            raise HTTPException(status_code=400, detail="Not active.")
        await db.apprenticeships.update_one(
            {"id": app_id},
            {"$set": {"status": "abandoned", "abandoned_at": _now_iso()}},
        )
        return {"ok": True}
