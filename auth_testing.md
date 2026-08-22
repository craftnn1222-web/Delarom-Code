# Auth Testing Playbook — httpOnly Cookie Migration

This file documents the testing procedure for the JWT → httpOnly cookie migration
on the Continents of Delarom backend (`/app/backend`) and frontend (`/app/frontend`).

---

## Step 1: MongoDB Verification

```
mongosh
use <DB_NAME>  # from backend/.env
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```

Verify:
- bcrypt hash starts with `$2b$` (existing format — unchanged by this migration)
- index exists on `users.email` (unique) — pre-existing in this codebase

---

## Step 2: API Testing — Cookie Auth Round-Trip

Login should set `access_token` + `refresh_token` cookies on the response and the
`/api/auth/me` call should succeed using the cookie store.

```
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

# Clear any old cookie jar
rm -f /tmp/cookies.txt

# Login — verify cookies set
curl -c /tmp/cookies.txt -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"craftnn1222@gmail.com","password":"admin123"}' -v 2>&1 | grep -iE "(set-cookie|httponly|samesite|^< )"

# Show captured cookies
cat /tmp/cookies.txt

# Use cookie to fetch /me — should return the user
curl -b /tmp/cookies.txt "$API_URL/api/auth/me"

# Hit a protected endpoint (e.g., /api/characters/mine) with cookie
curl -b /tmp/cookies.txt "$API_URL/api/characters/mine"

# Logout — verify cookies cleared
curl -b /tmp/cookies.txt -c /tmp/cookies.txt -X POST "$API_URL/api/auth/logout"
cat /tmp/cookies.txt   # should show expired/empty cookies

# Verify /me now returns 401
curl -b /tmp/cookies.txt "$API_URL/api/auth/me"
```

---

## Step 3: Backward-Compat — Bearer Header Path

During transition the backend `get_current_user` dependency reads cookie first and
falls back to `Authorization: Bearer <token>`. Verify both paths still work so any
inflight Postman / cron / curl scripts keep functioning:

```
# Get a token via login (response body still contains it for now)
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"craftnn1222@gmail.com","password":"admin123"}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('token',''))")

curl "$API_URL/api/auth/me" -H "Authorization: Bearer $TOKEN"
```

---

## Step 4: Frontend Smoke Test

1. Login at `/login` — UI must navigate to `/dashboard` without error.
2. Open DevTools → Application → Cookies — `access_token` cookie should be present,
   marked HttpOnly + SameSite=Lax + Secure (in prod) + Path=/.
3. localStorage should **NOT** contain `token` after a fresh login.
4. Refresh the page — user stays logged in (cookie persisted).
5. Navigate to `/admin` — admin dashboard loads (cookie carries through protected routes).
6. Click "Logout" — cookie cleared, user lands on `/login`, refresh keeps them on `/login`.

---

## Step 5: CSRF Posture

Cookies are `SameSite=Lax`. Lax blocks cross-site POST/PUT/DELETE — the primary CSRF
vector for a SPA — so no explicit CSRF token is required. Cross-origin requests from
malicious sites cannot ride the cookie.

If a 3rd-party iframe scenario is added later, switch to `SameSite=Strict` or add a
double-submit-cookie CSRF token then.

---

## Step 6: Regression Coverage

After migration, all protected backend routes must still work for an authenticated
user. The testing agent should run a sample of:
- GET /api/characters/mine
- POST /api/quests/* (any create endpoint that uses the auth dep)
- GET /api/admin/* (admin-only — verify role check still functions)
- POST /api/auth/logout (verifies the cookie clear path)
