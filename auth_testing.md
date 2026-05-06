# Auth Testing Playbook (User auth — Phase 2)

## Endpoints
- `POST /api/users/signup` — body: `{name, email, password}`; min password 8 chars
- `POST /api/users/login` — body: `{email, password}` → `{token, email, name, role:"user", reading_seconds_balance}`
- `GET  /api/users/me` — Bearer auth → user object
- `POST /api/users/logout` — frontend clears token
- `POST /api/reader/session/start` — body: `{book_slug, chapter_id}` (auth) → `{session_id}`
- `POST /api/reader/heartbeat` — body: `{session_id, visible, idle}` (auth) → `{deducted_seconds, remaining_seconds, status}`
- `POST /api/reader/session/end` — body: `{session_id}` (auth)
- Admin: `GET /api/admin/users`, `POST /api/admin/users/{id}/wallet/adjust`, `GET /api/admin/users/{id}/transactions`

## MongoDB Verification
```
db.users.findOne({role:"user"})
db.wallet_transactions.find({user_id:"<uid>"}).sort({created_at:-1})
db.reading_sessions.find({user_id:"<uid>"}).sort({started_at:-1})
```
- bcrypt hash starts with `$2b$`
- email index unique on users
- wallet_transactions has user_id index
- reading_sessions has user_id + status index

## Flow Test
1. Signup → expect `200 { token, ... }` + user inserted with `reading_seconds_balance:0`
2. Login wrong password → `401 Invalid email or password`
3. GET /me with token → user object (no password_hash)
4. Admin adjust +60 minutes → wallet_transaction `{type:"credit", seconds:3600}`, user balance updated
5. Reader session start (chapter not preview) → session_id, server returns `balance_seconds`
6. Heartbeat with `visible:true, idle:false` → deduct 30s, return remaining
7. Heartbeat with `visible:false` → deduct 0
8. Heartbeat when balance reaches 0 → status:"depleted", do not deduct below 0
9. Free preview chapter (order=0) — no auth required, no deduction

## Credentials (current)
- Test user: `reader@earnalism.com` / `Reader@2026` (seeded only if absent)
- Admin: see `/app/memory/test_credentials.md`
