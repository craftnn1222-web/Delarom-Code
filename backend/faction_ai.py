"""AI helper for Faction Quests (Round 3).

Generates short, lore-flavoured quest objectives keyed to a faction's
character (motto, home nation, current rival, etc.). Uses the existing
Emergent LLM key + the cheap gpt-4o-mini model used elsewhere for
non-critical narrative beats. Resilient — any error returns a hand-rolled
fallback so the quest still gets created.
"""
import json
import logging
import os
import re
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# Hand-rolled fallback templates — used when the LLM is unreachable
# (budget cap, network error, malformed JSON). Five lore-tinted seeds keyed
# by faction icon so the result still feels appropriate.
FALLBACK_TEMPLATES = {
    "swords":  ("Patrol the marches",
                "Walk the rough country at the edge of our influence. Report back what banners you saw, "
                "and turn aside any who would raid our holdings."),
    "skull":   ("Settle an old debt",
                "There is a name on our list that has not yet bled. Take a quiet token of proof — a ring, "
                "a sealed page — and return it to us. Ask no questions of the where or how."),
    "tree":    ("Tend the wounded grove",
                "The old wood has been bitten by axe and ill weather. Walk three days into it, mend what "
                "you can, and bring back a single living seed."),
    "hammer":  ("Forge-mark a worthy blade",
                "A blade has been laid aside half-finished. Carry it to a Master of our guild, see it "
                "tempered and rune-struck, and bear it back to our coffer with the seal intact."),
    "crown":   ("Carry the King's silence",
                "A sealed missive must reach a quiet ear at a quieter table. Lose it and you lose more. "
                "Travel alone and return with the receiver's mark."),
    "scroll":  ("Recover a lost name",
                "There is a name our Vault no longer remembers. Walk to where it was last spoken — a "
                "ruin, a graveyard, an old library — and write it back into the rolls."),
}


def _api_key() -> Optional[str]:
    return os.environ.get("EMERGENT_LLM_KEY")


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


def _fallback(faction: dict) -> dict:
    template = FALLBACK_TEMPLATES.get(faction.get("icon", "swords"), FALLBACK_TEMPLATES["swords"])
    return {
        "title": f"{template[0]} for {faction.get('name', 'the Faction')}",
        "objective": template[1],
        "flavour": faction.get("motto") or "Bring what is asked, and ask not what is given.",
    }


async def generate_faction_quest(
    faction: dict,
    *,
    rival_name: Optional[str] = None,
) -> dict:
    """Return `{title, objective, flavour}` for a new faction quest.

    Args:
        faction: full faction doc (needs name, motto, description, nation_home, icon).
        rival_name: optional name of a currently-rival faction — included so the
            AI can flavour the quest toward that rivalry when appropriate.
    """
    api_key = _api_key()
    if not api_key:
        return _fallback(faction)

    rival_clause = (
        f"\nA bitter rivalry currently burns between us and {rival_name}. "
        "If it fits naturally, you MAY orient this quest against them — but "
        "never command an outright assassination; we are not common butchers."
        if rival_name else ""
    )

    system_message = (
        "You are the Quest Captain for an in-world faction in the dark-fantasy realm of "
        "Continents of Delarom. You produce short, lore-flavoured quests for members of "
        "the faction. Write in third-person commission style, never as the player. "
        "Output VALID JSON ONLY, with no commentary outside the JSON."
    )

    prompt = f"""
Issue ONE quest for the faction below. Stay in lore. Keep the objective concrete
enough that a roleplayer can write it (travel, recover, deliver, witness, etc.).
Avoid OOC language, modern idioms, and explicit kill orders.

FACTION
- Name: {faction.get('name', 'Unknown')}
- Motto: {faction.get('motto') or '—'}
- Home: {faction.get('nation_home') or 'unaligned'}
- Charter: {(faction.get('description') or '')[:600]}
{rival_clause}

Return JSON in this exact shape:
{{
  "title": "A short, evocative quest name (max 80 chars)",
  "objective": "What the member must do, in 2-3 sentences (max 600 chars)",
  "flavour": "An in-character single line the faction officer says when issuing the quest (max 200 chars)"
}}
"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"faction_quest_{faction.get('slug', 'x')}",
            system_message=system_message,
        ).with_model("openai", "gpt-4o-mini")

        response = await chat.send_message(UserMessage(text=prompt))
        parsed = _safe_parse_json(response)
        if not parsed:
            logger.warning("Faction quest LLM returned unparseable response.")
            return _fallback(faction)

        return {
            "title":     (parsed.get("title") or "Untitled Commission")[:80],
            "objective": (parsed.get("objective") or "")[:600] or _fallback(faction)["objective"],
            "flavour":   (parsed.get("flavour") or faction.get("motto") or "")[:200],
        }
    except Exception as e:
        logger.warning("Faction quest AI generation failed: %s", e)
        return _fallback(faction)
