from __future__ import annotations

import json
from pathlib import Path

from scripts.bengali_audiobook_chunker import SAMPLE_TEXT, chunk_text, split_sentences
from scripts.bengali_text_normalizer import normalize_payload


ROOT = Path(__file__).resolve().parents[2]


def test_chunker_preserves_bengali_punctuation():
    chunks = chunk_text("kshudhita-pashan", SAMPLE_TEXT)

    assert chunks
    assert any("।" in chunk["text"] for chunk in chunks)
    assert all("punctuation_profile" in chunk for chunk in chunks)
    assert all(chunk["regeneration_status"] == "INTERNAL_REVIEW_ONLY_NOT_GENERATED" for chunk in chunks)


def test_chunker_avoids_splitting_inside_quote_marks():
    text = '"তুমি কি শুনিতে পাও? সে বলিল।" বাইরে নীরবতা।'
    sentences = split_sentences(text)

    assert sentences[0].startswith('"তুমি')
    assert sentences[0].endswith('।"')
    assert len(sentences) == 2


def test_chunker_produces_deterministic_chunk_ids():
    first = chunk_text("kshudhita-pashan", SAMPLE_TEXT)
    second = chunk_text("kshudhita-pashan", SAMPLE_TEXT)

    assert [chunk["chunk_id"] for chunk in first] == [chunk["chunk_id"] for chunk in second]


def test_chunk_schema_contains_expected_bakeoff_fields():
    chunk = chunk_text("kshudhita-pashan", SAMPLE_TEXT)[0]

    for field in [
        "chunk_id",
        "chapter_id",
        "paragraph_ids",
        "text",
        "text_normalized",
        "punctuation_profile",
        "expected_pause_profile",
        "expected_emotion",
        "intensity",
        "speaker_style",
        "pronunciation_notes",
        "regeneration_status",
    ]:
        assert field in chunk
    assert chunk["expected_emotion"] in {
        "neutral_literary",
        "eerie",
        "suspense",
        "sorrow",
        "fear",
        "anger_restrained",
        "warmth",
        "wonder",
        "dialogue",
        "whispered_tension",
    }


def test_voice_profile_caps_emotion_intensity():
    profile = json.loads((ROOT / "data/audiobook_voice_profiles/bengali-gothic-premium-v1.json").read_text())

    assert profile["emotion_intensity_max"] <= 0.55
    assert profile["no_public_release"] is True


def test_normalizer_keeps_original_and_normalized_side_by_side():
    payload = normalize_payload("সে বলিল— “৩ দিন পরে আসিব।”")

    assert payload["original_text"] != payload["normalized_text"]
    assert "৩" in payload["original_text"]
    assert "3" in payload["normalized_text"]
    assert payload["punctuation_profile"]["danda"] == 1
