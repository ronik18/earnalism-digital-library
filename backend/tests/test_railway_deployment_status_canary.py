from __future__ import annotations

import importlib.util
import json
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "railway_deployment_status_canary",
    ROOT / "scripts" / "railway_deployment_status_canary.py",
)
canary = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(canary)

EVENT_GATE_SPEC = importlib.util.spec_from_file_location(
    "railway_deployment_event_gate",
    ROOT / "scripts" / "railway_deployment_event_gate.py",
)
event_gate = importlib.util.module_from_spec(EVENT_GATE_SPEC)
assert EVENT_GATE_SPEC and EVENT_GATE_SPEC.loader
EVENT_GATE_SPEC.loader.exec_module(event_gate)


def test_canary_rejects_non_read_only_http_methods():
    try:
        canary.request("https://api.theearnalism.com", "/healthz", method="POST")
    except ValueError as error:
        assert "GET and HEAD" in str(error)
    else:  # pragma: no cover - protects the production mutation boundary.
        raise AssertionError("non-read-only method was accepted")


def request_with_header_lines(monkeypatch, lines, status=200):
    message = Message()
    for name, value in lines:
        message[name] = value

    class Response(BytesIO):
        def __init__(self):
            super().__init__(b'{"version":"edition-42"}')
            self.status = status
            self.headers = message

    def fake_urlopen(req, *, timeout):
        assert req.get_method() == "GET"
        assert timeout == 15
        if status != 200:
            raise HTTPError(req.full_url, status, "Test HTTP response", message, BytesIO(b""))
        return Response()

    monkeypatch.setattr(canary, "urlopen", fake_urlopen)
    return canary.request("https://api.example.test", "/api/reader/book/dracula/manifest")


@pytest.mark.parametrize("mixed_case", [False, True])
@pytest.mark.parametrize("status", [200, 304])
def test_request_preserves_repeated_cache_and_vary_fields(monkeypatch, mixed_case, status):
    response = request_with_header_lines(monkeypatch, [
        ("Vary", "Authorization"),
        ("vArY" if mixed_case else "Vary", "Cookie"),
        ("vary" if mixed_case else "Vary", "accept-encoding"),
        ("Cache-Control", "private"),
        ("cache-control" if mixed_case else "Cache-Control", "no-store"),
    ], status=status)

    assert canary.header(response, "Vary") == "Authorization, Cookie, accept-encoding"
    assert canary.header(response, "Cache-Control") == "private, no-store"
    assert canary.manifest_cache_check("manifest", response)["passed"] is (status == 200)


@pytest.mark.parametrize("mixed_case", [False, True])
@pytest.mark.parametrize("public_first", [False, True])
@pytest.mark.parametrize("status", [200, 304])
def test_request_cannot_hide_public_directive_in_repeated_fields(monkeypatch, mixed_case, public_first, status):
    cache_fields = [
        ("Cache-Control", "public"),
        ("cache-control" if mixed_case else "Cache-Control", "private, no-store"),
    ]
    if not public_first:
        cache_fields.reverse()
    response = request_with_header_lines(monkeypatch, [("Vary", "Authorization, Cookie"), *cache_fields], status=status)

    assert "public" in canary.header(response, "Cache-Control").split(", ")
    assert canary.manifest_cache_check("manifest", response)["passed"] is False


def test_header_lookup_combines_differently_cased_fields():
    response = {"status": 200, "headers": {
        "Vary": "Authorization", "vary": "Cookie",
        "Cache-Control": "private, no-store", "cache-control": "public",
    }}
    assert canary.header(response, "Vary") == "Authorization, Cookie"
    assert canary.header(response, "Cache-Control") == "private, no-store, public"
    assert canary.manifest_cache_check("manifest", response)["passed"] is False


@pytest.fixture
def healthy_public_api(monkeypatch):
    fixture = canary.load_approved_audio_fixture(ROOT / "backend" / "fixtures" / "railway_approved_audio_fixture.json")
    calls = []

    def response(body, status=200, headers=None):
        return {"status": status, "headers": headers or {}, "body": json.dumps(body), "error": ""}

    manifest_body = {"version": "edition-42", "audio": {"enabled": False, "assets": {}}}
    manifest_headers = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie, Origin"}
    manifests = {
        "regular": response(manifest_body, headers=dict(manifest_headers)),
        "conditional": response(manifest_body, headers=dict(manifest_headers)),
    }
    responses = {
        "/healthz": response({"status": "ok"}, headers={"Cache-Control": "no-store"}),
        "/api/reading-pass/config": response({"public_text_pages": 3, "public_audio_seconds": 0}, headers={"Access-Control-Allow-Origin": canary.CANARY_ORIGIN}),
        "/api/books?q=dracula": response([{"slug": "dracula", "audio_enabled": False, "audiobook_enabled": False}]),
        f"/api/books/{fixture['slug']}": response({
            "slug": fixture["slug"], "reader_enabled": True, "audio_enabled": True, "audiobook_enabled": True,
            "audiobook_release_gate": fixture["public_contract"]["audiobook_release_gates"][0],
            "audio_qa_status": fixture["public_contract"]["audio_qa_status"],
        }),
        "/api/reader/book/dracula/audiobook": response({}, status=404),
        f"/api/reader/book/{fixture['slug']}/audiobook": response({}, status=401),
    }

    def fake_request(base_url, path, *, method="GET", headers=None):
        calls.append({"path": path, "method": method, "headers": headers or {}})
        if path == "/api/reader/book/dracula/manifest":
            return manifests["conditional" if headers and "If-None-Match" in headers else "regular"]
        return responses[path]

    monkeypatch.setattr(canary, "request", fake_request)
    return fixture, manifests, calls


def test_live_canary_probes_exact_historical_etag_without_mutations(healthy_public_api):
    fixture, _manifests, calls = healthy_public_api
    report = canary.run("https://api.example.test", fixture)

    assert report["status"] == "PASS"
    assert report["manifest_conditional_etag"] == 'W/"reader-manifest-edition-42"'
    manifest_calls = [call for call in calls if call["path"].endswith("/manifest")]
    assert [call["headers"] for call in manifest_calls] == [{}, {"If-None-Match": 'W/"reader-manifest-edition-42"'}]
    assert all(call["method"] == "GET" for call in calls)
    assert report["production_mutation_performed"] is False
    assert report["india_reader_remote_smoke"] == "NOT_AVAILABLE_IN_CURRENT_RUNNER"


@pytest.mark.parametrize("phase", ["regular", "conditional"])
@pytest.mark.parametrize("unsafe_headers", [
    {"Cache-Control": "public, max-age=60, stale-while-revalidate=300"},
    {"Cache-Control": "private, max-age=20"},
    {"Cache-Control": "no-store"},
    {"Cache-Control": "private, no-store, public"},
    {"Vary": "Origin, Cookie"},
    {"Vary": "Authorization"},
    {"ETag": 'W/"reader-manifest-edition-42"'},
])
def test_live_canary_rejects_unsafe_manifest_caching(healthy_public_api, phase, unsafe_headers):
    fixture, manifests, _calls = healthy_public_api
    manifests[phase]["headers"].update(unsafe_headers)
    report = canary.run("https://api.example.test", fixture)

    assert report["status"] == "FAIL"
    check_name = "manifest_private_no_store" if phase == "regular" else "manifest_conditional_private_no_store"
    assert next(item for item in report["checks"] if item["name"] == check_name)["passed"] is False


def test_live_canary_rejects_not_modified_even_with_safe_headers(healthy_public_api):
    fixture, manifests, _calls = healthy_public_api
    manifests["conditional"]["status"] = 304
    manifests["conditional"]["body"] = ""
    report = canary.run("https://api.example.test", fixture)

    assert report["status"] == "FAIL"
    assert next(item for item in report["checks"] if item["name"] == "manifest_conditional_private_no_store")["passed"] is False


def test_live_canary_cannot_pass_without_version_for_conditional_probe(healthy_public_api):
    fixture, manifests, calls = healthy_public_api
    manifests["regular"]["body"] = json.dumps({"audio": {"enabled": False, "assets": {}}})
    report = canary.run("https://api.example.test", fixture)

    assert report["status"] == "FAIL"
    assert report["manifest_conditional_etag"] == ""
    assert len([call for call in calls if call["path"].endswith("/manifest")]) == 1


def test_untrusted_non_india_runner_denials_are_expected_not_reader_smoke_failures(healthy_public_api, monkeypatch):
    fixture, manifests, _calls = healthy_public_api
    denied = {"status": 451, "headers": {}, "body": json.dumps({"detail": {"code": "RELEASE_PROXY_SCOPE_INVALID"}}), "error": ""}
    manifests["regular"].update(denied)
    responses = {
        "/api/books?q=dracula": dict(denied),
        f"/api/books/{fixture['slug']}": dict(denied),
        "/api/reader/book/dracula/audiobook": dict(denied),
        f"/api/reader/book/{fixture['slug']}/audiobook": dict(denied),
    }
    original_request = canary.request

    def fake_request(base_url, path, *, method="GET", headers=None):
        if path == "/api/reader/book/dracula/manifest":
            return dict(denied)
        if path in responses:
            return dict(responses[path])
        return original_request(base_url, path, method=method, headers=headers)

    # Avoid a network fallback for known protected production routes.
    monkeypatch.setattr(canary, "request", fake_request)
    report = canary.run("https://api.example.test", fixture)

    assert report["status"] == "PASS"
    assert report["territory_denial_test"] == "NOT_AVAILABLE_IN_CURRENT_RUNNER"
    assert report["untrusted_reader_request_test"] == "PASS"
    assert report["india_reader_remote_smoke"] == "NOT_AVAILABLE_IN_CURRENT_RUNNER"
    assert next(item for item in report["checks"] if item["name"] == "untrusted_reader_requests_denied")["passed"] is True


def test_workflow_checks_out_exact_event_sha_and_accepts_empty_ref_when_main_reachable():
    workflow = (ROOT / ".github" / "workflows" / "railway-deployment-canary.yml").read_text(encoding="utf-8")
    assert "deployment_status:" in workflow
    assert "github.event.deployment_status.state == 'success'" in workflow
    assert "ref: ${{ github.event.deployment.sha }}" in workflow
    assert 'test "${checked_out_sha}" = "${DEPLOYMENT_SHA}"' in workflow
    assert 'git merge-base --is-ancestor "${DEPLOYMENT_SHA}" origin/main' in workflow
    assert "github.event.deployment.ref == 'main'" not in workflow
    event_gate_script = (ROOT / "scripts" / "railway_deployment_event_gate.py").read_text(encoding="utf-8")
    assert "PROVIDER_UNCONFIRMED" in event_gate_script
    assert "railway up" not in workflow.lower()


def test_regression_workflow_has_no_railway_cli_or_token_dependency():
    workflow = (ROOT / ".github" / "workflows" / "regression.yml").read_text(encoding="utf-8")
    assert "railway up" not in workflow.lower()
    assert "RAILWAY_TOKEN" not in workflow
    assert "RAILWAY_SERVICE_ID" not in workflow
    assert "deploy_frontend:" in workflow
    assert "frontend_production_canary:" in workflow
    assert "needs.deploy_frontend.outputs.deployed == 'true'" in workflow
    assert "scripts/post_deploy_route_canary.py" in workflow
    assert "scripts/post_deploy_static_seo_canary.py" in workflow
    assert "regression/scripts/post-deploy-canary.js" in workflow
    assert "railway-deployment-canary" not in workflow


def test_repository_config_keeps_docker_context_and_port_contract_aligned():
    railway_config = (ROOT / "backend" / "railway.json").read_text(encoding="utf-8")
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    start_script = (ROOT / "backend" / "start_prod.sh").read_text(encoding="utf-8")

    assert '"builder": "DOCKERFILE"' in railway_config
    assert "buildCommand" not in railway_config
    assert '"/backend/**"' in railway_config
    assert "COPY requirements-runtime.txt ." in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "os.environ.get('PORT', '8080')" in dockerfile
    assert "USER app" in dockerfile
    assert '--host 0.0.0.0' in start_script
    assert '--port "${PORT:-8080}"' in start_script


def _event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "deployment_id": "101",
        "deployment_sha": "a" * 40,
        "deployment_ref": "main",
        "environment": "production",
        "state": "success",
        "status_id": "202",
        "target_url": "https://railway.example/deployment/101",
        "log_url": "https://railway.example/deployment/101/logs",
        "environment_url": "https://api.theearnalism.com",
        "sender": "railway-app",
        "creator": "railway-app",
        "task": "deploy",
        "description": "Railway deployment completed",
        "checked_out_sha": "a" * 40,
        "reachable_from_main": True,
    }
    event.update(overrides)
    return event


def test_railway_branch_ref_event_is_confirmed_with_a_reviewed_marker():
    result = event_gate.evaluate_event(_event(), railway_provider_marker="railway")
    assert result["provider_classification"] == event_gate.RAILWAY_CONFIRMED
    assert result["run_backend_canary"] is True
    assert result["railway_deployment_proof"] is True


def test_verified_native_railway_event_marker_and_scoped_production_environment_are_confirmed():
    result = event_gate.evaluate_event(
        _event(
            environment="earnalism / production",
            sender="railway-app[bot]",
            creator="railway-app[bot]",
            target_url="https://railway.com/project/example",
            log_url="https://railway.com/project/example",
        )
    )
    assert result["provider_classification"] == event_gate.RAILWAY_CONFIRMED
    assert result["event_eligibility"] == "ELIGIBLE"
    assert result["run_backend_canary"] is True
    assert result["railway_deployment_proof"] is True


def test_railway_sha_event_with_empty_ref_is_accepted():
    result = event_gate.evaluate_event(_event(deployment_ref=""), railway_provider_marker="railway")
    assert result["provider_classification"] == event_gate.RAILWAY_CONFIRMED
    assert result["event_eligibility"] == "ELIGIBLE"
    assert result["run_backend_canary"] is True


def test_non_railway_production_deployment_is_an_explicit_skip():
    result = event_gate.evaluate_event(
        _event(
            sender="vercel[bot]",
            creator="vercel[bot]",
            target_url="https://earnalism.vercel.app",
            log_url="https://earnalism.vercel.app",
        )
    )
    assert result["provider_classification"] == event_gate.NON_RAILWAY_DEPLOYMENT
    assert result["run_backend_canary"] is False
    assert result["railway_deployment_proof"] is False


def test_deployment_sha_not_reachable_from_main_is_rejected():
    result = event_gate.evaluate_event(_event(reachable_from_main=False), railway_provider_marker="railway")
    assert result["provider_classification"] == event_gate.RAILWAY_CONFIRMED
    assert result["event_eligibility"] == "INELIGIBLE"
    assert result["run_backend_canary"] is False


def test_approved_audio_fixture_is_derived_from_checked_in_release_truth():
    fixture = json.loads((ROOT / "backend" / "fixtures" / "railway_approved_audio_fixture.json").read_text(encoding="utf-8"))
    curated = json.loads((ROOT / "frontend" / "src" / "data" / "homeCuratedSprint1.json").read_text(encoding="utf-8"))
    approved = next(book for book in curated["shelves"]["approved_audiobooks"] if book["slug"] == fixture["slug"])

    assert approved["reader_enabled"] is True
    assert approved["audiobook_enabled"] is True
    assert approved["audiobook_release_gate"] == fixture["repository_contract"]["audiobook_release_gate"]
    assert approved["audio_qa_status"] == fixture["repository_contract"]["audio_qa_status"]
    assert approved["reader_url"] == f"/reader/{fixture['slug']}"
    assert fixture["public_contract"]["raw_audio_url"] == "absent"
    assert set(fixture["public_contract"]["anonymous_range_statuses"]) == {401, 403}


def test_container_contract_workflow_rebuilds_backend_root_context():
    workflow = (ROOT / ".github" / "workflows" / "backend-container-contract.yml").read_text(encoding="utf-8")
    assert "docker build --file backend/Dockerfile --tag earnalism-backend-ci backend" in workflow
    assert "test \"$(docker image inspect --format '{{.Config.User}}' earnalism-backend-ci)\" = \"app\"" in workflow
    assert "--env PORT=8080" in workflow
    assert "http://127.0.0.1:18080/healthz" in workflow
    assert "earnalism-container-rs0" in workflow
