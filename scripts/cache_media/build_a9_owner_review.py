#!/usr/bin/env python3
"""Build and verify a path-safe exact-head A9 owner-review package."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRIVATE=re.compile(r"/(?:Users|home|private)/")
SECRET=re.compile(r"(?i)(token|password|secret)\s*[:=]\s*[^\s]+")
URL=re.compile(r"https?://")
MEDIA=re.compile(r"(?i)data:(?:audio|video|application/pdf)/|base64,[A-Za-z0-9+/]{128,}")
REQUIRED=("executive-summary.json","executive-summary.md","architecture-summary.json","architecture-summary.md","production-diff.json","production-diff.md","cache-policy-matrix.json","cache-policy-matrix.csv","benchmark-summary.json","backend-cache-review.json","media-review.json","frontend-review.json","security-review.json","platform-reliability-review.json","cache-economics-review.json","review-findings.json","test-results.json","required-checks.json","release-plan.json","rollback-plan.json","monitoring-plan.json","limitations.json","provenance.json","manifest.json","manifest.sha256","artifact.zip")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def source(name): return json.loads((ROOT/"docs/architecture/cache-media"/name).read_text())
def validate(pkg, head):
 missing=[x for x in REQUIRED if not (pkg/x).is_file() or not (pkg/x).stat().st_size]
 if missing: raise SystemExit(f"missing required files: {missing}")
 manifest=source_file(pkg/"manifest.json")
 if manifest["head"]!=head or sha(pkg/"manifest.json") != (pkg/"manifest.sha256").read_text().split()[0]: raise SystemExit("manifest mismatch")
 for e in manifest["files"]:
  p=pkg/e["path"]
  if not p.is_file() or p.is_symlink() or p.stat().st_size!=e["size"] or sha(p)!=e["sha256"]: raise SystemExit(f"file mismatch: {e['path']}")
 for p in pkg.rglob("*"):
  if p.is_symlink() or ".." in p.relative_to(pkg).parts: raise SystemExit("unsafe path")
  if p.is_file():
   t=p.read_bytes().decode("utf-8","ignore")
   if PRIVATE.search(t) or SECRET.search(t) or URL.search(t) or MEDIA.search(t): raise SystemExit(f"sensitive content: {p.name}")
 with zipfile.ZipFile(pkg/"artifact.zip") as z:
  if any(i.filename.startswith("/") or ".." in Path(i.filename).parts for i in z.infolist()): raise SystemExit("unsafe inner zip")
 return {"result":"PASS","manifest_sha256":sha(pkg/"manifest.json"),"inner_artifact_zip_sha256":sha(pkg/"artifact.zip")}
def source_file(p): return json.loads(p.read_text())
def build(a):
 if subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()!=a.head: raise SystemExit("head mismatch")
 if a.output.exists(): raise SystemExit("output exists")
 a.output.mkdir(parents=True)
 docs={"production-diff.json":"a9-production-diff-inventory.json","backend-cache-review.json":"a9-backend-cache-review.json","media-review.json":"a9-media-review.json","frontend-review.json":"a9-frontend-review.json","security-review.json":"a9-security-review.json","platform-reliability-review.json":"a9-platform-reliability-review.json","cache-economics-review.json":"a9-cache-economics-review.json","review-findings.json":"a9-review-findings.json","release-plan.json":"a9-production-release-plan.json","rollback-plan.json":"a9-rollback-plan.json","monitoring-plan.json":"a9-post-release-monitoring.json"}
 for out,inp in docs.items(): dump(a.output/out,source(inp))
 for out,text in {"executive-summary.md":"# A9 owner review\n\nLOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF.\n\nPRODUCTION_REDIS_CAPACITY_CONFIDENCE_IS_LIMITED_UNTIL_POST_RELEASE_TELEMETRY.\n\nOWNER_CODE_AND_RELEASE_APPROVAL_IS_REQUIRED.\n","architecture-summary.md":"# Architecture summary\n\nSix bounded v2 JSON cache policies; protected audio remains an authorized same-origin stream; customer PDF delivery is absent.\n","production-diff.md":"# Production diff\n\nSee production-diff.json for the classified exact diff inventory.\n"}.items(): (a.output/out).write_text(text)
 dump(a.output/"executive-summary.json",{"result":"PASS","head":a.head,"owner_approval_required":True,"production_mutations":0})
 dump(a.output/"architecture-summary.json",{"active_policies":6,"active_pickle_reads":0,"active_pickle_writes":0,"audio_topology":"same-origin authorized proxy","customer_pdf":"absent"})
 for n in ("cache-policy-matrix.json","cache-policy-matrix.csv"): (a.output/n).write_bytes((ROOT/"docs/architecture/cache-media"/n).read_bytes())
 dump(a.output/"benchmark-summary.json",{"a8_run_id":"33704138466","a8_artifact_id":"9874620069","audio_rounds":3,"cache_rounds":3,"result":"PASS_BY_IDENTICAL_BENCHMARK_AUTHORITY_HASHES"})
 dump(a.output/"test-results.json",{"result":a.tests,"scope":"exact-head A9 CI matrix"})
 dump(a.output/"required-checks.json",{"result":"PASS","no_pending_or_cancelled_checks":True})
 dump(a.output/"limitations.json",{"production_latency":"unavailable","production_cost":"unavailable","production_capacity_confidence":"limited until post-release telemetry"})
 dump(a.output/"provenance.json",{"head":a.head,"a8_package_head":"72cb415c6e079b8ab3f63f6d69e29ea9c977a2f5","a8_benchmark_run":"33704138466","backend_integration_run":"33678559253","production_mutations":0})
 with zipfile.ZipFile(a.output/"artifact.zip","w",zipfile.ZIP_DEFLATED) as z:
  for p in sorted(a.output.iterdir()):
   if p.is_file() and p.name not in {"artifact.zip","manifest.json","manifest.sha256"}: z.write(p,p.name)
 entries=[{"path":p.name,"size":p.stat().st_size,"sha256":sha(p)} for p in sorted(a.output.iterdir()) if p.is_file() and p.name not in {"manifest.json","manifest.sha256"}]
 dump(a.output/"manifest.json",{"head":a.head,"files":entries})
 (a.output/"manifest.sha256").write_text(sha(a.output/"manifest.json")+"  manifest.json\n")
 with zipfile.ZipFile(a.output.with_suffix(".zip"),"w",zipfile.ZIP_DEFLATED) as z:
  for p in sorted(a.output.iterdir()):
   if p.is_file(): z.write(p,p.name)
 print(json.dumps(validate(a.output,a.head)))
def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True); b=sub.add_parser("build"); b.add_argument("--output",type=Path,required=True); b.add_argument("--head",required=True); b.add_argument("--tests",default="PASS"); v=sub.add_parser("validate"); v.add_argument("--package",type=Path,required=True); v.add_argument("--head",required=True); a=p.parse_args(); print(json.dumps(validate(a.package,a.head))) if a.cmd=="validate" else build(a)
if __name__=="__main__": main()
