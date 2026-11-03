"""Offline contracts. Synthetic trust fixtures are never production adoption."""
from pathlib import Path
import copy,json,hashlib,importlib.util,sys
import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'backend')]
import sredni_scored_retained as profile
import audiobook_active_release_v2 as manager
from rights_decision_gate import record_sha256
DATA=profile.DATA

@pytest.fixture
def ctx(tmp_path,monkeypatch):
    monkeypatch.setattr(profile,'DATA',DATA);monkeypatch.setattr(profile,'ROOT',ROOT)
    reg=tmp_path/'synthetic-adoption-registry.json';monkeypatch.setattr(profile,'REGISTRY',reg)
    a=json.loads((DATA/'SOURCE-ADOPTION.PROPOSED.json').read_text())
    # This fixture exercises the real registry/evaluation contract only. It is not
    # actual owner/rights acceptance and is never part of source registry data.
    a.update(descriptor_sha256=profile.DESCRIPTOR_SHA,status='ADOPTED',adopted_by='SYNTHETIC_TEST_ONLY',authority_reference='SYNTHETIC_NO_PRODUCTION_AUTHORITY',authority_evidence_sha256=hashlib.sha256(b'synthetic-test-only').hexdigest(),independent_source_review_sha256=profile.REVIEW_SHA)
    r=a['audio_use_decision'];r.pop('scope',None);r.update(status='ACCEPTED',valid_from='2026-01-01T00:00:00+00:00',accepted_by='SYNTHETIC_TEST_ONLY',conditions_satisfied=True)
    trusted={r['decision_id']:record_sha256(r)};revoked=frozenset()
    monkeypatch.setattr(profile,'load_production_registry',lambda:(trusted,revoked))
    def save():reg.write_text(json.dumps({'schema':'earnalism.sredni-scored-adoptions.v1','adoptions':[{'record':a,'record_sha256':profile.sha(profile.canonical(a))}]}))
    save()
    d=json.loads((DATA/'prospective-registration/release-descriptor.json').read_text());p=json.loads((DATA/'prospective-registration/package-identity.json').read_text())
    return a,d,p,save,trusted

def call(d,p,lang='en'):
    return manager.validate_qa_candidate_release_descriptor(d,p,controlled_language=lang)

def test_real_manager_dispatch_exact_source_only(ctx):
    a,d,p,save,trusted=ctx
    assert call(d,p)==d
    assert call(d,p)['release_candidate_evidence']['all_release_gates_passed'] is False

def test_actual_proposal_is_not_adopted(ctx):
    a,d,p,save,trusted=ctx;a['status']='PROPOSED_NOT_ADOPTED';save()
    with pytest.raises(manager.ReleasePointerError,match='adoption'):call(d,p)

@pytest.mark.parametrize('field,value',[('word_count',1787),('paragraph_count',158),('duration_ms',638106),('slug','the-selfish-giant')])
def test_actual_counts_and_title_fail_closed(ctx,field,value):
    a,d,p,save,trusted=ctx;p[field]=value
    with pytest.raises((manager.ReleasePointerError,ValueError)):call(d,p)

@pytest.mark.parametrize('field,value',[('master_mp3_sha256','a'*64),('highlight_sync_enabled',True),('manuscript_sha256','b'*64)])
def test_descriptor_identity_not_labels(ctx,field,value):
    a,d,p,save,trusted=ctx;d[field]=value
    with pytest.raises(manager.ReleasePointerError):call(d,p)

def test_non_english_denied(ctx):
    a,d,p,save,trusted=ctx
    with pytest.raises(manager.ReleasePointerError,match='English'):call(d,p,'bn')

def test_actual_rights_trust_required(ctx):
    a,d,p,save,trusted=ctx;trusted.clear()
    with pytest.raises(manager.ReleasePointerError,match='rights registry'):call(d,p)

def test_rights_proposal_never_acceptance(ctx):
    a,d,p,save,trusted=ctx;a['audio_use_decision']['status']='PROPOSED_NOT_ACCEPTED';save()
    with pytest.raises(manager.ReleasePointerError):call(d,p)

def test_territory_not_expanded(ctx):
    a,d,p,save,trusted=ctx;a['audio_use_decision']['territories']=['IN','US'];save()
    with pytest.raises(manager.ReleasePointerError,match='India'):call(d,p)

def test_evidence_and_independent_review_cannot_drift(ctx):
    a,d,p,save,trusted=ctx;a['independent_source_review_sha256']='c'*64;save()
    with pytest.raises(manager.ReleasePointerError,match='Independent'):call(d,p)


@pytest.fixture
def local_bundle(tmp_path, monkeypatch):
    """Synthetic byte contracts only; no real audio, trust or provider access."""
    d=json.loads((DATA/'prospective-registration/release-descriptor.json').read_text())
    package=json.loads((DATA/'prospective-registration/package-identity.json').read_text())
    bundle={'schema':'earnalism.sredni-scored-local-package.v1','release_descriptor':d,
            'package_identity':package,'source_units':json.loads((DATA/'source-units.json').read_text()),
            'evidence_files':{},'asset_files':{}}
    def put(name,raw):
        (tmp_path/name).write_bytes(raw)
        return {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
    for key,raw in [('master_wav',b'SYNTHETIC_WAV_NOT_AUDIO'),('master_mp3',b'SYNTHETIC_MP3_NOT_AUDIO'),
                    ('listened_master_mp3',b'SYNTHETIC_LISTENED_NOT_AUDIO'),('manuscript',(DATA/'manuscript.txt').read_bytes())]:
        bundle[key]=put(key+'.bin',raw);d[key+'_sha256' if key!='manuscript' else 'manuscript_sha256']=bundle[key]['sha256']
    for role in profile.EVIDENCE_ROLES:
        bundle['evidence_files'][role]=put(role+'.json',b'{}')
    d['evidence_sha256']={k:v['sha256'] for k,v in bundle['evidence_files'].items()}
    chunk=package['tracks'][0]['chunks'][0]
    for role,fact in chunk['assets'].items():
        ref=bundle['master_mp3'] if role=='audio' else put(role+'.bin',('SYNTHETIC_'+role).encode())
        bundle['asset_files'][chunk['segment_id']+'-'+role]=ref
        fact.update(sha256=ref['sha256'],size_bytes=(tmp_path/ref['path']).stat().st_size)
    monkeypatch.setattr(profile,'validate',lambda *a: d)
    monkeypatch.setattr(profile.media,'wav_identity',lambda _: {'frames':30629040})
    proof={'items':{'listened':{'canonical_decoded_PCM':{'sha256':'c'*64},
                             'elementary_encoded_audio_packets':{'sha256':'d'*64,'bytes':100}}}}
    ref=put('container_metadata_reuse.json',json.dumps(proof).encode())
    bundle['evidence_files']['container_metadata_reuse']=ref;d['evidence_sha256']['container_metadata_reuse']=ref['sha256']
    monkeypatch.setattr(profile.media,'validate_container_reuse',lambda *a,**kw:None)
    monkeypatch.setattr(profile,'publication_tags',lambda _:None)
    monkeypatch.setattr(profile.media,'decoded_pcm_identity',lambda _: {'sha256':'c'*64,'packet_sha256':'d'*64,'packet_bytes':100,'frames':30629040})
    path=tmp_path/'bundle.json'
    def save():path.write_text(json.dumps(bundle))
    save()
    return bundle,path,save

def test_local_prepare_emits_supported_semantics_only(local_bundle,tmp_path):
    bundle,path,save=local_bundle
    result=profile.prepare(path,tmp_path/'output')
    assert result['uploads'] is False and result['public_release_approved'] is False
    plan=json.loads((tmp_path/'output/upload-plan.json').read_text())
    semantics=json.loads((tmp_path/'output/package-semantics.json').read_text())
    assert len(plan['assets'])==4 and len(semantics['tracks'][0]['chunks'][0]['asset_ids'])==4
    assert semantics['schema_version']=='audiobook_package_semantics.v2'

@pytest.mark.parametrize('key',['master_wav','master_mp3','listened_master_mp3','manuscript'])
def test_self_sealed_substitute_cannot_replace_descriptor_master(local_bundle,tmp_path,key):
    bundle,path,save=local_bundle
    raw=b'SELF_SEALED_SUBSTITUTE_NOT_ACCEPTED'
    ref=bundle[key];(tmp_path/ref['path']).write_bytes(raw);ref['sha256']=hashlib.sha256(raw).hexdigest();save()
    with pytest.raises(profile.Error,match='descriptor'):profile.prepare(path,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()

@pytest.mark.parametrize('change',['missing','extra'])
def test_exact_evidence_roles_required_before_output(local_bundle,tmp_path,change):
    bundle,path,save=local_bundle
    if change=='missing':bundle['evidence_files'].pop('music_rights')
    else:bundle['evidence_files']['unreviewed']=bundle['manuscript']
    save()
    with pytest.raises(profile.Error,match='evidence role'):profile.prepare(path,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()

@pytest.mark.parametrize('kind',['file','directory','escape'])
def test_symlink_and_escape_denied_before_output(local_bundle,tmp_path,kind):
    bundle,path,save=local_bundle
    ref=bundle['master_wav'];target=tmp_path/ref['path']
    if kind=='file':
        link=tmp_path/'linked.bin';link.symlink_to(target);ref['path']=link.name
    elif kind=='directory':
        directory=tmp_path/'real';directory.mkdir();(directory/'file').write_bytes(target.read_bytes())
        (tmp_path/'linked').symlink_to(directory,target_is_directory=True);ref['path']='linked/file'
    else:ref['path']='../outside'
    save()
    with pytest.raises(profile.Error):profile.prepare(path,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()

@pytest.mark.parametrize('change',['missing','extra'])
def test_exact_delivery_asset_set_required(local_bundle,tmp_path,change):
    bundle,path,save=local_bundle
    if change=='missing':bundle['asset_files'].pop(next(iter(bundle['asset_files'])))
    else:bundle['asset_files']['extra']=bundle['master_mp3']
    save()
    with pytest.raises(profile.Error,match='delivery asset set'):profile.prepare(path,tmp_path/'not-created')


def test_actual_pcm_divergence_denied(local_bundle,tmp_path,monkeypatch):
    bundle,path,save=local_bundle
    def decoded(p):
        return {'sha256':('e' if 'listened' in p.name else 'c')*64,'packet_sha256':'d'*64,'packet_bytes':100,'frames':30629040}
    monkeypatch.setattr(profile.media,'decoded_pcm_identity',decoded)
    with pytest.raises(profile.Error,match='PCM differs'):profile.prepare(path,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()


def test_actual_frozen_verse_tags_are_not_cedar_metadata():
    tags=json.loads((DATA/'support/ec259383acb3-PUBLICATION-TAG-READBACK.json').read_text())['tags']
    profile.validate_publication_tags(tags)

@pytest.mark.parametrize('change',[{'artist':'Saki; AI narration: OpenAI Cedar'},
    {'title':'The Selfish Giant'}, {'comment':'AI narration: OpenAI Verse'},
    {'album':'/Users/private/path'}, {'album':'Draft'}])
def test_wrong_voice_stale_or_uncredited_publication_denied(change):
    tags=json.loads((DATA/'support/ec259383acb3-PUBLICATION-TAG-READBACK.json').read_text())['tags']
    tags.update(change)
    with pytest.raises(profile.Error):profile.validate_publication_tags(tags)


def test_shipped_prospective_source_registry_exact_india_only():
    """Canonical candidate source admission only; not storage/runtime acceptance."""
    d=json.loads((DATA/'prospective-registration/release-descriptor.json').read_text())
    p=json.loads((DATA/'prospective-registration/package-identity.json').read_text())
    result=call(d,p)
    assert result['release_candidate_evidence']['all_release_gates_passed'] is False
    assert result['known_release_blockers']==profile.common.DOWNSTREAM
    a=profile.load_adoption()
    assert a['audio_use_decision']['territories']==['IN']
    assert a['audio_use_decision']['uses']==['audio_stream']
    assert a['authority_evidence_sha256']=='70853686516bf26b01a7d98d9bb5c70bf410d623ae5742dd58ec5d91b3138686'


def test_real_manager_empty_assets_are_not_an_admitted_package(ctx):
    a,d,p,save,trusted=ctx;p['tracks'][0]['chunks'][0]['assets']={}
    with pytest.raises((manager.ReleasePointerError,ValueError)):call(d,p)


def test_real_manager_frozen_index_digest_is_mandatory(ctx,monkeypatch):
    a,d,p,save,trusted=ctx;monkeypatch.setattr(profile,'INDEX_SHA','a'*64)
    with pytest.raises(manager.ReleasePointerError,match='evidence index'):call(d,p)


def test_altered_source_units_cannot_prepare(local_bundle,tmp_path):
    bundle,path,save=local_bundle;bundle['source_units'][0]['source_end']-=1;save()
    with pytest.raises(profile.Error,match='source units'):profile.prepare(path,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()
