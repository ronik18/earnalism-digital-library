"""Fixed private media executors for the instruction-driven Earnalism controller.

Specs contain bound data, never commands, import paths or callbacks. Completion
means that this stage ran; it never supplies listening, acting or release consent.
The existing source, score, compositor, Wan and release validators remain in use.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = ROOT / "skills/earnalism-video/software"
SCIENCE = {
    "thermal-touch": ("thermal_touch", "Thermal"),
    "condensation": ("condensation", "Condensation"),
    "sky-colour": ("sky_colour", "SkyColour"),
    "rainbow": ("rainbow", "Rainbow"),
}
KINDS = {
    "source": {"book-source"}, "timing": {"measured-timing"},
    "score": {"source-bound-score"},
    "visuals": {"wan-batch", "wan-import", "science-animation", "source-bound-assets"},
    "compose": {"book-av", "science-finish", "retained-audio-layout"},
    "review": {"book-av-review", "retained-audio-review"},
    "release-ready": {"book-release", "science-release"},
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError("Unexpected or missing typed adapter fields")


def _inside(path, workspace, base=None):
    path = Path(path)
    if not path.is_absolute():
        path = (base or workspace) / path
    resolved = path.resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("Media path escapes the private workspace")
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(workspace)):
        raise ValueError("Symlink media inputs/outputs are not supported")
    return resolved


def _ref(value, workspace, base=None):
    _keys(value, ("path", "sha256"))
    if not isinstance(value["path"], str) or not re.fullmatch(r"[a-f0-9]{64}", str(value["sha256"])):
        raise ValueError("Exact file path and SHA-256 required")
    path = _inside(value["path"], workspace, base)
    if not path.is_file() or sha(path) != value["sha256"]:
        raise ValueError("Missing or changed bound media file: " + str(path))
    return path


def _json(path):
    from scripts.audiobook_score import load_json
    return load_json(Path(path))


def _scan_refs(value, workspace, base):
    """Constrain nested existing job references before invoking their validators."""
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            _ref({key: value[key] for key in ("path", "sha256")}, workspace, base)
        for child in value.values():
            _scan_refs(child, workspace, base)
    elif isinstance(value, list):
        for child in value:
            _scan_refs(child, workspace, base)


def _bound(path):
    return {"path": str(path), "sha256": sha(path)}


def _files(root):
    result = []
    for folder, directories, filenames in os.walk(root):
        directories[:] = sorted(d for d in directories if d not in {
            "model", "venv", "hf-cache", "node_modules", "render-bundle", "__pycache__"}
            and not (Path(folder) / d).is_symlink())
        result.extend(_bound(Path(folder) / name) for name in sorted(filenames)
                      if not (Path(folder) / name).is_symlink())
    return result


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _result(artifacts=(), *, blockers=(), bindings=None, **details):
    return {"status": "BLOCKED" if blockers else "COMPLETE", "artifacts": list(artifacts),
            "blockers": list(blockers),
            "acceptance": {"publication_approved": False, "listening": "UNPERFORMED",
                           "acting": "UNPERFORMED", "release_approved": False},
            "details": {"bindings": bindings or {}, **details}}


def _consume(context, stage, role, expected):
    upstream = context.get("upstream")
    if upstream is None:  # Direct command use still validates all exact input bytes.
        return
    record = upstream.get(stage) or {}
    bindings = (record.get("details") or {}).get("bindings") or {}
    actual = bindings.get(role)
    if actual:
        hashes = {actual.get("sha256")} if isinstance(actual, dict) else {actual}
    else:
        hashes = {r.get("sha256") for r in record.get("artifacts", [])}
    if expected not in hashes:
        raise ValueError(f"Stale handoff: {role} does not consume the current {stage} output")


def _score_input(spec, context, workspace):
    from scripts.audiobook_score import validate_input
    path = _ref(spec["score_input"], workspace)
    raw = _json(path)
    _scan_refs(raw, workspace, path.parent)
    if raw.get("fixture_mode"):
        raise ValueError("Production adapter does not accept synthetic fixture timing")
    data = validate_input(path)
    if raw["manuscript"]["language"] != context["language"]:
        raise ValueError("Manuscript language differs from selected project")
    _consume(context, "source", "manuscript", raw["manuscript"]["sha256"])
    _consume(context, "narration", "narration", raw["narration"]["sha256"])
    return path, raw, data


def _source(spec, context, workspace):
    from scripts.produce_release import check_file, check_rights
    _keys(spec, ("kind", "manifest"))
    path = _ref(spec["manifest"], workspace)
    data = _json(path)
    manuscript = data.get("manuscript") or {}
    _scan_refs(manuscript, workspace, path.parent)
    rights = check_rights(data)
    check = check_file(path.parent, manuscript.get("path"), manuscript.get("sha256"), "manuscript")
    if rights["status"] != "PASS" or check["status"] != "PASS":
        raise ValueError(rights["detail"] if rights["status"] != "PASS" else check["detail"])
    if manuscript.get("language") != context["language"]:
        raise ValueError("Explicit EN/BN source language binding required")
    source = _ref({k: manuscript[k] for k in ("path", "sha256")}, workspace, path.parent)
    if not source.read_text(encoding="utf-8").strip():
        raise ValueError("Empty source manuscript")
    return _result([_bound(path), _bound(source)], bindings={"manuscript": _bound(source)},
                   rights=rights, scope="Source-file/retained-rights checks only; no new legal or editorial acceptance")


def _timing(spec, context, workspace):
    _keys(spec, ("kind", "score_input"))
    path, raw, data = _score_input(spec, context, workspace)
    timing = _ref({k: raw["timing"][k] for k in ("path", "sha256")}, workspace, path.parent)
    return _result([_bound(path), _bound(timing)], bindings={
        "manuscript": {k: data["manuscript"][k] for k in ("path", "sha256")},
        "narration": {k: data["narration"][k] for k in ("path", "sha256")},
        "timing": _bound(timing)}, timing_method=data["timing"]["method"],
        scope="Validates supplied measured alignment; does not infer new speech timings")


def _score(spec, context, workspace):
    from scripts.audiobook_score import plan_score
    from scripts.audiobook_score_renderer import render_score
    _keys(spec, ("kind", "score_input", "direction", "output_dir"), ("continuous_body",))
    if "continuous_body" in spec and type(spec["continuous_body"]) is not bool:
        raise ValueError("continuous_body must be an explicit boolean")
    path, raw, data = _score_input(spec, context, workspace)
    _consume(context, "timing", "timing", raw["timing"]["sha256"])
    direction = _ref(spec["direction"], workspace)
    plan = plan_score(path, direction)
    # Missing stems/uncertain semantic interpretation are not a finished score.
    pending = plan.get("review_items") or []
    if pending:
        return _result([_bound(path), _bound(direction)], blockers=["Score direction/stem review remains unresolved"], review=pending)
    if spec.get("continuous_body"):
        _require_continuous(plan)
    output = _inside(spec["output_dir"], workspace)
    report = render_score(plan, output)
    mix = _bound(Path(report["outputs"]["final_mix"]["path"]))
    return _result(_files(output), bindings={"scored_audio": mix,
        "score_plan": _bound(Path(report["outputs"]["effective_plan"]["path"])),
        "manuscript": {k: data["manuscript"][k] for k in ("path", "sha256")},
        "narration": {k: data["narration"][k] for k in ("path", "sha256")},
        "timing": {k: data["timing_ref"][k] for k in ("path", "sha256")}},
        render_report=_bound(output / "report.json"), scope="Actual private score stems/mix; emotional fit requires review")


def _require_continuous(plan):
    placements = sorted(plan.get("placements", []), key=lambda p: p["start_ms"])
    duration = plan["narration"]["duration_ms"]
    if not placements or placements[0]["start_ms"] != 0:
        raise ValueError("Science requires cleared instrumental coverage from body opening")
    end = placements[0]["end_ms"]
    previous = placements[0]
    for placement in placements[1:]:
        overlap = end - placement["start_ms"]
        if overlap < 0 or (overlap == 0 and (previous["fade_out_ms"] or placement["fade_in_ms"])):
            raise ValueError("Science body music contains an intentional gap or unoverlapped internal fade")
        end = max(end, placement["end_ms"])
        previous = placement
    if end < duration:
        raise ValueError("Science instrumental coverage ends before the full body")


def _known_module(relative, name):
    spec = importlib.util.spec_from_file_location(name, SOFTWARE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(args, *, cwd=None, timeout=1800, log=None, env=None):
    """Only callers below construct argv; no command field is read from a job."""
    if log is None:
        return subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                              text=True, check=True, timeout=timeout, env=env)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("x") as stream:
        process = subprocess.Popen([str(a) for a in args], cwd=cwd, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True, env=env)
        try:
            code = process.wait(timeout=timeout)
            if code:
                raise subprocess.CalledProcessError(code, args)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)


def _wan(spec, context, workspace):
    _keys(spec, ("kind", "job", "inputs", "authority", "output_dir"))
    job_path = _ref(spec["job"], workspace)
    inputs = _ref(spec["inputs"], workspace)
    auth_path = _ref(spec["authority"], workspace)
    batch = _known_module("wan22/batch.py", "earnalism_fixed_wan_batch")
    job = batch.validate(_json(job_path))
    authority = _json(auth_path)
    # A stored approval alone cannot activate setup/downloads in an ordinary run.
    if context.get("execute") is not True or context.get("shutdown_guard_armed") is not True:
        return _result(blockers=["Wan execution requires current explicit runtime activation and its original shutdown guard"])
    if Path(str(context.get("authority_path", ""))).resolve() != auth_path:
        raise ValueError("Wan authority differs from the active runtime authority")
    batch._authority(authority, job, sha(job_path))
    start = authority.get("allocation_started_at")
    deadline = context.get("original_deadline")
    if type(start) not in (int, float) or type(deadline) not in (int, float) or not math.isfinite(start) or deadline != start + job["wall_seconds"]:
        raise ValueError("Actual original allocation clock required; no renewed deadline")
    if deadline - time.time() <= batch.EXPORT_RESERVE:
        raise ValueError("Original Wan allocation has no execution time remaining")
    output = _inside(spec["output_dir"], workspace)
    if output.exists():
        raise ValueError("Existing Wan attempt is preserved; this adapter never retries or resumes")
    batch.unpack_inputs(inputs, output, sha(inputs))
    if (output / "job.json").read_bytes() != job_path.read_bytes():
        raise ValueError("Wan input archive differs from exact bound job")
    batch.begin(output, authority)
    try:
        batch.preflight(output)
        batch.setup(output)
        # One warm process uses the pinned environment installed by setup.
        _run([output / "venv/bin/python", SOFTWARE / "wan22/batch.py", "run", output, "--execute"],
             timeout=batch.remaining(output), log=output / "orchestrator-run.log")
    finally:
        archive = batch.export(output)
    rows = batch._ledger(output, job)
    blockers = ["One or more Wan shots did not finish; no automatic retry"] if len(rows) != len(job["scenes"]) or any(r["status"] != "TECHNICAL_PASS_REVIEW_PENDING" for r in rows) else []
    artifacts = [_bound(archive), *_files(output / "outputs")]
    artifacts.extend(_bound(p) for p in output.iterdir() if p.is_file() and p != archive)
    return _result(artifacts, blockers=blockers, outputs=_files(output / "outputs"),
                   scope="Actual pinned-model technical output; motion/semantic/acting acceptance pending")


def _wan_import(spec, context, workspace):
    _keys(spec, ("kind", "job", "archive", "output_dir"))
    job = _ref(spec["job"], workspace)
    archive = _ref(spec["archive"], workspace)
    output = _inside(spec["output_dir"], workspace)
    batch = _known_module("wan22/batch.py", "earnalism_fixed_wan_import")
    clips = batch.import_export(archive, output, sha(archive), job)
    expected = len(batch.validate(_json(job))["scenes"])
    return _result(_files(output), blockers=[] if len(clips) == expected else ["Not every named Wan shot has a verified technical output"],
                   outputs=clips, scope="Strict imported actual output; no motion acceptance")


def _science_name(spec):
    name = spec.get("science")
    if name not in SCIENCE:
        raise ValueError("Unsupported science mechanism; a tested topic adapter is required")
    return SCIENCE[name]


def _runtime_seconds(context, cap=1800):
    """Setup/render share the allocation's original clock; local CPU is bounded."""
    deadline = context.get("original_deadline_epoch", context.get("original_deadline"))
    if deadline is None:
        deadline = context.get("original_deadline")
    if deadline is None:
        return cap
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError("Invalid original render runtime deadline")
    # _run may spend 5 + 5 seconds terminating its process group. Reserve
    # that cleanup inside the original clock rather than extending authority.
    remaining = deadline - time.time() - 10
    if remaining <= 0:
        raise ValueError("Original render runtime deadline exhausted")
    return min(cap, remaining)


def _runtime_record(path, value):
    _write(path, value)
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _runtime_environment():
    # npm must not inherit account credentials, user configs or NODE_OPTIONS.
    return {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR")
            if key in os.environ}


def _render_runtime(context, workspace):
    """Prepare one owned, locked CPU renderer; never qualify media or retry setup."""
    context = dict(context)
    if context.get("original_deadline_epoch") is None and context.get("original_deadline") is None:
        context["original_deadline_epoch"] = time.time() + 1800
    _runtime_seconds(context)
    node = shutil.which("node")
    if not node:
        raise ValueError("Node runtime missing; automatic renderer setup cannot start")
    files = {name: SOFTWARE / name for name in (
        "package.json", "package-lock.json", "src/render-runtime.mjs", "src/prepare-render-runtime.mjs")}
    hashes = {name: sha(path) for name, path in files.items()}
    package = _json(files["package.json"])
    lock = _json(files["package-lock.json"])
    versions = {name: package["dependencies"][name] for name in (
        "remotion", "@remotion/bundler", "@remotion/renderer", "react", "react-dom")}
    if any(not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version)
           or lock.get("packages", {}).get("node_modules/" + name, {}).get("version") != version
           for name, version in versions.items()):
        raise ValueError("Renderer requires exact maintained package and lock versions")
    for entry in lock.get("packages", {}).values():
        if "resolved" in entry:
            url = urlsplit(entry["resolved"])
            if (url.scheme, url.netloc) != ("https", "registry.npmjs.org") or url.username or url.password:
                raise ValueError("Renderer lock contains a non-public-npm download")
    requested_browser = os.environ.get("EARNALISM_RENDER_BROWSER")
    if requested_browser and (not Path(requested_browser).is_absolute()
                              or not Path(requested_browser).is_file()
                              or not os.access(requested_browser, os.X_OK)):
        raise ValueError("Explicit renderer browser must be an existing absolute executable")
    identity = {"source_files": hashes, "requested_browser": requested_browser,
                "platform": sys.platform, "machine": platform.machine()}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    runtime = _inside(workspace / ".orchestrator/runtimes" / ("remotion-" + key), workspace)
    intent = runtime / "SETUP-INTENT.json"
    receipt = runtime / "RESULT.json"
    failure = runtime / "FAILED.json"
    env = {**_runtime_environment(), "EARNALISM_REMOTION_RUNTIME": str(runtime)}
    if requested_browser:
        env["EARNALISM_RENDER_BROWSER"] = requested_browser
    command = [node, files["src/prepare-render-runtime.mjs"], "--base", SOFTWARE,
               "--runtime", runtime, "--result", receipt]
    if runtime.exists():
        if (not intent.is_file() or intent.is_symlink() or _json(intent).get("identity") != identity
                or _json(intent).get("runtime_root") != str(runtime)):
            raise ValueError("Unowned renderer setup directory preserved; explicit reconciliation required")
        if failure.exists() or not receipt.is_file() or receipt.is_symlink():
            raise ValueError("Prior renderer setup failed or has unknown outcome; preserved without automatic retry")
        # Verify-only never downloads, repairs or rewrites a cached installation.
        _run([*command, "--verify-only"], cwd=SOFTWARE,
             timeout=_runtime_seconds(context), env=env)
    else:
        npm = shutil.which("npm")
        if not npm:
            raise ValueError("npm runtime missing; automatic renderer setup cannot start")
        runtime.mkdir(mode=0o700, parents=True, exist_ok=False)
        _runtime_record(intent, {"schema": "earnalism.render_runtime_intent.v1", "identity": identity,
            "runtime_root": str(runtime), "started_at": time.time(),
            "original_deadline_epoch": context.get("original_deadline_epoch", context.get("original_deadline")),
            "scope": "Locked local CPU package/browser setup only; no cloud allocation or media qualification"})
        try:
            for name in ("package.json", "package-lock.json"):
                with (runtime / name).open("xb") as stream:
                    stream.write(files[name].read_bytes())
            for name in ("npm-user.ini", "npm-global.ini"):
                (runtime / name).write_text("", encoding="utf-8")
            _run([npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund",
                  "--registry", "https://registry.npmjs.org", "--cache", runtime / "npm-cache",
                  "--userconfig", runtime / "npm-user.ini", "--globalconfig", runtime / "npm-global.ini"],
                 cwd=runtime, timeout=_runtime_seconds(context), log=runtime / "npm-ci.log", env=env)
            _run(command, cwd=SOFTWARE, timeout=_runtime_seconds(context),
                 log=runtime / "prepare-browser.log", env=env)
        except BaseException as exc:
            _runtime_record(failure, {"schema": "earnalism.render_runtime_failure.v1",
                "status": "FAILED_OR_UNKNOWN_NOT_RETRIED", "error_type": type(exc).__name__,
                "failed_at": time.time(), "intent": _bound(intent)})
            raise
    data = _json(receipt)
    browser = data.get("browser") or {}
    browser_path = Path(browser.get("path", ""))
    if (data.get("schema") != "earnalism.render_runtime.v1"
            or data.get("status") != "LOCAL_RENDER_PACKAGES_BROWSER_READY_NOT_RENDER_QUALIFIED"
            or data.get("runtime_root") != str(runtime) or data.get("versions") != versions
            or data.get("package_json_sha256") != hashes["package.json"]
            or data.get("package_lock_sha256") != hashes["package-lock.json"]
            or not browser_path.is_absolute() or not browser_path.is_file()
            or not os.access(browser_path, os.X_OK) or browser_path.stat().st_size != browser.get("bytes")
            or sha(browser_path) != browser.get("sha256")):
        raise ValueError("Renderer setup receipt or retained browser is stale; preserved without automatic retry")
    _runtime_seconds(context)
    return {**env, "EARNALISM_RENDER_BROWSER": str(browser_path)}, _bound(receipt)


def _visual_assets(spec, context, workspace):
    from scripts.book_av_render import validate
    _keys(spec, ("kind", "job"))
    path = _ref(spec["job"], workspace)
    raw = _json(path)
    _scan_refs(raw, workspace, path.parent)
    if raw.get("fixture_mode"):
        raise ValueError("Fixture assets cannot be selected for production")
    job = validate(path)
    for role, stage in (("manuscript", "source"), ("narration", "narration"),
                        ("timing", "timing"), ("scored_audio", "score")):
        _consume(context, stage, role, raw[role]["sha256"])
    assets = [_bound(Path(a["path"])) for a in job["assets_by_id"].values()]
    return _result([_bound(path), *assets],
        scope="Selected actual source-bound assets/rights checked; still/camera motion does not establish natural character acting")


def _science(spec, context, workspace):
    _keys(spec, ("kind", "science", "project"))
    module_name, prefix = _science_name(spec)  # Reject before any model/renderer call.
    manifest_path = _ref(spec["project"], workspace)
    project = _json(manifest_path)
    _keys(project, ("schema", "root", "files", "narration", "public_assets"))
    if project["schema"] != "earnalism.media-project.v1" or not isinstance(project["files"], list):
        raise ValueError("Bound actual science project required")
    root = _inside(project["root"], workspace, manifest_path.parent)
    refs = [_ref(ref, workspace, root) for ref in project["files"]]
    narration = _ref(project["narration"], workspace, root)
    _consume(context, "narration", "narration", sha(narration))
    required = {"timeline.json", "assembly-manifest.json", "voice-binding.json", "asr-review.json",
                "caption-quality.json", "narration.wav", "units.json"}
    if not {root / name for name in required}.issubset(refs) or narration != root / "narration.wav":
        raise ValueError("Complete actual science assembly/ASR/caption evidence must be hash-bound")
    timeline = _json(root / "timeline.json")
    assembly = _json(root / "assembly-manifest.json")
    source_root = _inside(assembly["source_root"], workspace, root)
    for name, digest in assembly["input_files"].items():
        _ref({"path": name, "sha256": digest}, workspace, source_root)
    if str(SOFTWARE) not in sys.path:
        sys.path.insert(0, str(SOFTWARE))
    validation_module = importlib.import_module(module_name + (".pipeline" if module_name == "rainbow" else ".finish"))
    validation_module.validate_inputs(root)  # Does not call the old score composer.
    if len(set(refs)) != len(refs):
        raise ValueError("Duplicate science project input")
    for name in ("props.json", "shorts-props.json", "clean-shorts-props.json"):
        if root / name not in refs:
            raise ValueError("Every actual-audio science props file must be hash-bound")
        props = _json(root / name)
        _scan_refs(props, workspace, root)
        # Existing topic renderers validate their exact scene/mark contracts.
        if not props.get("scenes") or props.get("outro") is not True:
            raise ValueError("Actual complete science timeline and approved END required")
        if props.get("scenes") != timeline.get("scenes") or props.get("duration") != timeline.get("duration"):
            raise ValueError("Science props differ from the bound actual-audio timeline")
    probe = _json_probe(narration)
    seconds = float(probe["format"]["duration"])
    if abs(seconds - float(timeline["duration"])) > .04:
        raise ValueError("Science actual narration duration differs from the bound timeline")
    public_assets = _inside(project["public_assets"], workspace, root)
    public_files = [p for p in public_assets.rglob("*") if p.is_file()]
    if not public_files or not set(public_files).issubset(refs):
        raise ValueError("Every private rendering public asset must be hash-bound")
    logo = public_assets / "brand-sting/production-lockup.png"
    if not logo.is_file() or sha(logo) != "951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919":
        raise ValueError("Exact canonical full Earnalism lockup required")
    # A non-Colab CPU render still gets one bounded setup + rendering clock.
    render_context = dict(context)
    if context.get("original_deadline_epoch") is None and context.get("original_deadline") is None:
        render_context["original_deadline_epoch"] = time.time() + 1800
    env, runtime_receipt = _render_runtime(render_context, workspace)
    env["EARNALISM_RENDER_PUBLIC"] = str(public_assets)
    if module_name in {"sky_colour", "rainbow"}:
        _run(["node", SOFTWARE / module_name / "render-batch.mjs", root, "--body-only"], cwd=SOFTWARE,
             timeout=_runtime_seconds(render_context), log=root / "orchestrator-render.log", env=env)
    else:
        body_props = root / "orchestrator-body-props"
        body_props.mkdir(exist_ok=False)
        for fmt, props, composition in (("landscape", "props.json", prefix + "Landscape"),
                                        ("shorts", "shorts-props.json", prefix + "Shorts"),
                                        ("clean-shorts", "clean-shorts-props.json", prefix + "CleanShorts")):
            _write(body_props / props, {**_json(root / props), "outro": False})
            _run(["node", SOFTWARE / module_name / "render.mjs", body_props / props,
                  root / fmt / "animation.mp4", composition], cwd=SOFTWARE,
                 timeout=_runtime_seconds(render_context), log=root / ("orchestrator-render-" + fmt + ".log"), env=env)
    if any(sha(p) != ref["sha256"] for p, ref in zip(refs, project["files"])):
        raise ValueError("Science source inputs changed while rendering")
    outputs = [_bound(root / fmt / "animation.mp4") for fmt in ("landscape", "shorts", "clean-shorts")]
    return _result(outputs, science=spec["science"], body_only=True, runtime_receipt=runtime_receipt,
        scope="Actual silent topic-specific body animations; final compositor must append exact bound END and shared soundtrack")


def _compose(spec, context, workspace):
    from scripts.book_av_render import render
    _keys(spec, ("kind", "job", "output_dir"), ("science", "score_plan"))
    if spec["kind"] == "science-finish":
        _science_name(spec)
        plan_ref = spec.get("score_plan") or (((context.get("upstream") or {}).get("score") or {}).get("details") or {}).get("bindings", {}).get("score_plan")
        plan_path = _ref(plan_ref, workspace)
        _consume(context, "score", "score_plan", sha(plan_path))
        _require_continuous(_json(plan_path))
    elif "science" in spec:
        raise ValueError("Science field requires the finite science-finish adapter")
    path = _ref(spec["job"], workspace)
    job = _json(path)
    _scan_refs(job, workspace, path.parent)
    if job.get("fixture_mode") or job.get("manuscript", {}).get("language") != context["language"]:
        raise ValueError("Real language-bound composition required")
    for role, stage in (("manuscript", "source"), ("narration", "narration"),
                        ("timing", "timing"), ("scored_audio", "score")):
        _consume(context, stage, role, job[role]["sha256"])
    for asset in job.get("assets", []):
        _consume(context, "visuals", "visual", asset["sha256"])
    if spec["kind"] == "science-finish" and any(a.get("kind") != "video" for a in job.get("assets", [])):
        raise ValueError("Science finishing requires actual topic animation assets")
    output = _inside(spec["output_dir"], workspace)
    report = render(path, output)
    scored = _ref({k: job["scored_audio"][k] for k in ("path", "sha256")}, workspace, path.parent)
    return _result(_files(output), bindings={"scored_audio": _bound(scored),
        "outputs": [_bound(Path(item["path"])) for item in report["outputs"]]},
        render_report=_bound(output / "render-report.json"),
        scope="Actual full source-bound composition; source PCM/END and shared AAC checked; listening/acting review pending")


def _retained(spec, context, workspace, check=False):
    if str(SOFTWARE) not in sys.path:
        sys.path.insert(0, str(SOFTWARE))
    from audiobook_visuals import pipeline
    if check:
        _keys(spec, ("kind", "project"))
        path = _ref(spec["project"], workspace)
        if path.name != "manifest.json":
            raise ValueError("Retained-audio check requires its exact output manifest.json")
        manifest = _json(path)
        output = path.parent
        _scan_refs(manifest, workspace, output)
        compiled = _json(output / "compiled.json")
        _scan_refs(compiled, workspace, output)
        _inside(compiled["audio_path"], workspace, output)
        report = pipeline.check(output)
        return _result(_files(output), report=report)
    _keys(spec, ("kind", "plan", "output_dir"))
    path = _ref(spec["plan"], workspace)
    data = _json(path)
    _scan_refs(data, workspace, path.parent)
    _consume(context, "narration", "narration", data["audio"]["sha256"])
    output = _inside(spec["output_dir"], workspace)
    report = pipeline.render(path, output)
    return _result(_files(output), report=report,
        scope="Private retained-audio illustrated storyboard; not proof of premium character animation")


def _review(spec, context, workspace):
    from scripts.release_acceptance import measure_audiovisual
    _keys(spec, ("kind", "manifest", "render_report", "output_dir"))
    path = _ref(spec["manifest"], workspace)
    report_path = _ref(spec["render_report"], workspace)
    manifest = _json(path)
    _scan_refs(manifest, workspace, path.parent)
    _consume(context, "compose", "render_report", sha(report_path))
    output = _inside(spec["output_dir"], workspace)
    output.mkdir(parents=True, exist_ok=False)
    # Stage references are workspace-relative; the existing evaluator resolves
    # its descriptor relative to the nested manifest's own directory.
    report = measure_audiovisual(manifest, path.parent, _bound(report_path))
    _write(output / "technical-review.json", report)
    return _result(_files(output), scope="Actual existing technical measurement only; full listening/AV remains separate")


def _release(spec, context, workspace):
    from scripts.produce_release import evaluate
    _keys(spec, ("kind", "manifest", "output_dir"), ("reader_approval", "audio_approval", "science"))
    if spec["kind"] == "science-release":
        _science_name(spec)
    path = _ref(spec["manifest"], workspace)
    manifest = _json(path)
    _scan_refs(manifest, workspace, path.parent)
    if "audiovisual" not in manifest:
        raise ValueError("An explicit complete audiovisual manifest is required; audio-only readiness is insufficient")
    if manifest.get("audiovisual", {}).get("fixture_mode"):
        raise ValueError("Fixture media cannot qualify for release")
    av = manifest["audiovisual"]
    for role, stage in (("manuscript", "source"), ("narration", "narration"),
                        ("timing", "timing"), ("scored_audio", "score")):
        _consume(context, stage, role, (av.get("files", {}).get(role) or {}).get("sha256"))
    for delivered in av.get("outputs", []):
        _consume(context, "compose", "output", delivered.get("sha256"))
    approvals = [_ref(spec[key], workspace) if key in spec else None for key in ("reader_approval", "audio_approval")]
    report = evaluate(manifest, path.parent, *approvals)
    output = _inside(spec["output_dir"], workspace)
    output.mkdir(parents=True, exist_ok=False)
    _write(output / "release-evaluation.json", report)
    ready = report.get("release_status") == "READY_FOR_GO_LIVE"
    return _result(_files(output), blockers=[] if ready else ["Existing release governor retains unresolved gates"],
        release_status=report["release_status"], eligible_for_separate_release=ready,
        governor=report, evaluator="scripts.produce_release.evaluate", manifest=_bound(path),
        scope="Read-only existing release evaluation; never uploads or publishes")


def run_stage(stage, spec, context):
    """Execute one known action; return real artifacts or concrete truthful blockers."""
    try:
        if stage not in KINDS or not isinstance(spec, dict) or spec.get("kind") not in KINDS[stage]:
            raise ValueError("Unknown fixed media stage/kind")
        if context.get("language") not in {"en", "bn"}:
            raise ValueError("Explicit en/bn language required")
        workspace = Path(context["workspace"]).resolve()
        if not workspace.is_dir() or any((p / ".git").exists() for p in (workspace, *workspace.parents)):
            raise ValueError("Existing private workspace outside git is required")
        if "repo_root" in context and Path(context["repo_root"]).resolve() != ROOT:
            raise ValueError("Adapter repository differs from the running pinned source")
        spec = dict(spec)
        if "output_dir" not in spec and context.get("output_dir") and stage in {"score", "compose", "review", "release-ready"} | ({"visuals"} if spec["kind"] in {"wan-batch", "wan-import"} else set()):
            spec["output_dir"] = str(context["output_dir"])
        if stage == "source": return _source(spec, context, workspace)
        if stage == "timing": return _timing(spec, context, workspace)
        if stage == "score": return _score(spec, context, workspace)
        if stage == "visuals":
            return {"wan-batch": _wan, "wan-import": _wan_import, "science-animation": _science,
                    "source-bound-assets": _visual_assets}[spec["kind"]](spec, context, workspace)
        if spec["kind"] == "retained-audio-layout": return _retained(spec, context, workspace)
        if spec["kind"] == "retained-audio-review": return _retained(spec, context, workspace, check=True)
        if stage == "compose": return _compose(spec, context, workspace)
        if stage == "review": return _review(spec, context, workspace)
        return _release(spec, context, workspace)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as exc:
        artifacts = []
        if isinstance(spec, dict) and spec.get("output_dir") and context.get("workspace"):
            try:
                output = _inside(spec["output_dir"], Path(context["workspace"]).resolve())
                if output.is_dir(): artifacts = _files(output)
            except (OSError, ValueError):
                pass
        return _result(artifacts, blockers=[str(exc)], failure_type=type(exc).__name__)


def _json_probe(path):
    return json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]).stdout)
