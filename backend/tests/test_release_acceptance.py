"""Dummy release evidence only: no provider, media generation or paid sessions."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import release_acceptance as policy
from scripts.produce_release import evaluate
from scripts.release_runtime import promote, RuntimeBlocked
from backend.tests.test_produce_release import _manifest, _reader_approval, _audio_approval


def candidate(tmp_path):
    manifest, audio = _manifest(tmp_path)
    manifest['audio'].update(sha256='a'*64, package_version='sha256-'+'b'*64)
    manifest['release_descriptor_sha256'] = 'c'*64
    contract = json.loads(policy.CONSUMER_CONTRACT.read_text())
    manifest['delivery'] = {'consumer': contract['consumer'], 'route': '/listener/pilot',
                            'features': dict(policy.FEATURES_OFF), 'sync_claim': 'NONE'}
    proof = {'schema': 'earnalism.text_sync_applicability.v1', 'status': 'NOT_APPLICABLE',
             'binding': policy._binding(manifest), 'delivery': copy.deepcopy(manifest['delivery']),
             'consumer_sources': contract['sources']}
    manifest['automated_checks']['synchronization'] = {'status': 'NOT_APPLICABLE', 'applicability': proof}
    reader = tmp_path/'reader-approval.json'; reader.write_text(json.dumps(_reader_approval(manifest)))
    listening = tmp_path/'audio-approval.json'; listening.write_text(json.dumps(_audio_approval(audio)))
    manifest.update(release_status='READY_FOR_GO_LIVE', audio_release_gate_status='PASS',
                    reader_approval=_reader_approval(manifest), audio_samples_approval=_audio_approval(audio))
    return manifest, reader, listening


class DummyPromoter:
    def __init__(self): self.calls = 0
    def promote(self, payload, *, execute):
        assert execute is False
        self.calls += 1
        return {'status': 'DRY_RUN', 'network_calls_performed': 0}


def test_proven_nonconsumer_na_survives_evaluation_and_promotion(tmp_path):
    manifest, reader, listening = candidate(tmp_path)
    report = evaluate(manifest, tmp_path, reader, listening)
    assert report['release_status'] == 'READY_FOR_GO_LIVE'
    assert report['automated_checks']['synchronization']['status'] == 'NOT_APPLICABLE'
    fake = DummyPromoter()
    result = promote(manifest, {'passed': True, 'release_eligible': False, 'release_id':'dummy'}, execute=False, promoter=fake)
    assert fake.calls == 1 and result['network_calls_performed'] == 0


@pytest.mark.parametrize('feature', list(policy.FEATURES_OFF))
def test_consuming_features_still_require_measured_sync(tmp_path, feature):
    manifest, reader, listening = candidate(tmp_path)
    manifest['delivery']['features'][feature] = True
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'
    with pytest.raises(RuntimeBlocked):
        promote(manifest, {'passed':True,'release_eligible':False,'release_id':'dummy'}, execute=False, promoter=DummyPromoter())


@pytest.mark.parametrize('mutation', ['no_proof','wrong_audio','wrong_package','stale_source','legacy_reader','sync_claim','boolean_coercion'])
def test_na_cannot_be_self_asserted_or_reused_out_of_binding(tmp_path, mutation):
    manifest, reader, listening = candidate(tmp_path)
    check = manifest['automated_checks']['synchronization']
    if mutation == 'no_proof': check.pop('applicability')
    elif mutation == 'wrong_audio': manifest['audio']['sha256'] = 'd'*64
    elif mutation == 'wrong_package': manifest['audio']['package_version'] = 'sha256-'+'e'*64
    elif mutation == 'stale_source': check['applicability']['consumer_sources'] = {'unknown.js': 'f'*64}
    elif mutation == 'legacy_reader': manifest['delivery']['route'] = '/reader-legacy/pilot'
    elif mutation == 'sync_claim': manifest['delivery']['sync_claim'] = 'MEASURED_PARAGRAPH'
    else: manifest['delivery']['features']['read_along'] = 0
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


def test_actual_consumer_source_drift_fails_closed(tmp_path, monkeypatch):
    manifest, reader, listening = candidate(tmp_path)
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


@pytest.mark.parametrize('gate', ['rights','technical_audio','chapter_index','asr_coverage','boundary_order','storage','browser'])
def test_sync_na_never_waives_other_acceptance(tmp_path, gate):
    manifest, reader, listening = candidate(tmp_path)
    if gate == 'rights': manifest['rights']['commercial_use'] = 'UNKNOWN'
    else: manifest['automated_checks'][gate]['status'] = 'NOT_APPLICABLE'
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


def test_warning_only_does_not_create_defect_or_extra_review(tmp_path):
    manifest, reader, listening = candidate(tmp_path)
    manifest['quality_findings'] = [{'id':'word-7','classification':'UNCERTAINTY_WARNING','span':[7,8]}]
    report = evaluate(manifest, tmp_path, reader, listening)
    assert report['release_status'] == 'READY_FOR_GO_LIVE'
    assert report['quality_findings']['warnings'][0]['resolution'] == 'UNCONFIRMED_WARNING_NOT_A_DEFECT'
    assert report['quality_findings']['blockers'] == []


@pytest.mark.parametrize('kind', ['CONFIRMED_MATERIAL_DEFECT','MISSING_MANDATORY_ACCEPTANCE'])
def test_real_defects_and_missing_acceptance_still_block(tmp_path, kind):
    manifest, reader, listening = candidate(tmp_path)
    manifest['quality_findings'] = [{'id':'word-7','classification':kind,'span':[7,8]}]
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'
    with pytest.raises(RuntimeBlocked):
        promote(manifest, {'passed':True,'release_eligible':False,'release_id':'dummy'}, execute=False, promoter=DummyPromoter())


def test_adjudication_is_scoped_reference_not_threshold_or_approval_factory(tmp_path):
    manifest, reader, listening = candidate(tmp_path)
    manifest['quality_findings'] = [{'id':'word-7','classification':'UNCERTAINTY_WARNING','span':[7,8]}]
    manifest['accepted_adjudications'] = [{'finding_id':'word-7','status':'ACCEPTED','span':[7,8],
        'audio_sha256':'a'*64,'manuscript_sha256':manifest['manuscript']['sha256'],'evidence_sha256':'d'*64}]
    findings = policy.classify_quality_findings(manifest)
    assert findings['warnings'][0]['resolution'] == 'EXISTING_SOURCE_BOUND_ADJUDICATION_REFERENCE'
    assert findings['warnings'][0]['acceptance_rechecked_by_classifier'] is False
    manifest['accepted_adjudications'][0]['audio_sha256'] = '0'*64
    assert policy.classify_quality_findings(manifest)['warnings'][0]['resolution'] == 'UNCONFIRMED_WARNING_NOT_A_DEFECT'
    manifest['automated_checks']['asr_coverage']['status'] = 'UNPERFORMED'
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


def test_unclassified_optional_signal_is_not_an_invented_release_gate(tmp_path):
    manifest, reader, listening = candidate(tmp_path)
    manifest['quality_findings'] = [{'id':'uncertain','classification':'UNKNOWN'}]
    report = evaluate(manifest, tmp_path, reader, listening)
    assert report['release_status'] == 'READY_FOR_GO_LIVE'
    assert report['quality_findings']['warnings'][0]['resolution'] == 'UNCLASSIFIED_SIGNAL_NOT_CONFIRMED_DEFECT'


def test_unused_text_sync_cannot_keep_a_contradictory_sync_claim(tmp_path):
    manifest, reader, listening = candidate(tmp_path)
    manifest['audio']['sync_tier'] = 'WORD_OR_PHRASE_SYNC_FLAGSHIP'
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


def test_text_heuristics_warn_but_actual_empty_or_corrupt_input_blocks():
    # Execute the real pure method/constants only; importing the legacy producer
    # would load dotenv/provider dependencies, which this offline test excludes.
    import ast
    import re
    import types
    source = policy.ROOT/'scripts/audiobook_production_pipeline.py'
    tree = ast.parse(source.read_text())
    names = {'SUSPICIOUS_TEXT_PATTERNS', 'REPEATED_LINE_SYMBOL_PATTERNS'}
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)]
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Pipeline')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_is_sanitized_text_valid')
    method.decorator_list = []
    namespace = {'re': re, 'logger': types.SimpleNamespace(warning=lambda *a: None)}
    exec(compile(ast.Module(body=assignments+[method], type_ignores=[]), str(source), 'exec'), namespace)
    validate = namespace['_is_sanitized_text_valid']
    valid, warnings = validate('dummy', 'He wrote about an Exception and json in a story.', 'dummy')
    assert valid and warnings
    for text in ('', 'bad\x00text', 'bad�text'):
        assert validate('dummy', text, 'dummy')[0] is False


def test_bengali_campaign_proven_na_is_not_an_estimated_sync_failure(tmp_path):
    import importlib.util
    path = policy.ROOT/'internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py'
    spec = importlib.util.spec_from_file_location('campaign_applicability_test', path)
    campaign = importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)
    manifest, _, _ = candidate(tmp_path)
    evidence = {'full_pilot_listening_score':9.4,'confidence':0.95,'asr_score':9.8,
                'text_sync_status':'NOT_APPLICABLE','release_manifest':manifest,
                'auto_estimated_sync':True,'upload_checksum_status':'PASS','metadata_status':'PASS','browser_status':'PASS'}
    assert campaign.full_audio_publishable(evidence)[0] is True
    manifest['delivery']['features']['read_along'] = True
    assert campaign.full_audio_publishable(evidence)[0] is False


def test_bengali_low_confidence_diagnostic_does_not_order_regeneration(tmp_path):
    import importlib.util
    path = policy.ROOT/'internal/audiobook_lab/scripts/bengali_asr_normalization.py'
    spec = importlib.util.spec_from_file_location('bengali_diagnostic_test', path)
    import sys
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    report = module.analyze_bengali_asr(slug='dummy',title='Dummy',author='Dummy',language='ben',
        manuscript='গিন্নি ছাত্রবৃত্তি ক্লাসের নীচে আমাদের পণ্ডিত ছিলেন শিবনাথ পণ্ডিত।',
        transcript='this recognizer returned an uncertain unrelated line',raw_asr_score=0.1,run_dir=tmp_path)
    assert report['diagnostic_classification'] == 'UNCERTAINTY_WARNING'
    assert report['mandatory_fidelity_acceptance_status'] == 'NOT_ESTABLISHED_BY_THIS_DIAGNOSTIC'
    assert report['release_pass'] is False
    assert 'no automatic regeneration or retry' in report['recommended_action'] or 'do not mandate' in report['recommended_action']


@pytest.mark.parametrize('value', [1, 'true', None, [], {}])
def test_na_rejects_non_boolean_feature_controls(tmp_path, value):
    manifest, reader, listening = candidate(tmp_path)
    manifest['audio']['highlight_sync_enabled'] = value
    assert evaluate(manifest, tmp_path, reader, listening)['release_status'] == 'BLOCKED'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, 'invalid'])
def test_bengali_scores_must_be_finite_numbers(tmp_path, value):
    import importlib.util
    path = policy.ROOT/'internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py'
    spec = importlib.util.spec_from_file_location('finite_campaign_test', path)
    campaign = importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)
    evidence = {'full_pilot_listening_score':value,'confidence':value,'asr_score':value,
                'upload_checksum_status':'PASS','metadata_status':'PASS','browser_status':'PASS'}
    assert campaign.full_audio_publishable(evidence)[0] is False
    assert campaign.representative_passes({'representative_score':value,'confidence':value})[0] is False


def test_explicit_invalid_bengali_scores_cannot_hide_behind_alias_or_passage_truthiness():
    import importlib.util
    path = policy.ROOT/'internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py'
    spec = importlib.util.spec_from_file_location('strict_campaign_test', path)
    campaign = importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)
    assert campaign.representative_passes({'representative_score':False,'overall_listening_score':9.9,'confidence':0.95})[0] is False
    assert campaign.representative_passes({'representative_score':9.9,'confidence':0.95,'passage_scores':[{'overall_listening_score':0}]})[0] is False
