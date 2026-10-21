"""Exact alias gate with explicitly admitted one-shot production promotion; no retries."""
import argparse
import hashlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
try:
    from scripts.reader_alias_canaries import wall_deadline
except ModuleNotFoundError:
    from reader_alias_canaries import wall_deadline

PROJECT = "prj_kxPN55TOJ23lDgoXIXrvqHtzy607"
TEAM = "team_HAGNRSEiW5MZXY2AhV0cQvE0"
HOSTS = ("theearnalism.com", "www.theearnalism.com", "earnalism.vercel.app",
         "earnalism-sales-8498s-projects.vercel.app")
PUBLIC_HOSTS = HOSTS[:-1]
PROTECTED_HOST = HOSTS[-1]
ROLLBACK = "dpl_6hzaPakeBuma2y4JB6CGyngzCKJf"
RETAINED_READY = "dpl_5nrp6vYYMZurfhVde1Jbu3aofsfB"
CREATION_CONTROLLER = "2dad58e388918c9ea74d75935ef5d3753d93f4f3"
CALLER_FRONTEND = "b3998d72f2e93bd99ffb1563c906c77e78aa5b49"
CALLER_BACKEND = "0f2bb1e728890f1f0e41ded9b12f07c76246bce0"


def release_rollback(environ=None):
    env = os.environ if environ is None else environ
    return RETAINED_READY if (env.get("FRONTEND_SHA") == CALLER_FRONTEND
        and env.get("BACKEND_SHA") == CALLER_BACKEND) else ROLLBACK


class NoProviderRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def provider_request(path, method, timeout, env):
    """One native request, no redirects/retries, no credential or response logging."""
    token = env.get("VERCEL_TOKEN")
    rollback = release_rollback(env)
    if method not in ("GET", "POST") or (method == "POST" and not re.fullmatch(
            (r"/v10/projects/" + PROJECT + r"/promote/dpl_[A-Za-z0-9]+|/v9/projects/"
             + PROJECT + r"/rollback/" + rollback), path)):
        raise ValueError("Provider mutation route rejected")
    if not token or not path.startswith(("/v4/aliases/", "/v9/projects/", "/v13/deployments/", "/v6/deployments?", "/v10/projects/")):
        raise ValueError("Scoped provider request unavailable")
    url = "https://api.vercel.com" + path + ("&" if "?" in path else "?") + "teamId=" + TEAM
    req = Request(url, data=b"{}" if method == "POST" else None, method=method,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with wall_deadline(timeout):
        try:
            response = build_opener(NoProviderRedirect()).open(req, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            if method == "POST":
                # Never read an error body or follow provider redirects.
                return "QUEUED" if response.code == 202 else "RETURNED"
            if response.code != 200:
                raise ValueError("Scoped provider read rejected")
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("Oversized provider metadata rejected")
            return json.loads(raw)


def readonly_access_check(environ=None, request=provider_request):
    """Six fixed GETs only; no promotion, rollback, build or authentication bypass."""
    env = os.environ if environ is None else environ
    if (env.get('GITHUB_REPOSITORY') != 'ronik18/earnalism-digital-library'
            or env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or env.get('CONFIRM_PRODUCTION') not in ('READ_ONLY_VERCEL_ACCESS', 'DEPLOY_PRODUCTION')
            or env.get('VERCEL_PROJECT_ID') != PROJECT or env.get('VERCEL_ORG_ID') != TEAM):
        raise ValueError('Read-only execution context mismatch')
    deadline = time.monotonic() + 30
    def get(path):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('Read-only preflight deadline exhausted')
        result = request(path, 'GET', min(5, remaining), env)
        if time.monotonic() >= deadline:
            raise ValueError('Read-only preflight deadline exceeded')
        return result
    with wall_deadline(30):
        project = get('/v9/projects/' + PROJECT)
        if (project.get('id') != PROJECT or project.get('accountId') != TEAM
                or project.get('rollingRelease')
                or (project.get('lastAliasRequest') or {}).get('jobStatus') in ('pending','in-progress')
                or project.get('targets', {}).get('production', {}).get('id') != RETAINED_READY):
            raise ValueError('Current exact project/production target unverified')
        target = get('/v13/deployments/' + RETAINED_READY)
        if (target.get('id') != RETAINED_READY or target.get('projectId') != PROJECT
                or target.get('ownerId') != TEAM or target.get('target') != 'production'
                or target.get('readyState') != 'READY' or target.get('aliasError') is not None
                or target.get('meta', {}).get('githubCommitSha') != '229df7f8b2cfb49a7f46215be3979608c39f7c33'):
            raise ValueError('Rollback identity/source/readiness unverified')
        for host in HOSTS:
            row = get('/v4/aliases/' + host)
            if (row.get('alias') != host or row.get('projectId') != PROJECT
                    or row.get('deploymentId') != RETAINED_READY):
                raise ValueError('Current exact alias assignment unverified')
    report = {'status': 'READ_ONLY_ACCESS_PASS', 'project_id': PROJECT, 'team_id': TEAM,
            'current_production_deployment': RETAINED_READY,
            'rollback_source': '229df7f8b2cfb49a7f46215be3979608c39f7c33',
            'provider_gets': 6, 'mutations': 0,
            'rollback_execution_eligibility': 'NOT_PROVEN_BY_METADATA_ONLY',
            'backend_compatibility': 'SEPARATE_GATE_NOT_RUN'}
    report['snapshot_sha256'] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    report['observed_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    return report


def conditional_promotion(metadata, environ=None, clock=time.monotonic, now=None,
                          request=provider_request, pause=time.sleep, existing_ready=False):
    """One production-only command; uncertain outcomes allow bounded GETs only.

    No runtime receipt is created here. The manual dispatch and protected environment
    provide the separately required production consent. Persist intent before sending.
    """
    env = os.environ if environ is None else environ
    expected_id = metadata.get("id")
    instant = dt.datetime.now(dt.timezone.utc) if now is None else now
    ready_ms = metadata.get("ready")
    rollback = release_rollback(env)
    if (not isinstance(expected_id, str) or not re.fullmatch(r"dpl_[A-Za-z0-9]+", expected_id)
            or expected_id == rollback or metadata.get("projectId") != PROJECT
            or metadata.get("ownerId") != TEAM or metadata.get("target") != "production"
            or metadata.get("readyState") != "READY" or type(ready_ms) is not int
            or metadata.get("aliasError") is not None
            or env.get("VERCEL_PROJECT_ID") != PROJECT or env.get("VERCEL_ORG_ID") != TEAM):
        raise ValueError("Production deployment/project/team binding rejected")
    for key, name in (("githubCommitSha", "FRONTEND_SHA"),
                      ("readerControllerSha", "CONTROLLER_SHA"),
                      ("readerBackendSha", "BACKEND_SHA")):
        expected = CREATION_CONTROLLER if existing_ready and name == "CONTROLLER_SHA" else env.get(name, "")
        if not re.fullmatch(r"[0-9a-f]{40}", expected) or metadata.get("meta", {}).get(key) != expected:
            raise ValueError("Exact production source binding rejected")
    age = instant.timestamp() - ready_ms / 1000
    # The caller release follows the already promoted Reader asset. Preserve
    # the historical promotion-only transaction and its PR528 predecessor.
    previous_id = RETAINED_READY if (not existing_ready
        and env.get("FRONTEND_SHA") == CALLER_FRONTEND
        and env.get("BACKEND_SHA") == CALLER_BACKEND) else ROLLBACK
    if existing_ready:
        # Separate, freshly authorized promotion-only operation. Never falsify READY
        # or the immutable controller that created this retained production asset.
        if (expected_id != RETAINED_READY or age < 0
                or ready_ms != 1792521693385
                or env.get("FRONTEND_SHA") != "229df7f8b2cfb49a7f46215be3979608c39f7c33"
                or env.get("BACKEND_SHA") != "fda9d5b4a4618447ef75026edf17bba7f28f0c83"
                or not re.fullmatch(r"[0-9a-f]{40}", env.get("CONTROLLER_SHA", ""))):
            raise ValueError("Retained production asset identity rejected")
    elif not 0 <= age < 900:
        raise ValueError("Original READY deadline expired")
    started = clock()
    ready_deadline = started + (900 if existing_ready else 900 - age)
    gets = 0
    resolution_deadline = None

    def get(path):
        nonlocal gets
        deadline = ready_deadline if resolution_deadline is None else min(ready_deadline, resolution_deadline)
        remaining = deadline - clock()
        if gets >= 30 or remaining <= 0:
            raise ValueError("Read-only resolution cap exhausted; operator resolution required")
        gets += 1
        result = request(path, "GET", min(5, remaining), env)
        if clock() >= deadline:
            raise ValueError("Read-only resolution deadline exceeded")
        return result

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
    public_hosts = set(PUBLIC_HOSTS)
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
        return {"status": "SKIPPED_ALREADY_ASSIGNED", "gets": gets, "aliases": rows}
    current = p.get("targets", {}).get("production", {})
    # Run39476136501: disabling custom-domain assignment retained all three
    # public aliases on PR528 but still moved the registered protected automatic
    # alias to the new STAGED deployment. Admit only that exact transition.
    staged_automatic_transition = (
        all(rows[host].get("deploymentId") == previous_id for host in PUBLIC_HOSTS)
        and rows[PROTECTED_HOST].get("deploymentId") == expected_id
        and metadata.get("readySubstate") == "STAGED"
        and metadata.get("aliasAssigned") is True
        and current.get("automaticAliases") == [PROTECTED_HOST]
        and metadata.get("automaticAliases") == [PROTECTED_HOST]
        and metadata.get("alias") == [PROTECTED_HOST]
    )
    if ids != {previous_id} and not staged_automatic_transition:
        raise ValueError("Mixed, foreign or unknown aliases; no promotion")
    if (current.get("id") != previous_id or set(current.get("alias", [])) != set(HOSTS)
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
    if staged_automatic_transition and any(fresh.get(key) != metadata.get(key) for key in
            ("readySubstate", "aliasAssigned", "automaticAliases", "alias")):
        raise ValueError("Staged automatic alias transition changed before promotion")
    if ready_deadline - clock() < 600:
        raise ValueError("Insufficient acceptance window immediately before promotion")
    intent = Path(env["RUNNER_TEMP"]) / "reader-promotion-intent.json"
    with intent.open("x") as handle:
        json.dump({"state": "SINGLE_ATTEMPT_STARTED_NO_RETRY", "deployment_id": expected_id,
                   "controller_sha": env["CONTROLLER_SHA"], "original_ready": ready_ms}, handle)
    # A timeout is not server cancellation. No second POST, even on timeout/error.
    command_state = "UNKNOWN"
    try:
        command_state = request("/v10/projects/" + PROJECT + "/promote/" + expected_id,
                                "POST", 60, env)
    except Exception:
        pass
    resolution_deadline = clock() + 60
    gets = 0  # All subsequent GETs, including final alias guard, share this cap.
    while True:
        p = project()
        alias_request = p.get("lastAliasRequest") or {}
        status = alias_request.get("jobStatus")
        if alias_request.get("toDeploymentId") != expected_id or alias_request.get("type") != "promote":
            raise ValueError("NEEDS_OPERATOR_RESOLUTION: promotion identity unavailable")
        if status in ("pending", "in-progress"):
            remaining = min(resolution_deadline, ready_deadline) - clock()
            if remaining <= 0 or gets >= 24:
                raise ValueError("NEEDS_OPERATOR_RESOLUTION: pending; no competing mutation")
            pause(min(2, remaining))
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
        if status in ("failed", "skipped") and ids == {previous_id}:
            raise ValueError("PROMOTION_FAILED_OLD_SERVING; leave the verified predecessor unchanged")
        raise ValueError("NEEDS_OPERATOR_RESOLUTION: terminal partial/queued/unknown; exact pinned recovery")

def rollback_disposition(project, aliases, rollback, expected_id, environ=None):
    """Read-only prerequisite to recovery: never POST an already restored target.

    The protected automatic alias is reported separately from public restoration.
    Unknown or mixed states require operator resolution, never an automatic retry.
    """
    rollback_id = release_rollback(environ)
    if (project.get("id") != PROJECT or project.get("accountId") != TEAM
            or project.get("rollingRelease") or set(aliases) != set(HOSTS)
            or rollback.get("id") != rollback_id or rollback.get("projectId") != PROJECT
            or rollback.get("ownerId") != TEAM or rollback.get("target") != "production"
            or rollback.get("readyState") != "READY" or rollback.get("aliasError") is not None
            or not re.fullmatch(r"dpl_[A-Za-z0-9]+", expected_id or "")
            or expected_id == rollback_id):
        raise ValueError("Recovery identity unavailable; no mutation")
    active = project.get("lastAliasRequest") or {}
    if active.get("jobStatus") in ("pending", "in-progress"):
        raise ValueError("Recovery operation unresolved; no mutation")
    for host, row in aliases.items():
        if (row.get("alias") != host or row.get("projectId") != PROJECT
                or row.get("deploymentId") not in (rollback_id, expected_id)):
            raise ValueError("Recovery alias unknown or foreign; no mutation")
    public = {aliases[h]["deploymentId"] for h in PUBLIC_HOSTS}
    current = project.get("targets", {}).get("production", {}).get("id")
    if public == {rollback_id} and current == rollback_id:
        status = "PUBLIC_RESTORATION_ALREADY_SATISFIED"
    elif public == {expected_id} and current == expected_id:
        status = "CONDITIONAL_ROLLBACK_REQUIRED"
    else:
        raise ValueError("Mixed public recovery state; operator resolution required")
    return {"status": status, "rollback_post_allowed": status == "CONDITIONAL_ROLLBACK_REQUIRED",
            "public_deployment_id": next(iter(public)),
            "protected_deployment_id": aliases[PROTECTED_HOST]["deploymentId"],
            "all_four_restored": all(r["deploymentId"] == rollback_id for r in aliases.values())}


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
    parser.add_argument("--github-output")
    parser.add_argument("--rollback-snapshot", action="store_true",
                        help="Read-only recovery prerequisite; metadata contains project/aliases/rollback/deployment_id")
    parser.add_argument("--conditional-promotion", action="store_true")
    parser.add_argument("--existing-ready-promotion", action="store_true",
                        help="Freshly authorized promotion-only operation for the exact retained asset; no build/deploy")
    args = parser.parse_args()
    try:
        metadata = json.loads(Path(args.metadata).read_text())
        if args.rollback_snapshot:
            if args.conditional_promotion or args.existing_ready_promotion:
                raise ValueError("Recovery classification cannot promote")
            report = rollback_disposition(metadata["project"], metadata["aliases"],
                                          metadata["rollback"], metadata["deployment_id"])
            with Path(args.output).open("x") as handle:
                json.dump(report, handle, indent=2)
            print(json.dumps(report, sort_keys=True))
            return 0
        if not args.github_output:
            raise ValueError("Release output destination required")
        if args.existing_ready_promotion and args.conditional_promotion:
            raise ValueError("Choose one promotion mode")
        operation_started = dt.datetime.now(dt.timezone.utc)
        promotion = conditional_promotion(metadata, existing_ready=args.existing_ready_promotion) if (
            args.conditional_promotion or args.existing_ready_promotion) else None
        if args.existing_ready_promotion:
            require_assigned_aliases(metadata, promotion["aliases"], RETAINED_READY, PROJECT)
            report = {"status": "PASS", "deployment_id": RETAINED_READY,
                      "original_ready": metadata["ready"], "project_id": PROJECT,
                      "promotion_window_started_at": operation_started.isoformat(),
                      "creation_controller_sha": CREATION_CONTROLLER,
                      "operator_controller_sha": os.environ["CONTROLLER_SHA"]}
        else:
            report = collect(metadata, alias_snapshot=promotion.get("aliases") if promotion else None)
        if promotion:
            report["promotion"] = {k: v for k, v in promotion.items() if k != "aliases"}
            Path(args.metadata).write_text(json.dumps(metadata) + "\n")
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        with Path(args.github_output).open("a") as handle:
            handle.write("deployment_id=" + report["deployment_id"] + "\n")
            if "ready_at" in report:
                handle.write("ready_at=" + report["ready_at"] + "\n")
            else:
                handle.write("promotion_window_started_at=" + report["promotion_window_started_at"] + "\n")
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
