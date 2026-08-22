"""Iteration 31 — Validate the image storage refactor.

Covers:
  - GET /api/admin/image-batch/survey (admin-only)
  - GET /api/admin/image-batch/status (admin-only)
  - POST /api/admin/shrink-image-storage (admin-only, idempotent)
  - GET /api/cities/aigraels/vargath — small payload with /api/image/<id> ref
  - GET /api/cities?nation=aigraels — no data: URLs
  - GET /api/image/<id> — serves image bytes
"""
import os
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://npc-economy-preview.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Admin image-batch endpoints ────────────────────────────────────
class TestImageBatchAdmin:
    def test_survey_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/image-batch/survey", timeout=15)
        assert r.status_code in (401, 403)

    def test_survey_returns_shape(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/image-batch/survey",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("cities_missing", "locations_missing", "total_missing"):
            assert k in data, f"missing field {k} in {data}"
            assert isinstance(data[k], int)
        assert data["total_missing"] == data["cities_missing"] + data["locations_missing"]

    def test_status_returns_shape(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/image-batch/status",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Must at least contain is_running flag
        assert "is_running" in data
        assert isinstance(data["is_running"], bool)


# ─── Shrink endpoint ────────────────────────────────────────────────
class TestShrinkImageStorage:
    def test_shrink_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/shrink-image-storage?limit=50", timeout=15)
        assert r.status_code in (401, 403)

    def test_shrink_returns_shape(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/shrink-image-storage?limit=50",
                          headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("worked_on", "migrated_this_call", "remaining_by_collection", "total_remaining", "done"):
            assert k in data, f"missing key {k} in {data}"
        assert isinstance(data["migrated_this_call"], int)
        assert isinstance(data["total_remaining"], int)
        assert isinstance(data["done"], bool)
        rbc = data["remaining_by_collection"]
        for coll in ("locations", "cities", "nations"):
            assert coll in rbc, f"missing collection {coll} in {rbc}"

    def test_shrink_is_idempotent(self, admin_headers):
        # Call twice, second call should be safe (may already be done)
        r1 = requests.post(f"{BASE_URL}/api/admin/shrink-image-storage?limit=50",
                           headers=admin_headers, timeout=60)
        r2 = requests.post(f"{BASE_URL}/api/admin/shrink-image-storage?limit=50",
                           headers=admin_headers, timeout=60)
        assert r1.status_code == 200 and r2.status_code == 200
        # After 2 calls, remaining should be non-increasing
        assert r2.json()["total_remaining"] <= r1.json()["total_remaining"]


# ─── Hardened /cities endpoints ─────────────────────────────────────
class TestCitiesNoBase64:
    def test_get_city_vargath_small_and_ref(self):
        r = requests.get(f"{BASE_URL}/api/cities/aigraels/vargath", timeout=30)
        assert r.status_code == 200, r.text
        body_bytes = len(r.content)
        # Well under 5KB per requirement
        assert body_bytes < 5_000, f"city payload too large: {body_bytes} bytes"
        data = r.json()
        img = data.get("image_url")
        # Must NOT be a base64 blob
        assert not (img and str(img).startswith("data:")), f"image_url still embedded: {str(img)[:60]}"
        # Should be a /api/image/<id> ref or None
        if img is not None:
            assert img.startswith("/api/image/"), f"unexpected image_url: {img}"

    def test_list_cities_no_data_urls(self):
        r = requests.get(f"{BASE_URL}/api/cities", params={"nation": "aigraels"}, timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        for city in items:
            img = city.get("image_url")
            if img:
                assert not str(img).startswith("data:"), f"data: URL leaked in list: {city.get('slug')}"
                assert img.startswith("/api/image/"), f"unexpected image_url: {img}"

    def test_image_endpoint_serves_bytes(self):
        # Fetch vargath, then GET its image_url and verify content-type is image/png
        r = requests.get(f"{BASE_URL}/api/cities/aigraels/vargath", timeout=30)
        assert r.status_code == 200
        img_url = r.json().get("image_url")
        if not img_url:
            pytest.skip("Vargath has no image yet; skipping bytes check")
        assert img_url.startswith("/api/image/")
        full = f"{BASE_URL}{img_url}"
        r2 = requests.get(full, timeout=30)
        assert r2.status_code == 200, f"image GET failed: {r2.status_code}"
        ctype = r2.headers.get("content-type", "")
        assert ctype.startswith("image/"), f"unexpected content-type: {ctype}"
        assert len(r2.content) > 100, "image bytes suspiciously small"
