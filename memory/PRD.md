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

## Prioritized Backlog

### P1 — Phase 3 Monetization
- **Razorpay** payment links / orders + webhook → credit wallet on success (4 packs).
- **Cookie-based session migration** for both admin and user (currently Bearer + localStorage).

### P2 — Growth
- Google OAuth (real, replacing the disabled placeholder button).
- Mobile OTP (real provider integration).
- Password reset via email (Resend / SendGrid).
- Reading streaks, "continue reading" shelf, bookmarks.

### P3 — Future
- DOCX / Google Doc imports for chapters.
- Multi-currency, gifting reading time, referral credits.
- Audio chapter playback.

## Test Credentials
See `/app/memory/test_credentials.md`. Admin can change password via Account tab in `/admin`.

## Refactoring Note
`server.py` is ~1170 lines. Splitting into `/app/backend/routes/{auth,books,admin,reader}.py` is a recommended next refactor but **not** a blocker. User has explicitly asked to avoid refactors that don't ship value.
