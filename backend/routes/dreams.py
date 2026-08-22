"""
Dreams & Visions (Phase 4, 2026-05-30).

Once per UTC day per character, a player may "sleep" and have a short
AI-generated dream drawn from the character's recent NPC memories,
family lineage, active festivals, recent chronicle events, and personal
backstory. Dreams are stored permanently and viewable by the player.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def _gather_dream_seeds(db, character: Dict) -> Dict:
    """Pull a small bouquet of contextual material to feed the dream LLM."""
    char_id = character.get("id")
    seeds: Dict = {
        "name": character.get("name", "Unknown"),
        "race": character.get("race", ""),
        "character_class": character.get("character_class", ""),
        "nation": character.get("nation", ""),
        "backstory_excerpt": (character.get("backstory") or "")[:500],
        "relatives": (character.get("relatives") or [])[:5],
    }

    # Recent NPC interactions (memories)
    try:
        memories = await db.npc_memories.find(
            {"character_id": char_id},
            {"_id": 0, "summary": 1, "npc_name": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(5)
        seeds["recent_memories"] = memories
    except Exception:
        seeds["recent_memories"] = []

    # Recent world events involving this character
    try:
        events = await db.world_events.find(
            {"involved_characters": char_id},
            {"_id": 0, "summary": 1, "event_type": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(3)
        seeds["recent_events"] = events
    except Exception:
        seeds["recent_events"] = []

    return seeds


async def _generate_dream(seeds: Dict) -> Dict:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Dreams are out of reach tonight.")

    system = (
        "You are a dreamweaver of Delarom, a high-fantasy world. You produce short, "
        "atmospheric, slightly-cryptic dream sequences for sleeping characters. "
        "Style: evocative, symbolic, never literal exposition. 2-3 short paragraphs. "
        "Draw from the material provided but transform it — dreams MIX, DISTORT, and "
        "FRAGMENT memory. Never reveal mechanics or out-of-character info. "
        "Output ONLY the dream prose, followed on a NEW line by 'MOOD: <one word>' "
        "(serene / unsettling / haunting / radiant / sorrowful / mocking / fevered)."
    )
    relatives_lines = "\n".join(
        f"  - {r.get('name','?')} ({r.get('relationship','?')}, {r.get('status','?')}): {(r.get('story') or '')[:120]}"
        for r in seeds.get("relatives", [])
    ) or "  (none declared)"
    memory_lines = "\n".join(
        f"  - With {m.get('npc_name','?')}: {(m.get('summary') or '')[:160]}"
        for m in seeds.get("recent_memories", [])
    ) or "  (none recent)"
    event_lines = "\n".join(
        f"  - {(e.get('summary') or '')[:160]}"
        for e in seeds.get("recent_events", [])
    ) or "  (none recent)"

    prompt = (
        f"Compose a dream sequence for the sleeping character below.\n\n"
        f"CHARACTER: {seeds['name']}, {seeds['race']} {seeds['character_class']} of {seeds['nation']}\n"
        f"BACKSTORY EXCERPT: {seeds['backstory_excerpt']}\n\n"
        f"DECLARED KIN:\n{relatives_lines}\n\n"
        f"RECENT NPC INTERACTIONS:\n{memory_lines}\n\n"
        f"RECENT WORLD EVENTS INVOLVING THEM:\n{event_lines}\n\n"
        "Remember: dreams are SYMBOLIC and FRAGMENTED. Mix the seeds. Add original "
        "imagery — a recurring image, a half-remembered voice, a place that doesn't "
        "exist. Length: 2-3 short paragraphs. End with 'MOOD: <one word>'."
    )

    chat = LlmChat(
        api_key=api_key,
        session_id=f"dream-{uuid.uuid4()}",
        system_message=system,
    ).with_model("openai", "gpt-4o")

    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"The dreamweaver is silent: {e}")

    lines = [ln.rstrip() for ln in raw.strip().splitlines()]
    mood = "unsettling"
    body_lines: List[str] = []
    for line in lines:
        if line.strip().upper().startswith("MOOD:"):
            mood = line.split(":", 1)[1].strip().lower() or mood
        else:
            body_lines.append(line)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    body = "\n".join(body_lines).strip() or raw.strip()
    return {"body": body, "mood": mood}


def attach_dream_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.get("/characters/{character_id}/dreams")
    async def list_dreams(
        character_id: str,
        current_user: User = Depends(get_current_user),
        limit: int = 30,
    ):
        """List dreams in reverse-chronological order. Includes a `can_dream_today` flag."""
        await resolve_character_for_user(character_id, current_user)
        cursor = db.dreams.find({"character_id": character_id}, {"_id": 0}).sort("dreamed_at", -1)
        dreams = await cursor.to_list(min(max(limit, 1), 100))
        last = await db.dreams.find_one(
            {"character_id": character_id},
            {"_id": 0, "dreamed_on": 1},
            sort=[("dreamed_at", -1)],
        )
        can_dream_today = not last or last.get("dreamed_on") != _today_utc()
        return {"dreams": dreams, "can_dream_today": can_dream_today}

    @api_router.post("/characters/{character_id}/dream")
    async def have_a_dream(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Sleep and dream. Allowed once per UTC day per character."""
        char = await resolve_character_for_user(character_id, current_user)
        # Daily rate-limit check
        today = _today_utc()
        existing = await db.dreams.find_one(
            {"character_id": character_id, "dreamed_on": today},
            {"_id": 0, "id": 1},
        )
        if existing:
            raise HTTPException(status_code=429, detail="This character has already dreamed today. Try again at dawn.")

        seeds = await _gather_dream_seeds(db, char)
        generated = await _generate_dream(seeds)

        doc = {
            "id": str(uuid.uuid4()),
            "character_id": character_id,
            "character_name": char.get("name", "Unknown"),
            "user_id": current_user.id,
            "body": generated["body"],
            "mood": generated["mood"],
            "dreamed_at": _now_iso(),
            "dreamed_on": today,
        }
        await db.dreams.insert_one(doc)
        doc.pop("_id", None)
        return doc
