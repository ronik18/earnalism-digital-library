"""Validate real Rust source/audio/timing without synthesis, scoring or acceptance.

The existing fixed science dispatcher calls validate_inputs. Rendering is a silent
body; the common compositor owns the selected scored master and exact END once.
No historical stock-B assembler, private path or estimated timing is imported.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import struct

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
TOPIC = CONTRACT["topic_id"]
SOURCE_SHA = CONTRACT["script_sha256"]
SCENE_KINDS = tuple(s["id"] for s in CONTRACT["scenes"])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    from scripts.audiobook_score import load_json
    return load_json(Path(path))


def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?|\d+", text.lower().replace("’", "'"))


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def bound(ref, base):
    require(isinstance(ref, dict) and isinstance(ref.get("path"), str) and
            re.fullmatch(r"[a-f0-9]{64}", str(ref.get("sha256", ""))), "Exact local file binding required")
    require("://" not in ref["path"], "Local materialized file required")
    p = Path(ref["path"])
    p = p if p.is_absolute() else Path(base) / p
    require(not any(x.is_symlink() for x in (p, *p.parents)) and p.is_file() and
            sha(p) == ref["sha256"], "Missing/changed regular bound input")
    return p


def wave_info(path):
    """Read ordinary integer/float PCM chunks, without loading or changing audio."""
    fmt = data_size = None
    size = Path(path).stat().st_size
    with Path(path).open("rb") as f:
        header = f.read(12)
        require(len(header) == 12 and header[:4] == b"RIFF" and header[8:] == b"WAVE" and
                struct.unpack("<I", header[4:8])[0] + 8 == size, "Complete native RIFF WAV required")
        while f.tell() + 8 <= size:
            kind, length = struct.unpack("<4sI", f.read(8))
            require(f.tell() + length <= size, "Truncated WAV chunk")
            if kind == b"fmt ":
                require(fmt is None and length >= 16, "One PCM format required")
                fmt = struct.unpack("<HHIIHH", f.read(16))
                f.seek(length - 16, 1)
            elif kind == b"data":
                require(data_size is None, "One PCM data chunk required")
                data_size = length
                f.seek(length, 1)
            else:
                f.seek(length, 1)
            f.seek(length % 2, 1)
    require(fmt is not None and data_size is not None, "PCM format/data missing")
    code, channels, rate, byte_rate, block, bits = fmt
    require(code in (1, 3) and channels in (1, 2) and rate in (24000, 44100, 48000) and
            bits in ((32,) if code == 3 else (16, 24, 32)) and
            block == channels * bits // 8 and byte_rate == rate * block and
            data_size > 0 and data_size % block == 0, "Supported native PCM dimensions required")
    return {"duration": data_size / block / rate, "frames": data_size // block,
            "sample_rate": rate, "channels": channels}


def scene_ranges():
    return [(s["id"], s["word_start"], s["word_end"]) for s in CONTRACT["scenes"]]


def validate_timeline(timeline):
    require(timeline.get("schema") == "earnalism.metal-rust.timeline.v1" and
            timeline.get("topic_id") == TOPIC and timeline.get("source_sha256") == SOURCE_SHA,
            "Exact Metal Rust source identity required")
    require(timeline.get("fixture_mode", False) is False and
            timeline.get("timing_status") == "actual_audio_aligned" and
            timeline.get("method") in ("measured_word_alignment", "human_verified_audio"),
            "Measured real audio required; no fixture/illustrative clock")
    duration = timeline.get("duration")
    require(finite(duration) and 0 < duration <= 600, "Finite actual short-episode duration required")
    require(re.fullmatch(r"[a-f0-9]{64}", str(timeline.get("audio_sha256", ""))), "Actual audio SHA required")
    words = timeline.get("words")
    require(isinstance(words, list) and words and
            [w.get("word") for w in words if isinstance(w, dict)] and
            len(words) == CONTRACT["word_count"] and
            hashlib.sha256(" ".join(sum((tokens(w.get("word", "")) for w in words if isinstance(w, dict)), [])).encode()).hexdigest() ==
            CONTRACT["normalized_tokens_sha256"], "Actual words must cover the complete current script")
    require(all(isinstance(w, dict) and len(tokens(w.get("word", ""))) == 1 for w in words),
            "One recognized source word per measured interval required")
    end = 0
    for word in words:
        a, b = word.get("start"), word.get("end")
        require(finite(a) and finite(b) and end <= a < b <= duration, "Invalid/reordered measured word interval")
        end = b
    scenes = timeline.get("scenes", [])
    require(tuple(s.get("scene") for s in scenes) == SCENE_KINDS, "Exact six Rust thoughts required")
    end = 0
    for scene, (kind, first, last) in zip(scenes, scene_ranges()):
        a, b = scene.get("start"), scene.get("end")
        require(finite(a) and finite(b) and abs(a - end) < .001 and a < b <= duration and
                scene.get("word_start") == first and scene.get("word_end") == last,
                "Contiguous current-script scene word ranges required")
        expected_start = 0 if first == 0 else words[first]["start"]
        expected_end = duration if last == len(words) else words[last]["start"]
        require(abs(a - expected_start) < .001 and abs(b - expected_end) < .001,
                "Scene boundaries must follow actual current word onsets")
        marks = scene.get("marks", {})
        expected = {name: words[index]["start"] - a
                    for name, index in CONTRACT["anchors"][kind].items()}
        require(set(marks) == set(expected) and all(finite(marks[k]) and
                abs(marks[k] - v) < .001 for k, v in expected.items()),
                "Rust action anchors must use their current measured spoken words")
        end = b
    require(abs(end - duration) < .001, "Complete actual body timeline required")
    captions = timeline.get("captions")
    require(isinstance(captions, list) and captions, "Actual verbatim captions required")
    cursor = 0
    for cue in captions:
        first, last = cue.get("word_start"), cue.get("word_end")
        require(type(first) is int and type(last) is int and first == cursor < last <= len(words),
                "Complete ordered caption word coverage required")
        require(tokens(cue.get("text", "")) == sum((tokens(w["word"]) for w in words[first:last]), []) and
                finite(cue.get("start")) and finite(cue.get("end")) and
                abs(cue["start"] - words[first]["start"]) < .001 and
                abs(cue["end"] - words[last - 1]["end"]) < .001,
                "Captions must be verbatim and use actual word boundaries")
        cursor = last
    require(cursor == len(words), "Caption omission")
    return duration, scenes


def validate_voice(binding, root, audio_sha):
    from scripts.earnalism_voice import inspect_profile
    require(binding.get("identity") == "TheEarnalismVoice" and binding.get("language") == "en" and
            binding.get("source_sha256") == SOURCE_SHA and binding.get("narration_sha256") == audio_sha and
            binding.get("no_tempo_or_pitch_change") is True,
            "Real requested branded English narration must be preserved; no stock B fallback")
    profile = bound(binding["profile"], root)
    inspection = inspect_profile(profile, "en", purpose="production")
    require(inspection.get("status") == "QUALIFIED" and inspection.get("production_accepted") is True,
            "The Earnalism Voice English production qualification remains required")
    provenance = bound(binding["provenance"], root)
    receipt = load(provenance)
    require(receipt.get("profile_sha256") == sha(profile) and
            receipt.get("checkpoint_sha256") == inspection.get("checkpoint_sha256") and
            receipt.get("source_sha256") == SOURCE_SHA and receipt.get("purpose") == "production" and
            receipt.get("source_coverage") == "FULL_EXACT_TEXT_NOT_AUDIO_FIDELITY" and
            audio_sha in {r.get("sha256") for r in receipt.get("outputs", [])},
            "Exact trained-profile/checkpoint/source/audio provenance required")
    return {"path": str(profile), "sha256": sha(profile)}


def validate_inputs(root):
    root = Path(root)
    assembly = load(root / "assembly-manifest.json")
    require(assembly.get("state") == "ASSEMBLED_PRIVATE_REQUIRES_REVIEW" and
            assembly.get("topic_id") == TOPIC and not assembly.get("fixture_mode"), "Actual Rust assembly required")
    for name in ("timeline.json", "voice-binding.json", "asr-review.json", "caption-quality.json", "narration.wav", "units.json"):
        require(assembly.get("output_files", {}).get(name) == sha(root / name), "Stale Rust assembly output: " + name)
    source_root = Path(assembly["source_root"])
    source_root = source_root if source_root.is_absolute() else root / source_root
    inputs = assembly.get("input_files", {})
    require(inputs and all(sha(source_root / name) == digest for name, digest in inputs.items()), "Source evidence changed")
    manuscript = bound(assembly["manuscript"], source_root)
    require(sha(manuscript) == SOURCE_SHA and sha(manuscript) in inputs.values(), "Exact reviewed Rust manuscript required")
    timeline = load(root / "timeline.json")
    duration, _ = validate_timeline(timeline)
    audio_sha = sha(root / "narration.wav")
    require(timeline["audio_sha256"] == audio_sha and
            abs(wave_info(root / "narration.wav")["duration"] - duration) < .001, "Actual native audio/timeline mismatch")
    profile = validate_voice(load(root / "voice-binding.json"), root, audio_sha)
    timing = bound(timeline["timing"], root)
    shared = load(timing)
    require(shared.get("schema") == "earnalism.audiobook_score.timing.v1" and
            shared.get("method") == timeline["method"] and
            shared.get("manuscript_sha256") == SOURCE_SHA and shared.get("narration_sha256") == audio_sha and
            abs(shared.get("duration_ms", -1000) / 1000 - duration) <= .001 and
            shared.get("provenance", {}).get("boundary_validation") == "accepted", "Current measured shared score timing required")
    alignment = bound(timeline["word_alignment"], root)
    actual = load(alignment)
    require(actual.get("method") == timeline["method"] and actual.get("audio_sha256") == audio_sha and
            actual.get("source_sha256") == SOURCE_SHA and actual.get("words") == timeline["words"] and
            not actual.get("fixture_mode"), "Actual source-bound word alignment required")
    review = load(root / "asr-review.json")
    require(review.get("source_validation") == "PASS" and not review.get("differences") and
            review.get("word_alignment_sha256") == sha(alignment), "Unresolved actual ASR/source review")
    quality = load(root / "caption-quality.json")
    require(not quality.get("issues") and quality.get("timeline_sha256") == sha(root / "timeline.json"), "Current caption evidence required")
    units = load(root / "units.json")
    require(units.get("topic_id") == TOPIC and units.get("source_sha256") == SOURCE_SHA, "Rust unit/source identity required")
    return timeline, {"manuscript": {"path": str(manuscript), "sha256": SOURCE_SHA},
                      "timing": {"path": str(timing), "sha256": sha(timing)}, "voice_profile": profile,
                      "word_alignment": {"path": str(alignment), "sha256": sha(alignment)}}


def validate_props(props, timeline, name):
    require(props.get("topic_id") == TOPIC and props.get("source_sha256") == SOURCE_SHA and
            props.get("audio_sha256") == timeline["audio_sha256"] and
            props.get("timing_status") == "actual_audio_aligned" and
            props.get("method") == timeline["method"] and not props.get("fixture_mode"), "Real Rust props identity/timing required")
    require(all(props.get(k) == timeline[k] for k in ("duration", "scenes", "words", "captions")), "Rust props differ from current measured timeline")
    require(props.get("burnCaptions") is (name == "shorts-props.json"), "Separate clean/captioned destination props required")
