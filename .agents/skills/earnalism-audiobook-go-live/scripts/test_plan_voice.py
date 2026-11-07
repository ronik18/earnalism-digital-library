import unittest
from plan_voice import plan

class VoicePlanTests(unittest.TestCase):
    def test_accepted_master_wins_over_new_voice_or_theme(self):
        result = plan("the-open-window", theme="adventure", presentation="female")
        self.assertEqual(result["status"], "VERIFY_EXISTING_ACCEPTED_BINDING")
        self.assertIn("title name alone", result["next_action"])
        self.assertFalse(result["generation_authorized"])

    def test_selfish_giant_resume_reuses_accepted_package_not_new_audition(self):
        result = plan(" THE-SELFISH-GIANT ", theme="adventure", presentation="female")
        self.assertEqual(result["status"], "VERIFY_EXISTING_ACCEPTED_BINDING")
        self.assertEqual(result["accepted_package"], "sha256-b00212b82996e194a7b3bef4f3fb8982304b71afcd32e5f0fa6e93e9341f3211")
        self.assertTrue(result["requested_direction_not_applied"])
        self.assertFalse(result["generation_authorized"])
        self.assertEqual(result["network_requests"], 0)
        self.assertNotIn("supported_request_fields", result)

    def test_future_title_does_not_inherit_another_titles_acceptance(self):
        result = plan("the-happy-prince", theme="reflective")
        self.assertEqual(result["status"], "DIRECTION_PROPOSAL_NOT_QUALIFIED")
        self.assertNotIn("accepted_package", result)
        self.assertIn("current canonical title records", result["next_action"])
        self.assertFalse(result["generation_authorized"])
        self.assertEqual(result["network_requests"], 0)

    def test_new_male_is_a_proposal_not_a_grant(self):
        result = plan("another-cleared-title", theme="suspense")
        self.assertEqual(result["speaker"], "Ryan")
        self.assertEqual(set(result["supported_request_fields"]), {"speaker", "language", "instruct"})
        self.assertIn("Do not whisper", result["supported_request_fields"]["instruct"])
        self.assertFalse(result["generation_authorized"])

    def test_female_candidate_does_not_inherit_male_acceptance(self):
        result = plan("another-cleared-title", presentation="female")
        self.assertEqual(result["speaker"], "Serena")
        self.assertEqual(result["qualification"], "CONFIGURED_NOT_AUDITIONED")
        self.assertEqual(result["native_language"], "Chinese")
        self.assertFalse(result["generation_authorized"])

    def test_unsupported_language_cannot_fall_back(self):
        result = plan("bengali-title", language="bn")
        self.assertEqual(result["status"], "HOLD_LANGUAGE_QUALIFICATION")
        self.assertEqual(result["network_requests"], 0)

    def test_unknown_theme_fails_before_generation(self):
        with self.assertRaises(ValueError):
            plan("another-title", theme="invented-effect")

if __name__ == "__main__": unittest.main()
