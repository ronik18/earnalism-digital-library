from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_customer_ready_autonomy_envelope import DEFAULT_ENVELOPE, parse_restricted_yaml, validate


class CustomerReadyAutonomyEnvelopeTests(unittest.TestCase):
    def valid_text(self) -> str:
        return DEFAULT_ENVELOPE.read_text(encoding="utf-8")

    def errors_for(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "envelope.yaml"
            path.write_text(text, encoding="utf-8")
            return validate(parse_restricted_yaml(path))

    def assert_rejected(self, text: str) -> None:
        self.assertTrue(self.errors_for(text))

    def test_exact_corrected_envelope_passes(self) -> None:
        self.assertEqual(self.errors_for(self.valid_text()), [])

    def test_audio_preview_mutations_fail_closed(self) -> None:
        baseline = self.valid_text()
        for replacement in ("180", "1", "-1", '"0"'):
            with self.subTest(replacement=replacement):
                self.assert_rejected(baseline.replace("      seconds: 0", f"      seconds: {replacement}", 1))
        self.assert_rejected(baseline.replace("      seconds: 0\n", "", 1))
        self.assert_rejected(baseline.replace("    audio_preview:\n      seconds: 0\n      only_when_audio_release_approved: true\n", "", 1))
        self.assert_rejected(baseline.replace("      only_when_audio_release_approved: true", "      only_when_audio_release_approved: false", 1))

    def test_environment_and_fallback_audio_overrides_fail_closed(self) -> None:
        baseline = self.valid_text()
        for name in ("production", "staging", "fallback_default"):
            with self.subTest(name=name):
                injection = f"  environment_overrides:\n    {name}:\n      audio_preview:\n        seconds: 180\n"
                self.assert_rejected(baseline.replace("  environment_fallback_order:\n", injection + "  environment_fallback_order:\n", 1))

    def test_protected_audio_cache_permissions_fail_closed(self) -> None:
        baseline = self.valid_text()
        redis = "  redis_audio_cache:\n    protected_audio_bytes_allowed: true\n"
        service_worker = "  service_worker_audio_cache:\n    protected_audio_caching_allowed: true\n"
        self.assert_rejected(baseline.replace("  redis_architecture:\n", redis + "  redis_architecture:\n", 1))
        self.assert_rejected(baseline.replace("  redis_architecture:\n", service_worker + "  redis_architecture:\n", 1))

    def test_customer_ready_cannot_omit_zero_audio_verification(self) -> None:
        self.assert_rejected(self.valid_text().replace("      public_audio_preview_seconds_equals_zero_verified: true\n", "", 1))

    def test_permissions_and_rollout_cannot_broaden(self) -> None:
        baseline = self.valid_text()
        mutations = {
            "unknown_permission": baseline.replace("  permissions:\n", "  permissions:\n    unrestricted_root_access: true\n", 1),
            "incremental_spend": baseline.replace("    incremental_infrastructure_spend_usd: 0", "    incremental_infrastructure_spend_usd: 1", 1),
            "other_runtime_variable": baseline.replace("      name: READING_PASS_V2_ENABLED", "      name: OTHER_RUNTIME_VARIABLE", 1),
            "automatic_rollback": baseline.replace("    automatic_rollback_required_on_threshold: true", "    automatic_rollback_required_on_threshold: false", 1),
            "exact_deployment_identity": baseline.replace("    exact_code_identity_required: true", "    exact_code_identity_required: false", 1),
            "wildcard_cors": baseline.replace("  environment_fallback_order:\n", "  cors_policy:\n    allowed_origin: \"*\"\n  environment_fallback_order:\n", 1),
            "direct_main": baseline.replace("    direct_push_to_main_allowed: false", "    direct_push_to_main_allowed: true", 1),
            "administrator_bypass": baseline.replace("    administrator_bypass_allowed: false", "    administrator_bypass_allowed: true", 1),
            "no_isolated_validation": baseline.replace("    feature_flag_value: \"true\"", "    feature_flag_value: \"false\"", 1),
            "redis_flush_permission": baseline.replace("      - redis_FLUSHALL\n", "", 1),
            "reader_acceptance_omitted": baseline.replace("      reader_approved_title_pass_percent: 100\n", "", 1),
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                self.assert_rejected(mutated)


if __name__ == "__main__":
    unittest.main()
