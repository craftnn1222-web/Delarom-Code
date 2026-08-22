"""Image batch (city/location artwork) verification + prayer/tongue regression."""
import os
import re
import time
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
TIMEOUT = 60


@pytest.fixture(scope="module")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    password = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    assert email and password, "admin creds not found"
    return {"email": email.group(1), "password": password.group(1)}


@pytest.fixture(scope="module")
def admin_client(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": creds["email"], "password": creds["password"]}, timeout=TIMEOUT)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token in login response: {r.text[:300]}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def _get_retry(client, path, attempts=4):
    last = None
    for i in range(attempts):
        try:
            r = client.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            last = f"{r.status_code}: {r.text[:200]}"
        except Exception as e:  # transient ingress timeout while batcher hogs loop
            last = str(e)
        time.sleep(3)
    pytest.fail(f"GET {path} failed after {attempts} attempts -> {last}")


# ── Batch status ───────────────────────────────────────────────────────────
class TestImageBatchStatus:
    def test_status_running_and_generating(self, admin_client):
        data = _get_retry(admin_client, "/api/admin/image-batch/status").json()
        print("STATUS:", {k: v for k, v in data.items() if k != "last_results"})
        assert data["auto_continue"] is True, "auto_continue not enabled"
        assert data["generated"] > 0, "no images generated"
        assert data["last_error"] is None, f"last_error set: {data['last_error']}"
        assert data["is_running"] is True, f"batch not running; stopped_reason={data.get('stopped_reason')}"

    def test_failure_rate_low(self, admin_client):
        data = _get_retry(admin_client, "/api/admin/image-batch/status").json()
        total = data["generated"] + data["failed"]
        assert total > 0
        rate = data["failed"] / total
        print(f"generated={data['generated']} failed={data['failed']} fail_rate={rate:.2%}")
        assert rate < 0.2, f"high failure rate {rate:.2%}"

    def test_survey_progress(self, admin_client):
        first = _get_retry(admin_client, "/api/admin/image-batch/survey").json()
        print("SURVEY t0:", first)
        assert first["total_missing"] < 874, "total_missing has not decreased from ~874 baseline"
        time.sleep(45)
        second = _get_retry(admin_client, "/api/admin/image-batch/survey").json()
        print("SURVEY t1:", second)
        assert second["total_missing"] < first["total_missing"], (
            f"no forward progress in 45s: {first['total_missing']} -> {second['total_missing']}"
        )

    def test_status_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/image-batch/status", timeout=TIMEOUT)
        assert r.status_code in (401, 403), r.status_code


# ── Persisted artwork ──────────────────────────────────────────────────────
class TestPersistedArtwork:
    def test_city_list_has_images(self, admin_client):
        r = _get_retry(admin_client, "/api/cities/ammeonon")
        cities = r.json()
        assert isinstance(cities, list) and cities
        with_image = [c for c in cities if c.get("has_image")]
        print(f"ammeonon cities={len(cities)} has_image={len(with_image)}")
        assert with_image, "no ammeonon city reports has_image"

    def test_city_detail_image_is_data_url_or_blob(self, admin_client):
        cities = _get_retry(admin_client, "/api/cities/ammeonon").json()
        target = next((c for c in cities if c.get("has_image")), None)
        assert target, "no city with image"
        detail = _get_retry(admin_client, f"/api/cities/ammeonon/{target['slug']}").json()
        img = detail.get("image_url") or ""
        image_id = detail.get("image_id")
        print(f"city={target['slug']} image_url_prefix={img[:30]!r} len={len(img)} image_id={image_id}")
        assert img.startswith("data:image/") or image_id, "city has neither base64 image_url nor image_id"
        if img.startswith("data:image/"):
            assert len(img) > 10000, "image_url suspiciously small (placeholder?)"


# ── Regression: prayers + tongue of yros under load ────────────────────────
class TestRegressionUnderLoad:
    def test_prayers_gods(self):
        r = requests.get(f"{BASE_URL}/api/prayers/gods", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        gods = data if isinstance(data, list) else data.get("gods", [])
        names = " ".join(str(g.get("name", g)) for g in gods).lower()
        print("gods:", names)
        assert len(gods) == 4, f"expected 4 gods, got {len(gods)}"
        for expected in ("seren", "yros", "uesis", "ehena"):
            assert expected in names, f"missing god {expected}"

    def test_tongue_of_yros_state(self):
        r = requests.get(f"{BASE_URL}/api/tongue-of-yros/state", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:200]
        state = r.json()
        print("tongue state keys:", list(state.keys()))
        assert isinstance(state, dict) and state
