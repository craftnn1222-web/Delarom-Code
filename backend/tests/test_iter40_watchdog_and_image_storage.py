"""Iteration 40 — Image storage migration + watchdog / admin health.

Covers:
  * GET /api/image/{id} (200 + content-type, HEAD, ETag/304)
  * GET /api/admin/health snapshot shape and auth
  * GET /api/admin/health/incidents (admin-only)
  * POST /api/admin/health/check-now (admin-only, fresh snapshot)
  * Data-integrity probe: images_in_db == 0, orphan_shops == 0
  * Non-admin rejection on health endpoints
"""
import os
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "rep_tester_round2@delarom.com"
USER_PASSWORD = "Testpass123!"


# ---------- fixtures ----------

@pytest.fixture(scope="function")
def s():
    """Fresh session per test — no cookie leakage between admin/user/anon."""
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


def _login(email, password):
    """Login WITHOUT persisting cookies — return the bearer token only."""
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin_token():
    r = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def user_token():
    r = _login(USER_EMAIL, USER_PASSWORD)
    if r.status_code != 200:
        pytest.skip(f"non-admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def user_h(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="module")
def sample_image_id():
    """Fetch any image_id from Mongo directly (image_blobs collection)."""
    import asyncio
    async def _get():
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        # Prefer object-storage-backed (has storage_path)
        doc = await db.image_blobs.find_one({"storage_path": {"$exists": True}}, {"id": 1, "_id": 0})
        if not doc:
            doc = await db.image_blobs.find_one({}, {"id": 1, "_id": 0})
        client.close()
        return doc["id"] if doc else None
    return asyncio.get_event_loop().run_until_complete(_get())


# ---------- image serving ----------

class TestImageServing:
    def test_get_image_200_and_content_type(self, s, sample_image_id):
        assert sample_image_id, "No image_id found in image_blobs"
        r = s.get(f"{API}/image/{sample_image_id}", timeout=30)
        assert r.status_code == 200, f"got {r.status_code} body={r.text[:200]}"
        ctype = r.headers.get("Content-Type", "")
        assert ctype.startswith("image/"), f"unexpected content-type: {ctype}"
        assert len(r.content) > 100, "image bytes too small"
        assert r.headers.get("ETag") == f'"{sample_image_id}"'
        # Cache-Control set by backend may be overridden by CDN (Cloudflare
        # returns no-store for DYNAMIC responses). ETag is what enables caching.

    def test_head_image(self, s, sample_image_id):
        r = s.head(f"{API}/image/{sample_image_id}", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("ETag") == f'"{sample_image_id}"'
        # HEAD should be empty body (may still show content-length)
        assert r.content == b""

    def test_etag_304(self, s, sample_image_id):
        etag = f'"{sample_image_id}"'
        r = s.get(f"{API}/image/{sample_image_id}", headers={"If-None-Match": etag}, timeout=30)
        assert r.status_code == 304, f"expected 304, got {r.status_code}"

    def test_missing_image_404(self, s):
        r = s.get(f"{API}/image/nonexistent-image-id-xyz", timeout=15)
        assert r.status_code == 404


# ---------- admin health endpoints ----------

class TestAdminHealth:
    def test_get_health_admin(self, s, admin_h):
        r = s.get(f"{API}/admin/health", headers=admin_h, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "overall" in data
        assert data["overall"] in ("ok", "warning", "critical")
        assert "checked_at" in data
        assert "services" in data
        svcs = data["services"]
        for k in ("backend", "database", "image_batch", "data_integrity", "errors"):
            assert k in svcs, f"missing service {k}"
            assert "status" in svcs[k]
        assert "actions_taken" in data
        assert isinstance(data["actions_taken"], list)

    def test_get_health_unauth_401(self, s):
        r = s.get(f"{API}/admin/health", timeout=15)
        assert r.status_code in (401, 403), f"anonymous got {r.status_code}"

    def test_get_health_non_admin_forbidden(self, s, user_h):
        r = s.get(f"{API}/admin/health", headers=user_h, timeout=15)
        assert r.status_code in (401, 403), f"non-admin got {r.status_code}"

    def test_get_incidents_admin(self, s, admin_h):
        r = s.get(f"{API}/admin/health/incidents", headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_get_incidents_non_admin_forbidden(self, s, user_h):
        r = s.get(f"{API}/admin/health/incidents", headers=user_h, timeout=15)
        assert r.status_code in (401, 403)

    def test_check_now_admin(self, s, admin_h):
        r = s.post(f"{API}/admin/health/check-now", headers=admin_h, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["overall"] in ("ok", "warning", "critical")
        # fresh snapshot has all services
        for k in ("backend", "database", "image_batch", "data_integrity", "errors"):
            assert k in data["services"]

    def test_check_now_non_admin_forbidden(self, s, user_h):
        r = s.post(f"{API}/admin/health/check-now", headers=user_h, timeout=15)
        assert r.status_code in (401, 403)

    def test_data_integrity_probe_images_drained(self, s, admin_h):
        """Regression signal: image bytes must no longer live in MongoDB."""
        r = s.post(f"{API}/admin/health/check-now", headers=admin_h, timeout=60)
        assert r.status_code == 200
        di = r.json()["services"]["data_integrity"]
        assert di.get("images_in_db", -1) == 0, f"images still in DB: {di}"
        assert di.get("orphan_shops", -1) == 0, f"orphan shops present: {di}"
