"""Exact alias gate with explicitly admitted one-shot production promotion; no retries."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time

PROJECT = "prj_kxPN55TOJ23lDgoXIXrvqHtzy607"
TEAM = "team_HAGNRSEiW5MZXY2AhV0cQvE0"
HOSTS = ("theearnalism.com", "www.theearnalism.com", "earnalism.vercel.app",
         "earnalism-sales-8498s-projects.vercel.app")
ROLLBACK = "dpl_6hzaPakeBuma2y4JB6CGyngzCKJf"


def conditional_promotion(metadata, runner=subprocess.run, environ=None,
                          clock=time.monotonic, now=None):
    """One production-only command; uncertain outcomes allow bounded GETs only.

    No runtime receipt is created here. The manual dispatch and protected environment
    provide the separately required production consent. Persist intent before sending.
    """
    env = os.environ if environ is None else environ
    expected_id = metadata.get("id")
    instant = dt.datetime.now(dt.timezone.utc) if now is None else now
    ready_ms = metadata.get("ready")
    if (not isinstance(expected_id, str) or not re.fullmatch(r"dpl_[A-Za-z0-9]+", expected_id)
            or expected_id == ROLLBACK or metadata.get("projectId") != PROJECT
            or metadata.get("ownerId") != TEAM or metadata.get("target") != "production"
            or metadata.get("readyState") != "READY" or type(ready_ms) is not int
            or metadata.get("aliasError") is not None
            or env.get("VERCEL_PROJECT_ID") != PROJECT or env.get("VERCEL_ORG_ID") != TEAM):
        raise ValueError("Production deployment/project/team binding rejected")
    for key, name in (("githubCommitSha", "FRONTEND_SHA"),
                      ("readerControllerSha", "CONTROLLER_SHA"),
                      ("readerBackendSha", "BACKEND_SHA")):
        expected = env.get(name, "")
        if not re.fullmatch(r"[0-9a-f]{40}", expected) or metadata.get("meta", {}).get(key) != expected:
            raise ValueError("Exact production source binding rejected")
    age = instant.timestamp() - ready_ms / 1000
    if not 0 <= age < 900:
        raise ValueError("Original READY deadline expired")
    started = clock()
    ready_deadline = started + 900 - age
    gets = 0
    resolution_deadline = None

    def get(path):
        nonlocal gets
        deadline = ready_deadline if resolution_deadline is None else min(ready_deadline, resolution_deadline)
        remaining = deadline - clock()
        if gets >= 30 or remaining <= 0:
            raise ValueError("Read-only resolution cap exhausted; operator resolution required")
        gets += 1
        result = runner(["vercel", "api", path + ("&" if "?" in path else "?") + "teamId=" + TEAM,
                         "--method", "GET", "--raw"], check=True, capture_output=True,
                        text=True, timeout=min(5, remaining))
        if clock() >= deadline:
            raise ValueError("Read-only resolution deadline exceeded")
        return json.loads(result.stdout)

    def aliases():
        rows = {host: get("/v4/aliases/" + host) for host in HOSTS}
        ids = set()
        for host, row in rows.items():
            if row.get("alias") != host or row.get("projectId") != PROJECT:
                raise ValueError("Foreign or malformed production alias")
            ids.add(row.get("deploymentId"))
        return rows, ids

    def project():
        row = get("/v9/projects/" + PROJECT)
        if row.get("id") != PROJECT or row.get("accountId") != TEAM or row.get("rollingRelease"):
            raise ValueError("Project identity or rolling release rejected")
        return row

    p = project()
    active = p.get("lastAliasRequest") or {}
    if active.get("jobStatus") in ("pending", "in-progress"):
        raise ValueError("Competing alias operation; no promotion")
    inventory = get("/v9/projects/" + PROJECT + "/domains?production=true&limit=10")
    domains = inventory.get("domains")
    public_hosts = set(HOSTS) - {HOSTS[-1]}
    if (not isinstance(domains, list) or len(domains) != 3
            or {d.get("name") for d in domains} != public_hosts
            or inventory.get("pagination", {}).get("next") is not None
            or any(d.get("projectId") != PROJECT or d.get("verified") is not True
                   or d.get("gitBranch") is not None or d.get("customEnvironmentId") is not None
                   or d.get("redirect") is not None for d in domains)):
        raise ValueError("Exact production domain inventory rejected")
    rows, ids = aliases()
    if ids == {expected_id}:
        require_assigned_aliases(metadata, rows, expected_id, PROJECT)
        return {"status": "SKIPPED_ALREADY_ASSIGNED", "gets": gets}
    if ids != {ROLLBACK}:
        raise ValueError("Mixed, foreign or unknown aliases; no promotion")
    current = p.get("targets", {}).get("production", {})
    if (current.get("id") != ROLLBACK or set(current.get("alias", [])) != set(HOSTS)
            or current.get("readyState") != "READY" or current.get("target") != "production"
            or current.get("aliasError") is not None
            or p.get("autoAssignCustomDomains") is not False
            or env.get("CONDITIONAL_PROMOTION") != "true"
            or ready_deadline - clock() < 600):
        raise ValueError("Conditional promotion admission rejected")
    concurrent = get("/v6/deployments?projectId=" + PROJECT +
                     "&target=production&state=BUILDING,INITIALIZING,QUEUED&limit=10")
    if concurrent.get("deployments") != [] or concurrent.get("pagination", {}).get("next"):
        raise ValueError("Concurrent production deployment; no promotion")
    # Re-read the target immediately before the one mutation; never promote Preview.
    fresh = get("/v13/deployments/" + expected_id)
    if fresh.get("aliasError") is not None:
        raise ValueError("Deployment alias error before promotion")
    for key in ("id", "projectId", "ownerId", "target", "readyState", "ready", "meta"):
        if fresh.get(key) != metadata.get(key):
            raise ValueError("Deployment changed before promotion")
    if ready_deadline - clock() < 600:
        raise ValueError("Insufficient original READY window immediately before promotion")
    intent = Path(env["RUNNER_TEMP"]) / "reader-promotion-intent.json"
    with intent.open("x") as handle:
        json.dump({"state": "SINGLE_ATTEMPT_STARTED_NO_RETRY", "deployment_id": expected_id,
                   "controller_sha": env["CONTROLLER_SHA"], "original_ready": ready_ms}, handle)
    # CLI timeout is not server cancellation. No second command, even on timeout/error.
    command_state = "UNKNOWN"
    try:
        # Zero CLI polling: our own bounded resolver owns every subsequent status GET.
        # The pinned CLI supports timeout=0 as request-only, not cancellation/retry.
        result = runner(["vercel", "promote", expected_id, "--scope", TEAM, "--timeout", "0"],
                        check=False, capture_output=True, text=True, timeout=65,
                        input="n\n")
        command_state = "QUEUED" if "queued" in (result.stdout + result.stderr).lower() else "RETURNED"
    except (subprocess.SubprocessError, OSError):
        pass
    resolution_deadline = clock() + 60
    gets = 0  # All subsequent GETs, including final alias guard, share this cap.
    while True:
        p = project()
        request = p.get("lastAliasRequest") or {}
        status = request.get("jobStatus")
        if request.get("toDeploymentId") != expected_id or request.get("type") != "promote":
            raise ValueError("NEEDS_OPERATOR_RESOLUTION: promotion identity unavailable")
        if status in ("pending", "in-progress"):
            if clock() >= resolution_deadline or gets >= 24:
                raise ValueError("NEEDS_OPERATOR_RESOLUTION: pending; no competing mutation")
            continue
        fresh = get("/v13/deployments/" + expected_id)
        for key in ("id", "projectId", "ownerId", "target", "readyState", "ready", "meta"):
            if fresh.get(key) != metadata.get(key):
                raise ValueError("NEEDS_OPERATOR_RESOLUTION: post-promotion identity mismatch")
        rows, ids = aliases()
        if status == "succeeded" and command_state != "QUEUED":
            require_assigned_aliases(fresh, rows, expected_id, PROJECT)
            if p.get("targets", {}).get("production", {}).get("id") != expected_id:
                raise ValueError("NEEDS_OPERATOR_RESOLUTION: production target mismatch")
            metadata.update(fresh)
            # Feed the existing final read-only guard from this bounded snapshot.
            return {"status": "PROMOTED", "resolution_gets": gets, "aliases": rows,
                    "command_state": command_state}
        if status in ("failed", "skipped") and ids == {ROLLBACK}:
            raise ValueError("PROMOTION_FAILED_OLD_SERVING; leave retained PR528 unchanged")
        raise ValueError("NEEDS_OPERATOR_RESOLUTION: terminal partial/queued/unknown; conditional PR528 recovery")

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


def collect(metadata, runner=subprocess.run, environ=None, now=None, alias_snapshot=None):
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
    aliases = alias_snapshot
    if aliases is None:
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
    parser.add_argument("--conditional-promotion", action="store_true")
    args = parser.parse_args()
    try:
        metadata = json.loads(Path(args.metadata).read_text())
        promotion = conditional_promotion(metadata) if args.conditional_promotion else None
        report = collect(metadata, alias_snapshot=promotion.get("aliases") if promotion else None)
        if promotion:
            report["promotion"] = {k: v for k, v in promotion.items() if k != "aliases"}
            Path(args.metadata).write_text(json.dumps(metadata) + "\n")
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        with Path(args.github_output).open("a") as handle:
            handle.write("deployment_id=" + report["deployment_id"] + "\n")
            handle.write("ready_at=" + report["ready_at"] + "\n")
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as error:
        # CLI/JSON errors may contain private provider details; never print them.
        reason = "Exact deployment/alias binding unavailable or mismatched; no canaries"
        if isinstance(error, ValueError) and str(error).startswith(("NEEDS_OPERATOR_RESOLUTION:", "PROMOTION_FAILED_OLD_SERVING;")):
            reason = str(error)  # Static recovery dispositions only, never provider output.
        Path(args.output).write_text(json.dumps({"status": "FAIL", "reason": reason,
            "promotion_intent_preserved": (Path(os.environ.get("RUNNER_TEMP", "/tmp")) /
                                            "reader-promotion-intent.json").exists()}) + "\n")
        print("READER_ALIAS_BINDING=FAIL; no canaries")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
