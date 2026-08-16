#!/usr/bin/env python3
"""Reconcile two checksum-bound, already-live pilot audiobooks into repository truth.

This script does not upload, release, or publish audio. It only records the
existing production release after exact API, Range, checksum, and browser
verification, then rebuilds the controlled manifests and their backend mirrors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONTROLLED_ROOTS = (
    ROOT / "data" / "controlled_publications",
    ROOT / "backend" / "data" / "controlled_publications",
)
LAUNCH_PATHS = (ROOT / "data" / "controlled_launch.json", ROOT / "backend" / "data" / "controlled_launch.json")
RECONCILED_AT = "2026-08-16T06:45:34Z"
SOURCE_COMMIT = "e03b40e811bd0b1f79c5794b184e02a66d89fa3a"


CANDIDATES: dict[str, dict[str, Any]] = {
    "the-selfish-giant": {
        "title": "The Selfish Giant",
        "voice": "bm_george",
        "model": "hexgrad/Kokoro-82M",
        "fingerprint": "92a24c3442fe5ad637e72be523f52baded74d0390a256e3b5d5865bdb3f3d96e",
        "audio_sha256": "824944d0c068b4f4f45cb750e018918b2af55c5e043cd29417ce2a756e9a4c67",
        "audio_size_bytes": 7_673_229,
        "duration_seconds": 639.34,
        "manuscript_sha256": "0ec24ecbd6d5d594e74131b529b4e3d3ece31ae9f4130210f3c120c9db1ea62d",
        "asset_url": "https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks-prod-v2-236e72b043e2/audiobooks/the-selfish-giant/92a24c3442fe-824944d0c068.mp3",
        "asr_manuscript_score": 0.9994641900339346,
        "coverage": 0.9976275207591934,
        "first_span_score": 1.0,
        "last_span_score": 0.9960159362549801,
        "sample_set_sha256": "fc29c22eda6b074d002fac051c6ae36c1673b113f315bb9ed8f167cd6c8c8812",
        "accessibility_exception_sha256": "e32a5178f155eccbc006adc0b2321d82f1d63d8272fdf8479444b95a19cfa136",
        "parent_checksum_manifest_sha256": "34e28cb57223dfd6bf783e3109cbf710b4b8df9843d5841b9ceb0b8bf68f800e",
        "private_evidence_sha256": {
            "reader_preview_approval": "238548524f8f84699b44841a2439c0b994269bf7cd9767899205a93986fc9ea1",
            "audio_samples_approval": "93d26f41807f93bcfd81cd1c453325d0a5231e5a32973ad52b3acdeea5b44663",
            "accessibility_residual_risk_exception": "ce2f3cc53f77ce112af12bd72392a33062c505449a79580487f025f522ce97a0",
            "full_audio_derived_qa": "8f771ab326cd96d16e6d6ac39a205be4d481ee0b44b153bd517843fa8cae7458",
            "technical_audio_qa": "97c4f59f5483d6e95f2ed93cd0d92a0305d1138ec009c10374bd67dc3fc4f8eb",
            "ready_for_go_live": "2c977ee96cefe238623d44d9b80db7996d3e088045a24a631474da4ec70900c0",
        },
        "manifest_version_before_reconciliation": "07bf3a01e1ffcc91",
        "browser_elapsed_seconds": 2,
    },
    "a-white-heron": {
        "title": "A White Heron",
        "voice": "hf_alpha",
        "model": "hexgrad/Kokoro-82M",
        "fingerprint": "c8ff940d921f36625fb15ce92b2e6592c9e17dd0fd84e933ea872f73b16242e1",
        "audio_sha256": "70c94cc660fe15fdb4b5e3ef800643090d0eabd27b07523ffa5859b73e700f69",
        "audio_size_bytes": 19_917_837,
        "duration_seconds": 1659.725,
        "manuscript_sha256": "89989d544a1a01585bfe4e722ef141abf3f96642b45957d1683d37d4eddee300",
        "asset_url": "https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks-prod-v2-236e72b043e2/audiobooks/a-white-heron/c8ff940d921f-70c94cc660fe.mp3",
        "asr_manuscript_score": 0.9958909556841778,
        "coverage": 0.9972439136426274,
        "first_span_score": 0.967741935483871,
        "last_span_score": 0.9830508474576272,
        "sample_set_sha256": "7f70f8ec3bc332c19624b6ae79ff3439291e80d584ec9fd5f0aa1b5959a37f5c",
        "accessibility_exception_sha256": "3fcf89635301a67a8a64ac88f81ffcaef5dc86a7d800f333646ff990d8356b47",
        "parent_checksum_manifest_sha256": "beefbe20776e6b6a83a3ec8072535b0b39553e961cb179396e70dbaa9927988d",
        "private_evidence_sha256": {
            "reader_preview_approval": "e3147a2badb59e6f4252416b70341150c46903fa4c8eba9906dc8b7693bd357e",
            "audio_samples_approval": "e5659bde38271c84b9f03484072ac1c2fd0ae7a6ff0bd8181d7bdfe3e0d911b6",
            "accessibility_residual_risk_exception": "7f337b23f2752ebcacc84eb2b521512244abe07c1ca363b270b938ac2d9473c4",
            "full_audio_derived_qa": "2bb27b8f886141ae1dbe625b8d635cdec939ff5268cb1ef4009a53418d68393e",
            "technical_audio_qa": "d5ae84fe016c2705487585b3cdd484d415e6208be6dd90852d87bd5913001e64",
            "ready_for_go_live": "6bdb97f441cf2b933c2d73d0bb097ccabe5a862f6f42e9fd7fa16cb622fba1d6",
        },
        "manifest_version_before_reconciliation": "1e5cdb97f89fd8c7",
        "browser_elapsed_seconds": 3,
    },
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def approved_evidence(existing: dict[str, Any], slug: str, candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        **existing,
        "approval_scope": "batch2_checksum_bound_audio_release_reconciliation",
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
        "audiobook_enabled": True,
        "audio_qa_status": "QA_PASSED",
        "candidate_fingerprint": candidate["fingerprint"],
        "audio_sha256": candidate["audio_sha256"],
        "source_sha256": candidate["manuscript_sha256"],
        "audio_size_bytes": candidate["audio_size_bytes"],
        "duration_seconds": candidate["duration_seconds"],
        "provider": "kokoro",
        "model": candidate["model"],
        "voice": candidate["voice"],
        "asr_manuscript_score": candidate["asr_manuscript_score"],
        "source_coverage": candidate["coverage"],
        "first_span_score": candidate["first_span_score"],
        "last_span_score": candidate["last_span_score"],
        "no_missing_duplicated_reordered_content": True,
        "listening_qa_overall_score": 9.5,
        "listening_qa_minimum_score": 9.0,
        "listening_qa_confidence": 0.93,
        "listening_qa_sample_count": 6,
        "listening_qa_sample_set_sha256": candidate["sample_set_sha256"],
        "listening_qa_fatal_flags": [],
        "sync_tier": "AUDIO_ONLY_NO_SYNC",
        "auto_estimated_sync": False,
        "technical_audio_qa": {
            "codec": "mp3",
            "sample_rate_hz": 24000,
            "channels": 1,
            "full_decode_passed": True,
            "clipping_detected": False,
            "long_silence_detected": False,
        },
        "accessibility_residual_risk": {
            "decision": "OWNER_ACCEPTED_RESIDUAL_RISK",
            "voiceover_status": "NOT_TESTED",
            "talkback_status": "NOT_TESTED",
            "other_release_gates_waived": False,
            "confidence": 0.93,
            "exception_sha256": candidate["accessibility_exception_sha256"],
        },
        "private_evidence_sha256": candidate["private_evidence_sha256"],
        "upload_status": "UPLOADED_CHECKSUM_VERIFIED",
        "storage_backend": "b2_s3_private_proxy",
        "endpoint_url": f"/api/reader/book/{slug}/audiobook",
        "endpoint_http_status": 206,
        "endpoint_content_type": "audio/mpeg",
        "endpoint_accept_ranges": "bytes",
        "browser_gate_status": "PASS",
        "browser_playback_advanced": True,
        "release_blockers": [],
        "reconciled_at": RECONCILED_AT,
    }


def production_evidence(slug: str, candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "earnalism.batch2_live_audio_reconciliation.v1",
        "slug": slug,
        "candidate_fingerprint": candidate["fingerprint"],
        "audio_sha256": candidate["audio_sha256"],
        "audio_size_bytes": candidate["audio_size_bytes"],
        "duration_seconds": candidate["duration_seconds"],
        "verified_at": RECONCILED_AT,
        "source_commit": SOURCE_COMMIT,
        "production_api": {
            "status": 200,
            "reader_enabled": True,
            "audio_enabled": True,
            "audiobook_enabled": True,
            "audio_url": f"/api/reader/book/{slug}/audiobook",
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
        },
        "production_audio": {
            "full_get_status": 200,
            "full_get_sha256": candidate["audio_sha256"],
            "full_get_size_bytes": candidate["audio_size_bytes"],
            "range_status": 206,
            "range_request": "bytes=0-1023",
            "range_response_bytes": 1024,
            "content_type": "audio/mpeg",
            "accept_ranges": "bytes",
        },
        "browser": {
            "reader_url": f"https://theearnalism.com/reader/{slug}?listen=1",
            "player_visible": True,
            "first_narrated_page_opened": True,
            "playback_advanced": True,
            "elapsed_seconds_observed": candidate["browser_elapsed_seconds"],
            "pause_control_visible_while_playing": True,
        },
        "pre_reconciliation_manifest_contradiction": {
            "nested_book_audio_enabled": False,
            "top_level_audio_enabled": True,
            "manifest_version": candidate["manifest_version_before_reconciliation"],
        },
        "reconciliation_target": {
            "nested_book_audio_enabled": True,
            "top_level_audio_enabled": True,
            "root_backend_byte_parity": True,
            "raw_storage_url_exposed_by_public_api": False,
        },
    }


def rebuild_package(slug: str, candidate: dict[str, Any]) -> dict[Path, bytes]:
    canonical = CONTROLLED_ROOTS[0] / slug
    current_approval = read_json(canonical / "approval_evidence.json")
    already_reconciled = (
        current_approval.get("audio_public_release") == "PUBLIC_AUDIO_RELEASE_APPROVED"
        and current_approval.get("audio_sha256") == candidate["audio_sha256"]
    )
    if not already_reconciled and sha256_file(canonical / "checksum_manifest.json") != candidate["parent_checksum_manifest_sha256"]:
        raise RuntimeError(f"{slug}: parent checksum manifest changed; refusing reconciliation")

    public = read_json(canonical / "public_book.json")
    if public.get("audiobook_manuscript_sha256") != candidate["manuscript_sha256"]:
        raise RuntimeError(f"{slug}: manuscript checksum changed")
    public.update(
        {
            "audio_asset_slug": slug,
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": True,
            "audiobook_provider": "kokoro",
            "audiobook_voice": candidate["voice"],
            "audiobook_assets_updated_at": RECONCILED_AT,
            "audio_status": "AVAILABLE",
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_release_mode": "SERVER_OWNED_CONVEYOR",
            "audio_sha256": candidate["audio_sha256"],
            "candidate_fingerprint": candidate["fingerprint"],
            "updated_at": RECONCILED_AT,
        }
    )
    public.pop("audiobook_assets", None)
    public.pop("audiobook", None)
    reader = read_json(canonical / "reader_manifest.json")
    reader.update({"audio_enabled": True, "audiobook_enabled": True, "generated_at": RECONCILED_AT})
    approval = approved_evidence(current_approval, slug, candidate)
    evidence = production_evidence(slug, candidate)

    managed: dict[str, bytes] = {
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "approval_evidence.json": json_bytes(approval),
        "production_audio_evidence.json": json_bytes(evidence),
    }
    for relative in ("source_evidence.json", "highlight_sync.json", "chapters/chapter-001.json"):
        managed[relative] = (canonical / relative).read_bytes()

    checksum = {
        "slug": slug,
        "generated_at": RECONCILED_AT,
        "files": [
            {"file": relative, "sha256": sha256_bytes(data)}
            for relative, data in sorted(managed.items())
        ],
    }
    managed["checksum_manifest.json"] = json_bytes(checksum)

    with tempfile.TemporaryDirectory(prefix=f"{slug}-reconcile-") as temp_name:
        temp_dir = Path(temp_name)
        shutil.copytree(canonical, temp_dir, dirs_exist_ok=True)
        for relative, data in managed.items():
            target = temp_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        from backend.publication_manifest import build_manifest, validate_manifest

        manifest = build_manifest(temp_dir, publish_approved=True, generated_at=RECONCILED_AT)
        issues = validate_manifest(manifest)
        if issues:
            raise RuntimeError(f"{slug}: invalid publication manifest: {issues}")
        if manifest["audio_release"]["status"] != "APPROVED" or manifest["audio_release"]["exposed"] is not True:
            raise RuntimeError(f"{slug}: publication manifest did not approve audio")
        managed["publication_manifest.json"] = json_bytes(manifest)

    replacements: dict[Path, bytes] = {}
    for root in CONTROLLED_ROOTS:
        for relative, data in managed.items():
            replacements[root / slug / relative] = data
    return replacements


def launch_replacements() -> dict[Path, bytes]:
    # The existing database conveyor owns direct reader-player exposure. Static
    # launch allowlists also affect catalog/Home discovery, which this truth-only
    # reconciliation must not broaden.
    return {}


def title_history_replacement() -> tuple[Path, bytes]:
    path = ROOT / "internal" / "earnalism_intelligence" / "title_decision_history.json"
    payload = read_json(path)
    titles = payload.setdefault("titles", {})
    for slug, candidate in CANDIDATES.items():
        titles[slug] = {
            "latest_decision": "PUBLIC_READER_AND_CHECKSUM_BOUND_AUDIO_LIVE_RECONCILED",
            "decision_reason": "Production already served the owner-approved checksum-bound audiobook, but the controlled pack still said audio disabled. Repository truth is now bound to the exact production bytes and verified API, Range, checksum, and browser playback evidence.",
            "updated_at": RECONCILED_AT,
            "language": "en",
            "territory": "IN",
            "public_reader_status": "LIVE_APPROVED",
            "public_audio_status": "PUBLIC_AUDIO_RELEASE_APPROVED_AND_PROVEN",
            "candidate_fingerprint": candidate["fingerprint"],
            "audio_sha256": candidate["audio_sha256"],
            "voice": candidate["voice"],
            "production_audio_verified": True,
            "next_action": "Keep the exact bytes live and monitor API, Range, checksum, cache, and browser playback; do not regenerate or replace without a new checksum-bound two-gate attempt.",
        }
    batch = titles.setdefault("english-25-title-controlled-batch", {})
    batch.update(
        {
            "latest_decision": "TWO_PILOT_AUDIOBOOKS_LIVE_AND_REPOSITORY_TRUTH_RECONCILED",
            "decision_reason": "Production already serves the two owner-approved checksum-bound pilot audiobooks through the database-owned conveyor. Repository evidence now records the exact bytes while keeping catalog and Home discovery unchanged.",
            "updated_at": RECONCILED_AT,
            "pilot_generation_status": "THE_SELFISH_GIANT_AND_A_WHITE_HERON_LIVE_VERIFIED",
            "audio_hidden_count": 23,
            "live_audiobook_count": 2,
            "public_release_mutated": True,
            "next_action": "Continue the shortest-first queue through private reader approval, six-sample approval, full synthesis, automated QA, and production verification.",
        }
    )
    batch.pop("live_reader_count", None)
    return path, json_bytes(payload)


def ledger_replacement() -> tuple[Path, bytes]:
    path = ROOT / "internal" / "earnalism_intelligence" / "decision_ledger.jsonl"
    row = {
        "timestamp": RECONCILED_AT,
        "workstream": "english_25_title_controlled_release",
        "slug_or_area": "the-selfish-giant,a-white-heron",
        "decision": "reconcile_two_already_live_checksum_bound_audiobooks_into_controlled_repository_truth",
        "evidence": {
            slug: {
                "candidate_fingerprint": candidate["fingerprint"],
                "audio_sha256": candidate["audio_sha256"],
                "audio_size_bytes": candidate["audio_size_bytes"],
                "api_status": 200,
                "range_status": 206,
                "content_type": "audio/mpeg",
                "browser_playback_advanced": True,
            }
            for slug, candidate in CANDIDATES.items()
        },
        "selected_option": "Record the exact existing production asset, QA approvals, residual-risk exception, endpoint proof, and browser proof in byte-identical root/backend controlled packs without re-uploading or mutating live media.",
        "customer_experience_reason": "The reader manifest and player agree that both verified audiobooks are available while catalog and Home discovery remain unchanged.",
        "release_gate_reason": "No new exposure is created; reconciliation is guarded by exact fingerprints, source/audio checksums, private evidence checksums, production byte checksums, and a zero-blocker server-owned conveyor record.",
        "result": "LIVE_AUDIO_TRUTH_RECONCILED_PENDING_MERGE_DEPLOY_POSTCHECK",
        "next_action": "Merge the focused reconciliation and verify nested reader-manifest audio truth, Range 206, exact checksum, and browser playback on the deployed commit.",
    }
    encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    existing = path.read_text(encoding="utf-8")
    lines = existing.splitlines()
    replacement_index = None
    for index, line in enumerate(lines):
        try:
            existing_row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            existing_row.get("timestamp") == RECONCILED_AT
            and existing_row.get("workstream") == row["workstream"]
            and existing_row.get("slug_or_area") == row["slug_or_area"]
        ):
            replacement_index = index
            break
    encoded_line = encoded.rstrip("\n")
    if replacement_index is None:
        lines.append(encoded_line)
    else:
        lines[replacement_index] = encoded_line
    return path, (("\n".join(lines)).rstrip() + "\n").encode("utf-8")


def sprint_learnings_replacement() -> tuple[Path, bytes]:
    path = ROOT / "internal" / "earnalism_intelligence" / "sprint_learnings.md"
    section = """
## Live pilot audio truth reconciliation - 2026-08-16

- A successful database-owned audiobook release can leave a controlled reader pack stale: the public API and proxy may serve approved exact bytes while the nested reader manifest still says audio is disabled.
- Reconcile that split without re-uploading media: bind the production object to the exact attempt fingerprint, manuscript hash, audio SHA-256, size, duration, human approvals, objective QA, residual accessibility decision, API 200, Range 206, and observed browser playback.
- Keep the raw private storage URL only in the database-owned conveyor; controlled file packs, public projections, and reader manifests must expose only the same-origin release-gated API route.
- A publication manifest must represent approved audio as an independent lane. Reader approval cannot imply audio approval, and server-owned approved audio requires explicit release evidence, passing audio QA, a checksum, a fingerprint, an exact same-origin endpoint, and a verified production receipt.
""".lstrip()
    existing = path.read_text(encoding="utf-8")
    if section in existing:
        return path, existing.encode("utf-8")
    return path, (existing.rstrip() + "\n\n" + section).encode("utf-8")


def build_replacements() -> dict[Path, bytes]:
    replacements: dict[Path, bytes] = {}
    for slug, candidate in CANDIDATES.items():
        replacements.update(rebuild_package(slug, candidate))
    replacements.update(launch_replacements())
    for path, data in (title_history_replacement(), ledger_replacement(), sprint_learnings_replacement()):
        replacements[path] = data
    return replacements


def verify(replacements: dict[Path, bytes]) -> None:
    for slug, candidate in CANDIDATES.items():
        root = CONTROLLED_ROOTS[0] / slug
        backend = CONTROLLED_ROOTS[1] / slug
        for relative in (
            "public_book.json",
            "reader_manifest.json",
            "approval_evidence.json",
            "production_audio_evidence.json",
            "checksum_manifest.json",
            "publication_manifest.json",
        ):
            if replacements[root / relative] != replacements[backend / relative]:
                raise RuntimeError(f"{slug}: root/backend replacement mismatch for {relative}")
        approval = json.loads(replacements[root / "approval_evidence.json"])
        public = json.loads(replacements[root / "public_book.json"])
        if approval["audio_sha256"] != candidate["audio_sha256"]:
            raise RuntimeError(f"{slug}: approval audio checksum mismatch")
        if public.get("audiobook_release_mode") != "SERVER_OWNED_CONVEYOR":
            raise RuntimeError(f"{slug}: public audiobook delivery mode mismatch")
        if "backblazeb2.com" in json.dumps(public, sort_keys=True):
            raise RuntimeError(f"{slug}: controlled public book leaked a raw storage URL")
        checksum = json.loads(replacements[root / "checksum_manifest.json"])
        for row in checksum["files"]:
            target = root / row["file"]
            data = replacements[target] if target in replacements else target.read_bytes()
            if sha256_bytes(data) != row["sha256"]:
                raise RuntimeError(f"{slug}: checksum mismatch for {row['file']}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the deterministic reconciliation.")
    args = parser.parse_args(argv)
    replacements = build_replacements()
    verify(replacements)
    changed = [path for path, data in replacements.items() if not path.exists() or path.read_bytes() != data]
    if args.apply:
        for path in changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(replacements[path])
    print(json.dumps({"mode": "apply" if args.apply else "dry_run", "changed_files": [str(path.relative_to(ROOT)) for path in changed], "slugs": list(CANDIDATES)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
