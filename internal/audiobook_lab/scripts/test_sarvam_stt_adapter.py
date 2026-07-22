#!/usr/bin/env python3
"""Provider-free tests for the Sarvam STT adapter."""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from providers import sarvam_stt_adapter as adapter


APPROVAL_ENV = {
    "SARVAM_API_KEY": "secret",
    "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS": "true",
    "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF": "true",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
    "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN": "true",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD": "75",
    "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE": "8",
}


class SarvamSTTAdapterTests(unittest.TestCase):
    def test_provider_boundary_rejects_missing_campaign_approval(self) -> None:
        with mock.patch.dict(adapter.os.environ, {"SARVAM_API_KEY": "secret"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "approval is incomplete"):
                adapter.transcribe_rest(Path("unused.wav"))

    def test_campaign_approval_requires_positive_budgets(self) -> None:
        invalid = {**APPROVAL_ENV, "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE": "0"}
        with mock.patch.dict(adapter.os.environ, invalid, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MAX_ESTIMATED_USD_PER_TITLE"):
                adapter.require_paid_campaign_approval()

    def test_campaign_budget_caps_are_enforced(self) -> None:
        with mock.patch.dict(adapter.os.environ, APPROVAL_ENV, clear=True):
            adapter.validate_campaign_budget(title_estimate_usd=7.9, campaign_cumulative_usd=74.9)
            with self.assertRaisesRegex(RuntimeError, "per-title cap"):
                adapter.validate_campaign_budget(title_estimate_usd=8.1, campaign_cumulative_usd=10)
            with self.assertRaisesRegex(RuntimeError, "campaign cap"):
                adapter.validate_campaign_budget(title_estimate_usd=1, campaign_cumulative_usd=75.1)
    def test_timestamp_arrays_are_offset_and_length_checked(self) -> None:
        payload = {
            "timestamps": {
                "words": ["রাধারাণী গেল"],
                "start_time_seconds": [0.0],
                "end_time_seconds": [0.9],
                "timestamps": {
                    "words": ["রাধারাণী", "গেল"],
                    "start_time_seconds": [0.0, 0.5],
                    "end_time_seconds": [0.4, 0.9],
                },
            }
        }
        self.assertEqual(
            adapter.timestamp_words(payload, offset_seconds=29.0),
            [
                {"word": "রাধারাণী", "start": 29.0, "end": 29.4},
                {"word": "গেল", "start": 29.5, "end": 29.9},
            ],
        )
        payload["timestamps"]["timestamps"]["end_time_seconds"] = [0.4]
        with self.assertRaisesRegex(RuntimeError, "inconsistent"):
            adapter.timestamp_words(payload, offset_seconds=0.0)

    def test_segment_timestamps_are_not_mislabeled_as_words(self) -> None:
        payload = {
            "timestamps": {
                "words": ["রাধারাণী রথ দেখিতে গেল"],
                "start_time_seconds": [0.0],
                "end_time_seconds": [2.0],
            }
        }
        with self.assertRaisesRegex(RuntimeError, "segment timestamps"):
            adapter.timestamp_words(payload, offset_seconds=0.0)

    def test_transcribe_rest_is_timestamped_and_secret_safe(self) -> None:
        response = mock.Mock(status_code=200, headers={})
        response.json.return_value = {
            "request_id": "provider-request",
            "transcript": "রাধারাণী গেল",
            "timestamps": {
                "words": ["রাধারাণী", "গেল"],
                "start_time_seconds": [0.0, 0.5],
                "end_time_seconds": [0.4, 0.9],
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            clip = Path(raw) / "clip.wav"
            clip.write_bytes(b"RIFFaudio")
            clips = [{"index": 0, "path": clip, "offset_seconds": 0.0, "sha256": "clip-hash"}]
            with mock.patch.dict(adapter.os.environ, APPROVAL_ENV, clear=True), mock.patch.object(
                adapter, "prepare_clips", return_value=clips
            ), mock.patch.object(adapter.requests, "post", return_value=response) as post:
                result = adapter.transcribe_rest(clip, request_gap_seconds=0)
        self.assertEqual(result["text"], "রাধারাণী গেল")
        self.assertEqual(result["timestamp_granularity"], "word")
        self.assertEqual(len(result["words"]), 2)
        self.assertNotIn("provider-request", str(result))
        self.assertEqual(post.call_args.kwargs["data"]["with_timestamps"], "true")

    def test_http_error_redacts_provider_body(self) -> None:
        response = mock.Mock(status_code=403, headers={}, text="secret body")
        with tempfile.TemporaryDirectory() as raw:
            clip = Path(raw) / "clip.wav"
            clip.write_bytes(b"RIFFaudio")
            clips = [{"index": 0, "path": clip, "offset_seconds": 0.0, "sha256": "clip-hash"}]
            with mock.patch.dict(adapter.os.environ, APPROVAL_ENV, clear=True), mock.patch.object(
                adapter, "prepare_clips", return_value=clips
            ), mock.patch.object(adapter.requests, "post", return_value=response):
                with self.assertRaisesRegex(RuntimeError, "Sarvam ASR HTTP 403") as raised:
                    adapter.transcribe_rest(clip)
        self.assertNotIn("secret body", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
