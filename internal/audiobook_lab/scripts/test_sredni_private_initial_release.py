"""Actual retained storage fixture; local source transactions only, never live QA."""
import base64,copy,hashlib,json,shutil,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
import sredni_private_initial_release as release
import sredni_scored_metadata as metadata
import sredni_scored_retained as scored
import audiobook_active_release_v2 as manager
from rights_decision_gate import record_sha256
from protected_package_publication import protected_package_publication_valid
from native_audiobook_profiles import review_profile

ROOT=manager.ROOT


def clone(root):
    for side in ('data','backend/data'):
        source=ROOT/side/'controlled_publications'/release.SLUG
        target=root/side/'controlled_publications'/release.SLUG
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,target)
    for name in ('rights_decision_registry.json','approved_reader_bootstrap.json'):
        shutil.copyfile(ROOT/'backend/data'/name,root/'backend/data'/name)
    # Initial-stage tests use the frozen real Reader-only predecessor, rather
    # than assuming canonical metadata can never advance to a private stage.
    raw=(HERE/'fixtures/sredni-reader-only-source-snapshot.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='aa956917a2fdb93b393e32dc19b95a58ffda8270ed82263472595915d63af7a2'
    prior=json.loads(raw)
    for side in ('data','backend/data'):
        folder=root/side/'controlled_publications'/release.SLUG
        for name,value in prior['files'].items():
            (folder/name).write_bytes(base64.b64decode(value,validate=True))
    bp=root/'backend/data/approved_reader_bootstrap.json'
    bootstrap=json.loads(bp.read_text())
    row=next(r for r in bootstrap['titles'] if r['slug']==release.SLUG)
    row.clear();row.update(prior['bootstrap_row'])
    bp.write_bytes(manager.json_bytes(bootstrap))


def files(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
def book(root):return manager.read_json(root/'data/controlled_publications'/release.SLUG/'public_book.json')


@pytest.fixture
def prepared(tmp_path):
    root=tmp_path/'owned';root.mkdir();clone(root)
    data=json.loads((HERE/'fixtures/sredni-stored-source-stage.json').read_text())
    inputs=tmp_path/'stored';inputs.mkdir();paths={}
    for role,fact in data['files'].items():
        path=inputs/(role+'.json');path.write_text(fact['raw_utf8'])
        assert path.stat().st_size==fact['bytes'] and manager.sha256_file(path)==fact['sha256']
        paths[role]=str(path)
    args={'input_paths':paths,'snapshot_record':release.snapshot(root),
          'decision_id':'india-test-sredni-vashtar-private-source-stage','generated_at':'2026-11-03T10:00:00Z'}
    return root,args


def assert_rights(root):
    registry=manager.read_json(root/'backend/data/rights_decision_registry.json')
    for side in ('data','backend/data'):
        folder=root/side/'controlled_publications'/release.SLUG;rights=manager.read_json(folder/'rights_decision.json')
        assert registry['accepted_records'][rights['decision_id']]==record_sha256(rights)
        for name in release.FILES[:-1]:assert rights['components'][name[:-5]]==manager.sha256_file(folder/name)
    assert (root/'data/controlled_publications'/release.SLUG/'public_book.json').read_bytes()==(root/'backend/data/controlled_publications'/release.SLUG/'public_book.json').read_bytes()


def test_actual_four_receipts_stage_only_preserves_public_reader_source_and_other_rows(prepared):
    root,args=prepared;before=files(root);prior=book(root)
    result=release.stage(root,**args,apply=True);current=book(root)
    assert result['applied'] is True and len(result['files'])==12
    assert result['protected_playback']=='UNVERIFIED_NOT_AUTHORIZED_BY_SOURCE_STAGE'
    changed=set(result['files']);assert set(before)==set(files(root))
    assert all(files(root)[name]==raw for name,raw in before.items() if name not in changed)
    assert {k:v for k,v in current.items() if k not in ('audiobook_packages','audiobook_package_release_evidence',release.FIELD)}==prior
    reader=manager.read_json(root/'data/controlled_publications'/release.SLUG/'reader_manifest.json')
    assert 'audiobook_active_release' not in reader and reader['audio_enabled'] is False
    assert current['audiobook_active_release']=={'status':'DISABLED_TEXT_READER_ONLY'}
    marker=current[release.FIELD];assert marker['private_playback_authorized'] is marker['public_release_authorized'] is False
    assert marker['downstream_gates_unchanged']==scored.common.DOWNSTREAM
    assert protected_package_publication_valid(current) is False and review_profile(current) is None
    manifest=manager.read_json(root/'data/controlled_publications'/release.SLUG/'publication_manifest.json')
    assert manifest['reader_release']['exposed'] is True and manifest['audio_release']['exposed'] is False
    assert_rights(root)


def test_dry_run_is_byte_preserving_and_predicts_same_applied_outputs(prepared):
    root,args=prepared;before=files(root);plan=release.stage(root,**args)
    assert files(root)==before and plan['applied'] is False
    actual=release.stage(root,**args,apply=True)
    assert plan['files']==actual['files']


@pytest.mark.parametrize('role',list(release.INPUTS))
def test_each_actual_storage_input_changed_denies_before_source_mutation(prepared,role):
    root,args=prepared;path=Path(args['input_paths'][role]);path.write_bytes(path.read_bytes()+b' ');before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='size changed'):release.stage(root,**args,apply=True)
    assert files(root)==before


def test_same_size_wrong_package_or_receipt_bytes_denied(prepared):
    root,args=prepared;path=Path(args['input_paths']['package']);raw=path.read_bytes();path.write_bytes(raw.replace(b'8185',b'8186',1))
    before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='bytes changed'):release.stage(root,**args,apply=True)
    assert files(root)==before


def test_symlink_storage_input_denied(prepared,tmp_path):
    root,args=prepared;path=Path(args['input_paths']['primary']);link=tmp_path/'alias';link.symlink_to(path);args['input_paths']['primary']=str(link)
    before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='nonsymlink'):release.stage(root,**args,apply=True)
    assert files(root)==before


@pytest.mark.parametrize('change', ['active','enabled','old_package','reader_pointer','legacy_url','prior_marker'])
def test_initial_state_denies_other_release_or_audio_truth(prepared,change):
    root,args=prepared;c=release._context(root);book=copy.deepcopy(c['public_book']);reader=copy.deepcopy(c['reader_manifest'])
    if change=='active':book['audiobook_active_release']={'status':'ACTIVE'}
    elif change=='enabled':book['audio_enabled']=True
    elif change=='old_package':reader['audiobook_packages']={'unrelated':'KEEP'}
    elif change=='reader_pointer':reader['audiobook_active_release']=None
    elif change=='legacy_url':reader['audiobook']={'url':'https://example.invalid/old.mp3'}
    else:book[release.FIELD]={'status':'SOURCE_QA_STAGED_PRIVATE'}
    with pytest.raises(manager.ReleasePointerError):release._reader_only({**c,'public_book':book,'reader_manifest':reader})


def test_stale_title_or_bootstrap_snapshot_denies_without_overwrite(prepared):
    root,args=prepared;path=root/'data/controlled_publications'/release.SLUG/'chapters/chapter-001.json';path.write_bytes(path.read_bytes()+b' ')
    before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='snapshot changed'):release.stage(root,**args,apply=True)
    assert files(root)==before
    path.write_bytes(path.read_bytes()[:-1]);bp=root/'backend/data/approved_reader_bootstrap.json';bootstrap=json.loads(bp.read_text())
    next(r for r in bootstrap['titles'] if r['slug']==release.SLUG)['decision_id']='unrelated-changed';bp.write_text(json.dumps(bootstrap));before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='bootstrap row changed'):release.stage(root,**args,apply=True)
    assert files(root)==before


@pytest.mark.parametrize('kind',['reader','audio'])
def test_untrusted_or_revoked_separate_rights_deny(prepared,kind):
    root,args=prepared;path=root/'backend/data/rights_decision_registry.json';registry=json.loads(path.read_text())
    record=manager.read_json(root/'data/controlled_publications'/release.SLUG/'rights_decision.json') if kind=='reader' else scored.load_adoption()['audio_use_decision']
    registry['revoked_decision_ids'].append(record['decision_id']);path.write_text(json.dumps(registry));before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='rights denied'):release.stage(root,**args,apply=True)
    assert files(root)==before


def test_source_qa_holds_stay_immutable_and_generic_release_still_denies(prepared):
    root,args=prepared;docs=release.load_inputs(args['input_paths']);original=copy.deepcopy(docs['descriptor'])
    with pytest.raises(manager.ReleasePointerError,match='blockers'):manager.validate_release_descriptor(docs['descriptor'],docs['package'])
    release.stage(root,**args,apply=True)
    assert docs['descriptor']==original and docs['descriptor']['release_candidate_evidence']['all_release_gates_passed'] is False


def test_actual_stage_exact_credits_require_selected_bound_package_not_old_reader(prepared):
    root,args=prepared;release.stage(root,**args,apply=True);current=book(root);package=current['audiobook_packages'][release.DESCRIPTOR]
    value=metadata.metadata_for_selected_private_package(current,package,release.DESCRIPTOR,'en')
    assert value['audiobook_voice']=='Verse' and value['audiobook_provider']==''
    assert value['narration_disclosure']==metadata.DISCLOSURE and len(metadata.DISCLOSURE)==156
    assert metadata.metadata_for_selected_private_package({},package,release.DESCRIPTOR,'en') is None
    current[release.FIELD]['narrator_metadata']['narration_disclosure']='Ryan'
    with pytest.raises(scored.Error,match='Stale'):metadata.metadata_for_selected_private_package(current,package,release.DESCRIPTOR,'en')
    current=book(root);wrong=copy.deepcopy(package);wrong['package_version']='sha256-'+'0'*64
    with pytest.raises(scored.Error,match='selected'):metadata.metadata_for_selected_private_package(current,wrong,release.DESCRIPTOR,'en')


def test_guarded_restore_preserves_unrelated_rights_and_bootstrap(prepared):
    root,args=prepared;before=files(root);result=release.stage(root,**args,apply=True)
    registry=root/'backend/data/rights_decision_registry.json';data=json.loads(registry.read_text());data['accepted_records']['unrelated-new']='e'*64;registry.write_text(json.dumps(data));keep=registry.read_bytes()
    bp=root/'backend/data/approved_reader_bootstrap.json';data=json.loads(bp.read_text());other=next(r for r in data['titles'] if r['slug']!=release.SLUG);other['keep']='YES';bp.write_text(json.dumps(data))
    release.restore(root,snapshot_record=args['snapshot_record'],expected_transaction=result,apply=True)
    assert registry.read_bytes()==keep and next(r for r in json.loads(bp.read_text())['titles'] if r['slug']==other['slug'])['keep']=='YES'
    for side in ('data','backend/data'):
        for name in release.FILES:assert (root/side/'controlled_publications'/release.SLUG/name).read_bytes()==before[str(Path(side)/'controlled_publications'/release.SLUG/name)]
    assert_rights(root)


def test_restore_stale_title_or_bootstrap_denies(prepared):
    root,args=prepared;result=release.stage(root,**args,apply=True)
    path=root/'data/controlled_publications'/release.SLUG/'chapters/chapter-001.json';path.write_bytes(path.read_bytes()+b' ');before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='changed'):release.restore(root,snapshot_record=args['snapshot_record'],expected_transaction=result,apply=True)
    assert files(root)==before
    path.write_bytes(path.read_bytes()[:-1]);bp=root/'backend/data/approved_reader_bootstrap.json';data=json.loads(bp.read_text());next(r for r in data['titles'] if r['slug']==release.SLUG)['changed']=True;bp.write_text(json.dumps(data));before=files(root)
    with pytest.raises(manager.ReleasePointerError,match='bootstrap row changed'):release.restore(root,snapshot_record=args['snapshot_record'],expected_transaction=result,apply=True)
    assert files(root)==before


def test_existing_atomic_transaction_rolls_back_midwrite_failure(prepared,monkeypatch):
    root,args=prepared;before=files(root);original=manager.os.replace;calls=0
    def fail_once(a,b):
        nonlocal calls
        calls+=1
        if calls==3:raise OSError('SYNTHETIC_ONE_WRITE_FAILURE')
        return original(a,b)
    monkeypatch.setattr(manager.os,'replace',fail_once)
    with pytest.raises(manager.ReleasePointerError,match='rolled back'):release.stage(root,**args,apply=True)
    assert files(root)==before
