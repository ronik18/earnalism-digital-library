"""Owner-directed, reader-only audiobook exclusions. No network or filesystem I/O.

This restriction takes precedence over explicit selections, force/resume settings,
previous reviews, cached audio and the earlier general replacement instruction.
It does not alter reader availability or infer rights for other titles.
"""
from collections.abc import Mapping

POLICY_VERSION = "earnalism.owner_audio_exclusion.v1"
EXCLUDED_SLUGS = frozenset({"agentic-ai-with-python"})
EXCLUDED_BOOK_IDS = frozenset({"307adb30-176d-4a7b-a499-e20c8312337b"})
REASON = "OWNER_READER_ONLY: Agentic AI With Python is excluded from audiobook generation and release by Ronik Basak."

class AudioGenerationExcluded(ValueError):
    """The owner has explicitly excluded this title from all audiobook work."""

def _identity_values(value):
    if not isinstance(value, Mapping):
        return set()
    found = set()
    for key in ("slug", "book_slug", "book_id", "canonical_book_id", "id"):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            found.add(item.strip().lower())
    for key in ("artifact", "book", "reader", "live_observation", "scope"):
        child = value.get(key)
        if isinstance(child, Mapping) and child is not value:
            # Recognized identity containers only; do not inspect manuscript prose.
            found.update(_identity_values(child))
    return found

def audio_exclusion_reason(value):
    return REASON if _identity_values(value) & (EXCLUDED_SLUGS | EXCLUDED_BOOK_IDS) else ""

def assert_audio_allowed(value, *, require_identity=False):
    reason = audio_exclusion_reason(value)
    if reason:
        raise AudioGenerationExcluded(reason)
    if require_identity and not _identity_values(value):
        raise ValueError("BOOK_IDENTITY_REQUIRED: rebuild the job through the current notebook before generation.")
    return value

def audio_identity(value):
    assert_audio_allowed(value, require_identity=True)
    artifact = value.get("artifact", value)
    book = artifact.get("book") or {}
    return {"book_slug": artifact.get("slug") or book.get("slug") or "",
            "canonical_book_id": book.get("id") or artifact.get("id") or "",
            "owner_audio_policy_version": POLICY_VERSION}
