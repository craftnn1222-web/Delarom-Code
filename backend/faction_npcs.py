"""Living NPC roster for player-founded factions.

When a new faction is approved, this module:
  1. Seeds 3 founding NPC members with rolled names, bios, ranks (1 officer + 2 members).
  2. Periodically lets NPC members 'live' in the faction by:
     - Occasionally replying to faction threads (in-character, AI-flavoured)
     - Occasionally completing open faction quests (paying gold into the
       treasury and raising reputation in the home nation)
     - Slow trickle of new NPC members based on faction activity

All AI calls are best-effort with hand-rolled fallbacks — the faction never
breaks if the Emergent LLM key is unreachable.

This module is INTENTIONALLY not wired to a real cron. The "tick" function
is called lazily from a `/admin/factions/{slug}/tick` endpoint (admin-only)
plus a couple of opportunistic spots (every time the faction page loads,
we trigger a tick at most once per 6 hours per faction).
"""
import asyncio
import json
import logging
import os
import random
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------- name/personality fallbacks ----------------------
# Used when the LLM is unreachable. Names are short, low-Tolkien-ratio
# generics; the world feels more alive with even rolled names than with none.

FALLBACK_GIVEN = [
    "Arven", "Borin", "Calla", "Daros", "Elia", "Faren", "Goran", "Halia",
    "Iven", "Joras", "Kaela", "Larn", "Mira", "Norik", "Orla", "Perrin",
    "Quen", "Rolen", "Sora", "Tarn", "Una", "Vesh", "Wynn", "Xara", "Yorek",
    "Zin",
]
FALLBACK_SURNAMES = [
    "Ashford", "Blackbarrow", "Coldwater", "Drennan", "Embermark", "Farholt",
    "Greycloak", "Holm", "Ironbough", "Karth", "Lowfen", "Marrow", "Nethric",
    "Ostfir", "Penn", "Quarrenne", "Rookwood", "Silverstrand", "Thorne",
    "Underhill", "Velbrak", "Whetstone", "Yarrow", "Zorenne",
]
FALLBACK_OCCUPATIONS = [
    "an old quartermaster", "a tireless scribe", "a wandering scout",
    "a hedge-knight returned", "a young hopeful with a borrowed blade",
    "a stonemason turned spear-hand", "a midwife with a sharp tongue",
    "a former smuggler seeking respectability", "a quiet huntsman",
    "a tavern-singer with a knack for trouble", "a priest fallen from grace",
]


def _api_key() -> Optional[str]:
    return os.environ.get("EMERGENT_LLM_KEY")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_parse_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
    return None


def _fallback_npc(rank: str) -> dict:
    given = random.choice(FALLBACK_GIVEN)
    surname = random.choice(FALLBACK_SURNAMES)
    occ = random.choice(FALLBACK_OCCUPATIONS)
    return {
        "name": f"{given} {surname}",
        "title": "Officer" if rank == "officer" else "Sworn",
        "bio": f"{given} is {occ}; took the oath in their thirty-first winter.",
        "personality": random.choice([
            "stoic and methodical", "wry, hot-tempered", "quiet, watchful",
            "loyal to a fault", "ambitious and cold", "warm and earnest",
        ]),
        "rank": rank,
    }


async def _generate_npc(faction: dict, *, rank: str = "member") -> dict:
    """Roll a single NPC for the given faction. Falls back to template if AI unavailable."""
    api_key = _api_key()
    if not api_key:
        return _fallback_npc(rank)
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system = (
            "You roll one in-world NPC for a player-founded faction in a "
            "dark-fantasy realm. Output VALID JSON ONLY. No commentary."
        )
        prompt = f"""
Create ONE original NPC member for this faction:

FACTION
- Name: {faction.get('name','Unknown')}
- Motto: {faction.get('motto') or '—'}
- Home: {faction.get('nation_home') or 'unaligned'}
- Charter: {(faction.get('description') or '')[:400]}

The NPC's rank in the faction will be '{rank}'. Keep names short, evocative, NOT generic-fantasy ("Arven Ashford" good, "Sir Reginald Magnificus" bad). The NPC should plausibly belong to this faction's home nation, but feel free to invent occasional outsiders.

Return JSON in this exact shape:
{{
  "name": "Given Surname (max 40 chars)",
  "title": "Their honorific or role within the faction (max 40 chars). Examples: Sworn, Officer, Quartermaster, Scribe.",
  "bio": "One sentence describing what they did before joining (max 240 chars). No dates, no modern idioms.",
  "personality": "Two or three lower-case adjectives separated by commas (max 80 chars)"
}}
"""
        chat = LlmChat(
            api_key=api_key,
            session_id=f"npc_{faction.get('slug','x')}_{uuid.uuid4().hex[:6]}",
            system_message=system,
        ).with_model("openai", "gpt-4o-mini")
        resp = await chat.send_message(UserMessage(text=prompt))
        parsed = _safe_parse_json(resp)
        if not parsed:
            return _fallback_npc(rank)
        return {
            "name":        (parsed.get("name") or "")[:40] or _fallback_npc(rank)["name"],
            "title":       (parsed.get("title") or "Sworn")[:40],
            "bio":         (parsed.get("bio") or "")[:240] or _fallback_npc(rank)["bio"],
            "personality": (parsed.get("personality") or "")[:80] or _fallback_npc(rank)["personality"],
            "rank":        rank,
        }
    except Exception as e:
        logger.warning("NPC generation fell back: %s", e)
        return _fallback_npc(rank)


# ---------------------- seeding + lifecycle ----------------------

async def _build_and_insert_npc(db, *, faction: dict, rank: str, source: str) -> Optional[dict]:
    """One-shot: roll an NPC for `faction` at `rank` and insert it. Returns
    the inserted doc or None on failure. `source` is stamped on the doc so
    later tooling can tell founding/starter/recruitment NPCs apart.
    """
    try:
        base = await _generate_npc(faction, rank=rank)
        doc = {
            "id": str(uuid.uuid4()),
            "faction_id": faction["id"],
            "faction_slug": faction["slug"],
            "name": base["name"],
            "title": base["title"],
            "bio": base["bio"],
            "personality": base["personality"],
            "rank": base["rank"],
            "is_active": True,
            "joined_at": _now_iso(),
            "left_at": None,
            "source": source,
        }
        await db.faction_npcs.insert_one(dict(doc))
        return doc
    except Exception as e:
        logger.warning("npc insert (%s) skipped: %s", source, e)
        return None


async def seed_founding_npcs(db, *, faction: dict, count: int = 3) -> list[dict]:
    """Seed N founding NPCs into a fresh player-founded faction.
    1 officer + (N-1) members. Best-effort: any per-NPC failure is skipped.
    """
    if count < 1:
        return []
    ranks = ["officer"] + ["member"] * (count - 1)
    created = []
    for rank in ranks:
        doc = await _build_and_insert_npc(db, faction=faction, rank=rank, source="founding")
        if doc:
            created.append(doc)
    return created


async def seed_starter_npcs(db, *, faction: dict, count: int = 6) -> list[dict]:
    """Seed NPCs into a STARTER faction (the 6 canonical realm factions).
    Starter factions are old, established institutions, so they get a richer
    initial roster than player-founded ones: 2 officers + (N-2) members.

    Idempotent — if the faction already has any NPCs with source='starter',
    nothing happens. This makes it safe to call from the admin seed endpoint
    however many times.
    """
    if count < 2:
        return []
    existing = await db.faction_npcs.count_documents(
        {"faction_id": faction["id"], "source": "starter"},
    )
    if existing > 0:
        return []
    ranks = ["officer", "officer"] + ["member"] * (count - 2)
    created = []
    for rank in ranks:
        doc = await _build_and_insert_npc(db, faction=faction, rank=rank, source="starter")
        if doc:
            created.append(doc)
    return created



async def _maybe_post_in_thread(db, *, faction: dict, npc: dict) -> Optional[dict]:
    """Roll a chance for an NPC to leave a short reply in the faction's most
    recent thread. Best-effort: returns the reply doc on success, else None."""
    thread = await db.faction_threads.find_one(
        {"faction_id": faction["id"]},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not thread:
        return None
    # Don't double-reply within 24h.
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent = await db.faction_thread_replies.find_one(
        {"thread_id": thread["id"], "npc_id": npc["id"], "created_at": {"$gte": cutoff}},
        {"_id": 0, "id": 1},
    )
    if recent:
        return None

    api_key = _api_key()
    content = None
    if api_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            prompt = f"""
You write ONE short, in-character forum reply (1-3 sentences, max 280 chars) as the NPC below, addressing the most recent thread in their faction.

NPC: {npc['name']} — {npc['title']} of {faction['name']}
NPC personality: {npc.get('personality','')}
Faction motto: {faction.get('motto','')}

THREAD TITLE: {thread.get('title','')}
THREAD CONTENT: {(thread.get('content','') or '')[:600]}

Reply in third-person OR first-person as the NPC. No OOC text, no modern idioms.
Return ONLY the reply text — no JSON, no quotes, no commentary.
"""
            chat = LlmChat(
                api_key=api_key,
                session_id=f"npc_reply_{npc['id']}",
                system_message="You are a quiet, in-world NPC writing on a faction's private notice board.",
            ).with_model("openai", "gpt-4o-mini")
            resp = await chat.send_message(UserMessage(text=prompt))
            if resp and len(resp.strip()) > 0:
                content = resp.strip().strip('"')[:600]
        except Exception as e:
            logger.warning("npc thread reply LLM failed: %s", e)

    if not content:
        content = random.choice([
            "Aye, I read it. Mark me down as in agreement.",
            "I'll speak with the quartermaster on this come dawn.",
            "Strange days. I will keep my watch sharper than before.",
            "If it falls to my company, we'll see it done.",
            "A thought, said quietly: we are stretched thin already.",
        ])

    reply = {
        "id": str(uuid.uuid4()),
        "thread_id": thread["id"],
        "faction_id": faction["id"],
        "character_id": None,
        "character_name": npc["name"],
        "user_id": None,
        "npc_id": npc["id"],
        "npc_title": npc["title"],
        "content": content,
        "is_npc": True,
        "created_at": _now_iso(),
    }
    await db.faction_thread_replies.insert_one(dict(reply))
    await db.faction_threads.update_one(
        {"id": thread["id"]},
        {"$set": {"last_reply_at": _now_iso()},
         "$inc": {"replies_count": 1}},
    )
    return reply


async def _maybe_complete_quest(db, *, faction: dict, npc: dict) -> Optional[dict]:
    """Roll a chance for an NPC to complete an open faction quest. The reward
    goes into the faction TREASURY (not a user wallet) so the player who
    founded the faction sees their coffer grow over time.
    """
    quest = await db.faction_quests.find_one(
        {"faction_id": faction["id"], "is_active": True,
         "$expr": {"$lt": ["$completion_count", "$max_completions"]}},
        {"_id": 0},
        sort=[("created_at", 1)],  # oldest open first
    )
    if not quest:
        return None
    already = await db.faction_quest_completions.find_one(
        {"quest_id": quest["id"], "npc_id": npc["id"]}, {"_id": 0, "id": 1},
    )
    if already:
        return None

    completion = {
        "id": str(uuid.uuid4()),
        "quest_id": quest["id"],
        "faction_id": faction["id"],
        "character_id": None,
        "character_name": npc["name"],
        "user_id": None,
        "npc_id": npc["id"],
        "proof": f"Reported by {npc['name']}, {npc['title']}, by my own hand.",
        "gold_paid": quest["reward_gold"],
        "reputation_paid": quest["reward_reputation"],
        "is_npc_completion": True,
        "completed_at": _now_iso(),
    }
    await db.faction_quest_completions.insert_one(dict(completion))

    new_count = quest["completion_count"] + 1
    updates = {"$inc": {"completion_count": 1}}
    if new_count >= quest["max_completions"]:
        updates["$set"] = {"is_active": False, "closed_at": _now_iso()}
    await db.faction_quests.update_one({"id": quest["id"]}, updates)

    # Gold goes to the treasury, not to any user.
    if quest["reward_gold"] > 0:
        await db.faction_treasury.update_one(
            {"faction_id": faction["id"]},
            {"$inc": {"balance": quest["reward_gold"], "total_donated": quest["reward_gold"]},
             "$set":  {"updated_at": _now_iso()}},
            upsert=True,
        )
        await db.faction_treasury_log.insert_one({
            "id": str(uuid.uuid4()),
            "faction_id": faction["id"],
            "kind": "npc_quest",
            "character_id": None,
            "character_name": npc["name"],
            "npc_id": npc["id"],
            "amount": quest["reward_gold"],
            "quest_id": quest["id"],
            "created_at": _now_iso(),
        })
    return completion


async def _maybe_recruit(db, *, faction: dict) -> Optional[dict]:
    """Chance to add one more NPC member if the faction has been active.
    Active = at least 1 forum thread or 1 quest in the last 14 days.
    Caps at 12 NPCs per faction to prevent runaway growth.
    """
    npc_count = await db.faction_npcs.count_documents({"faction_id": faction["id"], "is_active": True})
    if npc_count >= 12:
        return None
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    has_recent = await db.faction_threads.find_one(
        {"faction_id": faction["id"], "created_at": {"$gte": cutoff}}, {"_id": 0, "id": 1},
    ) or await db.faction_quests.find_one(
        {"faction_id": faction["id"], "created_at": {"$gte": cutoff}}, {"_id": 0, "id": 1},
    )
    if not has_recent:
        return None
    base = await _generate_npc(faction, rank="member")
    doc = {
        "id": str(uuid.uuid4()),
        "faction_id": faction["id"],
        "faction_slug": faction["slug"],
        "name": base["name"],
        "title": base["title"],
        "bio": base["bio"],
        "personality": base["personality"],
        "rank": base["rank"],
        "is_active": True,
        "joined_at": _now_iso(),
        "left_at": None,
        "source": "recruitment",
    }
    await db.faction_npcs.insert_one(dict(doc))
    return doc


async def tick_faction(db, *, faction: dict) -> dict:
    """One "world tick" for a faction. Idempotent enough — each individual
    action self-throttles. Returns a small summary of what happened so the
    admin endpoint can show feedback.
    """
    summary = {
        "thread_replies": 0,
        "quest_completions": 0,
        "recruited": 0,
        "errors": 0,
    }
    npcs = await db.faction_npcs.find(
        {"faction_id": faction["id"], "is_active": True}, {"_id": 0},
    ).to_list(length=None)

    # Probability tuning: each NPC has small chance per tick.
    for npc in npcs:
        # Thread reply: ~30%
        if random.random() < 0.30:
            try:
                if await _maybe_post_in_thread(db, faction=faction, npc=npc):
                    summary["thread_replies"] += 1
            except Exception as e:
                logger.warning("npc thread reply error: %s", e)
                summary["errors"] += 1

        # Quest completion: ~15%
        if random.random() < 0.15:
            try:
                if await _maybe_complete_quest(db, faction=faction, npc=npc):
                    summary["quest_completions"] += 1
            except Exception as e:
                logger.warning("npc quest completion error: %s", e)
                summary["errors"] += 1

    # Recruitment: ~25% per tick when faction is active.
    if random.random() < 0.25:
        try:
            new = await _maybe_recruit(db, faction=faction)
            if new:
                summary["recruited"] += 1
        except Exception as e:
            logger.warning("npc recruitment error: %s", e)
            summary["errors"] += 1

    # Stamp the last tick on the faction so the lazy-trigger path can
    # throttle calls to once every 6 hours.
    await db.factions.update_one(
        {"id": faction["id"]},
        {"$set": {"npc_tick_at": _now_iso()}},
    )
    return summary
