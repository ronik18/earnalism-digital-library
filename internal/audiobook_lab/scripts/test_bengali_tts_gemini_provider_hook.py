#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "providers"))

import bengali_tts_provider_bakeoff as bakeoff  # noqa: E402
import google_gemini_tts_adapter as adapter  # noqa: E402


class BengaliTTSGeminiProviderHookTest(unittest.TestCase):
    def _configured_env(self, directory: Path) -> dict[str, str]:
        adc = directory / "adc.json"
        adc.write_text(
            json.dumps(
                {
                    "type": "authorized_user",
                    "client_id": "client",
                    "client_secret": "secret",
                    "refresh_token": "refresh",
                }
            ),
            encoding="utf-8",
        )
        return {
            "GOOGLE_APPLICATION_CREDENTIALS": str(adc),
            "GOOGLE_CLOUD_PROJECT": "earnalism-test",
            "EARNALISM_APPROVE_GOOGLE_GEMINI_TTS": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.10",
            "EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE": "8",
            "EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD": "75",
            "EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD": "17",
        }

    def test_gemini_is_explicitly_available_but_not_in_default_wave(self) -> None:
        self.assertNotIn("gemini_tts", bakeoff.parse_provider_filter(""))
        self.assertEqual(bakeoff.parse_provider_filter("gemini_tts"), ["gemini_tts"])

    def test_configured_gemini_voices_are_discovered_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with (
                patch.dict(os.environ, self._configured_env(Path(raw)), clear=True),
                patch.object(adapter.urllib.request, "urlopen") as urlopen,
            ):
                provider_env = bakeoff.detect_provider_env()
                voices, unavailable, metadata = bakeoff.available_voices(
                    provider_env,
                    2,
                    ["gemini_tts"],
                )
        self.assertEqual([voice.provider for voice in voices], ["gemini_tts", "gemini_tts"])
        self.assertEqual(metadata["gemini_tts"], ["Charon", "Kore"])
        self.assertFalse([item for item in unavailable if item.get("provider") == "gemini_tts"])
        urlopen.assert_not_called()

    def test_generation_hook_uses_exact_passage_and_canonical_metadata(self) -> None:
        passage = {
            "slug": "nishkriti",
            "passage_id": "opening",
            "text": "এই পাঠ্যটি অপরিবর্তিত থাকবে।",
            "text_hash": bakeoff.sha256_text("এই পাঠ্যটি অপরিবর্তিত থাকবে।"),
        }
        voice = bakeoff.ProviderVoice(
            "gemini_tts",
            "Charon",
            "bn-BD",
            model="gemini-2.5-pro-tts",
            output_codec="mp3",
            style_control=True,
        )
        expected = {"status": "PASS_PRIVATE_QA_REQUIRED"}
        with patch.object(adapter, "synthesize", return_value=expected) as synthesize:
            result = bakeoff.generate_gemini_tts_sample(
                voice,
                passage,
                passage["text"],
                "Use warm literary pacing.",
                Path("/tmp/private-gemini-audition.mp3"),
            )
        self.assertEqual(result, expected)
        call = synthesize.call_args
        self.assertEqual(call.args[0], passage["text"])
        self.assertEqual(call.kwargs["slug"], "nishkriti")
        self.assertEqual(call.kwargs["expected_source_sha256"], passage["text_hash"])
        self.assertTrue(call.kwargs["title"])
        self.assertTrue(call.kwargs["author"])


if __name__ == "__main__":
    unittest.main()
