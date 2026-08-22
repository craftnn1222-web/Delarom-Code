"""End-to-end backend tests for Phase 5 — Rumors + Apprenticeships.

Wanted-Poster generation hits an image LLM so is not covered here (verified
end-to-end via live curl). The rumor `_judge_rumor` call hits text LLM, so
the plant test is LLM-gated.
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
    return httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": "craftnn1222@gmail.com", "password": "admin123"},
        timeout=10,
    ).json()["access_token"]


@pytest.fixture(scope="module")
def fresh_user(admin_token):
    suffix = int(time.time() * 1000)
    email = f"p5_{suffix}@delarom.com"
    reg = httpx.post(
        f"{API_BASE}/auth/register",
        json={"username": f"P5_{suffix}", "email": email, "password": "password123", "application_text": "x"},
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
        json={"name": f"P5Char_{suffix}", "race": "Human", "character_class": "Wanderer",
              "backstory": "Lived between two worlds.", "powers": "", "appearance": "", "nation": "Ammeonon"},
        timeout=10,
    )
    return {"token": token, "character_id": ch.json()["id"]}


# =========================== APPRENTICESHIPS ===========================


class TestApprenticeships:
    def test_full_lifecycle(self, fresh_user, admin_token):
        tok = fresh_user["token"]
        cid = fresh_user["character_id"]
        H = {"Authorization": f"Bearer {tok}"}

        # Need an NPC to apprentice under — seed one via admin
        suffix = int(time.time() * 1000)
        npc = httpx.post(
            f"{API_BASE}/admin/npcs/ammeonon/wymroost",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Master Forgehand_{suffix}",
                "race": "Dwarf",
                "role": "Smith",
                "personality": "Gruff but kind",
                "motivation": "To pass on his craft.",
                "importance": "notable",
            },
            timeout=10,
        )
        assert npc.status_code == 200, npc.text
        mentor_id = npc.json()["id"]

        # Invalid craft
        r = httpx.post(
            f"{API_BASE}/apprenticeships",
            headers=H,
            json={"character_id": cid, "mentor_npc_id": mentor_id, "craft": "evilsmith", "intro_text": "x"},
            timeout=10,
        )
        assert r.status_code == 400

        # Start
        r = httpx.post(
            f"{API_BASE}/apprenticeships",
            headers=H,
            json={"character_id": cid, "mentor_npc_id": mentor_id, "craft": "smith", "intro_text": "First sweeping of the forge floor."},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        app = r.json()
        aid = app["id"]
        assert app["rank"] == "initiate"
        assert len(app["milestones"]) == 1

        # Duplicate active apprenticeship in same craft rejected
        r = httpx.post(
            f"{API_BASE}/apprenticeships",
            headers=H,
            json={"character_id": cid, "mentor_npc_id": mentor_id, "craft": "smith"},
            timeout=10,
        )
        assert r.status_code == 400

        # Record milestone
        r = httpx.post(
            f"{API_BASE}/apprenticeships/{aid}/milestone",
            headers=H,
            json={"text": "Forged my first true blade."},
            timeout=10,
        )
        assert r.status_code == 200

        # Cannot graduate before reaching master
        r = httpx.post(f"{API_BASE}/apprenticeships/{aid}/graduate", headers=H, timeout=10)
        assert r.status_code == 400

        # Rank backwards rejected
        r = httpx.post(f"{API_BASE}/apprenticeships/{aid}/promote", headers=H,
                       json={"rank": "initiate"}, timeout=10)
        assert r.status_code == 400

        # Promote forward
        r = httpx.post(f"{API_BASE}/apprenticeships/{aid}/promote", headers=H,
                       json={"rank": "journeyman"}, timeout=10)
        assert r.status_code == 200
        r = httpx.post(f"{API_BASE}/apprenticeships/{aid}/promote", headers=H,
                       json={"rank": "master"}, timeout=10)
        assert r.status_code == 200

        # Now graduate works
        r = httpx.post(f"{API_BASE}/apprenticeships/{aid}/graduate", headers=H, timeout=10)
        assert r.status_code == 200

        # Public list shows it
        r = httpx.get(f"{API_BASE}/characters/{cid}/apprenticeships", timeout=10)
        assert r.status_code == 200
        assert any(a["id"] == aid for a in r.json())

        # Cleanup the seeded NPC
        httpx.delete(f"{API_BASE}/admin/npcs/{mentor_id}",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)


# =========================== RUMORS (LLM-gated) ===========================


@pytest.mark.skipif(not os.environ.get("EMERGENT_LLM_KEY"), reason="LLM key missing")
class TestRumors:
    def test_plant_then_listed_publicly_judgement_hidden(self, fresh_user, admin_token):
        tok = fresh_user["token"]
        cid = fresh_user["character_id"]
        H = {"Authorization": f"Bearer {tok}"}

        # Need a victim NPC
        suffix = int(time.time() * 1000)
        npc = httpx.post(
            f"{API_BASE}/admin/npcs/ammeonon/wymroost",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Rumor Target_{suffix}",
                "race": "Human",
                "role": "Merchant",
                "personality": "Quiet and rich.",
                "motivation": "To grow their fortune.",
            },
            timeout=10,
        ).json()

        r = httpx.post(
            f"{API_BASE}/rumors",
            headers=H,
            json={
                "planter_character_id": cid,
                "nation": "ammeonon",
                "subject_kind": "npc",
                "subject_id": npc["id"],
                "text": "Some say the merchant pays smugglers to bring in moon-coral after dark.",
            },
            timeout=60,
        )
        assert r.status_code == 200, r.text
        public_view = r.json()
        rid = public_view["id"]
        # Public view should NOT include judgement
        assert "judgement" not in public_view

        # Public listing — judgement should still be hidden
        r = httpx.get(f"{API_BASE}/rumors", params={"nation": "ammeonon"}, timeout=10)
        listing = r.json()
        match = next(rm for rm in listing if rm["id"] == rid)
        assert "judgement" not in match

        # Planter's /mine view DOES include judgement
        r = httpx.get(f"{API_BASE}/characters/{cid}/rumors/mine", headers=H, timeout=10)
        mine = next(rm for rm in r.json() if rm["id"] == rid)
        assert mine["judgement"] in ("true", "partly-true", "false")

        httpx.delete(f"{API_BASE}/admin/npcs/{npc['id']}",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)


# ─── Master-NPC mentors endpoint ─────────────────────────────────────────


def test_mentors_endpoint_filters_by_craft_and_nation():
    """The seeded master NPCs (`seed_master_npcs.py`) must be queryable via
    the public `/apprenticeships/mentors` endpoint, filtered by craft, nation,
    and substring `q`. This is anonymous-friendly — no auth header sent."""
    # By craft only — at least one per nation should exist (we seeded 5).
    r = httpx.get(f"{API_BASE}/apprenticeships/mentors", params={"craft": "smith"}, timeout=10)
    assert r.status_code == 200, r.text
    smiths = r.json()
    assert len(smiths) >= 5, f"expected 5+ master smiths after seed, got {len(smiths)}"
    nations = {m["nation"] for m in smiths}
    assert nations >= {"ammeonon", "selindori", "dhor-kuldor", "aigraels", "veiled-realms"}, nations

    # By craft + nation — exactly one (one master per craft per nation).
    r = httpx.get(f"{API_BASE}/apprenticeships/mentors",
                  params={"craft": "smith", "nation": "ammeonon"}, timeout=10)
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Brask Cinderhand"
    assert rows[0]["role"] == "Master Smith"

    # By substring q — case-insensitive name match.
    r = httpx.get(f"{API_BASE}/apprenticeships/mentors",
                  params={"q": "borrik"}, timeout=10)
    rows = r.json()
    assert len(rows) == 1
    assert "Borrik" in rows[0]["name"]
    assert rows[0]["craft"] == "smith"

    # Invalid craft is rejected with 400.
    r = httpx.get(f"{API_BASE}/apprenticeships/mentors",
                  params={"craft": "blacksmurf"}, timeout=10)
    assert r.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
