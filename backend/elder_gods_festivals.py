"""Elder Gods Festival Calendar.

Each of the Four Elder Gods has a signature festival day (major) tied to
an equinox or solstice, PLUS a weekly minor holy day. When today falls on
a festival:

  • Prayers to that god get an `affinity_boost` bias applied by
    `PrayerService._judge_prayer` — nudges silence → flicker and
    flicker → blessing.
  • The scene state gains an `active_elder_festival` block. NPCs may
    reference the festival in RP scenes (streamers hung, temples open
    late, processions on the road, etc.) via the master prompt.

The calendar is deterministic (fixed dates + weekday); no admin
configuration. `get_active_festival(now)` returns the highest-priority
festival active on `now` (major beats minor), or None.

Real-world calendar dates are used — the year 215 A.E. maps 1:1 to the
Gregorian calendar for gameplay ergonomics.

This is separate from `festival_service.py`, which handles per-realm
seasonal festivals (Lanterns / Stormwake / etc.). Elder-Gods festivals
are realm-wide and tied to divine favour.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

# ── CANON: The Four Elder Festivals ────────────────────────────────────
FESTIVALS: Dict[str, Dict] = {
    "seren": {
        "name": "Seren's Bloom",
        "major_window": [(3, 19), (3, 20), (3, 21)],   # Spring equinox
        "weekly_dow": 6,                                # Sunday
        "major_atmosphere": (
            "The city is heavy with new blossom — every doorway, every "
            "temple archway, every merchant stall is dressed in fresh "
            "flowers. Children run garlanded through the streets. Every "
            "priestess of Seren keeps her doors open through the night."
        ),
        "minor_atmosphere": (
            "It is Seren's weekly day. The temples burn a low green "
            "incense; healers waive their fees for one hour at dawn."
        ),
        "affinity_boost_major": 30,
        "affinity_boost_minor": 10,
    },
    "yros": {
        "name": "Yros's Anvilrite",
        "major_window": [(12, 20), (12, 21), (12, 22)],  # Winter solstice
        "weekly_dow": 0,                                  # Monday
        "major_atmosphere": (
            "Every forge in every dwarven city rings from dawn to "
            "midnight; no craftsman may leave their anvil until sundown. "
            "In the human and elven realms, smiths hang their finest work "
            "in the market squares and refuse coin for a day."
        ),
        "minor_atmosphere": (
            "It is Yros's weekly day. Every forge keeps its fire brighter "
            "than usual; oath-swearing before a forge on this day is said "
            "to be doubly binding."
        ),
        "affinity_boost_major": 30,
        "affinity_boost_minor": 10,
    },
    "uesis": {
        "name": "Uesis's Star-Vigil",
        "major_window": [(6, 20), (6, 21), (6, 22)],   # Summer solstice
        "weekly_dow": 2,                                # Wednesday
        "major_atmosphere": (
            "The night lasts only two hours, and every scholar-mage in "
            "Tyrandria climbs to their rooftop to watch. Sky-lanterns "
            "drift by the thousand. Airship captains say the wind is "
            "clearer on this night than any other of the year."
        ),
        "minor_atmosphere": (
            "It is Uesis's weekly day. Sky-lanterns float from rooftops "
            "at dusk; scholars leave their books outside overnight to be "
            "'read by the stars.'"
        ),
        "affinity_boost_major": 30,
        "affinity_boost_minor": 10,
    },
    "ehena": {
        "name": "Ehena's Long Hour",
        "major_window": [(9, 21), (9, 22), (9, 23)],   # Autumn equinox
        "weekly_dow": 3,                                # Thursday
        "major_atmosphere": (
            "For one hour at noon, all clocks in Tyrandria are held. No "
            "contract may be signed, no oath sworn, no execution carried "
            "out. Elders sit in silence in the market squares while "
            "children lay ribbons on family graves."
        ),
        "minor_atmosphere": (
            "It is Ehena's weekly day. The market bells ring an extra "
            "beat at each hour; contracts signed today carry a longer "
            "grace period by tradition."
        ),
        "affinity_boost_major": 30,
        "affinity_boost_minor": 10,
    },
}


def _major_today(fest: Dict, now: datetime) -> bool:
    return (now.month, now.day) in [tuple(d) for d in fest["major_window"]]


def _minor_today(fest: Dict, now: datetime) -> bool:
    return now.weekday() == fest["weekly_dow"]


def get_active_festival(now: Optional[datetime] = None) -> Optional[Dict]:
    """Returns the highest-priority Elder-Gods festival active on `now`
    (default: now, UTC), or None. Major festivals beat minor.

    If two majors ever overlap (they can't with this calendar), the god
    listed first in FESTIVALS wins.
    """
    when = now or datetime.now(timezone.utc)
    for god_key, fest in FESTIVALS.items():
        if _major_today(fest, when):
            return {
                "god": god_key,
                "festival_name": fest["name"],
                "level": "major",
                "atmosphere": fest["major_atmosphere"],
                "affinity_boost": fest["affinity_boost_major"],
                "date_iso": when.date().isoformat(),
            }
    for god_key, fest in FESTIVALS.items():
        if _minor_today(fest, when):
            return {
                "god": god_key,
                "festival_name": fest["name"] + " (weekly observance)",
                "level": "minor",
                "atmosphere": fest["minor_atmosphere"],
                "affinity_boost": fest["affinity_boost_minor"],
                "date_iso": when.date().isoformat(),
            }
    return None


def list_calendar() -> List[Dict]:
    """Public catalogue — the frontend shows 'when is each festival?' without
    guessing dates."""
    dow_labels = ["Monday", "Tuesday", "Wednesday", "Thursday",
                  "Friday", "Saturday", "Sunday"]
    return [
        {
            "god": god_key,
            "festival_name": fest["name"],
            "major_dates_mm_dd": [f"{m:02d}-{d:02d}" for m, d in fest["major_window"]],
            "weekly_dow": fest["weekly_dow"],
            "weekly_dow_label": dow_labels[fest["weekly_dow"]],
        }
        for god_key, fest in FESTIVALS.items()
    ]
