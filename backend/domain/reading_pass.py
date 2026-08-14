"""Pure policy helpers for the server-authoritative Reading Pass.

This module deliberately has no FastAPI or MongoDB dependency.  It defines the
canonical segmentation and lease arithmetic shared by ingestion, runtime, and
tests.  Database atomicity lives in ``backend.reading_pass_service``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import html
import re
from typing import Any, Iterable, Mapping, Sequence


PUBLIC_TEXT_PAGE_COUNT = 3
PUBLIC_AUDIO_PREVIEW_SECONDS = 180
SAFE_INTEGER_MAX = 9_007_199_254_740_991


@dataclass(frozen=True)
class ReadingPassConfig:
    heartbeat_seconds: int = 10
    maximum_lease_seconds: int = 20
    reconnect_grace_seconds: int = 15
    text_inactivity_seconds: int = 120
    public_text_pages: int = PUBLIC_TEXT_PAGE_COUNT
    public_audio_seconds: int = PUBLIC_AUDIO_PREVIEW_SECONDS

    def __post_init__(self) -> None:
        if self.heartbeat_seconds < 1:
            raise ValueError("heartbeat_seconds must be positive")
        if self.maximum_lease_seconds < self.heartbeat_seconds:
            raise ValueError("maximum_lease_seconds must cover one heartbeat")
        if self.reconnect_grace_seconds < 0:
            raise ValueError("reconnect_grace_seconds cannot be negative")
        if self.text_inactivity_seconds < self.maximum_lease_seconds:
            raise ValueError("text_inactivity_seconds must exceed a lease")
        if self.public_text_pages != PUBLIC_TEXT_PAGE_COUNT:
            raise ValueError("the public text boundary is fixed at three canonical pages")
        if self.public_audio_seconds != PUBLIC_AUDIO_PREVIEW_SECONDS:
            raise ValueError("the public audio boundary is fixed at 180 seconds")


class ReadingPassError(RuntimeError):
    """Machine-readable access failure raised by the service layer."""

    def __init__(self, code: str, status_code: int, message: str, **context: Any) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = int(status_code)
        self.message = message
        self.context = context

    def payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.context}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def safe_seconds(value: Any, *, allow_negative: bool = False) -> int:
    """Return a bounded integer number of seconds; reject floats and booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("seconds must be an integer")
    minimum = -SAFE_INTEGER_MAX if allow_negative else 0
    if value < minimum or value > SAFE_INTEGER_MAX:
        raise ValueError("seconds are outside the safe integer range")
    return value


def token_fingerprint(token: str, secret: str) -> str:
    raw = str(token or "").encode("utf-8")
    if not secret:
        raise ValueError("a Reading Pass token secret is required")
    key = str(secret).encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def public_text_page(page_index: int) -> bool:
    return 1 <= int(page_index) <= PUBLIC_TEXT_PAGE_COUNT


def public_audio_position(position_seconds: float) -> bool:
    try:
        value = float(position_seconds)
    except (TypeError, ValueError):
        return False
    return 0 <= value < PUBLIC_AUDIO_PREVIEW_SECONDS


def lease_duration_seconds(balance_seconds: int, config: ReadingPassConfig) -> int:
    balance = safe_seconds(int(balance_seconds))
    return min(balance, config.maximum_lease_seconds)


def lease_expiry(now: datetime, balance_seconds: int, config: ReadingPassConfig) -> datetime:
    return ensure_utc(now) + timedelta(seconds=lease_duration_seconds(balance_seconds, config))


def server_billable_seconds(
    *,
    last_billed_at: datetime,
    lease_expires_at: datetime,
    now: datetime,
    active: bool,
    config: ReadingPassConfig,
) -> int:
    """Calculate debit exclusively from server timestamps.

    Billing is capped by the old lease, never by client elapsed time.  An
    inactive renewal pauses without debit.  A delayed renewal cannot turn one
    short lease into an unbounded charge.
    """

    if not active:
        return 0
    start = ensure_utc(last_billed_at)
    stop = min(ensure_utc(now), ensure_utc(lease_expires_at))
    elapsed = max(0, int((stop - start).total_seconds()))
    return min(elapsed, config.maximum_lease_seconds)


_BLOCK_RE = re.compile(
    r"(<(?P<tag>p|h[1-6]|blockquote|pre|ul|ol|figure|table)\b[^>]*>.*?</(?P=tag)>)",
    re.IGNORECASE | re.DOTALL,
)


def _content_blocks(content: str) -> list[str]:
    value = str(content or "").strip()
    if not value:
        return []
    matches = list(_BLOCK_RE.finditer(value))
    if matches:
        blocks: list[str] = []
        cursor = 0

        def preserve_fragment(fragment: str) -> None:
            plain = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
            plain = re.sub(r"\s+", " ", plain).strip()
            if plain:
                blocks.append(f"<p>{html.escape(plain)}</p>")

        for match in matches:
            preserve_fragment(value[cursor:match.start()])
            block = match.group(1).strip()
            if block:
                blocks.append(block)
            cursor = match.end()
        preserve_fragment(value[cursor:])
        return blocks
    paragraphs = [part.strip() for part in re.split(r"(?:\r?\n){2,}", value) if part.strip()]
    if len(paragraphs) > 1:
        return [f"<p>{html.escape(part)}</p>" for part in paragraphs]
    return [value]


def canonical_page_records(
    *,
    book_slug: str,
    chapters: Sequence[Mapping[str, Any]],
    target_characters: int = 3_200,
    segmentation_version: str = "canonical-html-blocks-v1",
) -> list[dict[str, Any]]:
    """Build deterministic, viewport-independent canonical reading pages.

    Block boundaries are preserved; viewport wrapping is never considered.
    Existing records are expected to be written once by the migration and
    replaced only under an explicit new segmentation version.
    """

    if target_characters < 800:
        raise ValueError("target_characters is too small for stable reading pages")
    slug = str(book_slug or "").strip()
    if not slug:
        raise ValueError("book_slug is required")

    records: list[dict[str, Any]] = []
    page_index = 1
    for chapter_order, chapter in enumerate(chapters, start=1):
        chapter_id = str(chapter.get("id") or f"chapter-{chapter_order:03d}")
        chapter_title = str(chapter.get("title") or "")
        blocks = _content_blocks(str(chapter.get("content") or ""))
        pending: list[str] = []
        pending_size = 0

        def flush() -> None:
            nonlocal page_index, pending, pending_size
            if not pending:
                return
            content = "\n".join(pending).strip()
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            records.append(
                {
                    "book_slug": slug,
                    "page_index": page_index,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "chapter_order": int(chapter.get("order") or chapter_order),
                    "content": content,
                    "content_sha256": digest,
                    "segmentation_version": segmentation_version,
                    "is_public_preview": page_index <= PUBLIC_TEXT_PAGE_COUNT,
                }
            )
            page_index += 1
            pending = []
            pending_size = 0

        for block in blocks:
            block_size = len(re.sub(r"<[^>]+>", "", block))
            if pending and pending_size + block_size > target_characters:
                flush()
            pending.append(block)
            pending_size += block_size
        flush()
    return records


def segment_manifest(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda row: int(row["page_index"]))
    chapters: dict[str, dict[str, Any]] = {}
    for row in ordered:
        chapter_id = str(row.get("chapter_id") or "")
        entry = chapters.setdefault(
            chapter_id,
            {
                "chapter_id": chapter_id,
                "chapter_title": str(row.get("chapter_title") or ""),
                "chapter_order": int(row.get("chapter_order") or 0),
                "first_page_index": int(row["page_index"]),
                "last_page_index": int(row["page_index"]),
            },
        )
        entry["last_page_index"] = int(row["page_index"])
    version_source = "|".join(
        f"{row['page_index']}:{row.get('content_sha256', '')}:{row.get('segmentation_version', '')}"
        for row in ordered
    )
    return {
        "total_pages": len(ordered),
        "public_preview_pages": PUBLIC_TEXT_PAGE_COUNT,
        "version": hashlib.sha256(version_source.encode("utf-8")).hexdigest()[:24],
        "chapters": sorted(chapters.values(), key=lambda row: (row["chapter_order"], row["first_page_index"])),
    }


def canonical_segment_chapter_title(
    canonical_chapters: Iterable[Mapping[str, Any]],
    chapter_id: Any,
    fallback: Any = "",
) -> str:
    """Resolve segment metadata through the controlled reader title source."""

    normalized_id = str(chapter_id or "").strip()
    for chapter in canonical_chapters:
        if str(chapter.get("id") or "").strip() == normalized_id:
            title = str(chapter.get("title") or "").strip()
            if title:
                return title
    return str(fallback or "").strip()


def canonicalize_segment_manifest_chapters(
    segment_chapters: Iterable[Mapping[str, Any]],
    canonical_chapters: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Keep Reading Pass and standard reader chapter labels identical."""

    canonical = list(canonical_chapters)
    return [
        {
            **dict(chapter),
            "chapter_title": canonical_segment_chapter_title(
                canonical,
                chapter.get("chapter_id"),
                chapter.get("chapter_title"),
            ),
        }
        for chapter in segment_chapters
    ]
