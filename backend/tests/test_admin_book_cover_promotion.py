from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import shutil
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "admin-cover-promotion-test-secret")

from backend import server
from backend.config import book_cover_promotion
from backend.config.book_cover_promotion import (
    APPROVAL_DECISION,
    CoverPromotionError,
    promote_cover_candidate,
    validate_immutable_candidate,
)
from backend.config.book_cover import (
    content_addressed_cover_candidate_asset_id,
    content_addressed_cover_candidate_public_id,
)


ROOT = Path(__file__).resolve().parents[2]
SLUG = "jekyll-and-hyde"


def image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1200, 1800), "#6B1020").save(buffer, format="PNG")
    return buffer.getvalue()


def candidate(body: bytes | None = None) -> dict:
    body = body or image_bytes()
    digest = hashlib.sha256(body).hexdigest()
    public_id = content_addressed_cover_candidate_public_id(
        SLUG,
        "front",
        digest,
    )
    return {
        "slug": SLUG,
        "kind": "front",
        "candidate_url": (
            "https://res.cloudinary.com/demo/image/upload/v1785384000/"
            f"{public_id}.png"
        ),
        "immutable_candidate_url": (
            "https://res.cloudinary.com/demo/image/upload/v1785384000/"
            f"{public_id}.png"
        ),
        "candidate_thumbnail_url": (
            "https://res.cloudinary.com/demo/image/upload/w_300/"
            "earnalism/covers/front/candidate_controlled-jekyll-and-hyde.png"
        ),
        "candidate_blur_placeholder": (
            "https://res.cloudinary.com/demo/image/upload/e_blur/"
            "earnalism/covers/front/candidate_controlled-jekyll-and-hyde.png"
        ),
        "candidate_dominant_color": "#6B1020",
        "cloudinary_public_id": public_id,
        "cloudinary_version": "1785384000",
        "cloudinary_version_id": "immutable-version-id",
        "cloudinary_resource_type": "image",
        "cloudinary_format": "png",
        "width": 1200,
        "height": 1800,
        "sha256": digest,
        "audit_status": "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW",
    }


def controlled_repo(tmp_path: Path) -> Path:
    source = ROOT / "data" / "controlled_publications" / SLUG
    for relative in (
        Path("data/controlled_publications") / SLUG,
        Path("backend/data/controlled_publications") / SLUG,
    ):
        shutil.copytree(source, tmp_path / relative)
    return tmp_path


def publication_files(repo_root: Path) -> dict[str, bytes]:
    result = {}
    for prefix in ("data", "backend/data"):
        directory = repo_root / prefix / "controlled_publications" / SLUG
        for path in directory.rglob("*"):
            if path.is_file():
                result[f"{prefix}/{path.relative_to(directory).as_posix()}"] = (
                    path.read_bytes()
                )
    return result


def audio_truth(payload: dict) -> dict:
    return {
        key: copy.deepcopy(payload.get(key))
        for key in book_cover_promotion.AUDIO_TRUTH_FIELDS
    }


def promote(repo_root: Path, *, body: bytes | None = None, **overrides):
    body = body or image_bytes()
    values = {
        "repo_root": repo_root,
        "slug": SLUG,
        "kind": "front",
        "candidate": candidate(body),
        "remote_bytes": body,
        "expected_candidate_sha256": hashlib.sha256(body).hexdigest(),
        "approval_decision": APPROVAL_DECISION,
        "editorial_approved": True,
        "rights_cleared": True,
        "approval_note": "Owner approved the exact reviewed front cover candidate.",
        "rights_basis": "Public-domain source art and original Earnalism layout cleared.",
        "event_id": "cover-event-001",
        "approved_at": "2026-07-30T12:00:00+00:00",
        "approved_by": "owner@example.com",
        "max_bytes": 4 * 1024 * 1024,
    }
    values.update(overrides)
    return promote_cover_candidate(**values)


def test_immutable_candidate_requires_version_bound_cloudinary_identity():
    valid = candidate()
    identity = validate_immutable_candidate(valid)
    assert identity["version"] == "1785384000"
    assert identity["public_id"].endswith(valid["sha256"])

    unversioned = {**valid, "immutable_candidate_url": valid["candidate_url"].replace(
        "/v1785384000", ""
    )}
    with pytest.raises(CoverPromotionError, match="immutable Cloudinary identity"):
        validate_immutable_candidate(unversioned)

    missing_version_id = {**valid, "cloudinary_version_id": ""}
    with pytest.raises(CoverPromotionError, match="immutable Cloudinary identity"):
        validate_immutable_candidate(missing_version_id)

    cross_title = {
        **valid,
        "cloudinary_public_id": (
            "earnalism/covers/front/cover_candidate_controlled-dracula"
        ),
    }
    with pytest.raises(CoverPromotionError, match="not title/side/content scoped"):
        validate_immutable_candidate(cross_title)


def test_promotion_updates_both_mirrors_checksums_and_approval_history_only(tmp_path):
    repo_root = controlled_repo(tmp_path)
    primary = repo_root / "data/controlled_publications" / SLUG
    before_public = json.loads((primary / "public_book.json").read_text())
    before_reader_bytes = (primary / "reader_manifest.json").read_bytes()
    before_audio = audio_truth(before_public)

    result = promote(repo_root)

    assert result["reader_audio_release_truth_unchanged"] is True
    assert result["candidate_sha256"] == hashlib.sha256(image_bytes()).hexdigest()
    primary_files = publication_files(repo_root)
    for relative, payload in primary_files.items():
        mirror_relative = (
            relative.replace("data/", "backend/data/", 1)
            if relative.startswith("data/")
            else relative.replace("backend/data/", "data/", 1)
        )
        assert primary_files[mirror_relative] == payload

    public_book = json.loads((primary / "public_book.json").read_text())
    assert public_book["cover_url"] == candidate()["immutable_candidate_url"]
    assert public_book["cover_image_url"] == candidate()["immutable_candidate_url"]
    assert "/v1785384000/" in public_book["thumbnail_url"]
    assert "/v1785384000/" in public_book["blur_placeholder"]
    assert public_book["cover_status"] == "CLOUDINARY_ASSIGNED"
    assert public_book["cover_dimensions"]["front"] == [1200, 1800]
    assert audio_truth(public_book) == before_audio
    assert (primary / "reader_manifest.json").read_bytes() == before_reader_bytes

    evidence = json.loads(
        (primary / "cover_approval_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["active_approvals"]["front"] == "cover-event-001"
    assert evidence["history"][0]["decision"] == APPROVAL_DECISION
    assert evidence["history"][0]["candidate_sha256"] == result["candidate_sha256"]
    assert evidence["rollback_pointers"]["front"]["from_event_id"] == "cover-event-001"
    assert (
        evidence["rollback_pointers"]["front"]["previous_canonical_cover"]["cover_status"]
        == before_public["cover_status"]
    )

    checksum = json.loads((primary / "checksum_manifest.json").read_text())
    rows = {row["file"]: row["sha256"] for row in checksum["files"]}
    assert rows["public_book.json"] == hashlib.sha256(
        (primary / "public_book.json").read_bytes()
    ).hexdigest()
    assert rows["cover_approval_evidence.json"] == hashlib.sha256(
        (primary / "cover_approval_evidence.json").read_bytes()
    ).hexdigest()


def test_upload_after_promotion_cannot_overwrite_promoted_content_addressed_url(
    tmp_path,
    monkeypatch,
):
    repo_root = controlled_repo(tmp_path)
    primary = repo_root / "data/controlled_publications" / SLUG
    first_body = image_bytes()
    first_candidate = candidate(first_body)

    promote(repo_root, body=first_body, candidate=first_candidate)
    promoted_url = json.loads((primary / "public_book.json").read_text())[
        "cover_url"
    ]

    second = BytesIO()
    Image.new("RGB", (1200, 1800), "#161616").save(second, format="PNG")
    second_body = second.getvalue()
    second_candidate = candidate(second_body)
    second_identity = validate_immutable_candidate(second_candidate)

    class Upload:
        filename = "later-front.png"
        content_type = "image/png"

        async def read(self):
            return second_body

    class Candidates:
        document = {}

        async def update_one(self, query, update, *, upsert=False):
            assert upsert is True
            self.document = {"_id": query["_id"], **copy.deepcopy(update["$set"])}
            return SimpleNamespace(matched_count=0, modified_count=0)

    class Audit:
        async def insert_one(self, document):
            return SimpleNamespace(inserted_id=document["id"])

    async def uploaded_book(_slug):
        return (
            {
                "id": f"controlled-{SLUG}",
                "slug": SLUG,
                "title": "The Strange Case of Dr. Jekyll and Mr. Hyde",
                "author": "Robert Louis Stevenson",
            },
            "controlled_publication",
        )

    expected_asset_id = content_addressed_cover_candidate_asset_id(
        SLUG,
        second_candidate["sha256"],
    )

    def process_later_candidate(body, asset_id, *, kind):
        assert body == second_body
        assert asset_id == expected_asset_id
        assert kind == "front"
        return {
            "cover_url": second_candidate["immutable_candidate_url"],
            "thumbnail_url": second_candidate["candidate_thumbnail_url"],
            "blur_placeholder": second_candidate["candidate_blur_placeholder"],
            "dominant_color": second_candidate["candidate_dominant_color"],
            "srcset": "",
            "cloudinary_public_id": second_identity["public_id"],
            "cloudinary_version": second_identity["version"],
            "cloudinary_version_id": second_identity["version_id"],
            "cloudinary_resource_type": second_identity["resource_type"],
            "cloudinary_format": second_identity["format"],
            "cloudinary_bytes": len(second_body),
        }

    candidates = Candidates()
    monkeypatch.setattr(server, "ENABLE_ADMIN_COVER_UPLOADS", True)
    monkeypatch.setattr(server, "_load_cover_upload_source_or_404", uploaded_book)
    monkeypatch.setattr(server, "_ensure_cloudinary", lambda: None)
    monkeypatch.setattr(
        server,
        "_process_book_cover_candidate",
        process_later_candidate,
    )
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            book_cover_candidates=candidates,
            admin_upload_audit=Audit(),
        ),
    )

    response = asyncio.run(
        server.admin_upload_cover(
            slug=SLUG,
            kind="front",
            confirm_expensive_job=True,
            file=Upload(),
            admin={"sub": "owner-1", "email": "owner@example.com"},
        )
    )

    assert second_candidate["sha256"] != first_candidate["sha256"]
    assert (
        second_identity["public_id"]
        != validate_immutable_candidate(first_candidate)["public_id"]
    )
    assert response["cover_url"] == second_candidate["immutable_candidate_url"]
    assert candidates.document["cloudinary_public_id"] == second_identity["public_id"]
    assert (
        json.loads((primary / "public_book.json").read_text())["cover_url"]
        == promoted_url
    )
    assert promoted_url == first_candidate["immutable_candidate_url"]
    assert promoted_url != second_candidate["immutable_candidate_url"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"approval_decision": "REVIEW_ONLY"}, "Explicit canonical-cover approval"),
        ({"editorial_approved": False}, "Editorial and cover-rights approval"),
        ({"rights_cleared": False}, "Editorial and cover-rights approval"),
        ({"expected_candidate_sha256": "0" * 64}, "current candidate SHA-256"),
    ],
)
def test_missing_or_stale_approval_fails_without_mutating_catalog(
    tmp_path, overrides, message
):
    repo_root = controlled_repo(tmp_path)
    before = publication_files(repo_root)

    with pytest.raises(CoverPromotionError, match=message):
        promote(repo_root, **overrides)

    assert publication_files(repo_root) == before


def test_remote_byte_mismatch_fails_before_catalog_mutation(tmp_path):
    repo_root = controlled_repo(tmp_path)
    before = publication_files(repo_root)
    reviewed_body = image_bytes()
    different = BytesIO()
    Image.new("RGB", (1200, 1800), "#161616").save(different, format="PNG")

    with pytest.raises(CoverPromotionError, match="do not match candidate input"):
        promote(
            repo_root,
            body=different.getvalue(),
            candidate=candidate(reviewed_body),
            expected_candidate_sha256=hashlib.sha256(reviewed_body).hexdigest(),
        )

    assert publication_files(repo_root) == before


def test_divergent_controlled_mirrors_fail_closed(tmp_path):
    repo_root = controlled_repo(tmp_path)
    backend_public = (
        repo_root
        / "backend/data/controlled_publications"
        / SLUG
        / "public_book.json"
    )
    backend_public.write_bytes(backend_public.read_bytes() + b" ")
    before = publication_files(repo_root)

    with pytest.raises(CoverPromotionError, match="mirrors diverge"):
        promote(repo_root)

    assert publication_files(repo_root) == before


def test_partial_replace_failure_rolls_back_both_mirrors(tmp_path, monkeypatch):
    repo_root = controlled_repo(tmp_path)
    before = publication_files(repo_root)
    real_replace = book_cover_promotion.os.replace
    failed = False

    def fail_once(source, destination):
        nonlocal failed
        if (
            not failed
            and "backend/data/controlled_publications" in str(destination)
            and str(destination).endswith("public_book.json")
        ):
            failed = True
            raise OSError("simulated mirror write failure")
        return real_replace(source, destination)

    monkeypatch.setattr(book_cover_promotion.os, "replace", fail_once)

    with pytest.raises(CoverPromotionError, match="rolled back"):
        promote(repo_root)

    assert failed is True
    assert publication_files(repo_root) == before


def test_promotion_route_is_authenticated_and_disabled_by_default():
    client = TestClient(server.app)
    response = client.post(
        f"/api/admin/books/{SLUG}/cover/promote",
        json={
            "kind": "front",
            "candidate_sha256": "a" * 64,
            "approval_decision": APPROVAL_DECISION,
            "editorial_approved": True,
            "rights_cleared": True,
            "approval_note": "Owner approved the reviewed candidate.",
            "rights_basis": "Rights evidence was reviewed and accepted.",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def promotion_payload(sha256: str | None = None) -> server.CoverPromotionIn:
    return server.CoverPromotionIn(
        kind="front",
        candidate_sha256=sha256 or hashlib.sha256(image_bytes()).hexdigest(),
        approval_decision=APPROVAL_DECISION,
        editorial_approved=True,
        rights_cleared=True,
        approval_note="Owner approved the reviewed candidate.",
        rights_basis="Rights evidence was reviewed and accepted.",
    )


def nested_value(document: dict, dotted_key: str):
    current = document
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


class CasCandidates:
    def __init__(
        self,
        document: dict,
        *,
        fail_finalize: bool = False,
        fail_revert: bool = False,
    ):
        self.document = copy.deepcopy(document)
        self.fail_finalize = fail_finalize
        self.fail_revert = fail_revert
        self.calls = []

    async def find_one(self, query, _projection=None):
        if all(nested_value(self.document, key) == value for key, value in query.items()):
            return copy.deepcopy(self.document)
        return None

    async def update_one(self, query, update, **_kwargs):
        self.calls.append((copy.deepcopy(query), copy.deepcopy(update)))
        matches = all(
            nested_value(self.document, key) == value for key, value in query.items()
        )
        is_finalize = (
            update.get("$set", {}).get("audit_status") == "CANONICAL_PROMOTED"
        )
        is_revert = (
            update.get("$set", {}).get("audit_status")
            == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
        )
        if matches and is_finalize and self.fail_finalize:
            self.document["audit_status"] = "RACING_OPERATOR_MUTATION"
            return SimpleNamespace(matched_count=0, modified_count=0)
        if matches and is_revert and self.fail_revert:
            self.document["audit_status"] = "RACING_OPERATOR_MUTATION"
            return SimpleNamespace(matched_count=0, modified_count=0)
        if not matches:
            return SimpleNamespace(matched_count=0, modified_count=0)
        for key, value in update.get("$set", {}).items():
            self.document[key] = copy.deepcopy(value)
        for key in update.get("$unset", {}):
            self.document.pop(key, None)
        return SimpleNamespace(matched_count=1, modified_count=1)


class RouteAudit:
    def __init__(
        self,
        *,
        fail_insert: bool = False,
        fail_finalize: bool = False,
    ):
        self.documents = []
        self.fail_insert = fail_insert
        self.fail_finalize = fail_finalize
        self.calls = []

    async def insert_one(self, document):
        self.calls.append(("insert", copy.deepcopy(document)))
        if self.fail_insert:
            raise RuntimeError("simulated audit intent failure")
        self.documents.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document["id"])

    async def update_one(self, query, update):
        self.calls.append(
            ("update", copy.deepcopy(query), copy.deepcopy(update))
        )
        status = update.get("$set", {}).get("status")
        if self.fail_finalize and status == "canonical_promoted":
            raise RuntimeError("simulated audit finalization failure")
        document = next(
            (
                item
                for item in self.documents
                if all(nested_value(item, key) == value for key, value in query.items())
            ),
            None,
        )
        if document is None:
            return SimpleNamespace(matched_count=0, modified_count=0)
        for key, value in update.get("$set", {}).items():
            document[key] = copy.deepcopy(value)
        return SimpleNamespace(matched_count=1, modified_count=1)


async def route_book(slug: str):
    return (
        {
            "id": f"controlled-{slug}",
            "slug": slug,
            "title": "The Strange Case of Dr. Jekyll and Mr. Hyde",
            "author": "Robert Louis Stevenson",
        },
        "controlled_publication",
    )


async def no_public_cache():
    return None


def route_candidate() -> dict:
    return {
        "_id": f"{SLUG}:front",
        **candidate(),
    }


def configure_route(
    monkeypatch,
    tmp_path: Path,
    candidates: CasCandidates,
    *,
    promotion_result=None,
    audits: RouteAudit | None = None,
):
    repo_root = controlled_repo(tmp_path)
    (repo_root / ".git").write_text("gitdir: /tmp/test-git-dir\n", encoding="utf-8")
    audits = audits or RouteAudit()
    monkeypatch.setattr(server, "ENABLE_ADMIN_COVER_PROMOTIONS", True)
    monkeypatch.setattr(server, "EARNALISM_CANONICAL_REPO_ROOT", repo_root)
    monkeypatch.setattr(server, "_load_cover_upload_source_or_404", route_book)
    monkeypatch.setattr(server, "_fetch_immutable_cover_bytes", lambda *_args: image_bytes())
    monkeypatch.setattr(server, "_public_cache_clear", no_public_cache)
    monkeypatch.setattr(server, "clear_controlled_artifact_caches", lambda: None)
    if promotion_result is not None:
        monkeypatch.setattr(server, "promote_cover_candidate", promotion_result)
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            book_cover_candidates=candidates,
            admin_upload_audit=audits,
        ),
    )
    return repo_root, audits


def test_promotion_route_fails_closed_when_feature_is_disabled(monkeypatch):
    monkeypatch.setattr(server, "ENABLE_ADMIN_COVER_PROMOTIONS", False)

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Canonical cover promotion is disabled."


def test_runtime_readiness_requires_explicit_git_checkout_and_both_mirrors(
    monkeypatch, tmp_path
):
    repo_root = controlled_repo(tmp_path)
    monkeypatch.setattr(server, "ENABLE_ADMIN_COVER_PROMOTIONS", True)
    monkeypatch.setattr(server, "EARNALISM_CANONICAL_REPO_ROOT", None)
    assert server._canonical_cover_promotion_runtime_ready(SLUG) is False

    monkeypatch.setattr(server, "EARNALISM_CANONICAL_REPO_ROOT", repo_root)
    assert server._canonical_cover_promotion_runtime_ready(SLUG) is False

    (repo_root / ".git").mkdir()
    assert server._canonical_cover_promotion_runtime_ready(SLUG) is True
    shutil.rmtree(
        repo_root / "backend/data/controlled_publications" / SLUG
    )
    assert server._canonical_cover_promotion_runtime_ready(SLUG) is False


def test_stale_candidate_sha_loses_cas_before_remote_fetch(
    monkeypatch, tmp_path
):
    candidates = CasCandidates(route_candidate())
    configure_route(monkeypatch, tmp_path, candidates)
    monkeypatch.setattr(
        server,
        "_fetch_immutable_cover_bytes",
        lambda *_args: pytest.fail("CAS failure must occur before remote fetch."),
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload("0" * 64),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 409
    assert "changed or is already being promoted" in exc_info.value.detail
    assert (
        candidates.document["audit_status"]
        == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    )
    assert "promotion_claim" not in candidates.document


def test_promotion_failure_reverts_exact_mongo_claim(monkeypatch, tmp_path):
    candidates = CasCandidates(route_candidate())

    def fail_promotion(**_kwargs):
        raise CoverPromotionError("simulated controlled mirror failure")

    _, audits = configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        promotion_result=fail_promotion,
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 409
    assert "simulated controlled mirror failure" in exc_info.value.detail
    assert (
        candidates.document["audit_status"]
        == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    )
    assert "promotion_claim" not in candidates.document
    assert audits.documents[0]["status"] == "canonical_promotion_failed"
    assert audits.documents[0]["failure_type"] == "CoverPromotionError"


def test_promotion_failure_reports_claim_rollback_cas_loss(monkeypatch, tmp_path):
    candidates = CasCandidates(route_candidate(), fail_revert=True)

    def fail_promotion(**_kwargs):
        raise CoverPromotionError("simulated controlled mirror failure")

    _, audits = configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        promotion_result=fail_promotion,
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 409
    assert "could not be reverted" in exc_info.value.detail
    assert (
        audits.documents[0]["status"]
        == "canonical_promotion_failed_claim_revert_conflict"
    )


def test_successful_route_finalizes_same_claim_and_writes_audit(
    monkeypatch, tmp_path
):
    candidates = CasCandidates(route_candidate())

    def successful_promotion(**kwargs):
        return {
            "slug": SLUG,
            "kind": "front",
            "canonical_cover_url": candidate()["immutable_candidate_url"],
            "candidate_sha256": kwargs["expected_candidate_sha256"],
            "remote_sha256": kwargs["expected_candidate_sha256"],
            "event_id": kwargs["event_id"],
            "approval_evidence_file": "cover_approval_evidence.json",
            "reader_audio_release_truth_unchanged": True,
        }

    _, audits = configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        promotion_result=successful_promotion,
    )

    response = asyncio.run(
        server.admin_promote_cover(
            SLUG,
            promotion_payload(),
            admin={"sub": "owner-1", "email": "owner@example.com"},
        )
    )

    assert response["success"] is True
    assert response["cover_audit_status"] == "CANONICAL_PROMOTED"
    assert candidates.document["audit_status"] == "CANONICAL_PROMOTED"
    assert "promotion_claim" not in candidates.document
    claim_event = candidates.calls[0][1]["$set"]["promotion_claim"]["event_id"]
    final_query = candidates.calls[1][0]
    assert final_query["promotion_claim.event_id"] == claim_event
    assert candidates.document["promotion_event_id"] == claim_event
    assert audits.documents[0]["id"] == claim_event
    assert audits.documents[0]["status"] == "canonical_promoted"
    assert audits.documents[0]["cache_invalidation_succeeded"] is True


def test_finalize_cas_race_preserves_intent_and_records_operator_review(
    monkeypatch,
    tmp_path,
):
    candidates = CasCandidates(route_candidate(), fail_finalize=True)

    def successful_promotion(**kwargs):
        return {
            "slug": SLUG,
            "kind": "front",
            "canonical_cover_url": candidate()["immutable_candidate_url"],
            "candidate_sha256": kwargs["expected_candidate_sha256"],
            "remote_sha256": kwargs["expected_candidate_sha256"],
            "event_id": kwargs["event_id"],
            "approval_evidence_file": "cover_approval_evidence.json",
            "reader_audio_release_truth_unchanged": True,
        }

    _, audits = configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        promotion_result=successful_promotion,
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 409
    assert "operator review is required" in exc_info.value.detail
    assert (
        audits.documents[0]["status"]
        == "canonical_mutation_committed_candidate_finalize_conflict"
    )
    assert audits.documents[0]["operator_review_required"] is True
    assert audits.documents[0]["cache_invalidation_succeeded"] is True


def test_audit_intent_failure_reverts_claim_before_canonical_mutation(
    monkeypatch,
    tmp_path,
):
    candidates = CasCandidates(route_candidate())
    audits = RouteAudit(fail_insert=True)
    repo_root, _ = configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        audits=audits,
        promotion_result=lambda **_kwargs: pytest.fail(
            "Canonical mutation must not run without its audit intent."
        ),
    )
    before = publication_files(repo_root)
    monkeypatch.setattr(
        server,
        "_fetch_immutable_cover_bytes",
        lambda *_args: pytest.fail(
            "Remote fetch must not run without its audit intent."
        ),
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 502
    assert "Canonical mutation was not attempted" in exc_info.value.detail
    assert publication_files(repo_root) == before
    assert (
        candidates.document["audit_status"]
        == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    )
    assert "promotion_claim" not in candidates.document
    assert audits.documents == []


def test_audit_finalize_failure_happens_after_cache_invalidation_and_retry_is_safe(
    monkeypatch,
    tmp_path,
):
    candidates = CasCandidates(route_candidate())
    audits = RouteAudit(fail_finalize=True)
    cache_calls = []

    def successful_promotion(**kwargs):
        return {
            "slug": SLUG,
            "kind": "front",
            "canonical_cover_url": candidate()["immutable_candidate_url"],
            "candidate_sha256": kwargs["expected_candidate_sha256"],
            "remote_sha256": kwargs["expected_candidate_sha256"],
            "event_id": kwargs["event_id"],
            "approval_evidence_file": "cover_approval_evidence.json",
            "reader_audio_release_truth_unchanged": True,
        }

    configure_route(
        monkeypatch,
        tmp_path,
        candidates,
        audits=audits,
        promotion_result=successful_promotion,
    )

    def clear_controlled():
        cache_calls.append("controlled")

    async def clear_public():
        cache_calls.append("public")

    monkeypatch.setattr(server, "clear_controlled_artifact_caches", clear_controlled)
    monkeypatch.setattr(server, "_public_cache_clear", clear_public)

    with pytest.raises(server.HTTPException) as first_error:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert first_error.value.status_code == 409
    assert "caches were invalidated" in first_error.value.detail
    assert "do not retry automatically" in first_error.value.detail
    assert candidates.document["audit_status"] == "CANONICAL_PROMOTED"
    assert cache_calls == ["controlled", "public"]
    assert audits.documents[0]["status"] == "canonical_promotion_in_progress"
    assert any(
        call[0] == "update"
        and call[2]["$set"]["status"] == "canonical_promoted"
        for call in audits.calls
    )

    audit_call_count = len(audits.calls)
    candidate_call_count = len(candidates.calls)
    monkeypatch.setattr(
        server,
        "_fetch_immutable_cover_bytes",
        lambda *_args: pytest.fail(
            "A retry must not fetch or reapply an already promoted candidate."
        ),
    )
    with pytest.raises(server.HTTPException) as retry_error:
        asyncio.run(
            server.admin_promote_cover(
                SLUG,
                promotion_payload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert retry_error.value.status_code == 409
    assert "changed or is already being promoted" in retry_error.value.detail
    assert len(audits.calls) == audit_call_count
    assert len(candidates.calls) == candidate_call_count + 1
    assert cache_calls == ["controlled", "public"]
