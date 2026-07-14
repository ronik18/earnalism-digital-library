from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HOOK_DIR = Path(__file__).with_name("factory_hooks")
sys.path.insert(0, str(HOOK_DIR))
SPEC = importlib.util.spec_from_file_location("upload_hook_single_part", HOOK_DIR / "upload_hook.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RecordingClient:
    def __init__(self):
        self.call = None

    def upload_file(self, *args, **kwargs):
        self.call = (args, kwargs)


class UploadHookSinglePartTests(unittest.TestCase):
    def test_json_sidecars_use_json_content_type(self):
        self.assertEqual(MODULE.content_type_for_key("json"), "application/json")
        self.assertEqual(MODULE.content_type_for_key("timestamps"), "application/json")

    def test_single_part_transfer_is_explicitly_opt_in(self):
        client = RecordingClient()
        env = {
            "B2_BUCKET": "public-audio",
            "B2_S3_ENDPOINT": "https://example.test",
            "EARNALISM_B2_FORCE_SINGLE_PART_UPLOAD": "true",
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
            MODULE, "b2_client", return_value=client
        ):
            path = Path(temporary) / "audio.mp3"
            path.write_bytes(b"audio")
            MODULE.upload_b2(path, key="earnalism/audiobooks/test/audio.mp3")

        self.assertIsNotNone(client.call)
        config = client.call[1]["Config"]
        self.assertEqual(config.multipart_threshold, 64 * 1024 * 1024)
        self.assertFalse(config.use_threads)

    def test_bounded_multipart_transfer_uses_requested_chunk_size(self):
        client = RecordingClient()
        env = {
            "B2_BUCKET": "public-audio",
            "B2_S3_ENDPOINT": "https://example.test",
            "EARNALISM_B2_MULTIPART_CHUNK_BYTES": str(5 * 1024 * 1024),
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
            MODULE, "b2_client", return_value=client
        ):
            path = Path(temporary) / "audio.mp3"
            path.write_bytes(b"audio")
            MODULE.upload_b2(path, key="earnalism/audiobooks/test/audio.mp3")

        config = client.call[1]["Config"]
        self.assertEqual(config.multipart_threshold, 5 * 1024 * 1024)
        self.assertEqual(config.multipart_chunksize, 5 * 1024 * 1024)
        self.assertFalse(config.use_threads)


if __name__ == "__main__":
    unittest.main()
