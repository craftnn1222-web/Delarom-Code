"""T1 player-puppeteering guard.

Detects and strips passages where the AI is voicing/acting for the player's
character — a direct violation of the T1 ruleset. Used as a safety net
behind the prompt because gpt-4o occasionally overrides explicit "do not
control the player character" instructions when given a vivid third-person
scene setup.

Detection strategy: locate every sentence that contains the player
character's name AND a self-action verb (speech, motion, emotion,
sensation) where the character is the subject. These are the clear
violations. Edge cases (e.g. "Ausar's blade" referring to the object, not
the actor) are left untouched.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Sentence-level verbs that, when applied to the player character as subject,
# clearly violate T1 (the AI is dictating speech, motion, emotion, or sensation
# of someone other than the NPCs / environment).
PUPPETEER_VERBS = [
    # Speech
    "say", "says", "said", "speaks", "spoke", "spoken", "speak",
    "reply", "replies", "replied", "responds", "responded",
    "asks", "asked", "answers", "answered", "tells", "told",
    "whispers", "whispered", "mutters", "muttered",
    "shouts", "shouted", "calls", "called", "calls out", "called out",
    "declares", "declared", "announces", "announced",
    "laughs", "laughed", "chuckles", "chuckled", "smiles", "smiled",
    "grins", "grinned", "frowns", "frowned", "sighs", "sighed",
    "exclaims", "exclaimed", "remarks", "remarked", "states", "stated",
    "yells", "yelled", "screams", "screamed", "growls", "growled",
    "agrees", "agreed", "nods", "nodded",
    # Motion (active movement of the character)
    "steps", "stepped", "walks", "walked", "approaches", "approached",
    "moves", "moved", "turns", "turned", "stands", "stood",
    "sits", "sat", "kneels", "knelt", "rises", "rose",
    "leans", "leaned", "draws", "drew", "reaches", "reached",
    "pulls", "pulled", "pushes", "pushed", "grabs", "grabbed",
    "shakes", "shook", "gestures", "gestured",
    "raises", "raised", "lowers", "lowered", "pauses", "paused",
    "bounds", "bounded", "bound",
    "dashes", "dashed", "darts", "darted",
    "runs", "ran", "rushes", "rushed",
    "leaps", "leaped", "leapt", "jumps", "jumped",
    "strides", "strode", "marches", "marched",
    "saunters", "sauntered", "ambles", "ambled",
    "hurries", "hurried", "creeps", "crept", "sneaks", "sneaked", "snuck",
    "enters", "entered", "exits", "exited", "leaves", "left", "arrives", "arrived",
    "departs", "departed", "returns", "returned",
    "follows", "followed", "approaches", "approached",
    "hugs", "hugged", "embraces", "embraced", "kisses", "kissed",
    "bows", "bowed", "curtsies", "curtsied",
    "swings", "swung", "throws", "threw", "tosses", "tossed",
    "fires", "fired", "strikes", "struck", "hits", "hit",
    "kicks", "kicked", "punches", "punched",
    "casts", "cast", "summons", "summoned",
    "lifts", "lifted", "drops", "dropped", "places", "placed",
    "opens", "opened", "closes", "closed",
    "looks", "looked", "stares", "stared", "glances", "glanced", "peers", "peered",
    # Emotion / sensation / thought
    "feels", "felt", "thinks", "thought", "wonders", "wondered",
    "decides", "decided", "remembers", "remembered",
    "knows", "knew", "realizes", "realized", "notices", "noticed",
    "sees", "saw", "hears", "heard", "smells", "smelled",
    "tastes", "tasted", "senses", "sensed",
    "considers", "considered", "ponders", "pondered",
    "is", "was", "seems", "seemed", "appears", "appeared",
    "feels", "felt", "becomes", "became",
    # Possession patterns where the AI dictates body-language
    "his gaze", "her gaze", "their gaze",
    "his voice", "her voice", "their voice",
    "his eyes", "her eyes", "their eyes",
    "his face", "her face", "their face",
    "his hand", "her hand", "their hand",
    "his hands", "her hands", "their hands",
    "his expression", "her expression", "their expression",
]


def _build_violation_regex(character_names) -> re.Pattern:
    """Compile a case-insensitive regex that catches `<name> <verb>...` and
    `<name>'s <body-part>...` constructs for any of the protected character
    names. Accepts either a single name string or a list of names — multi-
    name mode is critical for multi-player scenes where the AI is responding
    to player B's action but must not puppeteer player A's character either.
    """
    # Normalise input to a list of stripped non-empty names.
    if isinstance(character_names, str):
        names = [character_names]
    else:
        names = list(character_names or [])
    names = [n.strip() for n in names if n and n.strip()]
    if not names:
        return re.compile(r"(?!x)x")  # match nothing
    # Also detect first-name-only references (people rarely use full names
    # mid-sentence in narrative). e.g. given "Ausar Veltraus" also match "Ausar".
    expanded: list[str] = []
    for n in names:
        expanded.append(n)
        first = n.split()[0] if n.split() else ""
        if first and first not in expanded:
            expanded.append(first)
    safe_names = "|".join(re.escape(n) for n in expanded)
    verb_alt = "|".join(re.escape(v) for v in PUPPETEER_VERBS)
    # Pattern A: "<Name> <verb>" anywhere in the sentence.
    pattern_a = rf"\b(?:{safe_names})\b[^.!?]{{0,80}}\b(?:{verb_alt})\b"
    # Pattern B: "<Name>'s <body-part-or-trait>" — also a puppeteer move
    # because the AI is dictating internal state by way of body language.
    body_parts = (
        "voice|gaze|eyes|face|hand|hands|expression|features|shoulders|"
        "lips|brow|mouth|chest|heart|mind|thoughts|feet|step|steps|posture|"
        "smile|frown|laugh|laughter|tone|words|reply|response"
    )
    pattern_b = rf"\b(?:{safe_names})'s\s+(?:{body_parts})\b"
    combined = f"(?:{pattern_a})|(?:{pattern_b})"
    return re.compile(combined, re.IGNORECASE)


# Sentence splitter: simple but covers the AI's narrative style (full stops,
# question marks, exclamation marks, and stray double newlines).
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def detect_player_puppeteering(text: str, character_names) -> list[str]:
    """Return a list of sentence(s) in `text` that violate T1 by acting/speaking
    for any of the protected player characters. Pass a single name string or a
    list of names. Empty list means no violation detected.
    """
    if not text or not character_names:
        return []
    rx = _build_violation_regex(character_names)
    flagged: list[str] = []
    for sentence in SENTENCE_SPLIT.split(text):
        s = sentence.strip()
        if not s:
            continue
        if rx.search(s):
            flagged.append(s)
    return flagged


def sanitize_player_puppeteering(text: str, character_names) -> tuple[str, int]:
    """Strip violating sentences from `text`. Returns (cleaned_text, stripped_count).

    `character_names` may be a single string or list. If stripping would leave
    the response too short (< 80 chars), return the original instead — the
    caller can then either retry the LLM with a harsher prompt or surface a
    fallback. Returns -1 as the sentinel in that case.
    """
    if not text or not character_names:
        return text, 0
    rx = _build_violation_regex(character_names)
    kept: list[str] = []
    stripped = 0
    for sentence in SENTENCE_SPLIT.split(text):
        s = sentence.strip()
        if not s:
            continue
        if rx.search(s):
            stripped += 1
            logger.info("T1 puppeteer guard stripped sentence: %r", s[:140])
            continue
        kept.append(s)
    if stripped == 0:
        return text, 0
    cleaned = " ".join(kept).strip()
    if len(cleaned) < 80:
        return text, -1  # sentinel — caller will recognise as "regen required"
    return cleaned, stripped
