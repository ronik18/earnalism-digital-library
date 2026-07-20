#!/usr/bin/env python3
"""Preflight one materially different private Gift of the Magi audition.

The default path is dry-run only: it binds the canonical controlled source,
four exact representative passages, the locally installed ``bf_emma`` voice,
the pinned Kokoro/Whisper artifacts, British fallback-free G2P, completed
attempt history, audio-hidden catalog truth, and a private-only output path.

``--execute`` is deliberately separate.  It remains limited to the same four
private passages and cannot upload, publish, or mutate release truth.  This
module's tests and checked-in preflight never invoke that mode.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("earnalism_gift_emma_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
LANGUAGE = "en"
PROFILE = "gift-bf-emma-british-literary-warmth-v1"

ORIGIN_SOURCE_SHA256 = "490b76d444db0d952f5286f60c4ec2834ab91731d47e42dc94a3639d9183d295"
SANITIZED_SOURCE_SHA256 = "be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e"
NORMALIZED_SOURCE_SHA256 = "f32ebf1df2826126eac28341a0dba111be5a734828d9f7b6fffb41d9b95bfe27"
SOURCE_CHARACTERS = 11_298
NORMALIZED_SOURCE_CHARACTERS = 11_122
WORD_COUNT = 2_109

MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "bf_emma"
VOICE_SHA256 = "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
PREVIOUS_VOICE = "af_bella"
PREVIOUS_VOICE_SHA256 = "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

KOKORO_LANG_CODE = "b"
G2P_BRITISH = True
SPEED = 0.98
RANDOM_SEED = 2026072001

PASSAGE_SPECS = tuple(
    {
        **item,
        "risk": risk,
    }
    for item, risk in zip(
        BASE.PASSAGE_SPECS,
        (
            "opening cadence, currency, repetition, and quiet disappointment",
            "Madame Sofronie, source dialect, bargaining, and rapid dialogue",
            "intimate dialogue, emotional restraint, and precise speaker turns",
            "magi pronunciation, long literary syntax, and reflective final cadence",
        ),
    )
)
PASSAGE_CHARACTERS = BASE.EXPECTED_PASSAGE_CHARACTERS
PRONUNCIATION_OVERRIDES = dict(BASE.PRONUNCIATION_OVERRIDES)
ASR_VOCABULARY_PROMPT = BASE.ASR_VOCABULARY_PROMPT
ASR_PROMPT_POLICY = dict(BASE.ASR_PROMPT_POLICY)
SOURCE_EQUIVALENCE_POLICY = dict(BASE.SOURCE_EQUIVALENCE_POLICY)

# Every known failed or completed Gift attempt is retained as explicit
# no-repeat evidence.  Fingerprints from ASR/listening stages are included to
# make the historical binding complete even though their contracts differ.
PRIOR_ATTEMPTS = (
    {"stage": "google_candidate", "fingerprint": "716473a1705c4aa3e6ea718f2c117668875215ac368540f6402b4dab47932f43", "status": "FAILED"},
    {"stage": "google_candidate", "fingerprint": "75a6fbc43a06e181677d1f4a2afc2508416d7f0b137d325f79948df48a04fabe", "status": "FAILED"},
    {"stage": "google_candidate", "fingerprint": "cda6b9c871c9751f8ade43db4ec0c71b865c9ac0ba5ab5a63a49c6fbf2b13ddd", "status": "FAILED"},
    {"stage": "google_candidate", "fingerprint": "cf9b59637d5ba9180a691867ac5d6574dac6458a96344389dd4d8606867d1595", "status": "FAILED"},
    {"stage": "google_candidate", "fingerprint": "018bef83ba81b9902246be7a164bdda4027dc5dafe8efad03d724272c3b09e93", "status": "FAILED"},
    {"stage": "kokoro_af_bella_representative", "fingerprint": "bf5ff8b24d23e4ae912d332b247d26d5efb60eeb0b91ebad0bc179e40a7ea015", "status": "COMPLETED"},
    {"stage": "kokoro_af_bella_representative_asr", "fingerprint": "1b932d7d1193947aad72e51cc2deba889a4c09468b21618d02b21b38db124755", "status": "COMPLETED"},
    {"stage": "kokoro_af_bella_representative_listening", "fingerprint": "1ef9100b249fae4540df00cad7eba5d03dc29fa6008f3eb393ec3163b243fdf4", "status": "COMPLETED"},
    {"stage": "kokoro_af_bella_full_title", "fingerprint": "c28f5c70373854feed9009c5cb4dd0789dd7c2d09a5451e71d7fa41723283039", "status": "FAILED_CLOSED"},
    {"stage": "kokoro_af_bella_full_title_initial_asr", "fingerprint": "4343dbb64e9de4b741b5f0192b28b562e2b1530064ad7e7f3fc3a11382dbc0c3", "status": "FAILED"},
    {"stage": "kokoro_af_bella_full_title_asr_repair", "fingerprint": "b05c6392075ace4d50046f6f266ba20e04e48e68038755a1950b077b8ca27af9", "status": "FAILED_CLOSED"},
)
PRIOR_FINGERPRINTS = frozenset(str(item["fingerprint"]) for item in PRIOR_ATTEMPTS)

DEFAULT_ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/artifacts"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-gift-of-the-magi/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_bf_emma_representative_preflight_v1.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
PROVIDER_FAILURE_REGISTRY = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json"
)
CANONICAL_RELEASE_EVIDENCE = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_release_gate_evidence.json"
)
AF_BELLA_REPRESENTATIVE_EVIDENCE = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_representative_v1.json"
)
AF_BELLA_FULL_TITLE_EVIDENCE = (
    BASE.ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_full_title_asr_repair_v1.json"
)


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, list[dict[str, Any]]]:
    """Return four exact passages only when catalog/source truth is unchanged."""

    if slug != SLUG:
        raise BASE.KokoroTitlePilotError(
            f"slug is not allowed by {PROFILE}: {slug}; only {SLUG} is permitted"
        )
    publication = asset_root / "data/controlled_publications" / SLUG
    book = BASE.read_json(publication / "public_book.json")
    expected_book = {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "readerStatus": "reader_ready",
        "publicationStatus": "live",
        "audiobook_enabled": False,
        "audio_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }
    for key, expected in expected_book.items():
        if book.get(key) != expected:
            raise BASE.KokoroTitlePilotError(
                f"controlled catalog truth changed for {key}: expected {expected!r}, "
                f"observed {book.get(key)!r}"
            )

    approval = BASE.read_json(publication / "approval_evidence.json")
    if approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_NOT_APPROVED":
        raise BASE.KokoroTitlePilotError("controlled audio-hidden approval truth changed")
    if approval.get("audiobook_enabled") is not False:
        raise BASE.KokoroTitlePilotError("controlled audiobook approval truth changed")

    chapter_path = publication / "chapters/chapter-001.json"
    chapter = BASE.read_json(chapter_path)
    expected_chapter = {
        "id": "chapter-001",
        "bookSlug": SLUG,
        "title": TITLE,
        "language": LANGUAGE,
        "processing_status": "ready",
        "processing_warnings": [],
        "sourceSha256": ORIGIN_SOURCE_SHA256,
        "sanitizedSha256": SANITIZED_SOURCE_SHA256,
        "word_count": WORD_COUNT,
    }
    for key, expected in expected_chapter.items():
        if chapter.get(key) != expected:
            raise BASE.KokoroTitlePilotError(
                f"controlled chapter truth changed for {key}: expected {expected!r}, "
                f"observed {chapter.get(key)!r}"
            )
    manuscript = chapter.get("content")
    if not isinstance(manuscript, str):
        raise BASE.KokoroTitlePilotError("controlled manuscript is missing")
    if len(manuscript) != SOURCE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("controlled source character count changed")
    if BASE.sha256_text(manuscript) != SANITIZED_SOURCE_SHA256:
        raise BASE.KokoroTitlePilotError("controlled source bytes changed")
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    if len(normalized) != NORMALIZED_SOURCE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("normalized source character count changed")
    if BASE.sha256_text(normalized) != NORMALIZED_SOURCE_SHA256:
        raise BASE.KokoroTitlePilotError("normalized source hash changed")

    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start_marker = spec["start"]
        start = 0 if start_marker is None else normalized.find(str(start_marker))
        end_start = normalized.find(str(spec["end"]), start)
        if start < 0 or end_start < 0:
            raise BASE.KokoroTitlePilotError(
                f"canonical passage markers changed: {spec['passage_id']}"
            )
        end = end_start + len(str(spec["end"]))
        text = normalized[start:end]
        if len(text) != spec["characters"] or BASE.sha256_text(text) != spec["sha256"]:
            raise BASE.KokoroTitlePilotError(
                f"canonical passage binding changed: {spec['passage_id']}"
            )
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "text": text,
                "characters": len(text),
                "text_sha256": spec["sha256"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise BASE.KokoroTitlePilotError("bounded passage character total changed")
    return chapter_path, passages


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    """Hash every source, runtime, voice, locale, and preparation decision."""

    contract = {
        "contract": "earnalism.kokoro.gift_bf_emma_representative.v1",
        "profile": PROFILE,
        "slug": SLUG,
        "source_sha256": SANITIZED_SOURCE_SHA256,
        "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
        "passage_hashes": [str(item["text_sha256"]) for item in passages],
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "config_sha256": CONFIG_SHA256,
        "voice": VOICE,
        "voice_sha256": VOICE_SHA256,
        "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
        "kokoro_lang_code": KOKORO_LANG_CODE,
        "g2p_british": G2P_BRITISH,
        "g2p_fallback": None,
        "whisper_model": BASE.WHISPER_MODEL,
        "whisper_sha256": WHISPER_SHA256,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "prior_fingerprints": sorted(PRIOR_FINGERPRINTS),
        "scope": "four_passage_private_representative_pilot",
    }
    return BASE.sha256_bytes(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def validate_g2p_contract(
    passages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove every source token resolves with British fallback-free G2P."""

    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(
        trf=False,
        british=G2P_BRITISH,
        fallback=None,
        unk="",
    )
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
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
        if unresolved:
            raise BASE.KokoroTitlePilotError(
                "G2P fallback is disabled; unresolved tokens in "
                f"{passage['passage_id']}: {', '.join(unresolved)}"
            )
        reports.append(
            {
                "passage_id": passage["passage_id"],
                "source_text_sha256": passage["text_sha256"],
                "token_count": len(tokens),
                "phoneme_sha256": BASE.sha256_text(str(phonemes or "")),
                "unresolved_tokens": [],
            }
        )
    return {
        "status": "PASS",
        "kokoro_lang_code": KOKORO_LANG_CODE,
        "british": G2P_BRITISH,
        "fallback": None,
        "unknown_token_output": "",
        "all_source_tokens_resolved": True,
        "reports": reports,
    }


def synthesize_british(
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
) -> list[dict[str, Any]]:
    """The explicit later execution path, pinned to British G2P and bf_emma."""

    previous_filelock, _stub = BASE._install_local_filelock_stub()
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

    private_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = KModel(config=str(artifacts["config"]), model=str(artifacts["model"]))
    pipeline = KPipeline(lang_code=KOKORO_LANG_CODE, model=model, repo_id=None)
    pipeline.g2p = misaki_en.G2P(
        trf=False, british=G2P_BRITISH, fallback=None, unk=""
    )
    pipeline.g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    pipeline.g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    voice_tensor = torch.load(
        str(artifacts["voice"]), map_location="cpu", weights_only=True
    )
    prepared: list[tuple[Mapping[str, Any], Any]] = []
    for passage in passages:
        _phonemes, tokens = pipeline.g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        if unresolved:
            raise BASE.KokoroTitlePilotError(
                "G2P fallback is disabled; unresolved tokens in "
                f"{passage['passage_id']}: {', '.join(unresolved)}"
            )
        prepared.append((passage, tokens))

    results: list[dict[str, Any]] = []
    for passage, tokens in prepared:
        chunks: list[Any] = []
        phonemes: list[str] = []
        for item in pipeline.generate_from_tokens(
            tokens, voice=voice_tensor, speed=SPEED
        ):
            if item.audio is None:
                raise BASE.KokoroTitlePilotError(
                    f"Kokoro returned no audio: {passage['passage_id']}"
                )
            chunks.append(item.audio.detach().cpu().numpy())
            phonemes.append(str(item.phonemes or ""))
        if not chunks:
            raise BASE.KokoroTitlePilotError(
                f"Kokoro returned zero chunks: {passage['passage_id']}"
            )
        target = private_dir / f"{passage['passage_id']}.wav"
        sf.write(target, np.concatenate(chunks), BASE.SAMPLE_RATE, subtype="PCM_16")
        results.append(
            {
                "passage_id": passage["passage_id"],
                "source_text_sha256": passage["text_sha256"],
                "characters": passage["characters"],
                "audio_path": str(target),
                "phoneme_sha256": BASE.sha256_text("".join(phonemes)),
                "kokoro_lang_code": KOKORO_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "g2p_fallback_enabled": False,
                **BASE.wav_metrics(target),
            }
        )
    return results


_BASE_PREFLIGHT = BASE.preflight
_BASE_EXECUTE = BASE.execute


def _exact_command(asset_root: Path) -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python "
        "internal/audiobook_lab/scripts/sprint1_gift_bf_emma_private_preflight.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def gift_emma_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    g2p_evidence = validate_g2p_contract(passages)
    risks = {str(item["passage_id"]): str(item["risk"]) for item in PASSAGE_SPECS}
    for passage in payload["source"]["passages"]:
        passage["risk"] = risks[str(passage["passage_id"])]
    current_fingerprint = str(payload["engine"]["attempt_fingerprint"])
    if current_fingerprint in PRIOR_FINGERPRINTS:
        raise BASE.KokoroTitlePilotError("new bf_emma fingerprint repeats prior Gift work")
    payload.update(
        {
            "schema": "earnalism.kokoro.gift_bf_emma_private_preflight.v1",
            "source": {
                **payload["source"],
                "origin_source_sha256": ORIGIN_SOURCE_SHA256,
                "sanitized_source_sha256": SANITIZED_SOURCE_SHA256,
                "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
                "normalized_characters": NORMALIZED_SOURCE_CHARACTERS,
                "word_count": WORD_COUNT,
            },
            "catalog_truth": {
                "reader_status": "reader_ready",
                "publication_status": "live",
                "audiobook_enabled": False,
                "audio_enabled": False,
                "generate_audiobook": False,
                "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            },
            "g2p_preflight": g2p_evidence,
            "prior_attempts": list(PRIOR_ATTEMPTS),
            "no_repeat_history": {
                "inspected_paths": [
                    str(path) for path in BASE.NO_REPEAT_FILES if path.is_file()
                ],
                "prior_fingerprints": sorted(PRIOR_FINGERPRINTS),
                "exact_current_fingerprint_found": False,
                "fail_closed_on_completed_fingerprint": True,
            },
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "previous_voice": PREVIOUS_VOICE,
                "previous_voice_sha256": PREVIOUS_VOICE_SHA256,
                "voice_tensor_is_materially_different": VOICE_SHA256
                != PREVIOUS_VOICE_SHA256,
                "selected_asset_is_locally_installed_and_hash_verified": True,
                "locale": "British English",
                "kokoro_lang_code": KOKORO_LANG_CODE,
                "g2p_british": G2P_BRITISH,
            },
            "rights": {
                "model_and_voicepack_license": "Apache-2.0",
                "private_audition_allowed": True,
                "title_scoped_production_risk_acceptance_bound": False,
                "production_release_approved": False,
                "public_disclosure_required_if_later_approved": "AI voice",
            },
            "decision": {
                "representative_execution": "GO",
                "reason": (
                    "Canonical source, exact passages, materially different local "
                    "voice, pinned artifacts/runtime, British fallback-free G2P, "
                    "private path, audio-hidden truth, and no-repeat checks pass."
                ),
                "release": "NO_GO",
            },
            "next_stage_contract": {
                "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
                "exact_execute_command": _exact_command(Path(kwargs["asset_root"])),
                "execution_performed_by_this_preflight": False,
                "scope": "four exact source-bound passages only",
                "kokoro_lang_code": KOKORO_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "g2p_fallback_enabled": False,
                "browser_or_system_speech_fallback": False,
                "local_synthesis_provider_calls": 0,
                "estimated_provider_cost_usd": 0.0,
                "asr_must_pass_before_listening_qa": True,
                "full_title_generation_allowed": False,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
                "fail_closed_on": [
                    "catalog_or_source_hash_change",
                    "passage_hash_change",
                    "artifact_or_runtime_hash_change",
                    "unresolved_g2p_token_with_fallback_disabled",
                    "repeated_attempt_fingerprint",
                    "non_private_output_path",
                    "asr_source_score_below_9.7",
                    "missing_first_or_last_words",
                    "missing_duplicated_reordered_or_unexpected_content",
                ],
            },
        }
    )
    payload["engine"].update(
        {
            "known_failed_fingerprint_count": len(PRIOR_FINGERPRINTS),
            "kokoro_lang_code": KOKORO_LANG_CODE,
            "g2p_british": G2P_BRITISH,
        }
    )
    payload["safety"].update(
        {
            "execution_performed_by_this_preflight": False,
            "provider_calls": 0,
            "estimated_tts_provider_cost_usd": 0.0,
            "audio_generated": False,
            "asr_run": False,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        }
    )
    payload["blockers_to_release"] = [
        "REPRESENTATIVE_AUDIO_NOT_GENERATED",
        "REPRESENTATIVE_ASR_NOT_RUN",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    return payload, passages, artifacts


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = SANITIZED_SOURCE_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(str(item["sha256"]) for item in PASSAGE_SPECS)
    BASE.EXPECTED_PASSAGE_CHARACTERS = PASSAGE_CHARACTERS
    BASE.MODEL_REVISION = MODEL_REVISION
    BASE.MODEL_SHA256 = MODEL_SHA256
    BASE.CONFIG_SHA256 = CONFIG_SHA256
    BASE.VOICE = VOICE
    BASE.VOICE_FILENAME = f"voices/{VOICE}.pt"
    BASE.VOICE_SHA256 = VOICE_SHA256
    BASE.WHISPER_SHA256 = WHISPER_SHA256
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.ASR_VOCABULARY_PROMPT = ASR_VOCABULARY_PROMPT
    BASE.ASR_PROMPT_POLICY = ASR_PROMPT_POLICY
    BASE.SOURCE_EQUIVALENCE_POLICY = SOURCE_EQUIVALENCE_POLICY
    BASE.EXPECTED_EXISTING_AUDIO_HASHES = {}
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = PRIOR_FINGERPRINTS
    BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (
                *BASE.NO_REPEAT_FILES,
                PROVIDER_FAILURE_REGISTRY,
                CANONICAL_RELEASE_EVIDENCE,
                AF_BELLA_REPRESENTATIVE_EVIDENCE,
                AF_BELLA_FULL_TITLE_EVIDENCE,
            )
        )
    )
    BASE.controlled_source = controlled_source
    BASE.attempt_fingerprint = attempt_fingerprint
    BASE.synthesize = synthesize_british
    BASE.preflight = gift_emma_preflight
    BASE.execute = _BASE_EXECUTE


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    defaults: tuple[tuple[str, Path], ...] = (
        ("--asset-root", BASE.ROOT),
        ("--artifact-dir", DEFAULT_ARTIFACT_DIR),
        ("--whisper-cache-dir", DEFAULT_WHISPER_CACHE),
        ("--private-output-dir", DEFAULT_PRIVATE_OUTPUT),
        ("--output", DEFAULT_EVIDENCE),
        ("--paid-lock", DEFAULT_PAID_LOCK),
    )
    for option, value in defaults:
        if option not in options:
            args.extend((option, str(value)))
    if "--slug" not in options:
        args.extend(("--slug", SLUG))
    if "--profile" not in options:
        args.extend(("--profile", PROFILE))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_base()
    return int(BASE.main(expand_defaults(argv)))


configure_base()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
