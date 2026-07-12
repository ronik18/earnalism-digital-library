#!/usr/bin/env python3
"""Regression checks for ASR transcript/manuscript scoring."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import frontmatter_absent, group_repair_semantics, transcript_similarity  # noqa: E402


def assert_punctuation_normalized_prose_passes() -> None:
    manuscript = "True!—nervous—very, very dreadfully nervous I had been and am; but why will you say that I am mad?"
    transcript = "True. Nervous. Very, very dreadfully nervous I had been and am. But why will you say that I am mad?"
    metrics = transcript_similarity(manuscript, transcript)
    assert metrics["score"] >= 9.7, metrics
    assert metrics["token_order_similarity"] >= 0.97, metrics
    assert metrics["coverage"] >= 0.97, metrics


def assert_missing_content_blocks() -> None:
    manuscript = "one two three four five six seven eight nine ten"
    transcript = "one two three four five"
    metrics = transcript_similarity(manuscript, transcript)
    assert metrics["score"] < 9.7, metrics


def assert_boundary_allows_single_asr_name_variant() -> None:
    manuscript = (
        "Conradin listened to the noises and silences beyond the dining-room door. "
        "And while they debated the matter among themselves, Conradin made himself another piece of toast."
    )
    transcript = (
        "Conradin listened to the noises and silences beyond the dining room door. "
        "And while they debated the matter among themselves, Conradon made himself another piece of toast."
    )
    metrics = transcript_similarity(manuscript, transcript)
    assert metrics["last_words_match"], metrics
    assert metrics["last_words_match_score"] >= 0.86, metrics


def assert_boundary_missing_ending_blocks() -> None:
    manuscript = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
    transcript = "one two three four five six seven eight"
    metrics = transcript_similarity(manuscript, transcript)
    assert not metrics["last_words_match"], metrics


def assert_boundary_allows_hyphenated_compound_join() -> None:
    manuscript = (
        "and sorrier still that he had carried off my red blanket and my bath-tub."
    )
    transcript = (
        "poor fellow and sorrier still that he had carried off my red blanket and my bathtub."
    )
    metrics = transcript_similarity(manuscript, transcript)
    assert metrics["last_words_match"], metrics
    assert metrics["last_words_match_score"] == 1.0, metrics


def assert_bengali_literary_words_do_not_trigger_page_marker() -> None:
    assert frontmatter_absent("পৃথিবীর সমস্ত মাধ্যাকর্ষণশক্তি বালককে টানিতে লাগিল।")
    assert frontmatter_absent("পৃথিবীর লোক কোনো কালেও সে দিনের কথা ভুলিবে না।")


def assert_bengali_source_markers_still_block() -> None:
    assert not frontmatter_absent("১৯৫০ (পৃ. ৩৫-৩৯)\n\nগিন্নি")
    assert not frontmatter_absent("পৃষ্ঠা ১২\n\nগিন্নি")
    assert not frontmatter_absent("গল্পগুচ্ছ\n\nগিন্নি")


def assert_not_requested_repair_requires_verified_fresh_generation() -> None:
    accepted = group_repair_semantics({"status": "NOT_REQUESTED"}, construction_evidence_pass=True)
    assert accepted["accepted"], accepted
    required = group_repair_semantics(
        {"status": "NOT_REQUESTED", "repair_required": True},
        construction_evidence_pass=True,
    )
    assert not required["accepted"], required
    incomplete = group_repair_semantics({"status": "NOT_REQUESTED"}, construction_evidence_pass=False)
    assert not incomplete["accepted"], incomplete


def main() -> int:
    assert_punctuation_normalized_prose_passes()
    assert_missing_content_blocks()
    assert_boundary_allows_single_asr_name_variant()
    assert_boundary_missing_ending_blocks()
    assert_boundary_allows_hyphenated_compound_join()
    assert_bengali_literary_words_do_not_trigger_page_marker()
    assert_bengali_source_markers_still_block()
    assert_not_requested_repair_requires_verified_fresh_generation()
    print("ASR transcript similarity regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
