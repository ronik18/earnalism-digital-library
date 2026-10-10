"""Read-only HTTP/provider release identity gate. No source input is attested."""
import argparse
import json
import re
import subprocess
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler

PROJECT = "a8533934-35c4-463e-9f43-577a9ac391ee"
SERVICE = "5af42e7e-f518-4f6a-b602-d9950866501f"
ENVIRONMENT = "580b250c-80ee-48ad-bfbe-fa4e31a6b378"
ORIGIN = "https://api.theearnalism.com"


class VerificationError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise VerificationError("Backend redirect rejected")


def read_json(url):
    if not url.startswith(ORIGIN + "/"):
        raise VerificationError("Unapproved backend origin")
    with build_opener(NoRedirect).open(Request(url, headers={"Cache-Control": "no-cache"}), timeout=20) as response:
        if response.status != 200 or response.geturl() != url:
            raise VerificationError("Unexpected backend response")
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise VerificationError("Oversized backend response")
        return json.loads(raw), response.headers


def verify(expected, project, service, environment, health, provider, schema, headers):
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise VerificationError("Invalid expected SHA")
    if (project, service, environment) != (PROJECT, SERVICE, ENVIRONMENT):
        raise VerificationError("Unapproved production identity")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise VerificationError("Backend unhealthy or malformed")
    attestation = health.get("deployment")
    if not isinstance(attestation, dict) or attestation.get("status") != "AVAILABLE":
        raise VerificationError("Serving provenance unavailable")
    required = {"git_sha": expected, "project_id": project, "service_id": service, "environment_id": environment}
    if any(attestation.get(key) != value for key, value in required.items()):
        raise VerificationError("Serving source/identity mismatch")
    deployment_id = attestation.get("deployment_id")
    if not isinstance(deployment_id, str) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", deployment_id):
        raise VerificationError("Invalid serving deployment ID")
    if "no-store" not in headers.get("Cache-Control", "").lower():
        raise VerificationError("Serving attestation must not be cached")
    if provider.get("id") != project:
        raise VerificationError("Provider project mismatch")
    environments = [edge["node"] for edge in provider["environments"]["edges"] if edge["node"].get("id") == environment]
    if len(environments) != 1 or environments[0].get("name") != "production":
        raise VerificationError("Provider environment mismatch")
    services = [edge["node"] for edge in environments[0]["serviceInstances"]["edges"] if edge["node"].get("serviceId") == service]
    if len(services) != 1:
        raise VerificationError("Provider service missing/ambiguous")
    actual = services[0]["latestDeployment"]
    if actual.get("id") != deployment_id or actual.get("status") != "SUCCESS" or actual.get("deploymentStopped") is not False:
        raise VerificationError("Deployment stale, stopped, or not successful")
    if not any(instance.get("status") == "RUNNING" for instance in actual.get("instances", [])):
        raise VerificationError("No running production instance")
    if actual.get("meta", {}).get("commitHash") != expected:
        raise VerificationError("Provider Git source unavailable/mismatched")
    paths = schema.get("paths", {})
    for path in ("/api/reading-pass/sessions/start", "/api/reading-pass/leases/renew", "/api/reading-pass/sessions/end"):
        if "post" not in paths.get(path, {}):
            raise VerificationError("Lifecycle API unavailable")
    if not any("text_phase" in item.get("properties", {}) for item in schema.get("components", {}).get("schemas", {}).values()):
        raise VerificationError("Preparation lifecycle schema unavailable")
    return {"serving_sha": attestation["git_sha"], "deployment_id": deployment_id, "project_id": project,
            "service_id": service, "environment_id": environment, "health": "PASS", "lifecycle": "PASS"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--backend-url", required=True)
    args = parser.parse_args()
    try:
        if args.backend_url != ORIGIN:
            raise VerificationError("Unapproved backend URL")
        # Capture provider output privately; never log credentials or raw provider data.
        result = subprocess.run(["railway", "status", "--project", args.project, "--environment", args.environment, "--json"],
                                check=True, capture_output=True, text=True, timeout=40)
        provider = json.loads(result.stdout)
        health, headers = read_json(ORIGIN + "/healthz")
        schema, _ = read_json(ORIGIN + "/openapi.json")
        report = verify(args.expected_sha, args.project, args.service, args.environment, health, provider, schema, headers)
        print(json.dumps(report, sort_keys=True))
    except Exception:
        print("BACKEND_VERIFICATION=FAIL (source/identity/health/schema/provider evidence unavailable or mismatched)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
