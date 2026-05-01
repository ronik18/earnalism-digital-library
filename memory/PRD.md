# The Earnalism — PRD

## Problem Statement
Build a premium, fully responsive online bookstore and publishing brand website for "The Earnalism" at theearnalism.com. Luxury editorial tone, boutique bookstore + modern publishing house feel. 8 pages + admin dashboard. Deep burgundy, warm beige, ivory, champagne gold, soft charcoal palette. Elegant serif headings (Cormorant Garamond) + modern sans-serif body (Outfit). Editable Buy Now URLs (Razorpay/Amazon later), newsletter + contact + publishing submissions stored in DB only.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + PyJWT + bcrypt. Routes under `/api/*`.
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn/ui + sonner + lucide-react.
- **Auth**: JWT Bearer token (localStorage), single admin seeded from env.
- **DB collections**: `users`, `books`, `categories`, `blog_posts`, `newsletter`, `contacts`, `publishing_requests`, `settings` (featured_book).

## User Personas
1. **Premium reader** — discovers the bookstore, joins the Reading Circle, buys the featured book.
2. **Author/entrepreneur** — explores Publishing Services, submits a publishing-help request.
3. **Owner/Admin** — manages catalog (books, blog, categories), sets featured book, views subscribers + inquiries, changes own password.

## Core Requirements
- 8 public pages: Home, Shop, Product Detail, Journal (list + article), About, Publishing, Contact.
- Admin dashboard with JWT auth: CRUD for books/blog/categories, view newsletter + contact + publishing requests, set featured book, change own password.
- Buy Now URL per book is editable; empty → "Request Purchase Info" fallback.
- Mobile-first responsive (1440 / 1024 / 768 / 430 / 390).
- SEO title + meta + favicon.
- No email automation, no payment gateway integration in v1.

## What's Been Implemented (v1 — 2026-02-01)
- Backend: full API surface, JWT Bearer auth, bcrypt password hashing, idempotent admin seeding, password-change endpoint with validation.
- Seeded: 1 admin, 5 categories, 1 featured book (Brownies to Break-Even and Beyond), 3 journal posts.
- Frontend: 8 polished responsive pages + admin dashboard (7 tabs: books, blog, categories, newsletter, contacts, publishing, account/password).
- Premium aesthetic: Cormorant Garamond + Outfit, burgundy/beige/ivory/gold palette, paper grain overlay, glass header, pull quotes, drop caps, micro-interactions.
- SEO: browser title + meta description + SVG "E" monogram favicon.
- Tests: 18/18 backend pytest passing; all public flows + admin flows validated via testing_agent_v3; curl-verified password-change flow.
- Admin link removed from public footer; /admin/login accessible via direct URL only.

## Prioritized Backlog
### P1 — Near-term polish
- Password reset via email (requires SendGrid/Resend integration).
- Book image uploads via admin (object storage) — currently URL-only.
- OpenGraph + Twitter card meta tags for richer share previews.
- sitemap.xml + robots.txt for SEO.

### P2 — Growth
- Multiple authors / contributor profiles for journal posts.
- Tags + full-text search across books + journal.
- Razorpay Payment Link deep integration (one-click checkout without leaving the site).
- Reading Circle digest automation (weekly/monthly).

### P3 — Future
- Audiobook / excerpt preview player.
- Reader accounts + wishlist + reviews.
- Gifting flow.
- Multi-currency pricing.

## Admin Credentials
See `/app/memory/test_credentials.md` (admin can change password from the Account tab in /admin).
