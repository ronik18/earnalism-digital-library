#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "providers"))

import google_gemini_tts_adapter as adapter  # noqa: E402


MP3_BYTES = b"ID3\x04\x00\x00\x00\x00\x00\x15earnalism-test"


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _http_error(payload: dict, code: int = 400) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://oauth2.googleapis.com/token",
        code,
        "error",
        {},
        io.BytesIO(json.dumps(payload).encode("utf-8")),
    )


class GoogleGeminiTTSAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        adapter._SESSION_RESERVED_USD = 0.0
        adapter._SESSION_RESERVED_BY_TITLE.clear()

    def _paid_env(self, adc_path: Path) -> dict[str, str]:
        return {
            "GOOGLE_APPLICATION_CREDENTIALS": str(adc_path),
            "GOOGLE_CLOUD_PROJECT": "earnalism-test",
            "EARNALISM_APPROVE_GOOGLE_GEMINI_TTS": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.10",
            "EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE": "8",
            "EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD": "75",
            "EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD": "17",
        }

    def _adc(self, directory: Path) -> Path:
        path = directory / "adc.json"
        path.write_text(
            json.dumps(
                {
                    "type": "authorized_user",
                    "client_id": "client-id",
                    "client_secret": "client-secret",
                    "refresh_token": "refresh-token",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_title_prompt_is_deterministic_and_title_bound(self) -> None:
        kwargs = {
            "slug": "nishkriti",
            "title": "নিষ্কৃতি",
            "author": "শরৎচন্দ্র চট্টোপাধ্যায়",
            "language_code": "bn-BD",
            "direction": "Use warm, intimate literary restraint.",
        }
        first = adapter.build_title_style_prompt(**kwargs)
        second = adapter.build_title_style_prompt(**kwargs)
        self.assertEqual(first, second)
        self.assertIn("নিষ্কৃতি", first)
        self.assertIn("nishkriti", first)
        self.assertIn("Recite only the supplied text", first)

    def test_source_bound_chunking_is_lossless_and_byte_bounded(self) -> None:
        source = ("প্রথম অনুচ্ছেদ।\n\nদ্বিতীয় অনুচ্ছেদ একটু দীর্ঘ।\n" * 18).strip()
        prompt = adapter.build_title_style_prompt(
            slug="nishkriti",
            title="নিষ্কৃতি",
            author="শরৎচন্দ্র চট্টোপাধ্যায়",
            language_code="bn-BD",
            direction="Use calm literary pacing.",
        )
        chunks = adapter.source_bound_chunks(
            source,
            expected_source_sha256=adapter.sha256_text(source),
            style_prompt=prompt,
            max_text_bytes=180,
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunk["text"] for chunk in chunks), source)
        self.assertTrue(all(chunk["text_bytes"] <= 180 for chunk in chunks))
        self.assertEqual(
            [chunk["index"] for chunk in chunks],
            list(range(len(chunks))),
        )

    def test_source_hash_mismatch_fails_before_any_network_call(self) -> None:
        with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "SHA-256"):
            adapter.source_bound_chunks(
                "canonical",
                expected_source_sha256="wrong",
                style_prompt="prompt",
            )

    def test_missing_budget_approval_fails_before_adc_or_network(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(adapter.urllib.request, "urlopen") as urlopen,
        ):
            with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "approval is incomplete"):
                adapter.synthesize(
                    "Private source passage.",
                    Path("/tmp/private-sample.mp3"),
                    slug="test",
                    title="Test",
                    author="Author",
                    direction="Warm literary narration.",
                    language_code="en-US",
                )
        urlopen.assert_not_called()

    def test_multiple_clips_accumulate_against_campaign_cap(self) -> None:
        env = {
            "EARNALISM_APPROVE_GOOGLE_GEMINI_TTS": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS": "1",
            "EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE": "8",
            "EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD": "75",
            "EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD": "74.99",
        }
        with patch.dict(os.environ, env, clear=True):
            first = adapter.authorize_and_estimate("12345678", reserve_session=True)
            self.assertEqual(first["projected_campaign_estimated_usd"], 74.998)
            with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "campaign spend"):
                adapter.authorize_and_estimate("12345678", reserve_session=True)

    def test_multiple_clips_accumulate_against_per_title_cap(self) -> None:
        env = {
            "EARNALISM_APPROVE_GOOGLE_GEMINI_TTS": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS": "1",
            "EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE": "0.01",
            "EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD": "75",
            "EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            adapter.authorize_and_estimate("123456", budget_key="book", reserve_session=True)
            with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "title spend"):
                adapter.authorize_and_estimate("123456", budget_key="book", reserve_session=True)

    def test_invalid_rapt_is_redacted_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            adc = self._adc(Path(raw))
            with (
                patch.dict(os.environ, self._paid_env(adc), clear=True),
                patch.object(
                    adapter.urllib.request,
                    "urlopen",
                    side_effect=_http_error(
                        {
                            "error": "invalid_grant",
                            "error_description": "reauth related error (invalid_rapt)",
                        }
                    ),
                ),
            ):
                with self.assertRaises(adapter.GeminiTTSBlocked) as raised:
                    adapter.refresh_adc_access_token()
        message = str(raised.exception)
        self.assertIn("invalid_grant", message)
        self.assertIn("invalid_rapt", message)
        self.assertIn("gcloud auth application-default login", message)
        self.assertNotIn("refresh-token", message)
        self.assertNotIn("client-secret", message)

    def test_mock_synthesis_uses_stdlib_adc_rest_and_hashes_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            adc = self._adc(directory)
            output = directory / "private" / "sample.mp3"
            with (
                patch.dict(os.environ, self._paid_env(adc), clear=True),
                patch.object(
                    adapter.urllib.request,
                    "urlopen",
                    side_effect=[
                        _Response({"access_token": "access-token"}),
                        _Response({"audioContent": base64.b64encode(MP3_BYTES).decode("ascii")}),
                    ],
                ) as urlopen,
            ):
                result = adapter.synthesize(
                    "A source-bound English passage.",
                    output,
                    slug="test-book",
                    title="Test Book",
                    author="Test Author",
                    direction="Narrate with clarity and restrained warmth.",
                    language_code="en-US",
                    expected_source_sha256=adapter.sha256_text("A source-bound English passage."),
                )
        self.assertEqual(result["status"], "PASS_PRIVATE_QA_REQUIRED")
        self.assertEqual(result["audio_sha256"], adapter._sha256_bytes(MP3_BYTES))
        self.assertFalse(result["release_ready"])
        self.assertEqual(urlopen.call_count, 2)
        token_request = urlopen.call_args_list[0].args[0]
        synthesis_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(token_request.full_url, "https://oauth2.googleapis.com/token")
        self.assertEqual(synthesis_request.full_url, "https://texttospeech.googleapis.com/v1/text:synthesize")
        self.assertEqual(synthesis_request.headers["Authorization"], "Bearer access-token")
        body = json.loads(synthesis_request.data.decode("utf-8"))
        self.assertEqual(body["voice"]["model_name"], "gemini-2.5-pro-tts")
        self.assertEqual(body["voice"]["languageCode"], "en-US")
        self.assertEqual(body["audioConfig"]["audioEncoding"], "MP3")
        self.assertEqual(body["input"]["text"], "A source-bound English passage.")

    def test_private_title_package_has_hash_bound_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            adc = self._adc(directory)
            source = "First paragraph.\n\nSecond paragraph with exact source text."
            responses = [
                _Response({"access_token": "access-token"}),
                _Response({"audioContent": base64.b64encode(MP3_BYTES + b"-1").decode("ascii")}),
                _Response({"audioContent": base64.b64encode(MP3_BYTES + b"-2").decode("ascii")}),
            ]
            with (
                patch.dict(os.environ, self._paid_env(adc), clear=True),
                patch.object(adapter.urllib.request, "urlopen", side_effect=responses),
            ):
                manifest = adapter.synthesize_title(
                    source,
                    directory / "private-package",
                    slug="test-book",
                    title="Test Book",
                    author="Test Author",
                    direction="Warm, exact literary narration.",
                    expected_source_sha256=adapter.sha256_text(source),
                    language_code="en-US",
                    max_text_bytes=34,
                )
            manifest_path = Path(manifest["manifest_path"])
            persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "PRIVATE_GENERATED_QA_REQUIRED")
            self.assertTrue(persisted["source_reconstruction_pass"])
            self.assertEqual(persisted["chunk_count"], 2)
            self.assertTrue(all(item["audio_sha256"] for item in persisted["chunks"]))
            self.assertTrue(persisted["private_audio_only"])
            self.assertFalse(persisted["release_ready"])
            self.assertFalse(persisted["publication_performed"])

    def test_public_output_paths_are_rejected_before_adc_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            adc = self._adc(Path(raw))
            with (
                patch.dict(os.environ, self._paid_env(adc), clear=True),
                patch.object(adapter.urllib.request, "urlopen") as urlopen,
            ):
                with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "frontend/public"):
                    adapter.synthesize(
                        "Private passage.",
                        adapter.ROOT / "frontend" / "public" / "forbidden.mp3",
                        slug="test",
                        title="Test",
                        author="Author",
                        direction="Warm.",
                        language_code="en-US",
                    )
        urlopen.assert_not_called()

    def test_other_workspace_frontend_public_path_is_also_rejected(self) -> None:
        with self.assertRaisesRegex(adapter.GeminiTTSBlocked, "frontend/public"):
            adapter._assert_private_output(Path("/tmp/other-workspace/frontend/public/audio.mp3"))

    def test_capability_probe_never_refreshes_adc(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            adc = self._adc(Path(raw))
            with (
                patch.dict(os.environ, self._paid_env(adc), clear=True),
                patch.object(adapter.urllib.request, "urlopen") as urlopen,
            ):
                result = adapter.capability_probe()
        self.assertTrue(result["available_for_private_generation"])
        self.assertEqual(result["auth_status"], "configured_not_refreshed")
        self.assertFalse(result["network_probe_performed"])
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
