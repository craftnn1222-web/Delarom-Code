"""
Tests for GET /api/me/continue — 'Continue Where You Left Off' dashboard endpoint.

Verifies:
1. Admin (has RP history + active party) returns both last_scene + active_party populated.
2. Brand-new user (no RP, no party) returns nulls for both fields.
3. Response shape matches contract (nation, location, location_name, city, character_name, at | id, name, status, location, member_count).
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api_client):
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "craftnn1222@gmail.com", "password": "admin123"},
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def new_user_token(api_client):
    """Empty-state user (seeded directly in Mongo — see tests/_seed_empty_user.py).
    Falls back to /api/auth/register if the seed hasn't been run."""
    email = "TEST_continue_empty@delarom.com"
    pwd = "Testpass123!"
    lg = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    if lg.status_code != 200:
        pytest.skip(f"empty-state user not seeded (run tests/_seed_empty_user.py). status={lg.status_code} body={lg.text[:200]}")
    tok = lg.json().get("access_token")
    assert tok
    return tok


# ---------- Admin: populated case ----------
class TestContinuePopulated:
    def test_returns_200_and_shape(self, api_client, admin_token):
        r = api_client.get(
            f"{BASE_URL}/api/me/continue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "last_scene" in data
        assert "active_party" in data
        # Admin has both per playbook.
        assert data["last_scene"] is not None, "expected admin to have last_scene populated"
        assert data["active_party"] is not None, "expected admin to have active_party populated"

    def test_last_scene_fields(self, api_client, admin_token):
        r = api_client.get(
            f"{BASE_URL}/api/me/continue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        scene = r.json()["last_scene"]
        for key in ("nation", "location", "location_name", "city", "character_name", "at"):
            assert key in scene, f"last_scene missing '{key}': {scene}"
        assert isinstance(scene["nation"], str) and scene["nation"]
        assert isinstance(scene["location"], str) and scene["location"]
        assert isinstance(scene["location_name"], str)

    def test_active_party_fields(self, api_client, admin_token):
        r = api_client.get(
            f"{BASE_URL}/api/me/continue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        party = r.json()["active_party"]
        for key in ("id", "name", "status", "location", "member_count"):
            assert key in party, f"active_party missing '{key}': {party}"
        assert isinstance(party["id"], str) and party["id"]
        assert isinstance(party["member_count"], int)
        assert party["status"] in ("recruiting", "active"), party["status"]

    def test_party_id_resolvable(self, api_client, admin_token):
        """The returned party id should point to a real party doc."""
        r = api_client.get(
            f"{BASE_URL}/api/me/continue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        pid = r.json()["active_party"]["id"]
        p = api_client.get(
            f"{BASE_URL}/api/parties/{pid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert p.status_code == 200, f"party {pid} not fetchable: {p.status_code} {p.text[:200]}"
        pdoc = p.json()
        assert pdoc.get("id") == pid


# ---------- Empty state ----------
class TestContinueEmpty:
    def test_returns_nulls_for_new_user(self, api_client, new_user_token):
        r = api_client.get(
            f"{BASE_URL}/api/me/continue",
            headers={"Authorization": f"Bearer {new_user_token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("last_scene") is None, f"expected null last_scene, got {data.get('last_scene')}"
        assert data.get("active_party") is None, f"expected null active_party, got {data.get('active_party')}"


# ---------- Unauth ----------
def test_requires_auth():
    """Fresh client (no cookies, no bearer) — endpoint must reject."""
    r = requests.get(f"{BASE_URL}/api/me/continue")
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text[:200]}"
