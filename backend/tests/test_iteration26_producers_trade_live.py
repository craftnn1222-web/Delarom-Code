"""Iteration 26 live API tests — Producers + Trade Companies.

Covers:
  • /api/economy/producers/*  (seed, tick, state, city read)
  • /api/trade-companies/*    (charter, routes, invest, dissolve, reads)

Run:
  pytest /app/backend/tests/test_iteration26_producers_trade_live.py -v
"""
import os
import re
import uuid
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
API = f"{BASE_URL}/api"
TIMEOUT = 180

backend_env = dotenv_values("/app/backend/.env")
_mongo = MongoClient(backend_env["MONGO_URL"])
DB = _mongo[backend_env["DB_NAME"]]

ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
USER2_EMAIL = "rep_tester_round2@delarom.com"
USER2_PASSWORD = "Testpass123!"

STATE = {}  # cross-test shared ids


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    body = r.json()
    token = body.get("access_token") or body.get("token")
    assert token, f"no token in login response: {body}"
    return token


def _set_gold(email, gold):
    DB.users.update_one({"email": email}, {"$set": {"currency": int(gold)}})


def _gold(email):
    u = DB.users.find_one({"email": email}, {"_id": 0, "currency": 1})
    return u.get("currency")


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(ADMIN_EMAIL, ADMIN_PASSWORD)}"})
    return s


@pytest.fixture(scope="module")
def user2():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(USER2_EMAIL, USER2_PASSWORD)}"})
    return s


@pytest.fixture(scope="module")
def admin_char():
    u = DB.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "id": 1})
    c = DB.characters.find_one({"user_id": u["id"]}, {"_id": 0, "id": 1, "name": 1})
    return c


@pytest.fixture(scope="module")
def user2_char():
    u = DB.users.find_one({"email": USER2_EMAIL}, {"_id": 0, "id": 1})
    c = DB.characters.find_one({"user_id": u["id"]}, {"_id": 0, "id": 1, "name": 1})
    assert c, "user2 has no character"
    return c


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    ids = STATE.get("company_ids", [])
    for cid in ids:
        DB.trade_companies.delete_many({"id": cid})
        DB.trade_company_routes.delete_many({"company_id": cid})
        DB.trade_company_shareholders.delete_many({"company_id": cid})
        DB.trade_company_activity.delete_many({"company_id": cid})
        DB.trade_company_ledger.delete_many({"company_id": cid})


def _track(cid):
    STATE.setdefault("company_ids", []).append(cid)


def _charter(session, char_id, name=None, nation="ammeonon"):
    payload = {
        "name": name or f"TEST_Co_{uuid.uuid4().hex[:6]}",
        "motto": "TEST motto",
        "home_nation": nation,
        "founder_character_id": char_id,
        "sigil": "coins",
        "color": "#f59e0b",
    }
    return session.post(f"{API}/trade-companies", json=payload, timeout=TIMEOUT)


# ── Producers: seed / tick / state ─────────────────────────────────


class TestProducers:
    def test_seed_idempotent(self, admin):
        r1 = admin.post(f"{API}/economy/producers/admin/seed", timeout=TIMEOUT)
        assert r1.status_code == 200, r1.text[:300]
        d1 = r1.json()
        assert d1["total"] >= 59
        r2 = admin.post(f"{API}/economy/producers/admin/seed", timeout=TIMEOUT)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["inserted"] == 0, f"second seed inserted {d2['inserted']} (not idempotent)"
        assert d2["updated"] == d2["total"]

    def test_seed_requires_admin(self, user2):
        r = user2.post(f"{API}/economy/producers/admin/seed", timeout=TIMEOUT)
        assert r.status_code in (401, 403), f"non-admin seed allowed: {r.status_code}"

    def test_tick(self, admin):
        r = admin.post(f"{API}/economy/producers/admin/tick", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["producers_run"] >= 59, d
        assert d["units_produced"] > 0, d
        assert "trade" in d, d
        for k in ("routes_attempted", "routes_completed", "routes_failed", "ledgers_closed"):
            assert k in d["trade"], d["trade"]

    def test_state(self, admin):
        r = requests.get(f"{API}/economy/producers/state", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["tick_hours"] == 6
        assert d["last_tick_at"]
        assert d["next_due_at"]

    def test_city_producers_read(self):
        r = requests.get(f"{API}/economy/producers/cities/ammeonon/wymroost", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        slugs = sorted(p["good_slug"] for p in d["producers"])
        assert slugs == ["silken-cloth", "spiced-wine", "tanned-leather"], slugs
        for p in d["producers"]:
            assert p["units_per_tick"] > 0
            assert p["warehouse_cap"] > 0
            assert p["description"]
        stock_slugs = sorted(s["good_slug"] for s in d["stock"])
        assert set(slugs).issubset(set(stock_slugs)), (slugs, stock_slugs)
        for s in d["stock"]:
            assert s["units"] >= 0

    def test_owner_inventory_endpoint(self):
        r = requests.get(f"{API}/economy/inventory/city/ammeonon:duncroft", timeout=TIMEOUT)
        assert r.status_code == 200
        rows = r.json()
        assert any(x["good_slug"] == "grain" for x in rows), rows
        r2 = requests.get(f"{API}/economy/inventory/bogus/x", timeout=TIMEOUT)
        assert r2.status_code == 400

    def test_tick_log(self):
        r = requests.get(f"{API}/economy/producers/ticks?limit=5", timeout=TIMEOUT)
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) >= 1


# ── Trade companies: charter ──────────────────────────────────────


class TestCharter:
    def test_charter_success(self, admin, admin_char):
        _set_gold(ADMIN_EMAIL, 20000)
        before = _gold(ADMIN_EMAIL)
        r = _charter(admin, admin_char["id"], name="TEST_Charter_One")
        assert r.status_code == 200, r.text[:400]
        c = r.json()
        _track(c["id"])
        STATE["company_a"] = c["id"]
        assert c["treasury"] == 2500, c
        assert c["status"] == "active"
        assert c["founder_character_id"] == admin_char["id"]
        assert _gold(ADMIN_EMAIL) == before - 2500
        # founder shares
        sh = admin.get(f"{API}/trade-companies/{c['id']}/shareholders", timeout=TIMEOUT).json()
        assert len(sh) == 1
        assert sh[0]["shares"] == 25, sh

    def test_charter_twice_unique_slug(self, admin, admin_char):
        r = _charter(admin, admin_char["id"], name="TEST_Charter_One")
        assert r.status_code == 200, r.text[:300]
        c = r.json()
        _track(c["id"])
        STATE["company_b"] = c["id"]
        assert c["id"] != STATE["company_a"]
        first = DB.trade_companies.find_one({"id": STATE["company_a"]}, {"_id": 0, "slug": 1})
        assert c["slug"] != first["slug"], (c["slug"], first["slug"])

    def test_charter_insufficient_gold(self, admin, admin_char):
        _set_gold(ADMIN_EMAIL, 100)
        r = _charter(admin, admin_char["id"])
        assert r.status_code == 409, f"{r.status_code} {r.text[:300]}"
        assert "2500g" in r.json()["detail"]
        _set_gold(ADMIN_EMAIL, 20000)

    def test_charter_null_currency_wallet(self, admin, admin_char):
        """Regression: users seeded without a `currency` field must not 500."""
        DB.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"currency": None}})
        try:
            r = _charter(admin, admin_char["id"])
            assert r.status_code != 500, f"500 on null currency: {r.text[:300]}"
            assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
        finally:
            _set_gold(ADMIN_EMAIL, 20000)

    def test_charter_foreign_character(self, admin, user2_char):
        r = _charter(admin, user2_char["id"])
        assert r.status_code == 404, f"{r.status_code} {r.text[:300]}"

    def test_charter_requires_auth(self, admin_char):
        r = requests.post(
            f"{API}/trade-companies",
            json={"name": "TEST_NoAuth", "motto": "", "home_nation": "ammeonon",
                  "founder_character_id": admin_char["id"], "sigil": "coins", "color": "#fff"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (401, 403), r.status_code


# ── Routes ────────────────────────────────────────────────────────


class TestRoutes:
    def test_add_route(self, admin):
        cid = STATE["company_a"]
        r = admin.post(
            f"{API}/trade-companies/{cid}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "duncroft",
                  "dest_nation": "ammeonon", "dest_city_slug": "wymroost",
                  "good_slug": "grain", "units_per_run": 20},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text[:300]
        route = r.json()
        assert route["is_active"] is True
        assert route["units_per_run"] == 20
        STATE["route_a"] = route["id"]
        listed = admin.get(f"{API}/trade-companies/{cid}/routes", timeout=TIMEOUT).json()
        assert any(x["id"] == route["id"] for x in listed)

    def test_add_route_non_founder(self, user2):
        r = user2.post(
            f"{API}/trade-companies/{STATE['company_a']}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "duncroft",
                  "dest_nation": "ammeonon", "dest_city_slug": "amberport",
                  "good_slug": "grain", "units_per_run": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
        assert "founder" in r.json()["detail"].lower()

    def test_add_route_same_city(self, admin):
        r = admin.post(
            f"{API}/trade-companies/{STATE['company_a']}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "duncroft",
                  "dest_nation": "ammeonon", "dest_city_slug": "duncroft",
                  "good_slug": "grain", "units_per_run": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.status_code
        assert "different" in r.json()["detail"].lower()

    def test_add_route_unknown_good(self, admin):
        r = admin.post(
            f"{API}/trade-companies/{STATE['company_a']}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "duncroft",
                  "dest_nation": "ammeonon", "dest_city_slug": "wymroost",
                  "good_slug": "unobtainium", "units_per_run": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.status_code
        assert "unknown good" in r.json()["detail"].lower()

    def test_toggle_and_delete_route(self, admin):
        cid = STATE["company_a"]
        # temp route to toggle/delete
        r = admin.post(
            f"{API}/trade-companies/{cid}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "amberport",
                  "dest_nation": "ammeonon", "dest_city_slug": "wymroost",
                  "good_slug": "salted-fish", "units_per_run": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text[:300]
        rid = r.json()["id"]
        t = admin.post(f"{API}/trade-companies/{cid}/routes/{rid}/toggle", timeout=TIMEOUT)
        assert t.status_code == 200 and t.json()["is_active"] is False, t.text[:200]
        t2 = admin.post(f"{API}/trade-companies/{cid}/routes/{rid}/toggle", timeout=TIMEOUT)
        assert t2.json()["is_active"] is True
        before = len(admin.get(f"{API}/trade-companies/{cid}/routes", timeout=TIMEOUT).json())
        d = admin.delete(f"{API}/trade-companies/{cid}/routes/{rid}", timeout=TIMEOUT)
        assert d.status_code == 200 and d.json().get("deleted") is True
        after = len(admin.get(f"{API}/trade-companies/{cid}/routes", timeout=TIMEOUT).json())
        assert after == before - 1
        # deleting again -> 404/409
        again = admin.delete(f"{API}/trade-companies/{cid}/routes/{rid}", timeout=TIMEOUT)
        assert again.status_code in (404, 409), again.status_code


# ── Route execution ───────────────────────────────────────────────


class TestRouteExecution:
    def test_route_runs_and_profits(self, admin):
        cid = STATE["company_a"]
        r = admin.post(f"{API}/economy/producers/admin/tick", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        trade = r.json()["trade"]
        assert trade["routes_completed"] >= 1, trade
        c = admin.get(f"{API}/trade-companies/{cid}", timeout=TIMEOUT).json()
        assert c["treasury"] > 2500, c
        assert c["period_revenue"] > 0, c
        assert c["lifetime_revenue"] > 0
        acts = admin.get(f"{API}/trade-companies/{cid}/activity", timeout=TIMEOUT).json()
        runs = [a for a in acts if a["kind"] == "route_run"]
        assert runs, acts[:3]
        assert runs[0]["meta"]["profit"] > 0, runs[0]
        assert acts[0]["at"] >= acts[-1]["at"], "activity not descending"
        assert any(a["kind"] == "charter" for a in acts)

    def test_route_skipped_when_no_stock(self, admin, admin_char):
        cid = STATE["company_b"]
        r = admin.post(
            f"{API}/trade-companies/{cid}/routes",
            json={"source_nation": "dhor-kuldor", "source_city_slug": "gloomstone",
                  "dest_nation": "ammeonon", "dest_city_slug": "wymroost",
                  "good_slug": "silken-cloth", "units_per_run": 20},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text[:300]
        before = admin.get(f"{API}/trade-companies/{cid}", timeout=TIMEOUT).json()
        tick = admin.post(f"{API}/economy/producers/admin/tick", timeout=TIMEOUT).json()
        assert tick["trade"]["routes_failed"] >= 1, tick["trade"]
        after = admin.get(f"{API}/trade-companies/{cid}", timeout=TIMEOUT).json()
        assert after["treasury"] == before["treasury"], (before["treasury"], after["treasury"])
        assert after["period_revenue"] == before["period_revenue"]

    def test_ledgers_empty(self, admin):
        r = admin.get(f"{API}/trade-companies/{STATE['company_a']}/ledgers", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json() == [], r.json()


# ── Shareholders ──────────────────────────────────────────────────


class TestShareholders:
    def test_invest(self, admin, user2, user2_char):
        _set_gold(USER2_EMAIL, 2000)
        cid = STATE["company_a"]
        before = admin.get(f"{API}/trade-companies/{cid}", timeout=TIMEOUT).json()["treasury"]
        r = user2.post(
            f"{API}/trade-companies/{cid}/invest",
            json={"character_id": user2_char["id"], "gold": 500},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["treasury"] == before + 500
        assert _gold(USER2_EMAIL) == 1500
        sh = admin.get(f"{API}/trade-companies/{cid}/shareholders", timeout=TIMEOUT).json()
        assert len(sh) == 2, sh
        me = [s for s in sh if s["character_id"] == user2_char["id"]]
        assert me and me[0]["shares"] == 5, sh

    def test_invest_below_minimum(self, user2, user2_char):
        r = user2.post(
            f"{API}/trade-companies/{STATE['company_a']}/invest",
            json={"character_id": user2_char["id"], "gold": 50},
            timeout=TIMEOUT,
        )
        assert r.status_code in (409, 422), f"{r.status_code} {r.text[:200]}"

    def test_invest_more_than_wallet(self, user2, user2_char):
        _set_gold(USER2_EMAIL, 300)
        r = user2.post(
            f"{API}/trade-companies/{STATE['company_a']}/invest",
            json={"character_id": user2_char["id"], "gold": 1000},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
        _set_gold(USER2_EMAIL, 2000)

    def test_invest_foreign_character(self, user2, admin_char):
        r = user2.post(
            f"{API}/trade-companies/{STATE['company_a']}/invest",
            json={"character_id": admin_char["id"], "gold": 100},
            timeout=TIMEOUT,
        )
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"


# ── Dissolve ──────────────────────────────────────────────────────


class TestDissolve:
    def test_dissolve_non_founder(self, user2):
        r = user2.post(f"{API}/trade-companies/{STATE['company_a']}/dissolve", timeout=TIMEOUT)
        assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
        assert "founder" in r.json()["detail"].lower()

    def test_dissolve_pays_out_proportionally(self, admin):
        cid = STATE["company_a"]
        c = admin.get(f"{API}/trade-companies/{cid}", timeout=TIMEOUT).json()
        treasury = c["treasury"]
        sh = admin.get(f"{API}/trade-companies/{cid}/shareholders", timeout=TIMEOUT).json()
        total = sum(s["shares"] for s in sh)
        admin_before, user2_before = _gold(ADMIN_EMAIL), _gold(USER2_EMAIL)
        expected = {}
        for s in sh:
            expected[s["user_id"]] = int(treasury * (s["shares"] / total))

        r = admin.post(f"{API}/trade-companies/{cid}/dissolve", timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["status"] == "dissolved"
        assert d["treasury"] == 0
        au = DB.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "id": 1})["id"]
        u2 = DB.users.find_one({"email": USER2_EMAIL}, {"_id": 0, "id": 1})["id"]
        assert _gold(ADMIN_EMAIL) == admin_before + expected.get(au, 0), (
            admin_before, _gold(ADMIN_EMAIL), expected)
        assert _gold(USER2_EMAIL) == user2_before + expected.get(u2, 0)
        # routes deactivated
        routes = admin.get(f"{API}/trade-companies/{cid}/routes", timeout=TIMEOUT).json()
        assert all(not x["is_active"] for x in routes), routes
        acts = admin.get(f"{API}/trade-companies/{cid}/activity", timeout=TIMEOUT).json()
        assert acts[0]["kind"] == "dissolve", acts[0]

    def test_dissolve_twice(self, admin):
        r = admin.post(f"{API}/trade-companies/{STATE['company_a']}/dissolve", timeout=TIMEOUT)
        assert r.status_code == 409, f"{r.status_code} {r.text[:200]}"
        assert "already dissolved" in r.json()["detail"].lower()

    def test_dissolved_company_not_in_active_list(self, admin):
        rows = admin.get(f"{API}/trade-companies", timeout=TIMEOUT).json()
        assert all(x["id"] != STATE["company_a"] for x in rows)
        rows2 = admin.get(f"{API}/trade-companies?status=dissolved", timeout=TIMEOUT).json()
        assert any(x["id"] == STATE["company_a"] for x in rows2)

    def test_route_add_on_dissolved(self, admin):
        r = admin.post(
            f"{API}/trade-companies/{STATE['company_a']}/routes",
            json={"source_nation": "ammeonon", "source_city_slug": "duncroft",
                  "dest_nation": "ammeonon", "dest_city_slug": "amberport",
                  "good_slug": "grain", "units_per_run": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.status_code

    def test_mine_endpoint(self, admin, user2):
        r = admin.get(f"{API}/trade-companies/mine", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert any(x["id"] == STATE["company_a"] for x in d["founded"]), d["founded"][:2]
        r2 = user2.get(f"{API}/trade-companies/mine", timeout=TIMEOUT)
        assert r2.status_code == 200
        assert any(x["id"] == STATE["company_a"] for x in r2.json()["shares_only"])

    def test_get_unknown_company_404(self, admin):
        r = admin.get(f"{API}/trade-companies/{uuid.uuid4()}", timeout=TIMEOUT)
        assert r.status_code == 404
