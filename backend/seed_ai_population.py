"""AI population for the Continents of Delarom — notable & common NPCs per city.

Companion to `seed_royals_and_nobles.py` (which hand-authors the headline
NPCs). This module bulk-generates the populace of empty/sparse cities by
prompting gpt-4o-mini with the city's name + nation + region + description
and asking for 4 commoners + 2 notables in a strict JSON shape. Each result
is tagged `created_by: "seed:ai_population"` so admins can filter and refine.

Resilient: every error returns a small hand-rolled fallback so a city that
fails AI gen still gets two placeholder NPCs and can be retried.
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# How many NPCs to ask for per city, per importance tier.
PER_CITY_COMMON = 4
PER_CITY_NOTABLE = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_key() -> Optional[str]:
    return os.environ.get("EMERGENT_LLM_KEY")


def _safe_parse_json_array(text: str) -> Optional[list]:
    """Parse a JSON array from a model response, tolerating a code-fence
    wrapper or trailing commentary. Returns None if no array can be salvaged.
    """
    if not text:
        return None
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, list) else None
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            loaded = json.loads(m.group(0))
            return loaded if isinstance(loaded, list) else None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def _fallback_pair(city: dict) -> list:
    """Two-NPC fallback used when AI fails. Always inserts SOMETHING so the
    city is no longer 'empty'; admin can regenerate later."""
    nation = city.get("nation", "the realm")
    name = city.get("name") or "this city"
    return [
        {
            "name": f"Old Maren of {name}",
            "race": "Human",
            "role": "Tavern-keep",
            "personality": "Slow-spoken, watchful, remembers every face that ever drank under their roof.",
            "motivation": "Keep the tavern alive through another lean season.",
            "quirks": "Will not pour the first drink of the night until the candle is lit.",
            "importance": "common",
        },
        {
            "name": f"Captain Veska of the {name} Watch",
            "race": "Human",
            "role": f"Captain of the {name} City Watch",
            "personality": "Brisk, fair, has a long memory for grudges and a longer one for favours.",
            "motivation": f"Keep {name} free of the rot that has bled the rest of {nation}.",
            "quirks": "Patrols personally on the night of every new moon.",
            "importance": "notable",
        },
    ]


async def generate_population_for_city(city: dict) -> list:
    """Return a list of 4 common + 2 notable NPC dicts for the given city.

    Each dict is ready to be merged into the base NPC document by the caller
    (which will fill in id, nation, location, timestamps, etc.).
    """
    api_key = _api_key()
    if not api_key:
        return _fallback_pair(city)

    system_message = (
        "You are the World-Loom for the dark-fantasy realm of Continents of Delarom. "
        "You generate small rosters of residents for a city. Stay in lore. "
        "Output VALID JSON ONLY — a single array. No commentary outside the array."
    )

    prompt = f"""
Generate the populace of the city below: {PER_CITY_COMMON} commoners and {PER_CITY_NOTABLE} notables.

CITY
- Name: {city.get('name')}
- Nation: {city.get('nation')}
- Region: {city.get('region') or '—'}
- Description: {(city.get('description') or '')[:400]}

GUIDANCE
- Commoners are working folk: smiths, fishers, scribes, beggars, soldiers, midwives, etc.
- Notables are recognised locals: respected priests, guildwrights, captains, merchants, scholars.
- Names should fit the nation's tone (e.g. Ammeonon: human + half-elf; Selindori: sun-elf; Dhor-Kuldor: dwarf; Aigraels: high-elf + tiefling; Veiled Realms: high-elf, sea-elf, half-elf).
- Each NPC's "quirks" is ONE short sentence — a single concrete behaviour, not a list.
- Avoid OOC language, modern idioms, generic fantasy clichés.

Return JSON in this exact shape — a single array of {PER_CITY_COMMON + PER_CITY_NOTABLE} objects:
[
  {{
    "name": "Given Surname (or epithet)",
    "race": "Human / Sun-Elf / Dwarf / Half-Elf / etc.",
    "role": "Their trade or office, max 60 chars",
    "personality": "Two short clauses, max 140 chars",
    "motivation": "What they want, in 1 sentence, max 160 chars",
    "quirks": "A single concrete behaviour, max 140 chars",
    "importance": "common"
  }}
  // ... {PER_CITY_NOTABLE} of these should have "importance": "notable" instead
]
"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"populate_city_{city.get('slug', 'x')}",
            system_message=system_message,
        ).with_model("openai", "gpt-4o-mini")

        response = await chat.send_message(UserMessage(text=prompt))
        parsed = _safe_parse_json_array(response)
        if not parsed:
            logger.warning("City population LLM returned unparseable response for %s.", city.get("slug"))
            return _fallback_pair(city)

        # Light schema fixup so anything missing falls into safe defaults.
        cleaned = []
        for entry in parsed[: PER_CITY_COMMON + PER_CITY_NOTABLE]:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            importance = entry.get("importance", "common")
            if importance not in ("common", "notable"):
                importance = "common"
            cleaned.append({
                "name": str(entry.get("name"))[:120],
                "race": str(entry.get("race") or "Human")[:40],
                "role": str(entry.get("role") or "Citizen")[:80],
                "personality": str(entry.get("personality") or "")[:200],
                "motivation": str(entry.get("motivation") or "")[:200],
                "quirks": str(entry.get("quirks") or "")[:200],
                "importance": importance,
            })

        if not cleaned:
            return _fallback_pair(city)
        return cleaned
    except Exception as e:
        logger.warning("City population AI generation failed for %s: %s", city.get("slug"), e)
        return _fallback_pair(city)


async def populate_cities(db, max_cities: int = 5) -> dict:
    """Top up the `max_cities` cities currently most starved of residents.

    Skips any city that already has ≥ 4 NPCs (with importance `common` or
    `notable`). Inserts the AI-generated roster tagged with
    `created_by: "seed:ai_population"`. Idempotent in the sense that a city
    is only topped up if still short.

    Returns `{processed, inserted, cities: [{slug, name, inserted}]}`.
    """
    cursor = db.cities.find({}, {"_id": 0, "slug": 1, "name": 1, "nation": 1, "region": 1, "description": 1})
    all_cities = await cursor.to_list(2000)
    # Empty/sparse first: cities with fewest existing residents.
    counts = []
    for c in all_cities:
        cnt = await db.npcs.count_documents({
            "nation": c["nation"],
            "location": c["name"],
            "importance": {"$in": ["common", "notable"]},
        })
        counts.append((cnt, c))
    counts.sort(key=lambda x: x[0])
    target_cities = [c for cnt, c in counts if cnt < 4][:max_cities]

    inserted_total = 0
    per_city = []
    for city in target_cities:
        roster = await generate_population_for_city(city)
        ins_for_city = 0
        for entry in roster:
            # Idempotency: skip duplicate name+nation+location triples.
            existing = await db.npcs.find_one({
                "name": entry["name"],
                "nation": city["nation"],
                "location": city["name"],
            }, {"_id": 0})
            if existing:
                continue
            npc = {
                "id": str(uuid.uuid4()),
                "name": entry["name"],
                "race": entry["race"],
                "role": entry["role"],
                "nation": city["nation"],
                "location": city["name"],
                "appearance": "",
                "personality": entry["personality"],
                "motivation": entry["motivation"],
                "background": "",
                "quirks": entry["quirks"],
                "importance": entry["importance"],
                "overall_mood": "neutral",
                "mood_score": 0,
                "status": "alive",
                "status_note": "",
                "companion_of": None,
                "created_by_character_id": None,
                "is_admin_seeded": True,
                "created_by": "seed:ai_population",
                "created_at": _now_iso(),
                "last_seen_at": _now_iso(),
            }
            await db.npcs.insert_one(npc)
            ins_for_city += 1
        inserted_total += ins_for_city
        per_city.append({"slug": city.get("slug"), "name": city.get("name"), "inserted": ins_for_city})

    return {
        "processed": len(target_cities),
        "inserted": inserted_total,
        "cities": per_city,
    }
