"""Execute real read-only preflight with synthetic Mongo metadata, not production."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_reader_startup_readonly.py"


class Collection:
    def __init__(self, name, missing=False):
        self.name, self.missing = name, missing

    def index_information(self):
        if self.missing:
            return {}
        keys = {
            "reader_content_segments": [[("book_slug", 1), ("page_index", 1), ("segmentation_version", 1)]],
            "reader_segment_manifests": [[("book_slug", 1), ("segmentation_version", 1)], [("book_slug", 1)]],
            "reader_segment_activation_state": [[("book_slug", 1)]],
            "reader_segment_activation_operations": [[("operation_id", 1)]],
        }
        return {str(i): {"unique": True, "key": key, **({"partialFilterExpression": {"status": "active"}} if self.name == "reader_segment_manifests" and i == 1 else {})}
                for i, key in enumerate(keys[self.name])}

    def find_one(self, *_args):
        return {"generation": 1, "version": "2d6e081a92bbeac0e5364cf2", "segmentation_version": "synthetic"}

    def find(self, *_args):
        if self.name == "reader_content_segments":
            return self
        return [{"created_by": "operator"}]

    def sort(self, *_args):
        return [{"page_index": i, "content_sha256": "synthetic"} for i in range(211)]

    def count_documents(self, *_args):
        return 1


class Client:
    missing = False
    def __init__(self, *_args, **_kwargs):
        pass
    def __getitem__(self, name):
        return Collection(name, self.missing) if name.startswith("reader_") else self
    def __getattr__(self, name):
        return Collection(name, self.missing)
    def close(self):
        pass


class ReaderStartupReadOnlyTests(unittest.TestCase):
    def execute(self, missing=False, flags=None, state_digest="ed619a46c84fac9c945bb9a142519eb3e578a8b0b3dfe59ed429302c2bf44010"):
        Client.missing = missing
        env = {"MONGODB_URL": "mongodb://synthetic.invalid/test", "REDIS_CACHE_ENABLED": "false",
               "MULTI_REPLICA_ENABLED": "false", "ENABLE_STARTUP_DB_MAINTENANCE": "false",
               "READING_PASS_V2_ENABLED": "true", "ENVIRONMENT": "production",
               "ENABLE_BACKGROUND_WORKERS": "false", "ENABLE_BOOK_RENDERING_JOBS": "false", **(flags or {})}
        def fake_hash(payload):
            digest = ("df15333c38446899cb090888354e2bbf3cfdfd40979489ece414c376be020b62" if payload.startswith(b"[")
                      else state_digest)
            return types.SimpleNamespace(hexdigest=lambda: digest)
        output = io.StringIO()
        with patch.dict("os.environ", env), patch.dict("sys.modules", {"pymongo": types.SimpleNamespace(MongoClient=Client)}), \
             patch("hashlib.sha256", side_effect=fake_hash), contextlib.redirect_stdout(output):
            runpy.run_path(str(SCRIPT), run_name="__main__")
        return json.loads(output.getvalue())

    def test_safe_metadata_is_accepted_without_write_methods(self):
        self.assertEqual(self.execute()["startup_preflight"], "PASS")

    def test_missing_indexes_fail_closed(self):
        with self.assertRaises(SystemExit):
            self.execute(missing=True)

    def test_other_publication_or_configuration_drift_fails_closed(self):
        with self.assertRaises(SystemExit):
            self.execute(state_digest="changed-observed-state")

    def test_unsafe_configuration_fails_closed(self):
        for flag in ("REDIS_CACHE_ENABLED", "MULTI_REPLICA_ENABLED", "ENABLE_STARTUP_DB_MAINTENANCE", "ENABLE_BACKGROUND_WORKERS", "ENABLE_BOOK_RENDERING_JOBS"):
            with self.subTest(flag=flag), self.assertRaises(SystemExit):
                self.execute(flags={flag: "true"})

    def test_changed_publication_or_content_fails_closed(self):
        for field, value in (("generation", 2), ("version", "other-manifest")):
            with patch.object(Collection, "find_one", return_value={"generation": 1, "version": "2d6e081a92bbeac0e5364cf2", "segmentation_version": "synthetic", field: value}):
                with self.assertRaises(SystemExit):
                    self.execute()


if __name__ == "__main__":
    unittest.main()
