#!/usr/bin/env python3
"""Bengali ASR script-normalization and phonetic projection diagnostics.

This module is intentionally conservative. It can rescue obvious Bengali ASR
script shifts for transcript validation, but it does not turn low-confidence
transliteration into release approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
TOKEN_RE = re.compile(r"[\u0980-\u09FF\u0900-\u097FA-Za-z0-9]+")

DEVANAGARI_TO_BENGALI = str.maketrans(
    {
        "अ": "অ",
        "आ": "আ",
        "इ": "ই",
        "ई": "ঈ",
        "उ": "উ",
        "ऊ": "ঊ",
        "ऋ": "ঋ",
        "ए": "এ",
        "ऐ": "ঐ",
        "ओ": "ও",
        "औ": "ঔ",
        "ा": "া",
        "ि": "ি",
        "ी": "ী",
        "ु": "ু",
        "ू": "ূ",
        "ृ": "ৃ",
        "े": "ে",
        "ै": "ৈ",
        "ो": "ো",
        "ौ": "ৌ",
        "ं": "ং",
        "ँ": "ঁ",
        "ः": "ঃ",
        "्": "্",
        "क": "ক",
        "ख": "খ",
        "ग": "গ",
        "घ": "ঘ",
        "ङ": "ঙ",
        "च": "চ",
        "छ": "ছ",
        "ज": "জ",
        "झ": "ঝ",
        "ञ": "ঞ",
        "ट": "ট",
        "ठ": "ঠ",
        "ड": "ড",
        "ढ": "ঢ",
        "ण": "ণ",
        "त": "ত",
        "थ": "থ",
        "द": "দ",
        "ध": "ধ",
        "न": "ন",
        "प": "প",
        "फ": "ফ",
        "ब": "ব",
        "भ": "ভ",
        "म": "ম",
        "य": "য",
        "र": "র",
        "ल": "ল",
        "व": "ব",
        "श": "শ",
        "ष": "ষ",
        "स": "স",
        "ह": "হ",
        "़": "",
        "०": "0",
        "१": "1",
        "२": "2",
        "३": "3",
        "४": "4",
        "५": "5",
        "६": "6",
        "७": "7",
        "८": "8",
        "९": "9",
    }
)

BENGALI_TO_ROMAN = {
    "অ": "a",
    "আ": "a",
    "ই": "i",
    "ঈ": "i",
    "উ": "u",
    "ঊ": "u",
    "ঋ": "ri",
    "এ": "e",
    "ঐ": "oi",
    "ও": "o",
    "ঔ": "ou",
    "া": "a",
    "ি": "i",
    "ী": "i",
    "ু": "u",
    "ূ": "u",
    "ৃ": "ri",
    "ে": "e",
    "ৈ": "oi",
    "ো": "o",
    "ৌ": "ou",
    "ক": "k",
    "খ": "kh",
    "গ": "g",
    "ঘ": "gh",
    "ঙ": "ng",
    "চ": "ch",
    "ছ": "chh",
    "জ": "j",
    "ঝ": "jh",
    "ঞ": "n",
    "ট": "t",
    "ঠ": "th",
    "ড": "d",
    "ঢ": "dh",
    "ণ": "n",
    "ত": "t",
    "থ": "th",
    "দ": "d",
    "ধ": "dh",
    "ন": "n",
    "প": "p",
    "ফ": "ph",
    "ব": "b",
    "ভ": "bh",
    "ম": "m",
    "য": "j",
    "র": "r",
    "ল": "l",
    "শ": "sh",
    "ষ": "sh",
    "স": "s",
    "হ": "h",
    "ড়": "r",
    "ঢ়": "r",
    "য়": "y",
    "ৎ": "t",
    "ং": "ng",
    "ঁ": "",
    "ঃ": "",
    "্": "",
}

COMMON_VARIANTS = {
    "গল্পগুচ্ছ": "গল্পগুচ্ছ",
    "গল্পগুছ": "গল্পগুচ্ছ",
    "গল্পগুচ্ছো": "গল্পগুচ্ছ",
    "রবিন্দ্রনাথ": "রবীন্দ্রনাথ",
    "রবীন্দ্রনাথ": "রবীন্দ্রনাথ",
    "ঠাকুর": "ঠাকুর",
    "টাকা": "টাকা",
    "তাকা": "টাকা",
}

FRONTMATTER_TERMS = ("project gutenberg", "gutenberg.org", "wikisource", "repository", "গল্পগুচ্ছ", "পৃ", "পৃষ্ঠা")


@dataclass
class NormalizedToken:
    index: int
    text: str
    script: str
    normalized: str
    phonetic: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def script_counts(text: str) -> dict[str, int]:
    return {
        "bengali": len(BENGALI_RE.findall(text or "")),
        "devanagari": len(DEVANAGARI_RE.findall(text or "")),
        "latin": len(LATIN_RE.findall(text or "")),
    }


def detect_script_mix(text: str) -> str:
    counts = script_counts(text)
    active = [name for name, count in counts.items() if count > 0]
    if not active:
        return "unknown"
    if len(active) == 1:
        return {"bengali": "Bengali", "devanagari": "Devanagari", "latin": "Latin"}[active[0]]
    dominant = max(active, key=lambda name: counts[name])
    if counts[dominant] >= sum(counts.values()) * 0.82:
        return {"bengali": "Bengali", "devanagari": "Devanagari", "latin": "Latin"}[dominant]
    return "mixed"


def normalize_digits(text: str) -> str:
    return text.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))


def simplify_roman(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    replacements = [
        ("class", "klas"),
        ("cl", "kl"),
        ("kh", "k"),
        ("gh", "g"),
        ("chh", "ch"),
        ("jh", "j"),
        ("th", "t"),
        ("dh", "d"),
        ("ph", "f"),
        ("bh", "b"),
        ("sh", "s"),
        ("sz", "s"),
        ("ng", "n"),
        ("oo", "u"),
        ("ee", "i"),
        ("ou", "o"),
    ]
    for before, after in replacements:
        text = text.replace(before, after)
    text = re.sub(r"[aeiouy]", "", text)
    text = re.sub(r"(.)\1+", r"\1", text)
    return text


def bengali_to_roman(value: str) -> str:
    chars: list[str] = []
    for char in value:
        chars.append(BENGALI_TO_ROMAN.get(char, char if char.isascii() else ""))
    return "".join(chars)


def normalize_token_text(raw: str) -> tuple[str, str, str]:
    script = detect_script_mix(raw)
    token = normalize_digits(unicodedata.normalize("NFC", raw or "").strip())
    if script == "Devanagari":
        token = token.translate(DEVANAGARI_TO_BENGALI)
    token = re.sub(r"[^\u0980-\u09FFA-Za-z0-9]+", "", token)
    token = COMMON_VARIANTS.get(token, token)
    if BENGALI_RE.search(token):
        phonetic = simplify_roman(bengali_to_roman(token))
    else:
        phonetic = simplify_roman(token)
    return script, token.lower(), phonetic


def tokenize(text: str) -> list[NormalizedToken]:
    tokens: list[NormalizedToken] = []
    for match in TOKEN_RE.finditer(text or ""):
        raw = match.group(0)
        script, normalized, phonetic = normalize_token_text(raw)
        if not normalized and not phonetic:
            continue
        tokens.append(NormalizedToken(len(tokens), raw, script, normalized, phonetic))
    return tokens


def token_similarity(asr: NormalizedToken, manuscript: NormalizedToken) -> float:
    if asr.normalized and asr.normalized == manuscript.normalized:
        return 1.0
    if asr.phonetic and manuscript.phonetic and asr.phonetic == manuscript.phonetic:
        return 0.97
    normalized = SequenceMatcher(None, asr.normalized, manuscript.normalized).ratio() if asr.normalized and manuscript.normalized else 0.0
    phonetic = SequenceMatcher(None, asr.phonetic, manuscript.phonetic).ratio() if asr.phonetic and manuscript.phonetic else 0.0
    return max(normalized * 0.9, phonetic)


def align_tokens(asr_tokens: list[NormalizedToken], manuscript_tokens: list[NormalizedToken]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    skipped_asr: list[dict[str, Any]] = []
    cursor = 0
    window_size = 120
    for asr in asr_tokens:
        best_index = None
        best_score = 0.0
        window_end = min(len(manuscript_tokens), cursor + window_size)
        for mi in range(cursor, window_end):
            score = token_similarity(asr, manuscript_tokens[mi])
            if score > best_score:
                best_score = score
                best_index = mi
                if score >= 0.995:
                    break
        if best_index is not None and best_score >= 0.78:
            matches.append(
                {
                    "asr_index": asr.index,
                    "manuscript_index": best_index,
                    "asr_text": asr.text,
                    "manuscript_text": manuscript_tokens[best_index].text,
                    "score": round(best_score, 4),
                    "asr_script": asr.script,
                }
            )
            cursor = best_index + 1
        else:
            skipped_asr.append({"asr_index": asr.index, "asr_text": asr.text, "best_score": round(best_score, 4)})

    matched_manuscript = {int(item["manuscript_index"]) for item in matches}
    missing = missing_spans(manuscript_tokens, matched_manuscript)
    average_score = sum(float(item["score"]) for item in matches) / len(matches) if matches else 0.0
    coverage = len(matched_manuscript) / len(manuscript_tokens) if manuscript_tokens else 0.0
    return {
        "matches": matches,
        "skipped_asr": skipped_asr[:80],
        "matched_manuscript_count": len(matched_manuscript),
        "manuscript_token_count": len(manuscript_tokens),
        "coverage": round(coverage, 4),
        "average_match_score": round(average_score, 4),
        "projection_confidence": round(coverage * average_score, 4),
        "missing_spans": missing,
        "missing_span_count": len(missing),
    }


def missing_spans(tokens: list[NormalizedToken], matched_indices: set[int]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    start: int | None = None
    for index in range(len(tokens) + 1):
        missing = index < len(tokens) and index not in matched_indices
        if missing and start is None:
            start = index
        if (not missing or index == len(tokens)) and start is not None:
            end = index - 1
            spans.append(
                {
                    "start_index": start,
                    "end_index": end,
                    "word_count": end - start + 1,
                    "text": " ".join(token.text for token in tokens[start : end + 1])[:300],
                }
            )
            start = None
    return spans[:20]


def sequence_score(tokens_a: list[NormalizedToken], tokens_b: list[NormalizedToken], attr: str) -> float:
    a = " ".join(str(getattr(token, attr)) for token in tokens_a if getattr(token, attr))
    b = " ".join(str(getattr(token, attr)) for token in tokens_b if getattr(token, attr))
    return SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0.0


def ordered_character_alignment(
    asr_tokens: list[NormalizedToken], manuscript_tokens: list[NormalizedToken], attr: str
) -> dict[str, Any]:
    """Measure ordered content while ignoring ASR-only word-boundary changes.

    Bengali ASR regularly splits historical compounds (for example one source
    token into two transcript tokens). Token-greedy alignment treats the rest
    of the passage as missing after such a split. This character projection is
    still transcript-derived and ordered, but it removes only token spacing.
    """
    asr_text = "".join(str(getattr(token, attr)) for token in asr_tokens if getattr(token, attr))
    manuscript_text = "".join(
        str(getattr(token, attr)) for token in manuscript_tokens if getattr(token, attr)
    )
    if not asr_text or not manuscript_text:
        return {
            "sequence_similarity": 0.0,
            "manuscript_coverage": 0.0,
            "transcript_coverage": 0.0,
            "first_boundary_score": 0.0,
            "last_boundary_score": 0.0,
            "first_words_match": False,
            "last_words_match": False,
            "max_manuscript_gap_chars": 0,
            "max_transcript_gap_chars": 0,
            "material_missing_spans": [],
            "material_extra_spans": [],
        }
    matcher = SequenceMatcher(None, manuscript_text, asr_text, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    manuscript_gaps: list[dict[str, Any]] = []
    transcript_gaps: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"delete", "replace"} and i2 > i1:
            manuscript_gaps.append(
                {"tag": tag, "start": i1, "end": i2, "chars": i2 - i1, "text": manuscript_text[i1:i2]}
            )
        if tag in {"insert", "replace"} and j2 > j1:
            transcript_gaps.append(
                {"tag": tag, "start": j1, "end": j2, "chars": j2 - j1, "text": asr_text[j1:j2]}
            )
    boundary_window = min(48, len(manuscript_text), len(asr_text))
    first_score = SequenceMatcher(
        None, manuscript_text[:boundary_window], asr_text[:boundary_window], autojunk=False
    ).ratio()
    last_score = SequenceMatcher(
        None, manuscript_text[-boundary_window:], asr_text[-boundary_window:], autojunk=False
    ).ratio()
    # Release truth is exact after the explicit normalization/phonetic mapping
    # above. Any remaining character gap is unexplained audio content loss or
    # addition; a high aggregate score must never hide it.
    material_missing = list(manuscript_gaps)
    material_extra = list(transcript_gaps)
    return {
        "sequence_similarity": round(matcher.ratio(), 4),
        "manuscript_coverage": round(matched / len(manuscript_text), 4),
        "transcript_coverage": round(matched / len(asr_text), 4),
        "first_boundary_score": round(first_score, 4),
        "last_boundary_score": round(last_score, 4),
        "first_words_match": first_score >= 0.9,
        "last_words_match": last_score >= 0.9,
        "max_manuscript_gap_chars": max((int(item["chars"]) for item in manuscript_gaps), default=0),
        "max_transcript_gap_chars": max((int(item["chars"]) for item in transcript_gaps), default=0),
        "material_missing_spans": material_missing[:20],
        "material_extra_spans": material_extra[:20],
    }


def edge_match(matches: list[dict[str, Any]], manuscript_count: int, edge: str, tolerance: int = 10) -> bool:
    if not matches or manuscript_count <= 0:
        return False
    manuscript_indices = [int(item["manuscript_index"]) for item in matches]
    if edge == "first":
        return min(manuscript_indices) <= tolerance
    return max(manuscript_indices) >= max(0, manuscript_count - tolerance - 1)


def contains_frontmatter(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in FRONTMATTER_TERMS)


def blocker_category(report: dict[str, Any]) -> str:
    if report["likely_real_audio_manuscript_mismatch"]:
        return "bengali_audio_manuscript_mismatch"
    if report["likely_false_negative_due_to_script_mismatch"]:
        return "bengali_asr_script_mismatch"
    if report["content_match_proven"] and report["sync_regeneration_required"]:
        return "bengali_sync_regeneration_required"
    return "bengali_asr_low_confidence"


def analyze_bengali_asr(
    *,
    slug: str,
    title: str,
    author: str,
    language: str,
    manuscript: str,
    transcript: str,
    run_dir: Path,
    audio_path: str = "",
    audio_hash: str = "",
    raw_asr_score: float = 0.0,
    raw_similarity: float = 0.0,
    raw_coverage: float = 0.0,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    manuscript_tokens = tokenize(manuscript)
    asr_tokens = tokenize(transcript)
    alignment = align_tokens(asr_tokens, manuscript_tokens)
    normalized_similarity = sequence_score(asr_tokens, manuscript_tokens, "normalized")
    phonetic_similarity = sequence_score(asr_tokens, manuscript_tokens, "phonetic")
    normalized_ordered = ordered_character_alignment(asr_tokens, manuscript_tokens, "normalized")
    phonetic_ordered = ordered_character_alignment(asr_tokens, manuscript_tokens, "phonetic")
    phonetic_projection_score = round(
        min(
            phonetic_ordered["sequence_similarity"],
            phonetic_ordered["manuscript_coverage"],
            phonetic_ordered["transcript_coverage"],
        )
        * 10,
        4,
    )
    normalized_score = round(
        min(
            normalized_ordered["sequence_similarity"],
            normalized_ordered["manuscript_coverage"],
            normalized_ordered["transcript_coverage"],
        )
        * 10,
        4,
    )
    raw_script = detect_script_mix(transcript)
    first_words_match = bool(phonetic_ordered["first_words_match"])
    last_words_match = bool(phonetic_ordered["last_words_match"])
    projected_coverage = min(
        float(phonetic_ordered["manuscript_coverage"]), float(phonetic_ordered["transcript_coverage"])
    )
    projected_confidence = min(float(phonetic_ordered["sequence_similarity"]), projected_coverage)
    no_unexplained_gap = not phonetic_ordered["material_missing_spans"] and not phonetic_ordered["material_extra_spans"]
    projection_match_proven = (
        max(normalized_score, phonetic_projection_score) >= 9.7
        and projected_confidence >= 0.97
        and projected_coverage >= 0.98
        and first_words_match
        and last_words_match
        and no_unexplained_gap
        and not contains_frontmatter(transcript)
    )
    # Projection remains diagnostic evidence. It cannot replace the mandatory
    # raw audio-derived ASR/manuscript score at the public release gate.
    content_match_proven = bool(projection_match_proven and raw_asr_score >= 9.7)
    script_shifted = raw_script in {"Devanagari", "Latin", "mixed"}
    likely_false_negative = bool(script_shifted and raw_asr_score < 9.7 and max(normalized_score, phonetic_projection_score) > raw_asr_score + 1.0)
    likely_real_mismatch = bool(projected_coverage < 0.5 and max(normalized_score, phonetic_projection_score) < 5.0)
    sync_regeneration_required = bool(content_match_proven and raw_script != "Bengali")

    normalized_asr_path = run_dir / "normalized_asr_tokens.json"
    normalized_manuscript_path = run_dir / "normalized_manuscript_tokens.json"
    phonetic_alignment_path = run_dir / "phonetic_alignment.json"
    projection_report_path = run_dir / "bengali_asr_projection_report.json"
    diagnosis_path = run_dir / "bengali_asr_mismatch_diagnosis.json"

    write_json(normalized_asr_path, {"slug": slug, "script": raw_script, "tokens": [asdict(token) for token in asr_tokens]})
    write_json(normalized_manuscript_path, {"slug": slug, "tokens": [asdict(token) for token in manuscript_tokens]})
    write_json(
        phonetic_alignment_path,
        {
            "slug": slug,
            "ordered_normalized_alignment": normalized_ordered,
            "ordered_phonetic_alignment": phonetic_ordered,
            "legacy_token_alignment": alignment,
        },
    )

    report = {
        "slug": slug,
        "title": title,
        "author": author,
        "language": language,
        "audio_path": audio_path,
        "audio_hash": audio_hash,
        "clean_manuscript_hash": sha256_text(manuscript),
        "raw_asr_script_detected": raw_script,
        "script_counts": script_counts(transcript),
        "asr_confidence": None,
        "raw_similarity": raw_similarity,
        "raw_asr_score": raw_asr_score,
        "raw_coverage": raw_coverage,
        "normalized_similarity": round(normalized_similarity, 4),
        "normalized_asr_score": normalized_score,
        "phonetic_similarity": round(phonetic_similarity, 4),
        "phonetic_projection_score": phonetic_projection_score,
        "coverage": round(projected_coverage, 4),
        "projection_confidence": round(projected_confidence, 4),
        "first_words_match": first_words_match,
        "last_words_match": last_words_match,
        "missing_spans": phonetic_ordered["material_missing_spans"],
        "extra_spans": phonetic_ordered["material_extra_spans"],
        "ordered_normalized_alignment": normalized_ordered,
        "ordered_phonetic_alignment": phonetic_ordered,
        "duplicated_spans": [],
        "frontmatter_absent": not contains_frontmatter(transcript),
        "likely_false_negative_due_to_script_mismatch": likely_false_negative,
        "likely_real_audio_manuscript_mismatch": likely_real_mismatch,
        "projection_match_proven": projection_match_proven,
        "content_match_proven": content_match_proven,
        "sync_regeneration_required": sync_regeneration_required,
        "release_pass": bool(content_match_proven and not sync_regeneration_required),
        "recommended_action": "",
        "artifacts": {
            "normalized_asr_tokens": str(normalized_asr_path),
            "normalized_manuscript_tokens": str(normalized_manuscript_path),
            "phonetic_alignment": str(phonetic_alignment_path),
            "bengali_asr_projection_report": str(projection_report_path),
            "bengali_asr_mismatch_diagnosis": str(diagnosis_path),
        },
    }
    category = blocker_category(report)
    if report["release_pass"]:
        report["recommended_action"] = "normalized_projection_passed; continue ASR/sync gate"
    elif category == "bengali_sync_regeneration_required":
        report["recommended_action"] = "content match appears proven but timestamps are not canonical-script release sync; rebuild Bengali sync by construction or phrase/segment alignment"
    elif category == "bengali_asr_script_mismatch":
        report["recommended_action"] = "terminal-block with script-mismatch evidence unless a better Bengali ASR/transliteration path raises projection confidence"
    elif category == "bengali_audio_manuscript_mismatch":
        report["recommended_action"] = "treat as probable audio/manuscript mismatch; regenerate or rehydrate the correct audio before retry"
    else:
        report["recommended_action"] = "terminal-block as low-confidence Bengali ASR; continue catalog if ordered skip is allowed"
    report["blocker_category"] = category

    write_json(projection_report_path, report)
    write_json(diagnosis_path, report)
    return report


def self_test() -> int:
    manuscript = "গিন্নি ছাত্রবৃত্তি ক্লাসের নীচে আমাদের পণ্ডিত ছিলেন শিবনাথ পণ্ডিত।"
    cases = [
        ("bengali", "গিন্নি ছাত্রবৃত্তি ক্লাসের নীচে আমাদের পণ্ডিত ছিলেন শিবনাথ পণ্ডিত।", True),
        ("devanagari", "गिन्नी छात्रोबृत्ति क्लासेर नीचे आमादेर पंडित छिलेन शिबनाथ पंडित", True),
        ("latin", "ginni chatrobrtti classer niche amader pondit chilen shibnath pondit", True),
        ("mixed", "গিন্নি छात्रोबृत्ति classer নিচে amader পণ্ডিত chilen শিবনাথ pondit", True),
        ("mismatch", "this is unrelated english narration about another story", False),
    ]
    tmp = Path("/tmp/earnalism-bengali-asr-normalization-self-test")
    for name, transcript, expected in cases:
        report = analyze_bengali_asr(
            slug=f"self-test-{name}",
            title="self test",
            author="",
            language="ben",
            manuscript=manuscript,
            transcript=transcript,
            run_dir=tmp / name,
            raw_asr_score=10.0 if name == "bengali" else 0.0,
        )
        passed = report["content_match_proven"] if name == "bengali" else report["projection_match_proven"]
        if bool(passed) != expected:
            raise AssertionError(f"{name} expected {expected}, got {passed}: {report}")
    print("bengali_asr_normalization self-test PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    parser.error("Use --self-test or import analyze_bengali_asr from this module.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
