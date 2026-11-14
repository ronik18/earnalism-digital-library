#!/usr/bin/env python3
"""One private, resumable Earnalism production entry point.

``projects.json`` (schema ``earnalism.production_registry.v1``) contains a
``projects`` list. Each project has id, kind (book/science), title, language and
data-only ``stages`` keyed by STAGES below. Science queue entries additionally
have series=EverydayScience, queue_status=ready and an explicit queue_order.
Stage specs use the fixed ``kind`` dispatcher in earnalism_media_adapters;
narration uses retained-narration or trained-voice. All file descriptors contain
path/SHA-256 (and optionally bytes), relative to the private workspace or their
containing JSON file. This is an execution engine, not a claim that a title alone
supplies missing source, trained voice qualification, music or cinematic assets.

Model stages require an actual, original runtime envelope and the underlying
worker's exact authority. Reversible local checks/renders need no extra approval.
No command, Python module, callback or publication action is read from a manifest.
Feedback changes recipes/checkpoints; it never claims to train model weights.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import book_audiovisual

REGISTRY_SCHEMA = "earnalism.production_registry.v1"
RUNTIME_SCHEMA = "earnalism.orchestrator_runtime.v1"
STAGES = ("source", "narration", "timing", "score", "visuals", "compose", "review", "release-ready")
DEPENDENCIES = {
    "source": (), "narration": ("source",), "timing": ("source", "narration"),
    "score": ("source", "narration", "timing"),
    "visuals": ("source", "narration", "timing"),
    "compose": ("score", "visuals"), "review": ("compose",), "release-ready": ("review",),
}
AREA_STAGES = {
    "narration": {"narration", "timing", "score", "visuals", "compose", "review", "release-ready"},
    "score": {"score", "compose", "review", "release-ready"},
    "visual": {"visuals", "compose", "review", "release-ready"},
    "captions": {"compose", "review", "release-ready"},
    "rights": {"source", *STAGES}, "technical": {"compose", "review", "release-ready"},
}
MODEL_KINDS = {"trained-voice", "wan-batch"}
FORBIDDEN_KEYS = {"command", "commands", "shell", "callback", "module", "python_code", "executable"}
HASH = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,99}\Z")


def _sha(path: Path) -> str:
    return book_audiovisual.digest(path)


def _canonical(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load(path: Path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"nonfinite JSON: {x}")))


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            json.dump(value, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _private_workspace(value) -> Path:
    path = Path(value).expanduser().resolve()
    if path == ROOT or path.is_relative_to(ROOT) or any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("production workspace, outputs and feedback must remain outside the source repository")
    return path


def _inside(path: Path, roots) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _local_path(raw, base: Path, workspace: Path, *, output=False) -> Path:
    if not isinstance(raw, str) or not raw.strip() or "://" in raw or "\x00" in raw:
        raise ValueError("an explicit local file path is required")
    workspace = workspace.resolve()
    path = (base / raw).resolve()
    allowed = (workspace,) if output else (workspace, ROOT)
    if not _inside(path, allowed):
        raise ValueError("file reference escapes the private workspace or maintained source")
    return path


def _no_commands(value):
    if isinstance(value, dict):
        if FORBIDDEN_KEYS & value.keys():
            raise ValueError("manifest commands, modules and callbacks are not supported")
        for child in value.values():
            _no_commands(child)
    elif isinstance(value, list):
        for child in value:
            _no_commands(child)


def _refs(value, base: Path, workspace: Path, *, found=None, seen=None):
    """Verify transitive JSON file bindings before a cache can be reused."""
    found = {} if found is None else found
    seen = set() if seen is None else seen
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            path = _local_path(value["path"], base, workspace)
            expected = value["sha256"]
            if not isinstance(expected, str) or not HASH.fullmatch(expected):
                raise ValueError("file descriptor requires an exact SHA-256")
            if not path.is_file() or _sha(path) != expected:
                raise ValueError(f"missing or changed input: {path.name}")
            if "bytes" in value and (isinstance(value["bytes"], bool)
                                     or value["bytes"] != path.stat().st_size):
                raise ValueError(f"input byte length mismatch: {path.name}")
            found[str(path)] = expected
            if len(found) > 4096:
                raise ValueError("input inventory exceeds the bounded private manifest")
            identity = (str(path), expected)
            if path.suffix == ".json" and identity not in seen:
                if path.stat().st_size > 8 * 1024**2:
                    raise ValueError("JSON metadata exceeds 8 MiB; split the project manifest")
                seen.add(identity)
                nested = _load(path)
                if isinstance(nested, dict) and nested.get("schema") == "earnalism.voice_profile.v1":
                    # Retained accepted narration does not require reloading the
                    # model/cache. The immutable profile binds their expected
                    # bytes; the voice worker validates executable assets again
                    # before actual inference. Rights/qualification evidence
                    # remains transitive and must still verify on cache reuse.
                    nested = {k: v for k, v in nested.items() if k not in {"assets", "checkpoint"}}
                _refs(nested, path.parent, workspace, found=found, seen=seen)
        for child in value.values():
            if isinstance(child, (dict, list)):
                _refs(child, base, workspace, found=found, seen=seen)
    elif isinstance(value, list):
        for child in value:
            _refs(child, base, workspace, found=found, seen=seen)
    return found


def _ref_path(ref, workspace: Path, base=None) -> Path:
    if not isinstance(ref, dict) or "path" not in ref or "sha256" not in ref:
        raise ValueError("stage needs a checksum-bound file descriptor")
    _refs(ref, base or workspace, workspace)
    return _local_path(ref["path"], base or workspace, workspace)


def parse_instruction(instruction: str) -> dict:
    if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 4000:
        raise ValueError("a nonempty production instruction of at most 4000 characters is required")
    text = instruction.strip()
    if re.search(r"everyday\s*science", text, re.I):
        requested_next = bool(re.search(r"\bnext\b", text, re.I))
        match = re.search(r"(?:topic|episode)\s*[-–—:]\s*(.+)", text, re.I)
        title = match.group(1).strip(" \t\r\n\"'“”") if match else None
        if not requested_next and not title:
            raise ValueError("name an EverydayScience topic after 'topic -', or request the next registered topic")
        return {"kind": "science", "series": "EverydayScience", "title": title,
                "language": None, "next": requested_next, "publication_requested": False}
    match = re.search(r"(?:(Bengali|English)\s+)?book\s*[-–—:]\s*(.+)", text, re.I)
    if not match:
        raise ValueError("use 'book - TITLE', 'Bengali book - TITLE', or 'next EverydayScience topic'")
    title = match.group(2).strip(" \t\r\n\"'“”")
    if not book_audiovisual.title_key(title):
        raise ValueError("book title is empty")
    language = {"bengali": "bn", "english": "en"}.get((match.group(1) or "").lower())
    if language is None and re.search(r"[\u0980-\u09ff]", title):
        language = "bn"
    return {"kind": "book", "title": title, "language": language, "next": False,
            "publication_requested": False}


def _registry(path: Path) -> dict:
    value = _load(path)
    if (not isinstance(value, dict) or value.get("schema") != REGISTRY_SCHEMA
            or not isinstance(value.get("projects"), list)):
        raise ValueError("private registry must use earnalism.production_registry.v1/projects")
    _no_commands(value)
    ids, identities = set(), set()
    for project in value["projects"]:
        if not isinstance(project, dict) or not isinstance(project.get("id"), str) or not ID.fullmatch(project["id"]):
            raise ValueError("project needs a safe stable id")
        if project["id"] in ids:
            raise ValueError("duplicate project id")
        ids.add(project["id"])
        if (project.get("kind") not in {"book", "science"} or project.get("language") not in {"en", "bn"}
                or not isinstance(project.get("title"), str) or not book_audiovisual.title_key(project["title"])
                or not isinstance(project.get("stages"), dict)
                or set(project["stages"]) - set(STAGES)):
            raise ValueError("project needs kind, exact title, EN/BN language and supported stages")
        aliases = project.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(x, str) for x in aliases):
            raise ValueError("project aliases must be explicit title strings")
        for title in [project["title"], *aliases]:
            identity = (project["kind"], project["language"], book_audiovisual.title_key(title))
            if identity in identities:
                raise ValueError("ambiguous registered edition/title alias")
            identities.add(identity)
        for stage, spec in project["stages"].items():
            if not isinstance(spec, dict) or not isinstance(spec.get("kind"), str):
                raise ValueError(f"{stage} needs a fixed typed kind")
    return value


def _state_path(workspace: Path, project_id: str) -> Path:
    return workspace / "runs" / project_id / "state.json"


def _select(request, registry, workspace):
    projects = [p for p in registry["projects"] if p["kind"] == request["kind"]]
    if request["kind"] == "science" and request["next"]:
        projects = [p for p in projects if p.get("series") == "EverydayScience"
                    and p.get("queue_status") == "ready"]
        ready = []
        for project in projects:
            order = project.get("queue_order")
            if isinstance(order, bool) or not isinstance(order, int) or order < 0:
                raise ValueError("next science requires explicit nonnegative queue_order values")
            path = _state_path(workspace, project["id"])
            if path.exists() and _load(path).get("queue_consumed") is True:
                continue
            ready.append(project)
        if len({p["queue_order"] for p in ready}) != len(ready):
            raise ValueError("next science queue order is ambiguous")
        return sorted(ready, key=lambda p: p["queue_order"])[:1]
    title = book_audiovisual.title_key(request["title"])
    return [p for p in projects if (request["language"] is None or p["language"] == request["language"])
            and any(book_audiovisual.title_key(x) == title for x in [p["title"], *p.get("aliases", [])])]


def _history(request, project, workspace):
    if request["kind"] != "book":
        return None
    canonical_path = ROOT / "internal/earnalism_intelligence/title_decision_history.json"
    title = project["title"] if project else request["title"]
    language = project["language"] if project else request["language"]
    canonical = book_audiovisual.plan(title, canonical_path, language) if canonical_path.is_file() else None
    if not project or not project.get("history"):
        return canonical or {"state": "MISSING_INPUT", "blockers": ["title decision history is unavailable"]}
    # A history snapshot is discovery metadata. Bind its own bytes, not every
    # unrelated historical title's possibly off-device media. Execution inputs
    # retain the normal transitive checks before any stage/cache is used.
    ref = project["history"]
    if not isinstance(ref, dict) or not isinstance(ref.get("sha256"), str) or not HASH.fullmatch(ref["sha256"]):
        raise ValueError("private history needs its exact file checksum")
    private_path = _local_path(ref.get("path"), workspace, workspace)
    if (not private_path.is_file() or _sha(private_path) != ref["sha256"]
            or "bytes" in ref and (type(ref["bytes"]) is not int or ref["bytes"] != private_path.stat().st_size)):
        raise ValueError("private title-history snapshot is missing or changed")
    private = book_audiovisual.plan(title, private_path, language)
    if canonical is None:
        return private
    return _additive_history(canonical, private)


def _revision_time(revision):
    try:
        parsed = datetime.fromisoformat(str(revision.get("date", "")).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def _additive_history(canonical, private):
    """A private snapshot can add findings, never silently erase baseline holds.

    Only a provably later explicit resolution under the existing human-revision
    contract clears the named areas. Both input planners already enforce exact
    title/language identity and validate that contract.
    """
    packets = [("canonical", canonical), ("private", private)]
    revisions = [(name, packet.get("current_owner_revision")) for name, packet in packets
                 if packet.get("current_owner_revision")]
    active = []
    for name, revision in revisions:
        if revision["status"] != "ACTIVE":
            continue
        when = _revision_time(revision)
        remaining = []
        for area in revision["required_changes"]:
            resolved = any(other["status"] == "RESOLVED" and other.get("language") == revision.get("language")
                           and area in other["required_changes"] and when is not None
                           and _revision_time(other) is not None and _revision_time(other) > when
                           for _, other in revisions)
            if not resolved:
                remaining.append(area)
        if remaining:
            active.append((name, revision, remaining))
    if active:
        name, primary, _ = max(active, key=lambda item: (_revision_time(item[1]) or float("-inf"), item[0] == "canonical"))
        areas = {area for _, _, remaining in active for area in remaining}
        revision = {**primary, "status": "ACTIVE", "required_changes": [area for area in book_audiovisual.INVALIDATES if area in areas]}
    else:
        name, revision = max(revisions, key=lambda item: (_revision_time(item[1]) or float("-inf"), item[0] == "canonical")) if revisions else ("private", None)
        areas = set()
    chosen = canonical if name == "canonical" else private
    result = {**private, "current_owner_revision": revision,
              "history_sources": [{"kind": label, **packet["history"]} for label, packet in packets],
              "owner_revision_sources": [{"kind": label, "revision": packet.get("current_owner_revision")}
                                         for label, packet in packets]}
    result["state"] = "OWNER_REVISION_REQUIRED" if active else chosen["state"]
    result["next_generated_prompt"] = (
        f"Resume {result['title']} with additive canonical/private history. Preserve the unresolved "
        f"owner changes in {', '.join(revision['required_changes'])}; apply only evidenced corrections "
        "and reuse unchanged evidence. This grants no synthesis, compute or publication authority."
        if active else chosen["next_generated_prompt"])
    candidates, seen = [], set()
    for _, packet in reversed(packets):
        for candidate in packet.get("retained_candidates", []):
            key = (candidate.get("path"), candidate.get("sha256"))
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
    result["retained_candidates"] = candidates
    if "narration" in areas:
        result["retained_candidates"] = [{**candidate,
            "reuse_disposition": "HISTORICAL_ONLY_OWNER_NARRATION_REVISION"} for candidate in candidates]
    result["preferred_retained_candidate"] = None if "narration" in areas else (
        private.get("preferred_retained_candidate") or canonical.get("preferred_retained_candidate"))
    result["actions"] = list(chosen["actions"])
    for index, area in ((1, "narration"), (2, "narration"), (3, "visual")):
        # Keep the existing planner's exact action wording for the effective hold.
        for _, packet in reversed(packets):
            own = packet.get("current_owner_revision") or {}
            own_active = own.get("status") == "ACTIVE" and area in own.get("required_changes", [])
            if own_active == (area in areas):
                result["actions"][index] = packet["actions"][index]
                break
    return result


def plan(instruction, workspace, registry_path=None) -> dict:
    workspace = _private_workspace(workspace)
    request = parse_instruction(instruction)
    path = Path(registry_path).expanduser().resolve() if registry_path else workspace / "projects.json"
    if not _inside(path, (workspace,)):
        raise ValueError("private project registry must remain in its workspace")
    base = {"schema": "earnalism.orchestrator_plan.v1", "request": request,
            "workspace": str(workspace), "registry_path": str(path), "private_only": True,
            "publication_performed": False, "model_weights_trained": False,
            "skills": list(book_audiovisual.SKILLS), "stages": list(STAGES)}
    if not path.is_file():
        return {**base, "state": "MISSING_INPUT", "project": None,
                "discovery": _history(request, None, workspace),
                "blockers": [f"register the exact private project inputs in {path}"],
                "next_action": "Prepare the private source/project registry; a title is not a media or quality receipt."}
    registry = _registry(path)
    candidates = _select(request, registry, workspace)
    if not candidates:
        return {**base, "registry_sha256": _sha(path), "state": "MISSING_INPUT", "project": None,
                "discovery": _history(request, None, workspace),
                "blockers": ["no exact registered edition or ready unconsumed ordered science project"],
                "next_action": "Register the actual project or explicit next-topic queue; do not guess a title or adapter."}
    if len(candidates) != 1:
        return {**base, "registry_sha256": _sha(path), "state": "EDITION_REQUIRED", "project": None,
                "blockers": ["multiple registered languages match; request English or Bengali explicitly"],
                "next_action": "Name the requested language/edition."}
    project = candidates[0]
    discovery = _history(request, project, workspace)
    expected_stages = STAGES[:2] if project.get("purpose") == "qualification" else STAGES
    missing = [stage for stage in expected_stages if stage not in project["stages"]]
    blockers = ["missing stage input: " + stage for stage in missing]
    return {**base, "registry_sha256": _sha(path), "project": project,
            "stages": list(expected_stages),
            "language": project["language"], "discovery": discovery,
            "state": "MISSING_INPUT" if missing else "PRIVATE_EXECUTION_PREPARED",
            "blockers": blockers,
            "owner_revision_active": bool(discovery and (discovery.get("current_owner_revision") or {}).get("status") == "ACTIVE"),
            "next_action": ("Prepare the missing typed stage inputs." if missing else
                            "Run the same notebook with existing exact execution authority where model stages require it; release checks remain independent.")}


def _feedback_events(workspace: Path, project_id: str):
    directory = workspace / "feedback" / project_id
    if not directory.exists():
        return []
    return [_load(path) for path in sorted(directory.glob("*.json"))]


def _software(stage, spec=None):
    spec = spec or {}
    relative = {
        "source": ["scripts/earnalism_media_adapters.py", "scripts/produce_release.py"],
        "narration": ["scripts/earnalism_voice.py", "scripts/earnalism_voice_runtime/parler.py"],
        "timing": ["scripts/earnalism_media_adapters.py", "scripts/audiobook_score.py"],
        "score": ["scripts/earnalism_media_adapters.py", "scripts/audiobook_score.py", "scripts/audiobook_score_renderer.py"],
        "visuals": ["scripts/earnalism_media_adapters.py", "skills/earnalism-video/software/wan22/batch.py", "skills/earnalism-video/software/wan22/worker.py"],
        "compose": ["scripts/earnalism_media_adapters.py", "scripts/book_av_render.py"],
        "review": ["scripts/earnalism_media_adapters.py", "scripts/release_acceptance.py"],
        "release-ready": ["scripts/earnalism_media_adapters.py", "scripts/produce_release.py", "scripts/release_acceptance.py",
                          "internal/earnalism_intelligence/audiobook_acceptance_policy.json",
                          "internal/earnalism_intelligence/sync_acceptance_policy.json",
                          "internal/earnalism_intelligence/release_decision_policy.md", "AGENTS.md"],
    }
    if stage == "visuals" and spec.get("kind") == "science-animation":
        folder = {"thermal-touch": "thermal_touch", "condensation": "condensation",
                  "sky-colour": "sky_colour", "rainbow": "rainbow"}.get(spec.get("science"))
        if folder:
            base = ROOT / "skills/earnalism-video/software" / folder
            relative[stage] += [str(path.relative_to(ROOT)) for path in base.rglob("*")
                                if path.is_file() and path.suffix in {".py", ".mjs", ".tsx", ".ts"}
                                and not {"node_modules", "public", "output", "__pycache__"} & set(path.parts)]
            relative[stage] += ["skills/earnalism-video/software/" + name for name in (
                "src/BrandWatermark.tsx", "src/branding.mjs", "src/social-safe-area.mjs",
                "src/render-browser.mjs", "src/render-runtime.mjs", "src/prepare-render-runtime.mjs",
                "package.json", "package-lock.json")]
    return {name: _sha(ROOT / name) for name in ["scripts/earnalism_orchestrator.py", *relative[stage]]
            if (ROOT / name).is_file()}


def _input_signature(stage, spec, project, upstream, workspace):
    refs = _refs(spec, workspace, workspace)
    return _canonical({"stage": stage, "kind": project["kind"], "language": project["language"],
                       "purpose": project.get("purpose", "production"), "spec": spec,
                       "verified_transitive_inputs": refs,
                       "upstream": {name: upstream[name]["fingerprint"] for name in DEPENDENCIES[stage]},
                       "owner_revision": project.get("_active_owner_revision") if stage in {"narration", "visuals"} else None,
                       "software": _software(stage, spec)})


def _fingerprint(stage, spec, project, upstream, events, workspace):
    relevant = [e for e in events if stage in e["invalidated_stages"]]
    signature = _input_signature(stage, spec, project, upstream, workspace)
    for event in relevant:
        if event.get("baseline_input_signatures", {}).get(stage) == signature:
            raise ValueError("apply the recorded feedback correction to changed inputs before repeating this stage")
    return _canonical({"inputs": signature, "feedback": relevant}), signature


def _number(value, name, low=0, high=10**15):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"invalid {name}")
    return value


def _runtime(path, project, workspace, observations):
    if path is None:
        return None
    path = Path(path).expanduser().resolve()
    if not _inside(path, (workspace,)):
        raise ValueError("runtime authority must remain in the private workspace")
    value = _load(path)
    if (not isinstance(value, dict) or value.get("schema") != RUNTIME_SCHEMA or value.get("owner_authorized") is not True
            or value.get("project_id") != project["id"]
            or not isinstance(value.get("scope_ref"), str) or not value["scope_ref"].strip()
            or not isinstance(value.get("evidence_ref"), str) or not value["evidence_ref"].strip()
            or value.get("purchases_allowed") is not False or value.get("publication_allowed") is not False):
        raise ValueError("actual project-bound runtime scope is required; instructions do not create authority")
    started = _number(value.get("allocation_started_at"), "original allocation start", 1)
    deadline = _number(value.get("original_deadline_epoch"), "original allocation deadline", 1)
    if not started <= time.time() < deadline <= started + 86400:
        raise ValueError("original allocation clock is missing, expired or unbounded")
    rate = _number(value.get("observed_units_per_hour"), "observed runtime rate")
    cap = _number(value.get("approved_compute_units"), "approved compute allowance")
    free = value.get("free_runtime_confirmed") is True and rate == 0 and cap == 0
    metered = (value.get("free_runtime_confirmed") is False and rate > 0 and cap > 0
               and 2 * rate * (deadline - started) / 3600 <= cap)
    if not (free or metered):
        raise ValueError("actual free runtime or finite twice-rate compute headroom is required")
    maximum = value.get("max_model_stage_starts")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 256:
        raise ValueError("runtime must bound model-stage starts")
    stage_limits = value.get("stage_attempt_limits", {})
    if (not isinstance(stage_limits, dict) or set(stage_limits) - set(STAGES)
            or any(isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= maximum
                   for limit in stage_limits.values())):
        raise ValueError("invalid per-stage attempt limits")
    if (not isinstance(observations, dict) or observations.get("shutdown_guard_armed") is not True
            or observations.get("allocation_started_at") != started
            or observations.get("original_deadline_epoch") != deadline):
        raise ValueError("the actual original shutdown timer must be armed before model execution")
    value = {**value, "path": str(path), "sha256": _sha(path)}
    return value


def _reserve_model(runtime, stage, fingerprint, workspace):
    if runtime is None:
        raise ValueError("model stage requires an actual guarded runtime envelope and exact worker authority")
    if time.time() >= runtime["original_deadline_epoch"]:
        raise ValueError("original runtime deadline exhausted; no renewal or retry")
    name = hashlib.sha256(runtime["scope_ref"].encode()).hexdigest()
    path = workspace / ".orchestrator" / "authorities" / (name + ".json")
    ledger = _load(path) if path.exists() else {"schema": "earnalism.orchestrator_scope_ledger.v1",
            "scope_ref": runtime["scope_ref"], "authority_sha256": runtime["sha256"], "starts": []}
    if ledger["authority_sha256"] != runtime["sha256"]:
        raise ValueError("preserve the original scope/clock/counters; changed authority cannot reset them")
    if len(ledger["starts"]) >= runtime["max_model_stage_starts"]:
        raise ValueError("model-stage allowance spent; no automatic retry")
    stage_maximum = runtime.get("stage_attempt_limits", {}).get(stage, 1)
    if sum(item["stage"] == stage for item in ledger["starts"]) >= stage_maximum:
        raise ValueError("this model stage's attempt is spent; unused other-stage allowance is not a retry")
    ledger["starts"].append({"stage": stage, "fingerprint": fingerprint, "at": time.time(),
                              "status": "RESERVED_BEFORE_DISPATCH_PRESERVE_IF_UNKNOWN"})
    _write(path, ledger)


@contextmanager
def _lock(workspace):
    directory = workspace / ".orchestrator"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "pipeline.lock").open("a") as target:
        try:
            fcntl.flock(target, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another notebook owns this private workspace; preserve its active run") from exc
        yield


def _artifacts(result, workspace):
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("fixed adapter must report its actual artifacts")
    for artifact in artifacts:
        _ref_path(artifact, workspace)
    return artifacts


def _source_binding(upstream):
    return upstream.get("source", {}).get("details", {}).get("bindings", {}).get("manuscript", {})


def _voice_master(result, output_dir, workspace, *, unit_base=None):
    """Join complete native units without trimming, gain or hidden retakes.

    This lossless derivative supplies the whole narration to the measured-timing
    stage. It deliberately makes no assertion about heard joins/naturalness.
    """
    outputs = result.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("trained voice has no actual native unit outputs")
    normalized, total = [], 0
    expected_end = None
    for item in outputs:
        if not isinstance(item, dict) or item.get("token_cap_reached") is not False:
            raise ValueError("incomplete/token-capped speech cannot become a whole narration")
        path = _local_path(item.get("path"), unit_base or output_dir, workspace)
        _refs({**item, "path": str(path)}, workspace, workspace)
        with path.open("rb") as stream:
            header = stream.read(44)
        if (len(header) != 44 or header[:4] != b"RIFF" or header[8:16] != b"WAVEfmt "
                or struct.unpack("<IHHIIHH", header[16:36]) != (16, 3, 1, 44100, 176400, 4, 32)
                or header[36:40] != b"data"):
            raise ValueError("expected exact native 44100 Hz mono float32 unit WAV")
        size = struct.unpack("<I", header[40:44])[0]
        if size != path.stat().st_size - 44 or size != item.get("frames", -1) * 4:
            raise ValueError("native unit audio length differs from its receipt")
        if expected_end is not None and item.get("source_start") != expected_end:
            raise ValueError("voice unit source order/coverage is discontinuous")
        expected_end = item.get("source_end")
        total += size
        normalized.append({**item, "path": str(path)})
    if total > 2**32 - 36:
        raise ValueError("native narration exceeds bounded RIFF capacity")
    master = output_dir / "narration-master.wav"
    header = b"RIFF" + struct.pack("<I", 36 + total) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 3, 1, 44100, 176400, 4, 32) + b"data" + struct.pack("<I", total)
    with master.open("xb") as target:
        target.write(header)
        for item in normalized:
            with Path(item["path"]).open("rb") as source:
                source.seek(44)
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    target.write(block)
        target.flush()
        os.fsync(target.fileno())
    master_ref = {"path": str(master), "sha256": _sha(master), "bytes": master.stat().st_size}
    trace = {"schema": "earnalism.voice_master.v1", "source_sha256": result["source_sha256"],
             "profile_sha256": result["profile_sha256"], "checkpoint_sha256": result["checkpoint_sha256"],
             "purpose": result.get("purpose"), "source_coverage": result.get("source_coverage"),
             "operation": "CONCATENATE_EXACT_NATIVE_FLOAT32_PCM", "gain": 1.0, "trimmed": False,
             "unit_order": [item["unit"] for item in normalized], "native_units": normalized,
             "outputs": [master_ref], "join_naturalness": "UNPERFORMED",
             "production_accepted": False, "publication_approved": False}
    provenance = output_dir / "narration-master-provenance.json"
    with provenance.open("x", encoding="utf-8") as target:
        json.dump(trace, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")
    artifacts = [*normalized, master_ref, {"path": str(provenance), "sha256": _sha(provenance)}]
    native_result = output_dir / "RESULT.json"
    if native_result.is_file():
        artifacts.append({"path": str(native_result), "sha256": _sha(native_result)})
    return master_ref, artifacts


def _recover_voice(spec, state, context, fingerprint):
    """Recover a local derivative only after exact native completion is proved."""
    from scripts.earnalism_voice import verify_retained
    workspace = Path(context["workspace"])
    candidates = [attempt for attempt in state["attempts"] if attempt.get("stage") == "narration"
                  and attempt.get("output_dir") and
                  (_local_path(attempt["output_dir"], workspace, workspace, output=True) / "RESULT.json").is_file()]
    if not candidates:
        return None
    job = _ref_path(spec.get("job"), workspace)
    if (_load(job).get("source") or {}).get("sha256") != _source_binding(context["upstream"]).get("sha256"):
        return None
    for attempt in reversed(candidates):
        if (context.get("owner_narration_hold") and attempt.get("owner_revision_sha256")
                != context["owner_revision_sha256"]):
            continue
        original = _local_path(attempt["output_dir"], workspace, workspace, output=True)
        if not (original / "RESULT.json").is_file():
            continue
        try:
            result = verify_retained(job, original)
        except (OSError, ValueError, RuntimeError):
            continue
        output = Path(context["run_root"]) / "narration-recovery" / f"{fingerprint[:16]}-{time.time_ns()}"
        output.mkdir(parents=True, exist_ok=False)
        audio, artifacts = _voice_master(result, output, workspace, unit_base=original)
        artifacts.append({"path": str(original / "RESULT.json"), "sha256": _sha(original / "RESULT.json")})
        return {"status": "COMPLETE", "artifacts": artifacts, "blockers": [],
                "acceptance": {"release_approved": False},
                "details": {"voice_result": result, "bindings": {"narration": audio,
                    "manuscript": _source_binding(context["upstream"])},
                    "recovery": "VERIFIED_NATIVE_UNITS_LOCAL_MASTER_ONLY", "new_model_calls": 0,
                    "quality_acceptance": "NOT_INFERRED"}}
    return None


def _narration(spec, context):
    from scripts import earnalism_voice
    workspace = Path(context["workspace"])
    if spec["kind"] == "retained-narration":
        if context.get("owner_narration_hold"):
            return {"status": "BLOCKED", "artifacts": [],
                    "blockers": ["active owner narration revision prevents retained narration reuse"],
                    "acceptance": {"release_approved": False}, "details": {}}
        audio = _ref_path(spec.get("audio"), workspace)
        profile = _ref_path(spec.get("profile"), workspace)
        provenance = _ref_path(spec.get("provenance"), workspace)
        inspection = earnalism_voice.inspect_profile(profile, context["language"], purpose="production")
        if inspection.get("status") != "QUALIFIED" or inspection.get("production_accepted") is not True:
            return {"status": "BLOCKED", "artifacts": [], "blockers": inspection.get("blockers") or
                    ["The Earnalism Voice is not production-qualified for this language"],
                    "acceptance": {"release_approved": False}, "details": {"profile": inspection}}
        receipt = _load(provenance)
        source_sha = _source_binding(context["upstream"]).get("sha256")
        audio_sha = _sha(audio)
        outputs = receipt.get("outputs") or receipt.get("artifacts") or []
        output_shas = {r.get("sha256") for r in outputs if isinstance(r, dict)}
        if (receipt.get("profile_sha256") != _sha(profile)
                or receipt.get("checkpoint_sha256") != inspection.get("checkpoint_sha256")
                or not source_sha or receipt.get("source_sha256") != source_sha
                or audio_sha not in output_shas or receipt.get("purpose") != "production"
                or receipt.get("source_coverage") != "FULL_EXACT_TEXT_NOT_AUDIO_FIDELITY"):
            raise ValueError("retained narration lacks exact source/trained-profile/checkpoint/audio lineage")
        text = _ref_path(_source_binding(context["upstream"]), workspace).read_text(encoding="utf-8")
        units = receipt.get("native_units") or outputs
        end = 0
        for unit in units:
            if (type(unit.get("source_start")) is not int or type(unit.get("source_end")) is not int
                    or unit["source_start"] != end or not end < unit["source_end"] <= len(text)
                    or hashlib.sha256(text[end:unit["source_end"]].encode()).hexdigest() != unit.get("spoken_text_sha256")):
                raise ValueError("retained narration source spans do not cover the complete manuscript in order")
            end = unit["source_end"]
        if end != len(text):
            raise ValueError("partial qualification speech is not full-book retained narration")
        ref = {"path": str(audio), "sha256": audio_sha}
        return {"status": "COMPLETE", "artifacts": [ref, {"path": str(provenance), "sha256": _sha(provenance)}],
                "blockers": [], "acceptance": {"release_approved": False},
                "details": {"bindings": {"narration": ref, "manuscript": _source_binding(context["upstream"])},
                            "profile": inspection, "quality_acceptance": "NOT_INFERRED"}}
    if spec["kind"] != "trained-voice":
        raise ValueError("unsupported narration kind; stock/fallback speech is not the branded trained voice")
    job = _ref_path(spec.get("job"), workspace)
    authority = _ref_path(spec.get("authority"), workspace)
    value = _load(job)
    source = value.get("source") or value.get("manuscript")
    if not isinstance(source, dict) or source.get("sha256") != _source_binding(context["upstream"]).get("sha256"):
        raise ValueError("voice job source differs from the actual upstream manuscript")
    result = earnalism_voice.render(job, Path(context["output_dir"]), authority)
    if result.get("status") != "PRIVATE_GENERATED_REQUIRES_QA":
        return {"status": "BLOCKED", "artifacts": [], "blockers": result.get("blockers") or
                ["trained voice did not complete a private source-bound output"],
                "acceptance": {"release_approved": False}, "details": {"voice_result": result}}
    audio, artifacts = _voice_master(result, Path(context["output_dir"]), workspace)
    return {"status": "COMPLETE", "artifacts": artifacts, "blockers": [],
            "acceptance": {"release_approved": False},
            "details": {"voice_result": result, "bindings": {"narration": audio,
                        "manuscript": _source_binding(context["upstream"])}, "quality_acceptance": "NOT_INFERRED"}}


def _dispatch(stage, spec, context):
    if stage == "narration":
        return _narration(spec, context)
    from scripts.earnalism_media_adapters import run_stage
    return run_stage(stage, spec, context)


def _preflight_voice_job(spec, workspace, project, upstream):
    """Validate scope/full-text policy before reserving or calling a model."""
    job_path = _ref_path(spec.get("job"), workspace)
    job = _load(job_path)
    if (not isinstance(job, dict) or job.get("purpose") != project.get("purpose", "production")
            or job.get("language") != project["language"]):
        raise ValueError("voice job purpose/language must match the selected project before execution")
    if (job.get("source") or {}).get("sha256") != _source_binding(upstream).get("sha256"):
        raise ValueError("voice job source differs from the actual upstream manuscript")
    from scripts.earnalism_voice import validate_job
    validate_job(job_path)  # Production requires exact full spans and actual profile acceptance.


def _ready(stage_results, active_hold, purpose):
    last = stage_results.get("release-ready", {})
    details = last.get("details", {})
    return (not active_hold and purpose == "production"
            and all(stage_results.get(s, {}).get("status") == "COMPLETE" for s in STAGES)
            and details.get("evaluator") == "scripts.produce_release.evaluate"
            and details.get("governor", {}).get("release_status") == "READY_FOR_GO_LIVE"
            and bool(details.get("manifest")))


def run(instruction, workspace, registry_path=None, execute=False, authority_path=None,
        runtime_context=None) -> dict:
    action = plan(instruction, workspace, registry_path)
    if not execute or action.get("project") is None:
        return {**action, "execution_requested": bool(execute), "executed_stages": [],
                "production_ready": False, "model_calls": 0}
    workspace = _private_workspace(workspace)
    project = {**action["project"], "_active_owner_revision":
               (action.get("discovery") or {}).get("current_owner_revision")}
    purpose = project.get("purpose", "production")
    if purpose not in {"production", "qualification"}:
        raise ValueError("project purpose must be production or qualification")
    with _lock(workspace):
        runtime = _runtime(authority_path, project, workspace, runtime_context) if authority_path else None
        state_path = _state_path(workspace, project["id"])
        identity = {"kind": project["kind"], "language": project["language"],
                    "title": book_audiovisual.title_key(project["title"])}
        state = _load(state_path) if state_path.exists() else {"schema": "earnalism.orchestrator_state.v1",
                "project_id": project["id"], "identity": identity, "attempts": [], "stages": {}, "queue_consumed": False}
        if (not isinstance(state, dict) or state.get("project_id") != project["id"] or state.get("identity") != identity
                or not isinstance(state.get("attempts"), list)):
            raise ValueError("existing checkpoint belongs to another project or has invalid attempts")
        events = _feedback_events(workspace, project["id"])
        upstream, executed, reused, blockers = {}, [], [], []
        for stage in STAGES:
            if purpose == "qualification" and stage not in STAGES[:2]:
                break
            spec = project["stages"].get(stage)
            if spec is None:
                blockers.append("missing stage input: " + stage)
                break
            try:
                if stage == "narration" and spec.get("kind") == "trained-voice":
                    _preflight_voice_job(spec, workspace, project, upstream)
                fingerprint, input_signature = _fingerprint(stage, spec, project, upstream, events, workspace)
                model_stage = spec.get("kind") in MODEL_KINDS
                revision = project.get("_active_owner_revision") or {}
                narration_hold = revision.get("status") == "ACTIVE" and "narration" in revision.get("required_changes", [])
                if stage == "narration" and spec.get("kind") == "retained-narration" and narration_hold:
                    blockers.append("narration: active owner revision prevents rejected retained narration reuse")
                    break
                current = state["stages"].get(stage)
                if current and current.get("fingerprint") == fingerprint and current.get("status") == "COMPLETE":
                    _artifacts(current, workspace)
                    upstream[stage] = current
                    reused.append(stage)
                    continue
                if stage == "narration" and spec.get("kind") == "trained-voice":
                    recovery_context = {"workspace": str(workspace), "run_root": str(state_path.parent),
                        "upstream": upstream, "owner_narration_hold": narration_hold,
                        "owner_revision_sha256": _canonical(revision)}
                    recovered = _recover_voice(spec, state, recovery_context, fingerprint)
                    if recovered:
                        _artifacts(recovered, workspace)
                        recovered.update(fingerprint=fingerprint, input_signature=input_signature)
                        state["stages"][stage] = recovered
                        state["attempts"].append({"stage": stage, "fingerprint": fingerprint,
                            "status": "COMPLETE_LOCAL_RECOVERY", "at": time.time(), "model_stage_reserved": False})
                        _write(state_path, state)
                        upstream[stage] = recovered
                        executed.append(stage)
                        continue
                prior = [a for a in state["attempts"] if a.get("stage") == stage
                         and a.get("fingerprint") == fingerprint
                         and (not model_stage or a.get("authority_sha256") == (runtime or {}).get("sha256"))]
                if prior:
                    blockers.append(f"{stage}: prior {prior[-1]['status']} attempt remains consumed; inspect its records, no replay")
                    break
                output_dir = _local_path(spec.get("output_dir") or
                    f"runs/{project['id']}/{stage}/{fingerprint[:16]}", workspace, workspace, output=True)
                if runtime and time.time() >= runtime["original_deadline_epoch"]:
                    raise ValueError("original runtime deadline expired; preserve checkpoints")
                stage_authority = spec.get("authority")
                exact_authority = str(_ref_path(stage_authority, workspace)) if stage_authority else None
                if model_stage and not exact_authority:
                    raise ValueError("model stage needs its exact existing worker authority")
                if exact_authority and runtime:
                    child = _load(Path(exact_authority))
                    child_started = child.get("allocation_started_at")
                    child_deadline = child.get("original_deadline_epoch", child.get("absolute_deadline_epoch"))
                    if child_deadline is None and "wall_seconds" in child and child_started is not None:
                        child_deadline = child_started + child["wall_seconds"]
                    if (child_started != runtime["allocation_started_at"]
                            or child_deadline != runtime["original_deadline_epoch"]):
                        raise ValueError("worker authority must preserve the same original runtime clock")
                if model_stage:
                    _reserve_model(runtime, stage, fingerprint, workspace)
                context = {"workspace": str(workspace), "repo_root": str(ROOT), "project_id": project["id"],
                    "run_root": str(state_path.parent), "output_dir": str(output_dir), "language": project["language"],
                    "purpose": purpose, "execute": True, "upstream": upstream,
                    "authority_path": exact_authority, "shutdown_guard_armed": bool(runtime),
                    "allocation_started_at": runtime["allocation_started_at"] if runtime else None,
                    "original_deadline": runtime["original_deadline_epoch"] if runtime else None,
                    "original_deadline_epoch": runtime["original_deadline_epoch"] if runtime else None,
                    "owner_narration_hold": narration_hold}
                attempt = {"stage": stage, "fingerprint": fingerprint, "status": "STARTED",
                           "started": time.time(), "model_stage_reserved": model_stage,
                           "output_dir": str(output_dir), "owner_revision_sha256": _canonical(revision),
                           "authority_sha256": runtime["sha256"] if model_stage and runtime else None}
                state["attempts"].append(attempt)
                _write(state_path, state)
                result = _dispatch(stage, spec, context)
                if not isinstance(result, dict) or result.get("status") not in {"COMPLETE", "BLOCKED"}:
                    raise ValueError("fixed adapter returned an unknown status; no PASS can be inferred")
                _artifacts(result, workspace)
                if result["status"] == "COMPLETE" and (not result["artifacts"] or result.get("blockers")):
                    raise ValueError("stage completion requires actual artifacts and an empty blocker list")
                if _input_signature(stage, spec, project, upstream, workspace) != input_signature:
                    raise ValueError("stage inputs/software changed during execution; preserve outputs without promoting them")
                result = {**result, "fingerprint": fingerprint, "input_signature": input_signature}
                attempt.update(status=result["status"], ended=time.time())
                state["stages"][stage] = result
                if stage == "compose" and result["status"] == "COMPLETE":
                    state["queue_consumed"] = True  # next means next unprepared episode, never auto-publication
                _write(state_path, state)
                executed.append(stage)
                if result["status"] != "COMPLETE":
                    blockers.extend(f"{stage}: {b}" for b in result.get("blockers") or ["fixed adapter held the stage"])
                    break
                upstream[stage] = result
            except Exception as exc:
                if state["attempts"] and state["attempts"][-1].get("stage") == stage and state["attempts"][-1].get("status") == "STARTED":
                    state["attempts"][-1].update(status="FAILED_OR_UNKNOWN_NO_REPLAY", ended=time.time(),
                                                error_type=type(exc).__name__, error=str(exc))
                blockers.append(f"{stage}: {exc}")
                _write(state_path, state)
                break
        actual_projects = _registry(Path(action["registry_path"]))["projects"]
        actual_project = next((p for p in actual_projects if p["id"] == project["id"]), None)
        project_unchanged = actual_project == action["project"]
        if not project_unchanged:
            blockers.append("selected project changed during execution; preserve this candidate and reconcile its inputs")
        ready = project_unchanged and _ready(upstream, action.get("owner_revision_active", False), purpose)
        if action.get("owner_revision_active"):
            blockers.append("active owner revision remains unresolved; private changes do not clear it")
        qualification_complete = purpose == "qualification" and upstream.get("narration", {}).get("status") == "COMPLETE"
        if not blockers and not ready and not qualification_complete:
            blockers.append("complete candidate lacks an actual READY_FOR_GO_LIVE governor result")
        report = {"schema": "earnalism.orchestrator_result.v1", "project_id": project["id"],
                  "request": action["request"], "language": project["language"],
                  "state": ("GO_LIVE_READY_PRIVATE" if ready else "QUALIFICATION_READY_FURTHER_QA"
                            if qualification_complete else "PRIVATE_REVIEW_OR_INPUT_REQUIRED"),
                  "executed_stages": executed, "reused_stages": reused, "stages": upstream,
                  "blockers": blockers, "production_ready": ready, "private_only": True,
                  "publication_performed": False, "model_weights_trained": False,
                  "model_stage_dispatch_reservations_total": sum(a.get("model_stage_reserved") is True for a in state["attempts"]),
                  "next_action": ("Use the existing exact-candidate destination handoff; this notebook does not publish."
                                  if ready else "Review the exact audition for fidelity, accent, expression and naturalness; it is not full-title acceptance."
                                  if qualification_complete else "Resolve the first concrete blocker, preserve attempts and resume this same notebook.")}
        state["last_result"] = {k: v for k, v in report.items() if k != "stages"}
        _write(state_path, state)
        _write(state_path.parent / "result.json", report)
        return report


def feedback(input_path, workspace) -> dict:
    workspace = _private_workspace(workspace)
    path = Path(input_path).expanduser().resolve()
    value = _load(path)
    project_id = value.pop("project_id", None) if isinstance(value, dict) else None
    if not isinstance(project_id, str) or not ID.fullmatch(project_id):
        raise ValueError("feedback needs its exact registered project_id")
    event = book_audiovisual.feedback(value)
    state_path = _state_path(workspace, project_id)
    if not state_path.is_file():
        raise ValueError("feedback must bind an actual retained project candidate")
    state = _load(state_path)
    known = [ref for result in state.get("stages", {}).values()
             for ref in result.get("artifacts", []) if isinstance(ref, dict)
             and ref.get("sha256") == event["candidate_sha256"]]
    if not known:
        raise ValueError("feedback candidate is not an actual retained artifact of this project")
    if not any(_ref_path(ref, workspace).is_file() for ref in known):
        raise ValueError("feedback candidate bytes are unavailable")
    event.update(project_id=project_id, invalidated_stages=sorted(AREA_STAGES[event["area"]]),
                 baseline_input_signatures={stage: result.get("input_signature") for stage, result in
                     state.get("stages", {}).items() if stage in AREA_STAGES[event["area"]]},
                 model_weights_trained=False, acceptance_created=False)
    event_id = _canonical({"project_id": project_id, **value})
    target = workspace / "feedback" / project_id / (event_id + ".json")
    with _lock(workspace):
        if target.exists():
            return {**_load(target), "feedback_path": str(target), "duplicate_reused": True}
        _write(target, event)
    return {**event, "feedback_path": str(target), "duplicate_reused": False,
            "next_action": "Apply the evidenced bounded correction; unchanged stages remain reusable and spent model attempts stay consumed."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        item = commands.add_parser(name)
        item.add_argument("--instruction", required=True)
        item.add_argument("--workspace", type=Path, required=True)
        item.add_argument("--registry", type=Path)
        item.add_argument("--output", type=Path)
        if name == "run":
            item.add_argument("--execute", action="store_true")
            item.add_argument("--authority", type=Path)
            item.add_argument("--runtime-context", type=Path,
                              help="actual notebook timer observations, never synthesized approval")
    item = commands.add_parser("feedback")
    item.add_argument("--input", type=Path, required=True)
    item.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "feedback":
            result = feedback(args.input, args.workspace)
        elif args.command == "plan":
            result = plan(args.instruction, args.workspace, args.registry)
        else:
            result = run(args.instruction, args.workspace, args.registry, args.execute, args.authority,
                         _load(args.runtime_context) if args.runtime_context else None)
        if getattr(args, "output", None):
            out = _local_path(str(args.output), Path.cwd(), _private_workspace(args.workspace), output=True)
            _write(out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if args.command in {"plan", "feedback"} or not args.execute or result.get("production_ready") else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Earnalism orchestrator: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
