"""Live API smoke tests for the Economy endpoints.

Hits the public ingress (REACT_APP_BACKEND_URL) so we exercise routing as
well as the service layer. Read-only/admin flows only — does NOT mutate
faction specialties beyond ensuring the catalogue is seeded.
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env at runtime
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    }, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_session(session, admin_token):
    session.headers["Authorization"] = f"Bearer {admin_token}"
    return session


def test_seed_catalogue_idempotent(admin_session):
    """First call may insert; subsequent call must skip 25."""
    r1 = admin_session.post(f"{BASE_URL}/api/economy/admin/seed-catalogue", timeout=20)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    # Response envelope: {"goods": {"inserted":N,"skipped":M}, "specialties": {...}}
    assert "goods" in body1 and "specialties" in body1
    assert "inserted" in body1["goods"] and "skipped" in body1["goods"]

    r2 = admin_session.post(f"{BASE_URL}/api/economy/admin/seed-catalogue", timeout=20)
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["goods"]["inserted"] == 0
    assert body2["goods"]["skipped"] == 25


def test_goods_catalogue_returns_25(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/economy/goods", timeout=15)
    assert r.status_code == 200
    goods = r.json()
    assert isinstance(goods, list)
    assert len(goods) == 25
    sample = goods[0]
    for k in ("slug", "name", "category", "unit", "default_base_cost"):
        assert k in sample, f"missing {k} in {sample}"


def test_forgemasters_specialties(admin_session):
    r = admin_session.get(
        f"{BASE_URL}/api/economy/factions/forgemasters-guild/specialties",
        timeout=15,
    )
    assert r.status_code == 200
    body = r.json()
    # Envelope: {"faction": {...}, "specialties": [...]}
    assert "faction" in body and "specialties" in body
    specs = body["specialties"]
    assert isinstance(specs, list)
    assert len(specs) >= 5
    # Decoration check
    s = specs[0]
    assert "good_name" in s
    assert "good_category" in s
    assert "good_unit" in s


def test_top_movers_endpoint(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/economy/top-movers", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_broken_routes_endpoint(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/economy/broken-routes", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_contract_rejects_non_produced_good(admin_session):
    """Forgemasters does NOT produce spiced-wine → expect 400."""
    payload = {
        "from_faction_slug": "forgemasters-guild",
        "to_type": "city",
        "to_city_slug": "astra-lun",
        "to_nation": "aigraels",
        "good_slug": "spiced-wine",
        "tariff_pct": 25,
        "quantity_per_tick": 10,
    }
    r = admin_session.post(
        f"{BASE_URL}/api/economy/admin/contracts",
        json=payload,
        timeout=15,
    )
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


def test_leader_specialty_endpoint_requires_auth():
    """No auth → should be rejected (401 or 403)."""
    r = requests.post(
        f"{BASE_URL}/api/economy/factions/fantasy-map-dev/specialties",
        json={
            "faction_slug": "fantasy-map-dev",
            "good_slug": "iron-ingots",
            "base_cost": 100,
            "capacity": 10,
        },
        timeout=15,
    )
    assert r.status_code in (401, 403), f"got {r.status_code}: {r.text[:200]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
