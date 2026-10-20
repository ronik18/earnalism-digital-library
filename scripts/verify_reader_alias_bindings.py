"""Read-only exact deployment/alias gate. No promotion, retries or application GETs."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess

PROJECT = "prj_kxPN55TOJ23lDgoXIXrvqHtzy607"
TEAM = "team_HAGNRSEiW5MZXY2AhV0cQvE0"
HOSTS = ("theearnalism.com", "www.theearnalism.com", "earnalism.vercel.app",
         "earnalism-sales-8498s-projects.vercel.app")

def require_assigned_aliases(deployment, aliases, expected_id, expected_project):
    hosts = {"theearnalism.com", "www.theearnalism.com", "earnalism.vercel.app",
             "earnalism-sales-8498s-projects.vercel.app"}
    if (deployment.get("id") != expected_id
            or deployment.get("projectId") != expected_project
            or deployment.get("readyState") != "READY"
            or deployment.get("target") != "production"
            or deployment.get("aliasAssigned") is not True
            or deployment.get("aliasError") is not None
            or set(aliases) != hosts):
        raise ValueError("Production alias assignment is not verified; no canaries")
    for host in hosts:
        row = aliases[host]
        if (row.get("alias") != host or row.get("projectId") != expected_project
                or row.get("deploymentId") != expected_id):
            raise ValueError("Exact production alias binding mismatch; no canaries")


def collect(metadata, runner=subprocess.run, environ=None, now=None):
    env = os.environ if environ is None else environ
    deployment_id = metadata.get("id")
    if (not isinstance(deployment_id, str)
            or not re.fullmatch(r"dpl_[A-Za-z0-9]+", deployment_id)
            or metadata.get("projectId") != PROJECT
            or env.get("VERCEL_PROJECT_ID") != PROJECT
            or env.get("VERCEL_ORG_ID") != TEAM):
        raise ValueError("Deployment/project/team identity rejected")
    for key, name in (("githubCommitSha", "FRONTEND_SHA"),
                      ("readerControllerSha", "CONTROLLER_SHA"),
                      ("readerBackendSha", "BACKEND_SHA")):
        expected = env.get(name, "")
        if not re.fullmatch(r"[0-9a-f]{40}", expected) or metadata.get("meta", {}).get(key) != expected:
            raise ValueError("Exact deployment source binding rejected")
    ready_ms = metadata.get("ready")
    if type(ready_ms) is not int:
        raise ValueError("Actual READY timestamp unavailable")
    ready = dt.datetime.fromtimestamp(ready_ms / 1000, dt.timezone.utc)
    instant = dt.datetime.now(dt.timezone.utc) if now is None else now
    if not 0 <= (instant - ready).total_seconds() < 900:
        raise ValueError("READY observation window expired")
    aliases = {}
    for host in HOSTS:
        result = runner(["vercel", "api", f"/v4/aliases/{host}?teamId={TEAM}",
                         "--method", "GET", "--raw"], check=True, capture_output=True,
                        text=True, timeout=15)
        aliases[host] = json.loads(result.stdout)
    require_assigned_aliases(metadata, aliases, deployment_id, PROJECT)
    if now is None and (dt.datetime.now(dt.timezone.utc) - ready).total_seconds() >= 900:
        raise ValueError("READY observation window expired")
    return {"status": "PASS", "deployment_id": deployment_id,
            "ready_at": ready.isoformat(), "project_id": PROJECT,
            "aliases": {host: {"projectId": aliases[host]["projectId"],
                                "deploymentId": aliases[host]["deploymentId"]}
                        for host in HOSTS},
            "scope": "Four read-only alias snapshots; not atomic/future binding guarantee"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()
    try:
        report = collect(json.loads(Path(args.metadata).read_text()))
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        with Path(args.github_output).open("a") as handle:
            handle.write("deployment_id=" + report["deployment_id"] + "\n")
            handle.write("ready_at=" + report["ready_at"] + "\n")
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception:
        # CLI/JSON errors may contain private provider details; never print them.
        Path(args.output).write_text(json.dumps({"status": "FAIL", "reason":
            "Exact deployment/alias binding unavailable or mismatched; no canaries"}) + "\n")
        print("READER_ALIAS_BINDING=FAIL; no canaries")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
