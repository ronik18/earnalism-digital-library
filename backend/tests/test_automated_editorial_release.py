"""Synthetic local acceptance only: no media inference, accounts or provider I/O."""
import copy
import hashlib
import json

import pytest

from backend.domain.editorial_release_policy import (
    AUTOMATED_EDITORIAL_POLICY, AUTOMATED_EDITORIAL_CHECKS,
)
from backend.domain.audiobook_release import audiobook_release_qa_summary, audiobook_release_qa_blockers
from backend.tests.test_produce_release import _manifest
from backend.tests.test_audiobook_release_conveyor import complete_qa
from scripts.produce_release import evaluate, execute_go_live
from scripts.release_runtime import promote, RuntimeBlocked


def candidate(tmp_path):
    manifest, _ = _manifest(tmp_path)
    master = tmp_path / "synthetic-full-master.bin"
    master.write_bytes(b"synthetic immutable complete-master fixture, not narration")
    manifest.update(editorial_release_policy=AUTOMATED_EDITORIAL_POLICY,
                    owner_public_release_intent=True, release_descriptor_sha256="d" * 64,
                    audio_release_gate_status="PASS")
    manifest["audio"].update(path=master.name, sha256=hashlib.sha256(master.read_bytes()).hexdigest(),
                             package_version="sha256-" + "e" * 64, duration_seconds=10.0)
    # A full master and full objective evidence replace the routine sample set.
    manifest["audio"].pop("review_samples")
    manifest["audio"].pop("sample_set_sha256")
    binding = dict(slug=manifest['slug'], audio_sha256=manifest['audio']['sha256'],
                   manuscript_sha256=manifest['manuscript']['sha256'],
                   package_version=manifest['audio']['package_version'],
                   release_descriptor_sha256=manifest['release_descriptor_sha256'],
                   model=manifest['audio']['model'], voice=manifest['audio']['voice'],
                   duration_seconds=manifest['audio']['duration_seconds'])
    for name in (*manifest['automated_checks'], *AUTOMATED_EDITORIAL_CHECKS):
        path = tmp_path / f'{name}-bound-evidence.json'
        path.write_text(json.dumps({'schema': 'earnalism.automated_release_check.v1',
                                   'check': name, 'status': 'PASS', 'binding': binding}))
        manifest['automated_checks'][name] = dict(status='PASS', evidence_path=path.name,
            evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return manifest


def ready_manifest(manifest, report):
    return {**manifest, "release_status": report["release_status"],
            "artifact_root": report["artifact_root"],
            "automated_checks": report["automated_checks"]}


class FakePromoter:
    def __init__(self):
        self.calls = []

    def promote(self, payload, *, execute):
        self.calls.append((payload, execute))
        return {"status": "LIVE" if execute else "DRY_RUN", "passed": True,
                "network_calls_performed": 0}


def test_new_policy_evaluates_and_promotes_without_owner_packets_or_scores(tmp_path):
    manifest = candidate(tmp_path)
    report = evaluate(manifest, tmp_path, None, None)
    assert report["release_status"] == "READY_FOR_GO_LIVE"
    assert all(row["status"] == "NOT_APPLICABLE" for row in report["human_gates"].values())
    assert report["automated_checks"]["audio_review_samples"]["status"] == "NOT_APPLICABLE"
    fake = FakePromoter()
    promote(ready_manifest(manifest, report),
            {"passed": True, "release_eligible": False, "release_id": "synthetic-stage"},
            execute=False, promoter=fake)
    assert len(fake.calls) == 1 and fake.calls[0][1] is False
    assert "reader_approval" not in manifest and "audio_samples_approval" not in manifest


def test_coordinator_passes_actual_evaluated_checks_to_promotion(tmp_path):
    manifest = candidate(tmp_path)
    report = evaluate(manifest, tmp_path, None, None)
    stage = tmp_path / "stage.json"
    stage.write_text(json.dumps({"passed": True, "release_eligible": False, "release_id": "synthetic"}))
    fake = FakePromoter()
    result = execute_go_live(report, manifest, None, None, stage, promoter=fake)
    assert result["release_status"] == "LIVE"  # Fake result, never actual publication evidence.
    assert fake.calls[0][1] is True and result["promotion"]["network_calls_performed"] == 0


@pytest.mark.parametrize("gate", ["asr_coverage", "boundary_order", "technical_audio", "storage",
                                  "browser", *AUTOMATED_EDITORIAL_CHECKS])
def test_automation_never_waives_required_gate_in_either_consumer(tmp_path, gate):
    manifest = candidate(tmp_path)
    manifest["automated_checks"][gate]["status"] = "UNPERFORMED"
    assert evaluate(manifest, tmp_path, None, None)["release_status"] == "BLOCKED"
    forged = {**manifest, "release_status": "READY_FOR_GO_LIVE"}
    fake = FakePromoter()
    with pytest.raises(RuntimeBlocked):
        promote(forged, {"passed": True, "release_eligible": False, "release_id": "synthetic"},
                execute=False, promoter=fake)
    assert fake.calls == []


@pytest.mark.parametrize("mutation", ["no_master", "wrong_audio_hash", "no_duration", "no_voice",
                                      "no_authority", "held", "wrong_descriptor", "no_package"])
def test_exact_complete_candidate_and_holds_are_required(tmp_path, mutation):
    manifest = candidate(tmp_path)
    if mutation == "no_master": manifest["audio"].pop("path")
    elif mutation == "wrong_audio_hash": manifest["audio"]["sha256"] = "f" * 64
    elif mutation == "no_duration": manifest["audio"].pop("duration_seconds")
    elif mutation == "no_voice": manifest["audio"].pop("voice")
    elif mutation == "no_authority": manifest["owner_public_release_intent"] = False
    elif mutation == "held": manifest["release_holds"] = ["OWNER_HOLD"]
    elif mutation == "wrong_descriptor": manifest["release_descriptor_sha256"] = "not-a-hash"
    else: manifest["audio"].pop("package_version")
    assert evaluate(manifest, tmp_path, None, None)["release_status"] == "BLOCKED"


def test_warning_is_advisory_but_confirmed_defect_and_rights_failure_block(tmp_path):
    manifest = candidate(tmp_path)
    manifest["quality_findings"] = [{"id": "uncertain-word", "classification": "UNCERTAINTY_WARNING"}]
    assert evaluate(manifest, tmp_path, None, None)["release_status"] == "READY_FOR_GO_LIVE"
    manifest["quality_findings"][0]["classification"] = "CONFIRMED_MATERIAL_DEFECT"
    assert evaluate(manifest, tmp_path, None, None)["release_status"] == "BLOCKED"
    manifest.pop("quality_findings")
    manifest["rights"]["commercial_use"] = "UNKNOWN"
    assert evaluate(manifest, tmp_path, None, None)["release_status"] == "BLOCKED"


def test_legacy_and_unknown_policy_do_not_acquire_new_exemption(tmp_path):
    manifest, _ = _manifest(tmp_path)
    assert evaluate(manifest, tmp_path, None, None)["human_gates"]["audio_samples"]["status"] == "PENDING"
    manifest["editorial_release_policy"] = "invented"
    with pytest.raises(ValueError, match="Unsupported editorial"):
        evaluate(manifest, tmp_path, None, None)


def test_backend_keeps_scores_optional_and_historical_without_inventing_qa():
    qa = complete_qa(editorial_release_policy=AUTOMATED_EDITORIAL_POLICY)
    qa.pop("overall_score")
    qa.pop("confidence")
    kwargs = dict(title_slug='pilot', audio_sha256='a'*64,
                  manuscript_sha256='b'*64, attempt_fingerprint='c'*64)
    binding = dict(slug='pilot', audio_sha256='a'*64,
                   manuscript_sha256='b'*64, attempt_fingerprint='c'*64)
    qa['automated_acceptance'] = {name:dict(schema='earnalism.automated_release_check.v1',
        check=name,status='PASS',binding=binding,evidence_sha256='d'*64)
        for name in AUTOMATED_EDITORIAL_CHECKS}
    summary = audiobook_release_qa_summary(qa)
    assert summary["listening_score"] is None and summary["listening_confidence"] is None
    assert audiobook_release_qa_blockers(summary, **kwargs) == []
    for field, value, expected in [("asr_manuscript_score", 0.5, "ASR manuscript"),
                                    ("ordered_content_integrity", False, "Ordered manuscript"),
                                    ("fatal_flags", {"clipping": True}, "Fatal listening")]:
        issues = audiobook_release_qa_blockers(audiobook_release_qa_summary({**qa, field: value}), **kwargs)
        assert any(expected in issue for issue in issues)
    legacy = dict(qa)
    legacy.pop("editorial_release_policy")
    assert any("listening score" in issue for issue in audiobook_release_qa_blockers(audiobook_release_qa_summary(legacy)))


@pytest.mark.parametrize('change', ['master','source','voice','model','duration','descriptor','package'])
def test_changed_candidate_cannot_reuse_previous_automated_evidence(tmp_path, change):
    manifest = candidate(tmp_path)
    if change in ('master', 'source'):
        part = manifest['audio' if change == 'master' else 'manuscript']
        path = tmp_path / part['path']
        path.write_bytes(b'different genuine candidate fixture')
        part['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif change in ('voice','model'):
        manifest['audio'][change] = 'different-qualified-option'
    elif change == 'duration': manifest['audio']['duration_seconds'] = 11.0
    elif change == 'descriptor': manifest['release_descriptor_sha256'] = 'f'*64
    else: manifest['audio']['package_version'] = 'sha256-'+'f'*64
    report = evaluate(manifest, tmp_path, None, None)
    assert report['release_status'] == 'BLOCKED'
    fake = FakePromoter()
    with pytest.raises(RuntimeBlocked):
        promote({**ready_manifest(manifest, report),'release_status':'READY_FOR_GO_LIVE'},
                {'passed':True,'release_eligible':False,'release_id':'synthetic'},
                execute=False,promoter=fake)
    assert fake.calls == []


@pytest.mark.parametrize('change', ['evidence','master'])
def test_promotion_rechecks_bytes_after_evaluation(tmp_path, change):
    manifest = candidate(tmp_path)
    report = evaluate(manifest, tmp_path, None, None)
    assert report['release_status'] == 'READY_FOR_GO_LIVE'
    path = (tmp_path / manifest['audio']['path'] if change == 'master'
            else tmp_path / manifest['automated_checks']['accounting']['evidence_path'])
    path.write_bytes(b'changed after evaluation')
    fake = FakePromoter()
    with pytest.raises(RuntimeBlocked):
        promote(ready_manifest(manifest,report),
                {'passed':True,'release_eligible':False,'release_id':'synthetic'},
                execute=False,promoter=fake)
    assert fake.calls == []


@pytest.mark.parametrize('missing', AUTOMATED_EDITORIAL_CHECKS)
def test_backend_mode_cannot_omit_script_policy_obligations(missing):
    qa = complete_qa(editorial_release_policy=AUTOMATED_EDITORIAL_POLICY)
    # No human scores or owner packet can stand in for exact automated acceptance.
    qa['automated_acceptance'] = {}
    issues = audiobook_release_qa_blockers(audiobook_release_qa_summary(qa),
        title_slug='pilot',audio_sha256='a'*64,manuscript_sha256='b'*64,attempt_fingerprint='c'*64)
    assert f'Candidate-bound automated acceptance is required: {missing}.' in issues


@pytest.mark.parametrize('field', ['slug','audio_sha256','manuscript_sha256','attempt_fingerprint'])
def test_backend_rejects_automated_evidence_from_another_candidate(field):
    binding=dict(slug='pilot',audio_sha256='a'*64,manuscript_sha256='b'*64,attempt_fingerprint='c'*64)
    wrong={**binding,field:'other' if field=='slug' else 'f'*64}
    qa=complete_qa(editorial_release_policy=AUTOMATED_EDITORIAL_POLICY,
        automated_acceptance={name:dict(schema='earnalism.automated_release_check.v1',
            check=name,status='PASS',binding=wrong,evidence_sha256='d'*64)
            for name in AUTOMATED_EDITORIAL_CHECKS})
    issues=audiobook_release_qa_blockers(audiobook_release_qa_summary(qa),
        title_slug='pilot',audio_sha256='a'*64,manuscript_sha256='b'*64,attempt_fingerprint='c'*64)
    assert len([x for x in issues if 'Candidate-bound automated acceptance' in x])==5
