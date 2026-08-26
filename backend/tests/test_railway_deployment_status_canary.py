from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "railway_deployment_status_canary",
    ROOT / "scripts" / "railway_deployment_status_canary.py",
)
canary = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(canary)


def test_canary_rejects_non_read_only_http_methods():
    try:
        canary.request("https://api.theearnalism.com", "/healthz", method="POST")
    except ValueError as error:
        assert "GET and HEAD" in str(error)
    else:  # pragma: no cover - protects the production mutation boundary.
        raise AssertionError("non-read-only method was accepted")


def test_workflow_filters_to_successful_production_main_deployments():
    workflow = (ROOT / ".github" / "workflows" / "railway-deployment-canary.yml").read_text(encoding="utf-8")
    assert "deployment_status:" in workflow
    assert "github.event.deployment.environment == 'production'" in workflow
    assert "github.event.deployment_status.state == 'success'" in workflow
    assert "github.event.deployment.ref == 'main'" in workflow
    assert "railway up" not in workflow.lower()


def test_regression_workflow_has_no_railway_cli_or_token_dependency():
    workflow = (ROOT / ".github" / "workflows" / "regression.yml").read_text(encoding="utf-8")
    assert "railway up" not in workflow.lower()
    assert "RAILWAY_TOKEN" not in workflow
    assert "RAILWAY_SERVICE_ID" not in workflow
    assert "deploy_frontend:" in workflow


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
