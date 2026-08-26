from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_backend_requirement_authorities_use_the_verified_click_release():
    for relative_path in ("backend/requirements.txt", "backend/requirements-runtime.txt"):
        lines = (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
        assert "click==8.3.3" in lines
        assert "click==8.3.2" not in lines


def test_integrity_gate_is_bounded_and_uses_public_metadata_without_credentials():
    source = (ROOT / "scripts/verify_click_dependency_integrity.py").read_text(encoding="utf-8")
    assert "TIMEOUT_SECONDS = 10" in source
    assert "https://pypi.org/pypi/click/" in source
    assert "PUBLIC_PYPI_NETWORK_ERROR" in source
    assert "EXPECTED_CLICK_PIN = \"8.3.3\"" in source
    assert "REJECTED_CLICK_PINS = {\"8.3.2\"}" in source
    assert "MISSING_VERSION" in source


def test_uat_launcher_uses_python_311_and_exports_its_loopback_hosts():
    source = (ROOT / "scripts/start_local_uat.sh").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run_local_uat.sh").read_text(encoding="utf-8")
    assert 'command -v python3.11' in source
    assert 'export UAT_FRONTEND_HOST=%q' in source
    assert 'export UAT_BACKEND_HOST=%q' in source
    assert 'rm -f uat/runtime/system-uat/environment.sh' in runner
