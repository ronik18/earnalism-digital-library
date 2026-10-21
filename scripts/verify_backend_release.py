"""Read-only HTTP/provider release identity gate. No source input is attested."""
import argparse
import datetime
import hashlib
import os
from urllib.parse import urlparse, parse_qs
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



def classify_provider_error(exc):
    """Return constants only; reported error text is evidence, never authority."""
    if isinstance(exc, FileNotFoundError):
        return 'COMMAND_UNAVAILABLE', 'EXECUTABLE_NOT_FOUND'
    if isinstance(exc, subprocess.TimeoutExpired):
        return 'TRANSPORT_OR_COMMAND_TIMEOUT', 'LOCAL_COMMAND_TIMEOUT'
    if not isinstance(exc, subprocess.CalledProcessError):
        return 'UNKNOWN', 'UNRECOGNIZED_EXCEPTION'
    raw = exc.stderr
    if not isinstance(raw, (str, bytes)) or not raw:
        return 'UNKNOWN', 'STDERR_NOT_AVAILABLE'
    if len(raw) > 65536:
        return 'UNKNOWN', 'STDERR_EXCEEDS_BOUND'
    text = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text).lower()
    patterns = {
        'CREDENTIAL_EXPIRED_REPORTED': r'\b(?:token|credential|session) (?:has )?expired\b',
        'CREDENTIAL_INVALID_REPORTED': r'\b(?:invalid (?:api |access |railway )?token|token is invalid)\b',
        'TOKEN_TYPE_OR_SCOPE_REPORTED': r'\b(?:unsupported token type|incorrect token type|insufficient token scope|token scope is insufficient)\b',
        'PROJECT_ACCESS_DENIED_REPORTED': r'\b(?:access denied to (?:this |the )?project|permission denied for (?:this |the )?project|not authorized to access (?:this |the )?project)\b',
        'PROJECT_UNAVAILABLE_REPORTED': r'\b(?:project not found|project does not exist)\b',
        'AUTHENTICATION_REQUIRED_REPORTED': r'\b(?:not logged in|authentication required|unauthorized)\b',
        'TRANSPORT_DNS_REPORTED': r'\b(?:could not resolve host|failed to lookup address|name or service not known|temporary failure in name resolution)\b',
        'TRANSPORT_TLS_REPORTED': r'\b(?:certificate verify failed|invalid peer certificate|tls handshake failed)\b',
        'TRANSPORT_CONNECTION_REPORTED': r'\b(?:connection refused|connection reset|network is unreachable)\b',
        'COMMAND_ARGUMENT_ERROR_REPORTED': r'\b(?:unexpected argument|unrecognized option|unknown option|unknown subcommand)\b',
        'RUNTIME_DEPENDENCY_ERROR_REPORTED': r'\b(?:cannot find module|error while loading shared libraries|modulenotfounderror)\b',
        'CONFIGURATION_ERROR_REPORTED': r'\b(?:invalid configuration|configuration file not found|failed to parse configuration)\b',
    }
    matches = [category for category, pattern in patterns.items() if re.search(pattern, text)]
    if len(matches) != 1:
        return 'UNKNOWN', 'AMBIGUOUS_PATTERNS' if matches else 'UNRECOGNIZED_STDERR'
    return matches[0], 'REPORTED_STDERR_PATTERN'


# This is operator-attested provider evidence, never a fabricated Railway API response.
EXACT_FRONTEND = 'b3998d72f2e93bd99ffb1563c906c77e78aa5b49'
EXACT_FRONTEND_TREE = '8708ec1a1d506fdf3c5e6af1dde6face3a98c1a1'
EXACT_BACKEND = '0f2bb1e728890f1f0e41ded9b12f07c76246bce0'
EXACT_BACKEND_TREE = '2c7b9ce0f219ebdf12129bdcf4dd3faf07e22af5'
EXACT_DEPLOYMENT = '168e2abf-6b42-455e-b6c8-e2f8b77be4d3'


def frontend_only_scope(env):
    return all(env.get(k) == v for k, v in {
        'FRONTEND_SHA': EXACT_FRONTEND, 'FRONTEND_TREE': EXACT_FRONTEND_TREE,
        'BACKEND_SHA': EXACT_BACKEND, 'BACKEND_TREE': EXACT_BACKEND_TREE,
    }.items())


def evidence_digest(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def verify_operator_provider_evidence(raw, expected, now=None):
    if expected != EXACT_BACKEND or not frontend_only_scope(os.environ):
        raise VerificationError('Provider evidence scope mismatch')
    if not isinstance(raw, str) or not 0 < len(raw.encode()) <= 32768:
        raise VerificationError('Provider evidence missing or oversized')
    evidence = json.loads(raw)
    if evidence.get('schema') != 'reader-backend-provider-evidence.v1':
        raise VerificationError('Provider evidence schema mismatch')
    ui = evidence['authenticated_provider_ui_receipt']
    if ui.get('authenticated_provider_ui') is not True or any(ui.get(k) != v for k, v in {
        'project_id': PROJECT, 'service_id': SERVICE, 'environment_id': ENVIRONMENT,
    }.items()):
        raise VerificationError('Authenticated provider target mismatch')
    observed = datetime.datetime.fromisoformat(ui['observed_at_utc'])
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if observed.tzinfo is None or not datetime.timedelta(0) <= now-observed <= datetime.timedelta(minutes=15):
        raise VerificationError('Provider evidence stale or future-dated')
    deployment = ui['deployment']
    if any(type(deployment.get(k)) is not type(v) or deployment[k] != v for k, v in {
        'id': EXACT_DEPLOYMENT, 'current_active_card': True, 'status': 'ACTIVE',
        'service_status': 'Online', 'deployment_result': 'Deployment successful',
        'replicas_display': 1, 'full_source_sha': EXACT_BACKEND,
    }.items()):
        raise VerificationError('Provider deployment not current/online/exact')
    status = evidence['railway_origin_github_commit_status']
    if evidence.get('github_source_sha') != EXACT_BACKEND or any(status.get(k) != v for k, v in {
        'state': 'success', 'context': 'earnalism - earnalism', 'creator': 'railway-app[bot]',
        'description': 'Success - api.theearnalism.com',
    }.items()):
        raise VerificationError('Railway-origin source association mismatch')
    if type(status.get('id')) is not int or status['id'] <= 0:
        raise VerificationError('Missing immutable GitHub status identity')
    url = urlparse(status['target_url'])
    if (url.scheme, url.netloc, url.path, url.fragment) != (
            'https', 'railway.com', '/project/'+PROJECT+'/service/'+SERVICE, '') or parse_qs(url.query) != {
            'id': [EXACT_DEPLOYMENT], 'environmentId': [ENVIRONMENT]}:
        raise VerificationError('Railway-origin deployment association mismatch')
    return evidence_digest(raw)


def verify_protected_evidence_binding(raw, approval_raw):
    # Called only inside the existing protected environment, before any mutation.
    approval = json.loads(approval_raw)
    if approval.get('backend_provider_evidence_sha256') != evidence_digest(raw):
        raise VerificationError('Protected operator evidence digest mismatch')
    if approval.get('backend_provider_evidence_mode') != 'authenticated-ui-and-railway-origin-status.v1':
        raise VerificationError('Protected provider evidence mode mismatch')


def verify_http_without_provider(expected, project, service, environment, health, schema, headers):
    # Reuse every HTTP/schema check without synthesizing machine provider fields.
    if (expected, project, service, environment) != (EXACT_BACKEND, PROJECT, SERVICE, ENVIRONMENT):
        raise VerificationError('Exact backend identity required')
    attestation = health.get('deployment', {})
    if health.get('status') != 'ok' or attestation.get('status') != 'AVAILABLE' or any(
            attestation.get(k) != v for k, v in {
                'git_sha': expected, 'project_id': project, 'service_id': service,
                'environment_id': environment, 'deployment_id': EXACT_DEPLOYMENT}.items()):
        raise VerificationError('Live serving declaration mismatch/unavailable')
    if 'no-store' not in headers.get('Cache-Control', '').lower():
        raise VerificationError('Serving attestation must not be cached')
    paths = schema.get('paths', {})
    for path in ('/api/reading-pass/sessions/start', '/api/reading-pass/leases/renew', '/api/reading-pass/sessions/end'):
        if 'post' not in paths.get(path, {}):
            raise VerificationError('Lifecycle API unavailable')
    if 'get' not in paths.get('/api/admin/books/{book_id}/serving-binding', {}):
        raise VerificationError('Exact admin binding route unavailable')
    if not any('text_phase' in x.get('properties', {}) for x in schema.get('components', {}).get('schemas', {}).values()):
        raise VerificationError('Preparation lifecycle schema unavailable')
    return {'serving_sha': expected, 'deployment_id': EXACT_DEPLOYMENT, 'project_id': project,
            'service_id': service, 'environment_id': environment, 'health': 'PASS', 'lifecycle': 'PASS',
            'provider_basis': 'PROTECTED_OPERATOR_ATTESTATION_OF_AUTHENTICATED_UI_AND_RAILWAY_ORIGIN_STATUS'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-provider-evidence", action="store_true")
    parser.add_argument("--require-protected-binding", action="store_true")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--backend-url", required=True)
    args = parser.parse_args()
    stage = 'argument_validation'
    try:
        if args.backend_url != ORIGIN:
            raise VerificationError("Unapproved backend URL")
        if args.operator_provider_evidence:
            stage = 'operator_provider_evidence'
            raw = os.environ.get('BACKEND_PROVIDER_EVIDENCE_JSON', '')
            digest = verify_operator_provider_evidence(raw, args.expected_sha)
            if args.require_protected_binding:
                verify_protected_evidence_binding(raw, os.environ.get('RELEASE_APPROVAL_JSON', ''))
            stage = 'health_http_read'
            health, headers = read_json(ORIGIN + '/healthz')
            stage = 'schema_http_read'
            schema, _ = read_json(ORIGIN + '/openapi.json')
            report = verify_http_without_provider(args.expected_sha, args.project, args.service,
                                                  args.environment, health, schema, headers)
            report.update(provider_evidence_sha256=digest, protected_binding_verified=args.require_protected_binding)
            print(json.dumps(report, sort_keys=True))
            return 0
        # Capture provider output privately; never log credentials or raw provider data.
        stage = 'provider_cli_read'
        result = subprocess.run(["railway", "status", "--project", args.project, "--environment", args.environment, "--json"],
                                check=True, capture_output=True, text=True, timeout=40)
        stage = 'provider_json_decode'
        provider = json.loads(result.stdout)
        stage = 'health_http_read'
        health, headers = read_json(ORIGIN + "/healthz")
        stage = 'schema_http_read'
        schema, _ = read_json(ORIGIN + "/openapi.json")
        stage = 'identity_health_schema_validation'
        report = verify(args.expected_sha, args.project, args.service, args.environment, health, provider, schema, headers)
        print(json.dumps(report, sort_keys=True))
    except Exception as exc:
        # Never log raw subprocess output, response bodies, URL exceptions or credentials.
        reason = str(exc) if isinstance(exc, VerificationError) else 'REMOTE_OR_RUNTIME_DETAIL_REDACTED'
        diagnostic = {'status': 'BACKEND_VERIFICATION_FAIL', 'stage': stage,
                      'reason': reason, 'exception_type': type(exc).__name__}
        if isinstance(exc, subprocess.CalledProcessError):
            diagnostic['provider_exit_code'] = exc.returncode
        if stage == 'provider_cli_read':
            category, basis = classify_provider_error(exc)
            diagnostic.update(provider_error_category=category, provider_error_basis=basis)
        print(json.dumps(diagnostic, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
