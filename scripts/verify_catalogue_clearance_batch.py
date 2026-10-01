#!/usr/bin/env python3
"""Verify current held repairs independently of historical preparation snapshots."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.publication_manifest import validate_manifest
from backend.rights_decision_gate import evaluate_accepted_record, record_sha256
from datetime import datetime, timezone
from scripts.bengali_rights_package_validator import checksum_manifest_matches

def verify(root=ROOT,base='8be3926fd9fc4526dec66d51b64d8ca72b2d0035'):
    issues=[];slugs=set()
    names=subprocess.check_output(['git','diff','--name-only',base,'--','data/controlled_publications'],cwd=root,text=True).splitlines()
    names+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','data/controlled_publications'],cwd=root,text=True).splitlines()
    for name in names:
        parts=Path(name).parts
        if len(parts)>=4:slugs.add(parts[2])
    launch=json.loads((root/'data/controlled_launch.json').read_text());live=set(launch['live_approved_slugs'])
    for name in ('data/controlled_launch.json','data/catalog_exclusions.json','backend/data/rights_decision_registry.json'):
        if subprocess.check_output(['git','show',f'{base}:{name}'],cwd=root)!=(root/name).read_bytes():issues.append(f'Unexpected release authority change: {name}')
    statuses={}
    for slug in sorted(slugs):
        p=root/'data/controlled_publications'/slug
        if slug in live:issues.append(f'Live package modified: {slug}')
        manifest=json.loads((p/'publication_manifest.json').read_text())
        issues.extend(f'{slug}: {v}' for v in validate_manifest(manifest))
        if not checksum_manifest_matches(p):issues.append(f'{slug}: invalid checksum bundle')
        if manifest['reader_release']['exposed'] or manifest['audio_release']['exposed']:issues.append(f'{slug}: held preparation exposed a release')
        for chapter in json.loads((p/'public_book.json').read_text())['chapters']:
            chapter_path=p/'chapters'/f"{chapter['id']}.json"
            if not chapter_path.is_file():
                issues.append(f"{slug}/{chapter['id']}: missing canonical chapter")
                continue
            c=json.loads(chapter_path.read_text())
            if hashlib.sha256(c['content'].encode()).hexdigest()!=c['content_hash']:issues.append(f"{slug}/{chapter['id']}: content checksum mismatch")
        decision_path=p/'rights_decision.json'
        if decision_path.is_file():
            record=json.loads(decision_path.read_text())
            if record.get('status')=='ACCEPTED':
                components={name:hashlib.sha256((p/(name+'.json')).read_bytes()).hexdigest() for name in ('public_book','reader_manifest','source_evidence','approval_evidence','checksum_manifest','publication_manifest')}
                for name in record['components']:
                    path=p/(name+'.json')
                    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()!=record['components'][name]:issues.append(f'{slug}: stale accepted component {name}')
                for use,should_pass in (('reader_preview',True),('audio_stream',False)):
                    verdict=evaluate_accepted_record(record,edition_id=slug,operator_id='reo-enterprise',country='IN',country_trusted=True,use=use,required_components=components,accepted_records={record['decision_id']:record_sha256(record)},revoked_decision_ids=frozenset(),now=datetime.now(timezone.utc))
                    if verdict.passed!=should_pass:issues.append(f'{slug}: decision scope invalid for {use}: {verdict.reasons}')
        statuses[slug]=manifest['reader_release']['status']
    return {'result':'FAIL' if issues else 'PASS','changed_packages':len(slugs),'statuses':statuses,'issues':issues,'reader_exposed':False,'audio_exposed':False,'release_authority_unchanged':not any('authority' in v for v in issues)}
if __name__=='__main__':
    report=verify();print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(bool(report['issues']))
