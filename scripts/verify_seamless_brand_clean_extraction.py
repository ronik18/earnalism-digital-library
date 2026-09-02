#!/usr/bin/env python3
"""Verify the immutable, manifest-governed inner owner-review extraction."""
import argparse, hashlib, json, os, stat, sys
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--package',required=True); parser.add_argument('--report-json',required=True); args=parser.parse_args()
    root=Path(args.package); failures=[]; unexpected=[]; missing=[]; hashes=[]; sizes=[]; unsafe=0
    manifest_path=root/'manifest.json'; stats_path=root/'package-statistics.json'; sha_path=root/'manifest.sha256'
    for item in (manifest_path,sha_path,stats_path):
        if not item.is_file(): failures.append(f'missing {item.name}')
    manifest={}; stats={}
    if not failures:
        manifest=json.loads(manifest_path.read_text()); stats=json.loads(stats_path.read_text())
        if digest(manifest_path)!=sha_path.read_text().strip(): failures.append('manifest SHA mismatch')
    entries={}
    for entry in manifest.get('files',[]):
        rel=entry.get('path',''); candidate=Path(rel)
        if candidate.is_absolute() or '..' in candidate.parts or not rel: unsafe+=1; continue
        entries[rel]=entry
    artifact=(root/'artifact.zip').exists()
    if artifact: failures.append('artifact.zip present in clean extraction')
    regular=[]; symlinks=0
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path=Path(base)/name
            mode=path.lstat().st_mode
            if stat.S_ISLNK(mode): symlinks+=1
            elif not stat.S_ISREG(mode) and not stat.S_ISDIR(mode): failures.append(f'non-regular filesystem entry: {path.relative_to(root)}')
        for name in files:
            path=Path(base)/name
            if path.is_file() and not path.is_symlink(): regular.append(path)
    observed={str(path.relative_to(root)).replace(os.sep,'/') for path in regular}
    for rel, entry in entries.items():
        path=root/rel
        if not path.is_file(): missing.append(rel); continue
        if path.stat().st_size != entry.get('bytes'): sizes.append(rel)
        if digest(path) != entry.get('sha256'): hashes.append(rel)
    unexpected=sorted(observed-set(entries)-{'manifest.json','manifest.sha256','package-statistics.json'})
    if missing or hashes or sizes or unexpected or symlinks or unsafe: failures.append('manifest-governed extraction mismatch')
    count=len(regular); total=sum(path.stat().st_size for path in regular)
    expected_count=stats.get('extracted_verification_file_count'); expected_bytes=stats.get('extracted_verification_total_bytes')
    if count != expected_count: failures.append('regular file count mismatch')
    if total != expected_bytes: failures.append('regular byte total mismatch')
    report={'schema_version':1,'result':'PASS' if not failures else 'FAIL','manifest_entry_count':len(entries),'observed_regular_file_count':count,'expected_regular_file_count':expected_count,'observed_total_bytes':total,'expected_total_bytes':expected_bytes,'count_delta':None if expected_count is None else count-expected_count,'byte_delta':None if expected_bytes is None else total-expected_bytes,'unexpected_file_paths':unexpected,'missing_manifest_paths':missing,'hash_mismatch_paths':hashes,'size_mismatch_paths':sizes,'artifact_zip_present':artifact,'symlink_count':symlinks,'unsafe_path_count':unsafe,'failures':failures}
    Path(args.report_json).write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report)); raise SystemExit(0 if not failures else 1)
if __name__=='__main__': main()
