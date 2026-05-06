"""Phase 2 backend tests: user auth, reader sessions, heartbeat, admin wallet."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://earnalism-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@theearnalism.com"
ADMIN_PASSWORD = "Earnalism@2026"
BOOK_SLUG = "brownies-to-break-even-and-beyond"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def fresh_user(s):
    """Sign up a fresh user for the test run."""
    email = f"phase2-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    password = "TestPass123"
    r = s.post(f"{API}/users/signup", json={"name": "Phase2 Tester", "email": email, "password": password})
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
def book_chapters(s):
    r = s.get(f"{API}/books/{BOOK_SLUG}")
    assert r.status_code == 200, r.text
    chapters = sorted(r.json().get("chapters") or [], key=lambda c: c.get("order", 0))
    assert len(chapters) >= 2, "need at least 2 chapters for preview & paid tests"
    return chapters


# --------------------- Signup / Login ---------------------
class TestUserAuth:
    def test_signup_short_password_400(self, s):
        r = s.post(f"{API}/users/signup", json={
            "name": "X", "email": f"short-{uuid.uuid4().hex[:6]}@t.com", "password": "abc"
        })
        assert r.status_code == 400

    def test_signup_returns_token_and_user(self, fresh_user):
        assert fresh_user["token"]
        u = fresh_user["user"]
        assert u["email"] == fresh_user["email"].lower()
        assert u["role"] == "user"
        assert u["reading_seconds_balance"] == 0
        assert "password_hash" not in u

    def test_signup_normalizes_email_lowercase(self, s):
        email = f"Mixed-{uuid.uuid4().hex[:6]}@TeSt.com"
        r = s.post(f"{API}/users/signup", json={"name": "Mix", "email": email, "password": "TestPass123"})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == email.lower()

    def test_signup_duplicate_400(self, s, fresh_user):
        r = s.post(f"{API}/users/signup", json={
            "name": "Dup", "email": fresh_user["email"], "password": "TestPass123"
        })
        assert r.status_code == 400

    def test_login_wrong_password_401(self, s, fresh_user):
        r = s.post(f"{API}/users/login", json={"email": fresh_user["email"], "password": "wrong-pw"})
        assert r.status_code == 401
        assert "Invalid email or password" in r.json().get("detail", "")

    def test_login_correct_returns_token(self, s, fresh_user):
        r = s.post(f"{API}/users/login", json={"email": fresh_user["email"], "password": fresh_user["password"]})
        assert r.status_code == 200
        j = r.json()
        assert j["token"] and j["user"]["email"] == fresh_user["email"].lower()

    def test_users_me_with_user_token(self, s, fresh_user):
        r = s.get(f"{API}/users/me", headers=fresh_user["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == fresh_user["email"].lower()
        assert "password_hash" not in body

    def test_users_me_unauth_401(self, s):
        r = s.get(f"{API}/users/me")
        assert r.status_code == 401


# --------------------- Cross-role isolation ---------------------
class TestCrossRoleIsolation:
    def test_users_me_with_admin_token_403(self, s, admin_headers):
        r = s.get(f"{API}/users/me", headers=admin_headers)
        assert r.status_code == 403

    def test_admin_users_with_user_token_403(self, s, fresh_user):
        r = s.get(f"{API}/admin/users", headers=fresh_user["headers"])
        assert r.status_code == 403

    def test_admin_users_with_admin_token_returns_users_only(self, s, admin_headers):
        r = s.get(f"{API}/admin/users", headers=admin_headers)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for u in rows:
            assert u.get("role") == "user", f"admin/users returned {u.get('role')}"


# --------------------- Admin wallet adjust ---------------------
class TestWalletAdjust:
    def test_admin_credit_minutes(self, s, admin_headers, fresh_user):
        uid = fresh_user["user"]["id"]
        r = s.post(f"{API}/admin/users/{uid}/wallet/adjust",
                   json={"minutes": 60, "reason": "TEST top-up"}, headers=admin_headers)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["applied_seconds"] == 3600
        assert j["reading_seconds_balance"] == 3600

    def test_admin_debit_clamped_at_zero(self, s, admin_headers, fresh_user):
        uid = fresh_user["user"]["id"]
        # current is 3600 from previous test; deduct 90min => clamp at 0, applied -3600
        r = s.post(f"{API}/admin/users/{uid}/wallet/adjust",
                   json={"minutes": -90, "reason": "TEST overdraw"}, headers=admin_headers)
        assert r.status_code == 200
        j = r.json()
        assert j["reading_seconds_balance"] == 0
        assert j["applied_seconds"] == -3600

    def test_admin_user_transactions_sorted_desc(self, s, admin_headers, fresh_user):
        uid = fresh_user["user"]["id"]
        r = s.get(f"{API}/admin/users/{uid}/transactions", headers=admin_headers)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 2
        # sorted desc by created_at
        ts = [row["created_at"] for row in rows]
        assert ts == sorted(ts, reverse=True)


# --------------------- Reader: sessions + heartbeat ---------------------
class TestReaderFlow:
    def test_session_start_unauth_401(self, s, book_chapters):
        r = s.post(f"{API}/reader/session/start", json={
            "book_slug": BOOK_SLUG, "chapter_id": book_chapters[1]["id"]
        })
        assert r.status_code == 401

    def test_session_start_paid_chapter_zero_balance_402(self, s, fresh_user, book_chapters, admin_headers):
        # Ensure balance is 0
        uid = fresh_user["user"]["id"]
        # query me to read balance
        me = s.get(f"{API}/users/me", headers=fresh_user["headers"]).json()
        if me["reading_seconds_balance"] > 0:
            s.post(f"{API}/admin/users/{uid}/wallet/adjust",
                   json={"minutes": -10000, "reason": "TEST reset to 0"},
                   headers=admin_headers)
        paid_chap = book_chapters[1]["id"]
        r = s.post(f"{API}/reader/session/start",
                   json={"book_slug": BOOK_SLUG, "chapter_id": paid_chap},
                   headers=fresh_user["headers"])
        assert r.status_code == 402

    def test_session_start_preview_chapter_zero_balance_ok(self, s, fresh_user, book_chapters):
        preview_chap = book_chapters[0]["id"]
        r = s.post(f"{API}/reader/session/start",
                   json={"book_slug": BOOK_SLUG, "chapter_id": preview_chap},
                   headers=fresh_user["headers"])
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["is_preview"] is True
        assert j["tick_seconds"] == 30
        assert "session_id" in j

    def test_heartbeat_preview_never_deducts(self, s, fresh_user, book_chapters):
        preview_chap = book_chapters[0]["id"]
        start = s.post(f"{API}/reader/session/start",
                       json={"book_slug": BOOK_SLUG, "chapter_id": preview_chap},
                       headers=fresh_user["headers"]).json()
        sid = start["session_id"]
        r = s.post(f"{API}/reader/heartbeat",
                   json={"session_id": sid, "visible": True, "idle": False, "chapter_id": preview_chap},
                   headers=fresh_user["headers"])
        assert r.status_code == 200
        j = r.json()
        assert j["deducted_seconds"] == 0
        assert j["status"] == "preview"
        assert j["is_preview"] is True

    def test_heartbeat_visible_active_deducts_30s(self, s, fresh_user, book_chapters, admin_headers):
        uid = fresh_user["user"]["id"]
        # Top up 2 minutes
        s.post(f"{API}/admin/users/{uid}/wallet/adjust",
               json={"minutes": 2, "reason": "TEST heartbeat"},
               headers=admin_headers)
        paid_chap = book_chapters[1]["id"]
        start = s.post(f"{API}/reader/session/start",
                       json={"book_slug": BOOK_SLUG, "chapter_id": paid_chap},
                       headers=fresh_user["headers"]).json()
        sid = start["session_id"]

        # 1st beat: deduct 30 -> remaining 90
        r1 = s.post(f"{API}/reader/heartbeat",
                    json={"session_id": sid, "visible": True, "idle": False, "chapter_id": paid_chap},
                    headers=fresh_user["headers"]).json()
        assert r1["deducted_seconds"] == 30
        assert r1["remaining_seconds"] == 90
        assert r1["status"] == "active"

        # visible:false -> 0 deducted, paused
        r2 = s.post(f"{API}/reader/heartbeat",
                    json={"session_id": sid, "visible": False, "idle": False, "chapter_id": paid_chap},
                    headers=fresh_user["headers"]).json()
        assert r2["deducted_seconds"] == 0
        assert r2["status"] == "paused"
        assert r2["remaining_seconds"] == 90

        # idle:true -> 0 deducted, paused
        r3 = s.post(f"{API}/reader/heartbeat",
                    json={"session_id": sid, "visible": True, "idle": True, "chapter_id": paid_chap},
                    headers=fresh_user["headers"]).json()
        assert r3["deducted_seconds"] == 0
        assert r3["status"] == "paused"

        # 3 more active beats to drain balance: 90->60->30->0
        last = None
        for _ in range(3):
            last = s.post(f"{API}/reader/heartbeat",
                          json={"session_id": sid, "visible": True, "idle": False, "chapter_id": paid_chap},
                          headers=fresh_user["headers"]).json()
        assert last["remaining_seconds"] == 0
        assert last["status"] == "depleted"

        # Further beat with 0 balance -> deducted 0, status depleted
        r4 = s.post(f"{API}/reader/heartbeat",
                    json={"session_id": sid, "visible": True, "idle": False, "chapter_id": paid_chap},
                    headers=fresh_user["headers"]).json()
        assert r4["deducted_seconds"] == 0
        assert r4["status"] == "depleted"
        assert r4["remaining_seconds"] == 0

        # End the session
        end = s.post(f"{API}/reader/session/end",
                     json={"session_id": sid},
                     headers=fresh_user["headers"])
        assert end.status_code == 200
        assert end.json()["ended"] == 1


# --------------------- Block / Unblock ---------------------
class TestBlockUnblock:
    def test_block_then_login_403_then_unblock(self, s, admin_headers, fresh_user):
        uid = fresh_user["user"]["id"]
        # block
        r = s.patch(f"{API}/admin/users/{uid}/status",
                    json={"status": "blocked"}, headers=admin_headers)
        assert r.status_code == 200
        # login should now 403
        r2 = s.post(f"{API}/users/login",
                    json={"email": fresh_user["email"], "password": fresh_user["password"]})
        assert r2.status_code == 403, r2.text
        # unblock
        r3 = s.patch(f"{API}/admin/users/{uid}/status",
                     json={"status": "active"}, headers=admin_headers)
        assert r3.status_code == 200
        # login OK again
        r4 = s.post(f"{API}/users/login",
                    json={"email": fresh_user["email"], "password": fresh_user["password"]})
        assert r4.status_code == 200
