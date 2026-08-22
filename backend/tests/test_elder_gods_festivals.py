"""Elder-Gods festival calendar tests."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elder_gods_festivals import (  # noqa: E402
    FESTIVALS,
    get_active_festival,
    list_calendar,
)


def _dt(year, month, day):
    return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)


def test_all_four_gods_have_calendars():
    assert set(FESTIVALS) == {"seren", "yros", "uesis", "ehena"}


def test_list_calendar_returns_four_entries_with_dow_labels():
    cal = list_calendar()
    assert len(cal) == 4
    dow_set = {c["weekly_dow_label"] for c in cal}
    # No two gods should collide on weekly_dow
    assert len(dow_set) == 4
    for c in cal:
        assert 3 == len(c["major_dates_mm_dd"])  # 3-day windows


def test_serens_bloom_active_on_spring_equinox():
    # 2026-03-20 is Friday — but the major-window check ignores the day-of-week.
    fest = get_active_festival(_dt(2026, 3, 20))
    assert fest is not None
    assert fest["god"] == "seren"
    assert fest["level"] == "major"
    assert fest["affinity_boost"] == 30
    assert "Bloom" in fest["festival_name"]


def test_yross_anvilrite_active_on_winter_solstice():
    fest = get_active_festival(_dt(2026, 12, 21))
    assert fest is not None
    assert fest["god"] == "yros"
    assert fest["level"] == "major"
    assert fest["affinity_boost"] == 30


def test_uesis_star_vigil_active_on_summer_solstice():
    fest = get_active_festival(_dt(2026, 6, 21))
    assert fest is not None
    assert fest["god"] == "uesis"
    assert fest["level"] == "major"


def test_ehena_long_hour_active_on_autumn_equinox():
    fest = get_active_festival(_dt(2026, 9, 22))
    assert fest is not None
    assert fest["god"] == "ehena"
    assert fest["level"] == "major"


def test_no_major_window_edges_case_off_by_one():
    """Just outside a major window: no major festival."""
    fest = get_active_festival(_dt(2026, 3, 22))  # Bloom ends 3/21
    # 3/22 is a Sunday in 2026 — expect Seren minor (Sunday), not major
    assert fest is not None
    assert fest["level"] == "minor"
    assert fest["god"] == "seren"


def test_weekly_minor_holy_days():
    # 2026-04-06 is a Monday → Yros's weekly minor
    fest = get_active_festival(_dt(2026, 4, 6))
    assert fest is not None
    assert fest["god"] == "yros"
    assert fest["level"] == "minor"
    assert fest["affinity_boost"] == 10
    # 2026-04-08 is a Wednesday → Uesis's weekly minor
    fest = get_active_festival(_dt(2026, 4, 8))
    assert fest is not None
    assert fest["god"] == "uesis"
    assert fest["level"] == "minor"


def test_no_festival_returns_none_when_nothing_active():
    # Every day has SOME festival because there are 4 minor days + 3 majors
    # among 7 possible weekdays. Verify Friday/Saturday quiet days.
    # 2026-04-10 is Friday; 2026-04-11 is Saturday.
    fest_fri = get_active_festival(_dt(2026, 4, 10))
    fest_sat = get_active_festival(_dt(2026, 4, 11))
    # None of the four gods have Fri (4) or Sat (5) as their weekly_dow.
    assert fest_fri is None
    assert fest_sat is None


def test_major_beats_minor_on_priority():
    """When a major and a minor would both match (calendar allows this on
    the equinox/solstice weekday), the major wins."""
    # 2026-06-21 is a Sunday (Seren minor) AND Uesis major.
    # Priority: Uesis major beats Seren minor.
    fest = get_active_festival(_dt(2026, 6, 21))
    assert fest is not None
    assert fest["level"] == "major"
    assert fest["god"] == "uesis"


def test_active_festival_shape():
    fest = get_active_festival(_dt(2026, 3, 20))
    assert set(fest) >= {"god", "festival_name", "level", "atmosphere",
                         "affinity_boost", "date_iso"}
    assert isinstance(fest["atmosphere"], str)
    assert len(fest["atmosphere"]) > 20
