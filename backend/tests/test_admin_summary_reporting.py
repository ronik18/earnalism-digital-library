"""Exercise the actual ASGI response-model boundary, without production data."""
import asyncio
import copy
import importlib
import os
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

os.environ.setdefault("JWT_SECRET", "synthetic-admin-summary-test")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/test_admin_summary")
server = importlib.import_module("backend.server")
from backend.publication_workflow_adapter import canonical_update
from backend.api.schemas import Book


class Books:
    def __init__(self, rows):
        self.rows = rows

    def find(self, *_args):
        return self

    def sort(self, *_args):
        return self

    async def to_list(self, *_args):
        return copy.deepcopy(self.rows)


def request(monkeypatch, rows, authorized=True, path="/api/admin/books/summary"):
    app = FastAPI()
    app.include_router(server.api)
    @app.get("/synthetic-public", response_model=Book)
    def public_contract():
        return rows[0]
    if authorized:
        app.dependency_overrides[server.require_admin] = lambda: {"role": "admin"}
    monkeypatch.setattr(server, "db", SimpleNamespace(books=Books(rows)))
    async def execute():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(path)
    return asyncio.run(execute())


def row():
    book = {"id": "synthetic-id", "slug": "synthetic-title", "title": "Synthetic", "category_slug": "test"}
    book["publication_workflow"] = canonical_update(book)
    return book


def test_workflow_survives_http_serialization_without_writes(monkeypatch):
    book = row()
    original = copy.deepcopy(book)
    response = request(monkeypatch, [book])
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == book["id"]
    assert body[0]["publication_workflow"] == book["publication_workflow"]
    assert body[0]["admin_reporting"]["protected_text"]["status"] == "UNVERIFIED"
    assert book == original  # collection implements no write operation


def test_unauthorized_http_cannot_obtain_workflow(monkeypatch):
    response = request(monkeypatch, [row()], authorized=False)
    assert response.status_code in (401, 403)
    assert "publication_workflow" not in response.text


def test_public_contract_does_not_gain_admin_fields(monkeypatch):
    public = request(monkeypatch, [row()], path="/synthetic-public").json()
    assert "publication_workflow" not in public
    assert "admin_reporting" not in public


def test_editorial_and_runtime_capability_are_independent(monkeypatch):
    draft, published = row(), row()
    published["is_published"] = True
    monkeypatch.setattr(server, "_reader_audio_truth_doc", lambda book, _slug: book)
    monkeypatch.setattr(server, "_safe_live_public_projection", lambda book: {"preview_enabled": True, "audio_enabled": False} if not book.get("is_published") else None)
    draft_report, published_report = request(monkeypatch, [draft, published]).json()
    assert draft_report["admin_reporting"]["editorial"]["status"] == "DRAFT"
    assert draft_report["admin_reporting"]["preview"]["status"] == "CONFIGURED_AVAILABLE"
    assert published_report["admin_reporting"]["editorial"]["status"] == "PUBLISHED"
    assert published_report["admin_reporting"]["protected_text"]["status"] == "UNVERIFIED"
    assert published_report["admin_reporting"]["preview"]["status"] == "NOT_ADVERTISED"


def test_missing_and_malformed_workflow_stay_unknown(monkeypatch):
    rows = [row(), row()]
    rows[0].pop("publication_workflow")
    rows[1]["publication_workflow"] = {"rights": {"verification_status": "APPROVED"}}
    response = request(monkeypatch, rows)
    for book in response.json():
        assert book["publication_workflow"] is None
        assert book["admin_reporting"]["workflow"]["status"] == "UNAVAILABLE"
