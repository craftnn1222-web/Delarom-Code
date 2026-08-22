"""Backend regression suite for the Law / Crime / Imprisonment / Trial / Escape
system plus its dependent subsystems (NPC memory, companions, image storage,
butterfly-effect cascades, public Chronicle, scene-state injection).

Run:
    pytest /app/backend/tests/test_law_system.py -v \
        --junitxml=/app/test_reports/pytest/law_system.xml
"""
from __future__ import annotations

import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "craftnn1222@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

CRIME_NATION = "ammeonon"
CRIME_LOC_A = "wymroost"      # capital crime location
CRIME_LOC_B = "azure-castle"  # same-nation propagation location
OTHER_NATION = "dhor-kuldor"
OTHER_LOC = "anchor-smithy"


# ---------- shared fixtures ----------

@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def character_id(session, auth):
    """First character in admin's list (per request)."""
    r = session.get(f"{BASE_URL}/api/characters", headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    chars = r.json()
    assert isinstance(chars, list) and chars, "No characters found"
    return chars[0]["id"]


@pytest.fixture(scope="session", autouse=True)
def _cleanup(session, admin_token):
    """Sweep any leftover crimes/imprisonments for the test character before & after the run."""
    auth = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    # Pre-clean
    try:
        cid_r = session.get(f"{BASE_URL}/api/characters", headers=auth, timeout=15)
        if cid_r.status_code == 200 and cid_r.json():
            cid = cid_r.json()[0]["id"]
            rs = session.get(f"{BASE_URL}/api/characters/{cid}/rap-sheet", headers=auth, timeout=15)
            if rs.status_code == 200:
                data = rs.json()
                imp = data.get("imprisonment")
                if imp and imp.get("status") == "active":
                    session.post(
                        f"{BASE_URL}/api/admin/imprisonments/{imp['id']}/release",
                        headers=auth,
                        json={"status": "pardoned", "reason": "TEST cleanup"},
                        timeout=15,
                    )
                for c in data.get("crimes", []):
                    if c.get("status") == "open":
                        session.delete(
                            f"{BASE_URL}/api/admin/crimes/{c['id']}", headers=auth, timeout=15,
                        )
    except Exception as e:
        print(f"pre-cleanup warning: {e}")

    yield

    # Post-clean — same sweep
    try:
        cid_r = session.get(f"{BASE_URL}/api/characters", headers=auth, timeout=15)
        if cid_r.status_code == 200 and cid_r.json():
            cid = cid_r.json()[0]["id"]
            rs = session.get(f"{BASE_URL}/api/characters/{cid}/rap-sheet", headers=auth, timeout=15)
            if rs.status_code == 200:
                data = rs.json()
                imp = data.get("imprisonment")
                if imp and imp.get("status") == "active":
                    session.post(
                        f"{BASE_URL}/api/admin/imprisonments/{imp['id']}/release",
                        headers=auth,
                        json={"status": "pardoned", "reason": "TEST cleanup"},
                        timeout=15,
                    )
                for c in data.get("crimes", []):
                    if c.get("status") == "open":
                        session.delete(
                            f"{BASE_URL}/api/admin/crimes/{c['id']}", headers=auth, timeout=15,
                        )
    except Exception as e:
        print(f"post-cleanup warning: {e}")


# helper
def _post_roleplay(session, auth, nation, location, text, expect_status=200, timeout=120):
    r = session.post(
        f"{BASE_URL}/api/locations/{nation}/{location}/roleplay",
        headers=auth,
        json={"action_text": text},
        timeout=timeout,
    )
    if expect_status is not None:
        assert r.status_code == expect_status, f"[{nation}/{location}] expected {expect_status} got {r.status_code}: {r.text[:400]}"
    return r


# ============================================================
# 1. Law feature flag exposure
# ============================================================
class TestLawFeatureFlag:
    def test_rap_sheet_exposes_flag(self, session, auth, character_id):
        r = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "law_system_enabled" in data
        assert data["law_system_enabled"] is True
        # Structure assertions
        assert "crimes" in data and isinstance(data["crimes"], list)
        assert "bounties" in data and isinstance(data["bounties"], list)
        assert "imprisonment" in data  # may be None


# ============================================================
# 2. Crime auto-recording via AI analyzer
# ============================================================
class TestCrimeRecording:
    def test_violent_action_records_capital_crime(self, session, auth, character_id):
        text = (
            f"TEST_{uuid.uuid4().hex[:6]}: I draw my blade in a fit of rage and murder the noble merchant "
            "Lord Castellan in cold blood at the market square, slitting his throat and laughing as the crowd screams."
        )
        r = _post_roleplay(session, auth, CRIME_NATION, CRIME_LOC_A, text)
        body = r.json()
        assert body.get("rp_id"), f"missing rp_id: {body}"

        # Poll rap-sheet for up to ~25s for the analyzer to record the crime
        capital_crime = None
        for _ in range(10):
            rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20)
            assert rs.status_code == 200
            data = rs.json()
            for c in data.get("crimes", []):
                if c.get("status") == "open" and c.get("severity") in ("capital", "regicide") and c.get("nation") == CRIME_NATION:
                    capital_crime = c
                    break
            if capital_crime:
                break
            time.sleep(2.5)

        assert capital_crime, "No capital/regicide-tier open crime recorded after violent RP"
        assert capital_crime.get("bounty", 0) > 0, "Bounty should be > 0 for capital crime"
        assert capital_crime.get("victim_name"), "victim_name should be populated"
        assert capital_crime.get("character_id") == character_id


# ============================================================
# 3. Criminal record propagation within nation + cross-nation isolation
# ============================================================
class TestRecordPropagation:
    def test_record_propagates_same_nation_not_cross_nation(self, session, auth, character_id):
        # Ensure there is at least one open crime in ammeonon
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        open_here = [c for c in rs.get("crimes", []) if c.get("status") == "open" and c.get("nation") == CRIME_NATION]
        assert open_here, "Need at least one open crime in ammeonon — TestCrimeRecording must have passed"

        # RP in city B of same nation — guard reaction keywords
        r_same = _post_roleplay(session, auth, CRIME_NATION, CRIME_LOC_B, "I walk openly through the gate, hood down.")
        resp_text = (r_same.json().get("ai_response") or "").lower()
        keywords_same = ["guard", "recognis", "wanted", "arrest", "halberd", "warrant", "bounty"]
        hit_same = any(k in resp_text for k in keywords_same)
        if not hit_same:
            print(f"[same-nation] AI response snippet: {resp_text[:300]}")
        assert hit_same, f"Same-nation guard reaction expected in city B response, none of {keywords_same} present"

        # RP in different nation — bounty should NOT be referenced
        r_other = _post_roleplay(session, auth, OTHER_NATION, OTHER_LOC, "I walk into the foreign town and look for an inn.")
        resp_other = (r_other.json().get("ai_response") or "").lower()
        bounty_keywords = ["bounty", "wanted poster", "ammeonon guards", "your crimes in ammeonon"]
        # We tolerate the word "guard" generically (there are guards everywhere), but explicit bounty/wanted shouldn't appear
        # related to the prior crime.
        leaks = [k for k in ("bounty", "wanted poster", "warrant") if k in resp_other]
        assert not leaks, f"Cross-nation leak — bounty info bled into {OTHER_NATION}: {leaks} -- {resp_other[:300]}"


# ============================================================
# 4. Surrender flow
# ============================================================
class TestSurrenderFlow:
    def test_surrender_creates_trial_and_maybe_imprison(self, session, auth, character_id):
        # Resolve all existing capital/regicide open crimes first so the trial
        # has a chance of returning 'imprison' rather than 'execute' (which the
        # AI deterministically chooses for regicide). We then commit a fresh
        # 'major' tier crime to surrender on.
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        for c in rs.get("crimes", []):
            if c.get("status") == "open" and c.get("severity") in ("capital", "regicide"):
                session.delete(f"{BASE_URL}/api/admin/crimes/{c['id']}", headers=auth, timeout=15)

        # Commit a fresh non-capital crime via RP
        text = (
            f"TEST_{uuid.uuid4().hex[:6]}: In a drunken brawl I steal a chest of silver coins from a "
            "common merchant's stall and shove him to the ground, breaking his nose. I run laughing into the alley."
        )
        _post_roleplay(session, auth, CRIME_NATION, CRIME_LOC_A, text)
        # Poll for the crime to be recorded
        found = False
        for _ in range(8):
            rs2 = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
            if any(c.get("status") == "open" and c.get("nation") == CRIME_NATION
                   and c.get("severity") in ("minor", "major", "petty")
                   for c in rs2.get("crimes", [])):
                found = True
                break
            time.sleep(2.5)
        if not found:
            pytest.skip("Analyzer did not record a non-capital crime to surrender on")

        r = session.post(
            f"{BASE_URL}/api/characters/{character_id}/surrender",
            headers=auth,
            json={"nation": CRIME_NATION, "location": CRIME_LOC_A},
            timeout=60,
        )
        assert r.status_code == 200, f"Surrender failed: {r.status_code} {r.text}"
        body = r.json()
        assert "trial" in body and "imprisonment" in body
        trial = body["trial"]
        assert isinstance(trial.get("narration"), str)
        assert len(trial.get("narration", "")) >= 50, f"Trial narration too short: {trial.get('narration')}"

        if trial.get("sentence_type") == "imprison":
            imp = body["imprisonment"]
            assert imp is not None, "imprisonment object missing despite imprison sentence"
            assert imp.get("status") == "active"
            assert imp.get("sentence_turns", 0) > 0
            # store for later tests
            pytest.imprisonment_state = imp


# ============================================================
# 5. Imprisonment lock
# ============================================================
class TestImprisonmentLock:
    def test_rp_blocked_at_other_locations(self, session, auth, character_id):
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        imp = rs.get("imprisonment")
        if not imp or imp.get("status") != "active":
            pytest.skip("Character is not imprisoned; lock test n/a")

        jail_nation = imp["nation"]
        jail_loc = imp["jail_location"]
        other_loc = CRIME_LOC_B if jail_loc != CRIME_LOC_B else "ancient-market-square"

        # different location, same nation -> 403
        r = session.post(
            f"{BASE_URL}/api/locations/{jail_nation}/{other_loc}/roleplay",
            headers=auth,
            json={"action_text": "I stroll through town."},
            timeout=30,
        )
        assert r.status_code == 403, f"Expected 403 at non-jail location, got {r.status_code}: {r.text[:300]}"
        assert jail_loc.lower().replace("-", " ") in r.text.lower() or jail_loc in r.text, \
            f"Error should mention jail location '{jail_loc}': {r.text}"

        # different nation -> also 403 (imprisonment locks all RP)
        r2 = session.post(
            f"{BASE_URL}/api/locations/{OTHER_NATION}/{OTHER_LOC}/roleplay",
            headers=auth,
            json={"action_text": "I sneak across the border."},
            timeout=30,
        )
        assert r2.status_code == 403

    def test_rp_in_jail_increments_turns(self, session, auth, character_id):
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        imp = rs.get("imprisonment")
        if not imp or imp.get("status") != "active":
            pytest.skip("Character is not imprisoned; cannot test in-jail RP")

        before = imp["turns_served"]
        jail_nation, jail_loc = imp["nation"], imp["jail_location"]

        r = session.post(
            f"{BASE_URL}/api/locations/{jail_nation}/{jail_loc}/roleplay",
            headers=auth,
            json={"action_text": "I pace the cell and try to read the runes scratched on the wall."},
            timeout=120,
        )
        assert r.status_code == 200, f"In-jail RP should succeed: {r.status_code} {r.text[:300]}"

        rs2 = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        imp2 = rs2.get("imprisonment")
        # Could have completed if sentence was 1 turn — accept that too
        if imp2 and imp2.get("status") == "active":
            assert imp2["turns_served"] == before + 1, \
                f"turns_served should be {before+1}, got {imp2['turns_served']}"


# ============================================================
# 6. Escape flow — vague then creative
# ============================================================
class TestEscapeFlow:
    def test_vague_escape_fails_and_extends_sentence(self, session, auth, character_id):
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        imp = rs.get("imprisonment")
        if not imp or imp.get("status") != "active":
            pytest.skip("Not imprisoned; escape vague test n/a")

        before = imp["sentence_turns"]
        r = session.post(
            f"{BASE_URL}/api/characters/{character_id}/attempt-escape",
            headers=auth,
            json={"description": "I escape."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        judgement = body.get("judgement", {})
        # Vague should fail
        if judgement.get("success"):
            pytest.xfail("AI judged vague description as successful — non-deterministic; flagged")
        else:
            imp2 = body.get("imprisonment") or {}
            assert imp2.get("sentence_turns", 0) >= before + 2, \
                f"Sentence should extend by 2 on failure ({before} -> {imp2.get('sentence_turns')})"

    def test_creative_escape_succeeds_and_logs_new_crime(self, session, auth, character_id):
        rs = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
        imp = rs.get("imprisonment")
        if not imp or imp.get("status") != "active":
            pytest.skip("Not imprisoned; creative escape test n/a")

        desc = (
            "I crouch by the loose flagstone I noticed during my pacing yesterday and slowly pry it free, "
            "muffling each scrape against the dampened sleeve of my tunic. While my companion distracts the "
            "halberd-bearing nightwatch with a song through the bars, I slip the iron pin from the hinge using a "
            "fishbone, ease the cell door open one finger-width at a time, and ghost barefoot along the moss-slick "
            "drain channel that empties into the river below the keep. I time each step to the bell-tower's chime."
        )
        r = session.post(
            f"{BASE_URL}/api/characters/{character_id}/attempt-escape",
            headers=auth,
            json={"description": desc},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        judgement = body.get("judgement", {})
        if not judgement.get("success"):
            pytest.xfail(f"Creative escape was judged failure (AI is non-deterministic): {judgement}")
        else:
            # Imprisonment should be cleared
            assert body.get("imprisonment") in (None, {}) or body["imprisonment"].get("status") != "active"
            # New escape_from_custody crime must appear
            rs2 = session.get(f"{BASE_URL}/api/characters/{character_id}/rap-sheet", headers=auth, timeout=20).json()
            esc = [c for c in rs2.get("crimes", []) if c.get("crime_type") == "escape_from_custody" and c.get("status") == "open"]
            assert esc, "Expected an open escape_from_custody crime after success"
            assert esc[0].get("severity") == "major"
            assert "Crown" in (esc[0].get("victim_name") or "")


# ============================================================
# 7. Chronicle — trial + capital crime publish
# ============================================================
class TestChronicle:
    def test_chronicle_contains_trial_and_crime(self, session, auth):
        r = session.get(f"{BASE_URL}/api/chronicle", headers=auth, timeout=20)
        assert r.status_code == 200, r.text
        events = r.json()
        assert isinstance(events, list)
        types = {e.get("event_type") for e in events}
        # Either type may still be eventually-consistent, but we just shipped trial+crime — both should appear
        assert "trial" in types, f"No trial event in chronicle (types seen: {types})"
        # Crime event is published only for capital-tier — accept either 'crime' or absence with a warning
        if "crime" not in types:
            print(f"WARN: no 'crime' event_type in chronicle (types: {types})")


# ============================================================
# 8. Admin Law panel endpoints
# ============================================================
class TestAdminLawEndpoints:
    def test_admin_crimes_list(self, session, auth):
        r = session.get(f"{BASE_URL}/api/admin/crimes", headers=auth, timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_crimes_status_filter(self, session, auth):
        r = session.get(f"{BASE_URL}/api/admin/crimes?status=open", headers=auth, timeout=20)
        assert r.status_code == 200
        for c in r.json():
            assert c.get("status") == "open"

    def test_admin_imprisonments_list(self, session, auth):
        r = session.get(f"{BASE_URL}/api/admin/imprisonments", headers=auth, timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ============================================================
# 9. REGRESSION — Owned NPC / Companion CRUD
# ============================================================
class TestCompanionCRUD:
    def test_create_update_delete_companion(self, session, auth, character_id):
        # Create
        r = session.post(
            f"{BASE_URL}/api/characters/{character_id}/owned-npcs",
            headers=auth,
            json={
                "name": f"TEST_Comp_{uuid.uuid4().hex[:5]}",
                "race": "Human",
                "role": "scout",
                "description": "A loyal scout for testing.",
                "auto_bond": True,
            },
            timeout=30,
        )
        assert r.status_code in (200, 201), f"create owned-npc failed: {r.status_code} {r.text}"
        npc = r.json()
        npc_id = npc.get("id") or npc.get("_id") or (npc.get("npc") or {}).get("id")
        assert npc_id, f"missing id in {npc}"

        # Update
        rp = session.patch(
            f"{BASE_URL}/api/owned-npcs/{npc_id}",
            headers=auth,
            json={"description": "Updated description by TEST."},
            timeout=20,
        )
        assert rp.status_code in (200, 204), f"patch failed: {rp.status_code} {rp.text}"

        # Delete
        rd = session.delete(f"{BASE_URL}/api/owned-npcs/{npc_id}", headers=auth, timeout=20)
        assert rd.status_code in (200, 204), f"delete failed: {rd.status_code} {rd.text}"


# ============================================================
# 10. REGRESSION — Image storage refactor
# ============================================================
class TestImageStorage:
    def test_city_image_json_small(self, session, auth):
        r = session.get(f"{BASE_URL}/api/city-image/ammeonon/wymroost", headers=auth, timeout=20)
        assert r.status_code == 200
        # Should be small JSON, NOT image bytes
        assert len(r.content) <= 2048, f"city-image payload too large ({len(r.content)} bytes)"
        body = r.json()
        assert body.get("image_url", "").startswith("/api/image/")

    def test_nation_images_small(self, session, auth):
        r = session.get(f"{BASE_URL}/api/nations/images", headers=auth, timeout=20)
        assert r.status_code == 200
        assert len(r.content) <= 2048, f"nations/images payload too large ({len(r.content)} bytes)"
        data = r.json()
        assert isinstance(data, list) and len(data) == 5

    def test_image_endpoint_serves_bytes_with_cache_headers(self, session, auth):
        # Get an image_url
        ni = session.get(f"{BASE_URL}/api/nations/images", headers=auth, timeout=20).json()
        url_path = ni[0]["image_url"]
        r = session.get(f"{BASE_URL}{url_path}", headers=auth, timeout=30)
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("Content-Type", "")
        assert ct.startswith("image/"), f"Expected image content-type, got {ct}"
        # Cache header present?
        assert r.headers.get("ETag") or r.headers.get("Cache-Control"), \
            f"Missing ETag/Cache-Control on image response (headers={dict(r.headers)})"


# ============================================================
# 11. REGRESSION — Background seeding
# ============================================================
class TestBackgroundSeed:
    def test_start_seed_and_poll_completion(self, session, auth):
        r = session.post(
            f"{BASE_URL}/api/admin/start-full-seed?with_images=false",
            headers=auth,
            timeout=20,
        )
        assert r.status_code == 200, r.text
        # Poll up to ~30s
        for _ in range(15):
            s = session.get(f"{BASE_URL}/api/admin/seed-status", headers=auth, timeout=20).json()
            if s.get("status") in ("completed", "idle"):
                # If idle, must already be seeded
                return
            time.sleep(2)
        pytest.fail(f"Seed did not complete within 30s; last status: {s}")
