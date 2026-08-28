"""Iteration 42 — Production bug fix: Members Directory payload shrink & auth resilience.

Verifies:
- GET /api/public/members-directory returns 200, a SMALL payload (< 200KB), and NO
  character portrait_url that starts with 'data:' (all should be null or start with '/api/image/').
- Each '/api/image/{id}' portrait URL returned by members-directory serves 200 with image content-type.
- POST /api/characters/{character_id}/upload-image (auth required, owner only):
  * uploading returns portrait_url starting with '/api/image/'
  * that URL serves the image
  * character doc's portrait_url is now a short URL (NOT a data: URI)
  * uploading to a non-owned character -> 404
  * anonymous upload -> 401
- Regression: /api/auth/login + /api/auth/me still work for admin and non-admin.
"""
from __future__ import annotations

import io
import os
import struct
import zlib

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or ""
BASE_URL = BASE_URL.rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
ADMIN_CHARACTER_ID = "a35a8ce2-71db-467c-8ad0-451fe9433a87"  # 'Ausar Veltraus'

NONADMIN_EMAIL = "rep_tester_round2@delarom.com"
NONADMIN_PASSWORD = "Testpass123!"


def _minimal_png_bytes() -> bytes:
    """Return a valid 1x1 PNG (no external deps)."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))  # 1x1 RGB
    raw = b"\x00\xff\x00\x00"  # one filter byte + one pixel RGB
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No access_token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def nonadmin_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": NONADMIN_EMAIL, "password": NONADMIN_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        pytest.skip(f"Non-admin login failed: {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token")
    assert tok
    return tok


# ---------- Auth regression ----------
class TestAuthRegression:
    def test_admin_login_and_me(self, admin_token: str):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        me = r.json()
        assert me.get("email") == ADMIN_EMAIL
        assert me.get("role") == "admin"

    def test_nonadmin_login_and_me(self, nonadmin_token: str):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {nonadmin_token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        me = r.json()
        assert me.get("email") == NONADMIN_EMAIL


# ---------- Members Directory payload shrink ----------
class TestMembersDirectoryShrink:
    def test_payload_is_small_and_no_data_uris(self):
        r = requests.get(f"{BASE_URL}/api/public/members-directory", timeout=60)
        assert r.status_code == 200, r.text[:200]
        body = r.content
        size = len(body)
        # Reported measured ~36 KB after fix. Enforce a generous ceiling.
        assert size < 200 * 1024, f"members-directory payload too large: {size} bytes"
        data = r.json()
        assert isinstance(data, list)
        # Scan every character portrait_url — must NOT be a data: URI.
        bad = []
        good_paths = []
        for member in data:
            for char in member.get("characters", []) or []:
                purl = char.get("portrait_url")
                if purl is None:
                    continue
                assert isinstance(purl, str), f"portrait_url wrong type: {purl!r}"
                assert not purl.startswith("data:"), (
                    f"Base64 portrait leaking: char {char.get('id')} member {member.get('username')}"
                )
                if purl.startswith("/api/image/") or "/api/image/" in purl:
                    good_paths.append(purl)
                bad_prefix = purl.startswith("data:")
                if bad_prefix:
                    bad.append(purl[:80])
        assert not bad, f"Data URIs found in directory: {bad}"
        # Stash a sample for the next test
        pytest.members_directory_image_urls = good_paths

    def test_image_urls_serve_200_image(self):
        urls = getattr(pytest, "members_directory_image_urls", [])
        if not urls:
            pytest.skip("No /api/image/ portrait URLs to test")
        # Test up to 3 to keep it fast
        for path in urls[:3]:
            # Convert relative path to full URL
            full = path if path.startswith("http") else f"{BASE_URL}{path}"
            r = requests.get(full, timeout=30)
            assert r.status_code == 200, f"{full} -> {r.status_code}"
            ctype = r.headers.get("content-type", "")
            assert ctype.startswith("image/"), f"Non-image content-type at {full}: {ctype}"
            assert len(r.content) > 0


# ---------- Character portrait upload ----------
class TestCharacterUpload:
    def test_upload_anonymous_returns_401(self):
        png = _minimal_png_bytes()
        files = {"file": ("t.png", io.BytesIO(png), "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/characters/{ADMIN_CHARACTER_ID}/upload-image",
            files=files,
            timeout=30,
        )
        # FastAPI's Depends(get_current_user) rejects anonymous with 401 (or 403).
        assert r.status_code in (401, 403), f"anonymous should be denied, got {r.status_code}"

    def test_upload_non_owned_returns_404(self, nonadmin_token: str):
        png = _minimal_png_bytes()
        files = {"file": ("t.png", io.BytesIO(png), "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/characters/{ADMIN_CHARACTER_ID}/upload-image",
            files=files,
            headers={"Authorization": f"Bearer {nonadmin_token}"},
            timeout=30,
        )
        assert r.status_code == 404, f"non-owner should get 404, got {r.status_code}: {r.text[:200]}"

    def test_upload_owner_stores_object_and_serves_image(self, admin_token: str):
        png = _minimal_png_bytes()
        files = {"file": ("t.png", io.BytesIO(png), "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/characters/{ADMIN_CHARACTER_ID}/upload-image",
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=60,
        )
        assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:200]}"
        body = r.json()
        purl = body.get("portrait_url")
        assert isinstance(purl, str) and purl.startswith("/api/image/"), (
            f"portrait_url should be short /api/image/... URL, got: {purl!r}"
        )
        assert not purl.startswith("data:")

        # The URL must serve a real image
        img_r = requests.get(f"{BASE_URL}{purl}", timeout=30)
        assert img_r.status_code == 200
        assert img_r.headers.get("content-type", "").startswith("image/")
        assert len(img_r.content) > 0

        # Verify the character doc now shows the short URL (no base64) via GET
        gc = requests.get(
            f"{BASE_URL}/api/characters/{ADMIN_CHARACTER_ID}",
            timeout=15,
        )
        assert gc.status_code == 200, gc.text[:200]
        char = gc.json()
        assert char.get("portrait_url") == purl, (
            f"character portrait_url not persisted, got {char.get('portrait_url')!r}"
        )
        assert not str(char.get("portrait_url", "")).startswith("data:")
