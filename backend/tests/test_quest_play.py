"""Quest Play backend tests (iteration_34).

Covers:
- GET /api/quests/{id}
- GET /api/quests/{id}/actions (open)
- POST /api/quests/{id}/actions (requires accepted status)
- GET /api/quests/my-quests/accepted (lightweight character projection)
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

ACCEPTED_QUEST_ID = "201107e7-20ea-4df7-ab1a-906f20a639a8"  # Focused Test Quest
COMPLETED_QUEST_ID = "30976291-5616-402f-8309-de87967ba1a7"  # Cosmic Disturbances


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------- GET /api/quests/{id} ----------------
def test_get_accepted_quest(auth_headers):
    r = requests.get(f"{BASE_URL}/api/quests/{ACCEPTED_QUEST_ID}", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == ACCEPTED_QUEST_ID
    assert "title" in data
    assert "description" in data


def test_get_quest_not_found(auth_headers):
    r = requests.get(f"{BASE_URL}/api/quests/nonexistent-id-xyz", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# ---------------- GET /api/quests/{id}/actions ----------------
def test_get_quest_actions_returns_list(auth_headers):
    r = requests.get(
        f"{BASE_URL}/api/quests/{ACCEPTED_QUEST_ID}/actions", headers=auth_headers, timeout=15
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    # First action should be Quest Master opening narration
    if data:
        first = data[0]
        assert "turn_number" in first
        assert "action_text" in first
        assert "ai_response" in first


# ---------------- POST /api/quests/{id}/actions ----------------
def test_submit_quest_action_persists(auth_headers):
    action_text = "TEST_QuestPlay: The hero surveys the horizon, weighing which path to take."
    r = requests.post(
        f"{BASE_URL}/api/quests/{ACCEPTED_QUEST_ID}/actions",
        headers=auth_headers,
        json={"action_text": action_text},
        timeout=60,  # AI can be slow
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "action_id" in body
    assert "ai_response" in body
    assert "turn_number" in body
    assert isinstance(body["ai_response"], str)
    assert len(body["ai_response"]) > 0
    action_id = body["action_id"]

    # Verify persistence via GET
    r2 = requests.get(
        f"{BASE_URL}/api/quests/{ACCEPTED_QUEST_ID}/actions", headers=auth_headers, timeout=15
    )
    assert r2.status_code == 200
    actions = r2.json()
    found = next((a for a in actions if a["id"] == action_id), None)
    assert found is not None, "Submitted action did not persist"
    assert found["action_text"] == action_text
    assert found["ai_response"] == body["ai_response"]


def test_submit_action_without_acceptance_forbidden(auth_headers):
    # Find an open quest that admin has NOT accepted
    r = requests.get(f"{BASE_URL}/api/quests?status=open", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    open_quests = r.json()

    r2 = requests.get(f"{BASE_URL}/api/quests/my-quests/accepted", headers=auth_headers, timeout=15)
    assert r2.status_code == 200
    accepted_ids = {m["quest"]["id"] for m in r2.json()}

    candidate = next((q for q in open_quests if q["id"] not in accepted_ids), None)
    if candidate is None:
        pytest.skip("No open unaccepted quest available")

    r3 = requests.post(
        f"{BASE_URL}/api/quests/{candidate['id']}/actions",
        headers=auth_headers,
        json={"action_text": "TEST_unauth attempt"},
        timeout=30,
    )
    assert r3.status_code == 403


def test_submit_action_completed_quest_forbidden(auth_headers):
    """Completed acceptances have status='completed', which the endpoint filters out."""
    r = requests.post(
        f"{BASE_URL}/api/quests/{COMPLETED_QUEST_ID}/actions",
        headers=auth_headers,
        json={"action_text": "TEST_should_fail"},
        timeout=30,
    )
    # The route only queries for status='accepted', so completed -> 403
    assert r.status_code == 403, r.text


# ---------------- GET /api/quests/my-quests/accepted lightweight projection ----------------
def test_my_accepted_lightweight_character(auth_headers):
    r = requests.get(f"{BASE_URL}/api/quests/my-quests/accepted", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Response size should be small (< 200KB) - no base64 portrait
    payload_bytes = len(r.content)
    assert payload_bytes < 200_000, (
        f"my-quests/accepted payload too large: {payload_bytes} bytes — portrait may still be included"
    )

    for entry in data:
        char = entry.get("character")
        if char is None:
            continue
        # Lightweight fields only
        assert "id" in char
        assert "name" in char
        # Should NOT include portrait_url
        assert "portrait_url" not in char, (
            f"portrait_url leaked into my-quests/accepted character: {list(char.keys())}"
        )
        # Race and class expected in projection
        expected_extra = {"race", "character_class"}
        assert expected_extra.issubset(set(char.keys())), (
            f"Missing lightweight fields in character projection: {char.keys()}"
        )
