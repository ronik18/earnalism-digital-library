#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "factory_hooks"))
sys.path.insert(0, str(SCRIPT_DIR / "providers"))

import asr_sync_hook  # noqa: E402
import sarvam_tts_adapter  # noqa: E402


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class ProviderStdlibHttpTest(unittest.TestCase):
    def test_vertex_aggregate_requires_its_own_cost_cap_not_openai_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EARNALISM_LISTENING_QA_PROVIDER": "vertex",
                "EARNALISM_ENABLE_LISTENING_QA": "true",
                "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/test-adc.json",
                "GOOGLE_CLOUD_PROJECT": "test-project",
            },
            clear=True,
        ):
            result = asr_sync_hook.run_openai_listening_judge(
                SimpleNamespace(title="Title", author="Author", language="Bengali", slug="test"),
                Path("/tmp/not-read.mp3"),
                Path("/tmp"),
                [{"sample_label": "probe"}],
                "hash",
            )
        self.assertIn("LISTENING_QA_BUDGET_GATE_MISSING", result["_external_judge_error"])

    def test_vertex_listening_judge_uses_adc_and_structured_json(self) -> None:
        judgment = {
            field: 9.3 for field in asr_sync_hook.LISTENING_THRESHOLDS if field != "confidence_score"
        }
        judgment.update(
            {
                "confidence_score": 0.92,
                **{field: False for field in asr_sync_hook.BINARY_LISTENING_FLAGS},
                "frontmatter_present": False,
                "notes": "bounded vertex test",
                "blocker_reason": "",
            }
        )
        model_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(judgment),
                            }
                        ]
                    }
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "sample.mp3"
            audio_path.write_bytes(b"ID3-test")
            credentials_path = Path(temp_dir) / "adc.json"
            credentials_path.write_text(
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
            with (
                patch.dict(
                    os.environ,
                    {
                        "GOOGLE_APPLICATION_CREDENTIALS": str(credentials_path),
                        "GOOGLE_CLOUD_PROJECT": "test-project",
                    },
                    clear=False,
                ),
                patch.object(
                    asr_sync_hook.urllib.request,
                    "urlopen",
                    side_effect=[
                        _Response({"access_token": "access-token"}),
                        _Response(model_payload),
                    ],
                ) as urlopen,
            ):
                result = asr_sync_hook.judge_audio_sample_with_vertex(
                    SimpleNamespace(title="Title", author="Author", language="Bengali"),
                    {
                        "sample_audio_path": str(audio_path),
                        "sample_label": "probe",
                        "start_time": 0.0,
                        "duration": 1.0,
                    },
                )
        self.assertEqual(result["scores"]["overall_listening_score"], 9.3)
        self.assertEqual(result["confidence"], 0.92)
        self.assertEqual(result["judge_provider"], "vertex")
        model_request = urlopen.call_args_list[1].args[0]
        self.assertIn("gemini-2.5-flash:generateContent", model_request.full_url)

    def test_openai_listening_judge_works_without_sdk_client(self) -> None:
        judgment = {
            field: 9.2 for field in asr_sync_hook.LISTENING_THRESHOLDS if field != "confidence_score"
        }
        judgment.update(
            {
                "confidence_score": 0.91,
                **{field: False for field in asr_sync_hook.BINARY_LISTENING_FLAGS},
                "frontmatter_present": False,
                "notes": "bounded test",
                "blocker_reason": "",
            }
        )
        payload = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "arguments": json.dumps(judgment),
                                }
                            }
                        ]
                    }
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "sample.mp3"
            audio_path.write_bytes(b"ID3-test")
            with (
                patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False),
                patch.object(asr_sync_hook.urllib.request, "urlopen", return_value=_Response(payload)) as urlopen,
            ):
                result = asr_sync_hook.judge_audio_sample_with_openai(
                    None,
                    SimpleNamespace(title="Title", author="Author", language="Bengali"),
                    {
                        "sample_audio_path": str(audio_path),
                        "sample_label": "probe",
                        "start_time": 0.0,
                        "duration": 1.0,
                    },
                )
        self.assertEqual(result["scores"]["overall_listening_score"], 9.2)
        self.assertEqual(result["confidence"], 0.91)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")

    def test_sarvam_synthesis_uses_stdlib_http(self) -> None:
        audio_bytes = b"ID3-sarvam-test"
        payload = {"audios": [base64.b64encode(audio_bytes).decode("ascii")]}
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "sample.mp3"
            with (
                patch.dict(os.environ, {"SARVAM_API_KEY": "test-key"}, clear=False),
                patch.object(sarvam_tts_adapter.urllib.request, "urlopen", return_value=_Response(payload)),
            ):
                result = sarvam_tts_adapter.synthesize(
                    "নমুনা",
                    out_path,
                    speaker="ratan",
                    output_codec="mp3",
                )
            self.assertEqual(out_path.read_bytes(), audio_bytes)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["output_codec"], "mp3")


if __name__ == "__main__":
    unittest.main()
