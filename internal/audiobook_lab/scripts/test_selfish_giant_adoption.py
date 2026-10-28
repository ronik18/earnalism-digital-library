"""Exact committed source adoption checks; no storage, audio synthesis or release."""
import copy, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import owner_produced_package as o
from rights_decision_gate import evaluate_accepted_record, load_production_registry, load_audio_package_binding
C = o.REGISTRY.parent / "selfish-giant-20261029"
def read(name): return json.loads((C/name).read_text())
def test_exact_canonical_adoption_and_evidence():
    a = o.load_adoption("the-selfish-giant")
    d = read("release-descriptor.json")
    p = read("delivery-mapping.json")
    assert o.validate(d, p, "en", o.DOWNSTREAM) == d
    assert load_audio_package_binding("the-selfish-giant",o.sha(o.canonical(d)))["decision_id"] == a["audio_use_decision"]["decision_id"]
    assert a["audio_use_decision"]["valid_until"] == "LIFETIME"
    assert a["audio_use_decision"]["territories"] == ["IN"]
    assert a["audio_use_decision"]["uses"] == ["audio_stream"]
    for role, digest in a["evidence_sha256"].items():
        assert hashlib.sha256((C/"evidence"/(role+".json")).read_bytes()).hexdigest() == digest
    assert o.sha(o.canonical(read("source-units.json"))) == d["source_units_sha256"]
    assert d["release_candidate_evidence"]["human_scores"] is None
    assert d["known_release_blockers"] == o.DOWNSTREAM
def test_actual_lifetime_rights_remain_revocable_and_scoped():
    a=o.load_adoption("the-selfish-giant");r=a["audio_use_decision"];accepted,revoked=load_production_registry()
    args=dict(edition_id="the-selfish-giant", operator_id="reo-enterprise",country="IN",country_trusted=True,use="audio_stream",required_components=r["components"],accepted_records=accepted,revoked_decision_ids=revoked,now=datetime(2099,1,1,tzinfo=timezone.utc))
    assert evaluate_accepted_record(r,**args).passed
    for change in ({"country":"US"},{"use":"audio_download"},{"revoked_decision_ids":frozenset({r["decision_id"]})},{"accepted_records":{}},{"required_components":{"master_wav":"0"*64}}):
        assert not evaluate_accepted_record(r,**{**args,**change}).passed
