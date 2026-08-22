import os
import time

import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
API = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"

r = requests.post(f"{API}/auth/login",
                  json={"email": "craftnn1222@gmail.com", "password": "admin123"}, timeout=120)
tok = r.json().get("access_token") or r.json().get("token")
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {tok}"})

for label, path, method in [("pub_state", "/economy/producers/state", "GET"),
                            ("pub_seed", "/economy/producers/admin/seed", "POST"),
                            ("pub_tick", "/economy/producers/admin/tick", "POST")]:
    t0 = time.time()
    try:
        resp = s.get(f"{API}{path}", timeout=300) if method == "GET" else s.post(f"{API}{path}", timeout=300)
        print(f"{label}: {resp.status_code} in {time.time()-t0:.1f}s :: {resp.text[:300]}", flush=True)
    except Exception as e:
        print(f"{label}: EXC after {time.time()-t0:.1f}s {e}", flush=True)
