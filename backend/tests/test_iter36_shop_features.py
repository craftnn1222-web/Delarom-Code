"""Iteration 36 - Trade Contracts seed + Auto-restock persistence + Auto-pricing live prices.

Tests:
 1) POST /api/economy/admin/seed-contracts is idempotent (already run — should now report
    created:0, skipped:>=12, available_market_rows>=13)
 2) Auto-pricing lights up: /api/economy/market/prices returns retail prices for the
    four known good+city combos
 3) auto_restock + restock_target fields persist through item CREATE + UPDATE + GET
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://npc-economy-preview.preview.emergentagent.com').rstrip('/')
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# --- Trade Contracts seed --------------------------------------------------

class TestSeedTradeContracts:
    def test_seed_is_idempotent(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/economy/admin/seed-contracts")
        assert r.status_code == 200, r.text
        data = r.json()
        # Contract shape
        assert "created" in data
        assert "skipped" in data
        assert "contracts" in data
        assert "available_market_rows" in data
        # After main agent already ran once, re-run must be idempotent
        assert data["created"] == 0, f"expected 0 new (idempotent) got {data['created']}"
        assert data["skipped"] >= 12, f"expected >=12 skipped got {data['skipped']}"
        assert data["available_market_rows"] >= 13, (
            f"expected >=13 live market rows got {data['available_market_rows']}"
        )
        assert isinstance(data["contracts"], list)

    def test_seed_requires_admin(self):
        # No auth — should be 401/403
        r = requests.post(f"{BASE_URL}/api/economy/admin/seed-contracts")
        assert r.status_code in (401, 403), f"expected auth-gated, got {r.status_code}"


# --- Market prices "light up" ---------------------------------------------

class TestMarketPricesLive:
    """The four canonical combos main agent seeded should now return a retail price."""

    @pytest.mark.parametrize("nation,city_slug,good_slug,expected_import", [
        ("aigraels", "ironhold", "iron-ingots", 50),
        ("dhor-kuldor", "ancestor-hall", "iron-swords", 162),
        ("selindori", "aer-cyr", "scribing-service", 60),
        ("ammeonon", "amberport", "silver-bullion", 212),
    ])
    def test_combo_has_live_retail_price(self, admin_client, nation, city_slug, good_slug, expected_import):
        r = admin_client.get(f"{BASE_URL}/api/economy/markets/{nation}/{city_slug}")
        assert r.status_code == 200, f"market lookup {nation}/{city_slug}: {r.status_code} {r.text[:200]}"
        prices = r.json()
        assert isinstance(prices, list) and len(prices) >= 1, f"no market prices at {nation}/{city_slug}: {prices}"
        row = next((p for p in prices if p.get("good_slug") == good_slug), None)
        assert row is not None, f"{good_slug} not present in {nation}/{city_slug} market: {[p.get('good_slug') for p in prices]}"
        # Should have some price field > 0 (import_price or retail_price)
        price = row.get("retail_price") or row.get("import_price") or row.get("price")
        assert price is not None and price > 0, f"no price in market row: {row}"


# --- Auto-restock field persistence ---------------------------------------

class TestAutoRestockPersistence:
    """Create an item with auto_restock + restock_target, GET it back, update, GET again."""

    @pytest.fixture(scope="class")
    def shop_id(self, admin_client):
        # Admin owns 'Astral Antiquities' — /shops/my-shop returns the owner's shop
        r = admin_client.get(f"{BASE_URL}/api/shops/my-shop")
        assert r.status_code == 200, r.text
        shop = r.json()
        assert shop.get("id"), f"no shop returned: {shop}"
        return shop["id"]

    def test_create_item_with_restock(self, admin_client, shop_id):
        payload = {
            "shop_id": shop_id,
            "name": "TEST_iter36_restock_item",
            "description": "test auto-restock persistence",
            "category": "misc",
            "price": 25,
            "stock": 3,
            "auto_restock": True,
            "restock_target": 9,
        }
        r = admin_client.post(f"{BASE_URL}/api/shops/{shop_id}/items", json=payload)
        assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text[:400]}"
        item = r.json()
        item_id = item.get("id")
        assert item_id, item
        # Verify fields on the create response
        assert item.get("auto_restock") is True, f"auto_restock not True in response: {item}"
        assert item.get("restock_target") == 9, f"restock_target wrong in response: {item}"

        # GET items back to confirm persistence
        rget = admin_client.get(f"{BASE_URL}/api/shops/{shop_id}/items")
        assert rget.status_code == 200, rget.text
        items = rget.json()
        found = next((x for x in items if x.get("id") == item_id), None)
        assert found is not None, f"created item not found in list"
        assert found.get("auto_restock") is True
        assert found.get("restock_target") == 9

        # Update: disable, then re-enable with new target
        upd_payload = dict(payload)
        upd_payload["auto_restock"] = False
        upd_payload["restock_target"] = 0
        rupd = admin_client.put(f"{BASE_URL}/api/items/{item_id}", json=upd_payload)
        assert rupd.status_code == 200, f"update failed: {rupd.status_code} {rupd.text[:400]}"
        rget2 = admin_client.get(f"{BASE_URL}/api/shops/{shop_id}/items")
        found2 = next((x for x in rget2.json() if x.get("id") == item_id), None)
        assert found2 is not None
        assert found2.get("auto_restock") is False, f"disable didn't persist: {found2}"

        # Re-enable with target=12
        upd_payload["auto_restock"] = True
        upd_payload["restock_target"] = 12
        rupd2 = admin_client.put(f"{BASE_URL}/api/items/{item_id}", json=upd_payload)
        assert rupd2.status_code == 200, rupd2.text
        rget3 = admin_client.get(f"{BASE_URL}/api/shops/{shop_id}/items")
        found3 = next((x for x in rget3.json() if x.get("id") == item_id), None)
        assert found3 is not None
        assert found3.get("auto_restock") is True
        assert found3.get("restock_target") == 12

        # Cleanup
        admin_client.delete(f"{BASE_URL}/api/items/{item_id}")
