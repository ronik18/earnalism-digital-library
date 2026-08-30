from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "internal/audiobook_lab/sprint1_publication/cover_candidates/a-ghost-story/p0_v1"


def read_json(name: str) -> dict:
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def test_assignment_plan_is_exactly_bound_to_approved_private_assets():
    plan = read_json("a-ghost-story-cover-assignment-plan.json")
    candidates = {
        candidate["kind"]: candidate
        for candidate in read_json("staged-candidate-records.json")
    }

    expected = {
        "front": "d79e673971bf6de537d4886877d9e9daedd08efeeff467af0b2f9fbe43e52742",
        "back": "baa45f507dda0926dfeeb219430a8ecd580d53eec43fbdda66aaa0c7fa2a2400",
    }
    assert plan["status"] == "CANONICAL_PROMOTED"
    assert plan["approval_binding"] == {
        "front_sha256": expected["front"],
        "back_sha256": expected["back"],
    }
    for kind, digest in expected.items():
        local = PACKAGE / f"a-ghost-story_{kind}_1600x2400_v1.png"
        assert hashlib.sha256(local.read_bytes()).hexdigest() == digest
        assert plan["staged_media"][kind]["dimensions"] == [1600, 2400]
        assert plan["staged_media"][kind]["format"] == "PNG"
        assert candidates[kind]["sha256"] == digest
        assert candidates[kind]["audit_status"] == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"


def test_assignment_promotes_only_cover_fields_with_full_controlled_mirror_parity():
    plan = read_json("a-ghost-story-cover-assignment-plan.json")
    final_integrity = read_json("final-non-cover-integrity.json")
    public_book = json.loads(
        (ROOT / "data/controlled_publications/a-ghost-story/public_book.json").read_text(encoding="utf-8")
    )
    backend_public_book = json.loads(
        (ROOT / "backend/data/controlled_publications/a-ghost-story/public_book.json").read_text(encoding="utf-8")
    )

    assert public_book == backend_public_book
    assert public_book["cover_url"] == plan["staged_media"]["front"]["immutable_url"]
    assert public_book["back_cover_url"] == plan["staged_media"]["back"]["immutable_url"]
    assert public_book["thumbnail_url"] == plan["staged_media"]["front"]["thumbnail_url"]
    assert public_book["blur_placeholder"] == plan["staged_media"]["front"]["blur_placeholder"]
    assert public_book["dominant_color"] == plan["staged_media"]["front"]["dominant_color"]
    assert public_book["back_cover_thumbnail_url"] == plan["staged_media"]["back"]["thumbnail_url"]
    assert public_book["back_cover_blur_placeholder"] == plan["staged_media"]["back"]["blur_placeholder"]
    assert public_book["back_cover_dominant_color"] == plan["staged_media"]["back"]["dominant_color"]
    assert public_book["cover_dimensions"] == {"front": [1600, 2400], "back": [1600, 2400]}
    assert plan["production_mutations_to_date"] == 4
    assert "Applied through" in plan["promotion_policy"]
    assert final_integrity["mirror_differences"] == 0
    assert final_integrity["non_cover_field_changes"] == []
    forbidden = {
        "audio_enabled",
        "audiobook_enabled",
        "audiobook_release_gate",
        "audio_url",
        "reader_enabled",
        "is_published",
        "publication_status",
    }
    assert forbidden.isdisjoint(set(plan["changes"]["front"]) | set(plan["changes"]["back"]))
