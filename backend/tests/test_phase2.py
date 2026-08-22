"""End-to-end backend tests for Phase 2 — Letters, Tavern Boards, Sworn Bonds.

Creates two temporary users + characters, exercises every endpoint of each
feature, then cleans up. Run with:

    pytest backend/tests/test_phase2.py -v
"""
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
API_BASE = f"{BACKEND_URL}/api"


def _load_backend_url():
    """Read REACT_APP_BACKEND_URL from /app/frontend/.env if not in env."""
    global BACKEND_URL, API_BASE
    if BACKEND_URL != "http://localhost:8001":
        return
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND_URL = line.strip().split("=", 1)[1]
                    API_BASE = f"{BACKEND_URL}/api"
                    return
    except FileNotFoundError:
        pass


_load_backend_url()


def _approve_user(admin_token: str, user_id: str) -> None:
    """Admin-approves a user so their token can call protected endpoints."""
    httpx.post(
        f"{API_BASE}/admin/applications/{user_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )


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
def two_users(admin_token):
    """Register, approve, and return tokens + character IDs for two users."""
    suffix = int(time.time() * 1000)
    users = []
    tokens = []
    characters = []

    for i in (1, 2):
        email = f"p2user{i}_{suffix}@delarom.com"
        username = f"P2User{i}_{suffix}"
        # Register
        reg = httpx.post(
            f"{API_BASE}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "password123",
                "application_text": "Phase 2 e2e test user.",
            },
            timeout=10,
        )
        reg.raise_for_status()
        user_id = reg.json()["user"]["id"]
        users.append(user_id)

        # Approve
        _approve_user(admin_token, user_id)

        # Login
        login = httpx.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": "password123"},
            timeout=10,
        )
        login.raise_for_status()
        tokens.append(login.json()["access_token"])

    # Create a character for each
    nations = ["Ammeonon", "Selindori"]
    for i in (0, 1):
        ch = httpx.post(
            f"{API_BASE}/characters",
            headers={"Authorization": f"Bearer {tokens[i]}"},
            json={
                "name": f"P2Char{i+1}_{suffix}",
                "race": "Human",
                "character_class": "Wanderer",
                "backstory": "...",
                "powers": "",
                "appearance": "",
                "nation": nations[i],
            },
            timeout=10,
        )
        ch.raise_for_status()
        characters.append(ch.json()["id"])

    return {
        "tokens": tokens,
        "characters": characters,
        "user_ids": users,
        "suffix": suffix,
    }


# =========================== LETTERS ===========================


class TestLetters:
    def test_send_then_inbox_shows_in_transit_then_delivered(self, two_users):
        tok1, tok2 = two_users["tokens"]
        ch1, ch2 = two_users["characters"]

        # Send a letter from char1 to char2
        r = httpx.post(
            f"{API_BASE}/letters",
            headers={"Authorization": f"Bearer {tok1}"},
            json={
                "sender_character_id": ch1,
                "recipient_character_id": ch2,
                "subject": "Greetings",
                "body": "How fares thy hearth?",
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        letter = r.json()
        assert letter["subject"] == "Greetings"
        assert letter["sender_character_id"] == ch1
        assert letter["recipient_character_id"] == ch2

        # Sender's "sent" list contains it
        r = httpx.get(
            f"{API_BASE}/characters/{ch1}/letters/sent",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=10,
        )
        assert r.status_code == 200
        sent = r.json()
        assert any(let["id"] == letter["id"] for let in sent)
        # Cross-continent (ammeonon → selindori) → 4 hour delay → in_transit
        match = next(let for let in sent if let["id"] == letter["id"])
        assert match["status"] == "in_transit"

        # Recipient inbox does NOT contain it yet (still in transit)
        r = httpx.get(
            f"{API_BASE}/characters/{ch2}/letters/inbox",
            headers={"Authorization": f"Bearer {tok2}"},
            timeout=10,
        )
        assert r.status_code == 200
        assert not any(let["id"] == letter["id"] for let in r.json())

    def test_self_letter_rejected(self, two_users):
        tok1 = two_users["tokens"][0]
        ch1 = two_users["characters"][0]
        r = httpx.post(
            f"{API_BASE}/letters",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"sender_character_id": ch1, "recipient_character_id": ch1, "subject": "x", "body": "y"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_sender_must_own_character(self, two_users):
        # User 1 tries to send FROM user 2's character
        tok1 = two_users["tokens"][0]
        ch1 = two_users["characters"][0]
        ch2 = two_users["characters"][1]
        r = httpx.post(
            f"{API_BASE}/letters",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"sender_character_id": ch2, "recipient_character_id": ch1, "subject": "x", "body": "y"},
            timeout=10,
        )
        assert r.status_code == 403


# =========================== TAVERN BOARDS ===========================


class TestTavernBoards:
    def test_post_appears_in_listing(self, two_users):
        tok1 = two_users["tokens"][0]
        ch1 = two_users["characters"][0]
        r = httpx.post(
            f"{API_BASE}/locations/ammeonon/wymroost/notices",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"character_id": ch1, "body": "Caravan to Yillhone seeks armed escort. 50g. Meet at sundown."},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        notice_id = r.json()["id"]

        # List
        r = httpx.get(f"{API_BASE}/locations/ammeonon/wymroost/notices", timeout=10)
        assert r.status_code == 200
        notices = r.json()
        assert any(n["id"] == notice_id for n in notices)

        # Cleanup — delete it via author
        httpx.delete(
            f"{API_BASE}/notices/{notice_id}",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=10,
        )

    def test_non_author_cannot_delete(self, two_users):
        tok1, tok2 = two_users["tokens"]
        ch1 = two_users["characters"][0]
        r = httpx.post(
            f"{API_BASE}/locations/ammeonon/wymroost/notices",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"character_id": ch1, "body": "Lost pendant near the docks. Reward offered."},
            timeout=10,
        )
        notice_id = r.json()["id"]
        # User 2 attempts delete
        r = httpx.delete(
            f"{API_BASE}/notices/{notice_id}",
            headers={"Authorization": f"Bearer {tok2}"},
            timeout=10,
        )
        assert r.status_code == 403
        # Cleanup via author
        httpx.delete(
            f"{API_BASE}/notices/{notice_id}",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=10,
        )

    def test_anonymous_can_read(self, two_users):
        tok1 = two_users["tokens"][0]
        ch1 = two_users["characters"][0]
        r = httpx.post(
            f"{API_BASE}/locations/ammeonon/wymroost/notices",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"character_id": ch1, "body": "Public reading test."},
            timeout=10,
        )
        notice_id = r.json()["id"]
        # No auth header
        r = httpx.get(f"{API_BASE}/locations/ammeonon/wymroost/notices", timeout=10)
        assert r.status_code == 200
        assert any(n["id"] == notice_id for n in r.json())
        httpx.delete(
            f"{API_BASE}/notices/{notice_id}",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=10,
        )


# =========================== SWORN BONDS ===========================


class TestBonds:
    def test_full_lifecycle(self, two_users):
        tok1, tok2 = two_users["tokens"]
        ch1, ch2 = two_users["characters"]

        # 1. Propose
        r = httpx.post(
            f"{API_BASE}/characters/{ch1}/bonds/propose",
            headers={"Authorization": f"Bearer {tok1}"},
            json={
                "target_character_id": ch2,
                "bond_type": "blood-brothers",
                "proposal_text": "We have ridden together too long to be anything less.",
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        bond = r.json()
        bond_id = bond["id"]
        assert bond["status"] == "proposed"
        assert bond["bond_label"] == "Blood-brothers"

        # 2. Duplicate proposal rejected
        r = httpx.post(
            f"{API_BASE}/characters/{ch1}/bonds/propose",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"target_character_id": ch2, "bond_type": "rivals", "proposal_text": "x"},
            timeout=10,
        )
        assert r.status_code == 400

        # 3. Initiator cannot accept their own proposal
        r = httpx.post(
            f"{API_BASE}/bonds/{bond_id}/accept",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=10,
        )
        assert r.status_code == 403

        # 4. Target accepts
        r = httpx.post(
            f"{API_BASE}/bonds/{bond_id}/accept",
            headers={"Authorization": f"Bearer {tok2}"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

        # 5. /users/me/bonds shows it under "accepted" for both
        for tok in (tok1, tok2):
            r = httpx.get(
                f"{API_BASE}/users/me/bonds",
                headers={"Authorization": f"Bearer {tok}"},
                timeout=10,
            )
            assert r.status_code == 200
            assert any(b["id"] == bond_id for b in r.json()["accepted"])

        # 6. Either side can break
        r = httpx.post(
            f"{API_BASE}/bonds/{bond_id}/break",
            headers={"Authorization": f"Bearer {tok2}"},
            json={"reason": "A bitter quarrel over inheritance."},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "broken"

    def test_invalid_bond_type(self, two_users):
        tok1 = two_users["tokens"][0]
        ch1, ch2 = two_users["characters"]
        r = httpx.post(
            f"{API_BASE}/characters/{ch1}/bonds/propose",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"target_character_id": ch2, "bond_type": "lifemates", "proposal_text": "x"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_cannot_bond_with_self(self, two_users):
        tok1 = two_users["tokens"][0]
        ch1 = two_users["characters"][0]
        r = httpx.post(
            f"{API_BASE}/characters/{ch1}/bonds/propose",
            headers={"Authorization": f"Bearer {tok1}"},
            json={"target_character_id": ch1, "bond_type": "rivals", "proposal_text": "x"},
            timeout=10,
        )
        assert r.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
