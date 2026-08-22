"""Music player routes — playlists per theme, multi upload, chunked upload,
delete/wipe, and guard rails.

Covers /api/music/list, /api/admin/music/upload, /upload-many,
/chunk/{init,append,finalize,abort}, DELETE /admin/music/{theme}/{filename},
DELETE /admin/music/theme/{theme}.
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
API = f"{BASE_URL}/api"

MP3_HEADER = b"ID3\x03\x00\x00\x00\x00\x00\x00"


def _mp3_bytes(size: int) -> bytes:
    body = MP3_HEADER + b"\x00" * max(0, size - len(MP3_HEADER))
    return body[:size]


def _creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    emails = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*[-*]?\s*(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    if len(emails) < 2 or len(passwords) < 2:
        pytest.skip("credentials file incomplete")
    return (
        {"email": emails[0], "password": passwords[0]},
        {"email": emails[1], "password": passwords[1]},
    )


def _login(session, creds):
    r = session.post(f"{API}/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        pytest.fail(f"no token in login response: {r.text[:300]}")
    return token


@pytest.fixture(scope="session")
def admin_token():
    s = requests.Session()
    return _login(s, _creds()[0])


@pytest.fixture(scope="session")
def member_token():
    s = requests.Session()
    return _login(s, _creds()[1])


@pytest.fixture(scope="session")
def admin(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}"})
    return s


@pytest.fixture(scope="session")
def anon():
    return requests.Session()


def _list(session):
    r = session.get(f"{API}/music/list", timeout=60)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _upload(session, theme, name, size=200_000):
    return session.post(
        f"{API}/admin/music/upload",
        files={"file": (name, _mp3_bytes(size), "audio/mpeg")},
        data={"theme": theme},
        timeout=180,
    )


# ── list endpoint shape / legacy preservation ─────────────────────────────
class TestListEndpoint:
    THEMES = ["global", "ammeonon", "selindori", "dhor-kuldor",
              "aigraels", "veiled-realms", "tavern"]

    def test_public_list_shape(self, anon):
        data = _list(anon)
        assert set(["themes", "all", "tracks"]).issubset(data.keys())
        for t in self.THEMES:
            assert t in data["themes"], f"missing theme {t}"
            assert isinstance(data["themes"][t], list)
        assert isinstance(data["all"], list)

    def test_legacy_global_mp3_preserved(self, anon):
        data = _list(anon)
        legacy = [t for t in data["themes"]["global"] if t.get("legacy")]
        assert legacy, "legacy global.mp3 not surfaced under themes.global"
        assert legacy[0]["filename"] == "global.mp3"
        assert legacy[0]["url"] == "/api/static/music/global.mp3"
        r = requests.get(f"{BASE_URL}{legacy[0]['url']}", timeout=120)
        assert r.status_code == 200, "legacy file not served statically"

    def test_tracks_sorted_alphabetically(self, admin):
        names = ["TEST_zz_sort.mp3", "TEST_aa_sort.mp3", "TEST_mm_sort.mp3"]
        for n in names:
            assert _upload(admin, "veiled-realms", n).status_code == 200
        rows = [t for t in _list(admin)["themes"]["veiled-realms"] if not t.get("legacy")]
        filenames = [t["filename"].lower() for t in rows]
        assert filenames == sorted(filenames), "tracks not in stable sorted order"
        admin.delete(f"{API}/admin/music/theme/veiled-realms", timeout=60)


# ── single direct upload ──────────────────────────────────────────────────
class TestSingleUpload:
    def test_upload_then_appears_in_list(self, admin):
        r = _upload(admin, "ammeonon", "TEST_single.mp3", 150_000)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["success"] is True
        assert body["theme"] == "ammeonon"
        assert isinstance(body["id"], str) and len(body["id"]) == 8
        assert body["size"] == 150_000
        assert body["url"].startswith("/api/static/music/ammeonon/")
        assert body["filename"].endswith("TEST_single.mp3")

        rows = _list(admin)["themes"]["ammeonon"]
        assert any(t["filename"] == body["filename"] for t in rows)

        got = requests.get(f"{BASE_URL}{body['url']}", timeout=120)
        assert got.status_code == 200
        assert len(got.content) == 150_000

        admin.delete(f"{API}/admin/music/{body['theme']}/{body['filename']}", timeout=60)

    def test_two_uploads_same_theme_no_overwrite(self, admin):
        a = _upload(admin, "tavern", "TEST_tav_one.mp3", 90_000)
        b = _upload(admin, "tavern", "TEST_tav_two.mp3", 91_000)
        assert a.status_code == 200 and b.status_code == 200
        ja, jb = a.json(), b.json()
        assert ja["id"] != jb["id"]
        assert ja["filename"] != jb["filename"]
        rows = {t["filename"] for t in _list(admin)["themes"]["tavern"]}
        assert ja["filename"] in rows and jb["filename"] in rows

    def test_same_filename_twice_both_kept(self, admin):
        a = _upload(admin, "tavern", "TEST_dupe.mp3", 50_000)
        b = _upload(admin, "tavern", "TEST_dupe.mp3", 51_000)
        assert a.status_code == 200 and b.status_code == 200
        assert a.json()["filename"] != b.json()["filename"]
        rows = {t["filename"] for t in _list(admin)["themes"]["tavern"]}
        assert a.json()["filename"] in rows and b.json()["filename"] in rows
        admin.delete(f"{API}/admin/music/theme/tavern", timeout=60)


# ── multi upload ──────────────────────────────────────────────────────────
class TestUploadMany:
    def test_upload_many_two_files(self, admin):
        files = [
            ("files", ("TEST_many_a.mp3", _mp3_bytes(40_000), "audio/mpeg")),
            ("files", ("TEST_many_b.ogg", _mp3_bytes(41_000), "audio/ogg")),
        ]
        r = admin.post(f"{API}/admin/music/upload-many", files=files,
                       data={"theme": "dhor-kuldor"}, timeout=180)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert len(body["added"]) == 2, body
        assert body["skipped"] == []
        rows = {t["filename"] for t in _list(admin)["themes"]["dhor-kuldor"]}
        for rec in body["added"]:
            assert rec["filename"] in rows

    def test_upload_many_mixed_valid_invalid(self, admin):
        files = [
            ("files", ("TEST_ok.mp3", _mp3_bytes(30_000), "audio/mpeg")),
            ("files", ("TEST_bad.txt", b"not audio", "text/plain")),
        ]
        r = admin.post(f"{API}/admin/music/upload-many", files=files,
                       data={"theme": "dhor-kuldor"}, timeout=180)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert len(body["added"]) == 1
        assert len(body["skipped"]) == 1
        assert "audio" in body["skipped"][0]["reason"].lower()
        admin.delete(f"{API}/admin/music/theme/dhor-kuldor", timeout=60)


# ── chunked upload ────────────────────────────────────────────────────────
class TestChunkedUpload:
    def test_full_chunk_cycle(self, admin):
        total = 6_000_000
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "selindori", "filename": "TEST_song1.mp3",
                             "size": total}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        init = r.json()
        upload_id = init["upload_id"]
        assert init["chunk_limit"] == 4 * 1024 * 1024

        blob = _mp3_bytes(total)
        first = 4 * 1024 * 1024
        for part in (blob[:first], blob[first:]):
            ar = admin.post(f"{API}/admin/music/chunk/append",
                            data={"upload_id": upload_id},
                            files={"chunk": ("blob", part, "application/octet-stream")},
                            timeout=300)
            assert ar.status_code == 200, ar.text[:400]
            assert ar.json()["received"] == len(part)
        assert ar.json()["total"] == total

        fr = admin.post(f"{API}/admin/music/chunk/finalize",
                        json={"upload_id": upload_id, "theme": "selindori",
                              "filename": "TEST_song1.mp3"}, timeout=180)
        assert fr.status_code == 200, fr.text[:400]
        fin = fr.json()
        assert fin["size"] == total, f"assembled size mismatch: {fin['size']}"
        rows = _list(admin)["themes"]["selindori"]
        match = [t for t in rows if t["filename"] == fin["filename"]]
        assert match, "chunked track missing from list"
        assert match[0]["size"] == total
        admin.delete(f"{API}/admin/music/theme/selindori", timeout=60)

    def test_abort_removes_session(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "tavern", "filename": "TEST_abort.mp3",
                             "size": 1000}, timeout=120)
        assert r.status_code == 200
        uid = r.json()["upload_id"]
        ab = admin.post(f"{API}/admin/music/chunk/abort", data={"upload_id": uid}, timeout=60)
        assert ab.status_code == 200 and ab.json()["aborted"] is True
        # appending after abort must 404
        ap = admin.post(f"{API}/admin/music/chunk/append", data={"upload_id": uid},
                        files={"chunk": ("blob", b"abc", "application/octet-stream")},
                        timeout=60)
        assert ap.status_code == 404

    def test_init_rejects_non_audio(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "tavern", "filename": "huge.txt", "size": 1000},
                       timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "audio" in r.json()["detail"].lower()

    def test_init_rejects_oversize(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "tavern", "filename": "big.mp3", "size": 999_999_999},
                       timeout=60)
        assert r.status_code == 413, r.text[:300]
        assert "too large" in r.json()["detail"].lower()

    def test_init_rejects_bad_theme(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "not-a-theme", "filename": "x.mp3", "size": 10},
                       timeout=60)
        assert r.status_code == 400
        assert "Invalid theme" in r.json()["detail"]

    def test_append_unknown_session_404(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/append",
                       data={"upload_id": "deadbeef" * 4},
                       files={"chunk": ("blob", b"x", "application/octet-stream")},
                       timeout=60)
        assert r.status_code == 404

    def test_finalize_zero_bytes_400(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "tavern", "filename": "TEST_empty.mp3", "size": 10},
                       timeout=60)
        uid = r.json()["upload_id"]
        fr = admin.post(f"{API}/admin/music/chunk/finalize",
                        json={"upload_id": uid, "theme": "tavern",
                              "filename": "TEST_empty.mp3"}, timeout=60)
        assert fr.status_code == 400, fr.text[:300]
        assert "no bytes" in fr.json()["detail"].lower()

    def test_finalize_unknown_session_404(self, admin):
        fr = admin.post(f"{API}/admin/music/chunk/finalize",
                        json={"upload_id": "0" * 32, "theme": "tavern",
                              "filename": "TEST_x.mp3"}, timeout=60)
        assert fr.status_code == 404

    def test_append_chunk_too_large(self, admin):
        r = admin.post(f"{API}/admin/music/chunk/init",
                       data={"theme": "tavern", "filename": "TEST_bigchunk.mp3",
                             "size": 10_000_000}, timeout=60)
        uid = r.json()["upload_id"]
        oversize = _mp3_bytes(4 * 1024 * 1024 + 5000)
        ap = admin.post(f"{API}/admin/music/chunk/append", data={"upload_id": uid},
                        files={"chunk": ("blob", oversize, "application/octet-stream")},
                        timeout=300)
        assert ap.status_code == 413, ap.text[:300]
        admin.post(f"{API}/admin/music/chunk/abort", data={"upload_id": uid}, timeout=60)


# ── delete / wipe ─────────────────────────────────────────────────────────
class TestDelete:
    def test_delete_single_track(self, admin):
        up = _upload(admin, "aigraels", "TEST_del_one.mp3", 20_000).json()
        r = admin.delete(f"{API}/admin/music/aigraels/{up['filename']}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["deleted"] is True
        rows = {t["filename"] for t in _list(admin)["themes"]["aigraels"]}
        assert up["filename"] not in rows
        got = requests.get(f"{BASE_URL}{up['url']}", timeout=60)
        assert got.status_code == 404, "file still served after delete"

    def test_delete_missing_track_404(self, admin):
        r = admin.delete(f"{API}/admin/music/aigraels/nope-nope.mp3", timeout=60)
        assert r.status_code == 404

    def test_delete_invalid_theme_400(self, admin):
        r = admin.delete(f"{API}/admin/music/not-a-theme/x.mp3", timeout=60)
        assert r.status_code == 400
        assert "Invalid theme" in r.json()["detail"]

    def test_wipe_theme(self, admin):
        for n in ("TEST_wipe_a.mp3", "TEST_wipe_b.mp3"):
            assert _upload(admin, "aigraels", n, 10_000).status_code == 200
        r = admin.delete(f"{API}/admin/music/theme/aigraels", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["deleted"] >= 2
        assert _list(admin)["themes"]["aigraels"] == []

    def test_wipe_invalid_theme_400(self, admin):
        r = admin.delete(f"{API}/admin/music/theme/bogus", timeout=60)
        assert r.status_code == 400

    def test_path_traversal_blocked(self, admin):
        r = admin.delete(f"{API}/admin/music/tavern/..%2F..%2Fglobal.mp3", timeout=60)
        assert r.status_code in (400, 404), r.text[:300]
        # legacy global.mp3 must survive
        legacy = [t for t in _list(admin)["themes"]["global"] if t.get("legacy")]
        assert legacy, "global.mp3 was destroyed by traversal attempt"


# ── guard rails ───────────────────────────────────────────────────────────
class TestGuards:
    def test_non_audio_rejected(self, admin):
        r = admin.post(f"{API}/admin/music/upload",
                       files={"file": ("TEST_bad.txt", b"hello", "text/plain")},
                       data={"theme": "tavern"}, timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "audio" in r.json()["detail"].lower()

    def test_invalid_theme_rejected(self, admin):
        r = _upload(admin, "not-a-theme", "TEST_bad_theme.mp3", 5_000)
        assert r.status_code == 400, r.text[:300]
        assert "Invalid theme" in r.json()["detail"]

    def test_non_admin_forbidden(self, member_token):
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {member_token}"})
        r = s.post(f"{API}/admin/music/upload",
                   files={"file": ("TEST_x.mp3", _mp3_bytes(1000), "audio/mpeg")},
                   data={"theme": "tavern"}, timeout=60)
        assert r.status_code == 403, r.text[:300]
        assert "Admin access required" in r.json()["detail"]

    def test_non_admin_forbidden_all_admin_endpoints(self, member_token):
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {member_token}"})
        checks = [
            ("post", f"{API}/admin/music/upload-many", {"files": [("files", ("a.mp3", b"x", "audio/mpeg"))]}),
            ("post", f"{API}/admin/music/chunk/init", {"data": {"theme": "tavern", "filename": "a.mp3", "size": 10}}),
            ("delete", f"{API}/admin/music/theme/tavern", {}),
            ("delete", f"{API}/admin/music/tavern/a.mp3", {}),
        ]
        for method, url, kw in checks:
            if "files" in kw:
                r = getattr(s, method)(url, files=kw["files"], data={"theme": "tavern"}, timeout=60)
            else:
                r = getattr(s, method)(url, timeout=60, **kw)
            assert r.status_code == 403, f"{method.upper()} {url} -> {r.status_code}"

    def test_unauthenticated_rejected(self, anon):
        r = anon.post(f"{API}/admin/music/upload",
                      files={"file": ("TEST_x.mp3", _mp3_bytes(1000), "audio/mpeg")},
                      data={"theme": "tavern"}, timeout=60)
        assert r.status_code in (401, 403), r.text[:300]

    def test_unauthenticated_delete_rejected(self, anon):
        r = anon.delete(f"{API}/admin/music/theme/global", timeout=60)
        assert r.status_code in (401, 403), r.text[:300]


# ── final cleanup ─────────────────────────────────────────────────────────
def test_zz_cleanup(admin):
    for theme in ("ammeonon", "selindori", "dhor-kuldor", "aigraels",
                  "veiled-realms", "tavern"):
        admin.delete(f"{API}/admin/music/theme/{theme}", timeout=60)
    data = _list(admin)
    legacy = [t for t in data["themes"]["global"] if t.get("legacy")]
    assert legacy, "legacy global.mp3 must remain after cleanup"
