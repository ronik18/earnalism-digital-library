#!/usr/bin/env python3
"""Execute one hash-bound private bf_emma audition for The Tell-Tale Heart.

The preflight and execution modes share the already-reviewed canonical source
contract.  Execution is limited to four representative passages, exact local
Kokoro/Whisper artifacts, British G2P, and private WAV paths.  It cannot call a
provider, inspect a paid coordination lock, upload, publish, or mutate release
truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import types
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - installation guard
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_module(
    "earnalism_tell_tale_preflight",
    SCRIPT_DIR / "sprint1_tell_tale_kokoro_private_preflight.py",
)
BASE = _load_module(
    "earnalism_kokoro_title_base",
    SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py",
)

SLUG = PREFLIGHT.SLUG
TITLE = PREFLIGHT.TITLE
AUTHOR = PREFLIGHT.AUTHOR
PROFILE = PREFLIGHT.PROFILE
VOICE = PREFLIGHT.VOICE
VOICE_SHA256 = PREFLIGHT.VOICE_SHA256
SPEED = PREFLIGHT.SPEED
RANDOM_SEED = PREFLIGHT.RANDOM_SEED
EXPECTED_ATTEMPT_FINGERPRINT = (
    "5ab7a8abdc62cd901d16d7cb9fb6fe10094bb829d279574a6ccd6da88e1562f9"
)
BRITISH_LANG_CODE = "b"
BRITISH_G2P = True
G2P_FALLBACK = None
G2P_UNKNOWN_TOKEN_OUTPUT = ""
SAMPLE_RATE = 24_000

BRITISH_PHONEME_HASHES = {
    "opening_unreliable_sanity": "358708c587367584a392794b2a169288c7e0e806491fa49da66c4b31ae06d3f5",
    "bedroom_suspense_dialogue": "53889e558a06e270be0d283eea6b91e75e6a1c814856fc85a03b5f761f1c0044",
    "heartbeat_crescendo": "8dcc83a940610a93f41842c5e9460a459d984332bf9b7dc2b8a6a79567851dde",
    "final_confession": "048b7e72baca9d575e108c138e3a4aa19b95f7f34420e3620a0d1f9b3c9695e5",
}

ASR_VOCABULARY_PROMPT = ""
ASR_PROMPT_POLICY = {item["passage_id"]: "no_prompt" for item in PREFLIGHT.PASSAGE_SPECS}
SOURCE_EQUIVALENCE_POLICY = {item["passage_id"]: () for item in PREFLIGHT.PASSAGE_SPECS}

DEFAULT_EXECUTION_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-tell-tale-heart_kokoro_bf_emma_representative_execution_v1.json"
)


class TellTaleExecutorError(RuntimeError):
    """Raised when the private execution contract cannot be preserved."""


def configure_base() -> None:
    """Bind reusable ASR helpers to the immutable Tell-Tale contract."""

    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = PREFLIGHT.LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = PREFLIGHT.RAW_SOURCE_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = PREFLIGHT.RAW_SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PREFLIGHT.PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(
        str(item["sha256"]) for item in PREFLIGHT.PASSAGE_SPECS
    )
    BASE.EXPECTED_PASSAGE_CHARACTERS = PREFLIGHT.PASSAGE_CHARACTERS
    BASE.MODEL_REVISION = PREFLIGHT.MODEL_REVISION
    BASE.MODEL_SHA256 = PREFLIGHT.MODEL_SHA256
    BASE.CONFIG_SHA256 = PREFLIGHT.CONFIG_SHA256
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = f"voices/{VOICE}.pt"
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.WHISPER_MODEL = PREFLIGHT.WHISPER_MODEL
    BASE.WHISPER_SHA256 = PREFLIGHT.WHISPER_SHA256
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.ASR_SCORE_MIN = PREFLIGHT.ASR_SOURCE_SCORE_MIN
    BASE.ASR_COVERAGE_MIN = PREFLIGHT.ASR_COVERAGE_MIN
    BASE.PRONUNCIATION_OVERRIDES = {}
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.controlled_source = PREFLIGHT.controlled_source
    BASE.attempt_fingerprint = PREFLIGHT.attempt_fingerprint


def validate_british_g2p(
    passages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove every source token resolves with British G2P and no fallback."""

    try:
        from misaki import en as misaki_en  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - pinned runtime guard
        raise TellTaleExecutorError("pinned misaki runtime is unavailable") from exc
    g2p = misaki_en.G2P(
        trf=False,
        british=BRITISH_G2P,
        fallback=G2P_FALLBACK,
        unk=G2P_UNKNOWN_TOKEN_OUTPUT,
    )
    reports: list[dict[str, Any]] = []
    for passage in passages:
        phonemes, tokens = g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        passage_id = str(passage["passage_id"])
        observed_hash = PREFLIGHT.sha256_text(phonemes)
        expected_hash = BRITISH_PHONEME_HASHES[passage_id]
        if unresolved:
            raise TellTaleExecutorError(
                f"British G2P has unresolved tokens in {passage_id}: {', '.join(unresolved)}"
            )
        if observed_hash != expected_hash:
            raise TellTaleExecutorError(
                f"British G2P phoneme hash changed for {passage_id}: "
                f"expected {expected_hash}, observed {observed_hash}"
            )
        reports.append(
            {
                "passage_id": passage_id,
                "source_text_sha256": passage["text_sha256"],
                "token_count": len(tokens),
                "phoneme_sha256": observed_hash,
                "unresolved_tokens": [],
            }
        )
    return {
        "status": "PASS",
        "lang_code": BRITISH_LANG_CODE,
        "british": BRITISH_G2P,
        "fallback": None,
        "unknown_token_output": G2P_UNKNOWN_TOKEN_OUTPUT,
        "reports": reports,
    }


def _install_local_filelock_stub() -> types.ModuleType | None:
    """Keep model loading local without allowing hub-lock side effects."""

    stub = types.ModuleType("filelock")

    class LocalOnlyFileLock:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.lock_file = args[0] if args else None

        def acquire(self, *args: Any, **kwargs: Any) -> "LocalOnlyFileLock":
            return self

        def release(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "LocalOnlyFileLock":
            return self.acquire()

        def __exit__(self, *args: Any) -> None:
            self.release()

    class LocalOnlyTimeout(TimeoutError):
        pass

    stub.BaseFileLock = LocalOnlyFileLock
    stub.FileLock = LocalOnlyFileLock
    stub.SoftFileLock = LocalOnlyFileLock
    stub.Timeout = LocalOnlyTimeout
    previous = sys.modules.get("filelock")
    sys.modules["filelock"] = stub
    return previous


def synthesize_british(
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
) -> list[dict[str, Any]]:
    """Synthesize only the four audited passages with exact British G2P."""

    previous_filelock = _install_local_filelock_stub()
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from kokoro import KModel, KPipeline  # noqa: PLC0415
        from misaki import en as misaki_en  # noqa: PLC0415
    finally:
        if previous_filelock is None:
            sys.modules.pop("filelock", None)
        else:
            sys.modules["filelock"] = previous_filelock

    resolved_private_dir = PREFLIGHT.assert_private_path(private_dir)
    resolved_private_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = KModel(config=str(artifacts["config"]), model=str(artifacts["model"]))
    pipeline = KPipeline(lang_code=BRITISH_LANG_CODE, model=model, repo_id=None)
    pipeline.g2p = misaki_en.G2P(
        trf=False,
        british=BRITISH_G2P,
        fallback=G2P_FALLBACK,
        unk=G2P_UNKNOWN_TOKEN_OUTPUT,
    )
    voice_tensor = torch.load(
        str(artifacts["voice"]), map_location="cpu", weights_only=True
    )
    prepared: list[tuple[Mapping[str, Any], Any, str]] = []
    for passage in passages:
        phonemes, tokens = pipeline.g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        passage_id = str(passage["passage_id"])
        phoneme_hash = PREFLIGHT.sha256_text(phonemes)
        if unresolved:
            raise TellTaleExecutorError(
                f"G2P fallback is disabled; unresolved tokens in {passage_id}: "
                f"{', '.join(unresolved)}"
            )
        if phoneme_hash != BRITISH_PHONEME_HASHES[passage_id]:
            raise TellTaleExecutorError(f"British G2P binding changed: {passage_id}")
        prepared.append((passage, tokens, phoneme_hash))

    samples: list[dict[str, Any]] = []
    for passage, tokens, phoneme_hash in prepared:
        passage_id = str(passage["passage_id"])
        chunks: list[Any] = []
        for item in pipeline.generate_from_tokens(
            tokens, voice=voice_tensor, speed=SPEED
        ):
            if item.audio is None:
                raise TellTaleExecutorError(f"Kokoro returned no audio: {passage_id}")
            chunks.append(item.audio.detach().cpu().numpy())
        if not chunks:
            raise TellTaleExecutorError(f"Kokoro returned zero chunks: {passage_id}")
        target = resolved_private_dir / f"{passage_id}.wav"
        sf.write(target, np.concatenate(chunks), SAMPLE_RATE, subtype="PCM_16")
        samples.append(
            {
                "passage_id": passage_id,
                "source_text_sha256": passage["text_sha256"],
                "characters": passage["characters"],
                "audio_path": str(target),
                "phoneme_sha256": phoneme_hash,
                "lang_code": BRITISH_LANG_CODE,
                "british_g2p": True,
                "g2p_fallback_enabled": False,
                **BASE.wav_metrics(target),
            }
        )
    return samples


def exact_execute_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/sprint1_tell_tale_kokoro_private_executor.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {PREFLIGHT.DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {PREFLIGHT.DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {PREFLIGHT.DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EXECUTION_EVIDENCE}"
    )


def executor_preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    artifact_dir: Path,
    whisper_cache_dir: Path,
    private_output_dir: Path,
    output: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    configure_base()
    payload = PREFLIGHT.build_preflight(
        asset_root=asset_root,
        slug=slug,
        profile=profile,
        artifact_dir=artifact_dir,
        whisper_cache_dir=whisper_cache_dir,
        private_output_dir=private_output_dir,
        output=output,
    )
    _chapter, passages = PREFLIGHT.controlled_source(asset_root, slug)
    fingerprint = PREFLIGHT.attempt_fingerprint(passages)
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise TellTaleExecutorError(
            f"attempt fingerprint changed: expected {EXPECTED_ATTEMPT_FINGERPRINT}, "
            f"observed {fingerprint}"
        )
    artifacts, _artifact_evidence = PREFLIGHT.validate_artifacts(
        artifact_dir, whisper_cache_dir
    )
    g2p = validate_british_g2p(passages)
    runtime_ready = bool(
        payload["runtime_evidence"]["pinned_execution_runtime_verified"]
    )
    payload.update(
        {
            "schema": "earnalism.kokoro.tell_tale_private_executor.v1",
            "status": (
                "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION"
                if runtime_ready
                else "CONTRACT_VALID_PINNED_EXECUTION_RUNTIME_REQUIRED"
            ),
            "go_no_go": (
                "GO_PRIVATE_REPRESENTATIVE_ONLY"
                if runtime_ready
                else "NO_GO_UNDER_CURRENT_INTERPRETER"
            ),
            "g2p_audit": g2p,
            "next_stage_contract": {
                "status": "EXECUTOR_CODE_REVIEWED_NOT_EXECUTED",
                "exact_execute_command": exact_execute_command(asset_root),
                "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
                "scope": "these four exact source-bound passages only",
                "lang_code": BRITISH_LANG_CODE,
                "british_g2p": True,
                "g2p_fallback_enabled": False,
                "asr_source_score_min": PREFLIGHT.ASR_SOURCE_SCORE_MIN,
                "asr_coverage_min": PREFLIGHT.ASR_COVERAGE_MIN,
                "ordered_content_integrity_required": True,
                "full_title_generation_allowed": False,
                "listening_qa_allowed_by_this_command": False,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
            },
            "safety": {
                **payload["safety"],
                "executor_implemented": True,
                "executor_run": False,
                "paid_tts_lock_inspected": False,
                "paid_tts_lock_touched": False,
            },
        }
    )
    return payload, passages, artifacts


def execute(
    *,
    payload: dict[str, Any],
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
    whisper_cache_dir: Path,
) -> tuple[int, dict[str, Any]]:
    """Run only local synthesis and strict objective ASR."""

    if payload["runtime_evidence"]["pinned_execution_runtime_verified"] is not True:
        raise TellTaleExecutorError("execution requires the exact pinned interpreter")
    if payload["engine"]["attempt_fingerprint"] != EXPECTED_ATTEMPT_FINGERPRINT:
        raise TellTaleExecutorError("execution fingerprint changed")
    artifact_hashes_before = {
        name: PREFLIGHT.sha256_file(path) for name, path in artifacts.items()
    }
    samples = synthesize_british(passages, artifacts, private_dir)
    if not all(item.get("objective_format_pass") is True for item in samples):
        asr: dict[str, Any] = {
            "status": "NOT_RUN_OBJECTIVE_AUDIO_FAILED",
            "reports": [],
        }
    else:
        configure_base()
        asr = BASE.run_asr(samples, passages, whisper_cache_dir)
    artifact_hashes_after = {
        name: PREFLIGHT.sha256_file(path) for name, path in artifacts.items()
    }
    if artifact_hashes_before != artifact_hashes_after:
        raise TellTaleExecutorError("local model, voice, or ASR artifact changed")
    expected_ids = [str(item["passage_id"]) for item in passages]
    observed_sample_ids = [str(item.get("passage_id") or "") for item in samples]
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    observed_report_ids = [str(item.get("passage_id") or "") for item in reports]
    passed = bool(
        len(samples) == len(expected_ids) == 4
        and observed_sample_ids == expected_ids
        and all(item.get("objective_format_pass") is True for item in samples)
        and asr.get("status") == "PASS"
        and len(reports) == len(expected_ids)
        and observed_report_ids == expected_ids
        and all(item.get("pass") is True for item in reports)
    )
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "CANONICAL_FRONT_COVER_MISSING",
        "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
        "PRODUCTION_ENDPOINT_NOT_RUN",
        "BROWSER_PLAYBACK_GATE_NOT_RUN",
    ]
    if not passed:
        blockers.insert(0, "REPRESENTATIVE_OBJECTIVE_OR_ASR_GATE_FAILED")
    updated = {
        **payload,
        "generated_at": PREFLIGHT.utc_now(),
        "status": (
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA"
            if passed
            else "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
        ),
        "next_stage_contract": {
            **payload["next_stage_contract"],
            "status": (
                "EXECUTOR_COMPLETED_OBJECTIVE_PASS"
                if passed
                else "EXECUTOR_COMPLETED_OBJECTIVE_FAIL_CLOSED"
            ),
        },
        "samples": samples,
        "asr": asr,
        "safety": {
            **payload["safety"],
            "executor_run": True,
            "audio_generated": True,
            "asr_run": asr.get("status") != "NOT_RUN_OBJECTIVE_AUDIO_FAILED",
            "artifact_hashes_before": artifact_hashes_before,
            "artifact_hashes_after": artifact_hashes_after,
            "artifact_hashes_unchanged": True,
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": blockers,
    }
    return (0 if passed else 4), updated


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--asset-root", type=Path, default=PREFLIGHT.ROOT)
    parser.add_argument("--artifact-dir", type=Path, default=PREFLIGHT.DEFAULT_ARTIFACT_DIR)
    parser.add_argument(
        "--whisper-cache-dir", type=Path, default=PREFLIGHT.DEFAULT_WHISPER_CACHE
    )
    parser.add_argument(
        "--private-output-dir", type=Path, default=PREFLIGHT.DEFAULT_PRIVATE_OUTPUT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_EXECUTION_EVIDENCE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.expanduser().resolve()
    try:
        payload, passages, artifacts = executor_preflight(
            asset_root=args.asset_root.expanduser().resolve(),
            slug=args.slug,
            profile=args.profile,
            artifact_dir=args.artifact_dir,
            whisper_cache_dir=args.whisper_cache_dir,
            private_output_dir=args.private_output_dir,
            output=output,
        )
        if args.execute:
            code, payload = execute(
                payload=payload,
                passages=passages,
                artifacts=artifacts,
                private_dir=PREFLIGHT.assert_private_path(args.private_output_dir),
                whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
            )
        else:
            code = 0
        PREFLIGHT.atomic_write_json(output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "output": str(output),
                    "attempt_fingerprint": payload["engine"]["attempt_fingerprint"],
                    "voice": payload["engine"]["voice"],
                    "lang_code": payload["next_stage_contract"]["lang_code"],
                    "g2p_fallback_enabled": False,
                    "provider_calls": 0,
                    "audio_generated": payload["safety"]["audio_generated"],
                    "paid_tts_lock_touched": False,
                    "publication_performed": False,
                    "blockers_to_release": payload["blockers_to_release"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return code
    except (
        TellTaleExecutorError,
        PREFLIGHT.TellTalePreflightError,
        BASE.KokoroTitlePilotError,
    ) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure_base()


if __name__ == "__main__":
    raise SystemExit(main())
