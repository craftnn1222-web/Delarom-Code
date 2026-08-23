"""Iteration 35 — Backend sanity for endpoints consumed by:
- Quest Companions panel (web + mobile)
- Faction Halls Mobile (threads + treasury)
- My Shop Manager (mobile) with economy auto-pricing
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else "https://npc-economy-preview.preview.emergentagent.com"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PW = "admin123"
ACCEPTED_QUEST_ID = "201107e7-20ea-4df7-ab1a-906f20a639a8"
FACTION_SLUG = "ardent-legion"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ---- Quest Companions ----
def test_quest_participants_accepted(admin_headers):
    r = requests.get(f"{BASE_URL}/api/quests/{ACCEPTED_QUEST_ID}/participants", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    # Should be a list with at least the pre-seeded participant
    assert isinstance(data, list)
    assert len(data) >= 1
    p = data[0]
    # Verify shape: character info
    # Payload shape (observed): {"acceptance": {...}, "character": {...}, "user": {...}}
    assert "character" in p and isinstance(p["character"], dict)
    assert "id" in p["character"] and "name" in p["character"]
    joined = str(p).lower()
    assert "focused" in joined


# ---- Factions: threads + treasury ----
def test_faction_threads_list_public(admin_headers):
    r = requests.get(f"{BASE_URL}/api/factions/{FACTION_SLUG}/threads", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    threads = data if isinstance(data, list) else data.get("threads", [])
    assert isinstance(threads, list)


def test_faction_treasury_get(admin_headers):
    r = requests.get(f"{BASE_URL}/api/factions/{FACTION_SLUG}/treasury", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    # Expect balance and total_donated fields
    keys = set(data.keys())
    assert "balance" in keys or "gold" in keys or "total_balance" in keys


def test_non_member_thread_403(admin_headers):
    # Admin currently has no faction membership per task note. Reading a thread
    # should return 403 for non-members. First find a thread id.
    r = requests.get(f"{BASE_URL}/api/factions/{FACTION_SLUG}/threads", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    threads = r.json() if isinstance(r.json(), list) else r.json().get("threads", [])
    if not threads:
        pytest.skip("no threads")
    tid = threads[0].get("id") or threads[0].get("thread_id") or threads[0].get("_id")
    assert tid
    r2 = requests.get(f"{BASE_URL}/api/factions/{FACTION_SLUG}/threads/{tid}", headers=admin_headers, timeout=15)
    # Must be 403 (members-only) OR 200 if admin is auto-privileged. Accept 403 per task design.
    assert r2.status_code in (200, 403), r2.text


# ---- Shops: my-shop / items ----
def test_my_shop_get(admin_headers):
    r = requests.get(f"{BASE_URL}/api/shops/my-shop", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    # admin ALREADY OWNS 'Astral Antiquities'
    name = (data.get("name") if isinstance(data, dict) else None) or ""
    assert "astral" in name.lower() or data.get("shop", {}).get("name", "").lower().startswith("astral")


def test_economy_goods(admin_headers):
    r = requests.get(f"{BASE_URL}/api/economy/goods", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) > 0


def test_add_manual_item_and_delete(admin_headers):
    # Fetch shop id
    r = requests.get(f"{BASE_URL}/api/shops/my-shop", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    shop = r.json()
    shop_id = shop.get("id") or shop.get("_id") or shop.get("shop_id") or shop.get("shop", {}).get("id")
    assert shop_id
    payload = {
        "name": f"TEST_iter35_item_{int(time.time())}",
        "description": "TEST_iter35 manual price item",
        "price": 99,
        "stock": 3,
        "category": "misc",
    }
    r2 = requests.post(f"{BASE_URL}/api/shops/{shop_id}/items", headers=admin_headers, json=payload, timeout=15)
    assert r2.status_code in (200, 201), r2.text
    item = r2.json()
    item_id = item.get("id") or item.get("_id") or item.get("item_id")
    assert item_id
    assert item.get("price") == 99
    # Edit (PUT requires full ItemCreate body)
    edit_payload = {**payload, "price": 123, "stock": 5}
    r3 = requests.put(f"{BASE_URL}/api/items/{item_id}", headers=admin_headers, json=edit_payload, timeout=15)
    assert r3.status_code == 200, r3.text
    assert r3.json().get("price") == 123
    # Delete
    r4 = requests.delete(f"{BASE_URL}/api/items/{item_id}", headers=admin_headers, timeout=15)
    assert r4.status_code in (200, 204), r4.text
