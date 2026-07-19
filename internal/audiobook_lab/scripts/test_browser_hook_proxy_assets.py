#!/usr/bin/env python3

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_PATH = SCRIPTS_DIR / "factory_hooks" / "browser_hook.py"
sys.path.insert(0, str(SCRIPTS_DIR / "factory_hooks"))
SPEC = importlib.util.spec_from_file_location("browser_hook_proxy_assets", HOOK_PATH)
BROWSER_HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BROWSER_HOOK)


class BrowserHookProxyAssetTests(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(slug="the-open-window")

    def test_public_audio_assets_use_release_gated_proxy_routes(self):
        book = {
            "cover_url": "https://images.example/front.png",
            "back_cover_url": "https://images.example/back.png",
            "audiobook_assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/private/raw.mp3",
                "timestamps": "https://s3.us-west-004.backblazeb2.com/private/raw.json",
            },
        }
        with patch.object(BROWSER_HOOK, "load_public_book", return_value=book), patch.object(
            BROWSER_HOOK, "api_url", return_value="https://api.theearnalism.com/api"
        ):
            assets = BROWSER_HOOK.public_assets(self.args)

        base = "https://api.theearnalism.com/api/reader/book/the-open-window/audiobook"
        self.assertEqual(assets["mp3"], base)
        self.assertEqual(assets["timestamps"], f"{base}/timestamps")
        self.assertEqual(assets["vtt"], f"{base}/vtt")
        self.assertEqual(assets["chapters"], f"{base}/chapters")
        self.assertEqual(assets["meta"], f"{base}/meta")
        self.assertNotIn("backblazeb2.com", " ".join(assets.values()))

    def test_asset_checks_ranges_mp3_and_fetches_sidecars_through_proxy(self):
        assets = {
            "front_cover": "https://images.example/front.png",
            "back_cover": "https://images.example/back.png",
            "mp3": "https://api.example/audiobook",
            "timestamps": "https://api.example/audiobook/timestamps",
            "vtt": "https://api.example/audiobook/vtt",
            "chapters": "https://api.example/audiobook/chapters",
            "meta": "https://api.example/audiobook/meta",
        }
        success = {"ok": True, "status": 206, "headers": {}, "error": ""}
        with patch.object(BROWSER_HOOK, "public_assets", return_value=assets), patch.object(
            BROWSER_HOOK, "fetch_audio_start", return_value=success
        ) as audio_fetch, patch.object(BROWSER_HOOK, "fetch_url", return_value={**success, "status": 200}) as normal_fetch:
            checks = BROWSER_HOOK.asset_checks(self.args)

        audio_fetch.assert_called_once_with(assets["mp3"])
        self.assertEqual(normal_fetch.call_count, 6)
        self.assertTrue(all(item["ok"] for item in checks.values()))

    def test_private_origin_check_requires_anonymous_denial(self):
        book = {
            "audiobook_assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/book.mp3",
                "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/timestamps.json",
            }
        }
        denied = {"ok": False, "status": 401, "headers": {}, "error": "UnauthorizedAccess"}
        with patch.object(BROWSER_HOOK, "load_public_book", return_value=book), patch.object(
            BROWSER_HOOK, "fetch_url", return_value=denied
        ):
            checks = BROWSER_HOOK.private_origin_denial_checks(self.args)

        self.assertEqual(set(checks), {"mp3", "timestamps"})
        self.assertTrue(all(item["anonymous_access_denied"] for item in checks.values()))


if __name__ == "__main__":
    unittest.main()
