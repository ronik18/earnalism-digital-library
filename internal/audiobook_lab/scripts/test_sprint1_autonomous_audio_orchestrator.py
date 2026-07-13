import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("sprint1_autonomous_audio_orchestrator.py")
SPEC = importlib.util.spec_from_file_location("sprint1_autonomous_audio_orchestrator", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(slug, language="English", **overrides):
    payload = {
        "slug": slug,
        "title": slug,
        "language": language,
        "publicly_rendered_book": "Yes",
        "publicly_available_audiobook": "No",
        "public_audio_status": "AUDIO_HIDDEN",
        "final_status": "SPRINT_TARGET_INCOMPLETE",
        "sprint1_audio_target": True,
        "rights_status": "PASS",
        "sanitation_status": "PASS",
        "estimated_incremental_cost_usd": 0.2,
        "cost_used_usd": 0.0,
    }
    payload.update(overrides)
    return payload


class AutonomousOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.providers = {
            "google": {"available": True},
            "openai": {"available": True},
            "sarvam": {"available": True},
        }

    def test_fixed_caps_are_owner_bound_not_inherited(self):
        snapshot = MODULE.credential_snapshot({})
        self.assertEqual(snapshot["fixed_caps"]["SPRINT1_TOTAL_AUDIO_BUDGET_USD"], "175")
        self.assertEqual(snapshot["fixed_caps_source"], "OWNER_AUTHORIZED_AND_BOUND_INLINE_BY_ORCHESTRATOR")
        self.assertFalse(snapshot["secrets_printed"])

    def test_lock_requires_active_empty_fail_closed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(json.dumps({"active": True, "current_holder": "other", "allowed_next_holders": []}))
            snapshot = MODULE.lock_snapshot(path)
            self.assertFalse(snapshot["available"])
            with self.assertRaises(MODULE.OrchestratorError):
                MODULE.validate_lock(snapshot)

    def test_repository_lock_schema_accepts_active_and_none_string(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paid_tts.lock"
            path.write_text(json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}))
            snapshot = MODULE.lock_snapshot(path)
            self.assertTrue(snapshot["available"])
            MODULE.validate_lock(snapshot)

    def test_approved_title_is_never_queued_for_paid_work(self):
        approved = row(
            "a-ghost-story",
            publicly_available_audiobook="Yes",
            public_audio_status="PUBLIC_AUDIO_APPROVED",
            final_status="Yes, publicly rendered book + Yes, publicly available audiobook",
        )
        decision = MODULE.title_decision(approved, self.providers, 0)
        self.assertEqual(decision["state"], "VALIDATE_APPROVED_AND_SKIP")
        self.assertFalse(decision["paid_ready"])

    def test_human_track_and_rights_blockers_never_call_provider(self):
        human = row("the-open-window", final_status="HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED")
        rights = row("pather-panchali", language="Bengali", rights_status="OWNER_DOCUMENT_REQUIRED")
        self.assertFalse(MODULE.title_decision(human, self.providers, 0)["paid_ready"])
        self.assertEqual(MODULE.title_decision(rights, self.providers, 0)["state"], "OWNER_DOCUMENT_REQUIRED")

    def test_long_title_waits_until_five_new_short_publications(self):
        dracula = row("dracula", estimated_incremental_cost_usd=21.0)
        blocked = MODULE.title_decision(dracula, self.providers, 4)
        ready_for_preflight = MODULE.title_decision(dracula, self.providers, 5)
        self.assertEqual(blocked["state"], "WAITING_FOR_FIVE_NEW_SHORT_YES_YES")
        self.assertEqual(ready_for_preflight["state"], "ENGLISH_NON_PAID_PREFLIGHT")

    def test_dsires_uses_materially_different_achird_voice(self):
        decision = MODULE.title_decision(row("dsires-baby"), self.providers, 0)
        self.assertEqual(decision["voice"], "en-GB-Chirp3-HD-Achird")
        self.assertNotEqual(decision["voice"], "en-GB-Studio-C")
        self.assertEqual(decision["attempt_rule"], "ONE_MATERIALLY_DIFFERENT_VOICE_THEN_HUMAN_IMPORT")

    def test_fresh_short_titles_rank_by_expected_success_per_dollar(self):
        matrix = {
            "titles": [
                row("the-cop-and-the-anthem", estimated_incremental_cost_usd=0.17),
                row("the-yellow-wallpaper", estimated_incremental_cost_usd=0.38),
            ]
        }
        cost_report = {"titles": []}
        ledger = {"accounting": {"estimated_sprint_spend_usd": 10.0}}
        runtime = {"providers": self.providers}
        lock = {"available": True}
        board = MODULE.build_board(matrix, cost_report, ledger, runtime, lock)
        self.assertEqual(board["serialized_paid_queue"][0]["slug"], "the-cop-and-the-anthem")
        self.assertEqual(board["budget"]["estimated_remaining_usd"], 165.0)

    def test_conservative_accounting_checkpoint_is_authoritative(self):
        ledger = {
            "accounting": {
                "cumulative_conservative_estimated_spend_usd": 10.41276,
                "estimated_sprint_spend_usd": 4.0,
            }
        }
        self.assertEqual(MODULE.ledger_checkpoint(ledger), 10.41276)

    def test_command_builder_ignores_untrusted_matrix_next_command(self):
        action = {
            "slug": "dsires-baby",
            "decision": {
                "state": "GOOGLE_ENGLISH_ALTERNATE_AUDITION",
                "voice": "en-GB-Chirp3-HD-Achird",
                "speaking_rate": 0.9,
            },
            "next_command": "rm -rf /",
            "cost_used_usd": 0.0,
        }
        prepare, pipeline = MODULE.build_google_audition_command(
            Path("/repo"), Path("/repo/paid_tts.lock"), action, 10.0, Path("/tmp/private")
        )
        combined = " ".join(prepare + pipeline)
        self.assertNotIn("rm -rf", combined)
        self.assertIn("en-GB-Chirp3-HD-Achird", pipeline)

    def test_default_private_root_does_not_alias_default_worktree_name(self):
        args = MODULE.parse_args([])
        self.assertEqual(args.private_root.name, "earnalism-sprint1-autonomous-v2-private")

    def test_execute_preflight_failure_stops_before_paid_pipeline(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="input failed")

        board = {
            "next_paid_action": {
                "slug": "dsires-baby",
                "decision": {
                    "state": "GOOGLE_ENGLISH_ALTERNATE_AUDITION",
                    "provider": "google",
                    "voice": "en-GB-Chirp3-HD-Achird",
                    "speaking_rate": 0.9,
                },
            },
            "runtime": {"providers": self.providers},
            "lock": {"available": True},
            "budget": {"estimated_remaining_usd": 100.0, "estimated_checkpoint_usd": 10.0},
            "title_decisions": [{"slug": "dsires-baby"}],
            "matrix_rows": [{"slug": "dsires-baby", "cost_used_usd": 0.0}],
        }
        result = MODULE.execute_next_audition(
            board,
            Path("/repo"),
            Path("/repo/paid_tts.lock"),
            Path("/tmp/private"),
            {},
            runner=runner,
        )
        self.assertEqual(result["status"], "NON_PAID_INPUT_PREPARATION_FAILED")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
