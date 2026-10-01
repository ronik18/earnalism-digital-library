"""Reject production and unprepared targets before importing the application."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderBenchmarkRunnerTests(unittest.TestCase):
    def run_guard(self, **changes):
        environment = {
            'PATH': os.environ['PATH'],
            'ENVIRONMENT': 'uat',
            'READER_SEGMENT_MONGO_INTEGRATION': '1',
            'MONGODB_URL': 'mongodb://127.0.0.1:27018/earnalism_uat?replicaSet=earnalism-uat-rs0',
            'READER_BENCHMARK_PYTHON': shutil.which('python3'),
            **changes,
        }
        return subprocess.run(['bash', str(ROOT / 'scripts/run_reader_benchmark.sh')],
                              cwd=ROOT, env=environment, capture_output=True, text=True, timeout=10)

    def test_production_environment_is_rejected(self):
        result = self.run_guard(ENVIRONMENT='production')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('refuses a production environment', result.stderr)

    def test_external_or_credentialed_mongo_is_rejected(self):
        for uri in ['mongodb+srv://cluster.example/production',
                    'mongodb://mongo.example/production?replicaSet=earnalism-uat-rs0',
                    'mongodb://fixture:fixture@127.0.0.1:27018/test?replicaSet=earnalism-uat-rs0',
                    'mongodb://127.0.0.1:27018,mongo.example:27018/test?replicaSet=earnalism-uat-rs0',
                    'mongodb://127.0.0.1:27019/test?replicaSet=earnalism-uat-rs0',
                    'mongodb://127.0.0.1:27018/test?replicaSet=production']:
            with self.subTest(uri=uri):
                result = self.run_guard(MONGODB_URL=uri)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('requires the unauthenticated loopback UAT replica set', result.stderr)

    def test_missing_opt_in_cannot_succeed_by_skipping_the_benchmark(self):
        result = self.run_guard(READER_SEGMENT_MONGO_INTEGRATION='0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires explicit isolated MongoDB integration opt-in', result.stderr)


if __name__ == '__main__':
    unittest.main()
