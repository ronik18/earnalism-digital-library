#!/usr/bin/env python3
"""Prepare a Bengali gothic controlled-publication candidate in dry-run mode.

The script is intentionally fail-closed:
- no production mutation
- no public publishing
- no full audiobook generation
- no provider/API calls beyond source fetch when explicitly opted in
- no committed full source text by default
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audiobook_voice_pipeline import AudiobookPipelineInput, plan_audiobook_pipeline
from backend.rights_engine import evaluate_rights
from backend.source_ingestion import hash_provenance, hash_source


SLUG = "kshudhita-pashan"
TITLE_BN = "ক্ষুধিত পাষাণ"
TITLE_EN = "The Hungry Stones"
AUTHOR = "Rabindranath Tagore"
AUTHOR_BN = "রবীন্দ্রনাথ ঠাকুর"
AUTHOR_DEATH_YEAR = 1941
ORIGINAL_PUBLICATION_YEAR = 1895
LANGUAGE = "bn"
GENRE = "Bengali Gothic / Supernatural"
SOURCE_PAGE_TITLE = "গল্প-দশক/ক্ষুধিত পাষাণ"
SOURCE_URL = f"https://bn.wikisource.org/wiki/{quote(SOURCE_PAGE_TITLE.replace(' ', '_'), safe='/')}"
SOURCE_NAME = "Bengali Wikisource"
SOURCE_LICENSE_FALLBACK = "Creative Commons Attribution-Share Alike 4.0"
SOURCE_LICENSE_URL_FALLBACK = "https://creativecommons.org/licenses/by-sa/4.0/"
SOURCE_PAGE_OLDID = ""
ROLLBACK_OWNER = "Earnalism launch operator"
PUBLICATION_CAP = "Kshudhita Pashan controlled-readiness candidate only; public_publish_actions=0."

DATA_DIR = ROOT / "data" / "publication_candidates"
OUTPUT_DIR = ROOT / "output" / "publication_candidates" / SLUG

MIN_CLEANED_CHARS = 8_000
MIN_PARAGRAPHS = 20
MIN_SENTENCES = 45
MIN_BENGALI_RATIO = 0.62
PREVIEW_CHARS = 1_200

BENGALI_CHAR_RE = re.compile(r"[\u0980-\u09FF]")
SENTENCE_RE = re.compile(r"[^।!?]+[।!?]")
MOJIBAKE_RE = re.compile(r"(à¦|à§|Ã|Â|�)")
BOILERPLATE_LINE_RE = re.compile(
    r"^(?:রবীন্দ্রনাথ ঠাকুর|গল্প-দশক|অতিথি|প্রতিহিংসা|◄|►|"
    r"গল্প-দশকরবীন্দ্রনাথ ঠাকুরক্ষুধিত পাষাণ|১৬৫-১৮৮|১৮৯৫|"
    r"সম্পাদনা|বিষয়শ্রেণী|অন্য ভাষায়|উইকিসংকলন|মুদ্রণ/রপ্তানি)",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
HIDDEN_TEXT_RE = re.compile("[\u200b\u200c\u200d\ufeff]")
ENGLISH_QUOTE_RE = re.compile(r"[\"']")

PRONUNCIATION_TERMS = [
    {
        "word": "ক্ষুধিত পাষাণ",
        "pronunciation_hint": "খু-ধি-তো পা-ষাণ; conjunct ক্ষ stays soft, not kh-sh.",
        "context": "title and recurring mood phrase",
        "confidence": "high",
        "requires_human_spot_check": True,
    },
    {
        "word": "বরীচ",
        "pronunciation_hint": "বো-রীচ; final চ clear but restrained.",
        "context": "place name in the haunted palace narration",
        "confidence": "medium",
        "requires_human_spot_check": True,
    },
    {
        "word": "শুস্তা",
        "pronunciation_hint": "শুস্-তা; keep the river name smooth, not over-enunciated.",
        "context": "river beside the palace",
        "confidence": "medium",
        "requires_human_spot_check": True,
    },
    {
        "word": "জুনাগড়",
        "pronunciation_hint": "জু-না-গড়; light retroflex on ড়.",
        "context": "former administrative posting",
        "confidence": "high",
        "requires_human_spot_check": False,
    },
    {
        "word": "হাইদ্রাবাদ",
        "pronunciation_hint": "হাই-দ্রা-বাদ; natural Bengali pacing.",
        "context": "Nizam government setting",
        "confidence": "high",
        "requires_human_spot_check": False,
    },
    {
        "word": "মেহের আলি",
        "pronunciation_hint": "মে-হের আ-লি; keep the repeated warning urgent but not theatrical.",
        "context": "the haunted warning voice",
        "confidence": "high",
        "requires_human_spot_check": True,
    },
    {
        "word": "করীম খাঁ",
        "pronunciation_hint": "কো-রীম খাঁ; nasalize খাঁ lightly.",
        "context": "elder clerk who explains the palace",
        "confidence": "medium",
        "requires_human_spot_check": True,
    },
    {
        "word": "গুলবাগ",
        "pronunciation_hint": "গুল-বাগ; preserve the Persianate texture.",
        "context": "old palace history reference",
        "confidence": "medium",
        "requires_human_spot_check": True,
    },
    {
        "word": "তফাৎ যাও",
        "pronunciation_hint": "তো-ফাৎ যাও; repeated warning should sound haunted and breath-controlled.",
        "context": "signature refrain",
        "confidence": "high",
        "requires_human_spot_check": True,
    },
]


@dataclass
class SourceLoadResult:
    raw_text: str
    source_text_url: str
    source_license: str
    source_license_url: str
    source_retrieved_at: str
    load_status: str
    issues: list[str]


class ParsedHtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script", "sup", "table"}:
            self.skip_depth += 1
            return
        if not self.skip_depth and tag in {"p", "div", "br", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script", "sup", "table"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if not self.skip_depth and tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return html.unescape("".join(self.parts))


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_text_api_url(source_page_title: str = SOURCE_PAGE_TITLE) -> str:
    return "https://bn.wikisource.org/w/api.php?" + urlencode(
        {
            "action": "parse",
            "page": source_page_title,
            "prop": "text|displaytitle",
            "format": "json",
            "formatversion": "2",
        }
    )


def source_license_api_url() -> str:
    return "https://bn.wikisource.org/w/api.php?" + urlencode(
        {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "rightsinfo",
            "format": "json",
            "formatversion": "2",
        }
    )


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "EarnalismBengaliCandidateDryRun/1.0"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - opt-in public source fetch only.
        return json.loads(response.read().decode("utf-8", errors="replace"))


def extract_text_from_parsed_html(parsed_html: str) -> str:
    parser = ParsedHtmlTextExtractor()
    parser.feed(parsed_html)
    return parser.text()


def normalize_line(line: str) -> str:
    line = WHITESPACE_RE.sub(" ", HIDDEN_TEXT_RE.sub("", line))
    return line.strip()


def safe_preview(text: str, limit: int) -> str:
    return HIDDEN_TEXT_RE.sub("", text[:limit])


def hidden_unicode_counts(text: str) -> dict[str, int]:
    return {
        "zero_width_space": text.count("\u200b"),
        "zero_width_non_joiner": text.count("\u200c"),
        "zero_width_joiner": text.count("\u200d"),
        "bom": text.count("\ufeff"),
    }


def clean_bengali_source_text(raw_text: str) -> str:
    lines = [normalize_line(line) for line in raw_text.splitlines()]
    cleaned: list[str] = []
    seen_title = False
    for line in lines:
        if not line:
            continue
        if BOILERPLATE_LINE_RE.search(line):
            if TITLE_BN in line:
                seen_title = True
            continue
        if line in {"\u200b", "\ufeff"}:
            continue
        if not seen_title and TITLE_BN in line:
            seen_title = True
            cleaned.append(TITLE_BN)
            continue
        cleaned.append(line)
    text = "\n\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def bengali_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    bengali = sum(1 for ch in letters if BENGALI_CHAR_RE.match(ch))
    return bengali / len(letters)


def paragraph_count(text: str) -> int:
    return len([block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()])


def sentence_count(text: str) -> int:
    return len(SENTENCE_RE.findall(text))


def source_markers(raw_text: str, source_license: str) -> dict[str, bool]:
    return {
        "source_title_marker": TITLE_BN in raw_text,
        "author_marker": AUTHOR_BN in raw_text,
        "source_year_marker": "১৮৯৫" in raw_text or "1895" in raw_text,
        "source_license_marker": bool(source_license),
        "wikisource_marker": "wikisource" in SOURCE_URL.lower() or "উইকিসংকলন" in raw_text,
    }


def text_qa(raw_text: str, cleaned_text: str, source_license: str) -> dict[str, Any]:
    markers = source_markers(raw_text, source_license)
    paragraphs = paragraph_count(cleaned_text)
    sentences = sentence_count(cleaned_text)
    ratio = bengali_ratio(cleaned_text)
    issues: list[str] = []

    if not raw_text.strip():
        issues.append("source text is required")
    if not cleaned_text.strip():
        issues.append("cleaned text is required")
    if len(cleaned_text) < MIN_CLEANED_CHARS:
        issues.append(f"cleaned text must be at least {MIN_CLEANED_CHARS} characters")
    if paragraphs < MIN_PARAGRAPHS:
        issues.append(f"paragraph count must be at least {MIN_PARAGRAPHS}")
    if sentences < MIN_SENTENCES:
        issues.append(f"sentence count must be at least {MIN_SENTENCES}")
    if ratio < MIN_BENGALI_RATIO:
        issues.append(f"Bengali script ratio must be at least {MIN_BENGALI_RATIO}")
    if MOJIBAKE_RE.search(raw_text) or MOJIBAKE_RE.search(cleaned_text):
        issues.append("mojibake or replacement characters detected")
    if not all(markers.values()):
        missing = [key for key, value in markers.items() if not value]
        issues.append(f"missing source markers: {', '.join(missing)}")

    return {
        "qa_status": "QA_PASSED" if not issues else "BLOCKED_SOURCE_QA",
        "issues": issues,
        "bengali_script_ratio": round(ratio, 4),
        "unicode_normalization": "NFC-compatible source retained; zero-width/BOM stripped in cleanup.",
        "unicode_normalization_form": "NFC" if cleaned_text == unicodedata.normalize("NFC", cleaned_text) else "NON_NFC",
        "hidden_unicode_counts_raw": hidden_unicode_counts(raw_text),
        "hidden_unicode_counts_cleaned": hidden_unicode_counts(cleaned_text),
        "bom_removed": "\ufeff" in raw_text and "\ufeff" not in cleaned_text,
        "zero_width_characters_removed": sum(hidden_unicode_counts(raw_text).values()) > sum(hidden_unicode_counts(cleaned_text).values()),
        "mojibake_detected": bool(MOJIBAKE_RE.search(raw_text) or MOJIBAKE_RE.search(cleaned_text)),
        "replacement_characters_detected": "�" in raw_text or "�" in cleaned_text,
        "ocr_or_page_header_noise_detected": any(BOILERPLATE_LINE_RE.search(line) for line in raw_text.splitlines()),
        "source_navigation_boilerplate_removed": True,
        "paragraph_count": paragraphs,
        "sentence_count": sentences,
        "character_count": len(cleaned_text),
        "punctuation_preservation": {
            "danda_count": cleaned_text.count("।"),
            "bengali_punctuation_count": cleaned_text.count("।") + cleaned_text.count("॥"),
            "question_mark_count": cleaned_text.count("?") + cleaned_text.count("？"),
            "exclamation_count": cleaned_text.count("!"),
            "em_dash_count": cleaned_text.count("—"),
            "dialogue_mark_count": sum(cleaned_text.count(mark) for mark in ["“", "”", "\"", "‘", "’"]),
            "non_bengali_english_quote_count": len(ENGLISH_QUOTE_RE.findall(cleaned_text)),
        },
        "section_segmentation": {
            "type": "single_short_story",
            "segments": [
                {
                    "id": "kshudhita-pashan-story",
                    "title": TITLE_BN,
                    "character_count": len(cleaned_text),
                    "paragraph_count": paragraphs,
                }
            ],
        },
        "source_markers": markers,
    }


def load_source_text(args: argparse.Namespace) -> SourceLoadResult:
    if args.source_text_file:
        path = Path(args.source_text_file)
        if not path.exists():
            return SourceLoadResult("", source_text_api_url(), "", "", "", "BLOCKED_SOURCE_FILE_MISSING", [str(path)])
        license_data = load_source_license(allow_fetch=args.allow_fetch)
        return SourceLoadResult(
            raw_text=path.read_text(encoding="utf-8"),
            source_text_url=str(path),
            source_license=license_data.get("text", ""),
            source_license_url=license_data.get("url", ""),
            source_retrieved_at=utc_now(),
            load_status="LOADED_LOCAL_SOURCE_TEXT",
            issues=[] if license_data.get("text") else ["source license could not be verified"],
        )

    if not args.allow_fetch:
        return SourceLoadResult(
            "",
            source_text_api_url(),
            "",
            "",
            "",
            "BLOCKED_SOURCE_TEXT_REQUIRED",
            ["Pass --source-text-file or --allow-fetch with EARNALISM_ALLOW_SOURCE_FETCH=true."],
        )
    if os.getenv("EARNALISM_ALLOW_SOURCE_FETCH", "").strip().lower() != "true":
        return SourceLoadResult(
            "",
            source_text_api_url(),
            "",
            "",
            "",
            "BLOCKED_SOURCE_FETCH_NOT_ALLOWED",
            ["--allow-fetch requires EARNALISM_ALLOW_SOURCE_FETCH=true."],
        )

    try:
        parse_data = fetch_json(source_text_api_url())
        license_data = load_source_license(allow_fetch=True)
        parsed_html = parse_data.get("parse", {}).get("text", "")
        raw_text = extract_text_from_parsed_html(parsed_html)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return SourceLoadResult("", source_text_api_url(), "", "", "", "BLOCKED_SOURCE_FETCH_FAILED", [str(exc)])

    return SourceLoadResult(
        raw_text=raw_text,
        source_text_url=source_text_api_url(),
        source_license=license_data.get("text", ""),
        source_license_url=license_data.get("url", ""),
        source_retrieved_at=utc_now(),
        load_status="FETCHED_WIKISOURCE_WITH_EXPLICIT_OPT_IN",
        issues=[] if raw_text and license_data.get("text") else ["source text or license data missing from Wikisource"],
    )


def load_source_license(*, allow_fetch: bool) -> dict[str, str]:
    if not allow_fetch and os.getenv("EARNALISM_ALLOW_SOURCE_FETCH", "").strip().lower() != "true":
        return {}
    try:
        payload = fetch_json(source_license_api_url())
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {}
    rights = payload.get("query", {}).get("rightsinfo", {})
    return {"text": str(rights.get("text", "") or ""), "url": str(rights.get("url", "") or "")}


def candidate_book(evidence: dict[str, Any], qa: dict[str, Any]) -> dict[str, Any]:
    rights_tier = "A" if qa["qa_status"] == "QA_PASSED" else "C"
    verification_status = "approved" if qa["qa_status"] == "QA_PASSED" else "blocked"
    blocked_reason = "" if qa["qa_status"] == "QA_PASSED" else "; ".join(qa["issues"])
    generated_at = evidence["generated_at"]
    rights_metadata = {
        "work_title": TITLE_BN,
        "work_slug": SLUG,
        "author_name": AUTHOR,
        "author_death_year": AUTHOR_DEATH_YEAR,
        "original_publication_year": ORIGINAL_PUBLICATION_YEAR,
        "country_of_origin": "India",
        "source_url": evidence["source_url"],
        "source_name": evidence["source_name"],
        "source_license": evidence["source_license"],
        "source_license_url": evidence.get("source_license_url", ""),
        "attribution_required": evidence.get("attribution_required", True),
        "share_alike_required": evidence.get("share_alike_required", True),
        "attribution_text": evidence.get("attribution_text", ""),
        "license_compliance_status": evidence.get("license_compliance_status", ""),
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": "",
        "rights_tier": rights_tier,
        "verification_status": verification_status,
        "blocked_reason": blocked_reason,
        "publication_region": "global",
        "verified_at": generated_at if verification_status == "approved" else "",
    }
    return {
        "title": TITLE_BN,
        "title_en": TITLE_EN,
        "slug": SLUG,
        "author": AUTHOR,
        "author_death_year": AUTHOR_DEATH_YEAR,
        "original_publication_year": ORIGINAL_PUBLICATION_YEAR,
        "language": LANGUAGE,
        "category_slug": "bengali-gothic",
        "genre": GENRE,
        "is_published": False,
        "audiobook_enabled": False,
        "rights_metadata": rights_metadata,
        "source_hash": evidence["source_hash"],
        "content_hash": evidence["content_hash"],
        "provenance_hash": evidence["provenance_hash"],
        "qa_status": qa["qa_status"],
    }


def build_source_evidence(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = utc_now()
    load = load_source_text(args)
    raw_text = load.raw_text
    cleaned_text = clean_bengali_source_text(raw_text) if raw_text else ""
    source_hash = hash_source(raw_text) if raw_text else ""
    content_hash = hash_source(cleaned_text) if cleaned_text else ""
    provenance_hash = (
        hash_provenance(
            source_url=args.source_url,
            source_name=SOURCE_NAME,
            source_license=load.source_license,
            content_hash=content_hash,
        )
        if args.source_url and SOURCE_NAME and load.source_license and content_hash
        else ""
    )
    qa = text_qa(raw_text, cleaned_text, load.source_license)
    evidence = {
        "generated_at": generated_at,
        "dry_run": True,
        "mutation_performed": False,
        "public_publish_actions": 0,
        "title_bn": TITLE_BN,
        "title_en": TITLE_EN,
        "slug": SLUG,
        "author": AUTHOR,
        "author_bn": AUTHOR_BN,
        "author_death_year": AUTHOR_DEATH_YEAR,
        "original_publication_year": ORIGINAL_PUBLICATION_YEAR,
        "language": LANGUAGE,
        "genre": GENRE,
        "source_url": args.source_url,
        "source_name": SOURCE_NAME,
        "source_license": load.source_license,
        "source_license_url": load.source_license_url or SOURCE_LICENSE_URL_FALLBACK,
        "source_permalink": args.source_url,
        "source_page_oldid": SOURCE_PAGE_OLDID,
        "attribution_required": True,
        "share_alike_required": True,
        "attribution_text": (
            f"{TITLE_BN} ({TITLE_EN}) by {AUTHOR}, source text from {SOURCE_NAME}, "
            f"licensed under {load.source_license or SOURCE_LICENSE_FALLBACK}."
        ),
        "license_compliance_status": (
            "CC_BY_SA_ATTRIBUTION_SHAREALIKE_REQUIRED"
            if "share" in (load.source_license or SOURCE_LICENSE_FALLBACK).lower()
            else "ATTRIBUTION_REVIEW_REQUIRED"
        ),
        "source_text_url": load.source_text_url,
        "source_retrieved_at": load.source_retrieved_at,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "load_status": load.load_status,
        "source_load_issues": load.issues,
        "qa": qa,
        "qa_status": qa["qa_status"],
        "cleaned_text_preview": safe_preview(cleaned_text, PREVIEW_CHARS),
        "raw_text_preview": safe_preview(raw_text, 600),
        "cleaned_text_omitted": True,
        "full_source_text_committed": False,
        "rights_basis": (
            "Rabindranath Tagore died in 1941. Under the India life-plus-60 assumption used by "
            "the Phase 2 rights engine, the original literary work is public domain in India. "
            "This is a Tier A source-backed candidate with CC BY-SA attribution/share-alike compliance required. "
            "It excludes modern translations, illustrations, audio recordings, annotations, film material, and commentary."
        ),
        "rollback_owner": ROLLBACK_OWNER,
        "publication_cap": PUBLICATION_CAP,
        "rollback_plan": "Keep the candidate off public routes; remove pipeline shelf card and generated draft artifacts if gates fail.",
    }
    book = candidate_book(evidence, qa)
    rights_decision = evaluate_rights(book)
    if qa["qa_status"] == "QA_PASSED" and not rights_decision.approved:
        book["rights_metadata"]["rights_tier"] = "C"
        book["rights_metadata"]["verification_status"] = "blocked"
        book["rights_metadata"]["verified_at"] = ""
        book["rights_metadata"]["blocked_reason"] = "; ".join(rights_decision.issues)
        evidence["qa_status"] = "BLOCKED_RIGHTS_QA"
        rights_decision = evaluate_rights(book)
    evidence.update(
        {
            "rights_tier": rights_decision.rights_tier,
            "verification_status": "approved" if rights_decision.approved else book["rights_metadata"]["verification_status"],
            "publication_region": rights_decision.publication_region,
            "rights_decision": {
                "status": rights_decision.status,
                "approved": rights_decision.approved,
                "issues": rights_decision.issues,
                "metadata": rights_decision.metadata,
            },
            "book": book,
        }
    )
    return evidence


def audio_script_window(cleaned_text_preview: str) -> str:
    text = cleaned_text_preview.strip()
    if not text:
        return ""
    return text[:3600]


def preview_sync_chunks(narration: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = []
    cursor = 0
    for row in narration.get("chunks", []):
        preview = str(row.get("text_preview", ""))
        start = cursor
        end = start + len(preview)
        cursor = end
        chunks.append(
            {
                "chunk_id": f"kshudhita-pashan-preview-{int(row.get('index', 0)):02d}",
                "source_text_span": {"start": start, "end": end},
                "estimated_duration_seconds": row.get("estimated_seconds", 0),
                "expected_waveform_placeholder": "PENDING_AUDIO_PROVIDER_OUTPUT",
                "transcript_alignment_placeholder": "PENDING_STT_ALIGNMENT",
                "qa_status": "PENDING_AUDIO_QA",
            }
        )
    return chunks


def build_audio_preview_plan(evidence: dict[str, Any]) -> dict[str, Any]:
    approved = evidence.get("rights_tier") == "A" and evidence.get("verification_status") == "approved"
    source_text = audio_script_window(str(evidence.get("cleaned_text_preview") or ""))
    plans = {}
    for mode in ("preview_30s", "preview_90s", "preview_3m"):
        result = plan_audiobook_pipeline(
            AudiobookPipelineInput(
                book_slug=SLUG,
                title=TITLE_BN,
                source_text=source_text,
                language="bn",
                generation_mode=mode,
                provider="ai4bharat_indic_tts",
                linked_approved_book=approved,
                rights_tier=evidence.get("rights_tier", ""),
                verification_status=evidence.get("verification_status", ""),
                action_status="READY_FOR_GENERATION" if approved else "READY_FOR_RIGHTS_REVIEW",
                ingestion_status="CLEANED" if approved else "BLOCKED_SOURCE",
                edition_generation_status="READY_FOR_REVIEW" if approved else "BLOCKED_UPSTREAM_SOURCE",
                source_hash=evidence.get("source_hash", ""),
                content_hash=evidence.get("content_hash", ""),
                provenance_hash=evidence.get("provenance_hash", ""),
                dry_run=True,
                pronunciation_dictionary={},
                max_chunk_chars=900,
            )
        )
        row = result.as_dict(include_text=False, text_preview_chars=420)
        row["sync_plan"] = preview_sync_chunks(row.get("narration_script", {}))
        row["pronunciation_guide_attached"] = True
        plans[mode] = row
    public_audio_status = "AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA"
    return {
        "generated_at": utc_now(),
        "dry_run": True,
        "mutation_performed": False,
        "audio_file_created": False,
        "production_storage_upload": False,
        "book_slug": SLUG,
        "voice_identity": (
            "Refined female Bengali literary narrator; warm, intelligent, calm, expressive, "
            "punctuation-aware, emotionally restrained, haunted without theatrical overacting."
        ),
        "preview_lengths": ["30-second sample", "90-second sample", "3-minute sample"],
        "preferred_provider_route": "Bengali Indic TTS / AI4Bharat-compatible metadata hook first; OpenAI TTS fallback only after quality validation.",
        "manual_upload_fallback": "Metadata-only; uploaded files must pass QA before any public surface.",
        "pronunciation_dictionary": PRONUNCIATION_TERMS,
        "provider_plans": plans,
        "audio_preview_status": public_audio_status,
        "full_audiobook_status": "BLOCKED_FULL_AUDIO_QA_REQUIRED",
        "public_cta_status": {
            "listen_now": "BLOCKED",
            "full_audiobook": "BLOCKED",
            "audio_preview": "BLOCKED_UNTIL_PROVIDER_QA",
        },
        "required_public_audio_gates": [
            "linked book is rights approved",
            "audio script matches source text",
            "Bengali pronunciation dictionary prepared",
            "TTS/provider output exists",
            "transcript comparison passes",
            "word error rate below threshold",
            "no missing paragraphs",
            "no repeated lines",
            "no clipping",
            "no long silence",
            "loudness normalized",
            "waveform/timestamps generated",
            "mobile playback verified",
            "file size acceptable",
            "human spot-check sample completed",
        ],
    }


def candidate_score(evidence: dict[str, Any], audio_plan: dict[str, Any]) -> dict[str, Any]:
    score = 9.0
    if not evidence.get("source_hash") or not evidence.get("content_hash") or not evidence.get("provenance_hash"):
        score = min(score, 7.5)
    if evidence.get("rights_tier") != "A" or evidence.get("verification_status") != "approved":
        score = min(score, 7.5)
    if evidence.get("qa_status") != "QA_PASSED":
        score = min(score, 8.0)
    audio_score = 8.0 if audio_plan.get("audio_preview_status") == "AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA" else 7.0
    if score >= 8.5:
        recommendation = "READY_FOR_AUDIO_PREVIEW_PLANNING"
    else:
        recommendation = "HOLD_FOR_FIXES"
    return {
        "candidate_score": round(score, 2),
        "audio_preview_score": audio_score,
        "recommendation": recommendation,
        "candidate_status": "KEEP_AS_PIPELINE_CANDIDATE",
        "controlled_reading_status": (
            "READY_FOR_CONTROLLED_BENGALI_READING_APPROVAL"
            if score >= 8.5
            else "HOLD_FOR_FIXES"
        ),
    }


def render_reports(evidence: dict[str, Any], audio_plan: dict[str, Any], score: dict[str, Any]) -> dict[str, str]:
    approved = evidence.get("verification_status") == "approved"
    return {
        "KSHUDHITA_PASHAN_SOURCE_RIGHTS_REPORT.md": "\n".join(
            [
                "# Kshudhita Pashan Source Rights Report",
                "",
                f"Status: `{'PASS' if approved else 'HOLD_FOR_FIXES'}`",
                "",
                f"- Bengali title: `{TITLE_BN}`",
                f"- English title: `{TITLE_EN}`",
                f"- Source: `{evidence.get('source_name')}`",
                f"- Source URL: `{evidence.get('source_url')}`",
                f"- Source license: `{evidence.get('source_license')}`",
                f"- Source license URL: `{evidence.get('source_license_url')}`",
                f"- Source permalink: `{evidence.get('source_permalink')}`",
                f"- Source page oldid: `{evidence.get('source_page_oldid') or 'Not captured; permalink capture required before publication.'}`",
                f"- Attribution required: `{evidence.get('attribution_required')}`",
                f"- Share-alike required: `{evidence.get('share_alike_required')}`",
                f"- Attribution text: `{evidence.get('attribution_text')}`",
                f"- License compliance status: `{evidence.get('license_compliance_status')}`",
                f"- Source hash: `{evidence.get('source_hash')}`",
                f"- Content hash: `{evidence.get('content_hash')}`",
                f"- Provenance hash: `{evidence.get('provenance_hash')}`",
                f"- QA status: `{evidence.get('qa_status')}`",
                "",
                "Tier A source-backed candidate with CC BY-SA attribution/share-alike compliance required.",
                "",
                "No full source text is committed in this report.",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_RIGHTS_DECISION.md": "\n".join(
            [
                "# Kshudhita Pashan Rights Decision",
                "",
                f"Decision: `{'APPROVED_TIER_A_DRAFT_CANDIDATE' if approved else 'BLOCKED_RIGHTS_REVIEW_REQUIRED'}`",
                "",
                f"- Rights tier: `{evidence.get('rights_tier')}`",
                f"- Verification status: `{evidence.get('verification_status')}`",
                f"- Publication region: `{evidence.get('publication_region')}`",
                f"- Author death year: `{AUTHOR_DEATH_YEAR}`",
                f"- Original publication year: `{ORIGINAL_PUBLICATION_YEAR}`",
                f"- Source license URL: `{evidence.get('source_license_url')}`",
                f"- Attribution required: `{evidence.get('attribution_required')}`",
                f"- Share-alike required: `{evidence.get('share_alike_required')}`",
                f"- License compliance status: `{evidence.get('license_compliance_status')}`",
                "",
                "This decision treats Kshudhita Pashan as a Tier A source-backed candidate with CC BY-SA attribution/share-alike compliance required, not as an unrestricted global publication bundle.",
                "",
                "Modern translations, illustrations, audio recordings, annotations, film adaptations, and editorial notes are excluded and remain separate rights objects.",
                "",
                "Rights engine issues:",
                "",
                *[f"- {issue}" for issue in evidence.get("rights_decision", {}).get("issues", []) or ["None"]],
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_AUDIO_PREVIEW_PLAN.md": "\n".join(
            [
                "# Kshudhita Pashan Audio Preview Plan",
                "",
                f"Status: `{audio_plan.get('audio_preview_status')}`",
                "",
                "- No audio file was generated.",
                "- No TTS/STT/FFmpeg provider was called.",
                "- No production storage upload was performed.",
                "- Actual generation/public preview status: `AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA`.",
                f"- Full audiobook status: `{audio_plan.get('full_audiobook_status')}`",
                "",
                "Preview targets:",
                "",
                *[f"- {item}" for item in audio_plan.get("preview_lengths", [])],
                "",
                "Preferred provider route: Bengali Indic TTS / AI4Bharat-compatible hook first; OpenAI TTS fallback only after quality validation.",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_PRONUNCIATION_GUIDE.md": "\n".join(
            [
                "# Kshudhita Pashan Pronunciation Guide",
                "",
                "| Word | Pronunciation hint | Context | Confidence | Human spot-check |",
                "| --- | --- | --- | --- | --- |",
                *[
                    f"| {item['word']} | {item['pronunciation_hint']} | {item['context']} | {item['confidence']} | {item['requires_human_spot_check']} |"
                    for item in PRONUNCIATION_TERMS
                ],
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_AUDIO_QA_CHECKLIST.md": "\n".join(
            [
                "# Kshudhita Pashan Audio QA Checklist",
                "",
                "Audio preview cannot become public until every gate below passes:",
                "",
                *[f"- [ ] {gate}" for gate in audio_plan.get("required_public_audio_gates", [])],
                "",
                f"Current full audiobook status: `{audio_plan.get('full_audiobook_status')}`",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_LANDING_DRAFT.md": "\n".join(
            [
                "# Bengali Gothic Premiere: ক্ষুধিত পাষাণ",
                "",
                "After Dracula, enter a haunted Bengali palace.",
                "",
                "Read beautifully. Listen carefully.",
                "",
                "Allowed CTAs: Notify Me, Preview Coming Soon, Join Bengali Gothic Reading Circle, Hear the Voice Sample Soon.",
                "",
                "Blocked CTAs until gates pass: Start Reading, Listen Now, Full Audiobook.",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_CAMPAIGN_DRAFT.md": "\n".join(
            [
                "# Kshudhita Pashan Campaign Draft",
                "",
                "- Campaign line: Bengali Gothic Premiere: ক্ষুধিত পাষাণ",
                "- Mood bridge: After Dracula, enter a haunted Bengali palace.",
                "- CTA set: Notify Me / Follow Pipeline / Hear the Voice Sample Soon.",
                "- Safety: no ads, emails, social posts, or public publishing in this PR.",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_GROWTH_LOOP_DRAFT.md": "\n".join(
            [
                "# Kshudhita Pashan Growth Loop Draft",
                "",
                "Dry-run growth loop only:",
                "",
                "- Measure Bengali gothic pipeline interest.",
                "- Collect non-PII CTA intent events.",
                "- Hold publication until source, rights, text QA, and audio QA gates pass.",
                "- Keep Dracula as the only live controlled title until explicitly changed.",
                "",
            ]
        ),
        "BENGALI_GOTHIC_INTEREST_DASHBOARD.md": "\n".join(
            [
                "# Bengali Gothic Interest Dashboard",
                "",
                "Mock-safe event names:",
                "",
                "- `bengali_gothic_pipeline_view`",
                "- `kshudhita_pashan_notify_click`",
                "- `kshudhita_pashan_audio_interest_click`",
                "- `bengali_voice_sample_interest`",
                "- `bengali_gothic_reading_circle_click`",
                "",
                "No PII is required. No real analytics calls are made by tests.",
                "",
            ]
        ),
        "KSHUDHITA_PASHAN_ONBOARDING_REPORT.md": "\n".join(
            [
                "# Kshudhita Pashan Onboarding Report",
                "",
                f"Recommendation: `{score.get('recommendation')}`",
                "",
                f"- Candidate score: `{score.get('candidate_score')}`",
                f"- Audio preview score: `{score.get('audio_preview_score')}`",
                f"- Candidate status: `{score.get('candidate_status')}`",
                f"- Controlled reading status: `{score.get('controlled_reading_status')}`",
                f"- Audio preview status: `{audio_plan.get('audio_preview_status')}`",
                "- Actual generation/public preview: `AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA`",
                f"- Full audiobook status: `{audio_plan.get('full_audiobook_status')}`",
                "",
                "No publication, production storage upload, live payment, TTS, STT, LLM, image, email, or social call was performed.",
                "",
            ]
        ),
        "PHASE15_BENGALI_GOTHIC_AUDIO_READINESS_REPORT.md": "\n".join(
            [
                "# Phase 15 Bengali Gothic Audio Readiness Report",
                "",
                f"Final recommendation: `{score.get('recommendation')}`",
                "",
                f"- Source evidence status: `{evidence.get('qa_status')}`",
                f"- Rights decision: `{evidence.get('verification_status')}`",
                f"- Audio preview status: `{audio_plan.get('audio_preview_status')}`",
                "- Actual generation/public preview: `AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA`",
                f"- Full audiobook status: `{audio_plan.get('full_audiobook_status')}`",
                "- Claim ceiling: no 10/10 score until actual audio, sync, waveform, transcript QA, and human spot-check pass.",
                "",
            ]
        ),
    }


def write_outputs(evidence: dict[str, Any], audio_plan: dict[str, Any], score: dict[str, Any]) -> None:
    source_record = {
        "title_bn": TITLE_BN,
        "title_en": TITLE_EN,
        "slug": SLUG,
        "author": AUTHOR,
        "author_death_year": AUTHOR_DEATH_YEAR,
        "original_publication_year": ORIGINAL_PUBLICATION_YEAR,
        "language": LANGUAGE,
        "genre": GENRE,
        "source_url": evidence.get("source_url", ""),
        "source_name": evidence.get("source_name", ""),
        "source_license": evidence.get("source_license", ""),
        "source_license_url": evidence.get("source_license_url", ""),
        "source_permalink": evidence.get("source_permalink", ""),
        "source_page_oldid": evidence.get("source_page_oldid", ""),
        "attribution_required": evidence.get("attribution_required", True),
        "share_alike_required": evidence.get("share_alike_required", True),
        "attribution_text": evidence.get("attribution_text", ""),
        "license_compliance_status": evidence.get("license_compliance_status", ""),
        "source_text_url": evidence.get("source_text_url", ""),
        "source_retrieved_at": evidence.get("source_retrieved_at", ""),
        "source_hash": evidence.get("source_hash", ""),
        "content_hash": evidence.get("content_hash", ""),
        "provenance_hash": evidence.get("provenance_hash", ""),
        "rights_tier": evidence.get("rights_tier", ""),
        "verification_status": evidence.get("verification_status", ""),
        "publication_region": evidence.get("publication_region", ""),
        "qa_status": evidence.get("qa_status", ""),
        "rollback_owner": ROLLBACK_OWNER,
        "publication_cap": PUBLICATION_CAP,
        "full_source_text_committed": False,
    }
    write_json(DATA_DIR / f"{SLUG}.source.json", source_record)
    write_json(OUTPUT_DIR / "source_evidence.json", evidence)
    write_json(
        OUTPUT_DIR / "source_hashes.json",
        {
            "source_hash": evidence.get("source_hash", ""),
            "content_hash": evidence.get("content_hash", ""),
            "provenance_hash": evidence.get("provenance_hash", ""),
            "hash_policy": "source_hash=sha256(raw extracted source text); content_hash=sha256(cleaned text); provenance_hash=sha256(source_url + source_name + source_license + content_hash)",
        },
    )
    write_json(
        OUTPUT_DIR / "rights_evidence.json",
        {
            "rights_basis": evidence.get("rights_basis", ""),
            "source_license_url": evidence.get("source_license_url", ""),
            "source_permalink": evidence.get("source_permalink", ""),
            "source_page_oldid": evidence.get("source_page_oldid", ""),
            "attribution_required": evidence.get("attribution_required", True),
            "share_alike_required": evidence.get("share_alike_required", True),
            "attribution_text": evidence.get("attribution_text", ""),
            "license_compliance_status": evidence.get("license_compliance_status", ""),
            "rights_tier": evidence.get("rights_tier", ""),
            "verification_status": evidence.get("verification_status", ""),
            "publication_region": evidence.get("publication_region", ""),
            "rights_decision": evidence.get("rights_decision", {}),
            "excluded_rights_objects": [
                "modern translations",
                "illustrations",
                "audio recordings",
                "annotations",
                "film adaptations",
                "editorial notes",
            ],
        },
    )
    write_json(OUTPUT_DIR / "audio_preview_plan.json", audio_plan)
    for filename, body in render_reports(evidence, audio_plan, score).items():
        write_text(ROOT / filename, body)


def build(args: argparse.Namespace) -> dict[str, Any]:
    evidence = build_source_evidence(args)
    audio_plan = build_audio_preview_plan(evidence)
    score = candidate_score(evidence, audio_plan)
    write_outputs(evidence, audio_plan, score)
    return {"evidence": evidence, "audio_plan": audio_plan, "score": score}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Kshudhita Pashan as a dry-run Bengali gothic candidate.")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--source-text-file", default="")
    parser.add_argument("--allow-fetch", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args(argv)
    if args.slug != SLUG:
        parser.error(f"Only {SLUG} is supported by this controlled candidate script.")
    if args.dry_run is not True:
        parser.error("Bengali candidate preparation is dry-run only.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = build(args)
    score = result["score"]
    print(f"Kshudhita Pashan candidate status: {score['recommendation']}")
    print(f"Source QA: {result['evidence'].get('qa_status')}")
    print(f"Rights: {result['evidence'].get('rights_tier')} / {result['evidence'].get('verification_status')}")
    print(f"Audio preview: {result['audio_plan'].get('audio_preview_status')}")
    print(f"Report: {ROOT / 'KSHUDHITA_PASHAN_ONBOARDING_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
