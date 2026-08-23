"""Iteration 39 — Custom Faction Offerings + Two-way Commerce (Buy Offers).

Covers:
- POST /economy/factions/{slug}/offerings/custom (leader/admin only)
- POST /shops/{id}/treasury/deposit + /withdraw + guards
- POST /shops/{id}/buy-offers (player propose)
- GET /shops/{id}/buy-offers (owner list)
- POST /shops/{id}/buy-offers/{oid}/accept  (treasury-first, then owner gold)
- POST /shops/{id}/buy-offers/{oid}/decline
- GET /buy-offers/mine  (seller sees own)
- Cross-shop 403 authorization
"""
import os
import uuid
import requests
import pytest

def _read_env(key: str) -> str:
    v = os.environ.get(key)
    if v:
        return v
    for path in ("/app/frontend/.env", "/app/mobile/.env"):
        try:
            with open(path) as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip().strip('"')
        except FileNotFoundError:
            pass
    raise RuntimeError(f"{key} not set")

BASE = _read_env("REACT_APP_BACKEND_URL").rstrip("/") + "/api"

ADMIN = {"email": "craftnn1222@gmail.com", "password": "admin123"}
PLAYER = {"email": "rep_tester_round2@delarom.com", "password": "Testpass123!"}
ADMIN_SHOP_ID = "41fc2225-2fbc-4be9-abce-8ae1e166a37c"
FACTION_SLUG = "silverkeep-guild"  # will fall back if absent


def _login(creds):
    r = requests.post(f"{BASE}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="session")
def player_token():
    return _login(PLAYER)


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def player_headers(player_token):
    return {"Authorization": f"Bearer {player_token}"}


@pytest.fixture(scope="session")
def any_faction_slug(admin_headers):
    r = requests.get(f"{BASE}/factions", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    facs = r.json()
    assert facs, "no factions"
    return facs[0]["slug"]


# ── Feature 1: Custom offerings ─────────────────────────────────────

class TestCustomOfferings:
    def test_admin_can_coin_custom_offering(self, admin_headers, any_faction_slug):
        name = f"TEST_Custom_{uuid.uuid4().hex[:6]}"
        payload = {"name": name, "category": "custom", "unit": "per crate",
                   "base_cost": 42, "capacity": 25, "description": "TEST"}
        r = requests.post(
            f"{BASE}/economy/factions/{any_faction_slug}/offerings/custom",
            json=payload, headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "good" in body and "specialty" in body
        good = body["good"]
        assert good["name"] == name
        assert good.get("is_custom") is True
        assert good["default_base_cost"] == 42
        slug = good["slug"]
        # Appears in catalogue
        r2 = requests.get(f"{BASE}/economy/goods/{slug}", timeout=15)
        assert r2.status_code == 200
        # Appears in faction specialties
        r3 = requests.get(
            f"{BASE}/economy/factions/{any_faction_slug}/specialties", timeout=15)
        assert r3.status_code == 200
        specs = r3.json().get("specialties", [])
        assert any(s.get("good_slug") == slug for s in specs)

    def test_non_leader_non_admin_forbidden(self, player_headers, any_faction_slug):
        payload = {"name": f"TEST_Denied_{uuid.uuid4().hex[:6]}", "base_cost": 10}
        r = requests.post(
            f"{BASE}/economy/factions/{any_faction_slug}/offerings/custom",
            json=payload, headers=player_headers, timeout=15)
        assert r.status_code == 403, r.text


# ── Feature 2: Treasury deposit / withdraw ──────────────────────────

class TestTreasury:
    def test_deposit_then_withdraw_roundtrip(self, admin_headers):
        r0 = requests.get(f"{BASE}/shops/{ADMIN_SHOP_ID}", headers=admin_headers,
                          timeout=15)
        assert r0.status_code == 200
        t0 = int(r0.json().get("treasury", 0))
        # deposit
        d = requests.post(f"{BASE}/shops/{ADMIN_SHOP_ID}/treasury/deposit",
                         json={"amount": 5}, headers=admin_headers, timeout=15)
        assert d.status_code == 200, d.text
        assert d.json()["treasury"] == t0 + 5
        # withdraw
        w = requests.post(f"{BASE}/shops/{ADMIN_SHOP_ID}/treasury/withdraw",
                         json={"amount": 5}, headers=admin_headers, timeout=15)
        assert w.status_code == 200
        assert w.json()["treasury"] == t0

    def test_deposit_zero_amount_400(self, admin_headers):
        r = requests.post(f"{BASE}/shops/{ADMIN_SHOP_ID}/treasury/deposit",
                          json={"amount": 0}, headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_withdraw_more_than_treasury_400(self, admin_headers):
        r = requests.post(f"{BASE}/shops/{ADMIN_SHOP_ID}/treasury/withdraw",
                          json={"amount": 99999999}, headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_non_owner_cannot_deposit(self, player_headers):
        r = requests.post(f"{BASE}/shops/{ADMIN_SHOP_ID}/treasury/deposit",
                          json={"amount": 1}, headers=player_headers, timeout=15)
        assert r.status_code == 403


# ── Feature 3: Buy offers ────────────────────────────────────────────

class TestBuyOffers:
    def test_owner_lists_offers(self, admin_headers):
        r = requests.get(f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "treasury" in body and "offers" in body
        assert isinstance(body["offers"], list)

    def test_non_owner_list_forbidden(self, player_headers):
        r = requests.get(f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
                         headers=player_headers, timeout=15)
        assert r.status_code == 403

    def test_owner_cannot_sell_to_own_shop(self, admin_headers):
        # admin's char
        r = requests.get(f"{BASE}/characters", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        chars = r.json()
        if not chars:
            pytest.skip("admin has no character")
        cid = chars[0]["id"]
        r2 = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
            json={"character_id": cid, "inventory_item_id": "whatever",
                  "proposed_price": 10}, headers=admin_headers, timeout=15)
        assert r2.status_code == 400
        assert "own shop" in r2.text.lower()

    def test_player_propose_and_owner_accepts(self, admin_headers, player_headers):
        # Fetch player's characters
        rc = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
        assert rc.status_code == 200
        chars = rc.json()
        assert chars, "player has no character"
        char = chars[0]
        cid = char["id"]
        # Ensure an inventory item exists — buy one if empty
        inv = char.get("inventory") or []
        if not inv:
            # find a cheap item in the admin shop
            items = requests.get(f"{BASE}/shops/{ADMIN_SHOP_ID}/items",
                                 timeout=15).json()
            items = [i for i in items if i.get("stock", 0) > 0]
            if not items:
                pytest.skip("no items in admin shop to buy for seed")
            item = min(items, key=lambda i: i.get("price", 999999))
            # ensure player has gold
            requests.post(f"{BASE}/admin/users/grant-currency",
                          json={"user_email": PLAYER["email"], "amount": 5000},
                          headers=admin_headers, timeout=15)  # may 404 — ignore
            pr = requests.post(f"{BASE}/items/{item['id']}/purchase",
                               json={"character_id": cid},
                               headers=player_headers, timeout=15)
            if pr.status_code != 200:
                pytest.skip(f"could not seed inventory: {pr.status_code} {pr.text}")
            # refetch
            rc = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
            char = [c for c in rc.json() if c["id"] == cid][0]
            inv = char.get("inventory") or []
        assert inv, "still no inventory"
        inv_item = inv[0]

        # Create offer
        offer_price = 3  # small so treasury (200g) covers it
        cr = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
            json={"character_id": cid, "inventory_item_id": inv_item["id"],
                  "proposed_price": offer_price},
            headers=player_headers, timeout=15)
        assert cr.status_code == 200, cr.text
        offer_id = cr.json()["id"]
        assert cr.json()["status"] == "pending"

        # Seller sees it in /buy-offers/mine
        mine = requests.get(f"{BASE}/buy-offers/mine",
                            headers=player_headers, timeout=15).json()
        assert any(o["id"] == offer_id for o in mine)

        # Owner sees it in list
        lst = requests.get(f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
                           headers=admin_headers, timeout=15).json()
        assert any(o["id"] == offer_id for o in lst["offers"])
        treas_before = lst["treasury"]

        # Non-owner cannot accept
        na = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers/{offer_id}/accept",
            headers=player_headers, timeout=15)
        assert na.status_code == 403

        # Owner accepts
        acc = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers/{offer_id}/accept",
            headers=admin_headers, timeout=20)
        assert acc.status_code == 200, acc.text
        aj = acc.json()
        assert aj["ok"] is True
        assert aj["paid_from"] in ("treasury", "owner")
        # If treasury had enough, should be paid from treasury
        if treas_before >= offer_price:
            assert aj["paid_from"] == "treasury"
        assert aj["resale_price"] >= offer_price + 1

        # Double-accept blocked
        acc2 = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers/{offer_id}/accept",
            headers=admin_headers, timeout=15)
        assert acc2.status_code == 400

        # Seller's inventory no longer has the item
        rc2 = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
        char2 = [c for c in rc2.json() if c["id"] == cid][0]
        assert not any(i["id"] == inv_item["id"] for i in (char2.get("inventory") or []))

    def test_decline_offer(self, admin_headers, player_headers):
        # Create tiny offer using any inventory item; if none, skip
        rc = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
        char = rc.json()[0]
        inv = char.get("inventory") or []
        if not inv:
            pytest.skip("no inventory to decline-test")
        cr = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
            json={"character_id": char["id"], "inventory_item_id": inv[0]["id"],
                  "proposed_price": 1},
            headers=player_headers, timeout=15)
        assert cr.status_code == 200
        oid = cr.json()["id"]
        # Non-owner cannot decline
        nd = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers/{oid}/decline",
            headers=player_headers, timeout=15)
        assert nd.status_code == 403
        # Owner declines
        d = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers/{oid}/decline",
            headers=admin_headers, timeout=15)
        assert d.status_code == 200

    def test_price_must_be_positive(self, player_headers):
        rc = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
        char = rc.json()[0]
        inv = char.get("inventory") or []
        item_id = inv[0]["id"] if inv else "does-not-matter"
        r = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
            json={"character_id": char["id"], "inventory_item_id": item_id,
                  "proposed_price": 0},
            headers=player_headers, timeout=15)
        # positive check happens before inventory check
        assert r.status_code == 400

    def test_item_not_in_inventory_404(self, player_headers):
        rc = requests.get(f"{BASE}/characters", headers=player_headers, timeout=15)
        char = rc.json()[0]
        r = requests.post(
            f"{BASE}/shops/{ADMIN_SHOP_ID}/buy-offers",
            json={"character_id": char["id"],
                  "inventory_item_id": "nonexistent-id",
                  "proposed_price": 5},
            headers=player_headers, timeout=15)
        assert r.status_code == 404
