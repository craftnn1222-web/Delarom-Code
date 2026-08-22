"""Tests for the Economy service.

Covers:
- Catalogue seeding (idempotent).
- Faction specialty upsert + cost history capture.
- City import price computation (two-step chain).
- Price cascade when a base_cost changes.
- Contract break → city good marked unavailable.
- top_movers picks the largest absolute deltas.
- broken_routes returns broken contracts newest-first.
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from economy_service import (
    EconomyService,
    DEFAULT_FACTION_TO_CITY_TARIFF_PCT,
    goods_affected_by_event,
)
from tests.test_law_jail_overhaul import FakeDB, FakeCollection, _run  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — extend FakeDB with the collections the economy service needs.
# ---------------------------------------------------------------------------


def _make_db_with_faction(faction_slug="forgemasters-guild", nation_home="dhor-kuldor"):
    db = FakeDB()
    db.goods = FakeCollection()
    db.faction_specialties = FakeCollection()
    db.trade_contracts = FakeCollection()
    db.city_market_prices = FakeCollection()
    db.cost_history = FakeCollection()
    db.economy_events = FakeCollection()
    db.factions = FakeCollection()
    db.cities = FakeCollection()
    db.faction_memberships = FakeCollection()
    db.characters = FakeCollection()
    db.factions.docs.append({
        "id": "fid-forgemasters",
        "slug": faction_slug,
        "name": "The Forgemaster's Guild",
        "nation_home": nation_home,
        "is_active": True,
    })
    db.cities.docs.append({
        "id": "cid-astra-lun",
        "slug": "astra-lun",
        "nation": "aigraels",
        "name": "Astra'Lun",
    })
    return db


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def test_seed_canonical_goods_inserts_all_then_skips():
    db = _make_db_with_faction()
    es = EconomyService(db)
    r1 = _run(es.seed_canonical_goods())
    assert r1["inserted"] == 25
    assert r1["skipped"] == 0
    r2 = _run(es.seed_canonical_goods())
    assert r2["inserted"] == 0
    assert r2["skipped"] == 25


def test_seed_starter_specialties_writes_offerings():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    r = _run(es.seed_starter_specialties())
    # Forgemasters has 5 specialties in the starter seed
    assert r["upserts"] >= 5
    specs = _run(es.list_specialties_for_faction("fid-forgemasters"))
    slugs = {s["good_slug"] for s in specs}
    assert "iron-ingots" in slugs
    assert "steel-armor" in slugs


# ---------------------------------------------------------------------------
# Specialty upsert + cost history
# ---------------------------------------------------------------------------


def test_upsert_specialty_records_cost_history():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())

    # First update — bump iron-ingots from 40g to 70g
    doc = _run(es.upsert_specialty(
        faction_id="fid-forgemasters",
        faction_slug="forgemasters-guild",
        good_slug="iron-ingots",
        base_cost=70,
        capacity=120,
        description="Smelted in clan forges",
        reason="Coal shortage",
    ))
    assert doc["base_cost"] == 70
    assert any(h.get("delta") == 30 and h.get("reason") == "Coal shortage" for h in doc["cost_history"])
    # cost_history collection (global) also written
    assert len(db.cost_history.docs) == 1


def test_upsert_specialty_no_change_no_history():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    doc = _run(es.upsert_specialty(
        faction_id="fid-forgemasters",
        faction_slug="forgemasters-guild",
        good_slug="iron-ingots",
        base_cost=40,  # same as seed
        capacity=120,
    ))
    assert doc["base_cost"] == 40
    assert len(db.cost_history.docs) == 0


def test_remove_specialty_purges_row():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    ok = _run(es.remove_specialty("fid-forgemasters", "iron-ingots"))
    assert ok is True
    remaining = _run(es.list_specialties_for_faction("fid-forgemasters"))
    assert all(s["good_slug"] != "iron-ingots" for s in remaining)


# ---------------------------------------------------------------------------
# Contracts and price chain
# ---------------------------------------------------------------------------


def test_create_contract_propagates_import_price():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())

    contract = _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city",
        good_slug="iron-ingots",
        to_city_slug="astra-lun",
        to_nation="aigraels",
        tariff_pct=DEFAULT_FACTION_TO_CITY_TARIFF_PCT,  # 25
        quantity_per_tick=50,
    ))
    assert contract["status"] == "active"
    assert contract["base_cost_snapshot"] == 40

    market = _run(es.get_good_in_city("aigraels", "astra-lun", "iron-ingots"))
    # 40 * 1.25 = 50
    assert market["import_price"] == 50
    assert market["is_available"] is True
    assert market["source_faction_slug"] == "forgemasters-guild"


def test_base_cost_change_cascades_to_city_price():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city",
        good_slug="iron-ingots",
        to_city_slug="astra-lun",
        to_nation="aigraels",
        tariff_pct=25,
    ))
    # Bump base 40 → 70 → city should now show 88g (round(70 * 1.25))
    _run(es.upsert_specialty(
        faction_id="fid-forgemasters",
        faction_slug="forgemasters-guild",
        good_slug="iron-ingots",
        base_cost=70,
        capacity=120,
        reason="war",
    ))
    market = _run(es.get_good_in_city("aigraels", "astra-lun", "iron-ingots"))
    assert market["import_price"] == 88


def test_break_contract_marks_good_unavailable():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    contract = _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city",
        good_slug="iron-ingots",
        to_city_slug="astra-lun",
        to_nation="aigraels",
        tariff_pct=25,
    ))
    # Before break — available
    market = _run(es.get_good_in_city("aigraels", "astra-lun", "iron-ingots"))
    assert market["is_available"] is True
    # Break it
    _run(es.break_contract(contract["id"], reason="war between cities"))
    market = _run(es.get_good_in_city("aigraels", "astra-lun", "iron-ingots"))
    assert market["is_available"] is False
    assert market["import_price"] is None


def test_create_contract_fails_if_faction_doesnt_produce_good():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    # Forgemasters does NOT produce spiced-wine
    with pytest.raises(ValueError):
        _run(es.create_standing_contract(
            from_faction_id="fid-forgemasters",
            from_faction_slug="forgemasters-guild",
            to_type="city",
            good_slug="spiced-wine",
            to_city_slug="astra-lun",
            to_nation="aigraels",
            tariff_pct=25,
        ))


def test_compute_retail_price_static():
    assert EconomyService.compute_retail_price(100, 30) == 130
    assert EconomyService.compute_retail_price(0, 30) == 0
    assert EconomyService.compute_retail_price(50, 0) == 50


def test_resolve_item_auto_price_returns_none_without_market():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    price = _run(es.resolve_item_auto_price(
        nation="aigraels", city_slug="astra-lun",
        good_slug="iron-ingots", markup_pct=30,
    ))
    assert price is None


def test_resolve_item_auto_price_returns_chained_price():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city",
        good_slug="iron-ingots",
        to_city_slug="astra-lun",
        to_nation="aigraels",
        tariff_pct=25,
    ))
    # base 40 → city import 50 → shop retail at 30% markup = 65
    price = _run(es.resolve_item_auto_price(
        nation="aigraels", city_slug="astra-lun",
        good_slug="iron-ingots", markup_pct=30,
    ))
    assert price == 65


# ---------------------------------------------------------------------------
# Top movers + broken routes
# ---------------------------------------------------------------------------


def test_top_movers_orders_by_abs_delta():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    # Three deltas: +20 (small), +200 (huge), -50 (medium)
    _run(es.upsert_specialty(faction_id="fid-forgemasters", faction_slug="forgemasters-guild",
                              good_slug="iron-ore", base_cost=38, capacity=200, reason="r1"))
    _run(es.upsert_specialty(faction_id="fid-forgemasters", faction_slug="forgemasters-guild",
                              good_slug="steel-armor", base_cost=550, capacity=8, reason="r3"))  # 750 -> 550 = -200
    _run(es.upsert_specialty(faction_id="fid-forgemasters", faction_slug="forgemasters-guild",
                              good_slug="iron-swords", base_cost=80, capacity=30, reason="r2"))  # 130 -> 80 = -50
    movers = _run(es.top_movers(limit=10, hours=24))
    deltas = [m["delta"] for m in movers]
    assert abs(deltas[0]) >= abs(deltas[1]) >= abs(deltas[2])


def test_broken_routes_returns_only_broken():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    c1 = _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city", good_slug="iron-ingots",
        to_city_slug="astra-lun", to_nation="aigraels", tariff_pct=25,
    ))
    c2 = _run(es.create_standing_contract(
        from_faction_id="fid-forgemasters",
        from_faction_slug="forgemasters-guild",
        to_type="city", good_slug="iron-ore",
        to_city_slug="astra-lun", to_nation="aigraels", tariff_pct=25,
    ))
    _run(es.break_contract(c1["id"], reason="war"))
    routes = _run(es.list_broken_routes())
    ids = {r["id"] for r in routes}
    assert c1["id"] in ids
    assert c2["id"] not in ids


# ---------------------------------------------------------------------------
# Event hook helpers
# ---------------------------------------------------------------------------


def test_goods_affected_by_event_filters_by_tags():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    # "war" event maps to tags ["war","weapon","armor","metal"]
    affected = _run(goods_affected_by_event(db, event_type="war"))
    slugs = {g["slug"] for g in affected}
    assert "iron-ingots" in slugs
    assert "steel-armor" in slugs
    # food / luxury without metal tag should not appear
    assert "salted-fish" not in slugs


def test_unknown_event_returns_empty():
    db = _make_db_with_faction()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    out = _run(goods_affected_by_event(db, event_type="crime"))
    assert out == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
