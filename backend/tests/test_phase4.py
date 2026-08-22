"""End-to-end backend tests for Phase 4 — Dreams, Prophecies, Personas.

Dream + Prophecy generation hits the LLM, so those tests are gated on
EMERGENT_LLM_KEY. Persona is fully deterministic.
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
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def user_char(admin_token):
    """Fresh user + character for the test module."""
    suffix = int(time.time() * 1000)
    email = f"p4user_{suffix}@delarom.com"
    httpx.post(
        f"{API_BASE}/auth/register",
        json={"username": f"P4User_{suffix}", "email": email, "password": "password123", "application_text": "Phase 4 e2e."},
        timeout=10,
    )
    user = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": "password123"},
        timeout=10,
    )
    # Must approve via admin first
    user_id = httpx.get(
        f"{API_BASE}/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"q": email},
        timeout=10,
    )
    # Easier: get from registration response
    reg = httpx.post(
        f"{API_BASE}/auth/register",
        json={"username": f"P4User2_{suffix}", "email": f"alt_{email}", "password": "password123", "application_text": "x"},
        timeout=10,
    ).json()
    # Use this fresh user
    new_uid = reg["user"]["id"]
    httpx.post(f"{API_BASE}/admin/applications/{new_uid}/approve",
               headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
    token = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": f"alt_{email}", "password": "password123"},
        timeout=10,
    ).json()["access_token"]
    ch = httpx.post(
        f"{API_BASE}/characters",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"P4Char_{suffix}", "race": "Human", "character_class": "Wanderer",
            "backstory": "Once orphaned in Ammeonon, raised by the sea.", "powers": "",
            "appearance": "", "nation": "Ammeonon",
        },
        timeout=10,
    )
    return {"token": token, "character_id": ch.json()["id"]}


# =========================== PERSONA ===========================


class TestPersona:
    def test_full_lifecycle(self, user_char):
        tok = user_char["token"]
        cid = user_char["character_id"]
        H = {"Authorization": f"Bearer {tok}"}

        # Initially nothing
        r = httpx.get(f"{API_BASE}/characters/{cid}/persona", headers=H, timeout=10)
        assert r.status_code == 200
        assert r.json() is None

        # Toggle before declaring → 400
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/persona/toggle",
            headers=H, json={"active": True}, timeout=10,
        )
        assert r.status_code == 400

        # Upsert
        r = httpx.put(
            f"{API_BASE}/characters/{cid}/persona",
            headers=H,
            json={"name": "The Hooded Stranger", "race": "Half-Elf", "background": "A wandering apothecary."},
            timeout=10,
        )
        assert r.status_code == 200
        p = r.json()
        assert p["name"] == "The Hooded Stranger"
        assert p["active"] is False  # inactive by default

        # Toggle on
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/persona/toggle",
            headers=H, json={"active": True}, timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["active"] is True

        # Update — should preserve active state and declared_at
        r = httpx.put(
            f"{API_BASE}/characters/{cid}/persona",
            headers=H,
            json={"name": "The Hooded Stranger", "race": "Half-Elf", "background": "Updated cover."},
            timeout=10,
        )
        assert r.json()["active"] is True
        assert r.json()["background"] == "Updated cover."

        # Drop
        r = httpx.delete(f"{API_BASE}/characters/{cid}/persona", headers=H, timeout=10)
        assert r.status_code == 200
        r = httpx.get(f"{API_BASE}/characters/{cid}/persona", headers=H, timeout=10)
        assert r.json() is None

    def test_persona_requires_auth(self, user_char):
        # No auth header should be 401/403
        cid = user_char["character_id"]
        r = httpx.get(f"{API_BASE}/characters/{cid}/persona", timeout=10)
        assert r.status_code in (401, 403)


# =========================== PROPHECY ===========================


@pytest.mark.skipif(not os.environ.get("EMERGENT_LLM_KEY"), reason="LLM key missing")
class TestProphecy:
    def test_lifecycle(self, admin_token):
        # Create a one-shot user/character we can safely prophesize on
        suffix = int(time.time() * 1000)
        email = f"prop_{suffix}@delarom.com"
        reg = httpx.post(
            f"{API_BASE}/auth/register",
            json={"username": f"Prop_{suffix}", "email": email, "password": "password123", "application_text": "x"},
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
            json={"name": f"PropChar_{suffix}", "race": "Elf", "character_class": "Wanderer",
                  "backstory": "Born under a comet.", "powers": "", "appearance": "", "nation": "Ammeonon"},
            timeout=10,
        )
        cid = ch.json()["id"]
        H = {"Authorization": f"Bearer {token}"}

        # No prophecy yet
        r = httpx.get(f"{API_BASE}/characters/{cid}/prophecy", timeout=10)
        assert r.status_code == 200
        assert r.json() is None

        # Receive
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/prophecy",
            headers=H, json={"context": "A fortune-teller at the docks."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["text"]
        assert p["fulfilled"] is False

        # Public read
        r = httpx.get(f"{API_BASE}/characters/{cid}/prophecy", timeout=10)
        assert r.status_code == 200
        assert r.json()["text"] == p["text"]

        # Cannot receive a second one
        r = httpx.post(
            f"{API_BASE}/characters/{cid}/prophecy",
            headers=H, json={}, timeout=10,
        )
        assert r.status_code == 400


# =========================== DREAMS ===========================


@pytest.mark.skipif(not os.environ.get("EMERGENT_LLM_KEY"), reason="LLM key missing")
class TestDreams:
    def test_single_dream_then_rate_limit(self, admin_token):
        suffix = int(time.time() * 1000)
        email = f"dream_{suffix}@delarom.com"
        reg = httpx.post(
            f"{API_BASE}/auth/register",
            json={"username": f"Dream_{suffix}", "email": email, "password": "password123", "application_text": "x"},
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
            json={"name": f"Dreamer_{suffix}", "race": "Human", "character_class": "Wanderer",
                  "backstory": "A drifter haunted by the sea.", "powers": "", "appearance": "", "nation": "Selindori"},
            timeout=10,
        )
        cid = ch.json()["id"]
        H = {"Authorization": f"Bearer {token}"}

        # Initial state: 0 dreams, can_dream_today=True
        r = httpx.get(f"{API_BASE}/characters/{cid}/dreams", headers=H, timeout=10)
        assert r.status_code == 200
        assert r.json()["dreams"] == []
        assert r.json()["can_dream_today"] is True

        # Sleep & dream
        r = httpx.post(f"{API_BASE}/characters/{cid}/dream", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        dream = r.json()
        assert dream["body"]
        assert dream["mood"]

        # Second attempt same day → 429
        r = httpx.post(f"{API_BASE}/characters/{cid}/dream", headers=H, timeout=15)
        assert r.status_code == 429

        # can_dream_today is now False
        r = httpx.get(f"{API_BASE}/characters/{cid}/dreams", headers=H, timeout=10)
        assert r.json()["can_dream_today"] is False
        assert len(r.json()["dreams"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
