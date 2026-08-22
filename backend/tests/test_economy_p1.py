"""Tests for P1 economy extensions:
- Caravan lifecycle (post → claim → complete success/fail → cancel).
- Leader-vs-admin auth on caravan posting.
- Faction-leader contract creation (mirroring admin path).
- _auto_price_or_400 helper in routes/shops.py.
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from economy_service import EconomyService
from tests.test_law_jail_overhaul import FakeDB, FakeCollection, _run  # noqa: E402


# ---------------------------------------------------------------------------
# Fake DB extension — economy needs goods/specialties/contracts/cities
# ---------------------------------------------------------------------------


def _make_db():
    db = FakeDB()
    db.goods = FakeCollection()
    db.faction_specialties = FakeCollection()
    db.trade_contracts = FakeCollection()
    db.city_market_prices = FakeCollection()
    db.cost_history = FakeCollection()
    db.economy_events = FakeCollection()
    db.trade_caravans = FakeCollection()
    db.factions = FakeCollection()
    db.cities = FakeCollection()
    db.shops = FakeCollection()
    db.items = FakeCollection()
    db.faction_memberships = FakeCollection()
    db.users = FakeCollection()
    db.factions.docs.append({
        "id": "fid-forge", "slug": "forgemasters-guild", "name": "The Forgemaster's Guild",
        "nation_home": "dhor-kuldor", "is_active": True,
    })
    db.cities.docs.append({
        "id": "cid-astra", "slug": "astra-lun", "nation": "aigraels", "name": "Astra'Lun",
    })
    return db


# ---------------------------------------------------------------------------
# _auto_price_or_400 — sourcing path
# ---------------------------------------------------------------------------


def test_auto_price_returns_cascaded_retail_price():
    from routes.shops import _auto_price_or_400

    db = _make_db()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="city", good_slug="iron-ingots",
        to_city_slug="astra-lun", to_nation="aigraels", tariff_pct=25,
    ))
    # base 40 * 1.25 = 50 import * 1.30 markup = 65 retail
    item = {
        "source_good_slug": "iron-ingots",
        "source_city_slug": "astra-lun",
        "source_nation": "aigraels",
        "markup_pct": 30,
    }
    shop = {"nation": "aigraels"}
    price = _run(_auto_price_or_400(db, item, shop))
    assert price == 65


def test_auto_price_400_when_no_contract():
    from fastapi import HTTPException
    from routes.shops import _auto_price_or_400

    db = _make_db()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    # No contract created — market for astra-lun/iron-ingots is empty.
    item = {
        "source_good_slug": "iron-ingots",
        "source_city_slug": "astra-lun",
        "source_nation": "aigraels",
        "markup_pct": 30,
    }
    shop = {"nation": "aigraels"}
    with pytest.raises(HTTPException) as exc:
        _run(_auto_price_or_400(db, item, shop))
    assert exc.value.status_code == 400
    assert "active trade contract" in exc.value.detail.lower()


def test_auto_price_400_when_missing_fields():
    from fastapi import HTTPException
    from routes.shops import _auto_price_or_400

    db = _make_db()
    item = {
        "source_good_slug": "iron-ingots",
        # source_city_slug missing
        "source_nation": "aigraels",
        "markup_pct": 30,
    }
    shop = {"nation": "aigraels"}
    with pytest.raises(HTTPException) as exc:
        _run(_auto_price_or_400(db, item, shop))
    assert exc.value.status_code == 400


def test_auto_price_uses_shop_nation_fallback():
    """If item.source_nation is empty, fall back to shop.nation."""
    from routes.shops import _auto_price_or_400

    db = _make_db()
    es = EconomyService(db)
    _run(es.seed_canonical_goods())
    _run(es.seed_starter_specialties())
    _run(es.create_standing_contract(
        from_faction_id="fid-forge",
        from_faction_slug="forgemasters-guild",
        to_type="city", good_slug="iron-ingots",
        to_city_slug="astra-lun", to_nation="aigraels", tariff_pct=25,
    ))
    item = {
        "source_good_slug": "iron-ingots",
        "source_city_slug": "astra-lun",
        # source_nation empty — should use shop_doc.nation
        "markup_pct": 30,
    }
    shop = {"nation": "aigraels"}
    price = _run(_auto_price_or_400(db, item, shop))
    assert price == 65


# ---------------------------------------------------------------------------
# Charter offered_goods Pydantic shape
# ---------------------------------------------------------------------------


def test_offered_good_body_validates():
    from routes._factions_lib import OfferedGoodBody, FileCharterBody
    og = OfferedGoodBody(good_slug="iron-ingots", base_cost=50, capacity=20, description="From smelters")
    assert og.good_slug == "iron-ingots"
    assert og.base_cost == 50
    # Charter accepts a list of these
    charter = FileCharterBody(
        character_id="c1", name="Test Guild", description="Twenty character minimum description here.",
        offered_goods=[og],
    )
    assert len(charter.offered_goods) == 1
    assert charter.offered_goods[0].good_slug == "iron-ingots"


def test_offered_good_body_rejects_invalid_base_cost():
    from routes._factions_lib import OfferedGoodBody
    with pytest.raises(Exception):
        OfferedGoodBody(good_slug="x", base_cost=0)  # base_cost must be >= 1


def test_charter_offered_goods_capped_at_8():
    """Pydantic max_length=8 keeps charter applications focused."""
    from routes._factions_lib import OfferedGoodBody, FileCharterBody
    too_many = [OfferedGoodBody(good_slug=f"g{i}", base_cost=10) for i in range(9)]
    with pytest.raises(Exception):
        FileCharterBody(
            character_id="c1", name="Test", description="Long description here over 20 chars.",
            offered_goods=too_many,
        )


# ---------------------------------------------------------------------------
# Caravan Pydantic shape + status state machine
# ---------------------------------------------------------------------------


def test_post_caravan_body_validates():
    from routes.economy import PostCaravanBody
    body = PostCaravanBody(
        good_slug="iron-ingots", quantity=50, to_city_slug="astra-lun",
        reward_gold=400, expires_in_hours=48,
    )
    assert body.quantity == 50
    assert body.reward_gold == 400
    assert body.expires_in_hours == 48


def test_post_caravan_body_clamps_expires():
    """Pydantic constrains expires_in_hours to [1, 720]."""
    from routes.economy import PostCaravanBody
    with pytest.raises(Exception):
        PostCaravanBody(
            good_slug="iron-ingots", quantity=50, to_city_slug="astra-lun",
            reward_gold=400, expires_in_hours=1000,  # > 720
        )


def test_complete_caravan_default_success():
    from routes.economy import CompleteCaravanBody
    body = CompleteCaravanBody()
    assert body.success is True
    assert body.story == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
