"""Offline fault tests; no provider calls or real secrets."""
import hashlib
import json
import subprocess
import unittest
from types import SimpleNamespace
from scripts.india_release_provider_adapter import process_diagnostic


class DiagnosticTests(unittest.TestCase):
    def test_known_reports_do_not_establish_no_effect(self):
        for message, expected in [
            ('dns error: failed to lookup address information', 'DNS_LOOKUP_FAILED'),
            ('Unauthorized; please login', 'AUTHENTICATION_REPORTED'),
            ('unexpected argument --synthetic', 'CLI_ARGUMENT_REJECTED'),
            ('Failed to upload code. File too large (123 bytes)', 'UPLOAD_SIZE_REJECTED'),
            ('Failed to upload code with status code 503', 'UPLOAD_HTTP_REJECTED'),
            ('archive permission denied', 'UNKNOWN_FAILURE'),
            ('', 'UNKNOWN_FAILURE'),
            ('Unauthorized; unexpected argument', 'UNKNOWN_FAILURE'),
        ]:
            with self.subTest(expected=expected, message=message):
                result = process_diagnostic(SimpleNamespace(returncode=1, stdout='', stderr=message))
                self.assertEqual(result['class'], expected)
                self.assertEqual(result['effect'], 'UNKNOWN_REQUIRES_NATIVE_RECONCILIATION')

    def test_raw_output_and_exception_message_never_retained(self):
        secret = 'synthetic-token-DO-NOT-RETAIN'
        for result in [
            process_diagnostic(SimpleNamespace(returncode=1, stdout=secret, stderr='Unauthorized '+secret)),
            process_diagnostic(error=RuntimeError(secret)),
        ]:
            self.assertNotIn(secret, json.dumps(result))
            self.assertEqual(set(result), {'schema', 'class', 'effect', 'stdout_bytes', 'stderr_bytes', 'stdout_sha256', 'stderr_sha256'})

    def test_full_output_is_hashed_not_truncated_or_returned(self):
        data = b'not-a-real-secret' * 10000
        result = process_diagnostic(SimpleNamespace(returncode=1, stdout=data, stderr=b'\xff'))
        self.assertEqual(result['stdout_bytes'], len(data))
        self.assertEqual(result['stdout_sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(result['stderr_sha256'], hashlib.sha256(b'\xff').hexdigest())

    def test_success_is_not_acceptance(self):
        result = process_diagnostic(SimpleNamespace(returncode=0))
        self.assertEqual(result['class'], 'PROCESS_EXIT_ZERO')
        self.assertEqual(result['effect'], 'UNKNOWN_REQUIRES_NATIVE_RECONCILIATION')

    def test_timeout_preserves_partial_output_digest(self):
        result = process_diagnostic(error=subprocess.TimeoutExpired('synthetic', 1, output=b'partial', stderr=b'error'))
        self.assertEqual(result['class'], 'PROCESS_TIMEOUT')
        self.assertEqual(result['stdout_sha256'], hashlib.sha256(b'partial').hexdigest())
        self.assertEqual(process_diagnostic(error=TimeoutError())['class'], 'PROCESS_TIMEOUT')

if __name__ == '__main__': unittest.main()
