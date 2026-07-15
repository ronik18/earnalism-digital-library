#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
for path in (SCRIPTS_DIR, HOOK_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import common  # noqa: E402
from factory_hooks import cover_hook  # noqa: E402


@contextmanager
def cloudinary_env(**values: str):
    keys = {"CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "CLOUDINARY_URL"}
    old = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    for key, value in values.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key in keys:
            os.environ.pop(key, None)
        for key, value in old.items():
            if value is not None:
                os.environ[key] = value


def png_bytes(size: tuple[int, int]) -> bytes:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"Pillow unavailable: {exc}") from exc

    image = Image.new("RGB", size, "#33231f")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class CloudinaryCredentialContractTests(unittest.TestCase):
    def test_three_part_credentials_are_preferred_over_cloudinary_url(self) -> None:
        calls: list[dict[str, object]] = []
        fake_cloudinary = types.SimpleNamespace(config=lambda **kwargs: calls.append(kwargs))
        with cloudinary_env(
            CLOUDINARY_CLOUD_NAME="cloud",
            CLOUDINARY_API_KEY="key",
            CLOUDINARY_API_SECRET="secret",
            CLOUDINARY_URL="cloudinary://legacy",
        ), mock.patch.dict(sys.modules, {"cloudinary": fake_cloudinary}):
            importlib.reload(common)
            self.assertEqual(common.cloudinary_credential_source(), "three_part")
            common.cloudinary_configure()

        self.assertEqual(calls, [{"cloud_name": "cloud", "api_key": "key", "api_secret": "secret", "secure": True}])

    def test_cloudinary_url_is_optional_fallback(self) -> None:
        calls: list[dict[str, object]] = []
        fake_cloudinary = types.SimpleNamespace(config=lambda **kwargs: calls.append(kwargs))
        with cloudinary_env(CLOUDINARY_URL="cloudinary://legacy"), mock.patch.dict(sys.modules, {"cloudinary": fake_cloudinary}):
            importlib.reload(common)
            self.assertEqual(common.cloudinary_credential_source(), "url")
            common.cloudinary_configure()

        self.assertEqual(calls, [{"secure": True}])

    def test_missing_cloudinary_credentials_fail_closed_without_secret_output(self) -> None:
        with cloudinary_env():
            importlib.reload(common)
            self.assertFalse(common.has_cloudinary_credentials())
            status = common.cloudinary_credentials_status()
            self.assertEqual(status["source"], "missing")
            self.assertEqual(status["CLOUDINARY_API_SECRET"], "MISSING")
            self.assertNotIn("actual-secret-value", str(status))
            with self.assertRaisesRegex(RuntimeError, "CLOUDINARY_CREDENTIALS_MISSING"):
                common.cloudinary_configure()


class ExistingCoverReuseTests(unittest.TestCase):
    def test_existing_linked_6x9_cloudinary_covers_pass_without_upload_credentials(self) -> None:
        body = png_bytes((1024, 1536))
        public_book = {
            "cover_url": "https://res.cloudinary.com/demo/image/upload/v1/front.png",
            "back_cover_url": "https://res.cloudinary.com/demo/image/upload/v1/back.png",
        }

        def fake_fetch(url: str, **_: object) -> dict[str, object]:
            return {"status": 200, "ok": True, "headers": {"Content-Type": "image/png"}, "body": body, "error": ""}

        with mock.patch.object(cover_hook, "verify_remote_checksum", return_value={"status": 200, "resolves": True}), mock.patch.object(common, "fetch_url", side_effect=fake_fetch):
            result = cover_hook.existing_cover_pass(public_book)

        self.assertTrue(result["pass"])
        self.assertEqual(result["checks"]["front"]["dimensions"], [1024, 1536])
        self.assertEqual(result["checks"]["front"]["dimension_status"], "VALID_6x9_EXISTING_ASSET")

    def test_missing_cover_links_do_not_pass(self) -> None:
        result = cover_hook.existing_cover_pass({})
        self.assertFalse(result["pass"])
        self.assertIn("missing", result["reason"])


class ControlledPublicationResolverTests(unittest.TestCase):
    def test_backend_package_is_used_when_root_mirror_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/controlled_publications/nishkriti").mkdir(parents=True)
            backend = root / "backend/data/controlled_publications/nishkriti"
            (backend / "chapters").mkdir(parents=True)
            (backend / "public_book.json").write_text("{}", encoding="utf-8")
            (backend / "chapters/0001.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(common, "ROOT", root):
                self.assertEqual(common.controlled_dir("nishkriti"), backend)


if __name__ == "__main__":
    unittest.main()
