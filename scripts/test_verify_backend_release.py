import copy
import unittest
from unittest.mock import patch
from scripts.verify_backend_release import (verify, read_json, main, NoRedirect, VerificationError,
                                           PROJECT, SERVICE, ENVIRONMENT, ORIGIN)


class BackendReleaseTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.deployment = "11111111-1111-1111-1111-111111111111"
        self.health = {"status": "ok", "deployment": {"status": "AVAILABLE", "git_sha": self.sha,
            "deployment_id": self.deployment, "project_id": PROJECT, "service_id": SERVICE, "environment_id": ENVIRONMENT}}
        self.provider = {"id": PROJECT, "environments": {"edges": [{"node": {"id": ENVIRONMENT, "name": "production",
            "serviceInstances": {"edges": [{"node": {"serviceId": SERVICE, "latestDeployment": {
                "id": self.deployment, "status": "SUCCESS", "deploymentStopped": False,
                "instances": [{"status": "RUNNING"}], "meta": {"commitHash": self.sha}}}}]}}}]}}
        self.schema = {"paths": {path: {"post": {}} for path in ("/api/reading-pass/sessions/start",
            "/api/reading-pass/leases/renew", "/api/reading-pass/sessions/end")},
            "components": {"schemas": {"Lease": {"properties": {"text_phase": {"type": "string"}}}}}}
        self.headers = {"Cache-Control": "no-store"}

    def check(self):
        return verify(self.sha, PROJECT, SERVICE, ENVIRONMENT, self.health, self.provider, self.schema, self.headers)

    def test_independent_matching_provider_and_http_pass(self):
        self.assertEqual(self.check()["deployment_id"], self.deployment)

    def test_missing_malformed_wrong_and_unhealthy_http_fail_closed(self):
        good = copy.deepcopy(self.health)
        cases = [None, {}, {"status": "bad"}, {"status": "ok", "deployment": {"status": "UNAVAILABLE"}}]
        for field in ("git_sha", "deployment_id", "project_id", "service_id", "environment_id"):
            broken = copy.deepcopy(good)
            broken["deployment"][field] = "wrong"
            cases.append(broken)
        for item in cases:
            with self.subTest(item=item):
                self.health = item
                with self.assertRaises(VerificationError):
                    self.check()

    def test_provider_revision_deployment_health_and_identity_fail_closed(self):
        good = copy.deepcopy(self.provider)
        for field, value in (("id", "old-deployment"), ("status", "DEPLOYING"), ("deploymentStopped", True),
                             ("instances", []), ("meta", {}), ("meta", {"commitHash": "b" * 40})):
            self.provider = copy.deepcopy(good)
            deployment = self.provider["environments"]["edges"][0]["node"]["serviceInstances"]["edges"][0]["node"]["latestDeployment"]
            deployment[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(VerificationError):
                self.check()
        self.provider = {**good, "id": "other-project"}
        with self.assertRaises(VerificationError):
            self.check()
        self.provider = copy.deepcopy(good)
        self.provider["environments"]["edges"][0]["node"]["id"] = "other-environment"
        with self.assertRaises(VerificationError):
            self.check()
        self.provider = copy.deepcopy(good)
        self.provider["environments"]["edges"][0]["node"]["serviceInstances"]["edges"][0]["node"]["serviceId"] = "other-service"
        with self.assertRaises(VerificationError):
            self.check()

    def test_missing_lifecycle_and_cached_attestation_fail(self):
        self.schema = {}
        with self.assertRaises(VerificationError):
            self.check()
        self.setUp()
        self.headers = {"Cache-Control": "public, max-age=60"}
        with self.assertRaises(VerificationError):
            self.check()

    def test_unapproved_origin_and_redirect_fail_before_credentials(self):
        for url in ("http://api.theearnalism.com/healthz", "https://evil.invalid/healthz"):
            with self.assertRaises(VerificationError):
                read_json(url)
        with self.assertRaises(VerificationError):
            NoRedirect().redirect_request(None, None, None, None, None, "https://evil.invalid")

    def test_expected_sha_is_not_echoed_on_missing_provider_access(self):
        args = ["gate", "--expected-sha", self.sha, "--project", PROJECT, "--service", SERVICE,
                "--environment", ENVIRONMENT, "--backend-url", ORIGIN]
        with patch("sys.argv", args), patch("subprocess.run", side_effect=RuntimeError("credential-like-secret")), patch("builtins.print") as output:
            self.assertEqual(main(), 1)
            self.assertNotIn(self.sha, str(output.call_args_list))
            self.assertNotIn("credential-like-secret", str(output.call_args_list))


if __name__ == "__main__":
    unittest.main()
