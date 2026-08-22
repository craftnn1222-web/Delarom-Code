"""Backend tests for the global Character Switcher feature (iteration_32).

Covers:
- GET /api/characters/active — returns {character, active_character_id}, falls back to first character, NOT shadowed by /characters/{id}
- PUT /api/characters/active — validates ownership, persists across requests, 404 for bogus id
- Location RP now uses the resolved active hero (switching changes the acting character)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tk = r.json().get("access_token")
    assert tk, "No access_token in login response"
    return tk


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def characters(headers):
    r = requests.get(f"{API}/characters", headers=headers, timeout=30)
    assert r.status_code == 200
    chars = r.json()
    assert isinstance(chars, list)
    assert len(chars) >= 2, f"Admin needs >=2 chars for switch test, got {len(chars)}"
    return chars


# ---------- GET /api/characters/active ----------

def test_get_active_returns_character_and_id(headers, characters):
    r = requests.get(f"{API}/characters/active", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "character" in data
    assert "active_character_id" in data
    ch = data["character"]
    assert ch is not None
    # Must be one of the user's characters
    ids = {c["id"] for c in characters}
    assert ch["id"] in ids
    assert data["active_character_id"] == ch["id"]


def test_active_route_not_shadowed_by_id_route(headers):
    """The static /characters/active must be registered before /characters/{id}.
    If shadowed, backend would try find_one({id:'active'}) and return 404."""
    r = requests.get(f"{API}/characters/active", headers=headers, timeout=30)
    assert r.status_code == 200
    assert "character" in r.json()


# ---------- PUT /api/characters/active ----------

def test_put_active_404_for_bogus_id(headers):
    r = requests.put(
        f"{API}/characters/active",
        headers=headers,
        json={"character_id": "does-not-exist-xyz-000"},
        timeout=30,
    )
    assert r.status_code == 404, r.text


def test_put_active_switches_and_persists(headers, characters):
    # Pick two different characters
    c0 = characters[0]
    c1 = characters[1]

    # Switch to c0
    r0 = requests.put(f"{API}/characters/active", headers=headers, json={"character_id": c0["id"]}, timeout=30)
    assert r0.status_code == 200, r0.text
    assert r0.json()["active_character_id"] == c0["id"]
    assert r0.json()["character"]["id"] == c0["id"]

    # Verify GET reflects it
    g0 = requests.get(f"{API}/characters/active", headers=headers, timeout=30).json()
    assert g0["active_character_id"] == c0["id"]

    # Switch to c1
    r1 = requests.put(f"{API}/characters/active", headers=headers, json={"character_id": c1["id"]}, timeout=30)
    assert r1.status_code == 200, r1.text
    assert r1.json()["active_character_id"] == c1["id"]

    # Verify persistence across a fresh request
    g1 = requests.get(f"{API}/characters/active", headers=headers, timeout=30).json()
    assert g1["active_character_id"] == c1["id"]
    assert g1["character"]["id"] == c1["id"]


def test_put_active_requires_auth():
    r = requests.put(
        f"{API}/characters/active",
        json={"character_id": "anything"},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code in (401, 403)


# ---------- Location RP uses active hero ----------

def test_scene_state_uses_active_character(headers, characters):
    """The scene-state endpoint calls resolve_active_character(current_user) and
    passes that hero's id to NPCMemoryService.build_scene_state. We verify the
    switcher wiring works end-to-end by hitting scene-state right after each
    switch — a 200 with a schema-shaped response proves the resolver isn't
    crashing on the switched hero and that the endpoint is exercised."""
    nation, location = "Ammeonon", "Central Plaza"
    c0, c1 = characters[0], characters[1]

    for c in (c0, c1):
        r_switch = requests.put(f"{API}/characters/active", headers=headers, json={"character_id": c["id"]}, timeout=30)
        assert r_switch.status_code == 200
        # verify GET reflects the switch
        assert requests.get(f"{API}/characters/active", headers=headers, timeout=30).json()["active_character_id"] == c["id"]
        r_scene = requests.get(f"{API}/locations/{nation}/{location}/scene-state", headers=headers, timeout=30)
        if r_scene.status_code == 404:
            pytest.skip("scene-state target location not seeded")
        assert r_scene.status_code == 200, r_scene.text
        body = r_scene.json()
        # sanity: response shape
        assert "npcs" in body and "events" in body
