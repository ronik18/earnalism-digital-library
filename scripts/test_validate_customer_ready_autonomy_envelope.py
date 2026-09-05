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

    def test_rollback_requires_the_exact_flag_false_public_reader_baseline(self) -> None:
        baseline = self.valid_text()
        mutations = {
            "release_state_not_preserved": baseline.replace("      public_reader_release_state_preserved: true", "      public_reader_release_state_preserved: false", 1),
            "existing_reader_changed": baseline.replace("      existing_reader_behavior_unchanged: true", "      existing_reader_behavior_unchanged: false", 1),
            "page_four_public": baseline.replace("      page_4_plus_must_not_become_public: true", "      page_4_plus_must_not_become_public: false", 1),
            "public_audio_nonzero": baseline.replace("      public_audio_preview_seconds: 0", "      public_audio_preview_seconds: 1", 1),
            "title_fallback_allowed": baseline.replace("    flag_false_baseline_contract:\n      reading_pass_v2_enabled: false\n      public_reader_release_state_preserved: true\n      existing_reader_behavior_unchanged: true\n      book_detail_identity_must_match_release_truth: true\n      public_reader_manifest_identity_must_match_release_truth: true\n      v2_protected_access_must_not_remain_active: true\n      page_4_plus_must_not_become_public: true\n      public_audio_preview_seconds: 0\n      unrelated_title_fallback_allowed: false", "    flag_false_baseline_contract:\n      reading_pass_v2_enabled: false\n      public_reader_release_state_preserved: true\n      existing_reader_behavior_unchanged: true\n      book_detail_identity_must_match_release_truth: true\n      public_reader_manifest_identity_must_match_release_truth: true\n      v2_protected_access_must_not_remain_active: true\n      page_4_plus_must_not_become_public: true\n      public_audio_preview_seconds: 0\n      unrelated_title_fallback_allowed: true", 1),
            "dracula_fallback_allowed": baseline.replace("    flag_false_baseline_contract:\n      reading_pass_v2_enabled: false\n      public_reader_release_state_preserved: true\n      existing_reader_behavior_unchanged: true\n      book_detail_identity_must_match_release_truth: true\n      public_reader_manifest_identity_must_match_release_truth: true\n      v2_protected_access_must_not_remain_active: true\n      page_4_plus_must_not_become_public: true\n      public_audio_preview_seconds: 0\n      unrelated_title_fallback_allowed: false\n      dracula_fallback_allowed: false", "    flag_false_baseline_contract:\n      reading_pass_v2_enabled: false\n      public_reader_release_state_preserved: true\n      existing_reader_behavior_unchanged: true\n      book_detail_identity_must_match_release_truth: true\n      public_reader_manifest_identity_must_match_release_truth: true\n      v2_protected_access_must_not_remain_active: true\n      page_4_plus_must_not_become_public: true\n      public_audio_preview_seconds: 0\n      unrelated_title_fallback_allowed: false\n      dracula_fallback_allowed: true", 1),
            "manifest_identity_omitted": baseline.replace("      public_reader_manifest_identity_must_match_release_truth: true\n", "", 1),
            "flag_false_action_omitted": baseline.replace("      - set_READING_PASS_V2_ENABLED_false\n", "", 1),
            "stale_unavailable_action": baseline.replace("      - verify_reading_pass_v2_disabled_baseline_restored", "      - verify_controlled_reader_unavailable_state_restored", 1),
            "rights_mutation": baseline.replace("      - preserve_logs_metrics_and_deployment_ids", "      - mutate_rights_release_state", 1),
            "redis_mutation": baseline.replace("      - preserve_logs_metrics_and_deployment_ids", "      - mutate_redis_content", 1),
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                self.assert_rejected(mutated)


if __name__ == "__main__":
    unittest.main()
