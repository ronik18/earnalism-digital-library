"""Bounded fresh-runtime recovery after a verified incomplete narration transfer.

Preparation is inert: it neither connects nor runs a model. The prior successful
attempts remain historical facts, not reusable audio. New job-local attempts and
seeds stay truthful and are counted in addition to the known historical starts.
The runtime deadline and complete-transfer preflight must already exist; this
adapter never starts or extends the shutdown guard.
"""
from pathlib import Path
import argparse
import ast
import base64
import hashlib
import json
import os
import re
import tempfile

RUNTIME_ROOT = "/content/earnalism-thermal-touch-v2-recovery"
PRIOR_ARCHIVE_SHA256 = "5570175b91d205ee3c1018b656f11ffb9466b446c57f9b1b2e241b89c88b136b"
PRIOR_ARCHIVE_BYTES = 6626431
WORKER_SHA256 = "55500c69d0529ded866c744d5242d1c9320625bece8eb56958b8086948e2beeb"
BASELINE_SHA256 = "2ba56e871bfecca948d331a9e0e712155b376ef745b65448db359ee755e1a215"
ASR_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
PLAN_SCHEMA = "earnalism.thermal.recovery.plan.v1"
OBSERVATION_SCHEMA = "earnalism.thermal.recovery.observation.v1"


class RecoveryError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def load(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def validate_plan(plan, units=None, baseline=None):
    require(plan.get("schema") == PLAN_SCHEMA and plan.get("runtime_root") == RUNTIME_ROOT and
            plan.get("state") == "PREPARED_ONLY_NO_RECOVERY_RUN", "Wrong bounded recovery plan")
    require(plan.get("worker_sha256") == WORKER_SHA256 and plan.get("baseline_sha256") == BASELINE_SHA256 and
            plan.get("asr_model_revision") == ASR_REVISION, "Critical recovery recipe pin changed")
    history = plan.get("historical_transfer", {})
    failure = history.get("record", {})
    require(history.get("source_archive_sha256") == PRIOR_ARCHIVE_SHA256 and
            history.get("source_archive_bytes") == PRIOR_ARCHIVE_BYTES and
            failure.get("source_archive_sha256") == PRIOR_ARCHIVE_SHA256 and
            failure.get("source_archive_bytes") == PRIOR_ARCHIVE_BYTES and
            failure.get("original_job_units") == 6 and failure.get("original_model_attempts_per_unit") == 1 and
            failure.get("local_archive_complete") is False and failure.get("aligned_export_complete") is True and
            failure.get("shutdown_guard_released_original_runtime") is True,
            "Historical successful attempts/incomplete transfer cannot be reset")
    require(plan.get("attempt_cap_per_unit") == 3 and plan.get("max_new_attempts_per_unit") == 2,
            "Recovery budget must remain two new starts within the three-start total cap")
    rows = plan.get("units", [])
    require(len(rows) == 6 and len({r.get("id") for r in rows}) == 6, "Recovery needs six unique units")
    for row in rows:
        require(row.get("known_historical_attempts_started") == 1 and row.get("new_attempt_budget") == 2 and
                row.get("known_historical_attempts_started") + row.get("new_attempt_budget") <= 3 and
                row.get("new_attempts_observed") is None, "Prior starts were erased or recovery cap exceeded")
    require(plan.get("publication_approved") is False and plan.get("new_recording_listening") == "PENDING" and
            plan.get("no_purchases") is True, "Recovery is private compute preparation only")
    if units is not None:
        require([r["id"] for r in rows] == [u["id"] for u in units], "Recovery thought units changed")
        require(plan["units_object_sha256"] == hashlib.sha256(canonical(units).encode()).hexdigest(),
                "Recovery script/anchors changed")
    if baseline is not None:
        require(plan["baseline_object_sha256"] == hashlib.sha256(canonical(baseline).encode()).hexdigest(),
                "Recovery B recipe changed")
    return plan


def observation(plan, journal_raw):
    """Count real started events, including unsuccessful/interrupted inference."""
    validate_plan(plan)
    if isinstance(journal_raw, str):
        journal_raw = journal_raw.encode()
    rows = {r["id"]: r for r in plan["units"]}
    starts = {sid: [] for sid in rows}
    for line in journal_raw.decode().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") != "attempt_started":
            continue
        sid, number = event.get("segment_id"), event.get("attempt")
        require(sid in rows and isinstance(number, int) and not isinstance(number, bool) and
                1 <= number <= rows[sid]["new_attempt_budget"], "Unaccounted/out-of-budget recovery start")
        require(number not in starts[sid], "Duplicate new recovery attempt start")
        starts[sid].append(number)
    units = []
    for sid, row in rows.items():
        numbers = sorted(starts[sid])
        require(numbers == list(range(1, len(numbers) + 1)), "Missing recovery start ledger entry")
        total = row["known_historical_attempts_started"] + len(numbers)
        require(total <= plan["attempt_cap_per_unit"], "Combined historical/new attempt cap exceeded")
        units.append({"id": sid, "known_historical_attempts_started": row["known_historical_attempts_started"],
                      "new_attempt_numbers_started": numbers, "combined_known_starts": total,
                      "unused_new_attempt_budget": row["new_attempt_budget"] - len(numbers)})
    return {"schema": OBSERVATION_SCHEMA, "plan_object_sha256": hashlib.sha256(canonical(plan).encode()).hexdigest(),
            "plan": plan, "journal_sha256": hashlib.sha256(journal_raw).hexdigest(), "units": units,
            "complete_start_ledger_present": True, "new_recording_listening": "PENDING", "publication_approved": False,
            "note": "New job-local numbering is retained. Historical v1 success does not become a new cached "
                    "recording or listening approval. Interrupted starts consume the budget."}


def retain_observation(runtime_root, result_root):
    """Called by the real exporter after worker completion/failure, before ZIP."""
    runtime_root, result_root = Path(runtime_root), Path(result_root)
    plan = load(runtime_root / "recovery-accounting.json")
    journal = result_root / "logs/qwen.jsonl"
    require(journal.is_file(), "Recovery export requires the actual worker start ledger")
    result = observation(plan, journal.read_bytes())
    target = result_root / "recovery-accounting.json"
    if target.exists():
        require(load(target) == result, "Prior recovery observation changed: preserve prior export/ledger")
    else:
        write_new(target, result)
    return result


def validate_observation(actual, plan, journal_raw, job, units, metadata):
    validate_plan(plan, units)
    require(actual == observation(plan, journal_raw), "Recovery counts/ledger/plan binding differ")
    require(job.get("max_attempts") == 2, "Recovery worker job exceeds two-new-attempt budget")
    segments = job.get("segments", [])
    require([s.get("segment_id") for s in segments] == [u["id"] for u in units], "Recovery job units differ")
    lookup = {r["id"]: r for r in actual["units"]}
    for unit, segment in zip(units, segments):
        sid = unit["id"]
        require(segment.get("text") == unit["text"] and segment.get("speaker") == "Ryan", "Recovery job script/voice changed")
        require(segment.get("output_path") == f"{RUNTIME_ROOT}/result/raw/{sid}.wav", "Recovery output escaped isolated run")
        record = metadata[sid]
        selected = record.get("selected_attempt")
        attempts = lookup[sid]["new_attempt_numbers_started"]
        require(selected in attempts and 1 <= selected <= 2 and attempts,
                "Recovery source has no budgeted real start")
        known = [a.get("attempt") for a in record.get("attempts", [])]
        require(len(known) == len(set(known)) and set(known) <= set(attempts), "Source attempts disagree with recovery ledger")
        require(record["settings"]["seed_base"] == segment.get("seed") and
                record["settings"]["instruct"] == segment.get("instruct"), "Recovery voice controls diverged from job")
    return actual


def verify_imported(root, units, baseline):
    """Bind recovery counts to assembly without changing the speech/ASR pins."""
    root = Path(root)
    plan_file = root / "recovery-accounting.json"
    observed_file = root / "narration-transfer/recovery-observation.json"
    is_recovery = plan_file.exists() or observed_file.exists() or "v2-recovery" in root.name
    if not is_recovery:
        return {}, None
    require(plan_file.is_file() and observed_file.is_file(), "Recovery source is missing its bounded attempt accounting")
    plan = load(plan_file)
    validate_plan(plan, units, baseline)
    paths = [plan_file, observed_file, root / "narration-transfer/recovery-qwen.jsonl",
             root / "narration-transfer/recovery-job.json", root / "recovery-evidence/prior-transfer-failure.json"]
    require(all(p.is_file() for p in paths), "Recovery historical/new worker evidence incomplete")
    require(sha(paths[-1]) == plan["historical_transfer"]["record_sha256"] and
            load(paths[-1]) == plan["historical_transfer"]["record"], "Prior recovery evidence changed")
    actual = validate_observation(load(observed_file), plan, paths[2].read_bytes(), load(paths[3]), units,
                                  {u["id"]: load(root / "imported/raw" / f"{u['id']}.wav.json") for u in units})
    receipt = load(root / "transfer-receipt.json")
    require(receipt.get("recovery_observation_sha256") == sha(observed_file) and
            receipt.get("recovery_accounting") == actual, "Transfer receipt omitted/changed recovery accounting")
    return {str(p.relative_to(root)): sha(p) for p in paths}, actual


def prepared_payload(folder):
    # Reuse the reviewed inert builder in a temporary folder; never alter v1.
    try:
        from .build_colab import build
    except ImportError:
        from build_colab import build
    with tempfile.TemporaryDirectory(prefix="thermal-recovery-build-") as temporary:
        temporary = Path(temporary)
        (temporary / "units.json").write_bytes((Path(folder) / "units.json").read_bytes())
        build(temporary)
        launch = (temporary / "colab-launch.py").read_text()
    tree = ast.parse(launch)
    encoded = next(node.args[0].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "b64decode")
    payload = json.loads(base64.b64decode(encoded))
    episode = payload["software"]["episode.py"]
    episode = episode.replace("earnalism-thermal-touch-v1", "earnalism-thermal-touch-v2-recovery")
    episode = episode.replace("'thermal-touch-v1'", "'thermal-touch-v2-recovery'")
    require(episode.count("'max_attempts':3") == 1, "Reviewed worker adapter changed")
    episode = episode.replace("'max_attempts':3", "'max_attempts':2")
    for kind in ("speech", "aligned", "partial"):
        episode = episode.replace(f"thermal-touch-{kind}.zip", f"thermal-touch-recovery-{kind}.zip")
    episode = episode.replace("ROOT=Path(", "from recovery import retain_observation\nROOT=Path(", 1)
    episode = episode.replace(" def export(name):\n", " def export(name):\n  retain_observation(ROOT,OUT)\n", 1)
    needle = "  # A partial export is explicitly partial, retains every completed file and attempt record.\n"
    require(needle in episode, "Reviewed partial export adapter changed")
    episode = episode.replace(needle, needle + "  retain_observation(ROOT,OUT)\n", 1)
    payload["software"]["episode.py"] = episode
    payload["software"]["recovery.py"] = Path(__file__).read_text()
    payload["recovery"] = load(Path(folder) / "recovery-accounting.json")
    payload["prior_failure_raw"] = (Path(folder) / "recovery-evidence/prior-transfer-failure.json").read_text()
    return payload


def launch_source(payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    encoded, digest = base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()
    source = f'''# Private bounded recovery. Safe Run All never authorizes/model-runs.
RUN_THERMAL_TOUCH_RECOVERY = False
EXISTING_COMPUTE_ALLOWED = False
FREE_RUNTIME_CONFIRMED = False
if not RUN_THERMAL_TOUCH_RECOVERY:
 print('THERMAL_RECOVERY_DISABLED: first verify a complete bounded transfer; retain the fixed deadline.')
else:
 if not (EXISTING_COMPUTE_ALLOWED or FREE_RUNTIME_CONFIRMED):
  raise RuntimeError('No scoped compute authorization.')
 import pathlib,json,subprocess,sys,time,hashlib,base64,os
 deadline=globals().get('THERMAL_RUNTIME_DEADLINE')
 if not isinstance(deadline,(int,float)) or deadline-time.time()<=60 or 'thermal_touch_shutdown_guard' not in globals():
  raise RuntimeError('Fixed original runtime deadline/guard required; never restart or extend it.')
 preflight=globals().get('THERMAL_TRANSFER_PREFLIGHT',{{}})
 if not (preflight.get('complete_file_verified_locally') is True and preflight.get('bounded_output_verified') is True and preflight.get('bytes',0)>={PRIOR_ARCHIVE_BYTES} and preflight.get('runtime_deadline')==deadline and len(preflight.get('sha256',''))==64):
  raise RuntimeError('Complete-file bounded transfer preflight must pass before any generation.')
 ROOT=pathlib.Path({RUNTIME_ROOT!r});ROOT.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode({encoded!r})
 assert hashlib.sha256(raw).hexdigest()=={digest!r}
 package=json.loads(raw)
 soft=ROOT/'software';soft.mkdir(exist_ok=True)
 for name,text in package['software'].items():
  p=soft/name
  if p.exists() and p.read_text()!=text:raise RuntimeError('Preserve existing recovery software: '+name)
  if not p.exists():p.write_text(text)
 for name,value in [('units.json',package['units']),('baseline-job.json',package['baseline']),('recovery-accounting.json',package['recovery'])]:
  p=ROOT/name
  if p.exists() and json.loads(p.read_text())!=value:raise RuntimeError('Preserve existing recovery job/accounting: '+name)
  if not p.exists():p.write_text(json.dumps(value,indent=2))
 evidence=ROOT/'recovery-evidence';evidence.mkdir(exist_ok=True)
 p=evidence/'prior-transfer-failure.json'
 if p.exists() and p.read_text()!=package['prior_failure_raw']:raise RuntimeError('Prior failure record changed')
 if not p.exists():p.write_text(package['prior_failure_raw'])
 pidfile=ROOT/'process.json'
 if pidfile.exists():
  old=json.loads(pidfile.read_text())
  try:os.kill(old['pid'],0)
  except ProcessLookupError:pass
  else:raise RuntimeError('Existing process still present; inspect it instead of duplicating recovery.')
 if time.time()>=deadline:raise RuntimeError('Fixed runtime deadline reached; do not start.')
 log=open(ROOT/'console.log','a')
 process=subprocess.Popen([sys.executable,str(soft/'episode.py')],stdout=log,stderr=subprocess.STDOUT)
 pidfile.write_text(json.dumps({{'pid':process.pid,'started':time.time(),'payload_sha256':{digest!r},'fixed_runtime_deadline':deadline,'transfer_preflight':preflight,'max_new_attempts_per_unit':2,'known_historical_starts_per_unit':1}}))
 print('THERMAL_RECOVERY_STARTED',process.pid,'fixed preflight deadline retained; total attempts <=3; private only')
'''
    return source, digest


def prepare(source_root, destination, failure_path, chunks_dir, authorization_path):
    try:
        from . import assemble
    except ImportError:
        import assemble
    source_root, destination = Path(source_root).resolve(), Path(destination).resolve()
    failure_path, chunks_dir, authorization_path = Path(failure_path).resolve(), Path(chunks_dir).resolve(), Path(authorization_path).resolve()
    require(not os.path.lexists(destination), "Recovery folder already exists; preserve it")
    units, baseline = load(source_root / "units.json"), load(source_root / "baseline-job.json")
    assemble.validate_units(units)
    assemble.validate_baseline(baseline)
    require(sha(assemble.PUBLISHED_B_ROOT / "baseline-job.json") == BASELINE_SHA256 and
            sha(Path(__file__).resolve().parents[1] / "vendor/qwen_worker.py") == WORKER_SHA256,
            "Original B/worker pins changed")
    failure = load(failure_path)
    chunks = []
    for index in failure.get("local_verified_chunks", []):
        path = chunks_dir / f"{index:03}.bin"
        require(path.is_file(), "Previously verified local chunk is missing")
        chunks.append({"index": index, "path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)})
    require([c["index"] for c in chunks] == [0, 1, 2] and
            sum(c["bytes"] for c in chunks) == failure.get("local_verified_bytes") == 1572864,
            "Incomplete source transfer evidence changed")
    authorization = load(authorization_path)
    require(authorization.get("owner_answer") == "Allow existing compute; no purchases" and
            authorization.get("purchases") is False, "Existing owner compute scope is not established")
    plan = {"schema": PLAN_SCHEMA, "state": "PREPARED_ONLY_NO_RECOVERY_RUN", "runtime_root": RUNTIME_ROOT,
            "worker_sha256": WORKER_SHA256, "baseline_sha256": BASELINE_SHA256,
            "baseline_object_sha256": hashlib.sha256(canonical(baseline).encode()).hexdigest(),
            "units_sha256": sha(source_root / "units.json"),
            "units_object_sha256": hashlib.sha256(canonical(units).encode()).hexdigest(),
            "asr_model_revision": ASR_REVISION, "attempt_cap_per_unit": 3, "max_new_attempts_per_unit": 2,
            "units": [{"id": u["id"], "known_historical_attempts_started": 1, "new_attempt_budget": 2,
                       "new_attempts_observed": None} for u in units],
            "historical_transfer": {"record_path": str(failure_path), "record_sha256": sha(failure_path),
                                    "record": failure, "source_archive_sha256": PRIOR_ARCHIVE_SHA256,
                                    "source_archive_bytes": PRIOR_ARCHIVE_BYTES, "local_chunks": chunks,
                                    "full_archive_available_locally": False, "accepted_audio": False},
            "compute_scope": {"record_path": str(authorization_path), "record_sha256": sha(authorization_path),
                              "owner_answer": authorization["owner_answer"],
                              "new_guard_or_deadline_extension": False},
            "transfer_preflight": "PENDING_COMPLETE_BOUNDED_FILE_TRANSFER_BEFORE_GENERATION",
            "no_purchases": True, "new_recording_listening": "PENDING", "publication_approved": False}
    validate_plan(plan, units, baseline)
    destination.mkdir(parents=True)
    (destination / "recovery-evidence").mkdir()
    originals = {name: sha(source_root / name) for name in ("units.json", "baseline-job.json", "sources.json")}
    for name in originals:
        with (destination / name).open("xb") as handle:
            handle.write((source_root / name).read_bytes())
    with (destination / "recovery-evidence/prior-transfer-failure.json").open("xb") as handle:
        handle.write(failure_path.read_bytes())
    write_new(destination / "recovery-accounting.json", plan)
    payload = prepared_payload(destination)
    launch, payload_digest = launch_source(payload)
    status = f"from pathlib import Path\nROOT=Path({RUNTIME_ROOT!r})\nprint((ROOT/'status.json').read_text() if (ROOT/'status.json').exists() else 'Recovery not started')\nprint([(p.name,p.stat().st_size) for p in ROOT.glob('*.zip')])\n"
    download = f"from pathlib import Path\nfrom google.colab import files\np=Path({RUNTIME_ROOT!r})/'thermal-touch-recovery-aligned.zip'\nif not p.exists():raise RuntimeError('Aligned recovery export not complete; preserve any partial export.')\nfiles.download(str(p))\n"
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                             "language_info": {"name": "python"}, "accelerator": "GPU"},
                "cells": [{"cell_type": "markdown", "metadata": {}, "source": [
                    "# Earnalism thermal touch — bounded private recovery\n",
                    "Original v1 attempts/chunks remain intact. Two new starts per unit at most.\n",
                    "Disabled by default. Complete transfer preflight first; preserve the fixed shutdown deadline.\n"]},
                    *[{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                       "source": text.splitlines(True)} for text in (launch, status, download)]]}
    for name, text in (("colab-launch.py", launch), ("colab-status.py", status)):
        with (destination / name).open("x") as handle:
            handle.write(text)
    write_new(destination / "Earnalism_Everyday_Science_04_Recovery.ipynb", notebook)
    write_new(destination / "colab-payload.json", {"payload_sha256": payload_digest,
              "runtime_root": RUNTIME_ROOT, "disabled_by_default": True, "metered_authorization_default": False,
              "worker_sha256": WORKER_SHA256, "baseline_sha256": BASELINE_SHA256,
              "recovery_plan_sha256": sha(destination / "recovery-accounting.json"),
              "historical_starts_per_unit": 1, "max_new_attempts_per_unit": 2,
              "fixed_preflight_runtime_deadline_required": True, "shutdown_guard_restarted": False})
    require(all(sha(source_root / name) == digest for name, digest in originals.items()), "Protected v1 files changed")
    return {"root": str(destination), "payload_sha256": payload_digest,
            "state": "PREPARED_DISABLED_RECOVERY", "generation_started": False, "publication_approved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("failure_record", type=Path)
    parser.add_argument("chunks", type=Path)
    parser.add_argument("compute_authorization", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination, args.failure_record, args.chunks, args.compute_authorization), indent=2))
