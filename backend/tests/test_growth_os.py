import importlib
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def test_growth_guardrail_blocks_public_production_when_execution_disabled(monkeypatch):
    server = _server(monkeypatch)
    action = {
        "agent": "outreach",
        "tool": "schedule_email",
        "title": "Send reader message",
        "payload": {"message": "Welcome to Earnalism"},
    }

    result = server._growth_guardrail_decision(action, "production")

    assert result["decision"] == "block"
    assert any("Production execution is disabled" in reason for reason in result["reasons"])


def test_growth_guardrail_keeps_customer_actions_draft_only_in_dry_run(monkeypatch):
    server = _server(monkeypatch)
    action = {
        "agent": "customer_success",
        "tool": "send_reading_reminder",
        "title": "Reminder draft",
        "payload": {"message": "Your reading room is ready"},
    }

    result = server._growth_guardrail_decision(action, "dry_run")

    assert result["decision"] == "revise"
    assert any("draft-only" in reason for reason in result["reasons"])


def test_growth_guardrail_blocks_hallucinated_partnership_claims(monkeypatch):
    server = _server(monkeypatch)
    action = {
        "agent": "institution_sales",
        "tool": "send_institution_outreach",
        "title": "Unsafe claim",
        "payload": {"copy": "We are your official partner with a guaranteed refund."},
    }

    result = server._growth_guardrail_decision(action, "dry_run")

    assert result["decision"] == "block"
    assert any("claim" in reason.lower() for reason in result["reasons"])


def test_growth_action_templates_can_target_selected_agents(monkeypatch):
    server = _server(monkeypatch)

    templates = server._growth_action_templates(["seo", "finance_guard"])

    assert {item["agent"] for item in templates} == {"seo", "finance_guard"}
    assert all(item["tool"] in server.GROWTH_TOOL_DEFINITIONS for item in templates)
