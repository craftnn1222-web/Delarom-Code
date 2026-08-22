"""Tests for P1.5 — diplomacy → economy hook.

When two factions' rivalry intensity FRESHLY crosses into hostile territory
(>= HOSTILITY_BREAK_THRESHOLD = 50), all active standing contracts between
them are broken. Re-crossing within the hostile band does NOT re-fire the
break (idempotent on the threshold).
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from economy_service import EconomyService
from routes._factions_lib import (
    _maybe_break_contracts_on_hostility,
    HOSTILITY_BREAK_THRESHOLD,
)
from tests.test_law_jail_overhaul import FakeDB, FakeCollection, _run  # noqa: E402


def _make_db_with_two_factions():
    db = FakeDB()
    # Collections used by EconomyService + the hostility helper
    db.goods = FakeCollection()
    db.faction_specialties = FakeCollection()
    db.trade_contracts = FakeCollection()
    db.city_market_prices = FakeCollection()
    db.cost_history = FakeCollection()
    db.economy_events = FakeCollection()
    db.factions = FakeCollection()
    db.cities = FakeCollection()
    db.factions.docs.append({
        "id": "fid-forge", "slug": "forgemasters-guild", "name": "Forgemasters",
        "nation_home": "dhor-kuldor", "is_active": True,
    })
    db.factions.docs.append({
        "id": "fid-loremasters", "slug": "loremasters-guild", "name": "Loremasters",
        "nation_home": "selindori", "is_active": True,
    })
    db.cities.docs.append({
        "id": "cid-astra", "slug": "astra-lun", "nation": "aigraels", "name": "Astra'Lun",
    })
    return db


def test_threshold_constant_is_50():
    assert HOSTILITY_BREAK_THRESHOLD == 50


def test_no_break_when_below_threshold():
    db = _make_db_with_two_factions()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="faction",
        good_slug="iron-ingots",
        to_faction_id="fid-loremasters",
        to_faction_slug="loremasters-guild",
        tariff_pct=25,
    ))
    broken = _run(_maybe_break_contracts_on_hostility(
        db, faction_a_id="fid-forge", faction_b_id="fid-loremasters",
        old_intensity=10, new_intensity=40,
        reason="dispute over shipping lanes",
    ))
    assert broken == 0
    contract = db.trade_contracts.docs[0]
    assert contract["status"] == "active"


def test_break_when_freshly_crossing_threshold():
    db = _make_db_with_two_factions()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="faction",
        good_slug="iron-ingots",
        to_faction_id="fid-loremasters",
        to_faction_slug="loremasters-guild",
        tariff_pct=25,
    ))
    broken = _run(_maybe_break_contracts_on_hostility(
        db, faction_a_id="fid-forge", faction_b_id="fid-loremasters",
        old_intensity=40, new_intensity=55,
        reason="open hostilities",
    ))
    assert broken == 1
    contract = db.trade_contracts.docs[0]
    assert contract["status"] == "broken"
    assert "Diplomacy" in (contract.get("break_reason") or "")


def test_no_repeat_break_within_hostile_band():
    """Once both factions are hostile, escalating further must NOT keep
    re-breaking contracts (which would be inefficient + spammy)."""
    db = _make_db_with_two_factions()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="faction",
        good_slug="iron-ingots",
        to_faction_id="fid-loremasters",
        to_faction_slug="loremasters-guild",
        tariff_pct=25,
    ))
    # Already hostile (old >= threshold) — even if new is higher, return 0
    broken = _run(_maybe_break_contracts_on_hostility(
        db, faction_a_id="fid-forge", faction_b_id="fid-loremasters",
        old_intensity=55, new_intensity=80,
        reason="raids continue",
    ))
    assert broken == 0
    contract = db.trade_contracts.docs[0]
    # Contract was never re-broken, stays active
    assert contract["status"] == "active"


def test_break_works_bidirectionally():
    """Contracts where B is the source and A is the destination should ALSO
    be broken (the helper is symmetric)."""
    db = _make_db_with_two_factions()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    # Make Loremasters a producer of rune-scrolls
    # (already in starter — re-confirm)
    _run(es.create_standing_contract(
        from_faction_id="fid-loremasters",
        from_faction_slug="loremasters-guild",
        to_type="faction",
        good_slug="rune-scrolls",
        to_faction_id="fid-forge",
        to_faction_slug="forgemasters-guild",
        tariff_pct=20,
    ))
    broken = _run(_maybe_break_contracts_on_hostility(
        db, faction_a_id="fid-forge", faction_b_id="fid-loremasters",
        old_intensity=49, new_intensity=51,
        reason="trade-route assassination",
    ))
    # Either direction should have been broken — the contract from
    # Loremasters → Forgemasters is between A and B regardless of direction.
    assert broken >= 1
    assert any(c.get("status") == "broken" for c in db.trade_contracts.docs)


def test_break_does_not_touch_unrelated_contracts():
    """A third-party contract Forgemasters → some other faction must stay
    alive when Forgemasters/Loremasters become hostile."""
    db = _make_db_with_two_factions()
    db.factions.docs.append({
        "id": "fid-third", "slug": "third-faction", "name": "Third Faction",
        "nation_home": "ammeonon", "is_active": True,
    })
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="faction",
        good_slug="iron-ingots",
        to_faction_id="fid-third",
        to_faction_slug="third-faction",
        tariff_pct=25,
    ))
    broken = _run(_maybe_break_contracts_on_hostility(
        db, faction_a_id="fid-forge", faction_b_id="fid-loremasters",
        old_intensity=0, new_intensity=55,
        reason="war declared",
    ))
    assert broken == 0  # no contract between forge↔loremasters exists
    third_party = next(
        c for c in db.trade_contracts.docs if c.get("to_faction_id") == "fid-third"
    )
    assert third_party["status"] == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
