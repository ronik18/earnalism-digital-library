"""Backend API tests for The Earnalism."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://earnalism-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@theearnalism.com"
ADMIN_PASSWORD = "Earnalism@2026"


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
    assert isinstance(data, list) and len(data) == 5
    slugs = {c["slug"] for c in data}
    assert {"business", "self-growth", "literature", "spirituality", "bengali-reading"} <= slugs


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


def test_publishing_request(s):
    r = s.post(f"{API}/publishing-request", json={
        "name": "TEST", "email": f"p_{uuid.uuid4().hex[:6]}@x.com",
        "project_title": "TEST Book", "message": "TEST"
    })
    assert r.status_code == 200 and r.json()["ok"] is True


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
    for path in ["/admin/newsletter", "/admin/contacts", "/admin/publishing-requests",
                 "/admin/books", "/admin/blog"]:
        r = s.get(f"{API}{path}")
        assert r.status_code == 401, f"{path} should be 401"


def test_admin_lists_with_auth(s, auth):
    for path in ["/admin/newsletter", "/admin/contacts", "/admin/publishing-requests",
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
