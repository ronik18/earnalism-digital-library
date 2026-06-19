from __future__ import annotations

import json
from pathlib import Path

from scripts import controlled_publication_publish as publish


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def valid_source() -> dict:
    return {
        "generated_at": "2026-06-19T00:00:00Z",
        "slug": "dracula",
        "title": "Dracula",
        "author": "Bram Stoker",
        "author_death_year": 1912,
        "original_publication_year": 1897,
        "source_url": "https://www.gutenberg.org/ebooks/345",
        "source_name": "Project Gutenberg eBook #345",
        "source_license": "Project Gutenberg License",
        "source_hash": "a" * 64,
        "content_hash": "b" * 64,
        "provenance_hash": "c" * 64,
        "rights_tier": "A",
        "verification_status": "approved",
        "publication_region": "global",
        "qa_status": "QA_PASSED",
        "meaningful_chapter_count": 27,
        "ingestion": {
            "source_hash": "a" * 64,
            "content_hash": "b" * 64,
            "provenance_hash": "c" * 64,
        },
    }


def valid_gate() -> dict:
    return {
        "publishing_workflow_status": "READY_FOR_PUBLICATION_DRAFT_CANDIDATE",
        "workflow": {"blockers": [], "publish_readiness": "READY"},
        "recommendation": publish.GO_RECOMMENDATION,
        "high_blockers": [],
        "audio_status": "AUDIO_NOT_REQUIRED",
    }


def setup_context(tmp_path: Path, monkeypatch, *, rights_tier: str = "A", audio_status: str = "AUDIO_NOT_REQUIRED"):
    route = tmp_path / "output" / "launch" / "post_deploy_route_canary.json"
    payment = tmp_path / "output" / "launch" / "payment_smoke.json"
    source_path = tmp_path / "output" / "publication_candidates" / "dracula" / "source_evidence.json"
    gate_path = tmp_path / "output" / "publication_candidates" / "dracula" / "dracula_gate_results.json"
    source_hashes_path = tmp_path / "output" / "publication_candidates" / "dracula" / "source_hashes.json"
    for path in [route, payment, source_path, gate_path, source_hashes_path]:
        path.parent.mkdir(parents=True, exist_ok=True)

    source = valid_source()
    source["rights_tier"] = rights_tier
    gate = valid_gate()
    gate["audio_status"] = audio_status
    write_json(route, {"status": "PASS"})
    write_json(payment, {"status": "PASS_TEST_MODE"})
    write_json(source_path, source)
    write_json(gate_path, gate)
    write_json(
        source_hashes_path,
        {
            "source_hash": source["source_hash"],
            "content_hash": source["content_hash"],
            "provenance_hash": source["provenance_hash"],
        },
    )

    approval = tmp_path / "APPROVED_TO_PUBLISH.md"
    approval.write_text(
        "\n".join(
            [
                "# Approved To Publish",
                "",
                "## Dracula",
                "",
                "- Work Title: Dracula",
                "- Work Slug: dracula",
                f"- Rights Tier: {rights_tier}",
                "- Verification Status: approved",
                "- QA Status: QA_PASSED",
                "- Publication Cap: Dracula controlled-publication candidate only; public_publish_actions=0.",
                "- Production Parity Status: PASS",
                "- Production Parity Evidence: output/launch/post_deploy_route_canary.json",
                f"- Production Parity Evidence Hash: {publish.file_sha256(route)}",
                "- Payment Smoke Status: PASS_TEST_MODE",
                "- Payment Smoke Evidence: output/launch/payment_smoke.json",
                f"- Payment Smoke Evidence Hash: {publish.file_sha256(payment)}",
                "- Source Evidence: output/publication_candidates/dracula/source_evidence.json",
                f"- Source Evidence Hash: {publish.file_sha256(source_path)}",
                "- Gate Results Evidence: output/publication_candidates/dracula/dracula_gate_results.json",
                f"- Gate Results Hash: {publish.file_sha256(gate_path)}",
                "",
                "Approval Scope:",
                "",
                "- Approved Scope: Dracula core reading candidate only.",
                "- Not Approved: full study guide, full visual edition, full audiobook, paid ads, email sends, or social publishing.",
                "- Audiobook Status: AUDIO_NOT_REQUIRED.",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(publish, "ROOT", tmp_path)
    monkeypatch.setattr(publish, "SOURCE_EVIDENCE", source_path)
    monkeypatch.setattr(publish, "GATE_RESULTS", gate_path)
    monkeypatch.setattr(publish, "SOURCE_HASHES", source_hashes_path)
    context, issues = publish.load_validation_context(approval)
    assert context is not None
    assert issues == []
    return context


def test_valid_dracula_context_passes(monkeypatch, tmp_path):
    context = setup_context(tmp_path, monkeypatch)

    assert publish.validate_context(context) == []


def test_tier_b_is_not_publishable(monkeypatch, tmp_path):
    context = setup_context(tmp_path, monkeypatch, rights_tier="B")

    issues = publish.validate_context(context)

    assert "Approved item must be Tier A." in issues
    assert "source_evidence.rights_tier must be A." in issues


def test_full_audiobook_status_blocks_core_reading_publication(monkeypatch, tmp_path):
    context = setup_context(tmp_path, monkeypatch, audio_status="QA_PASSED")

    issues = publish.validate_context(context)

    assert "Gate audio_status must be AUDIO_NOT_REQUIRED for this core reading activation." in issues


def test_controlled_publication_update_publishes_reading_and_clears_audio():
    update = publish.controlled_publication_update(valid_source(), now="2026-06-19T00:00:00Z")

    assert update["is_published"] is True
    assert update["rights_metadata"]["rights_tier"] == "A"
    assert update["rights_metadata"]["verification_status"] == "approved"
    assert update["audiobook_enabled"] is False
    assert update["generate_audiobook"] is False
    assert update["audiobook_assets"] == {}
    assert update["audiobook"] == {}
    assert update["controlled_publication_scope"] == "core_reading_candidate_only"


def test_absolute_api_url_handles_reader_paths_without_double_api_prefix():
    resolved = publish.absolute_api_url(
        "https://api.theearnalism.com/api",
        "/api/reader/chapter/dracula/chapter-1",
    )

    assert resolved == "https://api.theearnalism.com/api/reader/chapter/dracula/chapter-1"


def test_redis_invalidation_reports_connection_failure_without_crashing(monkeypatch):
    class FailingRedisClient:
        def incr(self, _key):
            raise OSError("redis unavailable")

    class FailingRedis:
        @staticmethod
        def from_url(*_args, **_kwargs):
            return FailingRedisClient()

    monkeypatch.setenv("REDIS_URL", "redis://redis.railway.internal:6379")
    monkeypatch.setitem(__import__("sys").modules, "redis", FailingRedis)

    result = publish.invalidate_redis_cache_generations()

    assert result["attempted"] is True
    assert "Redis invalidation failed" in result["reason"]
