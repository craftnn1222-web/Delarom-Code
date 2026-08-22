"""Regression for the new Public Bounty Board surface (NPC perpetrators,
nation filtering, character visibility rules) and a quick smoke of the
previously-shipped law / companions / image / chronicle endpoints.

Seeds NPC crimes by directly hitting Mongo via LawService.record_crime so we
don't need an RP turn to land them. Cleans up via direct delete at teardown.

Run:
    pytest /app/backend/tests/test_bounty_board.py -v \
        --junitxml=/app/test_reports/pytest/bounty_board.xml
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from law_service import LawService  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "craftnn1222@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

NPC_TAG = f"TEST_BB_{uuid.uuid4().hex[:8]}"
SEED_AMME_NPC_ID = f"npc-amme-{NPC_TAG}"
SEED_AMME_NPC_NAME = f"Test Fugitive {NPC_TAG}"
SEED_SELI_NPC_ID = f"npc-seli-{NPC_TAG}"
SEED_SELI_NPC_NAME = f"Selindori Outlaw {NPC_TAG}"

SEED_NATION_AMME = "ammeonon"
SEED_NATION_SELI = "selindori"


# ---------- Async helpers ----------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.get_event_loop().is_running() else asyncio.run(coro)


async def _seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    law = LawService(db)
    # NPC in ammeonon — minor severity (still must show — NPC bounties always public)
    await law.record_crime(
        perpetrator_type="npc",
        perpetrator_id=SEED_AMME_NPC_ID,
        perpetrator_name=SEED_AMME_NPC_NAME,
        nation=SEED_NATION_AMME,
        location="wymroost",
        crime_type="banditry",
        severity="minor",
        victim_name="merchant",
        victim_importance="commoner",
        description=f"{NPC_TAG} ammeonon",
    )
    # NPC in selindori — major severity
    await law.record_crime(
        perpetrator_type="npc",
        perpetrator_id=SEED_SELI_NPC_ID,
        perpetrator_name=SEED_SELI_NPC_NAME,
        nation=SEED_NATION_SELI,
        location="silver-bay",
        crime_type="murder",
        severity="major",
        victim_name="captain",
        victim_importance="notable",
        description=f"{NPC_TAG} selindori",
    )
    client.close()


async def _cleanup():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.crimes.delete_many({"description": {"$regex": NPC_TAG}})
    await db.bounties.delete_many({"perpetrator_id": {"$in": [SEED_AMME_NPC_ID, SEED_SELI_NPC_ID]}})
    client.close()


@pytest.fixture(scope="module", autouse=True)
def _seed_and_clean():
    asyncio.run(_cleanup())   # pre-clean leftovers
    asyncio.run(_seed())
    yield
    asyncio.run(_cleanup())


# ---------- Shared fixtures ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_auth(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    tok = r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# =========================================================
# Bounty Board surface
# =========================================================

class TestBountyBoardAnonymous:
    """The board endpoint must be readable without any Authorization header."""

    def test_anonymous_get_returns_list(self, session):
        # Use a brand new session (no auth headers) to guarantee anonymous
        r = requests.get(f"{BASE_URL}/api/bounty-board", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"

    def test_anonymous_get_includes_seeded_npc_fields(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board", timeout=30)
        assert r.status_code == 200
        items = r.json()
        ours = [b for b in items if b.get("perpetrator_id") == SEED_AMME_NPC_ID]
        assert ours, f"Seeded NPC bounty not found on board. Got {len(items)} entries."
        b = ours[0]
        # Validate the documented shape
        for key in ("perpetrator_type", "perpetrator_id", "perpetrator_name",
                    "nation", "total_bounty", "worst_severity", "open_crime_count"):
            assert key in b, f"Missing key {key} in {b}"
        assert b["perpetrator_type"] == "npc"
        assert b["perpetrator_name"] == SEED_AMME_NPC_NAME
        assert b["nation"] == SEED_NATION_AMME
        assert b["worst_severity"] == "minor"  # NPC minor still visible
        assert b["open_crime_count"] >= 1
        assert b["total_bounty"] > 0


class TestBountyBoardNationFilter:
    def test_filter_ammeonon_includes_amme_excludes_seli(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board?nation=ammeonon", timeout=30)
        assert r.status_code == 200
        data = r.json()
        ids = {b["perpetrator_id"] for b in data}
        assert SEED_AMME_NPC_ID in ids, "Ammeonon NPC missing from ammeonon filter"
        assert SEED_SELI_NPC_ID not in ids, "Cross-nation leak: selindori NPC appeared under ammeonon"
        for b in data:
            assert b["nation"] == "ammeonon"

    def test_filter_selindori_includes_seli_excludes_amme(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board?nation=selindori", timeout=30)
        assert r.status_code == 200
        data = r.json()
        ids = {b["perpetrator_id"] for b in data}
        assert SEED_SELI_NPC_ID in ids
        assert SEED_AMME_NPC_ID not in ids


class TestBountyBoardVisibility:
    """Character petty/minor crimes are deliberately hidden from the board."""

    def test_no_character_petty_or_minor_bounties_present(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board", timeout=30)
        assert r.status_code == 200
        for b in r.json():
            if b["perpetrator_type"] == "character":
                assert b["worst_severity"] in ("major", "capital", "regicide"), (
                    f"Hidden severity {b['worst_severity']} character leaked onto board: {b}"
                )

    def test_npc_minor_is_visible(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board?nation=ammeonon", timeout=30)
        assert r.status_code == 200
        ours = [b for b in r.json() if b["perpetrator_id"] == SEED_AMME_NPC_ID]
        assert ours and ours[0]["worst_severity"] == "minor"


# =========================================================
# NPC hunting payout — direct service test (no AI required)
# =========================================================

class TestNpcHuntingPayout:
    def test_claim_npc_bounty_closes_crimes_and_returns_total(self):
        async def _run_claim():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            law = LawService(db)
            # Use the selindori NPC (major, total_bounty > 0)
            before = await db.bounties.find_one(
                {"perpetrator_id": SEED_SELI_NPC_ID, "nation": SEED_NATION_SELI},
                {"_id": 0},
            )
            assert before, "Seeded selindori bounty missing"
            expected_payout = before["total_bounty"]
            assert expected_payout > 0

            result = await law.claim_npc_bounty(
                npc_id=SEED_SELI_NPC_ID,
                nation=SEED_NATION_SELI,
                claimed_by_user_id="test-user",
                claimed_by_character_id="test-char",
                claimed_by_character_name="Tester",
                method="captured",
            )
            assert result["total_payout"] == expected_payout
            assert result["crimes_closed"] >= 1

            # All crimes for that NPC in that nation must now be 'claimed'
            remaining_open = await db.crimes.count_documents({
                "perpetrator_type": "npc",
                "perpetrator_id": SEED_SELI_NPC_ID,
                "nation": SEED_NATION_SELI,
                "status": "open",
            })
            assert remaining_open == 0
            claimed = await db.crimes.count_documents({
                "perpetrator_type": "npc",
                "perpetrator_id": SEED_SELI_NPC_ID,
                "nation": SEED_NATION_SELI,
                "status": "claimed",
            })
            assert claimed >= 1

            # Idempotent — second call returns 0
            result2 = await law.claim_npc_bounty(
                npc_id=SEED_SELI_NPC_ID,
                nation=SEED_NATION_SELI,
                claimed_by_user_id="test-user",
                claimed_by_character_id="test-char",
                claimed_by_character_name="Tester",
                method="captured",
            )
            assert result2["total_payout"] == 0
            client.close()

        asyncio.run(_run_claim())

    def test_claimed_npc_removed_from_bounty_board(self):
        r = requests.get(f"{BASE_URL}/api/bounty-board?nation=selindori", timeout=30)
        assert r.status_code == 200
        ids = {b["perpetrator_id"] for b in r.json()}
        assert SEED_SELI_NPC_ID not in ids, "Claimed NPC still showing on board"


# =========================================================
# Regression — pre-existing public/admin surfaces
# =========================================================

class TestRegressionLaw:
    def test_rap_sheet_endpoint(self, session, admin_auth):
        r = session.get(f"{BASE_URL}/api/characters", headers=admin_auth, timeout=30)
        assert r.status_code == 200
        chars = r.json()
        if not chars:
            pytest.skip("No characters for admin")
        cid = chars[0]["id"]
        r = session.get(f"{BASE_URL}/api/characters/{cid}/rap-sheet",
                        headers=admin_auth, timeout=30)
        assert r.status_code == 200
        data = r.json()
        # Documented shape
        assert "crimes" in data or "open_crimes" in data or "bounties" in data, data


class TestRegressionChronicle:
    def test_chronicle_public(self):
        r = requests.get(f"{BASE_URL}/api/chronicle", timeout=30)
        assert r.status_code == 200
        # Returns list or dict — both shapes acceptable, just ensure 200 + JSON
        r.json()


class TestRegressionImageStorage:
    def test_city_image_returns_small_json_with_image_url(self):
        r = requests.get(f"{BASE_URL}/api/city-image/ammeonon/wymroost", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "image_url" in data, data
        assert data["image_url"].startswith("/api/image/"), data["image_url"]

    def test_image_endpoint_serves_bytes(self):
        meta = requests.get(f"{BASE_URL}/api/city-image/ammeonon/wymroost", timeout=60).json()
        img_id = meta["image_url"].split("/api/image/")[-1]
        r = requests.get(f"{BASE_URL}/api/image/{img_id}", timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("Content-Type", "")
        assert ct.startswith("image/"), f"Unexpected Content-Type: {ct}"
        assert len(r.content) > 1024, "Image looks empty"


class TestRegressionCompanions:
    def test_owned_npcs_list(self, session, admin_auth):
        chars = session.get(f"{BASE_URL}/api/characters", headers=admin_auth, timeout=30).json()
        if not chars:
            pytest.skip("No characters")
        cid = chars[0]["id"]
        r = session.get(f"{BASE_URL}/api/characters/{cid}/owned-npcs",
                        headers=admin_auth, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
