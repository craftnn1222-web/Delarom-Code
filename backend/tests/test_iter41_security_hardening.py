"""
Iteration 41 — Deployment-readiness security hardening regression.

Verifies that the previously-public bootstrap endpoints
(reset-and-seed / populate-* / initialize*) now require admin auth:
  - anonymous  -> 401
  - non-admin  -> 403
  - (admin path is NOT invoked — those handlers are destructive/mutating.)

Also runs regressions on:
  - public reads (db-status, factions, health) still 200
  - normal auth flow still works (login + /auth/me for admin & non-admin)
  - admin-guard on a non-destructive admin route
    (/admin/image-batch/status): 200 admin, 403 non-admin, 401 anon
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
NONADMIN_EMAIL = "rep_tester_round2@delarom.com"
NONADMIN_PASSWORD = "Testpass123!"

# (method, path) tuples for the 8 locked-down legacy bootstrap endpoints.
GATED_ENDPOINTS = [
    ("POST", "/api/reset-and-seed"),
    ("GET",  "/api/populate-full/ammeonon"),
    ("GET",  "/api/populate-locations/ammeonon"),
    ("GET",  "/api/populate-all-nations"),
    ("GET",  "/api/initialize"),
    ("GET",  "/api/initialize/nations-images"),
    ("GET",  "/api/initialize/city-images/ammeonon"),
    ("GET",  "/api/initialize/location-images/ammeonon"),
]


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def anon_session():
    s = requests.Session()
    # IMPORTANT: cookies from a prior login could leak in. Use a fresh jar.
    s.cookies.clear()
    return s


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "access_token" in data and data["access_token"], "no access_token in login response"
    return data["access_token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def nonadmin_token() -> str:
    return _login(NONADMIN_EMAIL, NONADMIN_PASSWORD)


def _request_no_cookies(method: str, url: str, *, headers=None, timeout=30):
    """Fire a request with an empty cookie jar so we don't accidentally carry
    an httpOnly `access_token` cookie from an earlier login."""
    s = requests.Session()
    s.cookies.clear()
    return s.request(method, url, headers=headers or {}, timeout=timeout, allow_redirects=False)


# ---------- regressions on public reads ----------

class TestPublicReads:
    def test_health(self):
        # /health is app-root, but /api/health may also exist. Try both, one must be 200.
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        if r.status_code == 404:
            r = requests.get(f"{BASE_URL}/health", timeout=15)
        assert r.status_code == 200, f"health check failed: {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("status") in ("healthy", "ok"), f"unexpected health payload: {body}"

    def test_db_status(self):
        r = requests.get(f"{BASE_URL}/api/db-status", timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert "counts" in data
        for k in ("nations", "cities", "locations", "users"):
            assert k in data["counts"], f"missing count key {k}"
            assert isinstance(data["counts"][k], int)

    def test_factions_public(self):
        r = requests.get(f"{BASE_URL}/api/factions", timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        # Should be a list (possibly empty).
        assert isinstance(r.json(), list)


# ---------- security hardening: anonymous access rejected ----------

class TestGatedEndpointsAnonymous:
    @pytest.mark.parametrize("method,path", GATED_ENDPOINTS)
    def test_anonymous_returns_401(self, method, path):
        r = _request_no_cookies(method, f"{BASE_URL}{path}")
        assert r.status_code == 401, (
            f"{method} {path} expected 401 for anonymous, got {r.status_code}. "
            f"Body: {r.text[:300]}"
        )


# ---------- security hardening: non-admin access rejected ----------

class TestGatedEndpointsNonAdmin:
    @pytest.mark.parametrize("method,path", GATED_ENDPOINTS)
    def test_nonadmin_returns_403(self, method, path, nonadmin_token):
        headers = {"Authorization": f"Bearer {nonadmin_token}"}
        r = _request_no_cookies(method, f"{BASE_URL}{path}", headers=headers)
        assert r.status_code == 403, (
            f"{method} {path} expected 403 for non-admin, got {r.status_code}. "
            f"Body: {r.text[:300]}"
        )


# ---------- regression: auth flow ----------

class TestAuthFlow:
    def test_admin_me(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("email") == ADMIN_EMAIL
        assert body.get("role") == "admin"
        assert body.get("status") == "active"

    def test_nonadmin_me(self, nonadmin_token):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {nonadmin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("email") == NONADMIN_EMAIL
        assert body.get("role") != "admin", "test user should not be admin"

    def test_me_anonymous_401(self):
        r = _request_no_cookies("GET", f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401


# ---------- regression: admin route still guards correctly ----------

class TestAdminImageBatchStatusGuard:
    URL = "/api/admin/image-batch/status"

    def test_admin_200(self, admin_token):
        r = _request_no_cookies(
            "GET", f"{BASE_URL}{self.URL}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        # Some kind of JSON body is expected.
        r.json()

    def test_nonadmin_403(self, nonadmin_token):
        r = _request_no_cookies(
            "GET", f"{BASE_URL}{self.URL}",
            headers={"Authorization": f"Bearer {nonadmin_token}"},
        )
        assert r.status_code == 403, f"{r.status_code} {r.text[:300]}"

    def test_anonymous_401(self):
        r = _request_no_cookies("GET", f"{BASE_URL}{self.URL}")
        assert r.status_code == 401, f"{r.status_code} {r.text[:300]}"
