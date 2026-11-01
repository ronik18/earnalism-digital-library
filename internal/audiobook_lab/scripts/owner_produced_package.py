"""Prepare immutable owner-produced source-unit packages; never synthesize or publish.

A separately reviewed shipped adoption binds exact source, masters, unit mapping,
model/licences and actual QA. Only the exact reviewed Selfish Giant source candidate is admitted; downstream
storage and publication gates remain mandatory.
Google numeric policy and Open Window's frozen successor remain unchanged.
"""

from __future__ import annotations
import argparse, copy, hashlib, json, re, struct, subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
from rights_decision_gate import evaluate_accepted_record, load_production_registry
from audiobook_packages import (
    validate_audiobook_package,
    AudiobookPackageValidationError,
    segment_duration_limit_ms,
)

POLICY = "owner_produced_source_units.v1"
REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "release_gate/owner_produced_package_adoptions.json"
)
DOWNSTREAM = [
    "PRIVATE_B2_PRIMARY_UPLOAD_REQUIRED",
    "PRIVATE_B2_DR_REPLICA_REQUIRED",
    "CONTROLLED_RELEASE_ACTIVATION_REQUIRED",
    "PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED",
]
ALLOWED_SLUGS = {"the-selfish-giant"}
ROLES = {
    "audio": "audio/mpeg",
    "timestamps": "application/json",
    "vtt": "text/vtt",
    "metadata": "application/json",
}
EVIDENCE_ROLES = {
    "generation_provenance",
    "objective_qa",
    "material_wording_review",
    "voice_direction_acceptance",
    "model_voice_licence",
    "source_edition",
    "cover_reuse",
    "producer_authority",
}


class OwnerProducedError(ValueError):
    pass


def canonical(v):
    return json.dumps(
        v, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def validsha(v):
    return (
        isinstance(v, str) and bool(re.fullmatch("[a-f0-9]{64}", v)) and v != "0" * 64
    )


def require(ok, message):
    if not ok:
        raise OwnerProducedError(message)


def load_adoption(slug):
    try:
        r = json.loads(REGISTRY.read_text())
        require(
            r["schema"] == "earnalism.owner-produced-adoptions.v1",
            "Adoption registry schema",
        )
        entries = [x for x in r["adoptions"] if x["record"]["identity"]["slug"] == slug]
        require(len(entries) == 1, "Exactly one reviewed adoption required")
        e = entries[0]
        require(
            validsha(e["record_sha256"])
            and sha(canonical(e["record"])) == e["record_sha256"],
            "Adoption changed",
        )
        return e["record"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as e:
        raise OwnerProducedError("Reviewed adoption unavailable") from None


def mapping(package):
    """Storage-independent exact delivery mapping, reusing retained successor semantics."""
    tracks = []
    for t in package["tracks"]:
        chunks = []
        for c in t["chunks"]:
            assets = {
                r: {k: a[k] for k in ("sha256", "size_bytes", "mime_type")}
                for r, a in c["assets"].items()
            }
            chunks.append(
                {**{k: v for k, v in c.items() if k != "assets"}, "assets": assets}
            )
        tracks.append(
            {**{k: v for k, v in t.items() if k != "chunks"}, "chunks": chunks}
        )
    return sha(canonical(tracks))


def validate_topology(package):
    word = paragraph = elapsed = count = 0
    seen = set()
    require(
        package.get("highlight_sync_enabled") is False
        and package.get("sync_tier") == "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
        "Package sync claim",
    )
    require(bool(package["tracks"]), "Empty tracks")
    for ti, t in enumerate(package["tracks"]):
        require(
            t["order"] == ti
            and t["start_word"] == word
            and t["start_paragraph"] == paragraph
            and bool(t["chunks"]),
            "Track continuity",
        )
        for ci, c in enumerate(t["chunks"]):
            sid = c["segment_id"]
            require(
                isinstance(sid, str)
                and bool(re.fullmatch(r"[a-zA-Z0-9_-]+", sid))
                and sid not in seen,
                "Unique safe segment required",
            )
            seen.add(sid)
            require(
                c["order"] == ci
                and c["start_word"] == word
                and c["start_paragraph"] == paragraph
                and c["cumulative_start_ms"] == elapsed,
                "Ordered contiguous source-unit bounds",
            )
            require(
                all(
                    type(c[k]) is int
                    for k in (
                        "start_word",
                        "end_word",
                        "start_paragraph",
                        "end_paragraph",
                        "duration_ms",
                    )
                )
                and c["end_word"] >= word
                and c["end_paragraph"] >= paragraph
                and 0 < c["duration_ms"] <= segment_duration_limit_ms(package, t, c),
                "Measured finite unit bounds",
            )
            require(set(c["assets"]) == set(ROLES), "Exact asset roles")
            for r, a in c["assets"].items():
                require(
                    validsha(a["sha256"])
                    and type(a["size_bytes"]) is int
                    and a["size_bytes"] > 0
                    and a["mime_type"] == ROLES[r],
                    "Exact nonempty asset facts",
                )
            word = c["end_word"] + 1
            paragraph = c["end_paragraph"] + 1
            elapsed += c["duration_ms"]
            count += 1
        require(
            t["end_word"] == word - 1 and t["end_paragraph"] == paragraph - 1,
            "Track end bounds",
        )
    require(
        package["word_count"] == word
        and package["paragraph_count"] == paragraph
        and package["duration_ms"] == elapsed
        and package["segment_count"] == count,
        "Complete package counts",
    )


READER_CONTENT = ROOT / "frontend/src/lib/readerContent.js"


def reader_paragraph_map(source):
    """Run the existing local Reader reflow on exact text; never estimate timing."""
    script = """import fs from 'node:fs';
const code=fs.readFileSync(process.argv[1],'utf8')+'\\nexport {reflowHardWrappedBlocks};';
const {reflowHardWrappedBlocks}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const source=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(reflowHardWrappedBlocks(source.split(/\\n{2,}/).map(x=>x.trim()).filter(Boolean))));"""
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script, str(READER_CONTENT)],
            input=json.dumps(source),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        reflow = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise OwnerProducedError(
            "Actual local Reader paragraph mapping unavailable"
        ) from None
    blocks = list(re.finditer(r"\S(?:.*?\S)?(?=\n{2,}|$)", source, re.S))
    cursor = 0
    rows = []
    for i, text in enumerate(reflow):
        start = cursor
        joined = ""
        while cursor < len(blocks):
            joined += (" " if joined else "") + blocks[cursor].group()
            cursor += 1
            if joined == text:
                break
        require(
            start < cursor and joined == text, "Actual Reader source mapping changed"
        )
        a, z = blocks[start].start(), blocks[cursor - 1].end()
        rows.append(
            {
                "index": i,
                "source_start": a,
                "source_end": z,
                "text_sha256": sha(source[a:z].encode()),
            }
        )
    require(cursor == len(blocks) and bool(rows), "Incomplete Reader paragraph map")
    return {
        "reader_content_sha256": sha(READER_CONTENT.read_bytes()),
        "paragraphs": rows,
    }


def validate_source_grouping(source, units, package, paragraphs):
    """Bind many generation units to real paragraph-aligned delivery groups."""
    previous = word = 0
    seen = set()
    groups = []
    for u in units:
        start, end = u["source_start"], u["source_end"]
        require(
            type(start) is int
            and type(end) is int
            and previous <= start < end <= len(source)
            and not source[previous:start].strip(),
            "Exact source-unit offsets required",
        )
        require(u["id"] not in seen, "Duplicate source unit")
        seen.add(u["id"])
        require(
            source[start:end] == u["text"]
            and sha(u["text"].encode()) == u["text_sha256"],
            "Exact canonical unit text/hash required",
        )
        count = len(u["text"].split())
        require(
            count > 0 and u["start_word"] == word and u["end_word"] == word + count - 1,
            "Per-unit word bounds mismatch",
        )
        word += count
        group = u.get("delivery_segment_id", u["id"])
        if groups and groups[-1]["id"] == group:
            groups[-1]["units"].append(u)
        else:
            groups.append({"id": group, "units": [u]})
        previous = end
    require(
        not source[previous:].strip() and word == package["word_count"],
        "Canonical source coverage incomplete",
    )
    chunks = [c for t in package["tracks"] for c in t["chunks"]]
    require(
        [g["id"] for g in groups] == [c["segment_id"] for c in chunks],
        "Exact contiguous delivery grouping required",
    )
    require(
        package["paragraph_count"] == len(paragraphs),
        "Actual Reader paragraph count required",
    )
    for g, c in zip(groups, chunks):
        first, last = g["units"][0], g["units"][-1]
        a, z = first["source_start"], last["source_end"]
        selected = [
            p for p in paragraphs if p["source_start"] < z and p["source_end"] > a
        ]
        require(
            bool(selected)
            and all(a <= p["source_start"] and z >= p["source_end"] for p in selected),
            "Delivery boundary inside actual Reader paragraph",
        )
        require(
            c["start_word"] == first["start_word"]
            and c["end_word"] == last["end_word"]
            and c["start_paragraph"] == selected[0]["index"]
            and c["end_paragraph"] == selected[-1]["index"],
            "Delivery group actual source/paragraph bounds mismatch",
        )


def validate(descriptor, package, controlled_language, downstream_gates):
    """Only admits exact reviewed pre-storage evidence, never public exposure."""
    try:
        validate_topology(package)
        if "package_version" in package:
            try:
                validate_audiobook_package(
                    package,
                    expected_slug=descriptor["slug"],
                    expected_source_sha256=descriptor["controlled_source_sha256"],
                    expected_manuscript_sha256=descriptor["manuscript_sha256"],
                    expected_release_descriptor_sha256=sha(canonical(descriptor)),
                )
            except AudiobookPackageValidationError as e:
                raise OwnerProducedError(str(e)) from None
        identity = {
            k: descriptor[k]
            for k in (
                "slug",
                "title",
                "author",
                "controlled_source_sha256",
                "manuscript_sha256",
                "master_wav_sha256",
                "master_mp3_sha256",
            )
        }
        require(identity["slug"] in ALLOWED_SLUGS, "Title not supported")
        require(
            str(controlled_language).lower() in ("en", "eng", "english"), "English only"
        )
        require(
            all(validsha(identity[k]) for k in identity if k.endswith("sha256")),
            "Missing exact identity",
        )
        a = load_adoption(identity["slug"])
        candidate = descriptor["release_candidate_evidence"]
        require(
            a.get("status") == "ADOPTED"
            and a.get("policy") == POLICY
            and a.get("identity") == identity,
            "Exact adoption identity required",
        )
        require(
            a.get("authority_reference")
            and a.get("adopted_by")
            and validsha(a.get("authority_evidence_sha256")),
            "Actual adoption authority required",
        )
        require(
            a.get("unresolved_material_defects") == []
            and a.get("unresolved_wording_findings") == [],
            "Material quality hold",
        )
        require(
            candidate
            == {
                "acceptance_policy": POLICY,
                "status": "OWNER_PRODUCED_QA_ADOPTED",
                "adoption_sha256": sha(canonical(a)),
                "human_scores": None,
                "all_release_gates_passed": False,
                "highlight_sync_enabled": False,
            },
            "Acceptance inflation or mismatch",
        )
        require(
            descriptor.get("release_candidate_status")
            == "OWNER_PRODUCED_QA_ADOPTED_STORAGE_PENDING"
            and descriptor.get("known_release_blockers") == DOWNSTREAM
            and downstream_gates == DOWNSTREAM,
            "Downstream gates required",
        )
        require(
            descriptor.get("evidence_sha256") == a.get("evidence_sha256")
            and set(a["evidence_sha256"]) == EVIDENCE_ROLES
            and all(validsha(v) for v in a["evidence_sha256"].values()),
            "Exact complete evidence required",
        )
        require(
            descriptor.get("generation") == a.get("generation")
            and a["generation"]
            == {
                "provider": "owner_colab_qwen",
                "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "model_revision": "0c0e3051f131929182e2c023b9537f8b1c68adfe",
                "voice": "Ryan",
                "runtime_revision": a["generation"]["runtime_revision"],
            }
            and validsha(a["generation"]["runtime_revision"]),
            "Pinned Ryan runtime/model required",
        )
        require(
            descriptor.get("sync_tier") == "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY"
            and descriptor.get("highlight_sync_enabled") is False,
            "No estimated word highlighting",
        )
        require(
            validsha(a.get("reader_paragraph_map_sha256"))
            and descriptor.get("reader_paragraph_map_sha256")
            == a["reader_paragraph_map_sha256"]
            and a.get("reader_content_sha256") == sha(READER_CONTENT.read_bytes()),
            "Actual reviewed Reader paragraph mapping required",
        )
        require(
            validsha(a.get("source_units_sha256"))
            and descriptor.get("source_units_sha256") == a["source_units_sha256"],
            "Exact reviewed source-unit manifest required",
        )
        require(
            mapping(package) == a.get("chunk_mapping_sha256"),
            "Delivery mapping changed",
        )
        require(
            type(descriptor["duration_ms"]) is int
            and descriptor["duration_ms"] > 0
            and descriptor["duration_ms"] == package["duration_ms"] == a["duration_ms"],
            "Duration identity",
        )
        require(
            descriptor["sample_rate"] == 24000
            and type(descriptor["master_samples"]) is int
            and descriptor["master_samples"] > 0
            and descriptor["master_samples"] == a["master_samples"],
            "Master sample identity",
        )
        require(
            abs(descriptor["master_samples"] / 24 - descriptor["duration_ms"]) <= 1,
            "Measured duration mismatch",
        )
        rights = a["audio_use_decision"]
        accepted, revoked = load_production_registry()
        components = {
            "source_file": identity["controlled_source_sha256"],
            "selected_manuscript": identity["manuscript_sha256"],
            "master_wav": identity["master_wav_sha256"],
            "master_mp3": identity["master_mp3_sha256"],
            "audio_component_bindings": a["chunk_mapping_sha256"],
        }
        verdict = evaluate_accepted_record(
            rights,
            edition_id=identity["slug"],
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
            "Exact accepted India audio rights required",
        )
        return copy.deepcopy(descriptor)
    except (KeyError, TypeError, AttributeError) as e:
        raise OwnerProducedError("Incomplete owner-produced package evidence") from None


def wav_identity(raw):
    """Read PCM/IEEE-float RIFF frames without rewriting healthy float masters."""
    require(
        len(raw) >= 12
        and raw[:4] == b"RIFF"
        and raw[8:12] == b"WAVE"
        and struct.unpack_from("<I", raw, 4)[0] + 8 == len(raw),
        "Invalid RIFF length",
    )
    pos = 12
    fmt = data = None
    while pos + 8 <= len(raw):
        kind = raw[pos : pos + 4]
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        start = pos + 8
        end = start + size
        require(end <= len(raw), "Truncated WAV chunk")
        if kind == b"fmt ":
            require(fmt is None, "Duplicate WAV format")
            fmt = raw[start:end]
        if kind == b"data":
            require(data is None, "Duplicate WAV data")
            data = raw[start:end]
        pos = end + (size % 2)
    require(
        pos == len(raw) and fmt is not None and len(fmt) >= 16 and data is not None,
        "Incomplete WAV",
    )
    tag, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", fmt)
    if tag == 65534:
        require(
            len(fmt) >= 40 and struct.unpack_from("<H", fmt, 16)[0] >= 22,
            "Invalid extensible WAV",
        )
        guid = fmt[24:40]
        require(
            guid[4:] == bytes.fromhex("00001000800000aa00389b71"),
            "Unsupported WAV subformat",
        )
        tag = struct.unpack_from("<I", guid)[0]
    require(
        tag in (1, 3) and channels == 1 and rate == 24000,
        "Only actual24k mono PCM/float masters",
    )
    require(
        bits in ((8, 16, 24, 32) if tag == 1 else (32, 64))
        and align == bits // 8
        and byte_rate == rate * align
        and len(data) > 0
        and len(data) % align == 0,
        "Invalid WAV sample framing",
    )
    return {
        "sample_rate": rate,
        "channels": channels,
        "samples": len(data) // align,
        "format": "PCM" if tag == 1 else "IEEE_FLOAT",
    }


def prepare(bundle_path, output_dir):
    """Verify actual local master/evidence/delivery files, then emit generic finalize inputs.

    No arbitrary adoption path, provider writes, credentials, audio processing or
    canonical mutation. Caller supplies already-produced measured delivery assets.
    """
    bundle_path = Path(bundle_path).resolve()
    base = bundle_path.parent
    b = json.loads(bundle_path.read_text())
    require(
        b.get("schema") == "earnalism.owner-produced-local-package.v1",
        "Local bundle schema",
    )

    def file(ref):
        p = (base / ref["path"]).resolve()
        require(p.is_relative_to(base) and p.is_file(), "Local file outside bundle")
        raw = p.read_bytes()
        require(
            validsha(ref["sha256"]) and sha(raw) == ref["sha256"], "Local file changed"
        )
        return p, raw

    descriptor = b["release_descriptor"]
    identity = descriptor["slug"]
    require(identity in ALLOWED_SLUGS, "Unsupported title")
    for role, ref in b["evidence_files"].items():
        _, raw = file(ref)
        require(descriptor["evidence_sha256"].get(role) == sha(raw), "Evidence binding")
    require(
        set(b["evidence_files"]) == EVIDENCE_ROLES, "Complete evidence files required"
    )
    for role in ("master_wav", "master_mp3"):
        p, raw = file(b[role])
        require(sha(raw) == descriptor[role + "_sha256"], "Master binding")
        if role == "master_wav":
            facts = wav_identity(raw)
            require(
                facts["samples"] == descriptor["master_samples"],
                "Actual WAV sample count",
            )
    package = b["package_identity"]
    require(
        package["slug"] == identity
        and package["source_sha256"] == descriptor["controlled_source_sha256"]
        and package["manuscript_sha256"] == descriptor["manuscript_sha256"],
        "Source binding",
    )
    descriptor_sha = sha(canonical(descriptor))
    require(
        package["release_descriptor_sha256"] == descriptor_sha, "Descriptor binding"
    )
    validate(descriptor, package, "en", DOWNSTREAM)
    # Full lexical source coverage is bound separately to exact unit texts and source.
    _, manuscript = file(b["manuscript"])
    require(sha(manuscript) == descriptor["manuscript_sha256"], "Manuscript binding")
    tokens = lambda s: re.findall(r"\w+", s.casefold())
    require(
        tokens(" ".join(x["text"] for x in b["source_units"]))
        == tokens(manuscript.decode()),
        "Missing/duplicated/reordered source units",
    )
    require(
        len(manuscript.decode().split()) == package["word_count"],
        "Exact manuscript word count",
    )
    units = b["source_units"]
    require(
        sha(canonical(units)) == descriptor["source_units_sha256"],
        "Source-unit manifest changed",
    )
    paragraph_map = reader_paragraph_map(manuscript.decode())
    require(
        sha(canonical(paragraph_map)) == descriptor["reader_paragraph_map_sha256"],
        "Actual Reader paragraph map changed",
    )
    validate_source_grouping(
        manuscript.decode(), units, package, paragraph_map["paragraphs"]
    )
    assets = []
    tracks = []
    prefix = f"v1/prod/sprint1/{identity}/releases/{descriptor_sha}/"
    for role in ("master_wav", "master_mp3"):
        master, raw = file(b[role])
        assets.append(
            {
                "asset_id": role,
                "local_path": str(master),
                "key": prefix
                + "masters/"
                + role
                + "-sha256-"
                + sha(raw)
                + master.suffix,
                "sha256": sha(raw),
                "size_bytes": len(raw),
                "mime_type": "audio/wav" if role == "master_wav" else "audio/mpeg",
            }
        )
    for track in package["tracks"]:
        cs = []
        for chunk in track["chunks"]:
            require(set(chunk["assets"]) == set(ROLES), "Exact asset roles required")
            ids = {}
            for role, fact in chunk["assets"].items():
                aid = chunk["segment_id"] + "-" + role
                ref = b["asset_files"][aid]
                p, raw = file(ref)
                require(
                    sha(raw) == fact["sha256"]
                    and len(raw) == fact["size_bytes"]
                    and fact["mime_type"] == ROLES[role],
                    "Delivery asset binding",
                )
                require(re.fullmatch(r"[a-zA-Z0-9_-]+", aid), "Asset identifier")
                key = prefix + "delivery/" + aid + "-sha256-" + sha(raw) + p.suffix
                assets.append(
                    {
                        "asset_id": aid,
                        "local_path": str(p),
                        "key": key,
                        "sha256": sha(raw),
                        "size_bytes": len(raw),
                        "mime_type": ROLES[role],
                    }
                )
                ids[role] = aid
            cs.append(
                {**{k: v for k, v in chunk.items() if k != "assets"}, "asset_ids": ids}
            )
        tracks.append(
            {**{k: v for k, v in track.items() if k != "chunks"}, "chunks": cs}
        )
    semantics = {
        k: package[k]
        for k in (
            "slug",
            "release_descriptor_sha256",
            "source_sha256",
            "manuscript_sha256",
            "duration_ms",
            "segment_count",
            "word_count",
            "paragraph_count",
            "sync_tier",
            "highlight_sync_enabled",
        )
    }
    semantics.update(
        schema_version="audiobook_package_semantics.v2",
        package_schema_version="audiobook_package_manifest.v2",
        release_evidence_version=POLICY,
        tracks=tracks,
    )
    plan = {
        "schema_version": "audiobook_package_upload_plan.v2",
        "slug": identity,
        "release_descriptor_sha256": descriptor_sha,
        "immutable_prefix": prefix,
        "release_status": "RELEASE_CANDIDATE",
        "assets": assets,
    }
    out = Path(output_dir)
    require(not out.exists(), "Output exists; preserve prior work")
    out.mkdir(parents=True)
    for name, value in [
        ("release-descriptor.json", descriptor),
        ("package-semantics.json", semantics),
        ("upload-plan.json", plan),
    ]:
        with (out / name).open("x") as f:
            json.dump(value, f, indent=2)
    return {
        "status": "LOCAL_PREPARED_STORAGE_PENDING",
        "output_dir": str(out),
        "upload_performed": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.bundle, a.output_dir), indent=2))


if __name__ == "__main__":
    main()
