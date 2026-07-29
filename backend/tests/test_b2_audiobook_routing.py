import importlib
import asyncio
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def _package_book():
    from audiobook_packages import with_canonical_package_version

    release_descriptor_sha256 = "1" * 64
    manuscript_sha256 = "2" * 64
    prefix = (
        "v1/prod/sprint1/the-open-window/releases/"
        f"{release_descriptor_sha256}/"
    )

    def asset(name, digest, size, mime_type, segment_id):
        key = f"{prefix}{segment_id}.{name}"
        return {
            "sha256": digest,
            "size_bytes": size,
            "mime_type": mime_type,
            "storage": {
                "store": "prod",
                "bucket": "earnalism-audio-prod",
                "key": key,
                "version_id": f"primary-{segment_id}-{name}",
            },
            "replicas": [
                {
                    "store": "dr",
                    "bucket": "earnalism-audio-dr",
                    "key": key,
                    "version_id": f"replica-{segment_id}-{name}",
                }
            ],
        }

    package = with_canonical_package_version({
        "schema_version": "audiobook_package_manifest.v2",
        "slug": "the-open-window",
        "release_evidence_version": "release-evidence-v1",
        "release_descriptor_sha256": release_descriptor_sha256,
        "source_sha256": "d" * 64,
        "manuscript_sha256": manuscript_sha256,
        "duration_ms": 620_000,
        "segment_count": 2,
        "word_count": 200,
        "paragraph_count": 2,
        "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
        "highlight_sync_enabled": True,
        "tracks": [
            {
                "id": "chapter-001",
                "chapter_id": "chapter-001",
                "order": 0,
                "title": "Chapter 1",
                "start_word": 0,
                "end_word": 199,
                "start_paragraph": 0,
                "end_paragraph": 1,
                "chunks": [
                    {
                        "segment_id": "c001-s001",
                        "order": 0,
                        "start_word": 0,
                        "end_word": 99,
                        "start_paragraph": 0,
                        "end_paragraph": 0,
                        "cumulative_start_ms": 0,
                        "duration_ms": 300_000,
                        "assets": {
                            "audio": asset(
                                "audio",
                                "b" * 64,
                                4_800_000,
                                "audio/mpeg",
                                "c001-s001",
                            ),
                            "timestamps": asset(
                                "timestamps",
                                "c" * 64,
                                1200,
                                "application/json",
                                "c001-s001",
                            ),
                            "vtt": asset(
                                "vtt",
                                "3" * 64,
                                900,
                                "text/vtt",
                                "c001-s001",
                            ),
                            "metadata": asset(
                                "metadata",
                                "4" * 64,
                                700,
                                "application/json",
                                "c001-s001",
                            ),
                        },
                    },
                    {
                        "segment_id": "c001-s002",
                        "order": 1,
                        "start_word": 100,
                        "end_word": 199,
                        "start_paragraph": 1,
                        "end_paragraph": 1,
                        "cumulative_start_ms": 300_000,
                        "duration_ms": 320_000,
                        "assets": {
                            "audio": asset(
                                "audio",
                                "e" * 64,
                                5_120_000,
                                "audio/mpeg",
                                "c001-s002",
                            ),
                            "timestamps": asset(
                                "timestamps",
                                "f" * 64,
                                1300,
                                "application/json",
                                "c001-s002",
                            ),
                            "vtt": asset(
                                "vtt",
                                "5" * 64,
                                950,
                                "text/vtt",
                                "c001-s002",
                            ),
                            "metadata": asset(
                                "metadata",
                                "6" * 64,
                                720,
                                "application/json",
                                "c001-s002",
                            ),
                        },
                    },
                ],
            }
        ],
    })
    release_evidence = {
        "schema_version": "audiobook_package_release_evidence.v1",
        "slug": "the-open-window",
        "release_descriptor_sha256": release_descriptor_sha256,
        "package_version": package["package_version"],
        "primary_receipt_sha256": "7" * 64,
        "replica_receipt_sha256": "8" * 64,
        "receipt_roles": ["primary", "replica"],
        "release_eligible": True,
        "release_manifest_sha256": "9" * 64,
        "release_manifest_size_bytes": 12345,
        "release_manifest_key": (
            f"{prefix}release-manifest.json"
        ),
        "primary_release_manifest_version_id": "primary-manifest-version",
        "replica_release_manifest_version_id": "replica-manifest-version",
        "primary_release_manifest_store": "prod",
        "replica_release_manifest_store": "dr",
        "primary_release_manifest_receipt_sha256": "a" * 64,
        "replica_release_manifest_receipt_sha256": "0" * 64,
    }
    return {
        "slug": "the-open-window",
        "is_published": True,
        "audiobook_enabled": True,
        "content_hash": "d" * 64,
        "audiobook_manuscript_sha256": manuscript_sha256,
        "audiobook_release_descriptor_sha256": release_descriptor_sha256,
        "audiobook_assets": {},
        "audiobook_package": package,
        "audiobook_package_release_evidence": {
            release_descriptor_sha256: release_evidence,
        },
    }


def test_reader_manifest_rewrites_b2_mp3_to_api_proxy(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    monkeypatch.setattr(server, "B2_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_BUCKET", "earnalism-audio")
    monkeypatch.setattr(server, "B2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setattr(server, "B2_SECRET_ACCESS_KEY", "test-secret")
    book = {
        "audiobook_provider": "b2",
        "audio_asset_slug": "dracula",
        "audiobook_assets": {
            "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3",
            "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula_timestamps.json",
            "vtt": "https://res.cloudinary.com/demo/raw/upload/dracula_highlight.vtt",
        },
        "audiobook": {
            "provider": "b2",
            "url": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3",
            "size": 120_000_000,
            "duration_ms": 1234,
        },
    }

    audio = server._reader_manifest_audio(book, "dracula")

    assert audio["provider"] == "b2"
    assert audio["assets"]["mp3"] == "/api/reader/book/dracula/audiobook"
    assert audio["assets"]["timestamps"] == "/api/reader/book/dracula/audiobook/timestamps"
    assert audio["assets"]["vtt"].startswith("https://res.cloudinary.com/")
    assert audio["url"] == "/api/reader/book/dracula/audiobook"
    assert audio["size"] == 120_000_000
    assert audio["duration_ms"] == 1234


def test_reader_manifest_audio_slug_alone_does_not_enable_audio(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    book = {
        "audio_asset_slug": "dracula",
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }

    audio = server._reader_manifest_audio(book, "dracula")

    assert audio["asset_slug"] == "dracula"
    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""


def test_package_manifest_projects_only_same_origin_release_gated_urls(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)
    book = _package_book()

    manifest = server._reader_audio_package_manifest(book, "the-open-window")
    audio = server._reader_manifest_audio(book, "the-open-window")

    assert manifest is not None
    assert manifest["schema_version"] == "audiobook_package_manifest.v2"
    assert manifest["segment_count"] == 2
    assert manifest["tracks"][0]["audio_url"].startswith(
        "/api/reader/book/the-open-window/audiobook/packages/"
    )
    assert manifest["tracks"][0]["chunks"][1]["segment_id"] == "c001-s002"
    assert manifest["tracks"][0]["chunks"][1]["start_word"] == 100
    assert "source_sha256" not in manifest
    assert "release_evidence_version" not in manifest
    assert "backblazeb2.com" not in json.dumps(manifest)
    assert audio["assets"]["manifest"] == "/api/reader/book/the-open-window/audiobook/manifest"
    assert audio["package_version"] == book["audiobook_package"]["package_version"]


def test_package_manifest_endpoint_caches_only_projected_metadata_and_head_is_empty(
    monkeypatch,
):
    server = _server(monkeypatch)
    book = _package_book()
    cache = {}
    calls = []

    async def fake_book(_slug):
        return book

    async def fake_cache_get(namespace, key):
        calls.append(("get", namespace, key))
        return copy.deepcopy(cache.get((namespace, key)))

    async def fake_cache_set(namespace, key, value, ttl_seconds):
        calls.append(("set", namespace, key, ttl_seconds))
        cache[(namespace, key)] = copy.deepcopy(value)

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", fake_book)
    monkeypatch.setattr(server, "_redis_cache_get", fake_cache_get)
    monkeypatch.setattr(server, "_redis_cache_set", fake_cache_set)
    get_request = SimpleNamespace(headers={}, method="GET", cookies={})
    get_response = asyncio.run(
        server._reader_book_audiobook_package_manifest_response(
            "the-open-window",
            get_request,
        )
    )

    package_version = book["audiobook_package"]["package_version"]
    cache_key = ("reader-manifest", f"audiobook-package:{package_version}")
    cached = cache[cache_key]
    serialized = json.dumps(cached)
    assert get_response.status_code == 200
    assert json.loads(get_response.body)["package_version"] == package_version
    assert cached["slug"] == "the-open-window"
    assert "storage" not in serialized
    assert "replicas" not in serialized
    assert "backblazeb2.com" not in serialized
    assert server._redis_cache_payload_is_media(cached) is False

    head_request = SimpleNamespace(headers={}, method="HEAD", cookies={})
    head_response = asyncio.run(
        server._reader_book_audiobook_package_manifest_response(
            "the-open-window",
            head_request,
        )
    )
    assert head_response.status_code == 200
    assert head_response.body == b""
    assert int(head_response.headers["content-length"]) == len(get_response.body)
    assert head_response.headers["x-audiobook-package-version"] == package_version
    assert [call[0] for call in calls].count("set") == 1
    assert [call[0] for call in calls].count("get") == 2


def test_reader_manifest_truth_gate_invalidates_pre_package_v2_cache(monkeypatch):
    server = _server(monkeypatch)
    stale_key = (
        "book-manifest:audio-contract-v12:17:public:the-open-window"
    )
    current_key = (
        "book-manifest:audio-contract-v13:17:public:the-open-window"
    )
    cache = {
        ("reader-manifest", stale_key): {
            "audio": {
                "assets": {
                    "mp3": "/api/reader/book/the-open-window/audiobook",
                },
            },
        },
    }
    get_calls = []
    set_calls = []

    async def fake_generation():
        return 17

    async def fake_cache_get(namespace, key):
        get_calls.append((namespace, key))
        return copy.deepcopy(cache.get((namespace, key)))

    async def fake_cache_set(namespace, key, value, ttl_seconds):
        set_calls.append((namespace, key, ttl_seconds))
        cache[(namespace, key)] = copy.deepcopy(value)

    monkeypatch.setattr(
        server,
        "_reader_content_cache_generation_value",
        fake_generation,
    )
    monkeypatch.setattr(server, "_redis_cache_get", fake_cache_get)
    monkeypatch.setattr(server, "_redis_cache_set", fake_cache_set)

    result = asyncio.run(
        server._reader_book_manifest_doc("the-open-window")
    )

    assert result["audio"]["assets"]["manifest"] == (
        "/api/reader/book/the-open-window/audiobook/manifest"
    )
    assert get_calls == [(
        "reader-manifest",
        current_key,
    )]
    assert ("reader-manifest", stale_key) not in get_calls
    assert set_calls == [(
        "reader-manifest",
        current_key,
        server.READER_MANIFEST_CACHE_TTL_SECONDS,
    )]


def test_package_manifest_endpoint_never_reads_cache_before_release_selection(
    monkeypatch,
):
    server = _server(monkeypatch)
    book = _package_book()
    descriptor = book["audiobook_release_descriptor_sha256"]
    book["audiobook_package_release_evidence"][descriptor]["release_eligible"] = False

    async def fake_book(_slug):
        return book

    async def forbidden_cache_get(*_args, **_kwargs):
        raise AssertionError("invalid release selection must not read Redis")

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", fake_book)
    monkeypatch.setattr(server, "_redis_cache_get", forbidden_cache_get)
    request = SimpleNamespace(headers={}, method="GET", cookies={})
    response = asyncio.run(
        server._reader_book_audiobook_package_manifest_response(
            "the-open-window",
            request,
        )
    )

    assert response.status_code == 404
    assert response.headers["cache-control"] == "private, no-store"


def test_package_manifest_requires_release_eligible_runtime_evidence(monkeypatch):
    server = _server(monkeypatch)

    absent = _package_book()
    absent.pop("audiobook_package_release_evidence")
    assert server._reader_audio_package_manifest(absent, "the-open-window") is None

    private_qa = _package_book()
    descriptor = private_qa["audiobook_release_descriptor_sha256"]
    private_qa["audiobook_package_release_evidence"][descriptor][
        "release_eligible"
    ] = False
    assert (
        server._reader_audio_package_manifest(private_qa, "the-open-window")
        is None
    )

    tampered = _package_book()
    tampered["audiobook_package_release_evidence"][descriptor][
        "release_manifest_key"
    ] = "v1/private-qa/release-manifest.json"
    assert server._reader_audio_package_manifest(tampered, "the-open-window") is None


def test_package_manifest_rejects_evidence_store_identity_mismatch(monkeypatch):
    server = _server(monkeypatch)
    book = _package_book()
    descriptor = book["audiobook_release_descriptor_sha256"]
    book["audiobook_package_release_evidence"][descriptor][
        "primary_release_manifest_store"
    ] = "private_audio"

    assert server._reader_audio_package_manifest(book, "the-open-window") is None


def test_package_manifest_rejects_matching_private_qa_store_as_release_eligible(monkeypatch):
    server = _server(monkeypatch)
    from audiobook_packages import with_canonical_package_version

    book = _package_book()
    descriptor = book["audiobook_release_descriptor_sha256"]
    package = book["audiobook_package"]
    for track in package["tracks"]:
        for chunk in track["chunks"]:
            for asset in chunk["assets"].values():
                asset["storage"]["store"] = "private_audio"
                asset["storage"]["bucket"] = "earnalism-private-qa-audio"
    package = with_canonical_package_version(package)
    book["audiobook_package"] = package
    evidence = book["audiobook_package_release_evidence"][descriptor]
    evidence["package_version"] = package["package_version"]
    evidence["primary_release_manifest_store"] = "private_audio"

    assert server._reader_audio_package_manifest(book, "the-open-window") is None


def test_package_manifest_fails_closed_for_incomplete_or_noncontiguous_segments(monkeypatch):
    server = _server(monkeypatch)
    book = _package_book()
    book["audiobook_package"]["tracks"][0]["chunks"][1]["start_word"] = 101

    assert server._validated_audiobook_package(book, "the-open-window") is None
    assert server._reader_audio_package_manifest(book, "the-open-window") is None


def test_package_manifest_requires_exact_source_binding_and_contiguous_duration(monkeypatch):
    server = _server(monkeypatch)
    source_mismatch = _package_book()
    source_mismatch["audiobook_package"]["source_sha256"] = "0" * 64
    duration_mismatch = _package_book()
    duration_mismatch["audiobook_package"]["duration_ms"] += 1
    oversized_segment = _package_book()
    oversized_segment["audiobook_package"]["tracks"][0]["chunks"][0]["duration_ms"] = 720_001
    oversized_segment["audiobook_package"]["tracks"][0]["chunks"][1]["cumulative_start_ms"] = 720_001
    oversized_segment["audiobook_package"]["duration_ms"] = 1_040_001

    assert server._validated_audiobook_package(source_mismatch, "the-open-window") is None
    assert server._validated_audiobook_package(duration_mismatch, "the-open-window") is None
    assert server._validated_audiobook_package(oversized_segment, "the-open-window") is None


def test_hidden_audio_never_projects_package_manifest(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: False)

    audio = server._reader_manifest_audio(_package_book(), "the-open-window")

    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["package_version"] == ""


def test_package_segment_resolves_exact_current_version_and_segment(monkeypatch):
    server = _server(monkeypatch)
    book = _package_book()
    package_version = book["audiobook_package"]["package_version"]
    captured = {}

    async def fake_book(_slug):
        return book

    async def fake_stream(
        slug,
        asset_key,
        asset_url,
        request,
        *,
        extra_headers=None,
        version_id="",
    ):
        captured.update({
            "slug": slug,
            "asset_key": asset_key,
            "asset_url": asset_url,
            "request": request,
            "extra_headers": extra_headers,
            "version_id": version_id,
        })
        return "STREAMED"

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", fake_book)
    monkeypatch.setattr(server, "_stream_audiobook_asset_url", fake_stream)
    monkeypatch.setattr(
        server,
        "_audio_package_storage_url",
        lambda storage: f"https://private.test/{storage['bucket']}/{storage['key']}",
    )
    request = SimpleNamespace(headers={"range": "bytes=0-3"}, method="GET", cookies={})

    response = asyncio.run(
        server._reader_book_audiobook_package_segment(
            "the-open-window",
            package_version,
            "c001-s002",
            "mp3",
            request,
        )
    )

    assert response == "STREAMED"
    assert captured["slug"] == "the-open-window"
    assert captured["asset_key"] == "mp3"
    assert captured["asset_url"].endswith("/c001-s002.audio")
    assert captured["extra_headers"] == {"X-Audiobook-Package-Version": package_version}
    assert captured["version_id"] == "primary-c001-s002-audio"


def test_finalized_prod_receipt_resolves_and_streams_exact_versioned_range(monkeypatch):
    server = _server(monkeypatch)
    book = _package_book()
    package = book["audiobook_package"]
    package_version = package["package_version"]
    audio_asset = package["tracks"][0]["chunks"][1]["assets"]["audio"]
    endpoint = "https://s3.us-west-004.backblazeb2.com"

    monkeypatch.setattr(server, "B2_AUDIOBOOK_PROD_S3_ENDPOINT", endpoint)
    monkeypatch.setattr(server, "B2_AUDIOBOOK_PROD_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_AUDIOBOOK_PROD_BUCKET", "earnalism-audio-prod")
    monkeypatch.setattr(server, "B2_AUDIOBOOK_PROD_READ_ACCESS_KEY_ID", "runtime-read-key")
    monkeypatch.setattr(server, "B2_AUDIOBOOK_PROD_READ_SECRET_ACCESS_KEY", "runtime-read-secret")

    async def fake_book(_slug):
        return book

    class FakeBody:
        def __init__(self):
            self.remaining = b"test"

        def read(self, _size=-1):
            payload, self.remaining = self.remaining, b""
            return payload

        def close(self):
            return None

    class FakeS3:
        def __init__(self):
            self.calls = []

        def get_object(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "ContentLength": 4,
                "ContentRange": f"bytes 0-3/{audio_asset['size_bytes']}",
                "ContentType": "audio/mpeg",
                "ETag": '"immutable-etag"',
                "Body": FakeBody(),
            }

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "_reader_audio_book_for_slug", fake_book)
    monkeypatch.setattr(server, "_b2_client", lambda storage=None: fake_s3)
    request = SimpleNamespace(
        headers={"range": "bytes=0-3"},
        method="GET",
        cookies={},
    )

    runtime_store = next(
        store for store in server._b2_storage_configs()
        if store["name"] == "prod"
    )
    resolved_url = server._audio_package_storage_url(audio_asset["storage"])
    response = asyncio.run(
        server._reader_book_audiobook_package_segment(
            "the-open-window",
            package_version,
            "c001-s002",
            "mp3",
            request,
        )
    )

    assert runtime_store["access_key_id"] == "runtime-read-key"
    assert runtime_store["secret_access_key"] == "runtime-read-secret"
    assert resolved_url == (
        f"{endpoint}/earnalism-audio-prod/{audio_asset['storage']['key']}"
    )
    assert response.status_code == 206
    assert response.headers["content-range"] == (
        f"bytes 0-3/{audio_asset['size_bytes']}"
    )
    assert response.headers["x-audiobook-package-version"] == package_version
    assert fake_s3.calls == [{
        "Bucket": "earnalism-audio-prod",
        "Key": audio_asset["storage"]["key"],
        "Range": "bytes=0-3",
        "VersionId": audio_asset["storage"]["version_id"],
    }]


def test_package_segment_rejects_stale_version_and_unknown_segment(monkeypatch):
    server = _server(monkeypatch)
    book = _package_book()

    async def fake_book(_slug):
        return book

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", fake_book)
    request = SimpleNamespace(headers={}, method="GET")

    for version, segment_id in (
        (f"sha256-{'0' * 64}", "c001-s001"),
        (book["audiobook_package"]["package_version"], "c999-s999"),
    ):
        try:
            asyncio.run(
                server._reader_book_audiobook_package_segment(
                    "the-open-window",
                    version,
                    segment_id,
                    "mp3",
                    request,
                )
            )
        except server.HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("Stale or unknown package segments must fail closed")


def test_package_rollout_selects_sticky_5_25_100_and_rollback(monkeypatch):
    server = _server(monkeypatch)
    from audiobook_packages import (
        ACTIVE_RELEASE_SCHEMA_VERSION,
        deterministic_rollout_bucket,
    )

    book = _package_book()
    candidate = book.pop("audiobook_package")
    candidate_descriptor = candidate["release_descriptor_sha256"]
    legacy_descriptor = "9" * 64
    salt = "package-v2-canary-v1"
    book["audiobook_packages"] = {candidate_descriptor: candidate}
    book["audiobook_active_release"] = {
        "schema_version": ACTIVE_RELEASE_SCHEMA_VERSION,
        "slug": "the-open-window",
        "status": "ACTIVE",
        "active_release_descriptor_sha256": legacy_descriptor,
        "candidate_release_descriptor_sha256": candidate_descriptor,
        "retained_release_descriptor_sha256s": [
            legacy_descriptor,
            candidate_descriptor,
        ],
        "rollout": {"percentage": 5, "salt": salt},
    }

    candidate_key = next(
        f"reader-{index:024d}"
        for index in range(1000)
        if deterministic_rollout_bucket(
            slug="the-open-window",
            sticky_key=f"reader-{index:024d}",
            salt=salt,
        )
        < 5
    )
    legacy_key = next(
        f"reader-{index:024d}"
        for index in range(1000)
        if deterministic_rollout_bucket(
            slug="the-open-window",
            sticky_key=f"reader-{index:024d}",
            salt=salt,
        )
        >= 25
    )

    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={server.AUDIOBOOK_ROLLOUT_COOKIE: candidate_key}),
    )
    assert selected["package_version"] == candidate["package_version"]
    assert descriptor == candidate_descriptor

    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={server.AUDIOBOOK_ROLLOUT_COOKIE: legacy_key}),
    )
    assert selected is None
    assert descriptor == legacy_descriptor

    book["audiobook_active_release"]["rollout"]["percentage"] = 25
    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={server.AUDIOBOOK_ROLLOUT_COOKIE: legacy_key}),
    )
    assert selected is None
    assert descriptor == legacy_descriptor

    book["audiobook_active_release"]["rollout"]["percentage"] = 100
    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={}),
    )
    assert selected["package_version"] == candidate["package_version"]
    assert descriptor == candidate_descriptor

    # Rollback is a pointer-only mutation: zeroing the candidate rollout makes
    # the immutable candidate inaccessible while legacy audio remains active.
    book["audiobook_active_release"]["rollout"]["percentage"] = 0
    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={server.AUDIOBOOK_ROLLOUT_COOKIE: candidate_key}),
    )
    assert selected is None
    assert descriptor == legacy_descriptor

    book["audiobook_active_release"]["status"] = "INACTIVE"
    selected, descriptor, _new = server._selected_audiobook_package(
        book,
        "the-open-window",
        SimpleNamespace(cookies={server.AUDIOBOOK_ROLLOUT_COOKIE: candidate_key}),
    )
    assert selected is None
    assert descriptor == ""


def test_b2_key_and_range_helpers(monkeypatch):
    server = _server(monkeypatch)
    server.B2_S3_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
    server.B2_REGION = "us-west-004"
    server.B2_BUCKET = "earnalism-audio"
    server.B2_ACCESS_KEY_ID = "test-key"
    server.B2_SECRET_ACCESS_KEY = "test-secret"

    key = server._b2_key_from_url(
        "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3"
    )
    byte_range, status = server._parse_byte_range("bytes=100-199", 1000)

    assert key == "earnalism/audiobooks/en/dracula/dracula.mp3"
    assert byte_range == "bytes=100-199"
    assert status == 206
    assert server._content_range_header(byte_range, 1000) == "bytes 100-199/1000"
    assert server._range_content_length(byte_range, 1000) == 100


def test_private_audio_store_is_proxied_without_changing_primary_b2(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "earnalism-private-qa-audio")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "private-key")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "private-secret")
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
        "audiobook": {
            "url": private_url,
            "provider": "kokoro",
            "ai_narration_disclosure": "Narration: AI voice",
        },
    }

    storage = server._b2_storage_for_url(private_url)
    audio = server._reader_manifest_audio(book, "the-open-window")

    assert storage is not None
    assert storage["name"] == "private_audio"
    assert storage["bucket"] == "earnalism-private-qa-audio"
    assert server._b2_key_from_url(private_url, storage) == (
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    assert audio["assets"]["mp3"] == "/api/reader/book/the-open-window/audiobook"
    assert audio["url"] == "/api/reader/book/the-open-window/audiobook"
    assert audio["narration_disclosure"] == "Narration: AI voice"


def test_private_audio_endpoint_reads_the_selected_private_bucket(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "earnalism-private-qa-audio")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "private-key")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "private-secret")
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "slug": "the-open-window",
        "is_published": True,
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
        "audiobook": {"url": private_url, "provider": "kokoro"},
    }

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return book

    class FakeBody:
        def __init__(self):
            self._remaining = b"test"

        def read(self, _size=-1):
            payload, self._remaining = self._remaining, b""
            return payload

        def close(self):
            return None

    class FakeS3:
        def __init__(self):
            self.calls = []

        def get_object(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "ContentLength": 4,
                "ContentRange": "bytes 0-3/6283053",
                "ContentType": "audio/mpeg",
                "Body": FakeBody(),
            }

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda slug: slug == "the-open-window")
    monkeypatch.setattr(server, "_reader_audio_truth_doc", lambda value, _slug: value)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)
    monkeypatch.setattr(server, "_b2_client", lambda storage=None: fake_s3)
    request = SimpleNamespace(headers={"range": "bytes=0-3"}, method="GET")

    response = asyncio.run(server._reader_book_audiobook_asset("the-open-window", "mp3", request))

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/6283053"
    assert fake_s3.calls == [
        {
            "Bucket": "earnalism-private-qa-audio",
            "Key": "earnalism/audiobooks/the-open-window/the-open-window.mp3",
            "Range": "bytes=0-3",
        }
    ]


def test_unconfigured_backblaze_url_keeps_legacy_manifest_proxy_shape_but_has_no_store(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "B2_S3_ENDPOINT", "")
    monkeypatch.setattr(server, "B2_REGION", "")
    monkeypatch.setattr(server, "B2_BUCKET", "")
    monkeypatch.setattr(server, "B2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(server, "B2_SECRET_ACCESS_KEY", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "")

    url = "https://s3.us-west-004.backblazeb2.com/unconfigured-bucket/book.mp3"
    assert server._audio_asset_looks_like_b2(url) is True
    assert server._b2_storage_for_url(url) is None


def test_controlled_unconfigured_backblaze_asset_fails_closed_instead_of_redirecting(monkeypatch):
    server = _server(monkeypatch)
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "slug": "the-open-window",
        "is_published": True,
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
    }

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return book

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda slug: slug == "the-open-window")
    monkeypatch.setattr(server, "_reader_audio_truth_doc", lambda value, _slug: value)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)
    monkeypatch.setattr(server, "_b2_storage_configs", lambda: [])
    request = SimpleNamespace(headers={}, method="GET")

    try:
        asyncio.run(server._reader_book_audiobook_asset("the-open-window", "mp3", request))
    except server.HTTPException as exc:
        assert exc.status_code == 503
        assert "not configured" in str(exc.detail).lower()
    else:
        raise AssertionError("Unmatched private Backblaze asset must fail closed")


def test_audio_asset_cache_policy_keeps_audio_browser_hot(monkeypatch):
    server = _server(monkeypatch)

    assert "max-age=600" in server._audio_asset_cache_control("mp3")
    assert "stale-while-revalidate=3600" in server._audio_asset_cache_control("mp3")
    assert "max-age=3600" in server._audio_asset_cache_control("timestamps")
    assert server._audio_asset_content_type("timestamps", "application/octet-stream") == "application/json"
    assert server._audio_asset_content_type("vtt", "application/octet-stream") == "text/vtt"


def test_b2_wrappers_preserve_kwargs_while_running_off_event_loop(monkeypatch):
    server = _server(monkeypatch)

    class FakeS3:
        def __init__(self):
            self.calls = []

        def head_object(self, **kwargs):
            self.calls.append(("head", kwargs))
            return {"ContentLength": 10}

        def get_object(self, **kwargs):
            self.calls.append(("get", kwargs))
            return {"ContentLength": 4, "Body": object()}

    fake = FakeS3()

    head = asyncio.run(server._b2_head_object(fake, bucket="bucket", key="book.mp3"))
    obj = asyncio.run(server._b2_get_object(fake, bucket="bucket", key="book.mp3", byte_range="bytes=0-3"))

    assert head["ContentLength"] == 10
    assert obj["ContentLength"] == 4
    assert fake.calls == [
        ("head", {"Bucket": "bucket", "Key": "book.mp3"}),
        ("get", {"Bucket": "bucket", "Key": "book.mp3", "Range": "bytes=0-3"}),
    ]


def test_b2_wrappers_bind_reads_to_exact_version_id(monkeypatch):
    server = _server(monkeypatch)

    class FakeS3:
        def __init__(self):
            self.calls = []

        def head_object(self, **kwargs):
            self.calls.append(("head", kwargs))
            return {"ContentLength": 10}

        def get_object(self, **kwargs):
            self.calls.append(("get", kwargs))
            return {"ContentLength": 4, "Body": object()}

    fake = FakeS3()
    asyncio.run(
        server._b2_head_object(
            fake,
            bucket="bucket",
            key="book.mp3",
            version_id="v-immutable",
        )
    )
    asyncio.run(
        server._b2_get_object(
            fake,
            bucket="bucket",
            key="book.mp3",
            byte_range="bytes=0-3",
            version_id="v-immutable",
        )
    )

    assert fake.calls == [
        (
            "head",
            {
                "Bucket": "bucket",
                "Key": "book.mp3",
                "VersionId": "v-immutable",
            },
        ),
        (
            "get",
            {
                "Bucket": "bucket",
                "Key": "book.mp3",
                "Range": "bytes=0-3",
                "VersionId": "v-immutable",
            },
        ),
    ]


def test_direct_range_request_fails_closed_when_storage_ignores_range(monkeypatch):
    server = _server(monkeypatch)
    storage = {
        "name": "audiobook_prod",
        "endpoint": "https://s3.us-west-004.backblazeb2.com",
        "region": "us-west-004",
        "bucket": "private-prod",
        "access_key_id": "key",
        "secret_access_key": "secret",
    }

    class FakeBody:
        closed = False

        def close(self):
            self.closed = True

    body = FakeBody()

    class FakeS3:
        def head_object(self, **_kwargs):
            return {
                "ContentLength": 1000,
                "ContentType": "audio/mpeg",
            }

        def get_object(self, **_kwargs):
            return {
                "ContentLength": 1000,
                "ContentType": "audio/mpeg",
                "Body": body,
            }

    monkeypatch.setattr(server, "_b2_storage_for_url", lambda _url: storage)
    monkeypatch.setattr(server, "_b2_key_from_url", lambda _url, _storage: "v1/prod/book.mp3")
    monkeypatch.setattr(server, "_b2_client", lambda _storage=None: FakeS3())
    request = SimpleNamespace(headers={"range": "bytes=0-3"}, method="GET")

    try:
        asyncio.run(
            server._stream_audiobook_asset_url(
                "the-open-window",
                "mp3",
                "https://s3.us-west-004.backblazeb2.com/private-prod/v1/prod/book.mp3",
                request,
            )
        )
    except server.HTTPException as exc:
        assert exc.status_code == 502
        assert "byte range" in str(exc.detail).lower()
    else:
        raise AssertionError("A requested Range must never degrade to a full 200 response")

    assert body.closed is True


def test_invalid_range_returns_416_without_fetching_object_body(monkeypatch):
    server = _server(monkeypatch)
    storage = {
        "name": "audiobook_prod",
        "endpoint": "https://s3.us-west-004.backblazeb2.com",
        "region": "us-west-004",
        "bucket": "private-prod",
        "access_key_id": "key",
        "secret_access_key": "secret",
    }

    class FakeS3:
        def __init__(self):
            self.get_called = False

        def head_object(self, **_kwargs):
            return {
                "ContentLength": 1000,
                "ContentType": "audio/mpeg",
            }

        def get_object(self, **_kwargs):
            self.get_called = True
            error = RuntimeError("Requested range not satisfiable")
            error.response = {"ResponseMetadata": {"HTTPStatusCode": 416}}
            raise error

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "_b2_storage_for_url", lambda _url: storage)
    monkeypatch.setattr(server, "_b2_key_from_url", lambda _url, _storage: "v1/prod/book.mp3")
    monkeypatch.setattr(server, "_b2_client", lambda _storage=None: fake_s3)
    request = SimpleNamespace(headers={"range": "bytes=1000-1001"}, method="GET")

    response = asyncio.run(
        server._stream_audiobook_asset_url(
            "the-open-window",
            "mp3",
            "https://s3.us-west-004.backblazeb2.com/private-prod/v1/prod/book.mp3",
            request,
        )
    )

    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */1000"
    assert fake_s3.get_called is True


def test_malformed_range_returns_416_without_fetching_object_body(monkeypatch):
    server = _server(monkeypatch)
    storage = {
        "name": "audiobook_prod",
        "endpoint": "https://s3.us-west-004.backblazeb2.com",
        "region": "us-west-004",
        "bucket": "private-prod",
        "access_key_id": "key",
        "secret_access_key": "secret",
    }

    class FakeS3:
        def __init__(self):
            self.get_called = False

        def head_object(self, **_kwargs):
            return {
                "ContentLength": 1000,
                "ContentType": "audio/mpeg",
            }

        def get_object(self, **_kwargs):
            self.get_called = True
            raise AssertionError("malformed ranges must not fetch object bytes")

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "_b2_storage_for_url", lambda _url: storage)
    monkeypatch.setattr(server, "_b2_key_from_url", lambda _url, _storage: "v1/prod/book.mp3")
    monkeypatch.setattr(server, "_b2_client", lambda _storage=None: fake_s3)
    request = SimpleNamespace(headers={"range": "bytes=not-a-range"}, method="GET")

    response = asyncio.run(
        server._stream_audiobook_asset_url(
            "the-open-window",
            "mp3",
            "https://s3.us-west-004.backblazeb2.com/private-prod/v1/prod/book.mp3",
            request,
        )
    )

    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */1000"
    assert fake_s3.get_called is False


def test_open_window_controlled_release_exposes_only_proxy_assets_with_disclosure(monkeypatch):
    server = _server(monkeypatch)
    artifact = server.load_controlled_artifact_book("the-open-window")

    assert artifact is not None
    assert server.can_expose_audio({**artifact, "slug": "the-open-window"}) is True
    audio = server._reader_manifest_audio(artifact, "the-open-window")

    assert audio["enabled"] is True
    assert audio["provider"] == "kokoro"
    assert audio["voice"] == "af_bella"
    assert audio["release_gate"] == "APPROVED"
    assert audio["qa_status"] == "QA_PASSED"
    assert audio["sync_mode"] == "section_following"
    assert audio["highlight_sync_enabled"] is False
    assert audio["narration_disclosure"] == "Narration: AI voice"
    assert audio["size"] == 6283053
    assert audio["duration_ms"] == 392600
    assert audio["assets"] == {
        "mp3": "/api/reader/book/the-open-window/audiobook",
        "timestamps": "/api/reader/book/the-open-window/audiobook/timestamps",
        "vtt": "/api/reader/book/the-open-window/audiobook/vtt",
        "chapters": "/api/reader/book/the-open-window/audiobook/chapters",
        "meta": "/api/reader/book/the-open-window/audiobook/meta",
        "manifest": "/api/reader/book/the-open-window/audiobook/manifest",
    }


def test_admin_audiobook_asset_sanitizer_rejects_static_audio_fallbacks(monkeypatch):
    server = _server(monkeypatch)

    assets = server._safe_audiobook_assets(
        {
            "mp3": "/audio/the-open-window.mp3",
            "timestamps": "/audio/the-open-window.json",
            "meta": "https://private.example.invalid/the-open-window.json",
        }
    )

    assert assets == {
        "meta": "https://private.example.invalid/the-open-window.json",
    }
