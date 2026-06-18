from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


PROMPT_VERSION = "earnalism-edition-v1"
MODEL_VERSION = "deterministic-template-v1"
DEFAULT_MAX_SECTIONS_PER_RUN = 4
DEFAULT_MAX_GENERATION_BUDGET = 10_000
MAX_SOURCE_CHARS = 8_000

SECTION_ORDER = [
    "clean_reading_edition",
    "chapter_summary",
    "character_map",
    "historical_context",
    "glossary",
    "themes",
    "quiz",
    "seven_day_reading_plan",
    "teacher_parent_notes",
    "why_this_book_matters_today",
    "audiobook_ready_script",
    "seo_copy",
    "landing_page_copy",
    "social_excerpts",
]

REQUIRED_METADATA_FIELDS = ["title", "source_hash", "source_name", "source_url", "source_license"]
ADULT_RISK_RE = re.compile(r"\b(suicide|explicit|erotic|torture|graphic)\b", re.IGNORECASE)
CHARACTER_NAME_RE = re.compile(r"\b(?:Mr|Mrs|Miss|Dr|Professor)\.?\s+[A-Z][A-Za-z]+|\b[A-Z][a-z]{3,}\b")


@dataclass(frozen=True)
class EditionTemplate:
    section_id: str
    title: str
    prompt: str
    renderer: Callable[["EditionContext"], str]


@dataclass
class EditionContext:
    title: str
    author: str
    language: str
    source_name: str
    source_url: str
    source_license: str
    source_hash: str
    source_excerpt: str
    sentences: list[str]
    keywords: list[str]

    @property
    def source_note(self) -> str:
        return f"Source note: prepared from {self.source_name} ({self.source_url}); license: {self.source_license}."


@dataclass
class EditionGenerationState:
    source_hash: str
    prompt_version: str = PROMPT_VERSION
    model_version: str = MODEL_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quality_score: float = 0
    qa_status: str = "PENDING"

    def cache_key(self) -> str:
        return generation_cache_key(
            source_hash=self.source_hash,
            prompt_version=self.prompt_version,
            model_version=self.model_version,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_hash": self.source_hash,
            "prompt_version": self.prompt_version,
            "model_version": self.model_version,
            "generated_at": self.generated_at,
            "quality_score": round(self.quality_score, 2),
            "qa_status": self.qa_status,
            "cache_key": self.cache_key(),
        }


@dataclass
class EditionGenerationInput:
    title: str
    cleaned_text: str
    source_hash: str
    source_name: str
    source_url: str
    source_license: str
    author: str = ""
    language: str = "en"
    requested_sections: list[str] = field(default_factory=lambda: list(SECTION_ORDER))
    existing_cache_keys: set[str] = field(default_factory=set)
    max_sections_per_run: int = DEFAULT_MAX_SECTIONS_PER_RUN
    max_generation_budget: int = DEFAULT_MAX_GENERATION_BUDGET
    dry_run: bool = True


@dataclass
class EditionGenerationResult:
    state: EditionGenerationState
    sections: dict[str, str]
    requested_sections: list[str]
    generated_sections: list[str]
    skipped_sections: list[str]
    qa: dict[str, Any]
    cost_controls: dict[str, Any]
    generation_status: str
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.as_dict(),
            "sections": self.sections,
            "requested_sections": self.requested_sections,
            "generated_sections": self.generated_sections,
            "skipped_sections": self.skipped_sections,
            "qa": self.qa,
            "cost_controls": self.cost_controls,
            "generation_status": self.generation_status,
            "dry_run": self.dry_run,
        }


def generate_edition(payload: EditionGenerationInput) -> EditionGenerationResult:
    validate_input(payload)
    state = EditionGenerationState(source_hash=payload.source_hash)
    requested_sections = normalize_requested_sections(payload.requested_sections)
    cache_key = state.cache_key()
    if cache_key in payload.existing_cache_keys:
        state.qa_status = "SKIPPED_UNCHANGED"
        return EditionGenerationResult(
            state=state,
            sections={},
            requested_sections=requested_sections,
            generated_sections=[],
            skipped_sections=requested_sections,
            qa={
                "missing_sections": requested_sections,
                "hallucination_risk": False,
                "citation_source_coverage": 0,
                "readability_score": 0,
                "age_appropriateness_flag": False,
                "qa_issues": ["source_hash, prompt_version, and model_version are unchanged; generation skipped."],
            },
            cost_controls=cost_control_summary(payload, budget_used=0),
            generation_status="SKIPPED_UNCHANGED",
            dry_run=payload.dry_run,
        )

    context = build_context(payload)
    sections: dict[str, str] = {}
    generated_sections: list[str] = []
    skipped_sections: list[str] = []
    budget_used = 0
    section_limit = max(0, payload.max_sections_per_run)
    budget_limit = max(0, payload.max_generation_budget)

    for section_id in requested_sections:
        if len(generated_sections) >= section_limit:
            skipped_sections.append(section_id)
            continue
        template = EDITION_TEMPLATES[section_id]
        estimate = estimate_generation_cost(context, template)
        if budget_used + estimate > budget_limit:
            skipped_sections.append(section_id)
            continue
        rendered = template.renderer(context)
        sections[section_id] = rendered
        generated_sections.append(section_id)
        budget_used += estimate

    qa = evaluate_edition_quality(
        requested_sections=requested_sections,
        generated_sections=generated_sections,
        sections=sections,
        context=context,
        skipped_sections=skipped_sections,
    )
    state.quality_score = qa["quality_score"]
    state.qa_status = qa["qa_status"]
    if state.qa_status == "BLOCKED_QA":
        generation_status = "BLOCKED_QA"
    elif skipped_sections:
        generation_status = "PARTIAL_DRY_RUN"
    else:
        generation_status = "READY_FOR_REVIEW"

    return EditionGenerationResult(
        state=state,
        sections=sections,
        requested_sections=requested_sections,
        generated_sections=generated_sections,
        skipped_sections=skipped_sections,
        qa=qa,
        cost_controls=cost_control_summary(payload, budget_used=budget_used),
        generation_status=generation_status,
        dry_run=payload.dry_run,
    )


def validate_input(payload: EditionGenerationInput) -> None:
    missing = []
    for field_name in REQUIRED_METADATA_FIELDS:
        if not str(getattr(payload, field_name) or "").strip():
            missing.append(field_name)
    if missing:
        raise ValueError(f"Edition generation requires metadata: {', '.join(missing)}.")
    if not payload.cleaned_text.strip():
        raise ValueError("Edition generation requires cleaned_text from the source ingestion pipeline.")


def generation_cache_key(*, source_hash: str, prompt_version: str, model_version: str) -> str:
    material = "\n".join([source_hash.strip(), prompt_version.strip(), model_version.strip()])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_requested_sections(section_ids: Iterable[str]) -> list[str]:
    normalized = []
    for section_id in section_ids:
        key = str(section_id or "").strip().lower().replace("-", "_")
        if key not in EDITION_TEMPLATES:
            raise ValueError(f"Unsupported edition section: {section_id}")
        if key not in normalized:
            normalized.append(key)
    return normalized or list(SECTION_ORDER)


def build_context(payload: EditionGenerationInput) -> EditionContext:
    source_excerpt = payload.cleaned_text.strip()[:MAX_SOURCE_CHARS]
    sentences = split_sentences(source_excerpt)
    keywords = extract_keywords(source_excerpt, payload.title)
    return EditionContext(
        title=payload.title.strip(),
        author=payload.author.strip() or "Unknown author",
        language=payload.language.strip() or "unknown",
        source_name=payload.source_name.strip(),
        source_url=payload.source_url.strip(),
        source_license=payload.source_license.strip(),
        source_hash=payload.source_hash.strip(),
        source_excerpt=source_excerpt,
        sentences=sentences,
        keywords=keywords,
    )


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?।])\s+", compact)
    return [part.strip() for part in parts if part.strip()]


def extract_keywords(text: str, title: str, *, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}|[\u0980-\u09ff]{3,}", f"{title} {text}")
    stop_words = {
        "that",
        "with",
        "from",
        "this",
        "have",
        "were",
        "their",
        "there",
        "chapter",
        "source",
        "book",
    }
    counts: dict[str, int] = {}
    original: dict[str, str] = {}
    for word in words:
        key = word.lower()
        if key in stop_words:
            continue
        counts[key] = counts.get(key, 0) + 1
        original.setdefault(key, word.strip("'"))
    ranked = sorted(counts, key=lambda key: (-counts[key], key))
    return [original[key] for key in ranked[:limit]]


def estimate_generation_cost(context: EditionContext, template: EditionTemplate) -> int:
    return len(template.prompt) + min(len(context.source_excerpt), 1_500)


def cost_control_summary(payload: EditionGenerationInput, *, budget_used: int) -> dict[str, Any]:
    return {
        "max_sections_per_run": payload.max_sections_per_run,
        "max_generation_budget": payload.max_generation_budget,
        "budget_used": budget_used,
        "skip_unchanged_source_hash": True,
        "dry_run_default": payload.dry_run,
        "max_source_chars": MAX_SOURCE_CHARS,
    }


def evaluate_edition_quality(
    *,
    requested_sections: list[str],
    generated_sections: list[str],
    sections: dict[str, str],
    context: EditionContext,
    skipped_sections: list[str],
) -> dict[str, Any]:
    missing_sections = [section for section in requested_sections if section not in generated_sections]
    qa_issues: list[str] = []
    for section_id in generated_sections:
        text = sections.get(section_id, "")
        if len(text.strip()) < 80:
            qa_issues.append(f"{section_id} is too short for review.")

    citation_source_coverage = citation_coverage(sections, context)
    if generated_sections and citation_source_coverage < 1:
        qa_issues.append("Not every generated section includes source coverage.")

    readability_score = readability(context.source_excerpt)
    if readability_score < 35:
        qa_issues.append("Readability score is too low for a learner-facing edition.")

    hallucination_risk = bool(generated_sections and citation_source_coverage < 1)
    if len(context.source_excerpt) < 300:
        hallucination_risk = True
        qa_issues.append("Source text is too short; value-added claims may be under-supported.")

    age_flag = bool(ADULT_RISK_RE.search(context.source_excerpt))
    quality_score = max(
        0,
        100
        - (len(qa_issues) * 15)
        - (len(missing_sections) * 2)
        - (10 if hallucination_risk else 0)
        - (5 if age_flag else 0),
    )
    if qa_issues or quality_score < 75:
        qa_status = "BLOCKED_QA"
    elif skipped_sections:
        qa_status = "NEEDS_MORE_RUNS"
    else:
        qa_status = "PASS"

    return {
        "qa_status": qa_status,
        "quality_score": round(quality_score, 2),
        "missing_sections": missing_sections,
        "skipped_sections": skipped_sections,
        "hallucination_risk": hallucination_risk,
        "citation_source_coverage": round(citation_source_coverage, 2),
        "readability_score": round(readability_score, 2),
        "age_appropriateness_flag": age_flag,
        "qa_issues": qa_issues,
    }


def citation_coverage(sections: dict[str, str], context: EditionContext) -> float:
    if not sections:
        return 0
    covered = 0
    for text in sections.values():
        if context.source_name in text and context.source_url in text:
            covered += 1
    return covered / len(sections)


def readability(text: str) -> float:
    words = re.findall(r"[A-Za-z]+|[\u0980-\u09ff]+", text)
    sentences = max(1, len(split_sentences(text)))
    if not words:
        return 0
    average_words = len(words) / sentences
    average_chars = sum(len(word) for word in words) / len(words)
    score = 100 - (average_words * 1.4) - (average_chars * 4)
    return max(0, min(100, score))


def render_clean_reading_edition(context: EditionContext) -> str:
    excerpt = context.source_excerpt[:900].strip()
    return (
        f"Clean Reading Edition: {context.title}\n\n"
        f"{excerpt}\n\n"
        "Editorial note: This is a short preview scaffold only; Phase 5 does not generate a full book.\n"
        f"{context.source_note}"
    )


def render_chapter_summary(context: EditionContext) -> str:
    lead = context.sentences[0] if context.sentences else "The opening passage establishes the reading tone."
    return (
        f"Chapter Summary\n\n"
        f"- Opening focus: {lead}\n"
        f"- Reader takeaway: watch how {context.keywords[0] if context.keywords else context.title} shapes the scene.\n"
        f"- Use this summary as a review aid, not a replacement for the text.\n\n"
        f"{context.source_note}"
    )


def render_character_map(context: EditionContext) -> str:
    names = unique_names(context.source_excerpt)
    if not names:
        names = [context.author, "Reader"]
    rows = [f"- {name}: track this figure's role, relationships, and decisions." for name in names[:6]]
    return "Character Map\n\n" + "\n".join(rows) + f"\n\n{context.source_note}"


def render_historical_context(context: EditionContext) -> str:
    return (
        "Historical Context\n\n"
        f"This edition keeps historical framing conservative and source-tethered. For {context.title}, "
        "the context section should connect publication era, author background, and reader questions only after "
        "human-reviewed citations are added.\n\n"
        f"{context.source_note}"
    )


def render_glossary(context: EditionContext) -> str:
    terms = context.keywords[:6] or [context.title]
    lines = [f"- {term}: add a learner-friendly definition during editorial review." for term in terms]
    return "Glossary\n\n" + "\n".join(lines) + f"\n\n{context.source_note}"


def render_themes(context: EditionContext) -> str:
    terms = ", ".join(context.keywords[:4]) or context.title
    return (
        "Themes\n\n"
        f"- Close reading theme candidates: {terms}.\n"
        "- Ask how setting, voice, conflict, and moral choice develop across the passage.\n"
        "- Keep theme labels evidence-based and revise after full editorial review.\n\n"
        f"{context.source_note}"
    )


def render_quiz(context: EditionContext) -> str:
    keyword = context.keywords[0] if context.keywords else context.title
    return (
        "Quiz\n\n"
        f"1. What first impression does the passage create about {keyword}?\n"
        "2. Which sentence would you cite as evidence, and why?\n"
        "3. What question should a reader carry into the next chapter?\n\n"
        f"{context.source_note}"
    )


def render_seven_day_reading_plan(context: EditionContext) -> str:
    return (
        "7-Day Reading Plan\n\n"
        "Day 1: Preview title, author, and reading goal.\n"
        "Day 2: Read the opening section slowly.\n"
        "Day 3: Note characters and unfamiliar words.\n"
        "Day 4: Re-read one difficult passage.\n"
        "Day 5: Write a short summary.\n"
        "Day 6: Answer the quiz prompts.\n"
        "Day 7: Reflect on why the work still matters.\n\n"
        f"{context.source_note}"
    )


def render_teacher_parent_notes(context: EditionContext) -> str:
    return (
        "Teacher/Parent Notes\n\n"
        "- Use the text as a guided reading conversation.\n"
        "- Ask learners to support every answer with one sentence from the source.\n"
        "- Keep age suitability under review before assigning the complete work.\n\n"
        f"{context.source_note}"
    )


def render_why_matters(context: EditionContext) -> str:
    return (
        "Why This Book Matters Today\n\n"
        f"{context.title} can help modern readers practice attention, ethical reflection, and evidence-based "
        "interpretation. This section should remain grounded in the source text and editorial citations.\n\n"
        f"{context.source_note}"
    )


def render_audiobook_script(context: EditionContext) -> str:
    excerpt = context.source_excerpt[:700].strip()
    return (
        "Audiobook-Ready Script\n\n"
        "[Narration: clear, warm, unhurried]\n"
        f"{excerpt}\n\n"
        "[Pause briefly before discussion or comprehension prompts.]\n\n"
        f"{context.source_note}"
    )


def render_seo_copy(context: EditionContext) -> str:
    return (
        "SEO Copy\n\n"
        f"Title: {context.title} by {context.author} | Earnalism Edition\n"
        f"Description: Read a source-grounded Earnalism edition of {context.title}, with summaries, glossary, "
        "quiz prompts, and reading support for learners.\n\n"
        f"{context.source_note}"
    )


def render_landing_page_copy(context: EditionContext) -> str:
    return (
        "Landing Page Copy\n\n"
        f"Start {context.title} with a calm, guided reading edition built for deeper learning. "
        "Preview the text, follow the reading plan, and turn reading time into understanding.\n\n"
        f"{context.source_note}"
    )


def render_social_excerpts(context: EditionContext) -> str:
    keyword = context.keywords[0] if context.keywords else context.title
    return (
        "Social Excerpts\n\n"
        f"- Start {context.title} with an Earnalism guided edition built around {keyword}.\n"
        "- Read slowly. Learn deeply. Where Learning Becomes Earning.\n"
        "- A public-domain classic, prepared with summaries, glossary, and reading prompts.\n\n"
        f"{context.source_note}"
    )


def unique_names(text: str) -> list[str]:
    names: list[str] = []
    for match in CHARACTER_NAME_RE.findall(text):
        name = match.strip()
        if name.lower() in {"chapter", "source", "project", "gutenberg"}:
            continue
        if name not in names:
            names.append(name)
    return names


EDITION_TEMPLATES = {
    "clean_reading_edition": EditionTemplate(
        "clean_reading_edition",
        "Clean Reading Edition",
        "Prepare a clean, source-faithful reading edition preview without generating a full book.",
        render_clean_reading_edition,
    ),
    "chapter_summary": EditionTemplate(
        "chapter_summary",
        "Chapter Summary",
        "Summarize the supplied source excerpt using only evidence from the source.",
        render_chapter_summary,
    ),
    "character_map": EditionTemplate(
        "character_map",
        "Character Map",
        "Identify character-map placeholders from names visible in the source excerpt.",
        render_character_map,
    ),
    "historical_context": EditionTemplate(
        "historical_context",
        "Historical Context",
        "Create conservative historical-context scaffolding that requires editorial citation.",
        render_historical_context,
    ),
    "glossary": EditionTemplate(
        "glossary",
        "Glossary",
        "Select candidate glossary terms from the source excerpt.",
        render_glossary,
    ),
    "themes": EditionTemplate(
        "themes",
        "Themes",
        "List source-grounded theme candidates and review guidance.",
        render_themes,
    ),
    "quiz": EditionTemplate(
        "quiz",
        "Quiz",
        "Draft evidence-based learner quiz prompts.",
        render_quiz,
    ),
    "seven_day_reading_plan": EditionTemplate(
        "seven_day_reading_plan",
        "7-Day Reading Plan",
        "Create a short learner reading plan for the source text.",
        render_seven_day_reading_plan,
    ),
    "teacher_parent_notes": EditionTemplate(
        "teacher_parent_notes",
        "Teacher/Parent Notes",
        "Draft educator and parent guidance without inventing unsupported facts.",
        render_teacher_parent_notes,
    ),
    "why_this_book_matters_today": EditionTemplate(
        "why_this_book_matters_today",
        "Why This Book Matters Today",
        "Explain modern relevance while staying source-grounded.",
        render_why_matters,
    ),
    "audiobook_ready_script": EditionTemplate(
        "audiobook_ready_script",
        "Audiobook-Ready Script",
        "Prepare a short narration scaffold from the source excerpt only.",
        render_audiobook_script,
    ),
    "seo_copy": EditionTemplate(
        "seo_copy",
        "SEO Copy",
        "Draft metadata-safe SEO copy for the source-grounded edition.",
        render_seo_copy,
    ),
    "landing_page_copy": EditionTemplate(
        "landing_page_copy",
        "Landing Page Copy",
        "Draft conversion copy for a future edition landing page.",
        render_landing_page_copy,
    ),
    "social_excerpts": EditionTemplate(
        "social_excerpts",
        "Social Excerpts",
        "Draft short social excerpts suitable for review.",
        render_social_excerpts,
    ),
}


def edition_report_json(result: EditionGenerationResult) -> list[dict[str, Any]]:
    rows = []
    for section_id in result.generated_sections:
        rows.append({
            "section_id": section_id,
            "content": result.sections.get(section_id, ""),
            **result.state.as_dict(),
            "generation_status": result.generation_status,
            "dry_run": result.dry_run,
        })
    if not rows:
        rows.append({
            "section_id": "",
            "content": "",
            **result.state.as_dict(),
            "generation_status": result.generation_status,
            "dry_run": result.dry_run,
        })
    return rows


def edition_report_csv(result: EditionGenerationResult) -> str:
    fieldnames = [
        "section_id",
        "qa_status",
        "quality_score",
        "source_hash",
        "prompt_version",
        "model_version",
        "generation_status",
        "dry_run",
        "content_preview",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for section_id in result.generated_sections:
        writer.writerow({
            "section_id": section_id,
            "qa_status": result.state.qa_status,
            "quality_score": round(result.state.quality_score, 2),
            "source_hash": result.state.source_hash,
            "prompt_version": result.state.prompt_version,
            "model_version": result.state.model_version,
            "generation_status": result.generation_status,
            "dry_run": result.dry_run,
            "content_preview": result.sections.get(section_id, "")[:220],
        })
    return output.getvalue()


def edition_report_markdown(result: EditionGenerationResult) -> str:
    lines = [
        "# Earnalism Edition Generator Dry-Run Report",
        "",
        "No production content was published. No LLM, TTS, image, OCR, or paid API calls were made.",
        "",
        f"- Generation status: `{result.generation_status}`",
        f"- QA status: `{result.state.qa_status}`",
        f"- Quality score: `{round(result.state.quality_score, 2)}`",
        f"- Generated sections: {len(result.generated_sections)}",
        f"- Skipped sections: {len(result.skipped_sections)}",
        f"- Cache key: `{result.state.cache_key()}`",
        "",
        "## Sections",
        "",
    ]
    for section_id in result.generated_sections:
        lines.extend([
            f"### {EDITION_TEMPLATES[section_id].title}",
            "",
            result.sections[section_id],
            "",
        ])
    if result.skipped_sections:
        lines.extend([
            "## Skipped Sections",
            "",
            ", ".join(result.skipped_sections),
            "",
        ])
    lines.extend([
        "## QA",
        "",
        "```json",
        json.dumps(result.qa, indent=2, ensure_ascii=False),
        "```",
    ])
    return "\n".join(lines) + "\n"
