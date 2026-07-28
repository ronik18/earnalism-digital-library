#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import unittest

import sprint1_call_wild_openai_v390_representative as pilot


class CallWildOpenAIV390Tests(unittest.TestCase):
    def test_canonical_preflight_is_single_title_and_in_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                        "allowed_slugs": [pilot.SLUG],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                sanitized_source=pilot.DEFAULT_SOURCE,
                input_manifest=pilot.DEFAULT_INPUT_MANIFEST,
                private_output_dir=Path(tmp) / "private",
                output=Path(tmp) / "result.json",
                paid_lock=lock,
                whisper_cache_dir=pilot.DEFAULT_WHISPER_CACHE,
                run_budget_usd=0.15,
                title_budget_usd=8.0,
                title_spend_usd=0.0,
                sprint_budget_usd=75.0,
                sprint_spend_usd=74.0826,
            )
            payload, bundle, passages = pilot.preflight(args)
            self.assertEqual(payload["status"], "PREFLIGHT_PASS")
            self.assertEqual(bundle.slug, pilot.SLUG)
            self.assertEqual(len(passages), 4)
            self.assertEqual(payload["budget"]["estimated_tts_usd"], 0.031785)
            self.assertFalse(payload["provider_calls_ran"])

    def test_budget_fails_closed(self) -> None:
        _, passages = pilot.validate_bundle(
            pilot.DEFAULT_SOURCE, pilot.DEFAULT_INPUT_MANIFEST
        )
        result = pilot.budget(
            passages,
            run_cap=0.01,
            title_cap=8.0,
            title_spend=0.0,
            sprint_cap=75.0,
            sprint_spend=74.0826,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_wrong_lock_slug_is_rejected(self) -> None:
        raw = json.dumps(
            {
                "status": "active",
                "current_holder": "none",
                "allowed_next_holders": [],
                "allowed_slugs": ["other"],
            }
        ).encode()
        with self.assertRaisesRegex(pilot.CallWildPilotError, "does not allow"):
            pilot.validate_lock(raw)

    def test_repeat_provider_fingerprint_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            output.write_text(
                json.dumps(
                    {
                        "attempt_fingerprint": "a" * 64,
                        "provider_calls_ran": True,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                pilot.CallWildPilotError, "already reached the provider"
            ):
                pilot.reject_repeat(output, "a" * 64)


if __name__ == "__main__":
    unittest.main()
