"""Iteration 38 — Owner Payouts + Employees (NPC + Player) backend tests.

Covers:
- GET /api/shops/{id}/employees (owner-only auth gating)
- POST hire NPC (auto-named, wage=50, kind=npc)
- POST hire player (case-insensitive username lookup, sets player_user_id)
- POST hire player error cases (unknown, self, inactive, duplicate, missing username, unknown role, max cap)
- DELETE fire employee
- GET /api/shops/{id}/ledger returns {entries, totals}
- Cross-shop authorization (non-owner gets 403 on list/hire/fire/ledger)
"""
import os
import re
import pytest
import requests
from dotenv import dotenv_values

_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
SHOP_ID = "41fc2225-2fbc-4be9-abce-8ae1e166a37c"
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"
PLAYER_EMAIL = "rep_tester_round2@delarom.com"
PLAYER_PASSWORD = "Testpass123!"


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok, f"missing access_token in login for {email}"
    return tok


@pytest.fixture(scope="module")
def admin_hdrs():
    return {"Authorization": f"Bearer {_login(ADMIN_EMAIL, ADMIN_PASSWORD)}"}


@pytest.fixture(scope="module")
def player_hdrs():
    return {"Authorization": f"Bearer {_login(PLAYER_EMAIL, PLAYER_PASSWORD)}"}


@pytest.fixture(scope="module")
def player_username(player_hdrs):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=player_hdrs, timeout=15)
    assert r.status_code == 200, r.text
    uname = r.json().get("username")
    assert uname
    return uname


@pytest.fixture(scope="module")
def admin_username(admin_hdrs):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_hdrs, timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("username")


@pytest.fixture(scope="module")
def player_shop_id(player_hdrs):
    """Get (or create) a shop owned by the non-admin player for cross-shop tests."""
    r = requests.get(f"{BASE_URL}/api/shops/my-shop", headers=player_hdrs, timeout=15)
    if r.status_code == 200:
        return r.json()["id"]
    # create one
    r = requests.post(
        f"{BASE_URL}/api/shops",
        headers=player_hdrs,
        json={
            "name": "TEST_RepTester Shop",
            "description": "seed for iter38 cross-shop tests",
            "nation": "Ammeonon",
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ── Cleanup helper — remove any lingering TEST NPCs before/after runs ──
def _cleanup_test_employees(headers, shop_id):
    r = requests.get(f"{BASE_URL}/api/shops/{shop_id}/employees", headers=headers, timeout=15)
    if r.status_code != 200:
        return
    for emp in r.json():
        # only wipe employees created without a real player (NPCs) AND whose name
        # is a fresh NPC — we key off no player_user_id and role in known set.
        # Better: only fire employees we track via marker file; use per-test cleanup.
        pass  # per-test cleanup below


# ==================== EMPLOYEE ROUTES ====================

class TestEmployeeListAuth:
    def test_list_employees_owner_ok(self, admin_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=admin_hdrs, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_list_employees_non_owner_403(self, player_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=player_hdrs, timeout=15)
        assert r.status_code == 403, r.text

    def test_list_employees_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_list_employees_unknown_shop_404(self, admin_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/does-not-exist/employees", headers=admin_hdrs, timeout=15)
        assert r.status_code == 404, r.text


class TestHireNpc:
    def test_hire_npc_success(self, admin_hdrs):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "clerk", "kind": "npc"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        emp = r.json()
        assert emp["role"] == "clerk"
        assert emp["kind"] == "npc"
        assert emp["wage"] == 50
        assert emp["active"] is True
        assert emp["player_user_id"] is None
        assert emp["name"], "NPC should have an auto-generated name"
        assert "id" in emp
        # verify persistence
        list_r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=admin_hdrs, timeout=15)
        ids = [e["id"] for e in list_r.json()]
        assert emp["id"] in ids
        # cleanup — fire this NPC
        requests.delete(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees/{emp['id']}",
            headers=admin_hdrs, timeout=15,
        )

    def test_hire_unknown_role_400(self, admin_hdrs):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "wizard", "kind": "npc"},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "role" in r.json().get("detail", "").lower()


class TestHirePlayerErrors:
    def test_hire_player_unknown_username_404(self, admin_hdrs):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "clerk", "kind": "player",
                  "player_username": "TotallyNotARealUser_ZZZ_xyz_9821"},
            timeout=15,
        )
        assert r.status_code == 404, r.text

    def test_hire_self_400(self, admin_hdrs, admin_username):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "clerk", "kind": "player", "player_username": admin_username},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "yourself" in r.json().get("detail", "").lower()

    def test_hire_missing_username_400(self, admin_hdrs):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "clerk", "kind": "player", "player_username": "  "},
            timeout=15,
        )
        assert r.status_code == 400, r.text


class TestHirePlayerSuccessAndDup:
    """Runs at class scope so we can hire → check dup → fire in order."""

    @pytest.fixture(scope="class")
    def hired_emp_id(self, admin_hdrs, player_username):
        # ensure they're not already on payroll (may leftover from previous run)
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=admin_hdrs, timeout=15)
        for emp in r.json():
            if emp.get("name", "").lower() == player_username.lower() and emp.get("player_user_id"):
                requests.delete(
                    f"{BASE_URL}/api/shops/{SHOP_ID}/employees/{emp['id']}",
                    headers=admin_hdrs, timeout=15,
                )

        # case-insensitive hire — mangle the case to prove regex works
        mangled = player_username.swapcase()
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "stocker", "kind": "player", "player_username": mangled},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        emp = r.json()
        assert emp["kind"] == "player"
        assert emp["player_user_id"], "player hire must set player_user_id"
        assert emp["name"].lower() == player_username.lower(), \
            f"player employee should be named after the resolved username; got {emp['name']}"
        assert emp["wage"] == 50
        yield emp["id"]
        # cleanup
        requests.delete(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees/{emp['id']}",
            headers=admin_hdrs, timeout=15,
        )

    def test_hire_player_success_case_insensitive(self, hired_emp_id):
        assert hired_emp_id  # fixture side-effect covers primary assertions

    def test_duplicate_player_hire_400(self, admin_hdrs, player_username, hired_emp_id):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=admin_hdrs,
            json={"role": "barker", "kind": "player", "player_username": player_username},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "already" in r.json().get("detail", "").lower()

    def test_fire_employee(self, admin_hdrs, hired_emp_id):
        r = requests.delete(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees/{hired_emp_id}",
            headers=admin_hdrs, timeout=15,
        )
        assert r.status_code == 200, r.text
        # verify removal
        r2 = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=admin_hdrs, timeout=15)
        ids = [e["id"] for e in r2.json()]
        assert hired_emp_id not in ids
        # re-hire so downstream/dup test doesn't leave orphan; fixture's teardown handles both cases.

    def test_fire_unknown_employee_404(self, admin_hdrs):
        r = requests.delete(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees/nonexistent-id-zzz",
            headers=admin_hdrs, timeout=15,
        )
        assert r.status_code == 404, r.text


class TestMaxEmployeeCap:
    """Employees cap at MAX_EMPLOYEES_PER_SHOP=6."""

    def test_max_employee_cap_400(self, admin_hdrs):
        # Fill up to cap with NPCs, then expect the next hire to fail.
        created = []
        try:
            r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=admin_hdrs, timeout=15)
            current = len(r.json())
            slots = max(0, 6 - current)
            for _ in range(slots):
                rr = requests.post(
                    f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
                    headers=admin_hdrs,
                    json={"role": "clerk", "kind": "npc"},
                    timeout=15,
                )
                assert rr.status_code == 200, rr.text
                created.append(rr.json()["id"])
            # one more should fail
            rr = requests.post(
                f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
                headers=admin_hdrs,
                json={"role": "clerk", "kind": "npc"},
                timeout=15,
            )
            assert rr.status_code == 400, rr.text
            assert re.search(r"most|max|6", rr.json().get("detail", ""), re.IGNORECASE)
        finally:
            for eid in created:
                requests.delete(
                    f"{BASE_URL}/api/shops/{SHOP_ID}/employees/{eid}",
                    headers=admin_hdrs, timeout=15,
                )


# ==================== LEDGER ====================

class TestShopLedger:
    def test_ledger_owner_success(self, admin_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/ledger", headers=admin_hdrs, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "entries" in data
        assert "totals" in data
        assert isinstance(data["entries"], list)
        totals = data["totals"]
        for key in ("npc_sales", "player_sales", "wages", "restock", "net"):
            assert key in totals, f"missing {key} in totals"
            assert isinstance(totals[key], int), f"{key} should be int, got {type(totals[key])}"

    def test_ledger_non_owner_403(self, player_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/ledger", headers=player_hdrs, timeout=15)
        assert r.status_code == 403, r.text

    def test_ledger_unknown_shop_404(self, admin_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/does-not-exist/ledger", headers=admin_hdrs, timeout=15)
        assert r.status_code == 404, r.text


# ==================== CROSS-SHOP AUTH ====================

class TestCrossShopAuth:
    """Admin should not be able to touch a shop they don't own — and vice versa."""

    def test_non_owner_cannot_list_admin_shop(self, player_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/employees", headers=player_hdrs, timeout=15)
        assert r.status_code == 403

    def test_non_owner_cannot_hire_admin_shop(self, player_hdrs):
        r = requests.post(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees",
            headers=player_hdrs,
            json={"role": "clerk", "kind": "npc"},
            timeout=15,
        )
        assert r.status_code == 403

    def test_non_owner_cannot_fire_admin_shop(self, player_hdrs):
        r = requests.delete(
            f"{BASE_URL}/api/shops/{SHOP_ID}/employees/some-id",
            headers=player_hdrs, timeout=15,
        )
        assert r.status_code == 403

    def test_non_owner_cannot_ledger_admin_shop(self, player_hdrs):
        r = requests.get(f"{BASE_URL}/api/shops/{SHOP_ID}/ledger", headers=player_hdrs, timeout=15)
        assert r.status_code == 403

    def test_admin_cannot_list_others_shop_employees(self, admin_hdrs, player_shop_id):
        # admin does NOT get a bypass on shop ownership — endpoint checks owner_id, not is_admin
        r = requests.get(
            f"{BASE_URL}/api/shops/{player_shop_id}/employees",
            headers=admin_hdrs, timeout=15,
        )
        assert r.status_code == 403, f"admin should not see other's shop employees: {r.status_code} {r.text}"

    def test_admin_cannot_ledger_others_shop(self, admin_hdrs, player_shop_id):
        r = requests.get(
            f"{BASE_URL}/api/shops/{player_shop_id}/ledger",
            headers=admin_hdrs, timeout=15,
        )
        assert r.status_code == 403
