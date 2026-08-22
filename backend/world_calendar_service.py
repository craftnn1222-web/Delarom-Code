"""Delarom Calendar Service — in-world year progression.

The existing `world_clock_service` maps real UTC 1:1 to Delarom
month names and time-of-day. This service adds the missing YEAR axis
so the world can actually *age*.

Design (per user spec, iteration A):
    • Ratio B — 1 real week = 1 in-world month.
    • 12 real weeks = 1 in-world year (~4.33 in-world years / real year).
    • Anchor: 2026-02-21T00:00:00Z = 215 A.E., Stormwane 1.

`world_days_since_anchor()` is the canonical duration primitive — every
downstream feature (bounty expiry, letter delivery, siege length) is
measured in *world days*, not real days, so pacing feels consistent to
the player experiencing the ratio.

Formulas
--------
    world_days_per_real_day = 30 / 7   (30-day months ÷ 7-day real weeks)
    world_months_per_real_year = 365.25 / 7   ≈ 52.18
    world_years_per_real_year  = world_months_per_real_year / 12 ≈ 4.35
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from world_clock_service import DELAROM_MONTHS


# ── anchor ─────────────────────────────────────────────────────
ANCHOR_UTC = datetime(2026, 2, 21, 0, 0, 0, tzinfo=timezone.utc)
ANCHOR_YEAR = 215                            # 215 A.E.
ANCHOR_MONTH_INDEX = 1                       # Stormwane (Feb → Stormwane in DELAROM_MONTHS)
ANCHOR_DAY = 1                               # Stormwane 1

DAYS_PER_MONTH = 30
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = DAYS_PER_MONTH * MONTHS_PER_YEAR   # 360

# 7 real days = 1 in-world month = 30 in-world days
WORLD_DAYS_PER_REAL_DAY = DAYS_PER_MONTH / 7.0


def world_days_since_anchor(dt: Optional[datetime] = None) -> int:
    """Whole in-world days elapsed since the anchor (never negative)."""
    dt = dt or datetime.now(timezone.utc)
    delta_seconds = (dt - ANCHOR_UTC).total_seconds()
    real_days = delta_seconds / 86400.0
    world_days = real_days * WORLD_DAYS_PER_REAL_DAY
    return max(0, int(world_days))


def _resolve_date(world_days: int) -> Dict:
    """Convert an in-world day-count into {year, month_index, month_name, day}."""
    total = world_days + (ANCHOR_MONTH_INDEX * DAYS_PER_MONTH) + (ANCHOR_DAY - 1)
    # `total` is the absolute number of days since 1 Frostmere 215 A.E. (year 0-index).
    year_offset = total // DAYS_PER_YEAR
    remainder = total % DAYS_PER_YEAR
    month_index = int(remainder // DAYS_PER_MONTH)   # 0..11
    day = int(remainder % DAYS_PER_MONTH) + 1        # 1..30
    return {
        "year": ANCHOR_YEAR + int(year_offset),
        "month_index": month_index,
        "month_name": DELAROM_MONTHS[month_index],
        "day": day,
    }


def get_world_calendar(dt: Optional[datetime] = None) -> Dict:
    """Full Delarom calendar payload for the given moment."""
    dt = dt or datetime.now(timezone.utc)
    days = world_days_since_anchor(dt)
    d = _resolve_date(days)
    ordinal = _ordinal(d["day"])
    return {
        "year": d["year"],
        "year_label": f"{d['year']} A.E.",
        "month_index": d["month_index"],
        "month_name": d["month_name"],
        "day": d["day"],
        "world_days_elapsed": days,
        "formatted": f"{ordinal} of {d['month_name']}, {d['year']} A.E.",
        "compact": f"{d['day']} {d['month_name']} {d['year']} A.E.",
    }


def add_world_days(base_iso: Optional[str], world_days: int) -> str:
    """Add N world days to an ISO real-utc timestamp and return the new
    real-utc ISO string. Used for expiry math on bounties / contracts /
    sieges — callers store a real-utc expiry so they compare cheaply to
    `datetime.now(timezone.utc)`.
    """
    if base_iso:
        try:
            base = datetime.fromisoformat(base_iso.replace("Z", "+00:00"))
        except Exception:
            base = datetime.now(timezone.utc)
    else:
        base = datetime.now(timezone.utc)
    real_days_delta = world_days / WORLD_DAYS_PER_REAL_DAY
    return (base + timedelta(days=real_days_delta)).isoformat()


def real_seconds_until_world_days(world_days: int) -> float:
    """How many real seconds equal `world_days` in-world days."""
    return (world_days / WORLD_DAYS_PER_REAL_DAY) * 86400.0


def _ordinal(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suf}"
