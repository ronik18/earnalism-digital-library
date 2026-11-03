"""One exact Sredni Reader-only SOURCE_QA stage and guarded source restore.

No activation, cohort, playback grant, Mongo, provider or financial operation.
The immutable descriptor's downstream blockers remain unchanged.
"""
from __future__ import annotations
import argparse,base64,copy,json,shutil,tempfile
from pathlib import Path
from datetime import datetime
import audiobook_active_release_v2 as m
import sredni_scored_retained as scored
import sredni_scored_metadata as metadata
from publication_manifest import build_manifest,validate_manifest
from rights_decision_gate import record_sha256,load_production_registry,evaluate_accepted_record

SLUG='sredni-vashtar'
SOURCE='fdcfd2a238a8667549492119a94715d0f64bacc46812252ea2b116deca1bf50a'
MANUSCRIPT='f363729ab6b36e07f8b99f33ffd9405b5596a5d74f01c350ad2ddfaa84c0fc06'
DESCRIPTOR=scored.DESCRIPTOR_SHA
FIELD=metadata.FIELD
FILES=('public_book.json','reader_manifest.json','source_evidence.json','approval_evidence.json',
       'checksum_manifest.json','publication_manifest.json','rights_decision.json')
SNAPSHOT_SCHEMA='earnalism.sredni_reader_only_restore_snapshot.v1'
RESULT_SCHEMA='earnalism.sredni_private_source_transaction.v1'
# Actual immutable storage bytes, independently reviewed. Never derive a new
# accepted upload identity or substitute another title's synthetic receipts.
INPUTS={
 'package':('336ec7b7954375e8b8c35e350fac9565b835c62d22d63a430eb76d5f8e4c2a19',6544),
 'descriptor':('d2f09568772157b575b4f490afb7c250ee131f10055932a7fff47e98666e5e71',3331),
 'primary':('a04e0e49e58cdedfabf463a28bc1dee2412d4456efcf4773f83a8b923cf4edb4',3927),
 'replica':('8e887975fc5f0eb743de355abaeeeb0aa4d47e959287bff2c17b7f4eda85cd67',5474),
 'primary_manifest':('84a09fa7afc799357ea55be8f1eca7b13b1728946fc78a5f6437f40a9ea9e72b',1623),
 'replica_manifest':('86554014e57e700f818ed1566de5ca70b825f926ba7584a2cbef2b756ab5f0ae',2711),
}


def need(ok,message):
    if not ok:raise m.ReleasePointerError(message)


def digest(value):return m.sha256_bytes(m.canonical_json_bytes(value))


def _storage_input_path(value):
    name=str(Path(value).absolute())
    # Normalize only the actual macOS system alias. Linux /tmp is a real
    # directory and must remain /tmp; arbitrary aliases remain rejectable.
    if (name.startswith('/tmp/') and Path('/tmp').is_symlink()
            and Path('/tmp').resolve()==Path('/private/tmp')):
        name='/private/tmp/'+name[5:]
    return Path(name)


def load_inputs(paths):
    need(isinstance(paths,dict) and set(paths)==set(INPUTS),'Exact six Sredni storage input roles required')
    result={}
    for role,(expected,size) in INPUTS.items():
        # macOS /tmp is the documented system alias; every actual file or
        # non-system path component must still be nonsymlinked.
        path=_storage_input_path(paths[role])
        need(not any(x.is_symlink() for x in (path,*path.parents)) and path.is_file(),
             'Sredni storage inputs must be regular nonsymlink files')
        need(path.stat().st_size==size,'Sredni storage input size changed: '+role)
        raw=path.read_bytes()
        need(m.sha256_bytes(raw)==expected,'Sredni storage input bytes changed: '+role)
        result[role]=json.loads(raw)
    return result


def _context(root):
    c=m.load_mirrored_publication(root,SLUG);m._verify_controlled_checksums(c)
    need(SOURCE in m._controlled_hashes(c),'Controlled Sredni source changed')
    for name in FILES:
        need((c['dirs'][0]/name).read_bytes()==(c['dirs'][1]/name).read_bytes(),'Sredni source mirrors diverged')
    return c


def _reader_only(c):
    m._validate_reader_publication_truth(c,SLUG)
    book,reader,approval=c['public_book'],c['reader_manifest'],c['approval_evidence']
    need(book.get('audiobook_active_release')=={'status':'DISABLED_TEXT_READER_ONLY'}
         and 'audiobook_active_release' not in reader,'Exact Reader-only initial sentinel required')
    for doc in (book,reader):
        need(doc.get('audio_enabled') is False and doc.get('audiobook_enabled') is False,
             'Sredni ordinary audio must stay hidden')
        need(not doc.get(FIELD),'Sredni private stage already exists; reconcile without replay')
        for key in ('audiobook_legacy_release_descriptor_sha256','audiobook_release_descriptor_sha256',
                    'audiobook_package','audiobook_packages','audiobook_package_release_evidence',
                    'audiobook_public_package_approval','audiobook_assets','audiobook_new_title_package_canary'):
            need(not doc.get(key),'Sredni initial stage refuses existing release/package metadata: '+key)
        audio=doc.get('audiobook')
        need(not isinstance(audio,dict) or not audio.get('url'),'Sredni initial stage refuses legacy URL')
    need(approval.get('audiobook_enabled') is False
         and approval.get('audio_public_release')!='PUBLIC_AUDIO_RELEASE_APPROVED',
         'Sredni initial stage requires existing audio-hidden approval')


def _inventory(folder):
    return {str(p.relative_to(folder)):m.sha256_file(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def snapshot(root):
    root=Path(root).resolve();c=_context(root);_reader_only(c)
    rows=[r for r in m.read_json(root/'backend/data/approved_reader_bootstrap.json')['titles'] if r.get('slug')==SLUG]
    need(len(rows)==1,'Exact Sredni Reader bootstrap required')
    need(_inventory(c['dirs'][0])==_inventory(c['dirs'][1]),'Sredni publication file sets diverged')
    return {'schema_version':SNAPSHOT_SCHEMA,'slug':SLUG,'source_sha256':SOURCE,'manuscript_sha256':MANUSCRIPT,
            'files':{name:base64.b64encode((c['dirs'][0]/name).read_bytes()).decode() for name in FILES},
            'all_title_files':_inventory(c['dirs'][0]),'bootstrap_row':rows[0]}


def _snapshot_files(value):
    need(value.get('schema_version')==SNAPSHOT_SCHEMA and value.get('slug')==SLUG
         and value.get('source_sha256')==SOURCE and value.get('manuscript_sha256')==MANUSCRIPT
         and set(value.get('files',{}))==set(FILES),'Exact Sredni Reader-only snapshot required')
    try:files={name:base64.b64decode(value['files'][name],validate=True) for name in FILES}
    except (TypeError,ValueError):raise m.ReleasePointerError('Invalid Sredni snapshot bytes') from None
    need(all(value.get('all_title_files',{}).get(n)==m.sha256_bytes(b) for n,b in files.items()),'Snapshot inventory differs')
    _reader_only({**{n[:-5]:json.loads(b) for n,b in files.items() if n!='rights_decision.json'},'dirs':[]})
    return files


def _rights(root,c,when):
    prior=m.read_json(c['dirs'][0]/'rights_decision.json')
    accepted,revoked=load_production_registry(root/'backend/data/rights_decision_registry.json')
    required={name[:-5]:m.sha256_file(c['dirs'][0]/name) for name in FILES[:-1]}
    verdict=evaluate_accepted_record(prior,edition_id=SLUG,operator_id='reo-enterprise',country='IN',country_trusted=True,
        use='reader_delivery',required_components=required,accepted_records=accepted,revoked_decision_ids=revoked,now=when)
    need(verdict.passed,'Current Reader rights denied: '+','.join(verdict.reasons))
    audio=scored.load_adoption()['audio_use_decision']
    verdict=evaluate_accepted_record(audio,edition_id=SLUG,operator_id='reo-enterprise',country='IN',country_trusted=True,
        use='audio_stream',required_components=audio['components'],accepted_records=accepted,revoked_decision_ids=revoked,now=when)
    need(verdict.passed and audio['territories']==['IN'] and audio['uses']==['audio_stream'],'Exact accepted India audio rights denied')
    return prior,audio


def _prepare_changes(root,c,book,reader,*,prior,decision_id,when):
    need(isinstance(decision_id,str) and SLUG in decision_id,'Prospective Sredni Reader decision required')
    payloads={'public_book.json':m.json_bytes(book),'reader_manifest.json':m.json_bytes(reader)}
    with tempfile.TemporaryDirectory(prefix='sredni-source-stage-manifest-') as tmp:
        folder=Path(tmp)/SLUG;shutil.copytree(c['dirs'][0],folder)
        for name,data in payloads.items():(folder/name).write_bytes(data)
        manifest=build_manifest(folder,publish_approved=True,generated_at=when)
    need(not validate_manifest(manifest) and manifest['reader_release']['exposed'] is True
         and manifest['audio_release']['exposed'] is False,'Private source stage would change public Reader/audio access')
    payloads['checksum_manifest.json']=m.json_bytes(m._checksum_document(c['checksum_manifest'],payloads,when))
    payloads['publication_manifest.json']=m.json_bytes(manifest)
    registry_path=root/'backend/data/rights_decision_registry.json';registry=m.read_json(registry_path)
    need(decision_id not in registry['accepted_records'],'Successor Reader decision already exists; reconcile without retry')
    rights=copy.deepcopy(prior);rights['decision_id']=decision_id
    rights['basis']+='; Exact source-only private Sredni package metadata staging; Reader text, covers, uses, territory and validity unchanged. Audio rights remain separate; no playback or public release acceptance.'
    for name,data in payloads.items():rights['components'][name[:-5]]=m.sha256_bytes(data)
    rights['evidence_sha256']=list(prior['evidence_sha256'])+[digest({'prior':record_sha256(prior),'files':{n:m.sha256_bytes(b) for n,b in payloads.items()}})]
    registry['accepted_records'][decision_id]=record_sha256(rights)
    payloads['rights_decision.json']=m.json_bytes(rights)
    bp=root/'backend/data/approved_reader_bootstrap.json';bootstrap=m.read_json(bp)
    rows=[r for r in bootstrap['titles'] if r.get('slug')==SLUG];need(len(rows)==1,'Exact Reader bootstrap row required')
    rows[0].update(decision_id=decision_id,record_sha256=record_sha256(rights))
    changes={folder/name:data for folder in c['dirs'] for name,data in payloads.items()}
    changes.update({registry_path:m.json_bytes(registry),bp:m.json_bytes(bootstrap)})
    return changes


def _transaction(root,changes,operation,snap,*,apply):
    result={'schema_version':RESULT_SCHEMA,'slug':SLUG,'operation':operation,'snapshot_sha256':digest(snap),
        'applied':False,'public_audio_enabled':False,'protected_playback':'UNVERIFIED_NOT_AUTHORIZED_BY_SOURCE_STAGE',
        'files':{str(p.relative_to(root)):m.sha256_bytes(b) for p,b in changes.items()}}
    bp=root/'backend/data/approved_reader_bootstrap.json';bootstrap=json.loads(changes.get(bp,bp.read_bytes()))
    row=next(r for r in bootstrap['titles'] if r.get('slug')==SLUG);result['target_bootstrap_row_sha256']=digest(row)
    if apply:m._atomic_replace_many(changes);result['applied']=True
    return result


def stage(root,*,input_paths,snapshot_record,decision_id,generated_at=None,apply=False):
    root=Path(root).resolve();when=generated_at or m.utc_now();now=datetime.fromisoformat(when.replace('Z','+00:00'))
    need(now.tzinfo is not None,'Timezone-aware source transaction clock required')
    inputs=load_inputs(input_paths)
    with m._release_lock(root,SLUG):
        c=_context(root);_reader_only(c);files=_snapshot_files(snapshot_record)
        need(_inventory(c['dirs'][0])==snapshot_record['all_title_files']
             and _inventory(c['dirs'][1])==snapshot_record['all_title_files'],'Pre-stage title snapshot changed')
        rows=[r for r in m.read_json(root/'backend/data/approved_reader_bootstrap.json')['titles'] if r.get('slug')==SLUG]
        need(len(rows)==1 and rows[0]==snapshot_record['bootstrap_row'],'Pre-stage Sredni bootstrap row changed')
        prior,audio=_rights(root,c,now)
        valid,evidence=m._validated_release_bundle(c,SLUG,**{
            k:inputs[v] for k,v in [('package','package'),('release_descriptor','descriptor'),('primary_receipt','primary'),
              ('replica_receipt','replica'),('primary_release_manifest_receipt','primary_manifest'),('replica_release_manifest_receipt','replica_manifest')]},
            expected_manuscript_sha256=MANUSCRIPT,release_manifest_sha256=INPUTS['package'][0],release_manifest_size_bytes=INPUTS['package'][1],
            generated_at=when,**{label+'_receipt_sha256':INPUTS[role][0] for label,role in
                [('primary','primary'),('replica','replica'),('primary_release_manifest','primary_manifest'),('replica_release_manifest','replica_manifest')]},
            descriptor_validator=lambda d,p:m.validate_qa_candidate_release_descriptor(d,p,controlled_language=c['reader_manifest'].get('language')))
        need(valid['release_descriptor_sha256']==DESCRIPTOR and valid['package_version']==metadata.PACKAGE,'Exact stored Sredni package required')
        narrator=metadata.metadata_for_package(valid,DESCRIPTOR,c['reader_manifest']['language']);need(narrator,'Sredni metadata unavailable')
        marker={'schema_version':metadata.SCHEMA,'status':'SOURCE_QA_STAGED_PRIVATE','slug':SLUG,
            'candidate_descriptor_sha256':DESCRIPTOR,'candidate_package_version':valid['package_version'],
            'release_manifest_sha256':INPUTS['package'][0],'snapshot_sha256':digest(snapshot_record),
            'package_release_evidence_sha256':digest(evidence),'audio_use_decision':audio,'narrator_metadata':narrator,
            'downstream_gates_unchanged':copy.deepcopy(inputs['descriptor']['known_release_blockers']),
            'private_playback_authorized':False,'public_release_authorized':False,'staged_at':when}
        book=copy.deepcopy(c['public_book']);reader=copy.deepcopy(c['reader_manifest'])
        for document in (book,reader):
            document['audiobook_packages']={DESCRIPTOR:copy.deepcopy(valid)}
            document['audiobook_package_release_evidence']={DESCRIPTOR:copy.deepcopy(evidence)}
            document[FIELD]=copy.deepcopy(marker)
        changes=_prepare_changes(root,c,book,reader,prior=prior,decision_id=decision_id,when=when)
        return _transaction(root,changes,'STAGE_SOURCE_QA_PRIVATE',snapshot_record,apply=apply)


def restore(root,*,snapshot_record,expected_transaction,apply=False):
    root=Path(root).resolve()
    with m._release_lock(root,SLUG):
        c=_context(root);files=_snapshot_files(snapshot_record)
        need(expected_transaction.get('schema_version')==RESULT_SCHEMA and expected_transaction.get('slug')==SLUG
             and expected_transaction.get('operation')=='STAGE_SOURCE_QA_PRIVATE' and expected_transaction.get('applied') is True
             and expected_transaction.get('snapshot_sha256')==digest(snapshot_record),'Exact applied private stage required for restore')
        need((c['public_book'].get(FIELD) or {}).get('snapshot_sha256')==digest(snapshot_record),'Stage marker changed')
        changes={}
        for folder in c['dirs']:
            for path in folder.rglob('*'):
                if not path.is_file():continue
                name=str(path.relative_to(folder));expected=expected_transaction['files'].get(str(path.relative_to(root)),snapshot_record['all_title_files'].get(name))
                need(expected==m.sha256_file(path),'Staged title changed; refuse overwrite')
            need(set(_inventory(folder))==set(snapshot_record['all_title_files']),'Staged title file set changed')
            changes.update({folder/name:raw for name,raw in files.items()})
        registry=m.read_json(root/'backend/data/rights_decision_registry.json');prior=json.loads(files['rights_decision.json'])
        need(registry['accepted_records'].get(prior['decision_id'])==record_sha256(prior)
             and prior['decision_id'] not in registry.get('revoked_decision_ids',[]),'Prior Reader rights no longer accepted')
        bp=root/'backend/data/approved_reader_bootstrap.json';bootstrap=m.read_json(bp)
        rows=[r for r in bootstrap['titles'] if r.get('slug')==SLUG];need(len(rows)==1,'Exact restore Reader row required')
        need(digest(rows[0])==expected_transaction['target_bootstrap_row_sha256'],'Sredni bootstrap row changed')
        rows[0].clear();rows[0].update(copy.deepcopy(snapshot_record['bootstrap_row']));changes[bp]=m.json_bytes(bootstrap)
        # Accepted successor rights history and all unrelated rows are retained.
        return _transaction(root,changes,'RESTORE_READER_ONLY',snapshot_record,apply=apply)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=m.ROOT)
    commands=parser.add_subparsers(dest='command',required=True)
    capture=commands.add_parser('snapshot');capture.add_argument('--output',type=Path,required=True)
    for command in ('stage-private','restore-reader-only'):
        sub=commands.add_parser(command);sub.add_argument('--snapshot',type=Path,required=True);sub.add_argument('--inputs',type=Path,required=True);sub.add_argument('--apply',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='snapshot':
        value=snapshot(args.repo_root)
        with args.output.open('x') as out:json.dump(value,out,indent=2);out.write('\n')
        result={'snapshot_sha256':digest(value),'source_mutation':False}
    else:
        snap=m.read_json(args.snapshot);inputs=m.read_json(args.inputs)
        if args.command=='stage-private':
            need(set(inputs)=={'input_paths','decision_id'},'Exact private-stage CLI input fields required')
            result=stage(args.repo_root,snapshot_record=snap,apply=args.apply,**inputs)
        else:result=restore(args.repo_root,snapshot_record=snap,expected_transaction=inputs,apply=args.apply)
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
