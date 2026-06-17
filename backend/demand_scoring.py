from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


LAUNCH_PRIORITY_SEEDS = [
    "Anandamath",
    "Devdas",
    "Abol Tabol",
    "Sultana's Dream",
    "Sherlock Holmes",
    "Dracula",
    "Frankenstein",
    "Tagore Short Stories",
    "Calculus Made Easy",
    "Chander Pahar",
]

SEED_ALIASES = {
    "sultanas-dream": "sultana's dream",
    "sultana-s-dream": "sultana's dream",
    "tagore-short-stories": "tagore short stories",
}

REPORT_COLUMNS = [
    "priority_rank",
    "slug",
    "title",
    "category_slug",
    "language",
    "demand_score",
    "recommended_product_format",
    "growth_rationale",
    "page_views",
    "reading_starts",
    "reading_completions",
    "category_fit",
    "bengali_cultural_fit",
    "school_college_usefulness",
    "young_reader_usefulness",
    "seo_potential",
    "audiobook_potential",
    "visual_study_potential",
    "production_complexity",
    "rights_risk",
]


@dataclass
class DemandScore:
    slug: str
    title: str
    category_slug: str
    language: str
    demand_score: float
    priority_rank: int = 0
    growth_rationale: str = ""
    recommended_product_format: str = ""
    page_views: int = 0
    reading_starts: int = 0
    reading_completions: int = 0
    category_fit: float = 0
    bengali_cultural_fit: float = 0
    school_college_usefulness: float = 0
    young_reader_usefulness: float = 0
    seo_potential: float = 0
    audiobook_potential: float = 0
    visual_study_potential: float = 0
    production_complexity: float = 0
    rights_risk: float = 0
    source_signals: dict[str, Any] = field(default_factory=dict)

    def as_row(self) -> dict[str, Any]:
        return {
            "priority_rank": self.priority_rank,
            "slug": self.slug,
            "title": self.title,
            "category_slug": self.category_slug,
            "language": self.language,
            "demand_score": f"{self.demand_score:.2f}",
            "recommended_product_format": self.recommended_product_format,
            "growth_rationale": self.growth_rationale,
            "page_views": self.page_views,
            "reading_starts": self.reading_starts,
            "reading_completions": self.reading_completions,
            "category_fit": f"{self.category_fit:.1f}",
            "bengali_cultural_fit": f"{self.bengali_cultural_fit:.1f}",
            "school_college_usefulness": f"{self.school_college_usefulness:.1f}",
            "young_reader_usefulness": f"{self.young_reader_usefulness:.1f}",
            "seo_potential": f"{self.seo_potential:.1f}",
            "audiobook_potential": f"{self.audiobook_potential:.1f}",
            "visual_study_potential": f"{self.visual_study_potential:.1f}",
            "production_complexity": f"{self.production_complexity:.1f}",
            "rights_risk": f"{self.rights_risk:.1f}",
        }


def seed_books() -> list[dict[str, Any]]:
    return [
        {
            "title": "Anandamath",
            "slug": "anandamath",
            "category_slug": "literary-fiction",
            "language": "ben",
            "page_views": 0,
            "reading_starts": 0,
            "reading_completions": 0,
            "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
        },
        {
            "title": "Devdas",
            "slug": "devdas",
            "category_slug": "literary-fiction",
            "language": "ben",
            "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
        },
        {
            "title": "Abol Tabol",
            "slug": "abol-tabol",
            "category_slug": "young-readers",
            "language": "ben",
            "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
        },
        {
            "title": "Sultana's Dream",
            "slug": "sultanas-dream",
            "category_slug": "science-fiction",
            "language": "en",
            "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"},
        },
        {
            "title": "Sherlock Holmes",
            "slug": "sherlock-holmes",
            "category_slug": "mystery",
            "language": "en",
            "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"},
        },
        {
            "title": "Dracula",
            "slug": "dracula",
            "category_slug": "gothic-fiction",
            "language": "en",
            "audiobook_enabled": True,
            "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"},
        },
        {
            "title": "Frankenstein",
            "slug": "frankenstein",
            "category_slug": "gothic-fiction",
            "language": "en",
            "audiobook_enabled": True,
            "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"},
        },
        {
            "title": "Tagore Short Stories",
            "slug": "tagore-short-stories",
            "category_slug": "literary-fiction",
            "language": "ben",
            "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
        },
        {
            "title": "Calculus Made Easy",
            "slug": "calculus-made-easy",
            "category_slug": "study-material",
            "language": "en",
            "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"},
        },
        {
            "title": "Chander Pahar",
            "slug": "chander-pahar",
            "category_slug": "adventure",
            "language": "ben",
            "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
        },
    ]


def rank_demand(books: Iterable[dict[str, Any]]) -> list[DemandScore]:
    scored = [score_book(book) for book in books]
    scored.sort(key=lambda item: (-item.demand_score, item.title.lower()))
    for index, item in enumerate(scored, start=1):
        item.priority_rank = index
    return scored


def score_book(book: dict[str, Any]) -> DemandScore:
    title = _text(book.get("title") or book.get("work_title") or "Untitled")
    slug = _slug(book, title)
    category_slug = _text(book.get("category_slug") or book.get("category") or "")
    language = _language(book)
    page_views = _metric(book, "page_views", "views", "internal_page_views")
    reading_starts = _metric(book, "reading_starts", "starts", "reader_starts")
    reading_completions = _metric(book, "reading_completions", "completions", "reader_completions")

    category_fit = _category_fit(title, category_slug)
    bengali_cultural_fit = _bengali_cultural_fit(title, language, category_slug)
    school_college_usefulness = _school_college_usefulness(title, category_slug)
    young_reader_usefulness = _young_reader_usefulness(title, category_slug)
    seo_potential = _seo_potential(title, category_slug, language)
    audiobook_potential = _audiobook_potential(title, category_slug, language, book)
    visual_study_potential = _visual_study_potential(title, category_slug, language)
    production_complexity = _production_complexity(title, category_slug, language, book)
    rights_risk = _rights_risk(book)

    engagement = (
        _log_points(page_views, 12)
        + _log_points(reading_starts, 10)
        + _log_points(reading_completions, 8)
    )
    seed_bonus = 8 if _is_launch_seed(title, slug) else 0
    positive = (
        engagement
        + category_fit
        + bengali_cultural_fit
        + school_college_usefulness
        + young_reader_usefulness
        + seo_potential
        + audiobook_potential
        + visual_study_potential
        + seed_bonus
    )
    penalty = (production_complexity * 1.15) + (rights_risk * 1.35)
    demand_score = max(0, min(100, positive - penalty))

    score = DemandScore(
        slug=slug,
        title=title,
        category_slug=category_slug,
        language=language,
        demand_score=round(demand_score, 2),
        growth_rationale=_growth_rationale(
            seed_bonus=seed_bonus,
            bengali_cultural_fit=bengali_cultural_fit,
            school_college_usefulness=school_college_usefulness,
            seo_potential=seo_potential,
            audiobook_potential=audiobook_potential,
            visual_study_potential=visual_study_potential,
            production_complexity=production_complexity,
            rights_risk=rights_risk,
        ),
        recommended_product_format=_recommended_product_format(
            bengali_cultural_fit=bengali_cultural_fit,
            school_college_usefulness=school_college_usefulness,
            young_reader_usefulness=young_reader_usefulness,
            audiobook_potential=audiobook_potential,
            visual_study_potential=visual_study_potential,
        ),
        page_views=page_views,
        reading_starts=reading_starts,
        reading_completions=reading_completions,
        category_fit=category_fit,
        bengali_cultural_fit=bengali_cultural_fit,
        school_college_usefulness=school_college_usefulness,
        young_reader_usefulness=young_reader_usefulness,
        seo_potential=seo_potential,
        audiobook_potential=audiobook_potential,
        visual_study_potential=visual_study_potential,
        production_complexity=production_complexity,
        rights_risk=rights_risk,
    )
    return score


def demand_report_csv(scores: list[DemandScore]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for score in scores:
        writer.writerow(score.as_row())
    return output.getvalue()


def demand_report_markdown(scores: list[DemandScore], *, top_n: int = 10) -> str:
    lines = [
        "# Demand Priority Report",
        "",
        "Deterministic dry-run ranking for growth prioritization before content-generation spend.",
        "",
        "## Top Recommendations",
        "",
        "| Rank | Book / Topic | Score | Recommended Format | Rationale |",
        "|---:|---|---:|---|---|",
    ]
    for score in scores[:top_n]:
        lines.append(
            f"| {score.priority_rank} | {score.title} | {score.demand_score:.2f} | "
            f"{score.recommended_product_format} | {score.growth_rationale} |"
        )
    lines.extend(
        [
            "",
            "## Scoring Notes",
            "",
            "- No LLM, TTS, image, or paid API calls are used.",
            "- Rights risk lowers score.",
            "- Production complexity lowers score.",
            "- Internal page views, reading starts, and completions are used when present.",
            "- Missing internal engagement data is treated as zero rather than fabricated.",
            "",
            f"Total ranked items: {len(scores)}",
            "",
        ]
    )
    return "\n".join(lines)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slug(book: dict[str, Any], title: str) -> str:
    slug = _text(book.get("slug") or book.get("work_slug"))
    if slug:
        return slug
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"


def _language(book: dict[str, Any]) -> str:
    value = _text(book.get("language") or book.get("lang")).lower()
    if value in {"bn", "ben", "bengali"}:
        return "ben"
    if value in {"en", "eng", "english"}:
        return "en"
    title = _text(book.get("title"))
    return "ben" if any("\u0980" <= char <= "\u09ff" for char in title) else value


def _metric(book: dict[str, Any], *names: str) -> int:
    metrics = book.get("metrics") if isinstance(book.get("metrics"), dict) else {}
    analytics = book.get("analytics") if isinstance(book.get("analytics"), dict) else {}
    for name in names:
        for source in (book, metrics, analytics):
            if name in source:
                return _non_negative_int(source.get(name))
    return 0


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def _log_points(value: int, maximum: float) -> float:
    if value <= 0:
        return 0
    return min(maximum, math.log10(value + 1) / 4 * maximum)


def _is_launch_seed(title: str, slug: str) -> bool:
    normalized_title = _normalize_key(title)
    normalized_slug = SEED_ALIASES.get(_normalize_key(slug), _normalize_key(slug))
    seeds = {_normalize_key(seed) for seed in LAUNCH_PRIORITY_SEEDS}
    return normalized_title in seeds or normalized_slug in seeds


def _normalize_key(value: str) -> str:
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9']+", "-", value)
    return value.strip("-")


def _category_fit(title: str, category_slug: str) -> float:
    value = f"{title} {category_slug}".lower()
    if any(token in value for token in ("literary", "gothic", "science-fiction", "adventure", "young")):
        return 8.5
    if any(token in value for token in ("study", "calculus", "school", "college")):
        return 8
    if any(token in value for token in ("business", "self", "history")):
        return 6.5
    return 5


def _bengali_cultural_fit(title: str, language: str, category_slug: str) -> float:
    value = f"{title} {category_slug}".lower()
    if language == "ben":
        return 9.5
    if any(token in value for token in ("tagore", "anandamath", "devdas", "chander", "sultana")):
        return 8
    return 2


def _school_college_usefulness(title: str, category_slug: str) -> float:
    value = f"{title} {category_slug}".lower()
    if any(token in value for token in ("calculus", "study", "school", "college")):
        return 9.5
    if any(token in value for token in ("sherlock", "frankenstein", "dracula", "tagore", "sultana")):
        return 6.5
    return 4


def _young_reader_usefulness(title: str, category_slug: str) -> float:
    value = f"{title} {category_slug}".lower()
    if any(token in value for token in ("abol", "young", "chander", "adventure")):
        return 8.5
    if any(token in value for token in ("sherlock", "frankenstein", "tagore")):
        return 5.5
    return 3


def _seo_potential(title: str, category_slug: str, language: str) -> float:
    value = f"{title} {category_slug}".lower()
    score = 5
    if _is_launch_seed(title, ""):
        score += 2.5
    if any(token in value for token in ("dracula", "frankenstein", "sherlock", "calculus")):
        score += 3
    if language == "ben" or any(token in value for token in ("bengali", "tagore")):
        score += 2
    return min(10, score)


def _audiobook_potential(title: str, category_slug: str, language: str, book: dict[str, Any]) -> float:
    value = f"{title} {category_slug}".lower()
    score = 4
    if book.get("audiobook_enabled") or book.get("generate_audiobook") or book.get("audiobook_assets"):
        score += 2
    if any(token in value for token in ("dracula", "frankenstein", "sherlock", "devdas", "tagore", "anandamath")):
        score += 3
    if language == "ben":
        score += 1
    return min(10, score)


def _visual_study_potential(title: str, category_slug: str, language: str) -> float:
    value = f"{title} {category_slug}".lower()
    score = 3
    if any(token in value for token in ("calculus", "study")):
        score += 5
    if any(token in value for token in ("abol", "chander", "frankenstein", "dracula")):
        score += 3
    if language == "ben":
        score += 1
    return min(10, score)


def _production_complexity(title: str, category_slug: str, language: str, book: dict[str, Any]) -> float:
    value = f"{title} {category_slug}".lower()
    word_count = _non_negative_int(book.get("word_count") or book.get("estimated_word_count"))
    chapter_count = _non_negative_int(book.get("chapter_count") or len(book.get("chapters") or []))
    score = 3
    if word_count > 120_000 or chapter_count > 40:
        score += 4
    elif word_count > 60_000 or chapter_count > 20:
        score += 2
    if any(token in value for token in ("calculus", "study")):
        score += 3
    if language == "ben":
        score += 1.5
    if not (book.get("cover_image_url") or book.get("cover_url")):
        score += 1
    return min(10, score)


def _rights_risk(book: dict[str, Any]) -> float:
    metadata = book.get("rights_metadata") if isinstance(book.get("rights_metadata"), dict) else {}
    tier = _text(metadata.get("rights_tier")).upper().replace("TIER ", "")
    status = _text(metadata.get("verification_status")).lower()
    source_url = _text(metadata.get("source_url"))
    blocked_reason = _text(metadata.get("blocked_reason"))
    if tier == "C" or blocked_reason:
        return 10
    risk = 2
    if not metadata:
        risk += 4
    if status not in {"approved", "verified"}:
        risk += 3
    if not source_url:
        risk += 1.5
    if tier == "B":
        risk += 2
    return min(10, risk)


def _growth_rationale(
    *,
    seed_bonus: float,
    bengali_cultural_fit: float,
    school_college_usefulness: float,
    seo_potential: float,
    audiobook_potential: float,
    visual_study_potential: float,
    production_complexity: float,
    rights_risk: float,
) -> str:
    reasons: list[str] = []
    if seed_bonus:
        reasons.append("launch-priority seed")
    if bengali_cultural_fit >= 8:
        reasons.append("strong Bengali/cultural fit")
    if school_college_usefulness >= 8:
        reasons.append("school/college utility")
    if seo_potential >= 8:
        reasons.append("strong SEO surface")
    if audiobook_potential >= 8:
        reasons.append("audiobook upside")
    if visual_study_potential >= 8:
        reasons.append("visual-study potential")
    if production_complexity >= 8:
        reasons.append("complex production")
    if rights_risk >= 7:
        reasons.append("rights risk requires caution")
    return "; ".join(reasons or ["balanced baseline demand signals"])


def _recommended_product_format(
    *,
    bengali_cultural_fit: float,
    school_college_usefulness: float,
    young_reader_usefulness: float,
    audiobook_potential: float,
    visual_study_potential: float,
) -> str:
    if school_college_usefulness >= 8 and visual_study_potential >= 8:
        return "Visual study guide + reader"
    if bengali_cultural_fit >= 8 and audiobook_potential >= 8:
        return "Bengali reader + audiobook"
    if young_reader_usefulness >= 8 and visual_study_potential >= 7:
        return "Illustrated young-reader edition"
    if audiobook_potential >= 8:
        return "Audiobook-first reader"
    if visual_study_potential >= 8:
        return "Visual explainer + reader"
    return "SEO landing page + reader preview"
