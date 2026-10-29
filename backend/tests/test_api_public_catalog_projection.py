from __future__ import annotations

import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-catalog-projection-test-secret")

from backend import catalog_truth
from backend import server


def test_public_book_out_drops_private_catalog_fields():
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story", include_content=True)
    assert artifact is not None
    artifact["rights_metadata"] = {"rights_tier": "A"}
    artifact["audiobook_assets"] = {"mp3": "https://cdn.example.com/dracula.mp3"}

    projected = catalog_truth.public_book_projection(artifact)
    dumped = server.PublicBookOut.model_validate(projected).model_dump()

    serialized = str(dumped)
    assert dumped["slug"] == "a-ghost-story"
    assert dumped["reader_enabled"] is True
    assert dumped["preview_enabled"] is True
    assert dumped["audio_enabled"] is False
    assert dumped["audiobook_enabled"] is False
    assert dumped["audio_url"] == ""
    assert "rights_metadata" not in serialized
    assert "source_hash" not in serialized
    assert "content_hash" not in serialized
    assert "provenance_hash" not in serialized
    assert "audiobook_assets" not in serialized
    assert "https://cdn.example.com/dracula.mp3" not in serialized
    assert all("content" not in chapter for chapter in dumped["chapters"])


def test_public_projection_keeps_kshudhita_pipeline_only():
    projected = catalog_truth.public_book_projection(
        {
            "slug": "kshudhita-pashan",
            "title": "Kshudhita Pashan",
            "is_published": True,
            "pipeline_stage": "PIPELINE_ONLY",
            "reader_url": "/reader/kshudhita-pashan",
            "audiobook_assets": {"mp3": "https://cdn.example.com/kshudhita.mp3"},
        }
    )

    assert projected["publication_status"] == "PIPELINE_CANDIDATE"
    assert projected["reader_enabled"] is False
    assert projected["preview_enabled"] is False
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["reader_url"] == ""
    assert projected["preview_url"] == ""
    assert projected["audio_url"] == ""
    assert "audiobook_assets" not in projected


def test_actual_book_response_model_keeps_approved_package_metadata(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    artifact = server._controlled_artifact_doc("the-open-window")
    assert artifact is not None
    async def no_cache(*args, **kwargs): return None
    async def candidate(*args, **kwargs): return artifact, "controlled"
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_find_public_book_candidate", candidate)
    app = FastAPI()
    app.get("/books/{slug}", response_model=server.PublicBookOut)(server.get_book)
    response = TestClient(app).get("/books/the-open-window")
    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_enabled"] is True
    assert payload["audiobook_delivery_mode"] == "PROTECTED_PACKAGE_V2"
    assert payload["audiobook_package_version"] == "sha256-8e5c83a835cf8bea0a34809f8640603a2158a3cfe1aa8f1ac71117259a665b26"
    assert payload["audiobook_duration_ms"] == 491436
    assert payload["audio_url"] == ""
    for private in ["audiobook_packages", "audiobook_public_package_approval", "audiobook_package_release_evidence", "rights_metadata", "source_hash"]:
        assert private not in payload


def test_unreleased_book_response_model_keeps_package_metadata_empty():
    artifact = server._controlled_artifact_doc("a-ghost-story")
    projected = server._safe_live_public_projection(artifact)
    payload = server.PublicBookOut.model_validate(projected).model_dump()
    assert payload["audio_enabled"] is False
    assert payload["audiobook_delivery_mode"] == ""
    assert payload["audiobook_package_version"] == ""
    assert payload["audiobook_duration_ms"] == 0


def test_selfish_giant_final_public_response_keeps_exact_protected_package(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    artifact = server._controlled_artifact_doc("the-selfish-giant")
    assert artifact is not None
    async def no_cache(*args, **kwargs): return None
    async def candidate(*args, **kwargs): return artifact, "controlled"
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_find_public_book_candidate", candidate)
    app = FastAPI()
    app.get("/books/{slug}", response_model=server.PublicBookOut)(server.get_book)
    response = TestClient(app).get("/books/the-selfish-giant")
    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_enabled"] is True
    assert payload["audiobook_delivery_mode"] == "PROTECTED_PACKAGE_V2"
    assert payload["audiobook_package_version"] == "sha256-b00212b82996e194a7b3bef4f3fb8982304b71afcd32e5f0fa6e93e9341f3211"
    assert payload["audiobook_duration_ms"] == 777120
    assert payload["audio_url"] == ""
    for private in ["audiobook_packages", "audiobook_public_package_approval", "audiobook_package_release_evidence", "rights_metadata", "source_hash"]:
        assert private not in payload


def test_actual_candidate_merge_preserves_canonical_package_over_legacy_conveyor(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    artifact = server._controlled_artifact_doc('the-selfish-giant')
    # Historical approved conveyor metadata must not overwrite a later exact,
    # independently approved immutable protected publication.
    stale = {'slug': 'the-selfish-giant', 'audio_enabled': False,
             'audiobook_enabled': False, 'audio_status': 'NOT_AVAILABLE',
             'audiobook_release_gate': '', 'audio_qa_status': '',
             'audiobook_release_conveyor': {'schema_version': server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                                           'audio_release_approved': True}}
    async def find_one(*args, **kwargs): return stale
    async def no_cache(*args, **kwargs): return None
    monkeypatch.setattr(server, 'db', SimpleNamespace(books=SimpleNamespace(find_one=find_one)))
    monkeypatch.setattr(server, '_public_cache_get', no_cache)
    monkeypatch.setattr(server, '_public_cache_set', no_cache)
    app = FastAPI()
    app.get('/books/{slug}', response_model=server.PublicBookOut)(server.get_book)
    response = TestClient(app).get('/books/the-selfish-giant')
    assert response.status_code == 200
    payload = response.json()
    assert payload['audio_enabled'] is True
    assert payload['audiobook_delivery_mode'] == 'PROTECTED_PACKAGE_V2'
    assert payload['audiobook_duration_ms'] == 777120
    assert payload['audiobook_package_version'] == 'sha256-b00212b82996e194a7b3bef4f3fb8982304b71afcd32e5f0fa6e93e9341f3211'
    assert payload['audio_url'] == ''
    assert server._reader_audio_truth_doc(stale, 'the-selfish-giant')['audio_enabled'] is True
    assert server._merge_controlled_publication_truth(stale, artifact, slug='the-selfish-giant')['audiobook_public_package_approval'] == artifact['audiobook_public_package_approval']


def test_invalid_canonical_package_cannot_fall_back_to_legacy_database_approval():
    import copy
    artifact = copy.deepcopy(server._controlled_artifact_doc('the-selfish-giant'))
    artifact['audiobook_public_package_approval']['acceptance_sha256'] = '0' * 64
    legacy = {'audio_enabled': True, 'audiobook_enabled': True,
              'audiobook_release_gate': 'APPROVED', 'audio_qa_status': 'QA_PASSED',
              'audiobook_release_conveyor': {'schema_version': server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                                            'audio_release_approved': True}}
    merged = server._merge_controlled_publication_truth(legacy, artifact, slug='the-selfish-giant')
    assert not server.can_expose_audio(merged)


def test_existing_legacy_conveyor_overlay_remains_available_to_legacy_format():
    artifact = {'slug': 'legacy-fixture', 'audiobook_release_mode': 'LEGACY'}
    database = {'audio_status': 'APPROVED',
                'audiobook_release_conveyor': {'schema_version': server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                                              'audio_release_approved': True}}
    merged = server._merge_controlled_publication_truth(database, artifact, slug='legacy-fixture')
    assert merged['audio_status'] == database['audio_status']
    assert merged['audiobook_release_conveyor'] == database['audiobook_release_conveyor']


def test_explicit_canonical_protected_deny_cannot_be_reenabled_by_legacy_database():
    import copy
    artifact = copy.deepcopy(server._controlled_artifact_doc('the-selfish-giant'))
    artifact['audio_enabled'] = False
    artifact['audiobook_enabled'] = False
    database = {'audio_enabled': True, 'audiobook_enabled': True,
                'audiobook_assets': {'mp3': 'https://invalid.example/old.mp3'},
                'audiobook_release_conveyor': {'schema_version': server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                                              'audio_release_approved': True}}
    merged = server._merge_controlled_publication_truth(database, artifact, slug='the-selfish-giant')
    assert merged['audio_enabled'] is False and merged['audiobook_enabled'] is False
    assert merged['audiobook_assets'] == {}
    assert not server.can_expose_audio(merged)
