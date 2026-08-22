import os
import time

import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"
LOCAL = "http://localhost:8001/api"

r = requests.post(f"{API}/auth/login",
                  json={"email": "craftnn1222@gmail.com", "password": "admin123"}, timeout=120)
tok = r.json().get("access_token") or r.json().get("token")
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {tok}"})

for label, path in [("local_seed", "/economy/producers/admin/seed"),
                    ("local_tick", "/economy/producers/admin/tick"),
                    ("local_state", "/economy/producers/state")]:
    t0 = time.time()
    try:
        if "state" in path:
            resp = s.get(f"{LOCAL}{path}", timeout=600)
        else:
            resp = s.post(f"{LOCAL}{path}", timeout=600)
        print(f"{label}: {resp.status_code} in {time.time()-t0:.1f}s :: {resp.text[:400]}", flush=True)
    except Exception as e:
        print(f"{label}: EXC after {time.time()-t0:.1f}s {e}", flush=True)
