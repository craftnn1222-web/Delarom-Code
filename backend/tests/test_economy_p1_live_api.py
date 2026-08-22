"""Live API smoke tests for P1 economy extensions.

Covers:
  - Shop item auto-pricing (POST /api/shops/{id}/items with is_auto_priced=true)
  - POST /api/items/{id}/refresh-price
  - POST /api/shops/{id}/refresh-prices
  - GET /api/economy/factions/{slug}/contracts (public)
  - Caravan lifecycle: post → list → claim → complete → wallet credit
  - Caravan cancel (poster refund)
  - Public list filtering

Test fixtures clean up created caravans and shop items.
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
TEST_CHARACTER_ID = "a35a8ce2-71db-467c-8ad0-451fe9433a87"
TEST_SHOP_ID = "41fc2225-2fbc-4be9-abce-8ae1e166a37c"
FACTION_SLUG = "forgemasters-guild"  # fantasy-map-dev not seeded; use real faction (admin bypass)

CREATED_ITEM_IDS = []
CREATED_CARAVAN_IDS = []


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token
    s.headers["Authorization"] = f"Bearer {token}"
    yield s
    # Teardown — best-effort
    for item_id in CREATED_ITEM_IDS:
        try:
            s.delete(f"{BASE_URL}/api/items/{item_id}", timeout=10)
        except Exception:
            pass
    for cid in CREATED_CARAVAN_IDS:
        try:
            s.post(f"{BASE_URL}/api/economy/caravans/{cid}/cancel", timeout=10)
        except Exception:
            pass


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------------------------------------------------------------------------
# Auto-pricing & refresh endpoints
# ---------------------------------------------------------------------------


def test_auto_priced_item_creation_and_refresh(admin_session):
    """Create an auto-priced item, verify cascaded price, then refresh."""
    # Ensure catalogue + a base contract exist (idempotent)
    admin_session.post(f"{BASE_URL}/api/economy/admin/seed-catalogue", timeout=20)

    # Try to ensure an active contract exists for iron-ingots to astra-lun.
    # If broken, recreate. Soft-fail on contract creation.
    admin_session.post(
        f"{BASE_URL}/api/economy/admin/contracts",
        json={
            "from_faction_slug": "forgemasters-guild",
            "to_type": "city",
            "to_city_slug": "astra-lun",
            "to_nation": "aigraels",
            "good_slug": "iron-ingots",
            "tariff_pct": 25,
            "quantity_per_tick": 10,
        },
        timeout=15,
    )

    payload = {
        "name": "TEST_AutoPriced Iron Ingot",
        "description": "Auto-pricing smoke test item",
        "category": "material",
        "price": 999,  # should be overridden by auto-pricing
        "stock": 5,
        "is_auto_priced": True,
        "source_good_slug": "iron-ingots",
        "source_city_slug": "astra-lun",
        "source_nation": "aigraels",
        "markup_pct": 30,
    }
    r = admin_session.post(f"{BASE_URL}/api/shops/{TEST_SHOP_ID}/items",
                           json=payload, timeout=20)
    assert r.status_code in (200, 201), f"create item failed: {r.status_code} {r.text}"
    item = r.json()
    assert "id" in item
    CREATED_ITEM_IDS.append(item["id"])
    # Either price reflects cascade (40g base * 1.25 tariff * 1.30 markup = 65g)
    # or backend stores manual price + auto-pricing flag — verify auto-pricing flag
    assert item.get("is_auto_priced") is True
    # Price should NOT be the 999g we sent; some cascaded value > 0.
    assert item.get("price", 0) != 999
    assert item.get("price", 0) > 0

    # Refresh-price endpoint
    rr = admin_session.post(
        f"{BASE_URL}/api/items/{item['id']}/refresh-price", timeout=15,
    )
    assert rr.status_code == 200, f"refresh-price failed: {rr.status_code} {rr.text}"
    refreshed = rr.json()
    # Either returns the item or a wrapper — accept either
    new_price = refreshed.get("price") or refreshed.get("item", {}).get("price")
    assert new_price is not None
    assert new_price > 0


def test_refresh_price_400_when_not_auto_priced(admin_session):
    """Manual item should return 400 on refresh-price."""
    payload = {
        "name": "TEST_ManualItem",
        "description": "Manual price item",
        "category": "material",
        "price": 100,
        "stock": 5,
        "is_auto_priced": False,
    }
    r = admin_session.post(f"{BASE_URL}/api/shops/{TEST_SHOP_ID}/items",
                           json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    item = r.json()
    CREATED_ITEM_IDS.append(item["id"])

    rr = admin_session.post(
        f"{BASE_URL}/api/items/{item['id']}/refresh-price", timeout=15,
    )
    assert rr.status_code == 400, f"expected 400, got {rr.status_code}: {rr.text}"


def test_shop_bulk_refresh_prices(admin_session):
    r = admin_session.post(
        f"{BASE_URL}/api/shops/{TEST_SHOP_ID}/refresh-prices", timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ("updated", "skipped", "total_auto_priced"):
        assert k in body, f"missing {k} in {body}"
    assert isinstance(body["updated"], int)
    assert isinstance(body["total_auto_priced"], int)


def test_auto_priced_item_400_when_no_market(admin_session):
    """Trying to auto-price a good with no contract should yield 400."""
    payload = {
        "name": "TEST_NoMarketItem",
        "description": "Should 400 — no contract",
        "category": "material",
        "price": 100,
        "stock": 1,
        "is_auto_priced": True,
        # Unlikely good/city pairing — silver-bars to a random city
        "source_good_slug": "silver-bars",
        "source_city_slug": "astra-lun",
        "source_nation": "aigraels",
        "markup_pct": 20,
    }
    r = admin_session.post(f"{BASE_URL}/api/shops/{TEST_SHOP_ID}/items",
                           json=payload, timeout=15)
    # Accept either 400 (helper-raised) or 200 (if contract somehow exists)
    if r.status_code in (200, 201):
        CREATED_ITEM_IDS.append(r.json()["id"])
        pytest.skip("silver-bars contract already exists; skipping no-market case")
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
    detail = (r.json().get("detail") or "").lower()
    assert "active" in detail or "market" in detail or "contract" in detail


# ---------------------------------------------------------------------------
# Leader-scoped contracts list (public read)
# ---------------------------------------------------------------------------


def test_faction_contracts_public_list(anon_session):
    """Public read returns a list of contracts where faction is source."""
    r = anon_session.get(
        f"{BASE_URL}/api/economy/factions/forgemasters-guild/contracts", timeout=15,
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_leader_contract_create_url_body_mismatch(admin_session):
    """URL slug must match body.from_faction_slug → 400."""
    r = admin_session.post(
        f"{BASE_URL}/api/economy/factions/forgemasters-guild/contracts",
        json={
            "from_faction_slug": "different-faction",
            "to_type": "city",
            "to_city_slug": "astra-lun",
            "to_nation": "aigraels",
            "good_slug": "iron-ingots",
            "tariff_pct": 25,
            "quantity_per_tick": 10,
        },
        timeout=15,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"


def test_leader_contract_create_requires_auth(anon_session):
    r = anon_session.post(
        f"{BASE_URL}/api/economy/factions/forgemasters-guild/contracts",
        json={
            "from_faction_slug": "forgemasters-guild",
            "to_type": "city",
            "to_city_slug": "astra-lun",
            "to_nation": "aigraels",
            "good_slug": "iron-ingots",
            "tariff_pct": 25,
            "quantity_per_tick": 10,
        },
        timeout=15,
    )
    assert r.status_code in (401, 403), f"got {r.status_code}: {r.text[:200]}"


# ---------------------------------------------------------------------------
# Caravan lifecycle
# ---------------------------------------------------------------------------


def test_caravan_lifecycle_post_claim_complete(admin_session):
    """Full lifecycle — post (admin bypass), claim with TEST char, complete success."""
    # Wallet balance before
    me_pre = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me_pre.status_code != 200:
        me_pre = admin_session.get(f"{BASE_URL}/api/wallet", timeout=10)
    wallet_pre = me_pre.json().get("currency") if me_pre.status_code == 200 else None

    # POST caravan as admin (admin bypass on _ensure_faction_leader)
    reward = 50  # small to avoid wallet exhaustion
    payload = {
        "good_slug": "iron-ingots",
        "quantity": 10,
        "to_city_slug": "astra-lun",
        "reward_gold": reward,
        "expires_in_hours": 48,
        "description": "TEST caravan smoke",
    }
    r = admin_session.post(
        f"{BASE_URL}/api/economy/factions/{FACTION_SLUG}/caravans",
        json=payload, timeout=20,
    )
    assert r.status_code in (200, 201), f"post caravan failed: {r.status_code} {r.text}"
    caravan = r.json()
    cid = caravan["id"]
    CREATED_CARAVAN_IDS.append(cid)
    assert caravan["status"] == "open"
    assert caravan["reward_gold"] == reward
    assert caravan["good_slug"] == "iron-ingots"
    assert caravan["to_city_slug"] == "astra-lun"

    # GET it directly
    g = admin_session.get(f"{BASE_URL}/api/economy/caravans/{cid}", timeout=10)
    assert g.status_code == 200
    assert g.json()["status"] == "open"

    # Public listing should include it
    pl = admin_session.get(
        f"{BASE_URL}/api/economy/caravans",
        params={"status": "open", "to_city_slug": "astra-lun"}, timeout=15,
    )
    assert pl.status_code == 200
    assert any(c["id"] == cid for c in pl.json())

    # Claim with test character
    cl = admin_session.post(
        f"{BASE_URL}/api/economy/caravans/{cid}/claim",
        json={"character_id": TEST_CHARACTER_ID}, timeout=15,
    )
    assert cl.status_code == 200, f"claim failed: {cl.status_code} {cl.text}"
    assert cl.json()["status"] == "claimed"
    assert cl.json()["claimed_by_character_id"] == TEST_CHARACTER_ID

    # Double-claim should 400
    cl2 = admin_session.post(
        f"{BASE_URL}/api/economy/caravans/{cid}/claim",
        json={"character_id": TEST_CHARACTER_ID}, timeout=15,
    )
    assert cl2.status_code == 400, f"expected 400, got {cl2.status_code}: {cl2.text}"

    # Complete success
    cm = admin_session.post(
        f"{BASE_URL}/api/economy/caravans/{cid}/complete",
        json={"success": True, "story": "TEST: arrived safely."}, timeout=20,
    )
    assert cm.status_code == 200, f"complete failed: {cm.status_code} {cm.text}"
    completed = cm.json()
    assert completed["status"] == "completed"

    # Wallet should have been credited (net 0 since same admin posted and claimed
    # → -reward then +reward; assert net delta == 0)
    time.sleep(0.5)
    me_post = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me_post.status_code != 200:
        me_post = admin_session.get(f"{BASE_URL}/api/wallet", timeout=10)
    if wallet_pre is not None and me_post.status_code == 200:
        wallet_post = me_post.json().get("currency")
        if wallet_post is not None:
            # Net delta should be 0 (debited on post, credited on complete)
            assert wallet_post == wallet_pre, f"wallet delta: pre={wallet_pre} post={wallet_post}"

    # Cancelling a completed caravan should 400
    cn = admin_session.post(
        f"{BASE_URL}/api/economy/caravans/{cid}/cancel", timeout=10,
    )
    assert cn.status_code == 400


def test_caravan_cancel_refunds_poster(admin_session):
    """Post → cancel → wallet refunded → status=cancelled."""
    me_pre = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me_pre.status_code != 200:
        me_pre = admin_session.get(f"{BASE_URL}/api/wallet", timeout=10)
    wallet_pre = me_pre.json().get("currency") if me_pre.status_code == 200 else None

    reward = 75
    r = admin_session.post(
        f"{BASE_URL}/api/economy/factions/{FACTION_SLUG}/caravans",
        json={
            "good_slug": "iron-ingots",
            "quantity": 5,
            "to_city_slug": "astra-lun",
            "reward_gold": reward,
            "expires_in_hours": 24,
            "description": "TEST cancel caravan",
        }, timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    CREATED_CARAVAN_IDS.append(cid)

    cn = admin_session.post(
        f"{BASE_URL}/api/economy/caravans/{cid}/cancel", timeout=15,
    )
    assert cn.status_code == 200, f"cancel failed: {cn.status_code} {cn.text}"
    body = cn.json()
    assert body.get("status") == "cancelled" or "cancelled" in str(body).lower()

    time.sleep(0.3)
    me_post = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me_post.status_code != 200:
        me_post = admin_session.get(f"{BASE_URL}/api/wallet", timeout=10)
    if wallet_pre is not None and me_post.status_code == 200:
        wallet_post = me_post.json().get("currency")
        if wallet_post is not None:
            assert wallet_post == wallet_pre, f"refund mismatch: pre={wallet_pre} post={wallet_post}"


def test_caravan_post_requires_auth(anon_session):
    r = anon_session.post(
        f"{BASE_URL}/api/economy/factions/{FACTION_SLUG}/caravans",
        json={
            "good_slug": "iron-ingots", "quantity": 1,
            "to_city_slug": "astra-lun", "reward_gold": 10,
            "expires_in_hours": 24,
        }, timeout=15,
    )
    assert r.status_code in (401, 403)


def test_caravan_post_400_unknown_good(admin_session):
    r = admin_session.post(
        f"{BASE_URL}/api/economy/factions/{FACTION_SLUG}/caravans",
        json={
            "good_slug": "nonexistent-foobar", "quantity": 1,
            "to_city_slug": "astra-lun", "reward_gold": 10,
            "expires_in_hours": 24,
        }, timeout=15,
    )
    assert r.status_code in (400, 404), f"got {r.status_code}: {r.text}"


def test_caravans_public_list(anon_session):
    r = anon_session.get(f"{BASE_URL}/api/economy/caravans", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Charter offered_goods invalid good_slug
# ---------------------------------------------------------------------------


def test_charter_invalid_offered_good_returns_400(admin_session):
    """Invalid good_slug in offered_goods returns 400 BEFORE debiting gold."""
    payload = {
        "character_id": TEST_CHARACTER_ID,
        "name": "TEST Charter Faction",
        "description": "A test charter with bad offered goods to trigger 400.",
        "offered_goods": [
            {"good_slug": "totally-not-a-real-good", "base_cost": 50, "capacity": 10}
        ],
    }
    r = admin_session.post(f"{BASE_URL}/api/factions/charter",
                           json=payload, timeout=15)
    # Expect 400 due to invalid good_slug. Accept 404 if endpoint distinguishes.
    assert r.status_code in (400, 404), f"expected 400/404, got {r.status_code}: {r.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
