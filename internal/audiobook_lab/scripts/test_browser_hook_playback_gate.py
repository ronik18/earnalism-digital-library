#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).resolve().parent / "factory_hooks" / "browser_hook.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("browser_hook", SCRIPT)
assert SPEC and SPEC.loader
BROWSER_HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BROWSER_HOOK)


class BrowserHookPlaybackGateTests(unittest.TestCase):
    def test_metadata_ready_without_playback_does_not_pass(self):
        probe = {
            "audio_found": True,
            "ready_state_before": 4,
            "metadata_event_kind": "already_loaded",
            "playback_advanced": False,
        }
        self.assertIsNone(BROWSER_HOOK.browser_audio_start_latency(probe))

    def test_advanced_playback_uses_click_latency(self):
        probe = {
            "audio_found": True,
            "ready_state_before": 4,
            "metadata_event_kind": "already_loaded",
            "playback_advanced": True,
            "click_to_play_ms": 87.123,
        }
        self.assertEqual(BROWSER_HOOK.browser_audio_start_latency(probe), 87.12)

    def test_invalid_click_latency_fails_closed(self):
        probe = {
            "audio_found": True,
            "playback_advanced": True,
            "click_to_play_ms": "invalid",
        }
        self.assertIsNone(BROWSER_HOOK.browser_audio_start_latency(probe))


if __name__ == "__main__":
    unittest.main()
