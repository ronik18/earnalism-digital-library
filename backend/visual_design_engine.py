from __future__ import annotations

import csv
import html
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


VISUAL_ENGINE_VERSION = "earnalism-visual-v1"
DEFAULT_MAX_ASSETS_PER_RUN = 8
MAX_SOURCE_CHARS = 8_000

ASSET_TYPES = [
    "character_relationship_diagram",
    "timeline",
    "chapter_flow",
    "theme_map",
    "vocabulary_cards",
    "quiz_worksheet",
    "seven_day_reading_plan_card",
    "teacher_handout",
    "reading_edition_epub_hook",
    "study_guide_pdf_hook",
    "mobile_html_edition_hook",
]

DIAGRAM_ASSETS = {
    "character_relationship_diagram",
    "timeline",
    "chapter_flow",
    "theme_map",
}

HOOK_ASSETS = {
    "reading_edition_epub_hook",
    "study_guide_pdf_hook",
    "mobile_html_edition_hook",
}

HTML_ASSETS = {
    "vocabulary_cards",
    "quiz_worksheet",
    "seven_day_reading_plan_card",
    "teacher_handout",
    "mobile_html_edition_hook",
}

CHARACTER_NAME_RE = re.compile(r"\b(?:Mr|Mrs|Miss|Dr|Professor)\.?\s+[A-Z][A-Za-z]+|\b[A-Z][a-z]{3,}\b")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
EXTERNAL_IMAGE_DEPENDENCY_RE = re.compile(
    r"(<img\b|\bsrc\s*=|\bsrcset\s*=|background-image\s*:|url\s*\(|https?://|data:image|//cdn)",
    re.IGNORECASE,
)
ALLOWED_EDITION_STATUSES = {"READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"}


@dataclass(frozen=True)
class VisualAssetTemplate:
    asset_type: str
    title: str
    output_format: str
    renderer: Callable[["VisualAssetContext"], str]


@dataclass
class VisualAssetContext:
    source_work: str
    author: str
    source_hash: str
    cleaned_text: str
    source_excerpt: str
    keywords: list[str]
    characters: list[str]
    chapters: list[str]
    years: list[str]


@dataclass
class VisualAssetRecord:
    asset_type: str
    source_work: str
    source_hash: str
    generated_at: str
    quality_score: float
    file_size: int
    output_format: str
    content: str
    qa_status: str = "PASS"
    dry_run: bool = True
    generation_hook: str = ""

    def metadata(self, *, include_content: bool = False, content_preview_chars: int = 1200) -> dict[str, Any]:
        row = {
            "asset_type": self.asset_type,
            "source_work": self.source_work,
            "source_hash": self.source_hash,
            "generated_at": self.generated_at,
            "quality_score": round(self.quality_score, 2),
            "file_size": self.file_size,
            "output_format": self.output_format,
            "qa_status": self.qa_status,
            "dry_run": self.dry_run,
            "generation_hook": self.generation_hook,
            "content_preview": self.content[: max(0, int(content_preview_chars or 0))],
        }
        if include_content:
            row["content"] = self.content
        return row


@dataclass
class VisualGenerationInput:
    source_work: str
    cleaned_text: str
    source_hash: str
    content_hash: str = ""
    provenance_hash: str = ""
    rights_tier: str = ""
    verification_status: str = ""
    blocked_reason: str = ""
    action_status: str = ""
    ingestion_status: str = ""
    edition_generation_status: str = ""
    author: str = ""
    requested_assets: list[str] = field(default_factory=lambda: list(ASSET_TYPES))
    max_assets_per_run: int = DEFAULT_MAX_ASSETS_PER_RUN
    dry_run: bool = True


@dataclass
class VisualGenerationResult:
    source_work: str
    source_hash: str
    content_hash: str
    provenance_hash: str
    generated_assets: list[VisualAssetRecord]
    skipped_assets: list[str]
    qa: dict[str, Any]
    generation_status: str
    gate_status: str
    blocking_reason: str
    rights_tier: str
    action_status: str
    ingestion_status: str
    edition_generation_status: str
    dry_run: bool = True

    def as_dict(self, *, include_content: bool = False, content_preview_chars: int = 1200) -> dict[str, Any]:
        return {
            "source_work": self.source_work,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "generation_status": self.generation_status,
            "gate_status": self.gate_status,
            "blocking_reason": self.blocking_reason,
            "rights_tier": self.rights_tier,
            "action_status": self.action_status,
            "ingestion_status": self.ingestion_status,
            "edition_generation_status": self.edition_generation_status,
            "dry_run": self.dry_run,
            "generated_asset_count": len(self.generated_assets),
            "skipped_asset_count": len(self.skipped_assets),
            "generated_assets": [
                asset.metadata(include_content=include_content, content_preview_chars=content_preview_chars)
                for asset in self.generated_assets
            ],
            "skipped_assets": self.skipped_assets,
            "qa": self.qa,
            "engine_version": VISUAL_ENGINE_VERSION,
        }


def generate_visual_assets(payload: VisualGenerationInput) -> VisualGenerationResult:
    if not payload.cleaned_text.strip():
        return blocked_result(payload, "BLOCKED_INGESTION", "cleaned_text is required.")

    requested_assets = normalize_requested_assets(payload.requested_assets)
    gate_status, blocking_reason = evaluate_generation_gate(payload)
    if gate_status != "PASS":
        return blocked_result(payload, gate_status, blocking_reason, requested_assets=requested_assets)

    context = build_context(payload)
    generated: list[VisualAssetRecord] = []
    skipped: list[str] = []
    limit = max(0, payload.max_assets_per_run)
    for asset_type in requested_assets:
        if len(generated) >= limit:
            skipped.append(asset_type)
            continue
        template = VISUAL_ASSET_TEMPLATES[asset_type]
        content = template.renderer(context)
        generated.append(build_asset_record(template, context, content, dry_run=payload.dry_run))

    qa = evaluate_visual_assets(generated, requested_assets, skipped)
    if qa["qa_status"] == "BLOCKED_QA":
        generation_status = "BLOCKED_QA"
    elif skipped:
        generation_status = "PARTIAL_DRY_RUN"
    else:
        generation_status = "READY_FOR_REVIEW"
    return VisualGenerationResult(
        source_work=payload.source_work,
        source_hash=payload.source_hash,
        content_hash=payload.content_hash,
        provenance_hash=payload.provenance_hash,
        generated_assets=generated,
        skipped_assets=skipped,
        qa=qa,
        generation_status=generation_status,
        gate_status="PASS",
        blocking_reason="",
        rights_tier=normalized_rights_tier(payload.rights_tier),
        action_status=normalized_status(payload.action_status),
        ingestion_status=normalized_status(payload.ingestion_status),
        edition_generation_status=normalized_status(payload.edition_generation_status),
        dry_run=payload.dry_run,
    )


def evaluate_generation_gate(payload: VisualGenerationInput) -> tuple[str, str]:
    if payload.dry_run is not True:
        return "BLOCKED_NON_DRY_RUN", "Phase 6 visual generation is dry-run only."

    rights_tier = normalized_rights_tier(payload.rights_tier)
    verification_status = normalized_status(payload.verification_status)
    action_status = normalized_status(payload.action_status)
    ingestion_status = normalized_status(payload.ingestion_status)
    edition_status = normalized_status(payload.edition_generation_status)
    blocked_reason = str(payload.blocked_reason or "").strip()

    if rights_tier == "C":
        return "BLOCKED_RIGHTS", "Tier C rights block visual generation."
    if rights_tier in {"", "UNKNOWN", "NO", "MISSING"} or verification_status not in {"APPROVED", "VERIFIED"}:
        return "BLOCKED_RIGHTS_REVIEW_REQUIRED", "Approved Tier A rights metadata is required before visual generation."
    if rights_tier == "B":
        return "REGION_GATED_REVIEW", "Tier B rights require region-gated review before visual generation."
    if rights_tier != "A":
        return "BLOCKED_RIGHTS_REVIEW_REQUIRED", "Unknown rights tier requires Phase 2 rights review."
    if blocked_reason:
        return "BLOCKED_RIGHTS", f"Rights blocked_reason must be cleared: {blocked_reason}"
    if action_status != "READY_FOR_GENERATION":
        return "BLOCKED_PRIORITY_GATE", "Phase 3 action_status must be READY_FOR_GENERATION."
    if ingestion_status not in {"INGESTED", "CLEANED"}:
        return "BLOCKED_INGESTION", "Phase 4 ingestion_status must be INGESTED or CLEANED."
    if edition_status not in ALLOWED_EDITION_STATUSES:
        return "BLOCKED_EDITION_GATE", "Phase 5 edition_generation_status must be ready, partial dry-run, or QA passed."
    if not str(payload.source_hash or "").strip():
        return "BLOCKED_TRACEABILITY", "source_hash is required."
    if not str(payload.content_hash or "").strip() or not str(payload.provenance_hash or "").strip():
        return "BLOCKED_TRACEABILITY", "content_hash and provenance_hash are required."
    if not str(payload.source_work or "").strip():
        return "BLOCKED_TRACEABILITY", "source_work is required."
    return "PASS", ""


def blocked_result(
    payload: VisualGenerationInput,
    status: str,
    reason: str,
    *,
    requested_assets: list[str] | None = None,
) -> VisualGenerationResult:
    requested_assets = requested_assets or normalize_requested_assets(payload.requested_assets)
    return VisualGenerationResult(
        source_work=payload.source_work,
        source_hash=payload.source_hash,
        content_hash=payload.content_hash,
        provenance_hash=payload.provenance_hash,
        generated_assets=[],
        skipped_assets=requested_assets,
        qa={
            "qa_status": status,
            "quality_score": 0,
            "missing_assets": requested_assets,
            "issues": [reason],
            "copyrighted_image_dependency": False,
            "ai_image_generation_required": False,
            "epub_pdf_hooks_dry_run_capable": True,
        },
        generation_status=status,
        gate_status=status,
        blocking_reason=reason,
        rights_tier=normalized_rights_tier(payload.rights_tier),
        action_status=normalized_status(payload.action_status),
        ingestion_status=normalized_status(payload.ingestion_status),
        edition_generation_status=normalized_status(payload.edition_generation_status),
        dry_run=payload.dry_run,
    )


def normalized_rights_tier(value: Any) -> str:
    return str(value or "").strip().upper().replace("TIER ", "")


def normalized_status(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def normalize_requested_assets(asset_types: Iterable[str]) -> list[str]:
    normalized = []
    for asset_type in asset_types:
        key = str(asset_type or "").strip().lower().replace("-", "_")
        if key not in VISUAL_ASSET_TEMPLATES:
            raise ValueError(f"Unsupported visual asset type: {asset_type}")
        if key not in normalized:
            normalized.append(key)
    return normalized or list(ASSET_TYPES)


def build_context(payload: VisualGenerationInput) -> VisualAssetContext:
    excerpt = payload.cleaned_text.strip()[:MAX_SOURCE_CHARS]
    return VisualAssetContext(
        source_work=payload.source_work.strip(),
        author=payload.author.strip() or "Unknown author",
        source_hash=payload.source_hash.strip(),
        cleaned_text=payload.cleaned_text,
        source_excerpt=excerpt,
        keywords=extract_keywords(excerpt, payload.source_work),
        characters=extract_characters(excerpt, payload.author),
        chapters=extract_chapters(excerpt),
        years=extract_years(excerpt),
    )


def build_asset_record(
    template: VisualAssetTemplate,
    context: VisualAssetContext,
    content: str,
    *,
    dry_run: bool,
) -> VisualAssetRecord:
    quality_score = score_asset(template.asset_type, content)
    return VisualAssetRecord(
        asset_type=template.asset_type,
        source_work=context.source_work,
        source_hash=context.source_hash,
        generated_at=datetime.now(timezone.utc).isoformat(),
        quality_score=quality_score,
        file_size=len(content.encode("utf-8")),
        output_format=template.output_format,
        content=content,
        qa_status="PASS" if quality_score >= 75 else "BLOCKED_QA",
        dry_run=dry_run,
        generation_hook=generation_hook(template.asset_type),
    )


def score_asset(asset_type: str, content: str) -> float:
    score = 100
    if len(content.strip()) < 120:
        score -= 25
    if asset_type in DIAGRAM_ASSETS and not ("graph" in content or "timeline" in content or "<svg" in content):
        score -= 30
    if asset_type in HTML_ASSETS and "<" not in content:
        score -= 20
    if contains_external_image_reference(content):
        score -= 50
    return max(0, min(100, score))


def generation_hook(asset_type: str) -> str:
    if asset_type == "reading_edition_epub_hook":
        return "pandoc --from=html --to=epub3 --output reading-edition.epub"
    if asset_type == "study_guide_pdf_hook":
        return "pandoc --from=html --to=pdf --output study-guide.pdf"
    if asset_type == "mobile_html_edition_hook":
        return "static responsive HTML render"
    return ""


def evaluate_visual_assets(
    generated_assets: list[VisualAssetRecord],
    requested_assets: list[str],
    skipped_assets: list[str],
) -> dict[str, Any]:
    generated_types = {asset.asset_type for asset in generated_assets}
    missing_assets = [asset_type for asset_type in requested_assets if asset_type not in generated_types]
    issues = []
    if any(asset.qa_status == "BLOCKED_QA" for asset in generated_assets):
        issues.append("One or more generated assets failed quality scoring.")
    external_issues = external_dependency_issues(asset.content for asset in generated_assets)
    if external_issues:
        issues.append("External image dependency detected: " + ", ".join(sorted(set(external_issues))))
    if any(asset.file_size > 120_000 for asset in generated_assets):
        issues.append("Generated asset is too large for the lightweight Phase 6 target.")

    quality_score = max(0, 100 - (len(issues) * 20) - (len(missing_assets) * 2))
    qa_status = "BLOCKED_QA" if issues else ("NEEDS_MORE_RUNS" if skipped_assets else "PASS")
    return {
        "qa_status": qa_status,
        "quality_score": round(quality_score, 2),
        "missing_assets": missing_assets,
        "skipped_assets": skipped_assets,
        "issues": issues,
        "copyrighted_image_dependency": bool(external_issues),
        "ai_image_generation_required": False,
        "epub_pdf_hooks_dry_run_capable": True,
    }


def contains_external_image_reference(content: str) -> bool:
    return bool(EXTERNAL_IMAGE_DEPENDENCY_RE.search(content or ""))


def external_dependency_issues(contents: Iterable[str]) -> list[str]:
    issues: list[str] = []
    labels = {
        "<img": "<img",
        "src=": "src=",
        "srcset=": "srcset=",
        "background-image": "background-image",
        "url(": "url(",
        "http://": "http://",
        "https://": "https://",
        "data:image": "data:image",
        "//cdn": "//cdn",
    }
    for content in contents:
        lower = (content or "").lower()
        for needle, label in labels.items():
            if needle in lower:
                issues.append(label)
    return issues


def extract_keywords(text: str, title: str, *, limit: int = 10) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}|[\u0980-\u09ff]{3,}", f"{title} {text}")
    stop_words = {"that", "with", "from", "this", "have", "were", "their", "there", "chapter", "book"}
    counts: dict[str, int] = {}
    original: dict[str, str] = {}
    for word in words:
        key = word.lower().strip("'")
        if key in stop_words:
            continue
        counts[key] = counts.get(key, 0) + 1
        original.setdefault(key, word.strip("'"))
    ranked = sorted(counts, key=lambda key: (-counts[key], key))
    return [original[key] for key in ranked[:limit]] or [title]


def extract_characters(text: str, author: str) -> list[str]:
    names = []
    for match in CHARACTER_NAME_RE.findall(text):
        name = match.strip().replace("  ", " ")
        if name.lower() in {"chapter", "source", "project", "gutenberg"}:
            continue
        if name not in names:
            names.append(name)
    if author and author not in names:
        names.append(author)
    return names[:8] or ["Reader", "Narrator"]


def extract_chapters(text: str) -> list[str]:
    chapters = re.findall(r"(?im)^\s*(chapter\s+\d+|chapter\s+[ivxlcdm]+|part\s+\d+)\b.*$", text)
    return [chapter.strip() for chapter in chapters[:10]] or ["Opening", "Middle", "Reflection"]


def extract_years(text: str) -> list[str]:
    years = []
    for year in YEAR_RE.findall(text):
        if year not in years:
            years.append(year)
    return years[:8]


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned or "node"


def render_character_relationship_diagram(context: VisualAssetContext) -> str:
    characters = context.characters[:5]
    lines = ["graph TD"]
    center = slug(context.source_work)
    lines.append(f"  {center}[\"{esc(context.source_work)}\"]")
    for character in characters:
        node = slug(character)
        lines.append(f"  {center} --> {node}[\"{esc(character)}\"]")
    return "\n".join(lines) + "\n"


def render_timeline(context: VisualAssetContext) -> str:
    years = context.years or ["Start", "Turning point", "Reflection"]
    lines = ["timeline", f"  title {context.source_work} Study Timeline"]
    for index, year in enumerate(years, start=1):
        lines.append(f"  {year} : Reading milestone {index}")
    return "\n".join(lines) + "\n"


def render_chapter_flow(context: VisualAssetContext) -> str:
    lines = ["graph LR"]
    previous = ""
    for index, chapter in enumerate(context.chapters[:6], start=1):
        node = f"C{index}"
        lines.append(f"  {node}[\"{esc(chapter)}\"]")
        if previous:
            lines.append(f"  {previous} --> {node}")
        previous = node
    return "\n".join(lines) + "\n"


def render_theme_map(context: VisualAssetContext) -> str:
    keywords = context.keywords[:6]
    radius = 42
    circles = []
    for index, keyword in enumerate(keywords):
        x = 70 + (index % 3) * 120
        y = 70 + (index // 3) * 85
        circles.append(
            f'<g><circle cx="{x}" cy="{y}" r="{radius}" fill="#f8f1df" stroke="#9d7c38"/>'
            f'<text x="{x}" y="{y}" text-anchor="middle" font-size="12" fill="#3d2428">{esc(keyword)}</text></g>'
        )
    return (
        '<svg width="420" height="220" role="img" '
        f'aria-label="{esc(context.source_work)} theme map">'
        f'<rect width="420" height="220" fill="#fffaf0"/>{"".join(circles)}</svg>'
    )


def render_vocabulary_cards(context: VisualAssetContext) -> str:
    cards = []
    for term in context.keywords[:6]:
        cards.append(
            '<article class="vocab-card">'
            f"<h3>{esc(term)}</h3>"
            "<p>Add a learner-friendly definition during editorial review.</p>"
            "</article>"
        )
    return html_shell(context, "Vocabulary Cards", "".join(cards))


def render_quiz_worksheet(context: VisualAssetContext) -> str:
    body = (
        "<ol>"
        f"<li>What first impression does {esc(context.source_work)} create?</li>"
        "<li>Which sentence would you cite as evidence?</li>"
        "<li>What question should a reader carry into the next chapter?</li>"
        "</ol>"
    )
    return html_shell(context, "Quiz Worksheet", body)


def render_seven_day_reading_plan_card(context: VisualAssetContext) -> str:
    items = "".join(f"<li>Day {day}: {esc(task)}</li>" for day, task in enumerate([
        "Preview the title and author.",
        "Read the opening section slowly.",
        "Note key characters and terms.",
        "Re-read one difficult passage.",
        "Write a five-sentence summary.",
        "Answer the quiz worksheet.",
        "Reflect on why the work matters.",
    ], start=1))
    return html_shell(context, "7-Day Reading Plan", f"<ol>{items}</ol>")


def render_teacher_handout(context: VisualAssetContext) -> str:
    body = (
        "<section><h3>Classroom Use</h3>"
        "<p>Use this handout as a guided discussion scaffold. Ask learners to support every answer with source evidence.</p>"
        "<h3>Review Note</h3><p>Confirm age suitability before assigning the full work.</p></section>"
    )
    return html_shell(context, "Teacher Handout", body)


def render_epub_hook(context: VisualAssetContext) -> str:
    return json.dumps({
        "hook": generation_hook("reading_edition_epub_hook"),
        "source_work": context.source_work,
        "source_hash": context.source_hash,
        "dry_run": True,
        "inputs": ["clean-reading-edition.html", "metadata.json"],
    }, indent=2)


def render_pdf_hook(context: VisualAssetContext) -> str:
    return json.dumps({
        "hook": generation_hook("study_guide_pdf_hook"),
        "source_work": context.source_work,
        "source_hash": context.source_hash,
        "dry_run": True,
        "inputs": ["study-guide.html", "print.css"],
    }, indent=2)


def render_mobile_html_hook(context: VisualAssetContext) -> str:
    return html_shell(
        context,
        "Mobile HTML Edition Hook",
        "<p>Responsive mobile HTML scaffold for the approved reading edition.</p>",
    )


def html_shell(context: VisualAssetContext, title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{esc(title)} | {esc(context.source_work)}</title>"
        "<style>body{font-family:serif;margin:24px;color:#3d2428;background:#fffaf0}"
        ".vocab-card{border:1px solid #d6bd82;padding:12px;margin:8px 0;border-radius:6px}</style>"
        "</head><body>"
        f"<h1>{esc(title)}</h1><p><strong>Source:</strong> {esc(context.source_work)}</p>{body}</body></html>"
    )


VISUAL_ASSET_TEMPLATES = {
    "character_relationship_diagram": VisualAssetTemplate(
        "character_relationship_diagram",
        "Character Relationship Diagram",
        "mermaid",
        render_character_relationship_diagram,
    ),
    "timeline": VisualAssetTemplate("timeline", "Timeline", "mermaid", render_timeline),
    "chapter_flow": VisualAssetTemplate("chapter_flow", "Chapter Flow", "mermaid", render_chapter_flow),
    "theme_map": VisualAssetTemplate("theme_map", "Theme Map", "svg", render_theme_map),
    "vocabulary_cards": VisualAssetTemplate("vocabulary_cards", "Vocabulary Cards", "html", render_vocabulary_cards),
    "quiz_worksheet": VisualAssetTemplate("quiz_worksheet", "Quiz Worksheet", "html", render_quiz_worksheet),
    "seven_day_reading_plan_card": VisualAssetTemplate(
        "seven_day_reading_plan_card",
        "7-Day Reading Plan Card",
        "html",
        render_seven_day_reading_plan_card,
    ),
    "teacher_handout": VisualAssetTemplate("teacher_handout", "Teacher Handout", "html", render_teacher_handout),
    "reading_edition_epub_hook": VisualAssetTemplate(
        "reading_edition_epub_hook",
        "Reading Edition EPUB Hook",
        "json-hook",
        render_epub_hook,
    ),
    "study_guide_pdf_hook": VisualAssetTemplate(
        "study_guide_pdf_hook",
        "Study Guide PDF Hook",
        "json-hook",
        render_pdf_hook,
    ),
    "mobile_html_edition_hook": VisualAssetTemplate(
        "mobile_html_edition_hook",
        "Mobile HTML Edition Hook",
        "html",
        render_mobile_html_hook,
    ),
}


def visual_report_json(
    result: VisualGenerationResult,
    *,
    include_content: bool = False,
    content_preview_chars: int = 1200,
) -> dict[str, Any]:
    return result.as_dict(include_content=include_content, content_preview_chars=content_preview_chars)


def visual_report_csv(result: VisualGenerationResult) -> str:
    fieldnames = [
        "asset_type",
        "source_work",
        "source_hash",
        "content_hash",
        "provenance_hash",
        "generated_at",
        "quality_score",
        "file_size",
        "output_format",
        "qa_status",
        "generation_status",
        "gate_status",
        "blocking_reason",
        "rights_tier",
        "action_status",
        "ingestion_status",
        "edition_generation_status",
        "dry_run",
        "generation_hook",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for asset in result.generated_assets:
        writer.writerow({
            **asset.metadata(include_content=False, content_preview_chars=0),
            "generation_status": result.generation_status,
            "gate_status": result.gate_status,
            "blocking_reason": result.blocking_reason,
            "rights_tier": result.rights_tier,
            "action_status": result.action_status,
            "ingestion_status": result.ingestion_status,
            "edition_generation_status": result.edition_generation_status,
            "content_hash": result.content_hash,
            "provenance_hash": result.provenance_hash,
        })
    return output.getvalue()


def visual_report_markdown(
    result: VisualGenerationResult,
    *,
    include_content: bool = False,
    content_preview_chars: int = 1200,
) -> str:
    lines = [
        "# Visual Design Engine Dry-Run Report",
        "",
        "No production content was published. No AI image generation, copyrighted image dependency, OCR, network fetching, or paid API calls were used.",
        "",
        f"- Source work: `{result.source_work}`",
        f"- Source hash: `{result.source_hash}`",
        f"- Content hash: `{result.content_hash}`",
        f"- Provenance hash: `{result.provenance_hash}`",
        f"- Generation status: `{result.generation_status}`",
        f"- Gate status: `{result.gate_status}`",
        f"- Blocking reason: `{result.blocking_reason}`",
        f"- Rights tier: `{result.rights_tier}`",
        f"- Action status: `{result.action_status}`",
        f"- Ingestion status: `{result.ingestion_status}`",
        f"- Edition generation status: `{result.edition_generation_status}`",
        f"- QA status: `{result.qa.get('qa_status')}`",
        f"- Generated assets: {len(result.generated_assets)}",
        f"- Skipped assets: {len(result.skipped_assets)}",
        "",
        "## Assets",
        "",
    ]
    for asset in result.generated_assets:
        lines.extend([
            f"### {asset.asset_type}",
            "",
            f"- Format: `{asset.output_format}`",
            f"- File size: `{asset.file_size}` bytes",
            f"- Quality score: `{round(asset.quality_score, 2)}`",
            f"- Hook: `{asset.generation_hook}`",
            "",
            "**Content preview:**" if not include_content else "**Full deterministic content:**",
            "",
            asset.content if include_content else asset.content[: max(0, int(content_preview_chars or 0))],
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
