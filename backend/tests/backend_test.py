"""Backend API tests for The Earnalism."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@theearnalism.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Earnalism@2026")


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="session")
def token(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ----- Public -----
def test_categories(s):
    r = s.get(f"{API}/categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 5
    slugs = {c["slug"] for c in data}
    assert {"business", "technology", "history-strategy", "bengali-classics", "classic-literature"} <= slugs


def test_featured(s):
    r = s.get(f"{API}/featured")
    assert r.status_code == 200
    book = r.json().get("book")
    assert book and book["slug"] == "brownies-to-break-even-and-beyond"


def test_books_list_and_detail(s):
    r = s.get(f"{API}/books")
    assert r.status_code == 200
    assert any(b["slug"] == "brownies-to-break-even-and-beyond" for b in r.json())
    r2 = s.get(f"{API}/books/brownies-to-break-even-and-beyond")
    assert r2.status_code == 200
    assert r2.json()["title"].startswith("Brownies")


def test_blog_list_and_detail(s):
    r = s.get(f"{API}/blog")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) >= 3
    slug = posts[0]["slug"]
    r2 = s.get(f"{API}/blog/{slug}")
    assert r2.status_code == 200
    assert r2.json()["slug"] == slug


def test_newsletter_subscribe_and_dedupe(s):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/newsletter", json={"name": "TEST User", "email": email})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "Welcome" in r.json()["message"]
    r2 = s.post(f"{API}/newsletter", json={"name": "TEST User", "email": email})
    assert r2.status_code == 200
    assert "already part" in r2.json()["message"]


def test_contact(s):
    r = s.post(f"{API}/contact", json={
        "name": "TEST", "email": f"t_{uuid.uuid4().hex[:6]}@x.com",
        "subject": "Hello", "message": "TEST message"
    })
    assert r.status_code == 200 and r.json()["ok"] is True


def test_publishing_request_removed(s):
    """POST /api/publishing-request should be 404 (route removed)."""
    r = s.post(f"{API}/publishing-request", json={
        "name": "TEST", "email": "p@x.com",
        "project_title": "TEST", "message": "TEST"
    })
    assert r.status_code == 404


def test_admin_publishing_requests_removed(s):
    """GET /api/admin/publishing-requests should be 404 (route removed)."""
    r = s.get(f"{API}/admin/publishing-requests")
    assert r.status_code == 404


def test_book_about_author_no_publishing_brand(s):
    r = s.get(f"{API}/books/brownies-to-break-even-and-beyond")
    assert r.status_code == 200
    assert "publishing brand" not in r.json()["about_author"].lower()


# ----- Social settings -----
def test_get_social_public_returns_5_keys(s):
    r = s.get(f"{API}/settings/social")
    assert r.status_code == 200
    data = r.json()
    for k in ("instagram", "facebook", "youtube", "linkedin", "twitter"):
        assert k in data, f"Missing key {k}"
        assert isinstance(data[k], str)


def test_put_social_requires_auth(s):
    r = s.put(f"{API}/admin/settings/social", json={"instagram": "https://x"})
    assert r.status_code == 401


def test_put_social_persists(s, auth):
    payload = {
        "instagram": "https://instagram.com/earnalism_test",
        "facebook": "https://facebook.com/earnalism_test",
        "youtube": "",
        "linkedin": "",
        "twitter": "",
    }
    r = s.put(f"{API}/admin/settings/social", json=payload, headers=auth)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # GET should match
    r2 = s.get(f"{API}/settings/social")
    assert r2.status_code == 200
    got = r2.json()
    for k, v in payload.items():
        assert got[k] == v, f"{k}: expected {v}, got {got[k]}"
    # cleanup: clear
    r3 = s.put(f"{API}/admin/settings/social", json={
        "instagram": "", "facebook": "", "youtube": "", "linkedin": "", "twitter": ""
    }, headers=auth)
    assert r3.status_code == 200


# ----- Auth -----
def test_login_success(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    j = r.json()
    assert j["token"] and j["role"] == "admin"


def test_login_invalid(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(s):
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_me_with_token(s, auth):
    r = s.get(f"{API}/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL.lower()
    assert r.json()["role"] == "admin"


# ----- Admin protected lists -----
def test_admin_lists_require_auth(s):
    for path in ["/admin/newsletter", "/admin/contacts",
                 "/admin/books", "/admin/blog"]:
        r = s.get(f"{API}{path}")
        assert r.status_code == 401, f"{path} should be 401"


def test_admin_lists_with_auth(s, auth):
    for path in ["/admin/newsletter", "/admin/contacts",
                 "/admin/books", "/admin/blog"]:
        r = s.get(f"{API}{path}", headers=auth)
        assert r.status_code == 200, f"{path}: {r.status_code}"
        assert isinstance(r.json(), list)


# ----- Admin CRUD -----
def test_admin_book_crud(s, auth):
    title = f"TEST Book {uuid.uuid4().hex[:6]}"
    payload = {"title": title, "category_slug": "business", "short_description": "x"}
    r = s.post(f"{API}/admin/books", json=payload, headers=auth)
    assert r.status_code == 200, r.text
    slug = r.json()["slug"]
    # GET via public
    r2 = s.get(f"{API}/books/{slug}")
    assert r2.status_code == 200
    # UPDATE
    payload["short_description"] = "TEST updated"
    r3 = s.put(f"{API}/admin/books/{slug}", json=payload, headers=auth)
    assert r3.status_code == 200
    assert r3.json()["short_description"] == "TEST updated"
    # CHAPTER REORDER
    c1 = s.post(f"{API}/admin/books/{slug}/chapters", json={"title": "One", "content": "First"}, headers=auth)
    assert c1.status_code == 200, c1.text
    c2 = s.post(f"{API}/admin/books/{slug}/chapters", json={"title": "Two", "content": "Second"}, headers=auth)
    assert c2.status_code == 200, c2.text
    ids = [c["id"] for c in sorted(c2.json()["chapters"], key=lambda c: c.get("order", 0))]
    rr = s.put(f"{API}/admin/books/{slug}/chapters/reorder", json={"ids": list(reversed(ids))}, headers=auth)
    assert rr.status_code == 200, rr.text
    reordered = sorted(rr.json()["chapters"], key=lambda c: c.get("order", 0))
    assert [c["title"] for c in reordered] == ["Two", "One"]
    # DELETE
    r4 = s.delete(f"{API}/admin/books/{r3.json()['slug']}", headers=auth)
    assert r4.status_code == 200 and r4.json()["deleted"] == 1


def test_admin_blog_crud(s, auth):
    title = f"TEST Post {uuid.uuid4().hex[:6]}"
    r = s.post(f"{API}/admin/blog", json={"title": title, "excerpt": "e", "content": "c"}, headers=auth)
    assert r.status_code == 200
    slug = r.json()["slug"]
    r2 = s.put(f"{API}/admin/blog/{slug}", json={"title": title, "excerpt": "TEST e2", "content": "c"}, headers=auth)
    assert r2.status_code == 200 and r2.json()["excerpt"] == "TEST e2"
    r3 = s.delete(f"{API}/admin/blog/{slug}", headers=auth)
    assert r3.status_code == 200


def test_admin_category_crud(s, auth):
    name = f"TEST Cat {uuid.uuid4().hex[:6]}"
    r = s.post(f"{API}/admin/categories", json={"name": name}, headers=auth)
    assert r.status_code == 200
    slug = r.json()["slug"]
    r2 = s.put(f"{API}/admin/categories/{slug}", json={"name": name, "description": "TEST d"}, headers=auth)
    assert r2.status_code == 200 and r2.json()["description"] == "TEST d"
    r3 = s.delete(f"{API}/admin/categories/{slug}", headers=auth)
    assert r3.status_code == 200


def test_admin_featured(s, auth):
    r = s.put(f"{API}/admin/featured", json={"book_slug": "brownies-to-break-even-and-beyond"}, headers=auth)
    assert r.status_code == 200 and r.json()["ok"] is True


def test_admin_crud_no_auth(s):
    r = s.post(f"{API}/admin/books", json={"title": "x", "category_slug": "business"})
    assert r.status_code == 401
