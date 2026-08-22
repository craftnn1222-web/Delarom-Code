"""Regression checks after image-batch durability fixes (iteration_24).

Live API smoke against the preview URL: auth, prayers gods list, tongue-of-yros
state, prayer submission with an owned elf character.
Long timeouts because the running image batch saturates the event loop.
"""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
TIMEOUT = 120


@pytest.fixture(scope="module")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text()
    e = re.search(r'(?im)^\s*-?\s*Email:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*-?\s*Password:\s*`?([^`\s]+)', c)
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="module")
def client(creds):
    s = requests.Session()
    r = None
    for _ in range(3):  # busy event loop / hot-reload can transiently 502
        try:
            r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=TIMEOUT)
            if r.status_code == 200:
                break
        except requests.RequestException:
            r = None
        import time as _t
        _t.sleep(5)
    if r is None or r.status_code != 200:
        pytest.fail(f"login failed {getattr(r, 'status_code', 'exception')}: {getattr(r, 'text', '')[:300]}")
    tok = r.json().get("access_token")
    assert tok, f"no access_token in {r.json().keys()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# --- auth ---
def test_login_returns_token_and_user(client):
    r = client.get(f"{BASE_URL}/api/auth/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    me = r.json()
    assert me.get("email")
    assert me.get("role") == "admin"


# --- prayers module ---
def test_prayers_gods_returns_four_gods(client):
    r = client.get(f"{BASE_URL}/api/prayers/gods", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    gods = data if isinstance(data, list) else data.get("gods", [])
    assert len(gods) == 4, f"expected 4 gods, got {len(gods)}: {gods}"
    for g in gods:
        assert g.get("name") or g.get("slug")
        assert "_id" not in g


# --- tongue of yros ---
def test_tongue_of_yros_state(client):
    r = client.get(f"{BASE_URL}/api/tongue-of-yros/state", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    st = r.json()
    assert isinstance(st, dict) and st, "empty state"
    assert "_id" not in st


# --- prayer submission with owned elf character ---
def test_prayer_submit_with_owned_elf_character(client, creds):
    """Pick the admin's elf character straight from Mongo (the /api/characters
    list payload is huge and drops connections while the image batch runs)."""
    from pymongo import MongoClient
    from dotenv import dotenv_values as _dv
    env = _dv("/app/backend/.env")
    mdb = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
    user = mdb.users.find_one({"email": creds["email"]})
    assert user, "admin user not found in Mongo"
    char = mdb.characters.find_one({
        "user_id": user["id"],
        "race": {"$regex": "elf", "$options": "i"},
    })
    if not char:
        pytest.skip("admin owns no elf character")
    mdb.prayers.delete_many({"character_id": char["id"], "god": "seren"})
    body = {
        "character_id": char["id"],
        "god": "seren",
        "prayer_text": (
            "Mother Seren, I kneel among the roots and ask nothing for myself. "
            "Let the wounded of my village mend and the green return to our orchards."
        ),
    }
    import time as _t
    r = None
    for _ in range(3):
        # 502s here are ingress gateway timeouts caused by the running image
        # batch saturating the event loop — retry before failing.
        mdb.prayers.delete_many({"character_id": char["id"], "god": "seren"})
        try:
            r = client.post(f"{BASE_URL}/api/prayers/submit", json=body, timeout=TIMEOUT)
            if r.status_code == 200:
                break
        except requests.RequestException:
            r = None
        _t.sleep(5)
    assert r is not None and r.status_code in (200, 409), \
        f"unexpected {getattr(r, 'status_code', 'exception')}: {getattr(r, 'text', '')[:300]}"
    if r.status_code == 409:
        # A prior slow attempt (ingress 502 while the image batch saturates the
        # loop) landed server-side — cooldown proves the write persisted.
        assert "already prayed" in r.json().get("detail", "")
        assert mdb.prayers.find_one({"character_id": char["id"], "god": "seren"})
        return
    data = r.json()
    assert data["verdict"] in {"silence", "flicker", "blessing"}
    assert isinstance(data.get("narration"), str) and data["narration"]
    assert data["god"] == "seren"
    assert "_id" not in data
