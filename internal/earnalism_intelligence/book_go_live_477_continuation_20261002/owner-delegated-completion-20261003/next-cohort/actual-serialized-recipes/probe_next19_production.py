#!/usr/bin/env python3
"""Root-authorized, once-per-route public GET readback; no session mutation."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

SLUGS = [
    "dsires-baby", "sredni-vashtar", "the-cop-and-the-anthem", "the-open-window",
    "the-selfish-giant", "the-science-of-getting-rich", "bn-066", "lokrahasya",
    "mrinalini", "frankenstein", "pride-and-prejudice", "the-great-gatsby",
    "the-secret-garden", "the-time-machine", "acres-of-diamonds", "my-life-and-work",
    "the-principles-of-scientific-management", "the-wonderful-wizard-of-oz", "book-5704b31005",
]
FRONTEND = "https://theearnalism.com"

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_canary(root):
    source = root / "scripts/post_deploy_static_seo_canary.py"
    spec = importlib.util.spec_from_file_location("native_static_seo_canary", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def prepare_checks(root, module):
    checks = []
    for slug in SLUGS:
        folder = root / "data/controlled_publications" / slug
        public = read(folder / "public_book.json")
        reader = read(folder / "reader_manifest.json")
        decision = read(folder / "rights_decision.json")
        publication = read(folder / "publication_manifest.json")
        assert decision["decision_id"] == f"india-20261003-{slug}-exact-reader-cover-prospective-accepted"
        assert decision["territories"] == ["IN"]
        assert publication["reader_release"]["exposed"] is True
        assert publication["audio_release"]["exposed"] is False
        title = public["title"]
        for kind, robots in (("book", "index,follow"), ("reader", "noindex,follow"), ("listener", "noindex,follow")):
            checks.append({"slug": slug, "route": f"/{kind}/{slug}", "type": "html",
                "policy": {"kind": "disabled_listener" if kind == "listener" else kind,
                    "title": title, "canonical": f"/book/{slug}", "robots": robots, "audio_disabled": True}})
        chapters = reader["chapters"]
        for route, canonical in ((f"/api/reader/book/{slug}/manifest", False),
                                 (f"/api/reading-pass/books/{slug}/manifest", True)):
            policy = {"expected_status": 200, "expected_code": "", "expected_slug": slug}
            if canonical:
                policy.update(kind="canonical_manifest", expected_chapters=len(chapters),
                    expected_chapter_ids=[chapter["id"] for chapter in chapters])
            # Reuse the existing exact denial validator, which intentionally
            # accepts overseas denial only for registered route/policy pairs.
            module.PROTECTED_API_CHECKS[route] = policy
            checks.append({"slug": slug, "route": route, "type": "api", "policy": policy})
    assert len(checks) == 95
    return checks

def verify_gate(root, args):
    gate = read(args.canary_gate)
    frontend = read(args.frontend_report)
    backend = read(args.backend_report)
    current = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    merged = args.merged_main_sha
    if not re.fullmatch(r"[0-9a-f]{40}", merged):
        raise ValueError("An exact merged main SHA is required")
    assert current == merged, "Local source is not the exact merged main being observed"
    origin_main = subprocess.check_output(["git", "-C", str(root), "rev-parse", "origin/main"], text=True).strip()
    assert origin_main == merged, "Reconcile origin/main before observing this exact release"
    assert gate["merged_main_sha"] == merged
    assert gate["frontend_run_head_sha"] == merged
    assert gate["frontend_deployment_job_conclusion"] == "success"
    assert gate["frontend_canary_job_conclusion"] == "success"
    assert gate["backend_canary_job_conclusion"] == "success"
    assert isinstance(gate["frontend_run_url"], str) and gate["frontend_run_url"].startswith("https://github.com/ronik18/earnalism-digital-library/actions/runs/")
    assert isinstance(gate["backend_run_url"], str) and gate["backend_run_url"].startswith("https://github.com/ronik18/earnalism-digital-library/actions/runs/")
    assert frontend["result"] == "PASS"
    assert backend["status"] == "PASS" and backend["deployment_sha"] == merged
    assert gate["frontend_report_sha256"] == digest(args.frontend_report)
    assert gate["backend_report_sha256"] == digest(args.backend_report)
    assert gate["root_authorized_public_get_readback"] is True
    assert not backend.get("production_mutation_performed", False)
    return gate

def probe(check, module, timeout):
    route, policy = check["route"], check["policy"]
    if check["type"] == "html":
        status, headers, body, response_url = module.fetch_raw_html(FRONTEND, route, timeout)
        result = module.inspect_route(route, policy, status, headers, body, response_url)
        if module.urlsplit(response_url).path.rstrip("/") != route:
            result["failures"].append("unexpected route redirect")
        result.update(body=body, body_sha256=hashlib.sha256(body.encode()).hexdigest(), observed_canonical_version=None)
    else:
        status, headers, body, response_url = module.fetch_raw_html(FRONTEND, route, timeout)
        try:
            payload = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            payload = None
        result = module.inspect_protected_api(route, policy, status, payload, response_url)
        # This controller must record the actual US edge denial, never claim
        # an unobserved India version or a started Reading Pass session.
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if not (status == 451 and isinstance(detail, dict)
                and detail.get("code") == "RELEASE_TERRITORY_DENIED"
                and detail.get("country") == "US" and detail.get("allowed_countries") == ["IN"]):
            result["failures"].append("expected exact observed US451 India-only edge denial")
        result["detail"] = detail
        result["observed_reading_session"] = None
        result["body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        # Retain the exact public territorial denial only; an unexpected
        # response is assessed and hashed without persisting its body.
        if status == 451:
            result["body"] = body
    result["headers"] = {name: value for name, value in headers.items()
        if name.lower() in {"cache-control", "content-type", "x-vercel-cache", "x-vercel-id", "x-request-id"}}
    result["slug"] = check["slug"]
    result["result"] = "PASS" if not result["failures"] else "FAIL"
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--merged-main-sha", required=True)
    parser.add_argument("--canary-gate", type=Path, required=True)
    parser.add_argument("--frontend-report", type=Path, required=True)
    parser.add_argument("--backend-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=4)
    parser.add_argument("--authorized-production-get-readback", action="store_true", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; reconcile it rather than duplicate these probes")
    verify_gate(args.repo, args)
    module = load_canary(args.repo)
    checks = prepare_checks(args.repo, module)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(lambda check: probe(check, module, args.timeout), checks))
    failures = [row for row in rows if row["result"] != "PASS"]
    receipt = {"schema": "earnalism.next19.actual-public-get-readback.v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "merged_main": args.merged_main_sha,
        "production_mutation_performed": False, "requests": len(rows), "method": "GET_ONLY_ONCE_PER_ROUTE",
        "new_titles": SLUGS, "frontend_semantic_routes": 57, "protected_manifest_routes": 38,
        "observed_canonical_versions": {slug: next(row.get("observed_canonical_version")
            for row in rows if row["route"] == f"/api/reading-pass/books/{slug}/manifest") for slug in SLUGS},
        "observed_reading_sessions": {slug: None for slug in SLUGS},
        "india_backend_contract": "NOT_RUN_FROM_NON_IN" if all(row["status_code"] == 451
            for row in rows if row["route"].startswith("/api/")) else "UNEXPECTED_RESPONSE_REQUIRES_REVIEW",
        "reading_session_contract": "NO_SESSION_REQUEST_PERFORMED",
        "conditional_manual_production_observation_waiver": "NOT_GRANTED_BY_THIS_SCRIPT",
        "canary_gate_sha256": digest(args.canary_gate), "native_inspector_sha256": digest(args.repo / "scripts/post_deploy_static_seo_canary.py"),
        "result": "PASS" if not failures else "FAIL", "failure_count": len(failures), "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": receipt["result"], "requests": len(rows), "failure_count": len(failures), "output": str(args.output)}))
    return int(bool(failures))

if __name__ == "__main__":
    sys.exit(main())
