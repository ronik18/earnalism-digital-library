"""Security hardening tests — paid chapter content gating.

Verifies:
  1. GET /api/books strips non-preview chapter content across ALL books.
  2. GET /api/books/{slug} strips non-preview chapter content.
  3. GET /api/reader/chapter/{slug}/{chapter_id} enforces auth + balance.
  4. Admin token always unlocks.
  5. GET /api/admin/books returns FULL content (admin preview untouched).
  6. Blocked user -> reason=BLOCKED, no content.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@theearnalism.com")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "Earnalism@2026")

BOOK_SLUGS = [
    "brownies-to-break-even-and-beyond",
    "the-architecture-of-intelligent-systems",
]
PRIMARY_SLUG = BOOK_SLUGS[0]


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin_headers(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def fresh_user(s):
    email = f"gate-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    password = "TestPass123"
    r = s.post(f"{API}/users/signup",
               json={"name": "Gate Tester", "email": email, "password": password})
    assert r.status_code == 200, r.text
    j = r.json()
    return {
        "email": email,
        "password": password,
        "token": j["token"],
        "user": j["user"],
        "headers": {"Authorization": f"Bearer {j['token']}"},
    }


@pytest.fixture(scope="module")
def primary_chapters(s):
    """Return sorted chapters for PRIMARY_SLUG via admin API (full content)."""
    # Use admin books so we have the real full-content list to compare against.
    pass  # filled via admin_chapters fixture below


@pytest.fixture(scope="module")
def admin_chapters(s, admin_headers):
    r = s.get(f"{API}/admin/books", headers=admin_headers)
    assert r.status_code == 200, r.text
    by_slug = {b["slug"]: sorted(b.get("chapters") or [], key=lambda c: c.get("order", 0))
               for b in r.json()}
    for slug in BOOK_SLUGS:
        assert slug in by_slug, f"seeded book missing: {slug}"
        assert len(by_slug[slug]) >= 2, f"{slug}: need at least 2 chapters"
    return by_slug


# ---------------- 1. Public list/detail strips paid content ----------------
class TestPublicBookStripping:
    def test_public_books_list_strips_paid_content(self, s, admin_chapters):
        r = s.get(f"{API}/books")
        assert r.status_code == 200
        by_slug = {b["slug"]: b for b in r.json()}
        for slug in BOOK_SLUGS:
            assert slug in by_slug, f"{slug} missing from public /books"
            chapters = sorted(by_slug[slug].get("chapters") or [],
                              key=lambda c: c.get("order", 0))
            assert len(chapters) >= 2
            # Preview (index 0) MUST keep non-empty content
            admin_preview_content = admin_chapters[slug][0].get("content", "")
            assert chapters[0].get("content") == admin_preview_content
            assert len(chapters[0].get("content") or "") > 0, \
                f"{slug}: preview chapter content is empty"
            # All paid chapters must be blanked to ""
            for c in chapters[1:]:
                assert c.get("content") == "", \
                    f"{slug}: paid chapter '{c.get('title')}' leaked content"

    def test_public_book_detail_strips_paid_content(self, s, admin_chapters):
        for slug in BOOK_SLUGS:
            r = s.get(f"{API}/books/{slug}")
            assert r.status_code == 200
            chapters = sorted(r.json().get("chapters") or [],
                              key=lambda c: c.get("order", 0))
            assert chapters[0].get("content") == admin_chapters[slug][0].get("content")
            assert len(chapters[0].get("content") or "") > 0
            for c in chapters[1:]:
                assert c.get("content") == ""

    def test_public_book_body_does_not_contain_paid_content_raw(self, s, admin_chapters):
        """Guard test: the RAW JSON response body must not include the paid
        chapter body text anywhere (even as part of some other field)."""
        for slug in BOOK_SLUGS:
            paid_body = admin_chapters[slug][1].get("content", "")
            assert paid_body, f"{slug}: admin view has no paid body; test invalid"
            # Take a distinctive substring so we don't accidentally match common words.
            snippet = paid_body.strip().split("\n")[0][:120]
            assert len(snippet) > 30, "snippet too short to be distinctive"
            r = s.get(f"{API}/books/{slug}")
            assert r.status_code == 200
            assert snippet not in r.text, \
                f"{slug}: paid content snippet leaked in /books/{slug}"
            r2 = s.get(f"{API}/books")
            assert snippet not in r2.text, \
                f"{slug}: paid content snippet leaked in /books list"


# ---------------- 2. Admin endpoint keeps full content ----------------
class TestAdminBookUntouched:
    def test_admin_books_requires_auth(self, s):
        r = s.get(f"{API}/admin/books")
        assert r.status_code == 401

    def test_admin_books_returns_full_content(self, s, admin_headers):
        r = s.get(f"{API}/admin/books", headers=admin_headers)
        assert r.status_code == 200
        by_slug = {b["slug"]: b for b in r.json()}
        for slug in BOOK_SLUGS:
            chapters = sorted(by_slug[slug].get("chapters") or [],
                              key=lambda c: c.get("order", 0))
            # Every chapter should have non-empty content for admin view
            for c in chapters:
                assert (c.get("content") or "").strip(), \
                    f"admin view {slug}: chapter '{c.get('title')}' has empty content"


# ---------------- 3. /api/reader/chapter/{slug}/{cid} gating ----------------
class TestReaderChapterEndpoint:
    def test_guest_preview_returns_content(self, s, admin_chapters):
        preview = admin_chapters[PRIMARY_SLUG][0]
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{preview['id']}")
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is False
        assert j["is_preview"] is True
        assert j["chapter"]["id"] == preview["id"]
        assert j["chapter"]["title"] == preview["title"]
        assert j["chapter"]["order"] == preview["order"]
        assert (j["chapter"].get("content") or "").strip(), "preview content empty"
        assert j["chapter"]["content"] == preview["content"]

    def test_guest_paid_returns_locked_auth_required_no_content(self, s, admin_chapters):
        paid = admin_chapters[PRIMARY_SLUG][1]
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{paid['id']}")
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is True
        assert j["reason"] == "AUTH_REQUIRED"
        assert j.get("message")
        # Metadata only — no content key OR content must be absent/empty
        assert "content" not in j["chapter"] or not j["chapter"].get("content")
        assert j["chapter"]["id"] == paid["id"]
        assert j["chapter"]["title"] == paid["title"]
        # Guard: distinctive paid snippet must not appear anywhere in body
        snippet = paid["content"].strip().split("\n")[0][:120]
        assert snippet not in r.text, "paid body leaked in locked response!"

    def test_user_zero_balance_paid_returns_locked_insufficient(
        self, s, fresh_user, admin_headers, admin_chapters
    ):
        uid = fresh_user["user"]["id"]
        # Force balance to 0
        me = s.get(f"{API}/users/me", headers=fresh_user["headers"]).json()
        if me.get("reading_seconds_balance", 0) > 0:
            s.post(f"{API}/admin/users/{uid}/wallet/adjust",
                   json={"minutes": -10000, "reason": "TEST reset"},
                   headers=admin_headers)
        paid = admin_chapters[PRIMARY_SLUG][1]
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{paid['id']}",
                  headers=fresh_user["headers"])
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is True
        assert j["reason"] == "INSUFFICIENT_READING_TIME"
        assert "content" not in j["chapter"] or not j["chapter"].get("content")
        snippet = paid["content"].strip().split("\n")[0][:120]
        assert snippet not in r.text

    def test_user_positive_balance_paid_returns_content(
        self, s, fresh_user, admin_headers, admin_chapters
    ):
        uid = fresh_user["user"]["id"]
        s.post(f"{API}/admin/users/{uid}/wallet/adjust",
               json={"minutes": 30, "reason": "TEST unlock"},
               headers=admin_headers)
        paid = admin_chapters[PRIMARY_SLUG][1]
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{paid['id']}",
                  headers=fresh_user["headers"])
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is False
        assert j["is_preview"] is False
        assert j["chapter"]["content"] == paid["content"]
        # cleanup: drain balance back to 0 for downstream tests
        s.post(f"{API}/admin/users/{uid}/wallet/adjust",
               json={"minutes": -10000, "reason": "TEST drain"},
               headers=admin_headers)

    def test_blocked_user_gets_blocked_reason_no_content(
        self, s, fresh_user, admin_headers, admin_chapters
    ):
        uid = fresh_user["user"]["id"]
        # top up so we rule out INSUFFICIENT path
        s.post(f"{API}/admin/users/{uid}/wallet/adjust",
               json={"minutes": 30, "reason": "TEST"}, headers=admin_headers)
        # block
        br = s.patch(f"{API}/admin/users/{uid}/status",
                     json={"status": "blocked"}, headers=admin_headers)
        assert br.status_code == 200
        try:
            paid = admin_chapters[PRIMARY_SLUG][1]
            r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{paid['id']}",
                      headers=fresh_user["headers"])
            assert r.status_code == 200
            j = r.json()
            assert j["locked"] is True
            assert j["reason"] == "BLOCKED"
            assert "content" not in j["chapter"] or not j["chapter"].get("content")
            snippet = paid["content"].strip().split("\n")[0][:120]
            assert snippet not in r.text
        finally:
            # always unblock
            s.patch(f"{API}/admin/users/{uid}/status",
                    json={"status": "active"}, headers=admin_headers)

    def test_admin_token_unlocks_paid(self, s, admin_headers, admin_chapters):
        paid = admin_chapters[PRIMARY_SLUG][1]
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/{paid['id']}",
                  headers=admin_headers)
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is False
        assert j["is_preview"] is False
        assert j["chapter"]["content"] == paid["content"]

    def test_nonexistent_chapter_returns_404(self, s):
        r = s.get(f"{API}/reader/chapter/{PRIMARY_SLUG}/does-not-exist-{uuid.uuid4().hex[:6]}")
        assert r.status_code == 404

    def test_nonexistent_book_returns_404(self, s):
        r = s.get(f"{API}/reader/chapter/no-such-book-xyz/whatever")
        assert r.status_code == 404

    def test_second_book_guest_paid_also_gated(self, s, admin_chapters):
        """Ensure gating applies to BOTH seeded books, not just primary."""
        second = BOOK_SLUGS[1]
        paid = admin_chapters[second][1]
        r = s.get(f"{API}/reader/chapter/{second}/{paid['id']}")
        assert r.status_code == 200
        j = r.json()
        assert j["locked"] is True
        assert j["reason"] == "AUTH_REQUIRED"
        snippet = paid["content"].strip().split("\n")[0][:120]
        assert snippet not in r.text
