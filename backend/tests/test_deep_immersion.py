"""Deep Immersion arc live-API regression tests.

Covers: Prayer catalogue/submit/cooldown/validation/history (Tier 2a),
Tongue of Y'ros trial, admin image-batch endpoints, seed endpoints,
and 215 A.E. lore presence in quest_master_ai.py.
"""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

TIMEOUT = 120


# ───────────────────────────── fixtures ─────────────────────────────
@pytest.fixture(scope="session")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*Email:\s*`?([^`\s]+)', content).group(1)
    password = re.search(r'(?im)^\s*[-*]?\s*Password:\s*`?([^`\s]+)', content).group(1)
    return {"email": email, "password": password}


@pytest.fixture(scope="session")
def admin(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=TIMEOUT)
    if r.status_code != 200:
        pytest.fail(f"Admin login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token in login response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def characters(admin):
    r = admin.get(f"{BASE_URL}/api/characters", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    chars = data if isinstance(data, list) else data.get("characters", [])
    assert chars, "admin has no characters — cannot run prayer tests"
    return chars


@pytest.fixture(scope="session")
def elf_char(characters):
    for c in characters:
        if "elf" in (c.get("race") or "").lower():
            return c
    pytest.skip("no elf-race character available for admin")


@pytest.fixture(scope="session")
def non_dwarf_char(characters):
    for c in characters:
        if "dwarf" not in (c.get("race") or "").lower():
            return c
    pytest.skip("no non-dwarf character available")


# ───────────────────────── Prayer catalogue ─────────────────────────
class TestPrayerCatalogue:
    def test_gods_public_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/prayers/gods", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        gods = r.json()["gods"]
        keys = {g["key"] for g in gods}
        assert keys == {"seren", "yros", "uesis", "ehena"}, keys
        for g in gods:
            assert g["name"] and g["title"] and g["domain"]
            assert isinstance(g["race_affinity"], list)


# ───────────────────── Prayer submit / cooldown ─────────────────────
class TestPrayerFlow:
    def test_submit_prayer_elf_seren(self, admin, elf_char, mongo):
        # clear prior prayers for this character so cooldown logic is testable
        mongo.prayers.delete_many({"character_id": elf_char["id"]})
        payload = {
            "character_id": elf_char["id"],
            "god": "seren",
            "prayer_text": (
                "Mother Seren, I kneel among the roots and ask nothing for myself. "
                "Let the wounded of my village mend, let the green return to our "
                "orchards, and let life persist where the blight has walked."
            ),
        }
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert d["verdict"] in {"silence", "flicker", "blessing"}, d["verdict"]
        assert d["affinity_match"] is True
        assert isinstance(d["narration"], str) and len(d["narration"]) > 0
        assert d["id"] and d["god"] == "seren" and d["god_name"] == "Seren"
        assert d["prayed_at"]
        if d["verdict"] == "silence":
            assert d["expires_at"] is None
        else:
            assert d["expires_at"]
        assert "_id" not in d
        assert d.get("judgement_reason") != "AI judgement unavailable; fallback verdict applied.", (
            "LLM call failed — fallback judgement returned"
        )

    def test_same_god_cooldown_409(self, admin, elf_char):
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": elf_char["id"],
            "god": "seren",
            "prayer_text": "Seren, hear me once again; I ask for the healing of my people and green fields.",
        }, timeout=TIMEOUT)
        assert r.status_code == 409, f"{r.status_code}: {r.text[:300]}"
        assert "already prayed to Seren recently" in r.json()["detail"]

    def test_different_god_allowed(self, admin, elf_char):
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": elf_char["id"],
            "god": "yros",
            "prayer_text": "Yros of the deep stone, I keep my oaths and honour the makers. Steady my hands at the anvil.",
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"per-god cooldown leaked: {r.status_code} {r.text[:300]}"
        d = r.json()
        assert d["god"] == "yros" and d["god_name"] == "Yros"
        assert d["verdict"] in {"silence", "flicker", "blessing"}

    def test_short_prayer_rejected(self, admin, elf_char):
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": elf_char["id"], "god": "uesis", "prayer_text": "help",
        }, timeout=TIMEOUT)
        # Pydantic min_length=10 rejects with 422; service-level check would be 409.
        assert r.status_code in (409, 422), f"{r.status_code}: {r.text[:300]}"

    def test_unknown_god_400(self, admin, elf_char):
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": elf_char["id"], "god": "loki",
            "prayer_text": "Trickster, hear my long and heartfelt plea for mischief and fortune.",
        }, timeout=TIMEOUT)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:300]}"
        assert "Unknown god" in r.json()["detail"]

    def test_bad_character_404(self, admin):
        r = admin.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": "TEST_does_not_exist", "god": "seren",
            "prayer_text": "Seren, hear this prayer from nowhere and no one at all please.",
        }, timeout=TIMEOUT)
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"

    def test_unauthenticated_submit_rejected(self, elf_char):
        r = requests.post(f"{BASE_URL}/api/prayers/submit", json={
            "character_id": elf_char["id"], "god": "seren",
            "prayer_text": "An anonymous prayer that should never be accepted by the server.",
        }, timeout=TIMEOUT)
        assert r.status_code in (401, 403), f"{r.status_code}: {r.text[:200]}"


# ───────────────────── Blessings / history ─────────────────────
class TestPrayerHistory:
    def test_active_blessings(self, admin, elf_char):
        r = admin.get(f"{BASE_URL}/api/prayers/character/{elf_char['id']}/active", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert "active_blessings" in body and isinstance(body["active_blessings"], list)
        for b in body["active_blessings"]:
            assert b["god"] and b["god_name"] and b["verdict"] in {"blessing", "flicker"}

    def test_character_history_sorted(self, admin, elf_char):
        r = admin.get(f"{BASE_URL}/api/prayers/character/{elf_char['id']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 2
        stamps = [x["prayed_at"] for x in rows]
        assert stamps == sorted(stamps, reverse=True), "history not newest-first"
        assert all("_id" not in x for x in rows)

    def test_history_other_character_404(self, admin):
        r = admin.get(f"{BASE_URL}/api/prayers/character/TEST_nope", timeout=TIMEOUT)
        assert r.status_code == 404

    def test_recent_prayers_across_characters(self, admin, elf_char):
        r = admin.get(f"{BASE_URL}/api/prayers/recent", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and rows
        assert any(x["character_id"] == elf_char["id"] for x in rows)
        stamps = [x["prayed_at"] for x in rows]
        assert stamps == sorted(stamps, reverse=True)


# ───────────────────── Tongue of Y'ros ─────────────────────
class TestTongueOfYros:
    def test_state_shape(self):
        r = requests.get(f"{BASE_URL}/api/tongue-of-yros/state", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("bearer_active", "bearer_character_id", "bearer_character_name", "bearer_drawn_at"):
            assert k in d, f"missing {k}"
        assert "_id" not in d

    def test_non_dwarf_attempt_silence(self, admin, non_dwarf_char, mongo):
        mongo.tongue_of_yros_attempts.delete_many({"character_id": non_dwarf_char["id"]})
        state = requests.get(f"{BASE_URL}/api/tongue-of-yros/state", timeout=TIMEOUT).json()
        r = admin.post(f"{BASE_URL}/api/tongue-of-yros/attempt", json={
            "character_id": non_dwarf_char["id"],
            "attempt_text": "I lay my hand upon the hilt and speak my name with all humility.",
        }, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert d["verdict"] == "silence", d
        if not state.get("bearer_active"):
            assert "This blade knows the hands of the earth-folk" in d["narration"], d["narration"]
        assert "_id" not in d

    def test_attempt_cooldown_409(self, admin, non_dwarf_char):
        r = admin.post(f"{BASE_URL}/api/tongue-of-yros/attempt", json={
            "character_id": non_dwarf_char["id"],
            "attempt_text": "Once more I reach for the ancient stone blade in the tomb.",
        }, timeout=TIMEOUT)
        assert r.status_code == 409, f"{r.status_code}: {r.text[:300]}"
        assert "must rest and gather your resolve" in r.json()["detail"]

    def test_attempt_history(self, admin, non_dwarf_char):
        r = admin.get(f"{BASE_URL}/api/tongue-of-yros/character/{non_dwarf_char['id']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 1
        assert rows[0]["character_id"] == non_dwarf_char["id"]
        assert rows[0]["verdict"] in {"silence", "tremor", "drawn"}

    def test_attempt_bad_character_404(self, admin):
        r = admin.post(f"{BASE_URL}/api/tongue-of-yros/attempt", json={
            "character_id": "TEST_nope", "attempt_text": "I reach for the blade of stone here.",
        }, timeout=TIMEOUT)
        assert r.status_code == 404

    def test_relinquish_non_bearer_409(self, admin, non_dwarf_char):
        r = admin.post(f"{BASE_URL}/api/tongue-of-yros/relinquish", json={
            "character_id": non_dwarf_char["id"],
        }, timeout=TIMEOUT)
        assert r.status_code == 409, f"{r.status_code}: {r.text[:300]}"


# ───────────────────── Image batcher (read-only) ─────────────────────
class TestImageBatch:
    def test_survey(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/image-batch/survey", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("cities_missing", "locations_missing", "total_missing", "batch_size"):
            assert k in d, f"missing {k}"
        assert d["total_missing"] == d["cities_missing"] + d["locations_missing"]

    def test_status(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/image-batch/status", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ("is_running", "auto_continue", "iterations_run", "generated", "failed"):
            assert k in d, f"missing {k}"
        assert isinstance(d["is_running"], bool)

    def test_survey_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/image-batch/survey", timeout=TIMEOUT)
        assert r.status_code in (401, 403)


# ───────────────────── Seed endpoints (idempotent) ─────────────────────
class TestSeeds:
    def test_dhor_kuldor_canon_idempotent(self, admin):
        r1 = admin.post(f"{BASE_URL}/api/admin/seed-dhor-kuldor-canon", timeout=TIMEOUT)
        assert r1.status_code == 200, r1.text[:500]
        c1 = r1.json()["cities"]
        assert c1["total_processed"] == 6, c1
        r2 = admin.post(f"{BASE_URL}/api/admin/seed-dhor-kuldor-canon", timeout=TIMEOUT)
        assert r2.status_code == 200, r2.text[:500]
        c2 = r2.json()["cities"]
        assert c2["total_processed"] == 6
        # inserted/updated are lists of city slugs
        assert len(c2["inserted"]) == 0 and len(c2["updated"]) == 6, f"not idempotent: {c2}"

    def test_titan_sacred_sites(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/seed-titan-sacred-sites", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        for k in ("annotated", "already_annotated", "not_found_count", "sites"):
            assert k in d, f"missing {k}"
        assert isinstance(d["sites"], list)

    def test_seed_requires_admin(self):
        r = requests.post(f"{BASE_URL}/api/admin/seed-dhor-kuldor-canon", timeout=TIMEOUT)
        assert r.status_code in (401, 403)


# ───────────────────── Lore / canon greps ─────────────────────
class TestCanonLore:
    def test_215_ae_in_quest_master(self):
        text = Path("/app/backend/quest_master_ai.py").read_text(encoding="utf-8")
        assert "215 A.E." in text

    def test_no_old_dhor_khuldor_slug(self):
        hits = []
        for p in list(Path("/app/backend").rglob("*.py")) + list(Path("/app/frontend/src").rglob("*.js")):
            if "migrate_rename_dhor_kuldor" in str(p) or "/tests/" in str(p):
                continue
            if "dhor-khuldor" in p.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(p))
        assert not hits, f"stale slug dhor-khuldor in {hits}"
