from __future__ import annotations

import importlib.util
import json
from pathlib import Path


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
