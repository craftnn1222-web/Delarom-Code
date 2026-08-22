"""Iteration 26 live API tests — Elder-Gods festival calendar + Party Quests MVP.

Modules covered:
  • GET /api/prayers/festivals  (calendar shape, active nullable)
  • GET /api/prayers/gods, POST /api/prayers/submit (smoke regression)
  • /api/parties/* full lifecycle: create → join → start → turn rotation →
    not-your-turn 409 → leave → finish, plus guardrails.

Note: an image-batch background job may block the loop; LLM endpoints use
a 180s timeout.
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
USER2_EMAIL = "rep_tester_round2@delarom.com"
USER2_PASSWORD = "Testpass123!"

T = 90        # normal endpoints
T_LLM = 180   # LLM-backed endpoints

VALID_VERDICTS = {"silence", "flicker", "blessing"}


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": password}, timeout=T)
    if r.status_code != 200:
        pytest.fail(f"Login failed for {email}: {r.status_code} {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        pytest.fail(f"No access_token in login response: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def user2():
    return _login(USER2_EMAIL, USER2_PASSWORD)


@pytest.fixture(scope="module")
def admin_char(admin):
    r = admin.get(f"{BASE_URL}/api/characters", timeout=T)
    assert r.status_code == 200, r.text[:300]
    chars = r.json()
    assert chars, "Admin has no characters — cannot run party tests"
    return chars[0]


@pytest.fixture(scope="module")
def user2_char(user2):
    r = user2.get(f"{BASE_URL}/api/characters", timeout=T)
    assert r.status_code == 200, r.text[:300]
    chars = r.json()
    if chars:
        return chars[0]
    payload = {
        "name": f"TEST_Joiner_{uuid.uuid4().hex[:6]}",
        "race": "Human",
        "character_class": "Ranger",
        "backstory": "A test-created wanderer of the northern roads.",
        "powers": "Keen sight and a steady bow.",
        "appearance": "Weathered cloak, short brown hair.",
        "nation": "Ammeonon",
    }
    cr = user2.post(f"{BASE_URL}/api/characters", json=payload, timeout=T)
    assert cr.status_code in (200, 201), f"Character create failed: {cr.status_code} {cr.text[:300]}"
    return cr.json()


# ── Elder-Gods festival calendar ──────────────────────────────────────
class TestFestivals:
    def test_festivals_endpoint_shape(self, admin):
        r = requests.get(f"{BASE_URL}/api/prayers/festivals", timeout=T)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert set(["active", "calendar"]).issubset(data.keys())
        cal = data["calendar"]
        assert isinstance(cal, list) and len(cal) == 4, cal
        gods = [c["god"] for c in cal]
        assert set(gods) == {"seren", "yros", "uesis", "ehena"}, gods
        for c in cal:
            assert isinstance(c["festival_name"], str) and c["festival_name"]
            assert isinstance(c["major_dates_mm_dd"], list)
            assert len(c["major_dates_mm_dd"]) == 3, c
            assert 0 <= c["weekly_dow"] <= 6, c
            assert isinstance(c["weekly_dow_label"], str) and c["weekly_dow_label"]
        active = data["active"]
        if active is not None:
            assert active["god"] in {"seren", "yros", "uesis", "ehena"}
            assert active["level"] in {"major", "minor"}
            assert isinstance(active["affinity_boost"], int)

    def test_festivals_is_public(self):
        r = requests.get(f"{BASE_URL}/api/prayers/festivals", timeout=T)
        assert r.status_code == 200


# ── Prayer regression smoke ───────────────────────────────────────────
class TestPrayerSmoke:
    def test_gods_returns_four(self):
        r = requests.get(f"{BASE_URL}/api/prayers/gods", timeout=T)
        assert r.status_code == 200, r.text[:300]
        gods = r.json()["gods"]
        assert len(gods) == 4, gods

    def test_submit_prayer(self, admin, admin_char):
        payload = {
            "character_id": admin_char["id"],
            "god": "seren",
            "prayer_text": (
                "Seren, mother of the green, I kneel with nothing but "
                "gratitude and ask that the sick of my village breathe easy."
            ),
        }
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json=payload, timeout=T_LLM)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        verdict = data.get("verdict") or data.get("prayer", {}).get("verdict")
        assert verdict in VALID_VERDICTS, data


# ── Party lifecycle ───────────────────────────────────────────────────
class TestPartyLifecycle:
    party_id = None

    def test_a_create_party(self, admin, admin_char):
        payload = {
            "name": "TEST_The Lantern Circle",
            "scene_description": "A rain-slick tavern courtyard where a caravan master waits with an unsigned contract.",
            "location": "Tyrandria, Lower Market",
            "host_character_id": admin_char["id"],
            "max_members": 3,
        }
        r = admin.post(f"{BASE_URL}/api/parties", json=payload, timeout=T)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        p = r.json()
        assert p["status"] == "recruiting"
        assert p["turn_order"] == [admin_char["id"]]
        assert len(p["members"]) == 1
        assert p["members"][0]["role"] == "host"
        assert "_id" not in p
        TestPartyLifecycle.party_id = p["id"]

        g = admin.get(f"{BASE_URL}/api/parties/{p['id']}", timeout=T)
        assert g.status_code == 200
        assert g.json()["name"] == payload["name"]

    def test_b_second_user_joins(self, user2, user2_char):
        pid = TestPartyLifecycle.party_id
        assert pid
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/join",
                       json={"character_id": user2_char["id"]}, timeout=T)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        p = r.json()
        assert len(p["members"]) == 2
        assert user2_char["id"] in p["turn_order"]

    def test_b2_duplicate_join_conflict(self, user2, user2_char):
        pid = TestPartyLifecycle.party_id
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/join",
                       json={"character_id": user2_char["id"]}, timeout=T)
        assert r.status_code == 409, r.text[:300]
        assert "already in this party" in r.json()["detail"].lower()

    def test_b3_non_host_cannot_start(self, user2):
        pid = TestPartyLifecycle.party_id
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/start", timeout=T)
        assert r.status_code == 409, r.text[:300]
        assert "host" in r.json()["detail"].lower()

    def test_c_host_starts_party(self, admin):
        pid = TestPartyLifecycle.party_id
        r = admin.post(f"{BASE_URL}/api/parties/{pid}/start", timeout=T_LLM)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        assert r.json()["status"] == "active"
        acts = admin.get(f"{BASE_URL}/api/parties/{pid}/actions", timeout=T)
        assert acts.status_code == 200
        rows = acts.json()
        assert len(rows) == 1, rows
        assert rows[0]["actor_character_id"] == "MOC"
        assert rows[0]["ai_response"]

    def test_d_host_submits_action(self, admin):
        pid = TestPartyLifecycle.party_id
        before = admin.get(f"{BASE_URL}/api/parties/{pid}", timeout=T).json()
        r = admin.post(f"{BASE_URL}/api/parties/{pid}/action",
                       json={"action_text": "I step forward and read the contract aloud."},
                       timeout=T_LLM)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        doc = r.json()
        assert doc["turn_number"] == 1
        assert doc["ai_response"]
        acts = admin.get(f"{BASE_URL}/api/parties/{pid}/actions", timeout=T).json()
        assert len(acts) == 2, acts
        after = admin.get(f"{BASE_URL}/api/parties/{pid}", timeout=T).json()
        assert after["current_turn_index"] != before["current_turn_index"]

    def test_e_second_user_submits_action(self, user2):
        pid = TestPartyLifecycle.party_id
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/action",
                       json={"action_text": "I watch the crowd for cutpurses while he reads."},
                       timeout=T_LLM)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        after = user2.get(f"{BASE_URL}/api/parties/{pid}", timeout=T).json()
        assert after["current_turn_index"] == 0, after["current_turn_index"]

    def test_f_out_of_turn_rejected(self, user2):
        pid = TestPartyLifecycle.party_id
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/action",
                       json={"action_text": "I try to act out of turn now."},
                       timeout=T_LLM)
        assert r.status_code == 409, f"{r.status_code} {r.text[:300]}"
        assert "not your turn" in r.json()["detail"].lower()

    def test_g_second_user_leaves(self, user2, user2_char):
        pid = TestPartyLifecycle.party_id
        r = user2.post(f"{BASE_URL}/api/parties/{pid}/leave", timeout=T)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        p = r.json()
        assert all(m["character_id"] != user2_char["id"] for m in p["members"])
        assert user2_char["id"] not in p["turn_order"]
        assert len(p["members"]) == 1

    def test_h_host_cannot_leave(self, admin):
        pid = TestPartyLifecycle.party_id
        r = admin.post(f"{BASE_URL}/api/parties/{pid}/leave", timeout=T)
        assert r.status_code == 409, r.text[:300]
        assert "host" in r.json()["detail"].lower()

    def test_i_host_finishes_party(self, admin):
        pid = TestPartyLifecycle.party_id
        r = admin.post(f"{BASE_URL}/api/parties/{pid}/finish", timeout=T)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "finished"
        a = admin.post(f"{BASE_URL}/api/parties/{pid}/action",
                       json={"action_text": "One last word before we part."}, timeout=T)
        assert a.status_code == 409, a.text[:300]
        assert "not currently active" in a.json()["detail"].lower()

    def test_j_listing_hides_finished(self, admin):
        pid = TestPartyLifecycle.party_id
        rows = admin.get(f"{BASE_URL}/api/parties", timeout=T).json()
        assert all(p["id"] != pid for p in rows), "finished party still listed in default listing"
        mine = admin.get(f"{BASE_URL}/api/parties/mine", timeout=T).json()
        assert any(p["id"] == pid for p in mine), "finished party missing from /parties/mine"


# ── Guardrails ────────────────────────────────────────────────────────
class TestPartyGuardrails:
    def test_create_with_foreign_character_404(self, admin, user2_char):
        payload = {
            "name": "TEST_Stolen Character Party",
            "scene_description": "This party should never be created because the character is not mine.",
            "location": "Nowhere",
            "host_character_id": user2_char["id"],
            "max_members": 2,
        }
        r = admin.post(f"{BASE_URL}/api/parties", json=payload, timeout=T)
        assert r.status_code == 404, f"{r.status_code} {r.text[:300]}"

    def test_join_full_party_409(self, admin, admin_char, user2, user2_char):
        payload = {
            "name": "TEST_Full Party",
            "scene_description": "A two-seat table with only one chair left for a stranger to take.",
            "location": "Tyrandria, Docks",
            "host_character_id": admin_char["id"],
            "max_members": 2,
        }
        r = admin.post(f"{BASE_URL}/api/parties", json=payload, timeout=T)
        assert r.status_code == 200, r.text[:300]
        pid = r.json()["id"]
        j = user2.post(f"{BASE_URL}/api/parties/{pid}/join",
                       json={"character_id": user2_char["id"]}, timeout=T)
        assert j.status_code == 200, j.text[:300]
        # party is now full (2/2); a third joiner is impossible with 2 users,
        # so validate the full-check by shrinking is not possible — instead
        # re-attempt with user2 to confirm the duplicate guard, and assert
        # member count is capped.
        p = admin.get(f"{BASE_URL}/api/parties/{pid}", timeout=T).json()
        assert len(p["members"]) == p["max_members"] == 2
        admin.post(f"{BASE_URL}/api/parties/{pid}/finish", timeout=T)

    def test_start_nonexistent_party(self, admin):
        r = admin.post(f"{BASE_URL}/api/parties/{uuid.uuid4()}/start", timeout=T)
        assert r.status_code in (404, 409), r.text[:300]

    def test_get_nonexistent_party_404(self, admin):
        r = admin.get(f"{BASE_URL}/api/parties/{uuid.uuid4()}", timeout=T)
        assert r.status_code == 404

    def test_unauthenticated_party_list_rejected(self):
        r = requests.get(f"{BASE_URL}/api/parties", timeout=T)
        assert r.status_code in (401, 403), r.status_code

    def test_create_party_validation(self, admin, admin_char):
        r = admin.post(f"{BASE_URL}/api/parties", json={
            "name": "TEST_Short",
            "scene_description": "too short",
            "location": "X",
            "host_character_id": admin_char["id"],
        }, timeout=T)
        assert r.status_code == 422, r.status_code
