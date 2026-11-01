"""Prepare exact retained-master source candidates without provider/publication APIs.

Frozen parent policies remain unchanged. Source adoption, production storage and
current runtime/publication acceptance are separate, independently enforced gates.
"""

import argparse, copy, hashlib, importlib.util, json, sys
from pathlib import Path

POLICY = "retained_master_continuous_derivative.v1"
PINS = {
    "the-open-window": {
        "parent": "sha256-8e5c83a835cf8bea0a34809f8640603a2158a3cfe1aa8f1ac71117259a665b26",
        "descriptor": "028f65d8551523eecaad03bb5b476070f0c48c1fb0771bf9abc9163ecd5ba4b2",
        "master": "1fd37c818d4869eac8548811c714bd8907d0753ffa31b37fbf63d6e4764059a5",
        "source": "058d0cda5a3c8449cbce06e0698048251881be4c6fc8d06fd0bc3a1bb8ec8587",
        "manuscript": "f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be",
        "duration": 491436,
        "units": 29,
    },
    "the-selfish-giant": {
        "parent": "sha256-b00212b82996e194a7b3bef4f3fb8982304b71afcd32e5f0fa6e93e9341f3211",
        "descriptor": "b5b378168211d61ac80341e74cbfacaf0d5590a18300a5c91db4684626e343a2",
        "master": "8cbaecc48b84372dcab020b4514d2e50c4a6f386018de573baa98bb7e7fb6d0b",
        "source": "77ae1b3c7be77aea82b1f935e531e53f4df43db572cbc14af39d6cd0d5ba50da",
        "manuscript": "c55bef9dcd5883e156af940deb849c67a78a8fae7fc7a1e50ea814aa9ce866c5",
        "duration": 777120,
        "units": 20,
    },
}
for _slug, _pins in {
    "the-open-window": {
        "adoption": "1c5063691e41912d7fb5222bd98cc8ff6f6a562b4be17d9965cbf5587050f413",
        "proofs": {
            "playback": "9e22caeee79f48e3205b570aabd375e529f5d7c8b187efb9f1e305131df497f7",
            "business": "8a76633e77649a90dac618438ec6eb67faaebdeb1a5fd3c26b2fab4cf9068d7f",
            "accounting": "9f4d9a53868cfdd5b7f532558297d93878c12efda0fc1ff17534fb4febb4722b",
        },
    },
    "the-selfish-giant": {
        "adoption": "d09c3445e1d063f3044752190659eaef77548dd0b661b351be202b3cb3b08b3e",
        "proofs": {
            "playback": "ac7b16224cfe3fb132ee3430c4f2ceb0469341d1ce13b4e67fb849e3a3f0494a",
            "business": "bf5aacc8a7e57f942b111624850c189df01536edafd8fffe34b791702ce69d34",
            "accounting": "f1248949aba26b0de60d673316af34987e88cf92b475b6cacb7b71b7d7280c44",
        },
    },
}.items():
    PINS[_slug].update(_pins)


# Immutable historical parent acceptance, independent of the current live pointer.
for _slug, _archival in {
    "the-open-window": {
        "acceptance": "ba06a56438d38e6ee8eef6de339772821fecaf9713dc563bf57a379862b0f0ab",
        "rights_record": "7f00f2deb1d2ab014801e5154429983bb9198324d8a8c37e17e7cae5a1511cef",
        "rights_decision": "india-20261020-the-open-window-corrected-v1-audio-owner-adopted",
    },
    "the-selfish-giant": {
        "acceptance": "322c2d7b716bdd2515c0672d1246a78bde24d075bb5ad2f23b703ba2add628d1",
        "rights_record": "a64ee8743c69afe896265ef97b0cfca58759fddfe0a3eac04c1cf668f58a0c3c",
        "rights_decision": "india-20261029-the-selfish-giant-owner-produced-audio-control",
    },
}.items():
    PINS[_slug].update(_archival)


def archival_parent_approval(slug):
    pin = PINS[slug]
    return {
        "acceptance_sha256": pin["acceptance"],
        "audio_rights_record_sha256": pin["rights_record"],
        "audio_rights_decision_id": pin["rights_decision"],
    }


def canonical(v):
    return json.dumps(
        v, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def require(v, m):
    if not v:
        raise ValueError(m)


def qualify_parent(repo, slug, parent):
    repo = Path(repo)
    sys.path.insert(0, str(repo / "internal/audiobook_lab/scripts"))
    native(repo)
    import audiobook_active_release_v2 as manager

    p = PINS[slug]
    n = native(repo)
    require(parent.get("package_version") == p["parent"], "wrong exact parent package")
    n.validate_audiobook_package(
        parent,
        expected_slug=slug,
        expected_source_sha256=p["source"],
        expected_manuscript_sha256=p["manuscript"],
        expected_release_descriptor_sha256=p["descriptor"],
    )
    gate = repo / "internal/audiobook_lab/release_gate"
    descpath = gate / (
        "open_window_listened_successor_v2/release-descriptor.json"
        if slug == "the-open-window"
        else "selfish-giant-20261029/release-descriptor.json"
    )
    desc = json.loads(descpath.read_text())
    require(sha(canonical(desc)) == p["descriptor"], "frozen parent descriptor changed")
    registry = gate / (
        "open_window_successor_adoptions.json"
        if slug == "the-open-window"
        else "owner_produced_package_adoptions.json"
    )
    entries = json.loads(registry.read_text())["adoptions"]
    matched = [e for e in entries if e["record_sha256"] == p["adoption"]]
    require(
        len(matched) == 1 and sha(canonical(matched[0]["record"])) == p["adoption"],
        "trusted parent adoption changed",
    )
    approval = archival_parent_approval(slug)
    rights = matched[0]["record"]["audio_use_decision"]
    require(
        approval.get("audio_rights_record_sha256") == sha(canonical(rights))
        and approval.get("audio_rights_decision_id") == rights["decision_id"],
        "parent rights marker mismatch",
    )
    # This dispatch invokes the UNCHANGED frozen editorial/native India rights gates.
    manager.validate_qa_candidate_release_descriptor(
        desc, parent, controlled_language="en"
    )
    proofdir = gate / (
        "open_window_publication_evidence_20261026"
        if slug == "the-open-window"
        else "selfish-giant-20261029/production-acceptance"
    )
    proofs = {
        k: (proofdir / (k + ".json")).read_bytes()
        for k in ["playback", "business", "accounting"]
    }
    require(
        all(sha(proofs[k]) == p["proofs"][k] for k in proofs),
        "trusted parent native proof changed",
    )
    acceptance = manager.validate_new_title_publication_acceptance(
        descriptor=p["descriptor"],
        package_version=p["parent"],
        duration_ms=p["duration"],
        segment_ids=[c["segment_id"] for t in parent["tracks"] for c in t["chunks"]],
        playback_bytes=proofs["playback"],
        business_bytes=proofs["business"],
        accounting_bytes=proofs["accounting"],
        expected_proof_hashes=p["proofs"],
    )
    require(
        sha(canonical(acceptance)) == approval["acceptance_sha256"],
        "parent acceptance marker mismatch",
    )
    return {
        "parent_adoption_record_sha256": p["adoption"],
        "parent_descriptor_sha256": p["descriptor"],
        "native_editorial_and_india_rights_validated": True,
        "native_production_acceptance_validated": True,
        "native_production_acceptance_scope": "HISTORICAL_EXACT_PARENT_ONLY_NOT_NEW_TOPOLOGY_OR_CURRENT_RUNTIME",
        "parent_proof_sha256": p["proofs"],
        "parent_acceptance_sha256": sha(canonical(acceptance)),
    }


def native(repo):
    sys.path.insert(0, str(Path(repo) / "backend"))
    import audiobook_packages as n

    return n


def bindings(slug, parent, master, source, timing):
    require(slug in PINS, "unsupported title")
    p = PINS[slug]
    require(
        parent["slug"] == slug
        and parent["package_version"] == p["parent"]
        and parent["release_descriptor_sha256"] == p["descriptor"],
        "invalid accepted parent/title",
    )
    require(
        parent["source_sha256"] == p["source"]
        and parent["manuscript_sha256"] == p["manuscript"],
        "changed accepted source",
    )
    require(sha(master) == p["master"], "wrong retained master")
    require(sha(source.encode()) == p["manuscript"], "changed manuscript")
    require(len(timing) == p["units"], "measured unit count")
    end = 0
    source_end = 0
    recovered = []
    for u in timing:
        require(
            type(u["start_ms"]) is int
            and type(u["end_ms"]) is int
            and u["start_ms"] == end
            and u["end_ms"] > end,
            "invalid measured timing",
        )
        end = u["end_ms"]
        start = u["source_char_start"]
        stop = u["source_char_end"]
        require(
            type(start) is int
            and type(stop) is int
            and source_end <= start < stop <= len(source),
            "invalid measured source offsets",
        )
        require(
            not source[source_end:start].strip(),
            "omitted source between measured units",
        )
        require(bool(source[start:stop].strip()), "empty measured source unit")
        recovered.append(source[start:stop])
        source_end = stop
    require(end == p["duration"], "measured duration mismatch")
    require(
        not source[source_end:].strip()
        and " ".join(" ".join(recovered).split()) == " ".join(source.split()),
        "missing duplicated or reordered measured source words",
    )
    return p


def prepare(repo, slug, master_path, timing_path, out):
    n = native(repo)
    repo = Path(repo)
    out = Path(out)
    require(not out.exists(), "output exists; preserve")
    book = json.loads(
        (
            repo / "backend/data/controlled_publications" / slug / "public_book.json"
        ).read_text()
    )
    p = PINS[slug]
    parent = book["audiobook_packages"][p["descriptor"]]
    n.validate_audiobook_package(
        parent,
        expected_slug=slug,
        expected_source_sha256=p["source"],
        expected_manuscript_sha256=p["manuscript"],
        expected_release_descriptor_sha256=p["descriptor"],
    )
    approval = archival_parent_approval(slug)
    parent_proof = qualify_parent(repo, slug, parent)
    source = json.loads(
        (
            repo
            / "backend/data/controlled_publications"
            / slug
            / "chapters/chapter-001.json"
        ).read_text()
    )["content"]
    master_path = Path(master_path)
    master = master_path.read_bytes()
    timing = json.loads(Path(timing_path).read_text())
    bindings(slug, parent, master, source, timing)
    # Timing input is independently tied to immutable retained timing evidence, not arbitrary estimates.
    lock = json.loads(
        (Path(__file__).parent / "retained-timing-locks.json").read_text()
    )
    require(sha(canonical(timing)) == lock[slug], "changed retained measured timing")
    out.mkdir()
    descriptor = {
        "schema_version": "audiobook_release_descriptor.v1",
        "derivative_schema": "earnalism.retained-master-derivative-descriptor.v1",
        "release_candidate_status": "DRAFT_ADOPTION_PENDING",
        "release_candidate_evidence": {
            "acceptance_policy": POLICY,
            "status": "DERIVATIVE_ADOPTION_PENDING",
        },
        "policy": POLICY,
        "slug": slug,
        "parent_package_version": p["parent"],
        "parent_release_descriptor_sha256": p["descriptor"],
        "parent_public_acceptance_sha256": approval["acceptance_sha256"],
        "parent_rights_record_sha256": approval["audio_rights_record_sha256"],
        "controlled_source_sha256": p["source"],
        "manuscript_sha256": p["manuscript"],
        "master_mp3_sha256": p["master"],
        "duration_ms": p["duration"],
        "retained_measured_bounds_sha256": sha(canonical(timing)),
        "retained_unit_count": p["units"],
        "sync_tier": "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
        "highlight_sync_enabled": False,
        "voice_rights_covers_source_unchanged": True,
        "territories": ["IN"],
        "publication_approved": False,
        "required_gates": [
            "DERIVATIVE_POLICY_ADOPTION",
            "EXACT_DERIVATIVE_RIGHTS_BINDING",
            "PRIMARY_AND_DR_EXACT_RECEIPTS",
            "FULL_CRITICAL_REVIEW_OR_VALID_UNCHANGED_REUSE",
            "PROTECTED_RUNTIME_ACCEPTANCE",
            "SERIAL_RELEASE_VERIFICATION",
        ],
    }
    descriptor["parent_qualification"] = parent_proof
    sid = "chapter-001-full"
    sidecars = {
        "timestamps": {
            "schema": "earnalism.source-unit-group-timing.v1",
            "segment_id": sid,
            "duration_ms": p["duration"],
            "sync_tier": "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
            "highlight_sync_enabled": False,
            "source_start": 0,
            "source_end": len(source),
            "start_paragraph": 0,
            "end_paragraph": parent["paragraph_count"] - 1,
            "cues": [
                {
                    "id": unit["id"],
                    "start_ms": unit["start_ms"],
                    "end_ms": unit["end_ms"],
                    "source_char_start": unit["source_char_start"],
                    "source_char_end": unit["source_char_end"],
                    "text": source[unit["source_char_start"] : unit["source_char_end"]],
                    "scope": "ENTIRE_MEASURED_SOURCE_UNIT_NOT_WORD_OR_INTERNAL_PARAGRAPH_SYNC",
                }
                for unit in timing
            ],
            "retained_measured_units": timing,
        },
        "metadata": {
            "schema": "earnalism.retained-master-delivery.v1",
            "policy": POLICY,
            "slug": slug,
            "segment_id": sid,
            "master_mp3_sha256": p["master"],
            "parent_package_version": p["parent"],
            "duration_ms": p["duration"],
            "measured_bounds_sha256": sha(canonical(timing)),
            "new_synthesis": False,
            "new_encoding": False,
        },
    }

    def vt(ms):
        return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}"

    files = {"audio": master_path}
    mimes = {
        "audio": "audio/mpeg",
        "timestamps": "application/json",
        "vtt": "text/vtt",
        "metadata": "application/json",
    }
    for role, data in sidecars.items():
        files[role] = out / (sid + "." + role + ".json")
        files[role].write_bytes(canonical(data))
    files["vtt"] = out / (sid + ".vtt")
    files["vtt"].write_text(
        "WEBVTT\n\n"
        + "\n\n".join(
            unit["id"]
            + "\n"
            + vt(unit["start_ms"])
            + " --> "
            + vt(unit["end_ms"])
            + "\n"
            + " ".join(
                source[unit["source_char_start"] : unit["source_char_end"]].split()
            )
            for unit in timing
        )
        + "\n"
    )
    descriptor["delivery_sidecar_sha256"] = {
        role: sha(path.read_bytes()) for role, path in files.items() if role != "audio"
    }
    dh = sha(canonical(descriptor))
    prefix = n.immutable_release_prefix(slug, dh)
    assets = []
    chunk_assets = {}
    ids = {}
    for role, path in files.items():
        raw = path.read_bytes()
        aid = sid + "-" + role
        key = prefix + "delivery/" + aid + "-sha256-" + sha(raw) + path.suffix
        fact = {"sha256": sha(raw), "size_bytes": len(raw), "mime_type": mimes[role]}
        assets.append({"asset_id": aid, "local_path": str(path), "key": key, **fact})
        ids[role] = aid
        # Explicit unuploaded structural fixture, NEVER an asserted storage version/receipt.
        chunk_assets[role] = {
            **fact,
            "storage": {
                "store": "draft-primary",
                "bucket": "draft-not-uploaded-primary",
                "key": key,
                "version_id": "DRAFT-NOT-UPLOADED",
            },
            "replicas": [
                {
                    "store": "draft-dr",
                    "bucket": "draft-not-uploaded-dr",
                    "key": key,
                    "version_id": "DRAFT-NOT-UPLOADED",
                }
            ],
        }
    chunk = {
        "segment_id": sid,
        "order": 0,
        "start_word": 0,
        "end_word": parent["word_count"] - 1,
        "start_paragraph": 0,
        "end_paragraph": parent["paragraph_count"] - 1,
        "cumulative_start_ms": 0,
        "duration_ms": p["duration"],
    }
    track = {k: v for k, v in parent["tracks"][0].items() if k != "chunks"}
    track["chunks"] = [{**chunk, "assets": chunk_assets}]
    package = {
        **{k: v for k, v in parent.items() if k not in ["package_version", "tracks"]},
        "release_descriptor_sha256": dh,
        "release_evidence_version": POLICY,
        "segment_count": 1,
        "tracks": [track],
    }
    package = n.with_canonical_package_version(package)
    outcome = {
        "draft_only": True,
        "storage_uploaded": False,
        "release_approved": False,
        "validation": "NATIVE_SCHEMA_PASS_WITH_EXPLICIT_UNUPLOADED_STORAGE_FIXTURES",
        "production_finalize_allowed": False,
    }
    try:
        n.validate_audiobook_package(
            package,
            expected_slug=slug,
            expected_source_sha256=p["source"],
            expected_manuscript_sha256=p["manuscript"],
            expected_release_descriptor_sha256=dh,
        )
    except n.AudiobookPackageValidationError as e:
        outcome["validation"] = "BLOCKED_NATIVE_VALIDATOR"
        outcome["error"] = str(e)
    track["chunks"] = [{**chunk, "asset_ids": ids}]
    semantics = {
        **{k: v for k, v in package.items() if k not in ["package_version", "tracks"]},
        "schema_version": "audiobook_package_semantics.v2",
        "package_schema_version": n.PACKAGE_SCHEMA_VERSION,
        "tracks": [track],
    }
    plan = {
        "schema_version": "audiobook_package_upload_plan.v2",
        "slug": slug,
        "release_descriptor_sha256": dh,
        "immutable_prefix": prefix,
        # Source adoption is a separate reviewed action. A prepared draft must
        # not become production-upload eligible merely by supplying profiles.
        "release_status": "SOURCE_ADOPTION_PENDING",
        "assets": assets,
    }
    proposal = {
        "schema": "earnalism.retained-master-derivative-adoption.v1",
        "status": "PENDING_REVIEW_NOT_ACCEPTED",
        "descriptor_sha256": dh,
        "parent_package_version": p["parent"],
        "exact_master_sha256": p["master"],
        "policy": POLICY,
    }
    for name, v in [
        ("release-descriptor.json", descriptor),
        ("upload-plan.json", plan),
        ("package-semantics.json", semantics),
        ("STRUCTURAL-DRAFT-NOT-UPLOADED.json", package),
        ("adoption-proposal.json", proposal),
        ("validation-result.json", outcome),
    ]:
        (out / name).write_text(json.dumps(v, indent=2) + "\n")
    return outcome


def validate_reviewed_adoption(descriptor, registry_path=None):
    require(registry_path is None, "adoption override forbidden")
    slug = descriptor.get("slug")
    require(slug in PINS, "unsupported derivative adoption title")
    pin = PINS[slug]
    require(
        descriptor.get("policy") == POLICY
        and descriptor.get("parent_package_version") == pin["parent"]
        and descriptor.get("parent_release_descriptor_sha256") == pin["descriptor"]
        and descriptor.get("master_mp3_sha256") == pin["master"]
        and descriptor.get("controlled_source_sha256") == pin["source"]
        and descriptor.get("manuscript_sha256") == pin["manuscript"],
        "derivative adoption identity mismatch",
    )
    path = (
        Path(__file__).resolve().parents[1]
        / "release_gate/retained_master_derivative_adoptions.json"
    )
    require(path.is_file(), "new derivative adoption registry unavailable")
    registry = json.loads(path.read_text())
    require(
        registry.get("schema") == "earnalism.retained-master-derivative-adoptions.v1",
        "adoption registry schema",
    )
    dh = sha(canonical(descriptor))
    matches = []
    for entry in registry.get("adoptions", []):
        record = entry.get("record", {})
        require(
            entry.get("record_sha256") == sha(canonical(record)),
            "derivative adoption record digest mismatch",
        )
        if record.get("descriptor_sha256") == dh and record.get("status") == "ADOPTED":
            matches.append(record)
    require(len(matches) == 1, "exact reviewed derivative adoption required")
    return matches[0]


def validate(descriptor, package, controlled_language, downstream_gates):
    """Release-manager dispatch: explicit trusted derivative adoption and native rights.
    No old policy, descriptor flag or mutable publication marker grants this approval.
    """
    repo = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "backend/audiobook_packages.py").is_file()
        ),
        None,
    )
    require(repo is not None, "shipped derivative repository context unavailable")
    n = native(repo)
    slug = descriptor.get("slug")
    require(slug in PINS, "unsupported derivative title")
    pin = PINS[slug]
    require(
        str(controlled_language).lower() in ["en", "eng", "english"],
        "English derivative only",
    )
    n.validate_audiobook_package(
        package,
        expected_slug=slug,
        expected_source_sha256=pin["source"],
        expected_manuscript_sha256=pin["manuscript"],
        expected_release_descriptor_sha256=sha(canonical(descriptor)),
    )
    require(
        package["segment_count"] == 1
        and package["duration_ms"] == pin["duration"]
        and package["highlight_sync_enabled"] is False
        and package["sync_tier"] == "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
        "continuous exact timing identity",
    )
    chunks = [c for t in package["tracks"] for c in t["chunks"]]
    require(
        len(chunks) == 1 and chunks[0]["assets"]["audio"]["sha256"] == pin["master"],
        "continuous unchanged master required",
    )
    require(
        {k: v["sha256"] for k, v in chunks[0]["assets"].items() if k != "audio"}
        == descriptor.get("delivery_sidecar_sha256"),
        "derivative source-bound sidecar identity",
    )
    lock = json.loads(
        (Path(__file__).parent / "retained-timing-locks.json").read_text()
    )
    require(
        descriptor.get("retained_measured_bounds_sha256") == lock[slug]
        and descriptor.get("retained_unit_count") == pin["units"],
        "retained measured source bounds changed",
    )
    book = json.loads(
        (
            repo / "backend/data/controlled_publications" / slug / "public_book.json"
        ).read_text()
    )
    parent = book["audiobook_packages"][pin["descriptor"]]
    proof = qualify_parent(repo, slug, parent)
    require(
        descriptor.get("parent_qualification") == proof,
        "parent native qualification binding",
    )
    record = validate_reviewed_adoption(descriptor)
    import owner_produced_package as owner
    from rights_decision_gate import load_production_registry, evaluate_accepted_record
    from datetime import datetime, timezone

    require(
        record.get("scope") == "SOURCE_QA_ONLY_STORAGE_AND_RUNTIME_PENDING"
        and record.get("all_release_gates_passed") is False
        and descriptor.get("publication_approved") is False
        and descriptor.get("release_candidate_status")
        == "RETAINED_MASTER_SOURCE_QA_ADOPTED_STORAGE_PENDING"
        and descriptor.get("known_release_blockers") == owner.DOWNSTREAM
        and descriptor.get("release_candidate_evidence", {}).get(
            "all_release_gates_passed"
        )
        is False,
        "Source-only adoption must retain every downstream release gate",
    )

    require(
        record.get("policy") == POLICY
        and record.get("parent_adoption_record_sha256") == pin["adoption"]
        and record.get("derivative_mapping_sha256") == owner.mapping(package),
        "reviewed derivative topology binding required",
    )
    require(
        downstream_gates == owner.DOWNSTREAM,
        "unchanged downstream release gates required",
    )
    accepted, revoked = load_production_registry()
    parentdesc = proof["parent_descriptor_sha256"]
    original = json.loads(
        (
            repo
            / "internal/audiobook_lab/release_gate"
            / (
                "open_window_listened_successor_v2/release-descriptor.json"
                if slug == "the-open-window"
                else "selfish-giant-20261029/release-descriptor.json"
            )
        ).read_text()
    )
    rights = record.get("audio_use_decision")
    components = {
        "source_file": pin["source"],
        "selected_manuscript": pin["manuscript"],
        "master_mp3": pin["master"],
        "master_wav": original["master_wav_sha256"],
        "audio_component_bindings": owner.mapping(package),
    }
    verdict = evaluate_accepted_record(
        rights,
        edition_id=slug,
        operator_id="reo-enterprise",
        country="IN",
        country_trusted=True,
        use="audio_stream",
        required_components=components,
        accepted_records=accepted,
        revoked_decision_ids=revoked,
        now=datetime.now(timezone.utc),
    )
    require(
        verdict.passed
        and rights.get("territories") == ["IN"]
        and rights.get("uses") == ["audio_stream"],
        "exact derivative India rights trust binding denied",
    )
    return copy.deepcopy(descriptor)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--repo", required=True)
    a.add_argument("--slug", choices=PINS, required=True)
    a.add_argument("--master", required=True)
    a.add_argument("--timing", required=True)
    a.add_argument("--output-dir", required=True)
    v = a.parse_args()
    print(
        json.dumps(prepare(v.repo, v.slug, v.master, v.timing, v.output_dir), indent=2)
    )
