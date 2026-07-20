#!/usr/bin/env python3
"""Prepare The Masque of the Red Death's private Kokoro representative pilot.

The default preflight binds canonical catalog/manuscript truth, four gothic
risk passages, a locally hash-pinned British Kokoro voice, fallback-free G2P,
audio-hidden release truth, and the complete no-repeat history.  It performs
no synthesis, ASR, listening, upload, publication, or release-gate mutation.

``--execute`` is intentionally retained as the exact next-stage contract.  It
is limited to the four bound passages, writes only to a private path, and uses
British G2P for the British ``bf_emma`` voice.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_PATH = SCRIPT_DIR / "sprint1_kokoro_title_private_audition.py"
SPEC = importlib.util.spec_from_file_location("earnalism_kokoro_title_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load deterministic Kokoro executor: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


SLUG = "the-masque-of-the-red-death"
PROFILE = "masque-bf-emma-gothic-restraint-v1"
TITLE = "The Masque of the Red Death"
AUTHOR = "Edgar Allan Poe"
LANGUAGE = "en"

ORIGIN_SOURCE_SHA256 = "2264be57608b30c4af99db7b1d430accae5a7c4d9da738ac04651f7ef74bc266"
SANITIZED_SOURCE_SHA256 = "c517483495ef7266f533d077036a8e83bba53dc33cac60580cd895e757f637e3"
NORMALIZED_SOURCE_SHA256 = "a5057ddc09428de32f2b7531cd4a82de1c081fb840ae47c172f730b179c80ab8"
SOURCE_CHARACTERS = 13_885
NORMALIZED_SOURCE_CHARACTERS = 13_697
WORD_COUNT = 2_421

MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE = "bf_emma"
VOICE_SHA256 = "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701"
OTHER_LOCAL_KOKORO_VOICE_HASHES = {
    "af_bella": "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
    "af_sarah": "49bd364ea3be9eb3e9685e8f9a15448c4883112a7c0ff7ab139fa4088b08cef9",
}
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"

PIPELINE_LANG_CODE = "b"
G2P_BRITISH = True
SPEED = 0.94
RANDOM_SEED = 2026072001

PASSAGE_SPECS = (
    {
        "passage_id": "opening_plague_and_prospero",
        "start": "The “Red Death” had long devastated the country.",
        "end": "of half an hour.",
        "characters": 544,
        "sha256": "16e78152465fec59b1a45da95cad7eb8f7dffd7f0e845a372e3ff12e33809e48",
        "risk": "opening authority, plague imagery, long clauses, and Prince Prospero",
    },
    {
        "passage_id": "black_room_blood_light",
        "start": (
            "But in this chamber only, the colour of the windows failed to "
            "correspond with the decorations."
        ),
        "end": "the company bold enough to set foot within its precincts at all.",
        "characters": 1_009,
        "sha256": "4e908021ee2eb41c0897de247df3ec5b46f9f54206fef071ba7dc2dd00c19e0b",
        "risk": "British spelling, architectural vocabulary, colour imagery, and suspense",
    },
    {
        "passage_id": "ebony_clock_tension",
        "start": (
            "It was in this apartment, also, that there stood against the western "
            "wall, a gigantic clock of ebony."
        ),
        "end": "to harken to the sound;",
        "characters": 558,
        "sha256": "b23e8a225f916e6c56b810058cdf70f819a08f3ab155b71afcb1075f8d971227",
        "risk": "measured clock cadence, semicolon phrasing, and controlled dread",
    },
    {
        "passage_id": "final_confrontation_and_dominion",
        "start": (
            "There was a sharp cry—and the dagger dropped gleaming upon the sable "
            "carpet,"
        ),
        "end": "illimitable dominion over all.",
        "characters": 966,
        "sha256": "3156906cde350ac6a1964dd686fa7b92475390b0db3f5fd13d2fca277c3b2335",
        "risk": "climactic action, macabre vocabulary, repeated conjunctions, and final cadence",
    },
)
PASSAGE_CHARACTERS = 3_077

PRIOR_ATTEMPTS = (
    {
        "provider": "google",
        "voice": "en-GB-Studio-C",
        "speaking_rate": 0.94,
        "fingerprint": "6f561b31503df395",
        "scores": [8.4, 9.4, 9.4, 9.4],
        "minimum_confidence": 0.9,
        "fatal_flags": [],
        "status": "BLOCKED_LISTENING_QA",
    },
    {
        "provider": "google",
        "voice": "en-GB-Chirp3-HD-Achird",
        "speaking_rate": 0.9,
        "fingerprint": "c648177b25f4a6c4",
        "scores": [8.4, 8.4, 9.4, 9.4],
        "minimum_confidence": 0.9,
        "fatal_flags": [],
        "status": "BLOCKED_LISTENING_QA",
    },
)

# These are source-preserving lexicon bindings, not manuscript substitutions.
# They pin the intended British G2P output for high-risk proper names and
# gothic vocabulary while keeping fallback disabled.
PRONUNCIATION_OVERRIDES = {
    "Avatar": "ˈavətɑː",
    "Prospero": "pɹˈɒspəɹˌQ",
    "brazier": "bɹˈAzɪə",
    "candelabrum": "kˌandɪlˈɑːbɹəm",
    "cerements": "sˈɪəmᵊnts",
    "harken": "hˈɑːkən",
    "illimitable": "ɪlˈɪmɪtəbᵊl",
}
ASR_VOCABULARY_PROMPT = (
    "Canonical spellings: Edgar Allan Poe; Prince Prospero; Red Death; Avatar; "
    "candelabrum; brazier; harken; mummer; cerements; blood-bedewed; illimitable."
)
ASR_PROMPT_POLICY = {
    item["passage_id"]: "canonical_vocabulary_prompt" for item in PASSAGE_SPECS
}
SOURCE_EQUIVALENCE_POLICY = {item["passage_id"]: () for item in PASSAGE_SPECS}

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
    "internal/audiobook_lab/private_runs/kokoro/the-masque-of-the-red-death/"
    "f3ff3571-bf-emma-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-masque-of-the-red-death_kokoro_bf_emma_representative_preflight_v1.json"
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
    "the-masque-of-the-red-death_release_gate_evidence.json"
)


def validate_prior_attempts() -> None:
    """Require the two canonical failed fingerprints and no hidden third lane."""

    release = BASE.read_json(CANONICAL_RELEASE_EVIDENCE)
    if release.get("slug") != SLUG:
        raise BASE.KokoroTitlePilotError("canonical release evidence slug changed")
    observed_attempts = release.get("attempts")
    if observed_attempts != list(PRIOR_ATTEMPTS):
        raise BASE.KokoroTitlePilotError("canonical prior attempt evidence changed")

    registry = BASE.read_json(PROVIDER_FAILURE_REGISTRY)
    title_record = (registry.get("titles") or {}).get(SLUG)
    if not isinstance(title_record, dict):
        raise BASE.KokoroTitlePilotError("provider failure registry title is missing")
    expected_fingerprints = [str(item["fingerprint"]) for item in PRIOR_ATTEMPTS]
    if title_record.get("blocked_attempt_fingerprints") != expected_fingerprints:
        raise BASE.KokoroTitlePilotError("provider failure fingerprint history changed")
    if int(title_record.get("distinct_failed_family_count", -1)) != 2:
        raise BASE.KokoroTitlePilotError("provider failure family count changed")


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, list[dict[str, Any]]]:
    """Return four exact passages only while canonical truth remains unchanged."""

    if slug != SLUG:
        raise BASE.KokoroTitlePilotError(
            f"slug is not allowed by {PROFILE}: {slug}; only {SLUG} is permitted"
        )
    validate_prior_attempts()
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

    source_evidence = BASE.read_json(publication / "source_evidence.json")
    expected_source_evidence = {
        "slug": SLUG,
        "source_hash": ORIGIN_SOURCE_SHA256,
        "rights_basis": (
            "Edgar Allan Poe died 1849; first published 1842. Public domain in "
            "India and the U.S."
        ),
        "reader_facing_boilerplate_removed": True,
    }
    for key, expected in expected_source_evidence.items():
        if source_evidence.get(key) != expected:
            raise BASE.KokoroTitlePilotError(
                f"controlled source evidence changed for {key}: expected {expected!r}, "
                f"observed {source_evidence.get(key)!r}"
            )

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
        start = normalized.find(str(spec["start"]))
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


def synthesize_british(
    passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
) -> list[dict[str, Any]]:
    """Synthesize only the bound passages with British G2P and no fallback."""

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
    pipeline = KPipeline(lang_code=PIPELINE_LANG_CODE, model=model, repo_id=None)
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
        "internal/audiobook_lab/scripts/sprint1_masque_kokoro_private_audition.py "
        f"--execute --slug {SLUG} --profile {PROFILE} "
        f"--asset-root {asset_root} --artifact-dir {DEFAULT_ARTIFACT_DIR} "
        f"--whisper-cache-dir {DEFAULT_WHISPER_CACHE} "
        f"--private-output-dir {DEFAULT_PRIVATE_OUTPUT} "
        f"--output {DEFAULT_EVIDENCE} --paid-lock {DEFAULT_PAID_LOCK}"
    )


def masque_preflight(**kwargs: Any):
    payload, passages, artifacts = _BASE_PREFLIGHT(**kwargs)
    risks = {str(item["passage_id"]): str(item["risk"]) for item in PASSAGE_SPECS}
    for passage in payload["source"]["passages"]:
        passage["risk"] = risks[str(passage["passage_id"])]
    payload.update(
        {
            "schema": "earnalism.kokoro.masque_private_representative.v1",
            "source": {
                **payload["source"],
                "origin_source_sha256": ORIGIN_SOURCE_SHA256,
                "sanitized_source_sha256": SANITIZED_SOURCE_SHA256,
                "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
                "word_count": WORD_COUNT,
                "rights_basis_bound": True,
            },
            "catalog_truth": {
                "reader_status": "reader_ready",
                "publication_status": "live",
                "audiobook_enabled": False,
                "audio_enabled": False,
                "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            },
            "prior_attempts": list(PRIOR_ATTEMPTS),
            "prior_attempt_audit": {
                "canonical_release_evidence": str(CANONICAL_RELEASE_EVIDENCE),
                "provider_failure_registry": str(PROVIDER_FAILURE_REGISTRY),
                "failed_family_count": 2,
                "kokoro_attempt_found_for_title": False,
                "validated": True,
            },
            "no_repeat_history": {
                "inspected_paths": [
                    str(path) for path in BASE.NO_REPEAT_FILES if path.is_file()
                ],
                "prior_fingerprints": [
                    str(item["fingerprint"]) for item in PRIOR_ATTEMPTS
                ],
                "exact_current_fingerprint_found": False,
                "fail_closed_on_completed_fingerprint": True,
            },
            "voice_selection": {
                "selected_voice": VOICE,
                "selected_voice_sha256": VOICE_SHA256,
                "selection_reason": (
                    "already-local British voice selected for restrained gothic "
                    "narration; no prior Masque Kokoro attempt exists"
                ),
                "pipeline_lang_code": PIPELINE_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "different_from_prior_google_provider_voice_families": True,
                "different_from_other_local_kokoro_voice_assets": all(
                    VOICE_SHA256 != digest
                    for digest in OTHER_LOCAL_KOKORO_VOICE_HASHES.values()
                ),
                "selected_asset_is_locally_installed_and_hash_verified": True,
                "selected_asset_source_repo": BASE.MODEL_REPO,
                "selected_asset_source_revision": MODEL_REVISION,
            },
            "rights": {
                "source_text_rights_basis": (
                    "Edgar Allan Poe died 1849; first published 1842. Public "
                    "domain in India and the U.S."
                ),
                "model_and_voicepack_license": "Apache-2.0",
                "private_audition_allowed": True,
                "title_scoped_production_risk_acceptance_bound": False,
                "production_release_approved": False,
                "public_disclosure_required_if_later_approved": "AI voice",
            },
            "next_stage_contract": {
                "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
                "exact_execute_command": _exact_command(Path(kwargs["asset_root"])),
                "execution_performed_by_this_preflight": False,
                "scope": "four exact source-bound passages only",
                "pipeline_lang_code": PIPELINE_LANG_CODE,
                "g2p_british": G2P_BRITISH,
                "g2p_fallback_enabled": False,
                "browser_or_system_speech_fallback": False,
                "local_synthesis_provider_calls": 0,
                "asr_must_pass_before_listening_qa": True,
                "full_title_generation_allowed": False,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
                "fail_closed_on": [
                    "catalog_source_or_rights_hash_change",
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
    payload["engine"]["known_failed_fingerprint_count"] = len(PRIOR_ATTEMPTS)
    payload["engine"]["pipeline_lang_code"] = PIPELINE_LANG_CODE
    payload["engine"]["g2p_british"] = G2P_BRITISH
    payload["blockers_to_release"] = [
        "REPRESENTATIVE_AUDIO_NOT_GENERATED",
        "REPRESENTATIVE_ASR_NOT_RUN",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "MASQUE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    return payload, passages, artifacts


def masque_execute(**kwargs: Any):
    code, payload = _BASE_EXECUTE(**kwargs)
    payload["blockers_to_release"] = [
        blocker.replace(
            "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "MASQUE_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        )
        for blocker in payload["blockers_to_release"]
        if blocker != "OWNER_10_TARGET_NOT_VERIFIED"
    ]
    return code, payload


def configure_base() -> None:
    BASE.ALLOWED_SLUG = SLUG
    BASE.PROFILE_ID = PROFILE
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.EXPECTED_SOURCE_SHA256 = SANITIZED_SOURCE_SHA256
    BASE.EXPECTED_SOURCE_CHARACTERS = SOURCE_CHARACTERS
    BASE.PASSAGE_SPECS = PASSAGE_SPECS
    BASE.EXPECTED_PASSAGE_HASHES = tuple(
        str(item["sha256"]) for item in PASSAGE_SPECS
    )
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
    BASE.KNOWN_GIFT_FAILED_FINGERPRINTS = frozenset(
        str(item["fingerprint"]) for item in PRIOR_ATTEMPTS
    )
    BASE.NO_REPEAT_FILES = tuple(
        dict.fromkeys(
            (*BASE.NO_REPEAT_FILES, PROVIDER_FAILURE_REGISTRY, CANONICAL_RELEASE_EVIDENCE)
        )
    )
    BASE.controlled_source = controlled_source
    BASE.synthesize = synthesize_british
    BASE.preflight = masque_preflight
    BASE.execute = masque_execute


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
