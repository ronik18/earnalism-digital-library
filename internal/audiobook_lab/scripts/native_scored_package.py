"""Validate an exactly reviewed native Cedar scored edition, never publish.

The historical Ryan policy/registry remain unchanged. No supplied adoption path,
provider credentials, uploads, inference or inferred listening acceptance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import owner_produced_package as legacy
from rights_decision_gate import evaluate_accepted_record, load_production_registry
from audiobook_packages import validate_audiobook_package

POLICY = "owner_produced_native_scored.v1"
REGISTRY = Path(__file__).resolve().parents[1] / "release_gate/native_scored_package_adoptions.json"
SYNC_TIER = "PARAGRAPH_OR_SECTION_SYNC_PREMIUM"
EVIDENCE_ROLES = legacy.EVIDENCE_ROLES | {
    "scored_mix_acceptance", "music_rights", "measured_alignment", "container_metadata_reuse",
}
GENERATION = {
    "provider": "owner_openai_realtime",
    "model_id": "gpt-realtime-2.1-mini",
    "model_revision": None,  # Provider alias; never invent a dated weights revision.
    "voice": "cedar",
    "runtime_revision": "823ac4359c37d9ea00a8b015b296e9704b1d5eb30c8cda15ee0d90ec41e3fc29",
}
SOURCE = {
    "slug": "the-selfish-giant", "title": "The Selfish Giant", "author": "Oscar Wilde",
    "controlled_source_sha256": "77ae1b3c7be77aea82b1f935e531e53f4df43db572cbc14af39d6cd0d5ba50da",
    "manuscript_sha256": "c55bef9dcd5883e156af940deb849c67a78a8fae7fc7a1e50ea814aa9ce866c5",
}
SCORES = {
    "naturalness_score", "pronunciation_score", "emotional_expression_score",
    "punctuation_pause_score", "pacing_score", "continuity_score",
    "anti_robotic_texture_score", "anti_choppy_join_score", "listener_enjoyment_score",
    "overall_listening_score", "confidence_score",
}
IDENTITY_KEYS = tuple(SOURCE) + ("master_wav_sha256", "master_mp3_sha256")
require = legacy.require
canonical = legacy.canonical
sha = legacy.sha
validsha = legacy.validsha
Error = legacy.OwnerProducedError


def load_adoption(identity):
    """Only committed trust; permit historical/new exact identities to coexist."""
    try:
        registry = json.loads(REGISTRY.read_text())
        require(registry.get("schema") == "earnalism.native-scored-adoptions.v1", "Native adoption schema")
        entries = [x for x in registry["adoptions"] if x.get("record", {}).get("identity") == identity]
        require(len(entries) == 1, "Exactly one reviewed native adoption required")
        entry = entries[0]
        require(validsha(entry.get("record_sha256")) and sha(canonical(entry["record"])) == entry["record_sha256"], "Native adoption changed")
        return entry["record"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        raise Error("Reviewed native adoption unavailable") from None


def validate_container_reuse(proof, *, listened, published, frames):
    require(isinstance(proof, dict) and proof.get("schema") == "earnalism.container_metadata_audio_reuse.v1"
            and proof.get("status") == "PASS_EXACT_DECODED_PCM_AND_ELEMENTARY_PACKET_EQUALITY_METADATA_ONLY", "Container reuse proof schema")
    try:
        prior = proof["items"]["listened"]
        delivery = proof["items"]["delivery"]
        require(prior["file_sha256"] == listened and delivery["file_sha256"] == published, "Container identity mismatch")
        require(validsha(prior["canonical_decoded_PCM"]["sha256"])
                and prior["canonical_decoded_PCM"] == delivery["canonical_decoded_PCM"], "Decoded audio changed")
        require(validsha(prior["elementary_encoded_audio_packets"]["sha256"])
                and prior["elementary_encoded_audio_packets"] == delivery["elementary_encoded_audio_packets"], "Elementary audio packets changed")
        fmt = proof["canonical_decoded_PCM_format"]
        require(fmt.get("sample_rate") == 48000 and fmt.get("channels") == 2 and fmt.get("format") == "f32le"
                and type(fmt.get("frames")) is int and fmt["frames"] == frames
                and prior["canonical_decoded_PCM"]["bytes"] == frames * 8, "Decoded frame identity")
    except (KeyError, TypeError):
        raise Error("Incomplete container reuse proof") from None


def decoded_pcm_identity(path):
    """Reproducible local decoding only. Reject incompatible physical streams."""
    info = subprocess.run([
        "ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-f", "mp3",
        "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels",
        "-of", "json", str(path),
    ], capture_output=True, text=True, timeout=20, check=True)
    streams = json.loads(info.stdout).get("streams", [])
    require(len(streams) == 1 and streams[0].get("sample_rate") == "48000"
            and streams[0].get("channels") == 2, "MP3 physical stream identity")
    decoded = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-threads", "1",
        "-protocol_whitelist", "file,pipe", "-f", "mp3", "-i", str(path), "-map", "0:a:0",
        "-ar", "48000", "-ac", "2", "-f", "f32le", "pipe:1",
    ], capture_output=True, timeout=60, check=True).stdout
    require(bool(decoded) and len(decoded) % 8 == 0, "Decoded PCM framing")
    packets = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-threads", "1",
        "-protocol_whitelist", "file,pipe", "-f", "mp3", "-i", str(path), "-map", "0:a:0",
        "-c:a", "copy", "-f", "data", "pipe:1",
    ], capture_output=True, timeout=30, check=True).stdout
    require(bool(packets), "Missing elementary audio packets")
    return {"sha256": sha(decoded), "frames": len(decoded) // 8, "sample_rate": 48000, "channels": 2,
        "packet_sha256": sha(packets), "packet_bytes": len(packets)}


def validate_publication_tags(tags):
    """Read-back guard against stale draft labels and absent audible-score credits."""
    require(isinstance(tags, dict), "Publication tags missing")
    tags = {str(k).lower(): str(v) for k, v in tags.items()}
    comment = tags.get("comment", "")
    combined = "\n".join(tags.values()).lower()
    require(tags.get("title") == SOURCE["title"] and "cedar" in tags.get("artist", "").lower(), "Publication title/narrator tags")
    require(not re.search(r"\b(?:draft|private|pending|review)\b", combined)
            and all(stale not in combined for stale in ("proposed changes", "planned credits", "not evidence of rendering")), "Stale draft publication tags")
    require(not re.search(r"(?:file://|/(?:users|home|tmp|private|var/folders|volumes)/|[a-z]:[\\/](?:users|temp)[\\/])", combined)
            and all(marker not in combined for marker in ("x-amz-signature=", "x-amz-credential=", "authorization:", "bearer ")), "Private publication metadata leakage")
    require("ai narration" in comment.lower() and "cedar" in comment.lower()
            and "openai" in comment.lower() and "Heartwarming" in comment
            and "Heartbreaking" in comment and "Kevin MacLeod" in comment
            and "https://creativecommons.org/licenses/by/4.0/" in comment, "Publication AI disclosure/music attribution")


def publication_tags(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
        "-f", "mp3", "-show_entries", "format_tags", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=20, check=True)
    tags = json.loads(result.stdout).get("format", {}).get("tags", {})
    validate_publication_tags(tags)
    return tags


def wav_identity(raw):
    """48k stereo PCM/IEEE-float frame identity; no rewrite or rate laundering."""
    require(len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"
            and struct.unpack_from("<I", raw, 4)[0] + 8 == len(raw), "Invalid native RIFF")
    pos = 12
    fmt = data = None
    while pos + 8 <= len(raw):
        kind = raw[pos:pos + 4]
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        end = pos + 8 + size
        require(end <= len(raw), "Truncated native WAV")
        if kind == b"fmt ":
            require(fmt is None, "Duplicate WAV format")
            fmt = raw[pos + 8:end]
        if kind == b"data":
            require(data is None, "Duplicate WAV data")
            data = raw[pos + 8:end]
        pos = end + size % 2
    require(pos == len(raw) and fmt is not None and len(fmt) >= 16 and data is not None, "Incomplete native WAV")
    tag, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", fmt)
    if tag == 65534:
        require(len(fmt) >= 40 and struct.unpack_from("<H", fmt, 16)[0] >= 22
                and fmt[28:40] == bytes.fromhex("00001000800000aa00389b71"), "Unsupported native WAV subformat")
        tag = struct.unpack_from("<I", fmt, 24)[0]
    require(tag in (1, 3) and rate == 48000 and channels == 2, "Only actual 48k stereo masters")
    require(bits in ((8, 16, 24, 32) if tag == 1 else (32, 64))
            and align == channels * bits // 8 and byte_rate == rate * align
            and len(data) > 0 and len(data) % align == 0, "Native WAV sample framing")
    return {"sample_rate": rate, "channels": channels, "frames": len(data) // align}


def validate(descriptor, package, controlled_language, downstream_gates):
    try:
        require(isinstance(descriptor, dict) and descriptor.get("schema_version") == "audiobook_release_descriptor.v1", "Native descriptor schema")
        legacy.validate_topology(package, expected_sync_tier=SYNC_TIER)
        identity = {key: descriptor[key] for key in IDENTITY_KEYS}
        require(all(identity[key] == value for key, value in SOURCE.items()), "Exact approved native source/title required")
        require(all(validsha(identity[key]) for key in ("master_wav_sha256", "master_mp3_sha256")), "Native master identities")
        require(str(controlled_language).lower() in ("en", "eng", "english"), "English only")
        require(package.get("slug") == identity["slug"] and package.get("source_sha256") == identity["controlled_source_sha256"]
                and package.get("manuscript_sha256") == identity["manuscript_sha256"]
                and package.get("release_descriptor_sha256") == sha(canonical(descriptor)), "Native package identity")
        if "package_version" in package:
            validate_audiobook_package(package, expected_slug=identity["slug"], expected_source_sha256=identity["controlled_source_sha256"],
                expected_manuscript_sha256=identity["manuscript_sha256"], expected_release_descriptor_sha256=sha(canonical(descriptor)))
        a = load_adoption(identity)
        require(a.get("status") == "ADOPTED" and a.get("policy") == POLICY and a.get("identity") == identity, "Exact native adoption identity")
        require(a.get("adopted_by") and a.get("authority_reference") and validsha(a.get("authority_evidence_sha256")), "Actual native adoption authority")
        require(a.get("unresolved_material_defects") == [] and a.get("unresolved_wording_findings") == [], "Native material quality hold")
        require(descriptor.get("generation") == a.get("generation") == GENERATION, "Pinned authorized Cedar profile required")
        counts = a.get("generation_counts", {})
        require(counts == {"responses": 17, "one_shot_limit": 17, "retries": 0, "new_allocations": 0}
                and all(type(v) is int for v in counts.values()), "Native bounded generation lineage")
        require(descriptor.get("evidence_sha256") == a.get("evidence_sha256") and set(a["evidence_sha256"]) == EVIDENCE_ROLES
                and all(validsha(v) for v in a["evidence_sha256"].values()), "Complete native evidence binding")
        require(descriptor.get("known_release_blockers") == downstream_gates == legacy.DOWNSTREAM
                and descriptor.get("release_candidate_status") == "OWNER_PRODUCED_NATIVE_SCORED_QA_ADOPTED_STORAGE_PENDING", "Native downstream gates remain required")
        scores = a.get("human_scores", {})
        require(set(scores) == SCORES, "Complete actual full-title scores required")
        for key, value in scores.items():
            require(type(value) in (int, float) and math.isfinite(value)
                    and (0.90 if key == "confidence_score" else 8.9) <= value <= (1 if key == "confidence_score" else 10), "Native listening score missing/below policy")
        quality = a.get("quality", {})
        require(all(quality.get(k) is True for k in ("full_title_listening_performed", "full_scored_mix_listening_performed", "all_joins_reviewed", "music_continuity_and_intelligibility_reviewed", "first_words_match", "last_words_match", "ordered_content_integrity"))
                and quality.get("fatal_flags") == [] and quality.get("auto_estimated_sync") is False, "Native full quality evidence required")
        require(type(quality.get("asr_score")) in (int, float) and math.isfinite(quality["asr_score"])
                and 9.7 <= quality["asr_score"] <= 10 and type(quality.get("source_coverage")) in (int, float)
                and math.isfinite(quality["source_coverage"]) and quality["source_coverage"] == 1.0, "Native ASR/source coverage")
        require(descriptor.get("release_candidate_evidence") == {"acceptance_policy": POLICY, "status": "OWNER_PRODUCED_NATIVE_SCORED_QA_ADOPTED",
            "adoption_sha256": sha(canonical(a)), "human_scores": scores, "all_release_gates_passed": False, "highlight_sync_enabled": False}, "Native acceptance inflation/mismatch")
        require(descriptor.get("sync_tier") == SYNC_TIER and descriptor.get("highlight_sync_enabled") is False
                and validsha(a.get("reader_paragraph_map_sha256")) and descriptor.get("reader_paragraph_map_sha256") == a["reader_paragraph_map_sha256"]
                and a.get("reader_content_sha256") == sha(legacy.READER_CONTENT.read_bytes()), "Native measured Reader paragraph contract")
        require(validsha(a.get("source_units_sha256")) and descriptor.get("source_units_sha256") == a["source_units_sha256"]
                and descriptor.get("measured_alignment_sha256") == a["evidence_sha256"]["measured_alignment"], "Native source/alignment proof binding")
        require(type(a.get("duration_ms")) is int and type(package.get("duration_ms")) is int
                and type(descriptor.get("duration_ms")) is int and 0 < a["duration_ms"] == package.get("duration_ms") == descriptor.get("duration_ms") <= 720000
                and descriptor.get("sample_rate") == 48000 and descriptor.get("channels") == 2
                and type(a.get("master_samples")) is int and a["master_samples"] > 0
                and type(descriptor.get("master_samples")) is int and descriptor["master_samples"] == a["master_samples"]
                and abs(a["master_samples"] / 48 - a["duration_ms"]) <= 1, "Native actual sample/duration identity")
        require(all(type(package.get(k)) is int for k in ("segment_count", "word_count", "paragraph_count"))
                and package.get("segment_count") == 1 and package.get("word_count") == 1652 and package.get("paragraph_count") == 23, "Exact whole-book delivery counts")
        require(legacy.mapping(package) == a.get("chunk_mapping_sha256"), "Native delivery mapping changed")
        listened = a.get("listened_master_mp3_sha256")
        require(validsha(listened) and descriptor.get("listened_master_mp3_sha256") == listened, "Listened scored master identity")
        validate_container_reuse(a.get("container_metadata_reuse"), listened=listened, published=identity["master_mp3_sha256"], frames=a["master_samples"])
        alignment = a.get("alignment", {})
        chunk = package["tracks"][0]["chunks"][0]
        require(alignment.get("audio_derived_or_measured") is True and alignment.get("auto_estimated_sync") is False
                and alignment.get("paragraph_count") == 23 and alignment.get("word_count") == 1652
                and alignment.get("timestamps_sha256") == chunk["assets"]["timestamps"]["sha256"]
                and alignment.get("master_mp3_sha256") == identity["master_mp3_sha256"], "Exact native measured sidecar binding")
        score = a.get("score", {})
        require(score.get("licensed_instrumental_score") is True and score.get("attribution_bound") is True
                and score.get("reviewed_mp3_sha256") == listened and score.get("rights_evidence_sha256") == a["evidence_sha256"]["music_rights"], "Native score rights/review binding")
        rights = a["audio_use_decision"]
        accepted, revoked = load_production_registry()
        components = {"source_file": identity["controlled_source_sha256"], "selected_manuscript": identity["manuscript_sha256"],
            "master_wav": identity["master_wav_sha256"], "master_mp3": identity["master_mp3_sha256"], "audio_component_bindings": a["chunk_mapping_sha256"],
            "model_voice_licence": a["evidence_sha256"]["model_voice_licence"], "music_rights": a["evidence_sha256"]["music_rights"],
            "listened_master_mp3": listened, "container_metadata_reuse": a["evidence_sha256"]["container_metadata_reuse"]}
        verdict = evaluate_accepted_record(rights, edition_id=identity["slug"], operator_id="reo-enterprise", country="IN", country_trusted=True,
            use="audio_stream", required_components=components, accepted_records=accepted, revoked_decision_ids=revoked, now=datetime.now(timezone.utc))
        require(verdict.passed and rights.get("territories") == ["IN"] and rights.get("uses") == ["audio_stream"], "Exact accepted native India audio rights required")
        return copy.deepcopy(descriptor)
    except (KeyError, TypeError, AttributeError) as exc:
        raise Error("Incomplete native scored package evidence") from None


def prepare(bundle_path, output_dir):
    """Validate local accepted assets; prepare only four delivery objects, no writes to providers."""
    bundle_path = Path(bundle_path).resolve()
    base = bundle_path.parent
    bundle = json.loads(bundle_path.read_text())
    require(bundle.get("schema") == "earnalism.native-scored-local-package.v1", "Native bundle schema")

    def file(ref):
        p = (base / ref["path"]).resolve()
        require(p.is_relative_to(base) and p.is_file(), "Native file outside bundle")
        raw = p.read_bytes()
        require(validsha(ref.get("sha256")) and sha(raw) == ref["sha256"], "Native local asset changed")
        return p, raw

    descriptor = bundle["release_descriptor"]
    package = bundle["package_identity"]
    require(set(bundle["evidence_files"]) == EVIDENCE_ROLES, "Native evidence roles")
    for role, ref in bundle["evidence_files"].items():
        _, raw = file(ref)
        require(sha(raw) == descriptor["evidence_sha256"].get(role), "Native evidence bytes changed")
    _, raw_wav = file(bundle["master_wav"])
    facts = wav_identity(raw_wav)
    require(sha(raw_wav) == descriptor["master_wav_sha256"] and facts["frames"] == descriptor["master_samples"], "Native lossless master identity")
    del raw_wav
    published_path, published = file(bundle["master_mp3"])
    require(sha(published) == descriptor["master_mp3_sha256"], "Native delivery MP3 identity")
    listened_path, listened = file(bundle["listened_master_mp3"])
    require(sha(listened) == descriptor["listened_master_mp3_sha256"], "Native listened MP3 changed")
    proof_path, proof_raw = file(bundle["evidence_files"]["container_metadata_reuse"])
    proof = json.loads(proof_raw)
    validate_container_reuse(proof, listened=sha(listened), published=sha(published), frames=facts["frames"])
    publication_tags(published_path)
    prior_pcm = decoded_pcm_identity(listened_path)
    delivery_pcm = decoded_pcm_identity(published_path)
    require(prior_pcm == delivery_pcm and prior_pcm["sha256"] == proof["items"]["listened"]["canonical_decoded_PCM"]["sha256"]
            and prior_pcm["packet_sha256"] == proof["items"]["listened"]["elementary_encoded_audio_packets"]["sha256"]
            and prior_pcm["packet_bytes"] == proof["items"]["listened"]["elementary_encoded_audio_packets"]["bytes"]
            and prior_pcm["frames"] == facts["frames"], "Actual metadata-successor PCM differs")
    validate(descriptor, package, "en", legacy.DOWNSTREAM)
    _, manuscript = file(bundle["manuscript"])
    require(sha(manuscript) == descriptor["manuscript_sha256"] and len(manuscript.decode().split()) == 1652, "Native exact manuscript")
    units = bundle["source_units"]
    require(len(units) == 17 and [u["id"] for u in units] == [f"fresh-unit-{i:02}" for i in range(1, 18)]
            and sha(canonical(units)) == descriptor["source_units_sha256"], "Native 17-unit source manifest")
    paragraph_map = legacy.reader_paragraph_map(manuscript.decode())
    require(sha(canonical(paragraph_map)) == descriptor["reader_paragraph_map_sha256"], "Native actual Reader mapping changed")
    legacy.validate_source_grouping(manuscript.decode(), units, package, paragraph_map["paragraphs"])
    descriptor_sha = sha(canonical(descriptor))
    prefix = f"v1/prod/sprint1/{descriptor['slug']}/releases/{descriptor_sha}/"
    assets = []
    tracks = []
    for track in package["tracks"]:
        chunks = []
        for chunk in track["chunks"]:
            ids = {}
            for role, fact in chunk["assets"].items():
                aid = chunk["segment_id"] + "-" + role
                p, raw = file(bundle["asset_files"][aid])
                require(sha(raw) == fact["sha256"] and len(raw) == fact["size_bytes"] and fact["mime_type"] == legacy.ROLES[role], "Native delivery asset bytes changed")
                if role == "audio":
                    require(sha(raw) == descriptor["master_mp3_sha256"], "Unaccepted served audio")
                assets.append({"asset_id": aid, "local_path": str(p), "key": prefix + "delivery/" + aid + "-sha256-" + sha(raw) + p.suffix,
                    "sha256": sha(raw), "size_bytes": len(raw), "mime_type": legacy.ROLES[role]})
                ids[role] = aid
            chunks.append({**{k: v for k, v in chunk.items() if k != "assets"}, "asset_ids": ids})
        tracks.append({**{k: v for k, v in track.items() if k != "chunks"}, "chunks": chunks})
    semantics = {k: package[k] for k in ("slug", "release_descriptor_sha256", "source_sha256", "manuscript_sha256", "duration_ms", "segment_count", "word_count", "paragraph_count", "sync_tier", "highlight_sync_enabled")}
    semantics.update(schema_version="audiobook_package_semantics.v2", package_schema_version="audiobook_package_manifest.v2", release_evidence_version=POLICY, tracks=tracks)
    plan = {"schema_version": "audiobook_package_upload_plan.v2", "slug": descriptor["slug"], "release_descriptor_sha256": descriptor_sha,
        "immutable_prefix": prefix, "release_status": "RELEASE_CANDIDATE", "assets": assets}
    out = Path(output_dir)
    require(not out.exists(), "Output exists; preserve prior native package")
    out.mkdir(parents=True)
    for name, value in (("release-descriptor.json", descriptor), ("package-semantics.json", semantics), ("upload-plan.json", plan)):
        with (out / name).open("x") as f:
            json.dump(value, f, indent=2)
    return {"status": "LOCAL_NATIVE_SOURCE_QA_PREPARED_STORAGE_PENDING", "output_dir": str(out), "upload_performed": False, "public_release_approved": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.bundle, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
