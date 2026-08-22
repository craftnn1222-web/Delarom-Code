"""Probe: timing of admin seed/tick endpoints (502 investigation) + null-currency 500 repro."""
import os
import time

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
DB = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]

ADMIN = ("craftnn1222@gmail.com", "admin123")
USER2 = ("rep_tester_round2@delarom.com", "Testpass123!")


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=120)
    r.raise_for_status()
    return r.json().get("access_token") or r.json().get("token")


def main():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login(*ADMIN)}"})

    for label, path in [("seed", "/economy/producers/admin/seed"),
                        ("tick", "/economy/producers/admin/tick"),
                        ("seed2", "/economy/producers/admin/seed"),
                        ("tick2", "/economy/producers/admin/tick")]:
        t0 = time.time()
        try:
            r = s.post(f"{API}{path}", timeout=240)
            print(f"{label}: {r.status_code} in {time.time()-t0:.1f}s :: {r.text[:200]}")
        except Exception as e:
            print(f"{label}: EXC after {time.time()-t0:.1f}s {e}")

    # localhost comparison (bypass ingress)
    for label, path in [("local_seed", "/economy/producers/admin/seed"),
                        ("local_tick", "/economy/producers/admin/tick")]:
        t0 = time.time()
        r = s.post(f"http://localhost:8001/api{path}", timeout=240)
        print(f"{label}: {r.status_code} in {time.time()-t0:.1f}s :: {r.text[:160]}")

    # null-currency invest repro
    u2 = DB.users.find_one({"email": USER2[0]}, {"_id": 0, "id": 1})
    ch = DB.characters.find_one({"user_id": u2["id"]}, {"_id": 0, "id": 1})
    s2 = requests.Session()
    s2.headers.update({"Authorization": f"Bearer {login(*USER2)}"})
    co = s.post(f"{API}/trade-companies", json={
        "name": "TEST_NullWallet_Probe", "motto": "", "home_nation": "ammeonon",
        "founder_character_id": DB.characters.find_one(
            {"user_id": DB.users.find_one({"email": ADMIN[0]})["id"]}, {"_id": 0, "id": 1})["id"],
        "sigil": "coins", "color": "#f59e0b"}, timeout=180)
    print("probe charter:", co.status_code, co.text[:200])
    if co.status_code == 200:
        cid = co.json()["id"]
        DB.users.update_one({"email": USER2[0]}, {"$set": {"currency": None}})
        r = s2.post(f"{API}/trade-companies/{cid}/invest",
                    json={"character_id": ch["id"], "gold": 500}, timeout=180)
        print("invest with null currency:", r.status_code, r.text[:200])
        DB.users.update_one({"email": USER2[0]}, {"$set": {"currency": 2000}})
        # cleanup
        for coll in ("trade_companies", "trade_company_routes", "trade_company_shareholders",
                     "trade_company_activity", "trade_company_ledger"):
            DB[coll].delete_many({"company_id": cid})
        DB.trade_companies.delete_many({"id": cid})
    DB.users.update_one({"email": ADMIN[0]}, {"$set": {"currency": 20000}})


main()
