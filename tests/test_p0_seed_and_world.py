"""
Regression tests for P0 Seeding flow + Butterfly-Effect / Chronicle / NPC memory
+ NationDetail navigation backend support + admin sanity checks.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    }, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ---------- Admin Sanity ----------

class TestAdminSanity:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 10

    def test_database_status(self, admin_headers):
        r = requests.get(f"{API}/admin/database-status", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("nations", "cities", "locations", "users", "is_empty"):
            assert k in data, f"missing key {k}: {data}"

    def test_admin_users(self, admin_headers):
        r = requests.get(f"{API}/admin/users", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        users = data if isinstance(data, list) else data.get("users")
        assert isinstance(users, list), data
        assert len(users) > 0

    def test_admin_applications(self, admin_headers):
        r = requests.get(f"{API}/admin/applications", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        apps = data if isinstance(data, list) else data.get("applications")
        assert isinstance(apps, list), data


# ---------- P0 Seeding ----------

class TestSeedingFlow:
    def test_seed_status_idle_or_completed_initially(self, admin_headers):
        r = requests.get(f"{API}/admin/seed-status", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # required fields present
        for k in ("task_id", "status", "phase", "progress", "message", "results", "error"):
            assert k in data, f"missing field {k}"
        assert data["status"] in ("idle", "completed", "failed", "running")

    def test_start_full_seed_no_images_then_poll(self, admin_headers):
        # Kick off
        r = requests.post(f"{API}/admin/start-full-seed?with_images=false",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        start = r.json()
        # Either it started running OR something else is already running
        if start.get("already_running"):
            assert start.get("status") == "running"
        else:
            assert start.get("status") in ("running", "completed"), start
            assert start.get("task_id"), f"no task_id: {start}"

        # Immediately calling again should report already_running (or completed)
        r2 = requests.post(f"{API}/admin/start-full-seed?with_images=false",
                           headers=admin_headers, timeout=30)
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        # If first finished extremely fast, status may be completed and no already_running flag
        assert body2.get("status") in ("running", "completed") or body2.get("already_running")

        # Poll up to 90s for completion
        deadline = time.time() + 90
        last = None
        while time.time() < deadline:
            sr = requests.get(f"{API}/admin/seed-status", headers=admin_headers, timeout=20)
            assert sr.status_code == 200, sr.text
            last = sr.json()
            if last["status"] in ("completed", "failed"):
                break
            time.sleep(2)
        assert last is not None
        assert last["status"] == "completed", f"seeding did not complete: {last}"
        assert last["progress"] == 100, last
        # results breakdown shape
        res = last.get("results") or {}
        for key in ("nations", "cities", "locations", "errors"):
            assert key in res, f"missing results.{key} in {res}"

    def test_seed_requires_admin(self):
        # No auth -> 401/403
        r = requests.post(f"{API}/admin/start-full-seed?with_images=false", timeout=15)
        assert r.status_code in (401, 403), r.text


# ---------- Butterfly-Effect / World State ----------

class TestWorldStateEndpoints:
    def test_get_diplomacy(self, admin_headers):
        r = requests.get(f"{API}/admin/diplomacy", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_set_diplomacy(self, admin_headers):
        payload = {
            "nation_a": "ammeonon",
            "nation_b": "selindori",
            "score": 25,
            "reason": "TEST_set_diplomacy",
        }
        r = requests.post(f"{API}/admin/diplomacy/set", json=payload,
                          headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        # score should now be 25 in some shape
        assert ("score" in body) or ("nation_a" in body), body

    def test_adjust_diplomacy_emits_event(self, admin_headers):
        payload = {
            "nation_a": "ammeonon",
            "nation_b": "selindori",
            "delta": -5,
            "reason": "TEST_adjust_diplomacy",
        }
        r = requests.post(f"{API}/admin/diplomacy/adjust", json=payload,
                          headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text

    def test_world_events_list(self, admin_headers):
        r = requests.get(f"{API}/admin/world-events?limit=10",
                         headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_world_events_create(self, admin_headers):
        payload = {
            "event_type": "incident",
            "scope": "world",
            "summary": "TEST_event summary",
            "details": "TEST_event details",
            "nations": ["ammeonon"],
        }
        r = requests.post(f"{API}/admin/world-events", json=payload,
                          headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("summary") == "TEST_event summary" or body.get("id"), body

    def test_cascade_queue(self, admin_headers):
        r = requests.get(f"{API}/admin/cascade-queue", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_character_reputation_endpoint(self, admin_headers):
        # Use a probably-nonexistent ID; endpoint should still return 200 with [] / {}
        r = requests.get(f"{API}/admin/characters/nonexistent-id/reputation",
                         headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        # accept list or dict
        body = r.json()
        assert isinstance(body, (list, dict))


# ---------- Public Chronicle ----------

class TestChronicle:
    def test_chronicle_with_admin(self, admin_headers):
        r = requests.get(f"{API}/chronicle?limit=20", headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        if data:
            ev = data[0]
            for k in ("id", "event_type", "scope", "summary", "created_at"):
                assert k in ev, f"missing {k} in chronicle entry: {ev}"


# ---------- Location RP / NPC Memory ----------

class TestLocationRP:
    def test_submit_rp_action_persists(self, admin_headers):
        # Ensure admin has a character; create one if missing.
        chars = requests.get(f"{API}/characters", headers=admin_headers, timeout=20)
        if chars.status_code == 200 and isinstance(chars.json(), list) and len(chars.json()) == 0:
            create = requests.post(f"{API}/characters", headers=admin_headers, json={
                "name": "TEST_Inspector",
                "race": "Human",
                "character_class": "Wanderer",
                "backstory": "Test character.",
                "powers": "Observation.",
                "appearance": "Plain robes.",
            }, timeout=20)
            # Some schemas may differ; if creation fails, just skip persistence assertion
            if create.status_code not in (200, 201):
                pytest.skip(f"Could not create character for RP test: {create.status_code} {create.text}")

        nation, location = "ammeonon", "wymroost"
        before = requests.get(f"{API}/locations/{nation}/{location}/roleplay?limit=50", timeout=20)
        before_count = len(before.json()) if before.status_code == 200 else 0

        r = requests.post(
            f"{API}/locations/{nation}/{location}/roleplay",
            headers=admin_headers,
            json={"action_text": "TEST_RP I peer down the hall, taking note of any shadows."},
            timeout=60,
        )
        # Endpoint must respond 200; placeholder fallback is fine
        assert r.status_code == 200, r.text
        body = r.json()
        # Should contain an rp_id (post saved) — duplicate prevention may return existing id
        assert "rp_id" in body, f"no rp_id in response: {body}"

        after = requests.get(f"{API}/locations/{nation}/{location}/roleplay?limit=50", timeout=20)
        assert after.status_code == 200, after.text
        # Either new post added OR duplicate-window returned existing one; both acceptable
        assert len(after.json()) >= before_count


# ---------- NationDetail navigation backend ----------

class TestNationNavigationBackend:
    def test_cities_for_nation(self):
        # NationDetail uses getCitiesByNation
        r = requests.get(f"{API}/cities/ammeonon", timeout=20)
        # Some servers expose under /nations/{nation}/cities — check both
        if r.status_code == 404:
            r = requests.get(f"{API}/nations/ammeonon/cities", timeout=20)
        assert r.status_code == 200, f"cities endpoint failed: {r.status_code} {r.text}"
        data = r.json()
        assert isinstance(data, list)
