"""Phase A — Visibility endpoint tests.

Covers:
- GET /api/characters/{id}/faction (single lookup)
- POST /api/characters/factions/batch (batched lookup)
- GET /api/factions/{slug}/npcs (NPC roster - public)
- GET /api/factions/charter/mine (cookie auth)
- GET /api/admin/factions/charters?status=... (admin auth)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_character_id(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/characters", timeout=15)
    assert r.status_code == 200
    chars = r.json()
    assert isinstance(chars, list) and len(chars) > 0
    return chars[0]["id"]


# --- /characters/{id}/faction ---------------------------------------------

class TestCharacterFactionLookup:
    def test_single_character_returns_dict_or_null(self, admin_session, admin_character_id):
        r = admin_session.get(
            f"{BASE_URL}/api/characters/{admin_character_id}/faction", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # Either null or has the documented shape
        if data is not None:
            for key in ("faction_name", "faction_slug", "icon", "color_hex", "rank"):
                assert key in data, f"missing {key} in {data}"

    def test_unknown_character_returns_null(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/characters/does-not-exist/faction", timeout=15)
        # Either 200/null or 404 acceptable
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json() is None


# --- /characters/factions/batch -------------------------------------------

class TestBatchFactionLookup:
    def test_batch_returns_dict_keyed_by_id(self, admin_session, admin_character_id):
        r = admin_session.post(
            f"{BASE_URL}/api/characters/factions/batch",
            json={"character_ids": [admin_character_id, "missing-id-xyz"]},
            timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        # Should contain a key per id (value may be null)
        assert admin_character_id in data

    def test_batch_empty_list(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/characters/factions/batch",
            json={"character_ids": []},
            timeout=15)
        assert r.status_code == 200
        assert r.json() == {}


# --- /factions/{slug}/npcs ------------------------------------------------

class TestFactionNpcsRoster:
    def test_npcs_endpoint_returns_list(self):
        # Use a known starter faction slug
        r = requests.get(f"{BASE_URL}/api/factions/forgemasters-guild/npcs", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_npcs_endpoint_unknown_slug_returns_empty_or_404(self):
        r = requests.get(f"{BASE_URL}/api/factions/no-such-faction-xyz/npcs", timeout=15)
        assert r.status_code in (200, 404)


# --- /factions/charter/mine -----------------------------------------------

class TestCharterMine:
    def test_charter_mine_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/factions/charter/mine", timeout=15)
        assert r.status_code in (401, 403)

    def test_charter_mine_admin_returns_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/factions/charter/mine", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# --- /admin/factions/charters ---------------------------------------------

class TestAdminCharters:
    def test_admin_charters_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/factions/charters", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_charters_pending(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/admin/factions/charters?status=pending", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_charters_all(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/admin/factions/charters?status=all", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
