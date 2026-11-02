"""Current-public fixtures only. Synthetic storage/proofs never qualify a live release."""
import copy,json,sys,shutil,tempfile,hashlib
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'backend')]
import native_replacement_release as release
import audiobook_active_release_v2 as manager
import native_audiobook_replacement as native
from audiobook_packages import with_canonical_package_version
import test_audiobook_active_release_v2 as manager_fixtures
import test_new_title_publication_acceptance as acceptance_fixtures


def finalized_package():
    folder=ROOT/'internal/audiobook_lab/release_gate/selfish-giant-cedar-20261102'
    descriptor=json.loads((folder/'release-descriptor.json').read_text())
    package=json.loads((folder/'delivery-mapping.json').read_text())
    package.update(schema_version='audiobook_package_manifest.v2',release_evidence_version='owner_produced_native_scored.v1')
    prefix=f'v1/prod/sprint1/{native.SLUG}/releases/{native.DESCRIPTOR}/'
    for role,asset in package['tracks'][0]['chunks'][0]['assets'].items():
        asset.update(storage=dict(store='prod',bucket='prod-bucket',key=prefix+role,version_id='SYNTHETIC-prod-'+role),
            replicas=[dict(store='dr',bucket='dr-bucket',key=prefix+role,version_id='SYNTHETIC-dr-'+role)])
    return with_canonical_package_version(package),descriptor


def clone(root):
    for side in ('data','backend/data'):
        shutil.copytree(ROOT/side/'controlled_publications'/native.SLUG,root/side/'controlled_publications'/native.SLUG)
        shutil.copy2(ROOT/side/'controlled_launch.json',root/side/'controlled_launch.json')
    for name in ('rights_decision_registry.json','approved_reader_bootstrap.json'):
        shutil.copy2(ROOT/'backend/data'/name,root/'backend/data'/name)
    target='internal/audiobook_lab/release_gate/selfish-giant-cedar-20261102'
    shutil.copytree(ROOT/target,root/target)
    # Freeze the actual b5 predecessor independently of later canonical public
    # promotion. Its source text/covers remain the actual unchanged title.
    captured=json.loads((HERE/'fixtures/selfish-native-b5-predecessor.json').read_text())
    for side in ('data','backend/data'):
        for name,data in release._snapshot_files(captured).items():
            (root/side/'controlled_publications'/native.SLUG/name).write_bytes(data)
    bootstrap_path=root/'backend/data/approved_reader_bootstrap.json';bootstrap=json.loads(bootstrap_path.read_text())
    row=next(r for r in bootstrap['titles'] if r.get('slug')==native.SLUG)
    row.clear();row.update(copy.deepcopy(captured['bootstrap_row']));bootstrap_path.write_bytes(manager.json_bytes(bootstrap))


def stage_args(package,descriptor,snap):
    helper=manager_fixtures.ActiveReleaseManagerTests();helper.slug=native.SLUG
    primary,replica=helper._receipts(package)
    pm,rm,sha,size=helper._release_manifest_receipts(package)
    return dict(package=package,descriptor=descriptor,primary=primary,replica=replica,primary_manifest=pm,replica_manifest=rm,
        snapshot_record=snap,decision_id='india-fixture-the-selfish-giant-native-private-stage',generated_at='2026-11-02T02:00:00Z',
        release_manifest_sha256=sha,release_manifest_size_bytes=size,
        **{k+'_receipt_sha256':native.digest(v) for k,v in [('primary',primary),('replica',replica),('primary_release_manifest',pm),('replica_release_manifest',rm)]})


def proofs(package):
    data=acceptance_fixtures.AcceptanceTests();data.setUp();ids=[c['segment_id'] for t in package['tracks'] for c in t['chunks']]
    data.playback.update(descriptor=native.DESCRIPTOR,packageVersion=package['package_version'],durationMs=package['duration_ms'],
        segmentCount=len(ids),coverage=[dict(segment=k,durationMatches=True,ended=True,startedFromBeginning=True) for k in ids],
        timestamps=[dict(segment=k,http=200,sha256Matches=True) for k in ids])
    blobs={k:json.dumps(getattr(data,k)).encode() for k in ('playback','business','accounting')}
    return {**{k+'_bytes':v for k,v in blobs.items()},'expected_proof_hashes':{k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()}}


@pytest.fixture
def staged(tmp_path):
    clone(tmp_path);package,descriptor=finalized_package();snap=release.snapshot(tmp_path)
    result=release.stage(tmp_path,**stage_args(package,descriptor,snap),apply=True)
    return tmp_path,package,descriptor,snap,result


def book(root):return json.loads((root/'data/controlled_publications'/native.SLUG/'public_book.json').read_text())


def assert_reader_bound(root):
    from rights_decision_gate import record_sha256
    for side in ('data','backend/data'):
        folder=root/side/'controlled_publications'/native.SLUG
        rights=json.loads((folder/'rights_decision.json').read_text())
        registry=json.loads((root/'backend/data/rights_decision_registry.json').read_text())
        assert registry['accepted_records'][rights['decision_id']]==record_sha256(rights)
        for name in release.FILES[:-1]:assert rights['components'][name[:-5]]==hashlib.sha256((folder/name).read_bytes()).hexdigest()
    assert (root/'data/controlled_publications'/native.SLUG/'public_book.json').read_bytes()==(root/'backend/data/controlled_publications'/native.SLUG/'public_book.json').read_bytes()


def test_actual_current_public_stage_preserves_old_selection_narrator_reader_and_no_random_canary(staged):
    root,package,descriptor,snap,result=staged;prior=json.loads(release._snapshot_files(snap)['public_book.json']);current=book(root)
    for key in ('audiobook_active_release','audiobook_public_package_approval','audiobook_provider','audiobook_voice','narration_disclosure','chapters','cover_image_url','back_cover_image_url','source_hash','content_hash'):
        assert current.get(key)==prior.get(key)
    assert current[native.FIELD]['status']=='STAGED_PRIVATE' and current['audiobook_active_release']['rollout']['percentage']==0
    assert current['audiobook_active_release']['candidate_release_descriptor_sha256']==''
    assert current['audiobook_packages'][native.PREDECESSOR]==prior['audiobook_packages'][native.PREDECESSOR]
    assert native.candidate(current)[0]==package
    assert_reader_bound(root)


def test_full_current_public_promotion_and_exact_guarded_restore(staged):
    root,package,descriptor,snap,stage_result=staged
    result=release.promote(root,snapshot_record=snap,decision_id='india-fixture-the-selfish-giant-native-promotion',
        approved_by='SYNTHETIC_FIXTURE_ONLY',generated_at='2026-11-02T02:01:00Z',apply=True,**__import__('test_native_continuous_acceptance').arguments(package))
    current=book(root);assert current['audiobook_voice']=='Cedar'
    assert 'Kevin MacLeod' in current['narration_disclosure'] and current['audiobook_active_release']['active_release_descriptor_sha256']==native.DESCRIPTOR
    assert_reader_bound(root)
    with pytest.raises(manager.ReleasePointerError,match='dedicated'):manager.rollback_release(root,native.SLUG,'previous',apply=True)
    registry_before=(root/'backend/data/rights_decision_registry.json').read_bytes()
    release.restore(root,snapshot_record=snap,expected_transaction=result,apply=True)
    for side in ('data','backend/data'):
        folder=root/side/'controlled_publications'/native.SLUG
        for name,data in release._snapshot_files(snap).items():assert (folder/name).read_bytes()==data
    assert (root/'backend/data/rights_decision_registry.json').read_bytes()==registry_before
    assert_reader_bound(root)


def test_private_stage_restore_without_promotion_is_exact(staged):
    root,package,descriptor,snap,result=staged
    release.restore(root,snapshot_record=snap,expected_transaction=result,apply=True)
    assert native.FIELD not in book(root);assert book(root)==json.loads(release._snapshot_files(snap)['public_book.json']);assert_reader_bound(root)


def test_bad_proof_no_mutation_and_stale_restore_does_not_overwrite_concurrent_title_work(staged):
    root,package,descriptor,snap,result=staged
    args=proofs(package);args['playback_bytes']+=b' '
    before={str(p):p.read_bytes() for p in root.rglob('*.json')}
    with pytest.raises((manager.ReleasePointerError,native.ReplacementError)):release.promote(root,snapshot_record=snap,decision_id='india-fixture-the-selfish-giant-native-bad',approved_by='SYNTHETIC',apply=True,**args)
    assert before=={str(p):p.read_bytes() for p in root.rglob('*.json')}
    # A coherent other change after staging is not silently overwritten.
    primary=root/'data/controlled_publications'/native.SLUG/'approval_evidence.json'
    primary.write_bytes(primary.read_bytes()+b' ')
    with pytest.raises((manager.ReleasePointerError,native.ReplacementError)):release.restore(root,snapshot_record=snap,expected_transaction=result,apply=True)
    assert primary.read_bytes().endswith(b' ')


def test_restore_preserves_unrelated_bootstrap_rows_and_accepted_history(staged):
    root,package,descriptor,snap,result=staged
    path=root/'backend/data/approved_reader_bootstrap.json';data=json.loads(path.read_text())
    row=next(r for r in data['titles'] if r['slug']!=native.SLUG);row['unrelated_change']='KEEP';path.write_text(json.dumps(data))
    reg=root/'backend/data/rights_decision_registry.json';registered=json.loads(reg.read_text());registered['accepted_records']['unrelated-later-record']='f'*64;reg.write_text(json.dumps(registered))
    release.restore(root,snapshot_record=snap,expected_transaction=result,apply=True)
    assert next(r for r in json.loads(path.read_text())['titles'] if r['slug']==row['slug'])['unrelated_change']=='KEEP'
    assert json.loads(reg.read_text())['accepted_records']['unrelated-later-record']=='f'*64


def test_failed_atomic_native_promotion_restores_all_title_rights_and_bootstrap(staged,monkeypatch):
    root,package,descriptor,snap,result=staged
    before={str(p):p.read_bytes() for p in root.rglob('*.json')}
    replace=manager.os.replace;failed=[False]
    def fail_once(source,target):
        if not failed[0] and Path(target).name=='approved_reader_bootstrap.json':
            failed[0]=True;raise OSError('SYNTHETIC atomic failure')
        return replace(source,target)
    monkeypatch.setattr(manager.os,'replace',fail_once)
    with pytest.raises(manager.ReleasePointerError,match='rolled back'):
        release.promote(root,snapshot_record=snap,decision_id='india-fixture-the-selfish-giant-native-atomic',approved_by='SYNTHETIC',
            generated_at='2026-11-02T02:01:00Z',apply=True,**__import__('test_native_continuous_acceptance').arguments(package))
    assert failed[0] and before=={str(p):p.read_bytes() for p in root.rglob('*.json')}
    assert_reader_bound(root)


def test_restore_denies_concurrent_same_title_bootstrap_field_change(staged):
    root,package,descriptor,snap,result=staged
    path=root/'backend/data/approved_reader_bootstrap.json';value=json.loads(path.read_text())
    next(row for row in value['titles'] if row['slug']==native.SLUG)['concurrent_reader_change']='MUST_PRESERVE'
    path.write_bytes(manager.json_bytes(value));before={str(p):p.read_bytes() for p in root.rglob('*.json')}
    with pytest.raises(native.ReplacementError,match='bootstrap row changed'):
        release.restore(root,snapshot_record=snap,expected_transaction=result,apply=True)
    assert before=={str(p):p.read_bytes() for p in root.rglob('*.json')}
