import hashlib
import json
from pathlib import Path

from backend.reader_only_audio_policy import READER_ONLY_AUDIO_EXCLUDED_SLUGS, ReaderOnlyAudioExcluded


ROOT = Path(__file__).resolve().parents[2]
SLUG = "agentic-ai-with-python"
EXPECTED = [
    "21a43d95157e8222c9299d7b9b787fda366c67fc31f838f2759d3ee4a2cfe296", "9c374eb3789023d7094be65d866440113aa3563083f8bab3106cbecb1e290627", "249389f5c1a9d0cbc8f812ae2c42804506d57d612edee34cdf9b2e0371710acf", "8493f65276d763dd1c02e06be02a744fe0f987e928e2e4a7b6c3a403ae2fafa9", "f978201299db1071d1594385b193f741776e3a653ee8032b7bab837b3f5685b0", "5523929482657fd5d056e9d216f58b37301f9474033969a3d4a2f6867f5c85fe", "bf81dc96ff29454e366bd7b565c4bcf44494f73f1aa1a3c7c833d5c82e581e42", "6d94b6cf39755a9d7eb01adfe1128d8c481826a0c3053ded006dba8a55950dd6", "88a6a6c90e345489afd690e6689345644bcbf985ef371ec5a7e57c504417a7de", "4f64a442dc1a1a1b77a9b3ab72a59230b3e0d7c566db5382833dcfc5dab5766d", "194f9996934e09354b294482a294dd22568544e427fd0b29a52a821003d80def", "0b2f933b235a0f08d8c9d065b131943f19793495f84e6f12fb90bf51b0ed68dc", "6f5dafb4d00f18aeb1ec5e5ae4a92e5a97425f20a6306735f03673bb5b1bd047", "1a3b4df9a9feff3b08aff646d79cfa71b279c920d43a5ae67d0959767f16d542",
]


def test_revised_reader_artifact_matches_all_selected_chapters_and_remains_audio_hidden():
    artifact = ROOT / "backend" / "data" / "controlled_publications" / SLUG
    reader = json.loads((artifact / "reader_manifest.json").read_text())
    public = json.loads((artifact / "public_book.json").read_text())
    chapters = [json.loads((artifact / "chapters" / f"chapter-{number:03d}.json").read_text()) for number in range(1, 15)]
    assert [chapter["id"] for chapter in chapters] == [f"chapter-{number:03d}" for number in range(1, 15)]
    assert [hashlib.sha256(chapter["content"].encode()).hexdigest() for chapter in chapters] == EXPECTED
    assert [chapter["title"] for chapter in chapters] == [chapter["title"] for chapter in reader["chapters"]]
    assert public["audio_enabled"] is False and public["audiobook_enabled"] is False
    assert reader["audio_enabled"] is False and reader["audiobook_enabled"] is False
    assert SLUG in READER_ONLY_AUDIO_EXCLUDED_SLUGS


def test_reader_only_slug_is_refused_before_any_audio_pipeline_output(tmp_path):
    from scripts.audiobook_generation_sync_pipeline import run_pipeline
    from scripts.audiobook_chapter_pipeline import run_chapter_pipeline
    with __import__("pytest").raises(ReaderOnlyAudioExcluded):
        run_pipeline(book_slug=SLUG, chapter="1", language="en", model_candidate="local", mode="dry-run", output_dir=tmp_path / "audio", write_root_reports=False)
    assert not (tmp_path / "audio").exists()
    with __import__("pytest").raises(ReaderOnlyAudioExcluded):
        run_chapter_pipeline(book_slug=SLUG, chapter=1, language="en", provider="fixture", voice_id="fixture", voice_name="fixture", write_root_reports=False)
