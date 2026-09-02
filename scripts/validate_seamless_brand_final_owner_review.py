#!/usr/bin/env python3
"""Hard validator for the local PR344 final owner-review package."""
import argparse, hashlib, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"PENDING", "NOT RUN", "WORKFLOW RUNNING", "ARTIFACT NOT CREATED"}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())
def contains_forbidden(value):
    if isinstance(value, str): return value in FORBIDDEN
    if isinstance(value, dict): return any(contains_forbidden(item) for item in value.values())
    if isinstance(value, list): return any(contains_forbidden(item) for item in value)
    return False
def production_hash():
    files=[]
    for directory in [ROOT/'frontend/src', ROOT/'frontend/public']:
        for item in directory.rglob('*'):
            if item.is_file() and '__tests__' not in item.parts and '.test.' not in item.name and '.spec.' not in item.name: files.append(item)
    files.extend(ROOT/item for item in ['frontend/package.json','frontend/package-lock.json','frontend/vercel.json'])
    return hashlib.sha256(''.join(f'{sha(item)}  {item.relative_to(ROOT)}\n' for item in sorted(files)).encode()).hexdigest()
def need(condition, message, failures):
    if not condition: failures.append(message)
def scan(package):
    findings=[]
    patterns={'absolute private path':re.compile(r'(?:^|[\"\'\s])/(?:tmp|private(?:/tmp)?|Users)/'), 'sensitive value':re.compile(r'review@example\.invalid|access[_ -]?token|refresh[_ -]?token|owner@',re.I), 'raw media URL':re.compile(r'https?://[^\s\"\']*(?:audio|media|stream)[^\s\"\']*',re.I), 'protected Reader text':re.compile(r'PROTECTED_READER_TEXT')}
    for item in package.rglob('*'):
        if item.is_file() and item.suffix.lower() in {'.json','.html','.txt','.sha256'}:
            text=item.read_text(errors='ignore')
            for name, pattern in patterns.items():
                if pattern.search(text): findings.append(f'{name}: {item.relative_to(package)}')
    return findings
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--package',required=True); parser.add_argument('--allow-synthetic',action='store_true'); args=parser.parse_args()
    package=Path(args.package).resolve(); failures=[]
    required=['owner-review.html','owner-review.pdf','contact-sheet.png','executive-summary.json','visual-decision-checklist.json','route-inventory.json','state-manifest.json','cross-browser-selection-contract.json','final-evidence-inputs.json','article-stability-results.json','chromium-summary.json','firefox-summary.json','webkit-summary.json','browser-results.json','interaction-results.json','zoom-results.json','optical-readability-results.json','logo-integrity-results.json','brand-placement-results.json','static-snapshot-brand-results.json','route-surface-hashes.json','approval-carry-forward.json','accessibility-results.json','safety-results.json','package-statistics.json','provenance.json','manifest.json','manifest.sha256','artifact.zip']
    for name in required: need((package/name).is_file() and (package/name).stat().st_size>0, f'missing or empty {name}', failures)
    if failures: print(json.dumps({'FINAL_PACKAGE_VALIDATOR_RESULT':'FAIL','failures':failures})); raise SystemExit(1)
    executive, provenance, inputs, stats = [load(package/name) for name in ['executive-summary.json','provenance.json','final-evidence-inputs.json','package-statistics.json']]
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    need(provenance.get('package_generation_head')==current,'package head differs from checkout',failures); need(provenance.get('production_implementation_head'),'production implementation head missing',failures)
    need(executive.get('production_surface_sha256')==production_hash(),'production surface differs',failures); need(executive.get('canonical_logo_sha256')==sha(ROOT/'frontend/public/assets/brand/earnalism-brand-lockup.png'),'canonical logo differs',failures)
    need(inputs.get('production_surface_sha256')==executive.get('production_surface_sha256'),'input production hash differs',failures); need(inputs.get('canonical_logo_sha256')==executive.get('canonical_logo_sha256'),'input logo hash differs',failures)
    article=inputs.get('article_stability',{}).get('article_mobile',{})
    for browser, expected_count in [('webkit',10),('chromium',5),('firefox',5)]:
        item=article.get(browser,{})
        need((item.get('expected'),item.get('captured'),item.get('stable'))==(expected_count,expected_count,expected_count),f'{browser} Article stability evidence incomplete',failures)
    need(load(package/'article-stability-results.json')==inputs.get('article_stability'),'packaged Article stability evidence differs',failures)
    need(all(provenance.get('browsers',{}).get(name) for name in ['chromium','firefox','webkit']),'browser version missing',failures); need(all(provenance.get(key) for key in ['capture_tool_sha256','generator_sha256','validator_sha256']),'tool SHA missing',failures)
    expected=1 if args.allow_synthetic else 65
    chromium=load(package/'chromium-summary.json'); firefox=load(package/'firefox-summary.json'); webkit=load(package/'webkit-summary.json')
    need((chromium.get('expected_state_count'),chromium.get('captured_state_count'),chromium.get('stable_state_count'))==(expected,expected,expected),'Chromium evidence incomplete',failures)
    browser_expected=1 if args.allow_synthetic else 20
    for name,data in [('Firefox',firefox),('WebKit',webkit)]: need((data.get('expected_state_count'),data.get('captured_state_count'),data.get('stable_state_count'))==(browser_expected,browser_expected,browser_expected),f'{name} evidence incomplete',failures)
    need(load(package/'static-snapshot-brand-results.json').get('result')=='PASS','static evidence fails',failures); need(load(package/'route-surface-hashes.json').get('result')=='PASS','route hash evidence fails',failures); need(load(package/'interaction-results.json').get('result')=='PASS','interaction evidence fails',failures); need(load(package/'zoom-results.json').get('result')=='PASS','zoom evidence fails',failures); need(load(package/'optical-readability-results.json').get('result')=='PASS','optical evidence fails',failures)
    need(executive.get('rendered_ui_defects')==0,'rendered UI defects are nonzero',failures); need(executive.get('production_mutations')==0,'production mutations are nonzero',failures); need(not contains_forbidden(executive) and not contains_forbidden(inputs),'forbidden pending result appears',failures)
    need((package/'owner-review.pdf').read_bytes().startswith(b'%PDF'),'PDF signature fails',failures); need((package/'contact-sheet.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),'contact-sheet PNG signature fails',failures)
    html_text=(package/'owner-review.html').read_text(); refs=re.findall(r'<img[^>]+src="([^"]+)"',html_text)
    need(bool(refs) and all((package/ref).is_file() for ref in refs),'owner-review HTML image link fails',failures)
    manifest=load(package/'manifest.json'); need(sha(package/'manifest.json')==(package/'manifest.sha256').read_text().strip(),'manifest SHA mismatch',failures); entries=manifest.get('files',[]); need(bool(entries),'manifest is empty',failures)
    for entry in entries:
        item=package/entry['path']; need(not Path(entry['path']).is_absolute() and '..' not in Path(entry['path']).parts,'manifest path unsafe',failures); need(item.is_file() and item.stat().st_size==entry['bytes'] and sha(item)==entry['sha256'],'manifest entry mismatch',failures)
    try:
        with tempfile.TemporaryDirectory(prefix='pr344-package-validator-') as temp:
            output=Path(temp)
            with zipfile.ZipFile(package/'artifact.zip') as archive:
                for member in archive.infolist():
                    name=Path(member.filename); need(not name.is_absolute() and '..' not in name.parts and not member.is_dir(),'ZIP path traversal',failures)
                    if not member.is_dir():
                        target=output/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(archive.read(member))
            if (output/'manifest.json').is_file():
                extracted=load(output/'manifest.json')
                for entry in extracted.get('files',[]):
                    item=output/entry['path']; need(item.is_file() and sha(item)==entry['sha256'],'extracted manifest mismatch',failures)
            else: failures.append('ZIP extraction missing manifest')
    except (zipfile.BadZipFile, OSError) as exc: failures.append(f'ZIP extraction fails: {exc}')
    need(stats.get('zero_byte_required_file_count')==0,'zero-byte required file count differs',failures); need(stats.get('sensitive_data_finding_count')==0,'sensitive finding count differs',failures); need(stats.get('pdf_count',0)>=1 and stats.get('contact_sheet_bytes',0)>0,'package statistics incomplete',failures)
    findings=scan(package); need(not findings,'package scan finding: '+('; '.join(findings[:3])),failures)
    result='PASS' if not failures else 'FAIL'; print(json.dumps({'FINAL_PACKAGE_VALIDATOR_RESULT':result,'failures':failures})); raise SystemExit(0 if not failures else 1)
if __name__=='__main__': main()
