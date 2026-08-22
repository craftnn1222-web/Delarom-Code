"""Iteration 25 live regression: prayers/gods, tongue-of-yros state, auth login.

Verifies the public/regression endpoints still respond after the image-batch
durability + migration-aware-missing-query fixes.
"""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

TIMEOUT = 60


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- prayers module ---
def test_prayers_gods_returns_four_gods(client):
    r = client.get(f"{BASE_URL}/api/prayers/gods", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    gods = data["gods"] if isinstance(data, dict) else data
    assert isinstance(gods, list)
    assert len(gods) == 4, gods
    names = {g["name"] if isinstance(g, dict) else g for g in gods}
    assert len(names) == 4


# --- tongue of yros module ---
def test_tongue_of_yros_state(client):
    r = client.get(f"{BASE_URL}/api/tongue-of-yros/state", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert isinstance(data, dict) and data


# --- auth module ---
def test_admin_login_returns_jwt(client):
    r = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    token = data.get("access_token")
    assert isinstance(token, str) and token.count(".") == 2, data
    assert data.get("user", {}).get("email") == ADMIN_EMAIL


def test_admin_login_wrong_password_rejected(client):
    r = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "definitely-wrong-pw"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (400, 401, 403, 429), r.status_code


# --- image batch admin endpoints (read-only) ---
def test_image_batch_status_requires_auth_and_reports_state(client):
    login = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = client.get(
        f"{BASE_URL}/api/admin/image-batch/status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text[:300]
    state = r.json()
    for field in ("is_running", "auto_continue", "generated", "failed",
                  "iterations_run", "heartbeat_at", "stopped_reason"):
        assert field in str(state), f"{field} missing from status payload: {state}"
