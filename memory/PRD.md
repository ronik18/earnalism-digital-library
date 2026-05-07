# The Earnalism — PRD

## Problem Statement
Premium, fully responsive online bookstore + publishing brand pivoted to a **Digital Library MVP** ("Buy reading time. Read beautifully. Return whenever you wish."). Quiet digital reading room where users purchase wallet minutes to access books in the in-app reader. Luxury aesthetic: burgundy, ivory, champagne-gold, editorial serif typography (Cormorant Garamond + Outfit).

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + PyJWT + bcrypt. Routes under `/api/*`.
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn/ui + sonner + lucide-react.
- **Auth**: Two isolated JWT Bearer flows — admin (`earnalism_admin_token`) and reader user (`earnalism_user_token`). Cross-role tokens are rejected (403).
- **Wallet model**: `reading_seconds_balance` stored as INTEGER SECONDS, displayed in UI as `Xh YYm` / `Mm SSs` / `Ss`.
- **DB collections**: `users`, `books`, `categories`, `blog_posts`, `newsletter`, `contacts`, `settings`, `wallet_transactions`, `reading_sessions`.

## User Personas
1. **Premium reader** — signs up, gets a wallet, reads chapter 0 for free, buys reading time for the rest.
2. **Owner/Admin** — manages catalog (books, blog, categories), reader accounts, top-ups/deductions, and site settings.

## What's Been Implemented

### v1 (2026-02-01) — Bookstore MVP
- 8 public pages, admin dashboard with JWT, premium luxury design, SEO, 18/18 pytest passing.
- See archive: featured book, journal, catalog, contacts, social settings.

### Pivot (2026-02-15) — Digital Library
- Replaced Shop with Library; added manual chapter management; built `/reader/:slug` with themes, font sizing, ToC drawer, mobile swipe, watermarks.
- `/admin/login` cookie helper code present (Bearer remains primary mechanism).
- Removed Publishing module entirely; added Settings → Social, Share buttons, JSON-LD, OG tags.
- 23/23 backend tests pass (iteration_2.json).

### Phase 2 (2026-05-06) — Auth + Reading-Time Wallet ✅
- **User auth**: signup, login, logout, /me, /me/transactions. Bcrypt + 7-day JWT in `earnalism_user_token`. Cross-role isolation enforced.
- **Reading-time wallet**: integer-seconds balance, admin top-up/deduct, full transaction history with reasons + actor.
- **Reader heartbeat**: 30-second tick. Server deducts exactly 30s only when `visible && !idle && balance > 0 && chapter is not the free preview`. Idle = no input for 60s.
- **Free preview**: chapter with `order == 0` is open to everyone (even unauthenticated), never deducts time, watermarked.
- **Locked overlay**: when balance reaches 0 mid-session OR an unauthenticated user opens a chargeable chapter, a hard-stop overlay appears: "Top up to continue" / "Sign in to read on" with CTAs to /pricing or /login + "Return to Library".
- **Pricing placeholder**: `/pricing` shows 4 packs (30m, 1h, 3h, 10h) with disabled "Payments coming soon" buttons. Admin manual top-up is the current funding method.
- **Admin Users tab**: list reader accounts with balance + status, manage/top-up/deduct (with reason + audit), block/unblock, transaction history.
- **Routing**: new `/login`, `/signup`, `/account`, `/pricing`; `/signin` → `/login` redirect.
- **Header**: dynamically shows "Sign In" or "Account" based on user state.
- **Tests**: 43/43 backend pass (`/app/backend/tests/test_phase2_user_reader.py` + `backend_test.py`); all Phase 2 frontend flows green (iteration_3.json).

### Phase 2.1 (2026-05-06) — Server-side chapter content gating 🔒
- **`_strip_paid_chapter_content()`** scrubs chapter `content` from every PUBLIC `/api/books` and `/api/books/{slug}` response. Only chapter with `order==0` retains its body; the rest are metadata-only.
- **New `GET /api/reader/chapter/{slug}/{chapter_id}`** — sole source of chapter content for the public reader. Returns:
  - `{locked:false, is_preview:true, chapter:{...content...}}` — preview chapter for everyone (no auth).
  - `{locked:false, chapter:{...content...}}` — admin token (admin preview) OR reader user with `balance>0` and `status=="active"`.
  - `{locked:true, reason:"AUTH_REQUIRED" | "INSUFFICIENT_READING_TIME" | "BLOCKED", message, chapter:{id,title,order}}` — content key entirely absent in locked responses.
- **`optional_principal`** dependency — never raises, returns admin/user/None. Used by the gated chapter endpoint.
- **Reader.jsx** renders chapter body ONLY from the gated endpoint's response. Sends admin token first if present (so admin can preview from `/reader/{slug}`), else user token, else no auth. Locked overlay reads server `reason`+`message`.
- **Tests**: 14 new security tests in `/app/backend/tests/test_chapter_gating_security.py` — incl. a raw-text guard that greps `response.text` for paid snippets. **57/57 backend pass; all 8 frontend scenarios green** (iteration_4.json).
- Admin route `/api/admin/books` deliberately retains full content (admin preview) and is unchanged.

### Phase 3 (2026-05-06) — Razorpay TEST MODE wallet top-up 💳
- Backend pack catalogue (PACKS_BY_ID) is the authoritative source for minutes & paise. Frontend cannot influence amount.
- **POST /api/payments/topup** (auth) → creates a `topup_intents` row + Razorpay Order in test mode → returns `{intent_id, razorpay_order_id, key_id, amount, currency, name, prefill, pack}` for Checkout.js.
- **POST /api/payments/verify** (auth) — HMAC-SHA256 signature check on `order_id|payment_id` with `RAZORPAY_KEY_SECRET`. Idempotently credits.
- **POST /api/payments/webhook** — verifies `X-Razorpay-Signature` against raw body using `RAZORPAY_WEBHOOK_SECRET`. Stores every event in `payment_webhook_events` (incl. rejected). Idempotent on `event_id`.
- **Atomic credit guard** `_credit_wallet_for_intent()`: `update_one({id, status:{$ne:"credited"}}, {$set:{status:"credited",...}})` then `$inc` on user balance, then insert a `wallet_transactions` row. Only the first caller wins — verify and webhook can both fire safely.
- Dev-only **/api/payments/_simulate_topup + /_simulate_webhook** (gated by `RAZORPAY_MODE=="test"`) so the credit path can be exercised without real Razorpay keys.
- **Admin Payments tab** — config status, top-up intents table with manual reconcile button, webhook event log.
- **Pricing.jsx** — loads packs from API, dynamically loads Razorpay Checkout.js when keys are configured, otherwise runs the simulator path. After success, refreshes wallet and navigates to /account.
- **Index fix during testing**: `topup_intents.razorpay_order_id` / `razorpay_payment_id` use `partialFilterExpression={"$type":"string"}` so null pre-payment values don't collide on the unique index.
- **Tests**: 19 new payments tests in `/app/backend/tests/test_payments_razorpay.py`. **76/76 backend + all 12 frontend scenarios green** (iteration_5.json).
- Razorpay env vars added (currently empty placeholders): `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_MODE=test`.

### Deployment readiness (2026-05-07) 🚀
- New endpoint `GET /api/health` returns `{ok, service, mode, razorpay_configured, time}` for load-balancer healthchecks.
- `backend/.env.example` and `frontend/.env.example` document every required env var for any deployment target.
- Re-verified end-to-end: 76/76 backend tests, frontend `yarn build` clean (132.78 kB gz), all 12 SPA routes + 7 API routes return 200, chapter gating + Razorpay simulator + idempotency holds.
- Target deployment platform: **Emergent native deploy**, with Hostinger managing DNS only.

## Prioritized Backlog

### P1 — Phase 4 (next)
- Email-based password reset for readers (Resend / SendGrid).
- Cookie-based session migration (currently Bearer + localStorage for both admin & user).
- Wire real Razorpay keys + dashboard webhook (today everything is structurally ready in test simulator mode).

### P2 — Growth
- Google OAuth (real, replacing the disabled placeholder button).
- Mobile OTP (real provider integration).
- Reading streaks, "continue reading" shelf, bookmarks.

### P3 — Future
- DOCX / Google Doc imports for chapters.
- Multi-currency, gifting reading time, referral credits.
- Audio chapter playback.

## Test Credentials
See `/app/memory/test_credentials.md`. Admin can change password via Account tab in `/admin`.

## Refactoring Note
`server.py` is ~1170 lines. Splitting into `/app/backend/routes/{auth,books,admin,reader}.py` is a recommended next refactor but **not** a blocker. User has explicitly asked to avoid refactors that don't ship value.
