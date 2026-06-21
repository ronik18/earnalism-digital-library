from __future__ import annotations

from pathlib import Path

from scripts import controlled_publication_precheck as precheck


def write_approved_to_publish(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# Approved To Publish",
                "",
                "## Dracula",
                "- Work Title: Dracula",
                "- Work Slug: dracula",
                "- Rights Tier: A",
                "- Verification Status: approved",
                "- Source URL: https://www.gutenberg.org/ebooks/345",
                "- Source Name: Project Gutenberg eBook #345",
                "- Source License: Project Gutenberg License",
                "- Source License URL: https://www.gutenberg.org/policy/license.html",
                "- Commercial Use Status: conditional_allowed_subject_to_project_gutenberg_license_and_trademark_terms",
                "- Source Hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "- Content Hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "- Provenance Hash: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "- Attribution Requirement: simple public source note allowed; license evidence internal",
                "- Derivative Audiobook Rights Status: not approved; separate approval required; AUDIO_NOT_REQUIRED for core reading",
                "- Public Metadata Allowed: yes",
                "- Public CTA Allowed: yes",
                "- Owner Approval Status: approved",
                "- GO/HOLD Decision: GO_DRACULA_CORE_READING_ONLY",
                "- Rights Basis: public domain source evidence reviewed",
                "- QA Status: QA_PASSED",
                "- Rollback Owner: release-operator",
                "- Publication Cap: Dracula controlled-publication candidate only",
                "- Rollback Plan: restore prior publication state",
                "- Production Parity Status: PASS",
                "- Production Parity Evidence: output/launch/post_deploy_route_canary.json",
                "- Payment Smoke Status: PASS_TEST_MODE",
                "- Payment Smoke Evidence: output/launch/payment_smoke.json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_find_public_audio_like_files_detects_public_and_build_audio(tmp_path):
    public_audio = tmp_path / "frontend" / "public" / "audio" / "en"
    build_audio = tmp_path / "frontend" / "build" / "audio" / "ben"
    public_audio.mkdir(parents=True)
    build_audio.mkdir(parents=True)
    (public_audio / "demo.mp3").write_bytes(b"demo")
    (build_audio / "demo_timestamps.json").write_text("[]\n", encoding="utf-8")

    assert precheck.find_public_audio_like_files(tmp_path) == [
        "frontend/build/audio/ben/demo_timestamps.json",
        "frontend/public/audio/en/demo.mp3",
    ]


def test_controlled_publication_precheck_blocks_public_audio_assets(tmp_path, monkeypatch):
    approved = tmp_path / "APPROVED_TO_PUBLISH.md"
    write_approved_to_publish(approved)
    public_audio = tmp_path / "frontend" / "public" / "audio" / "en"
    public_audio.mkdir(parents=True)
    (public_audio / "dracula.mp3").write_bytes(b"demo")

    monkeypatch.setattr(precheck, "ROOT", tmp_path)
    monkeypatch.setattr(precheck, "APPROVED_FILE", approved)

    report = precheck.evaluate()

    assert report["status"] == "BLOCKED"
    assert report["public_audio_like_files"] == ["frontend/public/audio/en/dracula.mp3"]
    assert any("public/build audio-like assets must be quarantined" in issue for issue in report["issues"])
