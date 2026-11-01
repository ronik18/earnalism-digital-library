"""Native current-public replacement: private staging, proof-bound promotion and guarded restore.

No providers, uploads, keys, grants, wallet writes or deployment. Every source
change uses one title lock and the existing atomic multi-file transaction.
"""
from __future__ import annotations
import argparse,base64,copy,json,shutil,tempfile
from pathlib import Path
import audiobook_active_release_v2 as m
import native_scored_metadata as metadata
from native_audiobook_replacement import (FIELD,SCHEMA,SLUG,PREDECESSOR,DESCRIPTOR,SOURCE,MANUSCRIPT,
    PRIVATE_SCOPE,POST_GATES,candidate,rights_for_candidate,digest,need)
from rights_decision_gate import record_sha256
from protected_package_publication import protected_package_publication_valid
from publication_manifest import build_manifest,validate_manifest
from datetime import datetime

FILES=('public_book.json','reader_manifest.json','source_evidence.json','approval_evidence.json',
       'checksum_manifest.json','publication_manifest.json','rights_decision.json')
SNAPSHOT_SCHEMA='earnalism.native_replacement_restore_snapshot.v1'
RESULT_SCHEMA='earnalism.native_replacement_source_transaction.v1'


def _context(root):
    c=m.load_mirrored_publication(root,SLUG);m._verify_controlled_checksums(c)
    need(SOURCE in m._controlled_hashes(c),'Controlled source changed')
    return c


def snapshot(root):
    c=_context(root);book=c['public_book']
    need(protected_package_publication_valid(book),'Current public edition is not independently valid')
    need(book['audiobook_active_release']['active_release_descriptor_sha256']==PREDECESSOR
         and not book.get(FIELD),'Exact unchanged predecessor required')
    config=[m.read_json(root/base/'controlled_launch.json') for base in ('data','backend/data')]
    need(config[0]==config[1],'Launch configuration mirrors diverged')
    bootstrap=m.read_json(root/'backend/data/approved_reader_bootstrap.json')
    rows=[r for r in bootstrap['titles'] if r.get('slug')==SLUG];need(len(rows)==1,'Exact prior Reader row required')
    return {'schema_version':SNAPSHOT_SCHEMA,'slug':SLUG,'predecessor_descriptor_sha256':PREDECESSOR,
        'source_sha256':SOURCE,'manuscript_sha256':MANUSCRIPT,
        'files':{name:base64.b64encode((c['dirs'][0]/name).read_bytes()).decode() for name in FILES},
        'bootstrap_row':rows[0],
        'config_title_membership':SLUG in config[0].get('protected_package_public_slugs',[])}


def _snapshot_files(value):
    need(value.get('schema_version')==SNAPSHOT_SCHEMA and value.get('slug')==SLUG
         and value.get('predecessor_descriptor_sha256')==PREDECESSOR
         and value.get('source_sha256')==SOURCE and value.get('manuscript_sha256')==MANUSCRIPT
         and set(value.get('files',{}))==set(FILES),'Invalid exact predecessor snapshot')
    try:files={name:base64.b64decode(value['files'][name],validate=True) for name in FILES}
    except (ValueError,TypeError):raise m.ReleasePointerError('Invalid snapshot bytes') from None
    book=json.loads(files['public_book.json'])
    need(protected_package_publication_valid(book) and book['audiobook_active_release']['active_release_descriptor_sha256']==PREDECESSOR
         and not book.get(FIELD),'Snapshot predecessor binding invalid')
    return files


def _prepare_changes(root,c,book,reader,approval,*,decision_id,when,basis):
    """Rebind checksums, publication manifest and accepted Reader metadata together."""
    need(SLUG in decision_id and decision_id,'Exact prospective Reader decision identity required')
    payloads={'public_book.json':m.json_bytes(book),'reader_manifest.json':m.json_bytes(reader),
              'approval_evidence.json':m.json_bytes(approval)}
    with tempfile.TemporaryDirectory(prefix='native-replacement-manifest-') as tmp:
        folder=Path(tmp)/SLUG;shutil.copytree(c['dirs'][0],folder)
        for name,data in payloads.items():(folder/name).write_bytes(data)
        manifest=build_manifest(folder,publish_approved=True,generated_at=when)
    need(not validate_manifest(manifest) and manifest['reader_release'].get('exposed') is True
         and manifest['audio_release'].get('exposed') is True,'Replacement publication would disturb current Reader/audio')
    payloads['checksum_manifest.json']=m.json_bytes(m._checksum_document(c['checksum_manifest'],payloads,when))
    payloads['publication_manifest.json']=m.json_bytes(manifest)
    registry_path=root/'backend/data/rights_decision_registry.json';registry=m.read_json(registry_path)
    prior=m.read_json(c['dirs'][0]/'rights_decision.json')
    need(registry.get('accepted_records',{}).get(prior.get('decision_id'))==record_sha256(prior)
         and prior.get('decision_id') not in registry.get('revoked_decision_ids',[]),'Prior Reader rights untrusted')
    for name in FILES[:-1]:
        need(prior['components'].get(name[:-5])==m.sha256_file(c['dirs'][0]/name),'Prior Reader artifact binding changed')
    need(decision_id not in registry['accepted_records'],'Successor Reader decision already exists; reconcile without retry')
    rights=copy.deepcopy(prior);rights['decision_id']=decision_id
    rights['basis']=str(prior.get('basis') or '')+'; '+basis
    for name,data in payloads.items():
        if name[:-5] in rights['components']:rights['components'][name[:-5]]=m.sha256_bytes(data)
    rights['evidence_sha256']=list(prior['evidence_sha256'])+[digest({'prior':record_sha256(prior),'new_artifacts':{k:m.sha256_bytes(v) for k,v in payloads.items()}})]
    sha=record_sha256(rights);registry['accepted_records'][decision_id]=sha
    payloads['rights_decision.json']=m.json_bytes(rights)
    bootstrap_path=root/'backend/data/approved_reader_bootstrap.json';bootstrap=m.read_json(bootstrap_path)
    rows=[r for r in bootstrap['titles'] if r.get('slug')==SLUG];need(len(rows)==1,'Exact Reader bootstrap row required')
    rows[0].update(decision_id=decision_id,record_sha256=sha)
    changes={folder/name:data for folder in c['dirs'] for name,data in payloads.items()}
    changes.update({registry_path:m.json_bytes(registry),bootstrap_path:m.json_bytes(bootstrap)})
    return changes


def _transaction(root,changes,operation,snapshot_sha,*,apply):
    result={'schema_version':RESULT_SCHEMA,'operation':operation,'slug':SLUG,'snapshot_sha256':snapshot_sha,
        'source_sha256':SOURCE,'applied':False,'deployment_and_playback':'UNVERIFIED',
        'files':{str(p.relative_to(root)):m.sha256_bytes(data) for p,data in changes.items()}}
    bootstrap_path=root/'backend/data/approved_reader_bootstrap.json'
    bootstrap=json.loads(changes.get(bootstrap_path,bootstrap_path.read_bytes()))
    rows=[row for row in bootstrap['titles'] if row.get('slug')==SLUG]
    need(len(rows)==1,'Exact transaction Reader row required')
    result['target_bootstrap_row_sha256']=digest(rows[0])
    if apply:m._atomic_replace_many(changes);result['applied']=True
    return result


def stage(root,package,descriptor,primary,replica,primary_manifest,replica_manifest,*,
          snapshot_record,decision_id,generated_at=None,apply=False,**receipt_args):
    root=Path(root).resolve();when=generated_at or m.utc_now()
    with m._release_lock(root,SLUG):
        c=_context(root);prior_files=_snapshot_files(snapshot_record)
        need(all((c['dirs'][0]/name).read_bytes()==data for name,data in prior_files.items()),'Pre-stage snapshot no longer exact')
        m._validate_canary_title_author(c,descriptor,package)
        valid,evidence=m._validated_release_bundle(c,SLUG,package,descriptor,primary,replica,primary_manifest,replica_manifest,
            expected_manuscript_sha256=MANUSCRIPT,generated_at=when,
            descriptor_validator=lambda d,p:m.validate_qa_candidate_release_descriptor(d,p,controlled_language=c['reader_manifest'].get('language')),
            **receipt_args)
        need(valid['release_descriptor_sha256']==DESCRIPTOR,'Wrong native successor')
        book=copy.deepcopy(c['public_book']);reader=copy.deepcopy(c['reader_manifest']);approval=copy.deepcopy(c['approval_evidence'])
        record=m.read_json(root/'internal/audiobook_lab/release_gate/selfish-giant-cedar-20261102/audio-use-decision.json')
        marker={'schema_version':SCHEMA,'status':'STAGED_PRIVATE','slug':SLUG,'private_scope':PRIVATE_SCOPE,
            'predecessor_descriptor_sha256':PREDECESSOR,'predecessor_public_approval_sha256':digest(book['audiobook_public_package_approval']),
            'snapshot_sha256':digest(snapshot_record),'candidate_descriptor_sha256':DESCRIPTOR,
            'candidate_package_version':valid['package_version'],'package_release_evidence_sha256':digest(evidence),
            'post_deploy_proof_required':POST_GATES,'audio_use_decision':record,'staged_at':when}
        for document in (book,reader):
            document['audiobook_packages'][DESCRIPTOR]=copy.deepcopy(valid)
            document['audiobook_package_release_evidence'][DESCRIPTOR]=copy.deepcopy(evidence)
            document[FIELD]=copy.deepcopy(marker)
        # This validates the genuinely accepted separate new audio-use record,
        # while old publication/ordinary selection remain byte-identical values.
        rights_for_candidate(book,country='IN',now=datetime.fromisoformat(when.replace('Z','+00:00')))
        need(candidate(book) is not None,'Native private marker invalid')
        changes=_prepare_changes(root,c,book,reader,approval,decision_id=decision_id,when=when,
            basis='Owner-authorized private native audiobook replacement staging; prior public audiobook remains selected, Reader content and uses unchanged; no publication acceptance claimed.')
        return _transaction(root,changes,'STAGE_PRIVATE',digest(snapshot_record),apply=apply)


def promote(root,*,snapshot_record,decision_id,approved_by,playback_bytes,business_bytes,accounting_bytes,
            expected_proof_hashes,generated_at=None,apply=False):
    root=Path(root).resolve();when=generated_at or m.utc_now()
    with m._release_lock(root,SLUG):
        c=_context(root);book=copy.deepcopy(c['public_book']);reader=copy.deepcopy(c['reader_manifest']);approval=copy.deepcopy(c['approval_evidence'])
        _snapshot_files(snapshot_record)
        package,private=rights_for_candidate(book,country='IN',now=datetime.fromisoformat(when.replace('Z','+00:00')))
        need(private['snapshot_sha256']==digest(snapshot_record) and approved_by,'Exact retained restore snapshot and publication authority required')
        ids=[chunk['segment_id'] for track in package['tracks'] for chunk in track['chunks']]
        from native_continuous_acceptance import validate as validate_native_acceptance
        try:
            acceptance=validate_native_acceptance(package,playback_bytes=playback_bytes,business_bytes=business_bytes,
                accounting_bytes=accounting_bytes,expected_proof_hashes=expected_proof_hashes)
        except (ValueError,KeyError,TypeError):
            raise m.ReleasePointerError('Exact continuous native production acceptance denied') from None
        record=private['audio_use_decision']
        public={'schema_version':'audiobook_protected_package_publication.v1','status':'PUBLIC_APPROVED','slug':SLUG,
            'release_descriptor_sha256':DESCRIPTOR,'endpoint':f'/api/reader/book/{SLUG}/audiobook/manifest',
            'acceptance':acceptance,'acceptance_sha256':digest(acceptance),
            'audio_rights_decision_id':record['decision_id'],'audio_rights_record_sha256':record_sha256(record),
            'approved_by':approved_by,'approved_at':when}
        state=m.build_active_release_state(slug=SLUG,active_release_descriptor_sha256=DESCRIPTOR,
            retained_release_descriptor_sha256s=[DESCRIPTOR,PREDECESSOR])
        narrator=metadata.metadata_for_package(package,DESCRIPTOR,c['reader_manifest'].get('language'));need(narrator,'Exact native narrator binding required')
        for document in (book,reader):
            document.update(audiobook_active_release=copy.deepcopy(state),audiobook_release_descriptor_sha256=DESCRIPTOR,
                audiobook_public_package_approval=copy.deepcopy(public))
            document[FIELD]={**copy.deepcopy(private),'status':'PROMOTED_PUBLIC','promotion_acceptance_sha256':digest(acceptance)}
            metadata.apply_to_document(document,narrator)
        approval.update(sync_tier=package['sync_tier'],endpoint_url=public['endpoint'])
        need(protected_package_publication_valid(book),'Native promotion does not bind independent approval')
        changes=_prepare_changes(root,c,book,reader,approval,decision_id=decision_id,when=when,
            basis='Owner-authorized proof-bound native protected-audio replacement; exact Cedar narration and CC BY music attribution changed together; Reader text/covers/use/validity unchanged; separate audio rights retained.')
        return _transaction(root,changes,'PROMOTE_PUBLIC',digest(snapshot_record),apply=apply)


def restore(root,*,snapshot_record,expected_transaction,apply=False):
    """Restore exact old audio/narrator/Reader binding, preserving accepted history.

    Refuses stale target edits. Unrelated accepted registry history/bootstrap
    rows survive; no generic rollback can silently relabel retained audio.
    """
    root=Path(root).resolve()
    with m._release_lock(root,SLUG):
        c=_context(root);files=_snapshot_files(snapshot_record)
        need(expected_transaction.get('schema_version')==RESULT_SCHEMA and expected_transaction.get('applied') is True
             and expected_transaction.get('operation') in ('STAGE_PRIVATE','PROMOTE_PUBLIC')
             and expected_transaction.get('snapshot_sha256')==digest(snapshot_record),'Exact applied transaction required for guarded restore')
        marker=c['public_book'].get(FIELD) or {}
        need(marker.get('snapshot_sha256')==digest(snapshot_record),'Current replacement snapshot changed')
        changes={}
        for folder in c['dirs']:
            for name in FILES:
                path=folder/name;relative=str(path.relative_to(root))
                expected=expected_transaction.get('files',{}).get(relative)
                if name=='source_evidence.json':expected=m.sha256_bytes(files[name])
                need(expected and m.sha256_file(path)==expected,'Target changed after replacement transaction; scoped manual reconciliation required')
                changes[path]=files[name]
        registry=m.read_json(root/'backend/data/rights_decision_registry.json');prior=json.loads(files['rights_decision.json'])
        need(registry['accepted_records'].get(prior['decision_id'])==record_sha256(prior)
             and prior['decision_id'] not in registry.get('revoked_decision_ids',[]),'Prior Reader authority no longer accepted')
        bootstrap_path=root/'backend/data/approved_reader_bootstrap.json';bootstrap=m.read_json(bootstrap_path)
        rows=[r for r in bootstrap['titles'] if r.get('slug')==SLUG];need(len(rows)==1,'Exact Reader restore row required')
        need(expected_transaction.get('target_bootstrap_row_sha256')==digest(rows[0]),
             'Target Reader bootstrap row changed after replacement; reconcile without overwrite')
        current_rights=m.read_json(c['dirs'][0]/'rights_decision.json')
        need(rows[0].get('decision_id')==current_rights['decision_id'] and rows[0].get('record_sha256')==record_sha256(current_rights),'Reader bootstrap changed after replacement')
        rows[0].clear();rows[0].update(copy.deepcopy(snapshot_record['bootstrap_row']))
        changes[bootstrap_path]=m.json_bytes(bootstrap)
        # This workflow never modifies launch allowlists: predecessor was public.
        for base in ('data','backend/data'):
            config=m.read_json(root/base/'controlled_launch.json')
            need((SLUG in config.get('protected_package_public_slugs',[]))==snapshot_record['config_title_membership'],'Title launch membership changed')
        return _transaction(root,changes,'RESTORE_PRIOR_PUBLIC',digest(snapshot_record),apply=apply)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=m.ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    capture=sub.add_parser('snapshot');capture.add_argument('--output',type=Path,required=True)
    for command in ('stage-private','promote-public','restore-prior'):
        cmd=sub.add_parser(command);cmd.add_argument('--snapshot',type=Path,required=True);cmd.add_argument('--inputs',type=Path,required=True)
        cmd.add_argument('--apply',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='snapshot':
        value=snapshot(args.repo_root)
        with args.output.open('x') as out:json.dump(value,out,indent=2);out.write('\n')
        result={'snapshot_sha256':digest(value),'source_mutation':False}
    else:
        snap=m.read_json(args.snapshot);inputs=m.read_json(args.inputs)
        if args.command=='stage-private':
            paths={role:Path(inputs.pop(role)).resolve() for role in ('package','descriptor','primary','replica','primary_manifest','replica_manifest')}
            objects={role:m.read_json(path) for role,path in paths.items()}
            measured={'release_manifest_sha256':m.sha256_file(paths['package']),
                'release_manifest_size_bytes':paths['package'].stat().st_size,
                **{label+'_receipt_sha256':m.sha256_file(paths[role]) for label,role in
                    [('primary','primary'),('replica','replica'),('primary_release_manifest','primary_manifest'),('replica_release_manifest','replica_manifest')]}}
            need(not (set(inputs)&set(measured)), 'CLI receipt identities are measured from exact files, never supplied labels')
            result=stage(args.repo_root,**objects,snapshot_record=snap,apply=args.apply,**measured,**inputs)
        elif args.command=='promote-public':
            for role in ('playback','business','accounting'):inputs[role+'_bytes']=Path(inputs.pop(role+'_path')).read_bytes()
            result=promote(args.repo_root,snapshot_record=snap,apply=args.apply,**inputs)
        else:result=restore(args.repo_root,snapshot_record=snap,expected_transaction=inputs,apply=args.apply)
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
