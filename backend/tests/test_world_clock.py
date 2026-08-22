"""Tests for the World Clock + Festival services (Phase 1, 2026-05-30)."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from world_clock_service import (
    get_time_of_day,
    format_delarom_date,
    get_world_clock,
    DELAROM_MONTHS,
)
from festival_service import _is_active


# ---------- World Clock ----------

class TestTimeOfDay:
    def test_midnight_is_night(self):
        dt = datetime(2026, 5, 30, 0, 30, tzinfo=timezone.utc)
        assert get_time_of_day(dt)["phase"] == "night"

    def test_dawn(self):
        dt = datetime(2026, 5, 30, 5, 0, tzinfo=timezone.utc)
        assert get_time_of_day(dt)["phase"] == "dawn"

    def test_midday(self):
        dt = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
        assert get_time_of_day(dt)["phase"] == "midday"

    def test_dusk(self):
        dt = datetime(2026, 5, 30, 18, 0, tzinfo=timezone.utc)
        assert get_time_of_day(dt)["phase"] == "dusk"

    def test_late_night(self):
        dt = datetime(2026, 5, 30, 23, 30, tzinfo=timezone.utc)
        assert get_time_of_day(dt)["phase"] == "night"


class TestDelaromDate:
    def test_first_of_month(self):
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "1st of Frostmere"

    def test_second(self):
        dt = datetime(2026, 5, 2, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "2nd of Sunwarden"

    def test_third(self):
        dt = datetime(2026, 8, 3, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "3rd of Harvestglade"

    def test_eleventh_uses_th(self):
        dt = datetime(2026, 5, 11, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "11th of Sunwarden"

    def test_thirteenth_uses_th(self):
        dt = datetime(2026, 5, 13, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "13th of Sunwarden"

    def test_twentyfirst_uses_st(self):
        dt = datetime(2026, 5, 21, tzinfo=timezone.utc)
        assert format_delarom_date(dt) == "21st of Sunwarden"

    def test_all_12_months_named(self):
        assert len(DELAROM_MONTHS) == 12
        assert all(isinstance(m, str) and m for m in DELAROM_MONTHS)


class TestWorldClockBundle:
    def test_returns_all_keys(self):
        c = get_world_clock()
        assert "delarom_date" in c
        assert "time_of_day" in c
        assert "year_real" in c
        assert "phase" in c["time_of_day"]


# ---------- Festival active-window ----------

class TestFestivalIsActive:
    def test_single_day_match(self):
        fest = {"start_month": 5, "start_day": 1, "end_month": 5, "end_day": 1}
        assert _is_active(fest, datetime(2026, 5, 1, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 5, 2, tzinfo=timezone.utc))

    def test_multi_day_within_month(self):
        fest = {"start_month": 11, "start_day": 1, "end_month": 11, "end_day": 3}
        assert _is_active(fest, datetime(2026, 11, 1, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 11, 2, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 11, 3, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 10, 31, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 11, 4, tzinfo=timezone.utc))

    def test_cross_month_window(self):
        # The Veiling: Oct 31 -> Nov 1
        fest = {"start_month": 10, "start_day": 31, "end_month": 11, "end_day": 1}
        assert _is_active(fest, datetime(2026, 10, 31, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 11, 1, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 10, 30, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 11, 2, tzinfo=timezone.utc))

    def test_wraps_year_boundary(self):
        # Hypothetical festival: Dec 28 -> Jan 3
        fest = {"start_month": 12, "start_day": 28, "end_month": 1, "end_day": 3}
        assert _is_active(fest, datetime(2026, 12, 28, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 12, 31, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert _is_active(fest, datetime(2026, 1, 3, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 1, 4, tzinfo=timezone.utc))
        assert not _is_active(fest, datetime(2026, 12, 27, tzinfo=timezone.utc))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
