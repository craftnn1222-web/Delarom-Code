"""End-to-end backend tests for Phase 3 — Ballads, Family, Memorial Hall.

The ballad-commission test is gated on EMERGENT_LLM_KEY availability — it
calls a real LLM. Family + memorial tests are deterministic.
"""
import os
import sys
import time

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"


def _load_backend_url():
    global BACKEND_URL
    if BACKEND_URL != "http://localhost:8001":
        return
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND_URL = line.strip().split("=", 1)[1]
                    return
    except FileNotFoundError:
        pass


_load_backend_url()
API_BASE = f"{BACKEND_URL}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": "craftnn1222@gmail.com", "password": "admin123"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def fixture_user(admin_token):
    """Register, approve, log in, and create a single character. Returns
    {token, character_id, user_id}."""
    suffix = int(time.time() * 1000)
    email = f"p3user_{suffix}@delarom.com"
    username = f"P3User_{suffix}"

    reg = httpx.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": "password123", "application_text": "Phase 3 e2e."},
        timeout=10,
    )
    reg.raise_for_status()
    user_id = reg.json()["user"]["id"]

    httpx.post(
        f"{API_BASE}/admin/applications/{user_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    login = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": "password123"},
        timeout=10,
    )
    token = login.json()["access_token"]

    ch = httpx.post(
        f"{API_BASE}/characters",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"P3Char_{suffix}",
            "race": "Human",
            "character_class": "Wanderer",
            "backstory": "Born under cold stars.",
            "powers": "",
            "appearance": "",
            "nation": "Ammeonon",
        },
        timeout=10,
    )
    ch.raise_for_status()
    return {"token": token, "character_id": ch.json()["id"], "user_id": user_id}


# =========================== FAMILY ===========================


class TestFamily:
    def test_add_list_update_delete(self, fixture_user):
        tok = fixture_user["token"]
        cid = fixture_user["character_id"]
        H = {"Authorization": f"Bearer {tok}"}

        # Add
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/family",
            headers=H,
            json={"name": "Aunt Marrowen", "relationship": "aunt-uncle", "status": "living", "story": "Raised me after the fire."},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        relative = r.json()
        rid = relative["id"]
        assert relative["name"] == "Aunt Marrowen"

        # List
        r = httpx.get(f"{API_BASE}/characters/{cid}/family", timeout=10)
        assert r.status_code == 200
        assert any(r_["id"] == rid for r_ in r.json())

        # Update status
        r = httpx.patch(
            f"{API_BASE}/characters/{cid}/family/{rid}",
            headers=H,
            json={"status": "deceased", "story": "Lost to plague."},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "deceased"

        # Invalid relationship
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/family",
            headers=H,
            json={"name": "Foo", "relationship": "evil-twin", "status": "living"},
            timeout=10,
        )
        assert r.status_code == 400

        # Delete
        r = httpx.delete(
            f"{API_BASE}/characters/{cid}/family/{rid}",
            headers=H,
            timeout=10,
        )
        assert r.status_code == 200
        # Verify gone
        r = httpx.get(f"{API_BASE}/characters/{cid}/family", timeout=10)
        assert not any(r_["id"] == rid for r_ in r.json())

    def test_public_can_read_family(self, fixture_user):
        """No-auth GET works — family is intentionally public lore."""
        cid = fixture_user["character_id"]
        r = httpx.get(f"{API_BASE}/characters/{cid}/family", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# =========================== MEMORIAL ===========================


class TestMemorial:
    def test_retire_moves_character_to_memorial(self, admin_token):
        # Create a separate one-shot user/character we can safely retire.
        suffix = int(time.time() * 1000)
        email = f"retire_{suffix}@delarom.com"
        reg = httpx.post(
            f"{API_BASE}/auth/register",
            json={"username": f"RetireUser_{suffix}", "email": email, "password": "password123", "application_text": "x"},
            timeout=10,
        )
        uid = reg.json()["user"]["id"]
        httpx.post(f"{API_BASE}/admin/applications/{uid}/approve",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        token = httpx.post(f"{API_BASE}/auth/login",
                           json={"email": email, "password": "password123"},
                           timeout=10).json()["access_token"]
        ch = httpx.post(
            f"{API_BASE}/characters",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": f"RetiredOne_{suffix}", "race": "Human",
                "character_class": "Wanderer", "backstory": "A drifter.",
                "powers": "", "appearance": "", "nation": "Selindori",
            },
            timeout=10,
        )
        cid = ch.json()["id"]

        # Retire
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/retire",
            headers={"Authorization": f"Bearer {token}"},
            json={"cause": "Took to the road one last time."},
            timeout=60,  # Eulogy gen
        )
        assert r.status_code == 200
        assert r.json()["died_at"]

        # Appears in /memorial
        r = httpx.get(f"{API_BASE}/memorial", timeout=10)
        assert r.status_code == 200
        assert any(c["id"] == cid for c in r.json())

        # Individual record returns eulogy + cause
        r = httpx.get(f"{API_BASE}/memorial/{cid}", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "retired"
        assert "cause_of_death" in body
        # Eulogy MAY be empty if LLM unavailable — accept either.
        assert "eulogy" in body

        # Cannot retire twice
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/retire",
            headers={"Authorization": f"Bearer {token}"},
            json={"cause": "x"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_memorial_of_living_returns_404(self, fixture_user):
        cid = fixture_user["character_id"]
        r = httpx.get(f"{API_BASE}/memorial/{cid}", timeout=10)
        assert r.status_code == 404


# =========================== BALLADS ===========================


@pytest.mark.skipif(not os.environ.get("EMERGENT_LLM_KEY"), reason="LLM key missing")
class TestBallads:
    def test_commission_then_list_then_get(self, fixture_user):
        tok = fixture_user["token"]
        cid = fixture_user["character_id"]
        r = httpx.post(
            f"{API_BASE}/ballads/commission",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "character_id": cid,
                "tone": "heroic",
                "event_summary": (
                    "The character single-handedly turned back a band of cattle-thieves "
                    "from raiding their home village at dusk, taking a wound but losing none of the herd."
                ),
                "title_hint": "The Standing at Wymroost Crossing",
                "nation": "Ammeonon",
            },
            timeout=90,
        )
        assert r.status_code == 200, r.text
        ballad = r.json()
        bid = ballad["id"]
        assert ballad["title"]
        assert ballad["body"]
        assert ballad["bard"]
        assert ballad["subject_character_id"] == cid

        # Public listing
        r = httpx.get(f"{API_BASE}/ballads", timeout=10)
        assert any(b["id"] == bid for b in r.json())

        # Single get
        r = httpx.get(f"{API_BASE}/ballads/{bid}", timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == bid

    def test_short_summary_rejected(self, fixture_user):
        tok = fixture_user["token"]
        cid = fixture_user["character_id"]
        r = httpx.post(
            f"{API_BASE}/ballads/commission",
            headers={"Authorization": f"Bearer {tok}"},
            json={"character_id": cid, "event_summary": "short", "tone": "heroic"},
            timeout=10,
        )
        assert r.status_code == 422  # min_length=10 on event_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
