"""
World Clock Service.

Provides the in-world time-of-day and the Delarom calendar date for any
moment. Times are derived from real UTC — all players experience the same
in-world time regardless of their local timezone. The world thus has its
own consistent rhythm.

The Delarom calendar uses 12 invented month names mapped 1:1 to real-world
months, so festivals can be seeded with simple `(month, day)` tuples.
"""
from datetime import datetime, timezone
from typing import Optional, Dict

# Invented month names that map directly to Jan..Dec
DELAROM_MONTHS = [
    "Frostmere",     # Jan
    "Stormwane",     # Feb
    "Greenwake",     # Mar
    "Bloomtide",     # Apr
    "Sunwarden",     # May
    "Highember",     # Jun
    "Goldreap",      # Jul
    "Harvestglade",  # Aug
    "Mistweave",     # Sep
    "Hollowfall",    # Oct
    "Lanternlong",   # Nov
    "Yulewreath",    # Dec
]

# 6-phase day. Each tuple is (start_hour_inclusive, end_hour_exclusive, phase, icon, vibe).
# Hours roll over at midnight.
_TIME_PHASES = [
    (0,  4,  "night",     "moon",     "the streets are still, the stars are sharp"),
    (4,  7,  "dawn",      "sunrise",  "the first grey light bleeds through the windows"),
    (7,  11, "morning",   "sunrise",  "the day has begun in earnest, smoke rising from chimneys"),
    (11, 14, "midday",    "sun",      "the sun stands high and bright over the rooftops"),
    (14, 17, "afternoon", "sun",      "the warmth of afternoon lies heavy across the stones"),
    (17, 20, "dusk",      "sunset",   "the sky burns amber and the lamps are being lit"),
    (20, 24, "night",     "moon",     "torchlight flickers and night folk are about"),
]


def get_time_of_day(dt: Optional[datetime] = None) -> Dict:
    """Return the current in-world time phase and a short atmospheric line."""
    dt = dt or datetime.now(timezone.utc)
    h = dt.hour
    for start, end, phase, icon, vibe in _TIME_PHASES:
        if start <= h < end:
            return {
                "phase": phase,
                "icon": icon,
                "vibe": vibe,
                "hour_utc": h,
            }
    # Fallback (shouldn't hit — table covers 0..24)
    return {"phase": "night", "icon": "moon", "vibe": "darkness lies thick", "hour_utc": h}


def format_delarom_date(dt: Optional[datetime] = None) -> str:
    """Return a Delarom-style date string like '14th of Lanternlong'."""
    dt = dt or datetime.now(timezone.utc)
    day = dt.day
    month = DELAROM_MONTHS[dt.month - 1]
    # English ordinal suffix
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix} of {month}"


def get_world_clock(dt: Optional[datetime] = None) -> Dict:
    """Bundle the current Delarom date and time-of-day into one payload."""
    dt = dt or datetime.now(timezone.utc)
    # Import late to avoid a circular import if callers extend world_clock.
    try:
        from world_calendar_service import get_world_calendar
        calendar = get_world_calendar(dt)
    except Exception:
        calendar = None
    return {
        "delarom_date": format_delarom_date(dt),
        "time_of_day": get_time_of_day(dt),
        "year_real": dt.year,
        "calendar": calendar,
    }
