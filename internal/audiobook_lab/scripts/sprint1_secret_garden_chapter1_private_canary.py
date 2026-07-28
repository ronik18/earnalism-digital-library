#!/usr/bin/env python3
"""Generate and objectively verify Secret Garden chapter 1 as a full-run canary.

This is the first resumable checkpoint of the one authorized private full-title
run. It uses the representative-winning Kokoro/bf_emma profile, 18 lossless
sentence-bound sections, local Whisper ASR, and measured section sync. It
cannot call a listening provider, upload, publish, or mutate release truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name(
    "sprint1_gift_kokoro_full_title_private_qa.py"
)
CORE_SPEC = importlib.util.spec_from_file_location(
    "kokoro_full_title_objective_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load full-title objective core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name(
    "sprint1_secret_garden_kokoro_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "secret_garden_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Secret Garden profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SLUG = "the-secret-garden"
TITLE = "The Secret Garden"
AUTHOR = "Frances Hodgson Burnett"
LANGUAGE = "eng"
PROFILE_ID = "secret-garden-chapter-001-bf-emma-canary-v1"
SCHEMA = "earnalism.secret_garden_chapter1_private_canary.v1"
CHAPTER_ID = "chapter-001"
FULL_SOURCE_SHA256 = (
    "436678ed945b234545d12dc84c7f1edda9549a6cf99ac3b12fb459b42e6c1b79"
)
FULL_SOURCE_CHARACTERS = 10_188
NORMALIZED_SOURCE_SHA256 = (
    "270f3e4f34c0bca6942d92c3752fd977fd28d24dc8bfd1b04040f5997bf8bf9d"
)
NORMALIZED_SOURCE_CHARACTERS = 10_033
NORMALIZED_SOURCE_WORDS = 1_902
SOURCE_RIGHTS_BASIS = (
    "Public domain in India based on life plus 60 years; public domain in the "
    "U.S. based on original publication before 1931."
)

REPRESENTATIVE_EVIDENCE_SHA256 = (
    "41da29ba7dfdae707d4d9def4905bfee9b5d38797a00787c00fbc5a83ff59bcb"
)
REPRESENTATIVE_LISTENING_SHA256 = (
    "024a34ba1fb42152ee1761c25558c841e4136f6d2b39bdd7c8f363514e1b07c3"
)
REPRESENTATIVE_ATTEMPT_FINGERPRINT = (
    "f849e64889b7a614bce6eb2ad3c0b5630424cf5d338e6a1b9d216318842aceff"
)
REPRESENTATIVE_LISTENING_FINGERPRINT = (
    "86739b15acc542a390cef1e878bc5d5978914b4dee2a99f2581b65602cbc565d"
)
REPRESENTATIVE_ASR_FINGERPRINT = (
    "d73039f782de602ae41da7eda483a58c256a8b1be177d3b5aac5e848d89e707f"
)

SECTION_WORD_COUNTS = (
    110,
    150,
    108,
    106,
    96,
    130,
    95,
    103,
    107,
    99,
    95,
    108,
    104,
    105,
    95,
    109,
    156,
    26,
)
SECTION_HASHES = (
    "d59d39c7be7ec53b26c6a3fea7caf2ba8ce99e5b8ac1f983b01371e081e2114b",
    "3ba4dfb547ac6d57fa9cb288a1b6937e830a57d180c576e80441b246a3b642ec",
    "dda1d16df4a352ec6ab1fc0acb697183b8084d43f7451d8f2133dcb1527dee7c",
    "ddb779403e00a1485b102d55c8a971364b1f53b0e608630b46d7abc2c7bf53ce",
    "fba21b6e81755a75912ca78fd452389cde98f7c6b985b3a0c97bbe03cddad2fd",
    "e8977e9bc8617d93fe1599a92b19354f7242d398fc044b5c69c4f89000706135",
    "1ae957455030c72483b043e6ec0b1c8be402942264e885e062ec6ab708bb7bdf",
    "c0cf7de872d715715920fb93b7dd6ccdfc4ed60c00f2575c381beb2f343d7a88",
    "71f45772aa5aa0391a0b55096d3e3d8db65846a021a704a0fb43bf14d0d5ec61",
    "0c5cf34f873835e17e64a42da11d332f333e5044a2ee846e1f5f9da490a29858",
    "b64ddb0a8442f5f6345f16c65b0f88fc7831dac28a8831a035508cd16e55baeb",
    "9bc589b1ea3404ea0cfdf6bb4eb10815e3a2979af6dde6ecaa9a5896adae1816",
    "0b7dbd9a0f7765a498bb5365d24f4fb64411a29f99b3e0d864746052fdaa54c2",
    "369aa3d381f397ae767e0ab31c55ada0cab86ad205f47c0a7e2426878e3c4fdb",
    "5a9ed67b037e2abaea48b29dd0a8c3b43c2944ac1e5ae89d14d3bf9809401061",
    "4587944a01ef13c00922e61e978decb256814081458f6b1b77d5cd915b8b44ca",
    "74fa31ed268d8c32a88f491d1a5b8d50d1eccc799d2da7bf8c3fbbaa2e89ac71",
    "29193feafd5c40ec26c20dec27e23b6b5cbbcdc0adfc2c410da3ece63bee9a69",
)

PRONUNCIATION_OVERRIDES = dict(PROFILE.PRONUNCIATION_OVERRIDES)
PRONUNCIATION_OVERRIDES.update(
    {
        "Ayah": "ˈaɪə",
        "Sahib": "sˈɑːhɪb",
        "Mem": "mˈɛm",
        "Missie": "mˈɪsi",
        "Saidie": "sˈeɪdi",
    }
)
CANONICAL_PROPER_NAMES = (
    "Mary",
    "Lennox",
    "Misselthwaite",
    "Ayah",
    "Sahib",
    "Saidie",
)
G2P_SETTINGS = {
    "language_code": "b",
    "transformer": False,
    "british": True,
    "fallback": None,
    "unknown_token": "",
}
ASR_SETTINGS = {
    "language": "en",
    "task": "transcribe",
    "fp16": False,
    "temperature": 0,
    "condition_on_previous_text": False,
    "initial_prompt": None,
    "word_timestamps": True,
    "beam_size": 2,
    "patience": 1,
    "hallucination_silence_threshold": 0.5,
}
SOURCE_EQUIVALENCE_POLICY = {
    "gray": "grey",
}

DEFAULT_REPRESENTATIVE_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_LISTENING_EVIDENCE = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_bf_emma_listening_qa_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_chapter1_bf_emma_private_canary_v1.json"
)
DEFAULT_PRIVATE_DIR = Path(tempfile.gettempdir()) / (
    "earnalism-secret-garden-chapter1-bf-emma-v1"
)
DEFAULT_ARTIFACT_DIR = PROFILE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK


def controlled_source(asset_root: Path):
    publication = asset_root / "data/controlled_publications" / SLUG
    book = CORE.read_json(publication / "public_book.json")
    source = CORE.read_json(publication / "source_evidence.json")
    approval = CORE.read_json(publication / "approval_evidence.json")
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "isLive": True,
        "isPublic": True,
        "qa_status": "QA_PASSED",
        "audio_enabled": False,
        "audiobook_enabled": False,
    }.items():
        CORE.require(
            book.get(key) == expected,
            f"controlled book truth changed for {key}",
        )
    CORE.require(
        source.get("rights_basis") == SOURCE_RIGHTS_BASIS,
        "source rights basis changed",
    )
    CORE.require(
        source.get("source_license") == "Public domain",
        "source license changed",
    )
    CORE.require(
        approval.get("audio_public_release")
        == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "audio release truth changed",
    )
    chapter_path = publication / "chapters" / f"{CHAPTER_ID}.json"
    chapter = CORE.read_json(chapter_path)
    manuscript = str(chapter.get("content") or "")
    for key, expected in {
        "id": CHAPTER_ID,
        "bookSlug": SLUG,
        "processing_status": "ready",
        "processing_warnings": [],
        "sanitizedSha256": FULL_SOURCE_SHA256,
    }.items():
        CORE.require(
            chapter.get(key) == expected,
            f"controlled chapter truth changed for {key}",
        )
    CORE.require(
        CORE.sha256_text(manuscript) == FULL_SOURCE_SHA256,
        "controlled chapter bytes changed",
    )
    CORE.require(
        len(manuscript) == FULL_SOURCE_CHARACTERS,
        "controlled chapter length changed",
    )
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    CORE.require(
        CORE.sha256_text(normalized) == NORMALIZED_SOURCE_SHA256,
        "normalized chapter hash changed",
    )
    CORE.require(
        len(normalized) == NORMALIZED_SOURCE_CHARACTERS,
        "normalized chapter length changed",
    )
    words = normalized.split(" ")
    CORE.require(
        len(words) == NORMALIZED_SOURCE_WORDS,
        "normalized chapter word count changed",
    )
    CORE.require(
        sum(SECTION_WORD_COUNTS) == len(words),
        "section layout no longer covers chapter",
    )
    sections: list[dict[str, Any]] = []
    cursor = 0
    for index, (count, expected_hash) in enumerate(
        zip(SECTION_WORD_COUNTS, SECTION_HASHES), 1
    ):
        text = " ".join(words[cursor : cursor + count])
        cursor += count
        CORE.require(
            CORE.sha256_text(text) == expected_hash,
            f"section-{index:03d} hash changed",
        )
        CORE.require(
            bool(re.search(r"[.!?][\"”’']*$", text)),
            f"section-{index:03d} is not sentence-bound",
        )
        sections.append(
            {
                "passage_id": f"{CHAPTER_ID}-section-{index:03d}",
                "section_index": index,
                "text": text,
                "text_sha256": expected_hash,
                "characters": len(text),
                "word_count": count,
            }
        )
    CORE.require(
        " ".join(item["text"] for item in sections) == normalized,
        "chapter sections are not lossless",
    )
    return chapter_path, normalized, sections


def validate_predecessor_evidence(
    representative_path: Path, listening_path: Path
) -> dict[str, Any]:
    CORE.verify_file(
        representative_path,
        REPRESENTATIVE_EVIDENCE_SHA256,
        "representative evidence",
    )
    CORE.verify_file(
        listening_path,
        REPRESENTATIVE_LISTENING_SHA256,
        "representative listening evidence",
    )
    audition = CORE.read_json(representative_path)
    listening = CORE.read_json(listening_path)
    CORE.require(
        (audition.get("scope") or {}).get("slug") == SLUG,
        "representative slug changed",
    )
    CORE.require(
        (audition.get("source") or {}).get("source_sha256")
        == PROFILE.CANONICAL_MANUSCRIPT_SHA256,
        "representative source changed",
    )
    CORE.require(
        (audition.get("engine") or {}).get("attempt_fingerprint")
        == REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "representative fingerprint changed",
    )
    CORE.require(
        (audition.get("asr") or {}).get("status") == "PASS",
        "representative ASR did not pass",
    )
    CORE.require(
        (audition.get("asr") or {}).get("repair_fingerprint")
        == REPRESENTATIVE_ASR_FINGERPRINT,
        "representative ASR fingerprint changed",
    )
    CORE.require(
        listening.get("sample_fingerprint")
        == REPRESENTATIVE_LISTENING_FINGERPRINT,
        "listening fingerprint changed",
    )
    gate = listening.get("listening_gate") or {}
    minimums = gate.get("minimum_scores") or {}
    CORE.require(
        gate.get("policy") == "sprint1_audiobook_acceptance_v3_89",
        "listening policy changed",
    )
    CORE.require(
        gate.get("platform_screen_pass") is True,
        "representative listening did not pass",
    )
    CORE.require(
        float(minimums.get("overall_listening_score") or 0) >= 8.9,
        "representative overall listening below 8.9",
    )
    CORE.require(
        float(minimums.get("confidence_score") or 0) >= 0.9,
        "representative confidence below 0.9",
    )
    CORE.require(
        gate.get("fatal_flags") == [] and gate.get("sample_blockers") == [],
        "representative listening has blockers",
    )
    return {
        "representative_evidence_path": str(representative_path),
        "representative_evidence_sha256": REPRESENTATIVE_EVIDENCE_SHA256,
        "representative_attempt_fingerprint": REPRESENTATIVE_ATTEMPT_FINGERPRINT,
        "representative_asr_fingerprint": REPRESENTATIVE_ASR_FINGERPRINT,
        "listening_evidence_path": str(listening_path),
        "listening_evidence_sha256": REPRESENTATIVE_LISTENING_SHA256,
        "listening_fingerprint": REPRESENTATIVE_LISTENING_FINGERPRINT,
        "policy": "sprint1_audiobook_acceptance_v3_89",
        "minimum_overall_listening_score": minimums["overall_listening_score"],
        "minimum_confidence_score": minimums["confidence_score"],
        "fatal_flags": [],
        "authorization_basis": (
            "representative v3.89 pass authorizes the chapter-001 checkpoint "
            "of one private full-title run"
        ),
    }


def full_title_g2p_preflight(
    sections: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    from misaki import en as misaki_en

    g2p = misaki_en.G2P(trf=False, british=True, fallback=None, unk="")
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    encountered: set[str] = set()
    reports: list[dict[str, Any]] = []
    unresolved_all: set[str] = set()
    for section in sections:
        phonemes, tokens = g2p(str(section["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        applied = [
            name
            for name in CANONICAL_PROPER_NAMES
            if re.search(rf"\b{re.escape(name)}\b", str(section["text"]))
        ]
        encountered.update(applied)
        unresolved_all.update(unresolved)
        reports.append(
            {
                "section_id": section["passage_id"],
                "source_text_sha256": section["text_sha256"],
                "phoneme_sha256": CORE.sha256_text(str(phonemes or "")),
                "pronunciation_checkpoints": applied,
                "unresolved_tokens": unresolved,
                "pass": bool(phonemes) and not unresolved,
            }
        )
    missing = sorted(set(CANONICAL_PROPER_NAMES) - encountered)
    CORE.require(
        not missing,
        "canonical pronunciation checkpoints missing: " + ", ".join(missing),
    )
    CORE.require(
        not unresolved_all and all(item["pass"] for item in reports),
        "G2P unresolved tokens: " + ", ".join(sorted(unresolved_all)),
    )
    return {
        "status": "PASS",
        "fallback_enabled": False,
        "settings": G2P_SETTINGS,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "canonical_proper_names_encountered": sorted(encountered),
        "unresolved_token_count": 0,
        "implementation_sha256": CORE.sha256_text(
            inspect.getsource(full_title_g2p_preflight)
        ),
        "sections": reports,
    }


def synthesize_sections(
    sections: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    private_dir: Path,
) -> list[dict[str, Any]]:
    samples = PROFILE.BASE.synthesize(sections, artifacts, private_dir)
    by_id = {str(item["passage_id"]): item for item in sections}
    return [
        {
            **sample,
            "word_count": int(by_id[str(sample["passage_id"])]["word_count"]),
        }
        for sample in samples
    ]


def canonicalize_equivalences(text: str):
    value, count = re.subn(r"\bgrey\b", "gray", text, flags=re.IGNORECASE)
    applied = (
        [
            {
                "equivalence": "grey/gray",
                "replacement": "gray",
                "match_count": count,
            }
        ]
        if count
        else []
    )
    return value, applied


_CORE_PREFLIGHT = CORE.preflight
_CORE_EXECUTE = CORE.execute


def configure_core() -> None:
    bindings = {
        "representative": PROFILE.BASE,
        "SLUG": SLUG,
        "TITLE": TITLE,
        "AUTHOR": AUTHOR,
        "LANGUAGE": LANGUAGE,
        "PROFILE": PROFILE_ID,
        "SCHEMA": SCHEMA,
        "FULL_SOURCE_SHA256": FULL_SOURCE_SHA256,
        "FULL_SOURCE_CHARACTERS": FULL_SOURCE_CHARACTERS,
        "NORMALIZED_SOURCE_SHA256": NORMALIZED_SOURCE_SHA256,
        "NORMALIZED_SOURCE_CHARACTERS": NORMALIZED_SOURCE_CHARACTERS,
        "NORMALIZED_SOURCE_WORDS": NORMALIZED_SOURCE_WORDS,
        "SOURCE_RIGHTS_BASIS": SOURCE_RIGHTS_BASIS,
        "REPRESENTATIVE_EVIDENCE_SHA256": REPRESENTATIVE_EVIDENCE_SHA256,
        "REPRESENTATIVE_LISTENING_SHA256": REPRESENTATIVE_LISTENING_SHA256,
        "REPRESENTATIVE_ATTEMPT_FINGERPRINT": (
            REPRESENTATIVE_ATTEMPT_FINGERPRINT
        ),
        "REPRESENTATIVE_LISTENING_FINGERPRINT": (
            REPRESENTATIVE_LISTENING_FINGERPRINT
        ),
        "REPRESENTATIVE_ASR_FINGERPRINT": REPRESENTATIVE_ASR_FINGERPRINT,
        "MODEL_REPO": PROFILE.BASE.MODEL_REPO,
        "MODEL_REVISION": PROFILE.MODEL_REVISION,
        "MODEL_SHA256": PROFILE.MODEL_SHA256,
        "CONFIG_SHA256": PROFILE.CONFIG_SHA256,
        "VOICE": PROFILE.VOICE,
        "VOICE_SHA256": PROFILE.VOICE_SHA256,
        "SAMPLE_RATE": PROFILE.BASE.SAMPLE_RATE,
        "SPEED": PROFILE.SPEED,
        "RANDOM_SEED": PROFILE.RANDOM_SEED,
        "WHISPER_MODEL": PROFILE.BASE.WHISPER_MODEL,
        "WHISPER_SHA256": PROFILE.WHISPER_SHA256,
        "ASR_SCORE_MIN": 9.7,
        "ASR_COVERAGE_MIN": 0.98,
        "SYNC_SCORE_MIN": 9.7,
        "LISTENING_SCORE_MIN": 8.9,
        "LISTENING_CONFIDENCE_MIN": 0.9,
        "SECTION_WORD_COUNTS": SECTION_WORD_COUNTS,
        "SECTION_HASHES": SECTION_HASHES,
        "PRONUNCIATION_OVERRIDES": PRONUNCIATION_OVERRIDES,
        "CANONICAL_PROPER_NAMES": CANONICAL_PROPER_NAMES,
        "G2P_SETTINGS": G2P_SETTINGS,
        "ASR_SETTINGS": ASR_SETTINGS,
        "SOURCE_EQUIVALENCE_POLICY": SOURCE_EQUIVALENCE_POLICY,
        "DEFAULT_REPRESENTATIVE_EVIDENCE": DEFAULT_REPRESENTATIVE_EVIDENCE,
        "DEFAULT_LISTENING_EVIDENCE": DEFAULT_LISTENING_EVIDENCE,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_PRIVATE_DIR": DEFAULT_PRIVATE_DIR,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "NO_REPEAT_FILES": PROFILE.BASE.NO_REPEAT_FILES,
        "controlled_source": controlled_source,
        "validate_predecessor_evidence": validate_predecessor_evidence,
        "full_title_g2p_preflight": full_title_g2p_preflight,
        "synthesize_sections": synthesize_sections,
        "canonicalize_equivalences": canonicalize_equivalences,
    }
    for name, value in bindings.items():
        setattr(CORE, name, value)
    PROFILE.BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES


def preflight(**kwargs: Any):
    configure_core()
    payload, sections, artifacts = _CORE_PREFLIGHT(**kwargs)
    payload["schema"] = SCHEMA
    payload["scope"]["passage_count"] = len(sections)
    payload["scope"]["full_title_scope"] = "chapter-001 checkpoint of 27"
    payload["scope"]["full_title_generated"] = False
    payload["policy"] = {
        "version": "sprint1_audiobook_acceptance_v3_89",
        "representative_listening_min": 8.9,
        "asr_manuscript_min": 9.7,
        "coverage_min": 0.98,
    }
    payload["rights"].pop(
        "gift_title_scoped_publication_risk_acceptance_bound", None
    )
    payload["rights"].update(
        {
            "secret_garden_title_scoped_production_risk_acceptance_bound": True,
            "production_release_approved": False,
            "public_disclosure_required_if_later_approved": "AI narration",
        }
    )
    payload["blockers_to_release"] = [
        "REMAINING_26_CHAPTERS_NOT_GENERATED",
        "CHAPTER_001_AUDIO_DERIVED_ASR_NOT_RUN",
        "CHAPTER_001_MEASURED_SECTION_SYNC_NOT_RUN",
        "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    return payload, sections, artifacts


def execute(**kwargs: Any):
    configure_core()
    code, payload = _CORE_EXECUTE(**kwargs)
    payload["scope"]["full_title_scope"] = "chapter-001 checkpoint of 27"
    payload["policy"] = {
        "version": "sprint1_audiobook_acceptance_v3_89",
        "asr_manuscript_min": 9.7,
        "coverage_min": 0.98,
    }
    objective_pass = payload.get("status") == (
        "PRIVATE_FULL_TITLE_OBJECTIVE_PASS_LISTENING_PENDING"
    )
    payload["scope"]["full_title_generated"] = False
    payload["scope"]["chapter_checkpoint_generated"] = True
    payload["safety"]["full_title_generated"] = False
    payload["safety"]["chapter_checkpoint_generated"] = True
    payload["status"] = (
        "SECRET_GARDEN_CHAPTER_001_OBJECTIVE_PASS_READY_TO_RESUME"
        if objective_pass
        else "SECRET_GARDEN_CHAPTER_001_OBJECTIVE_FAIL_FULL_RUN_STOPPED"
    )
    payload["blockers_to_release"] = [
        *(
            []
            if objective_pass
            else ["CHAPTER_001_PRIVATE_OBJECTIVE_QA_FAILED"]
        ),
        "REMAINING_26_CHAPTERS_NOT_GENERATED",
        "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    CORE.write_json(Path(kwargs["output"]), payload)
    return code, payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument(
        "--whisper-cache-dir", type=Path, default=DEFAULT_WHISPER_CACHE
    )
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument(
        "--representative-evidence",
        type=Path,
        default=DEFAULT_REPRESENTATIVE_EVIDENCE,
    )
    parser.add_argument(
        "--listening-evidence",
        type=Path,
        default=DEFAULT_LISTENING_EVIDENCE,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload, sections, artifacts = preflight(
        asset_root=args.asset_root.expanduser().resolve(),
        artifact_dir=args.artifact_dir.expanduser().resolve(),
        whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
        private_dir=args.private_dir.expanduser().resolve(),
        output=args.output.expanduser().resolve(),
        paid_lock=args.paid_lock.expanduser().resolve(),
        representative_evidence=args.representative_evidence.expanduser().resolve(),
        listening_evidence=args.listening_evidence.expanduser().resolve(),
    )
    if args.dry_run:
        CORE.write_json(args.output.expanduser().resolve(), payload)
        code = 0
    else:
        code, payload = execute(
            preflight_payload=payload,
            sections=sections,
            artifacts=artifacts,
            private_dir=args.private_dir.expanduser().resolve(),
            whisper_cache_dir=args.whisper_cache_dir.expanduser().resolve(),
            paid_lock=args.paid_lock.expanduser().resolve(),
            output=args.output.expanduser().resolve(),
        )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "output": str(args.output.expanduser().resolve()),
                "section_count": len(sections),
                "audio_generated": payload["safety"]["audio_generated"],
                "provider_calls": payload["safety"]["provider_calls"],
                "upload_performed": payload["safety"]["upload_performed"],
                "publication_performed": payload["safety"][
                    "publication_performed"
                ],
                "blockers_to_release": payload["blockers_to_release"],
            },
            indent=2,
        )
    )
    return code


configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
