#!/usr/bin/env python3
"""Deterministic, fail-closed provenance helpers for private audiobook runs.

This module never downloads a model, calls a provider, uploads bytes, or changes
catalogue/release state. Audio synthesis is injected by the caller so callers
can make the paid/CUDA boundary explicit.
"""

from __future__ import annotations

import hashlib
import argparse
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA = "earnalism.audiobook_generation_provenance.v1"
GUTENBERG_ID = 269
MODEL_REPO = "hexgrad/Kokoro-82M"
DEFAULT_VOICES = ("af_heart", "af_bella", "af_nicole")
VOICE_LANGUAGES = {
    "af_heart": ("en",),
    "af_bella": ("en",),
    "af_nicole": ("en",),
    "af_sarah": ("en",),
    "af_sky": ("en",),
    "am_adam": ("en",),
    "am_michael": ("en",),
    "bf_emma": ("en",),
    "bf_isabella": ("en",),
    "bm_george": ("en",),
    "bm_lewis": ("en",),
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_gutenberg(raw: str | bytes, expected_id: int = GUTENBERG_ID) -> str:
    """Extract only the body between Gutenberg's exact ebook markers.

    Header/footer and license boilerplate are discarded. The result is UTF-8,
    LF-only, NFC-normalized, and has canonical blank-line/space handling.
    """
    import unicodedata

    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Project Gutenberg's legacy #269 plain-text file omits the numeric ID from
    # the in-file marker. Bind the ID through the separately verified source URL.
    if expected_id != GUTENBERG_ID:
        raise ValueError(f"This normalizer is pinned to Project Gutenberg #{GUTENBERG_ID}")
    marker = re.compile(r"^\s*\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*{3}\s*$", re.I | re.M)
    starts = list(marker.finditer(text))
    if len(starts) != 1:
        raise ValueError(f"Expected exactly one Gutenberg ebook start marker; found {len(starts)}")
    end_marker = re.compile(r"^\s*\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\*{3}\s*$", re.I | re.M)
    ends = [match for match in end_marker.finditer(text, starts[0].end())]
    if len(ends) != 1:
        raise ValueError(f"Expected exactly one Gutenberg end marker after start; found {len(ends)}")
    body = unicodedata.normalize("NFC", text[starts[0].end() : ends[0].start()])
    lines = [re.sub(r"[\t \u00a0]+$", "", line) for line in body.split("\n")]
    body = "\n".join(lines).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    if not body:
        raise ValueError("Gutenberg body is empty")
    if re.search(r"Project Gutenberg|gutenberg\.org|\*\*\*\s*(?:START|END) OF", body, re.I):
        raise ValueError("Gutenberg boilerplate leaked into normalized manuscript")
    return body + "\n"


def normalize_gutenberg_story(raw: str | bytes, *, title: str = "THE OPEN WINDOW",
                              next_title: str = "THE TREASURE SHIP") -> str:
    """Normalize the anthology and extract the exact #269 story interval."""
    body = normalize_gutenberg(raw)
    escaped_title = re.escape(title)
    escaped_next = re.escape(next_title)
    start = re.search(rf"(?m)^\s*{escaped_title}\s*$", body, re.I)
    if not start:
        raise ValueError(f"Gutenberg #269 story heading not found: {title}")
    end = re.search(rf"(?m)^\s*{escaped_next}\s*$", body[start.end():], re.I)
    if not end:
        raise ValueError(f"Gutenberg #269 next story heading not found: {next_title}")
    story = body[start.end(): start.end() + end.start()]
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", story):
        line = re.sub(r"\s+", " ", paragraph).strip()
        if line:
            paragraphs.append(line)
    if not paragraphs:
        raise ValueError("Gutenberg #269 story interval is empty")
    normalized = "\n\n".join(paragraphs) + "\n"
    if re.search(r"Project Gutenberg|gutenberg\.org|\*\*\*\s*(?:START|END) OF", normalized, re.I):
        raise ValueError("Gutenberg boilerplate leaked into normalized story")
    return normalized


def normalized_manuscript_hash(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def source_binding(source_bytes: bytes, normalized_text: str, source_url: str) -> dict[str, Any]:
    parsed = urlparse(source_url)
    if parsed.hostname not in {"www.gutenberg.org", "gutenberg.org"} or not re.search(r"(?:^|/)269(?:/|$)", parsed.path):
        raise ValueError("Source URL must bind the approved Project Gutenberg #269 source")
    return {
        "source_id": "project-gutenberg-269",
        "source_url": source_url,
        "source_sha256": sha256_bytes(source_bytes),
        "manuscript_sha256": normalized_manuscript_hash(normalized_text),
        "normalization": "gutenberg-269-story-dewrap-v1",
    }


def deterministic_generation_job_id(
    *, source_sha256: str, manuscript_sha256: str, model_repo: str,
    model_revision: str, voice: str, settings: dict[str, Any], language: str,
) -> str:
    payload = {
        "schema": "earnalism.generation_job.v1", "source_sha256": source_sha256,
        "manuscript_sha256": manuscript_sha256, "model_repo": model_repo,
        "model_revision": model_revision, "voice": voice, "settings": settings,
        "language": language,
    }
    return "egj_" + sha256_bytes(canonical_json(payload))


def tree_sha256(path: str | Path) -> str:
    root = Path(path)
    if root.is_file():
        return sha256_file(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        raise ValueError("Model artifact directory is empty")
    for file in files:
        rel = file.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(bytes.fromhex(sha256_file(file)))
    return digest.hexdigest()


def find_hf_model_snapshot(model_repo: str = MODEL_REPO) -> tuple[str | None, Path | None]:
    """Find a locally cached immutable Hugging Face snapshot without downloading."""
    cache_root = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    repo_dir = cache_root / "hub" / ("models--" + model_repo.replace("/", "--")) / "snapshots"
    if not repo_dir.is_dir():
        return None, None
    snapshots = sorted((p for p in repo_dir.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for snapshot in snapshots:
        if re.fullmatch(r"[0-9a-f]{40,64}", snapshot.name, re.I):
            return snapshot.name, snapshot
    return None, None


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def capture_runtime(*, model_revision: str | None, model_path: str | Path | None = None) -> dict[str, Any]:
    """Capture installed runtime and require immutable model revision evidence."""
    revision = (model_revision or "").strip()
    discovered_revision, discovered_path = find_hf_model_snapshot()
    if not revision and discovered_revision:
        revision = discovered_revision
    if model_path is None and discovered_path:
        model_path = discovered_path
    immutable_revision = bool(re.fullmatch(r"[0-9a-f]{40,64}", revision, flags=re.I))
    artifact_hash = tree_sha256(model_path) if model_path else None
    torch_info: dict[str, Any] = {"version": _version("torch"), "cuda_available": False, "cuda_version": None}
    try:
        import torch  # type: ignore

        torch_info.update(
            cuda_available=bool(torch.cuda.is_available()),
            cuda_version=getattr(torch.version, "cuda", None),
            device_count=int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        )
    except ImportError:
        pass
    packages = {name: _version(name) for name in ("kokoro", "torch", "soundfile", "misaki", "numpy")}
    return {
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "platform": platform.platform(), "packages": packages, "pytorch": torch_info,
        "model": {"repo": MODEL_REPO, "revision": revision or None,
                  "revision_immutable": immutable_revision, "artifact_sha256": artifact_hash,
                  "artifact_path_present": bool(model_path),
                  "pinning_ready": immutable_revision and artifact_hash is not None},
    }


def compatible_voice_inventory(language: str, available_voices: Iterable[str]) -> list[dict[str, Any]]:
    """Intersect explicit known voices with the runtime's actual voice inventory."""
    lang = language.lower()
    available = set(available_voices)
    return [
        {"voice_id": voice, "language": lang, "compatible": True}
        for voice, languages in VOICE_LANGUAGES.items()
        if voice in available and lang in languages
    ]


def run_auditions(
    *, text: str, voices: list[str], language: str, output_dir: str | Path,
    source_binding_data: dict[str, Any], model_revision: str,
    settings: dict[str, Any], synthesize: Callable[[str, str, dict[str, Any]], bytes],
    runtime_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize only explicitly requested audition samples and hash each file."""
    if not 2 <= len(voices) <= 3 or len(set(voices)) != len(voices):
        raise ValueError("Audition mode requires two or three distinct voices")
    inventory = compatible_voice_inventory(language, voices)
    if len(inventory) != len(voices):
        raise ValueError("Every audition voice must be explicitly inventoried and language-compatible")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for voice in voices:
        audio = synthesize(text, voice, settings)
        if not audio:
            raise ValueError(f"Synthesis returned empty audition bytes for {voice}")
        audio_path = out / f"audition-{voice}.wav"
        audio_path.write_bytes(audio)
        records.append({
            "voice_id": voice, "language": language, "source_sha256": source_binding_data["source_sha256"],
            "manuscript_sha256": source_binding_data["manuscript_sha256"],
            "sample_text_sha256": normalized_manuscript_hash(text), "model_repo": MODEL_REPO,
            "model_revision": model_revision, "settings": settings,
            "audio_file": audio_path.name, "audio_sha256": sha256_file(audio_path),
            "size_bytes": audio_path.stat().st_size,
        })
    manifest = {
        "schema_version": "earnalism.audiobook_audition_manifest.v1",
        "mode": "PRIVATE_AUDITION_ONLY", "voices": records,
        "inventory": inventory, "owner_selected_voice": None,
        "runtime_provenance": runtime_provenance,
        "full_generation_authorized": False, "public_release_ready": False,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))
    (out / "audition_manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    return manifest


def require_full_generation(owner_approved: bool, selected_voice: str | None) -> None:
    if not owner_approved:
        raise PermissionError("Full generation requires OWNER_FULL_GENERATION_APPROVED=True")
    if not selected_voice:
        raise PermissionError("Full generation requires OWNER_SELECTED_VOICE")
    if selected_voice not in VOICE_LANGUAGES:
        raise PermissionError("OWNER_SELECTED_VOICE is not in the explicit voice inventory")


def segment_provenance(
    *, job_id: str, segment_id: str, text: str, audio_path: str | Path,
    start_word: int, end_word: int, start_paragraph: int, end_paragraph: int,
    start_ms: int | None, end_ms: int | None, voice: str, model_revision: str,
) -> dict[str, Any]:
    path = Path(audio_path)
    measured = start_ms is not None and end_ms is not None and end_ms > start_ms
    return {
        "schema_version": "earnalism.audiobook_segment_provenance.v1",
        "generation_job_id": job_id, "segment_id": segment_id,
        "text_sha256": normalized_manuscript_hash(text), "audio_sha256": sha256_file(path),
        "audio_size_bytes": path.stat().st_size, "start_word": start_word, "end_word": end_word,
        "start_paragraph": start_paragraph, "end_paragraph": end_paragraph,
        "start_ms": start_ms, "end_ms": end_ms, "sync_measured": measured,
        "voice": voice, "model_repo": MODEL_REPO, "model_revision": model_revision,
    }


def build_generation_manifest(
    *, job_id: str, binding: dict[str, Any], runtime: dict[str, Any], voice: str,
    settings: dict[str, Any], segments: list[dict[str, Any]], qa_evidence: list[dict[str, Any]],
    license_evidence: list[dict[str, Any]], storage_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = {
        "schema_version": SCHEMA, "generation_job_id": job_id,
        "source_binding": binding, "model_runtime": runtime, "voice": voice,
        "generation_settings": settings, "segments": segments,
        "qa_evidence": qa_evidence, "license_evidence": license_evidence,
        "storage_receipts": storage_receipts,
        "release_state": "PRIVATE_CANDIDATE",
        "public_release_ready": False,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def evidence_reference(path: str | Path, evidence_type: str) -> dict[str, Any]:
    """Reference existing evidence without fabricating or promoting its status."""
    file = Path(path)
    return {"evidence_type": evidence_type, "path": str(file),
            "present": file.is_file(), "sha256": sha256_file(file) if file.is_file() else None,
            "decision": "UNREVIEWED"}


def storage_receipt_reference(path: str | Path, expected_assets: dict[str, str]) -> dict[str, Any]:
    """Bind an existing handoff receipt to expected assets; never create a receipt."""
    file = Path(path)
    if not file.is_file():
        return {"present": False, "path": str(file), "sha256": None,
                "matched_assets": False, "release_eligible": False}
    receipt = json.loads(file.read_text(encoding="utf-8"))
    asset_hashes = receipt.get("assets", {})
    matched = bool(expected_assets) and all(asset_hashes.get(key, {}).get("sha256") == value
                                           for key, value in expected_assets.items())
    return {"present": True, "path": str(file), "sha256": sha256_file(file),
            "matched_assets": matched, "release_eligible": False}


def build_rights_workflow_bundle(*, source_sha256: str, manuscript_sha256: str,
                                evidence_paths: dict[str, str | Path]) -> dict[str, Any]:
    required = ("rights_decision", "publication_manifest", "audio_distribution_authority", "ownership_chain")
    evidence = {name: evidence_reference(evidence_paths[name], name) for name in required}
    complete = all(item["present"] for item in evidence.values())
    return {
        "schema_version": "earnalism.audiobook_rights_workflow_bundle.v1",
        "source_sha256": source_sha256, "manuscript_sha256": manuscript_sha256,
        "evidence": evidence, "status": "EVIDENCE_PRESENT_UNREVIEWED" if complete else "BLOCKED_MISSING_EVIDENCE",
        "release_eligible": False,
    }


def create_package_v2_candidate(*, repo_root: str | Path, slug: str,
                                full_manifest: str | Path, objective_qa: str | Path,
                                listening_qa: str | Path, release_evidence: str | Path,
                                output_dir: str | Path) -> None:
    """Delegate to the repository's guarded package-v2 candidate builder."""
    command = [sys.executable, str(Path(repo_root) / "internal/audiobook_lab/scripts/audiobook_package_builder_v2.py"),
               "build-qa-candidate", "--repo-root", str(repo_root), "--slug", slug,
               "--full-manifest", str(full_manifest), "--objective-qa", str(objective_qa),
               "--listening-qa", str(listening_qa), "--release-evidence", str(release_evidence),
               "--output-dir", str(output_dir)]
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    normalize = subparsers.add_parser("normalize-gutenberg-269-story")
    normalize.add_argument("--input", required=True, help="Previously downloaded, rights-cleared PG #269 source")
    normalize.add_argument("--output", required=True, help="Internal canonical manuscript output path")
    normalize.add_argument("--manifest", required=True, help="Internal source-binding manifest path")
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    manuscript = normalize_gutenberg_story(raw)
    binding = source_binding(raw, manuscript, "https://www.gutenberg.org/cache/epub/269/pg269.txt")
    binding.update({"title": "The Open Window", "author": "Saki", "story_interval": {
        "start_heading": "THE OPEN WINDOW", "exclusive_end_heading": "THE TREASURE SHIP"},
        "normalization": "gutenberg-269-story-dewrap-v1", "public_release_ready": False})
    output, manifest = Path(args.output), Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(manuscript, encoding="utf-8")
    manifest.write_bytes(canonical_json(binding) + b"\n")
    print(json.dumps({"manuscript_sha256": binding["manuscript_sha256"],
                      "source_sha256": binding["source_sha256"],
                      "output": str(output), "manifest": str(manifest),
                      "public_release_ready": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
