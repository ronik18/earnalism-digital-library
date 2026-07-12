import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from internal.audiobook_lab.scripts.sprint1_parallel_execution_board import (
    assignment_map,
    materialize,
    title_evidence,
    validate_assignments,
)


class Sprint1ParallelExecutionBoardTests(unittest.TestCase):
    def setUp(self):
        self.matrix = {
            "titles": [
                {
                    "slug": "approved",
                    "title": "Approved",
                    "sprint1_audio_target": True,
                    "publicly_available_audiobook": "Yes",
                },
                {
                    "slug": "hidden",
                    "title": "Hidden",
                    "sprint1_audio_target": True,
                    "publicly_available_audiobook": "No",
                    "exact_blocker": "QA_REQUIRED",
                },
                {
                    "slug": "deferred",
                    "title": "Deferred",
                    "sprint1_audio_target": False,
                },
            ]
        }
        self.board = {
            "lanes": [
                {
                    "lane": 1,
                    "role": "guard",
                    "agent_id": "one",
                    "agent_nickname": "One",
                    "titles": ["approved"],
                },
                {
                    "lane": 2,
                    "role": "repair",
                    "agent_id": "two",
                    "agent_nickname": "Two",
                    "titles": ["hidden"],
                },
            ]
        }

    def test_active_titles_are_assigned_exactly_once(self):
        assignments = validate_assignments(self.matrix, self.board)
        self.assertEqual(set(assignments), {"approved", "hidden"})

    def test_duplicate_assignment_is_rejected(self):
        self.board["lanes"][1]["titles"].append("approved")
        with self.assertRaisesRegex(ValueError, "duplicate title assignment"):
            assignment_map(self.board)

    def test_missing_assignment_is_rejected(self):
        self.board["lanes"][1]["titles"] = []
        with self.assertRaisesRegex(ValueError, "lane coverage mismatch"):
            validate_assignments(self.matrix, self.board)

    def test_hidden_title_evidence_stays_fail_closed(self):
        assignment = validate_assignments(self.matrix, self.board)["hidden"]
        evidence = title_evidence(self.matrix["titles"][1], assignment, "2026-01-01T00:00:00Z")
        self.assertEqual(evidence["release_gate_state"], "INCOMPLETE_FAIL_CLOSED")
        self.assertFalse(evidence["public_audio_approved_this_sprint"])
        self.assertFalse(evidence["release_gate_mutated_this_sprint"])

    def test_materializer_uses_committed_batch_manifest_when_root_manifest_is_absent(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            publication = root / "internal/audiobook_lab/sprint1_publication"
            publication.mkdir(parents=True)
            matrix = {
                "titles": [
                    {
                        **self.matrix["titles"][0],
                        "next_command": "python tool.py --manifest book_import_manifest.json",
                    },
                    {
                        **self.matrix["titles"][1],
                        "next_command": "python tool.py --manifest ./book_import_manifest.json",
                    },
                ]
            }
            final = {"titles": [{"slug": "approved"}, {"slug": "hidden"}]}
            (publication / "sprint1_publication_matrix.json").write_text(json.dumps(matrix), encoding="utf-8")
            (publication / "sprint1_final_yes_yes_matrix.json").write_text(json.dumps(final), encoding="utf-8")
            (publication / "sprint1_parallel_execution_board.json").write_text(
                json.dumps(self.board), encoding="utf-8"
            )
            materialize(root, "2026-01-01T00:00:00Z")
            updated = json.loads(
                (publication / "sprint1_publication_matrix.json").read_text(encoding="utf-8")
            )
            self.assertTrue(
                all("book_import_manifest.batch-1.json" in row["next_command"] for row in updated["titles"])
            )


if __name__ == "__main__":
    unittest.main()
