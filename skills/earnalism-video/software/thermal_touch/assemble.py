"""Assemble new thermal-touch speech from exact published Spoon B settings.

No synthesis, inferred word timing, spelling auto-acceptance or time/pitch repair.
All new listening/AV decisions stay PENDING. A prior/partial output refuses reuse;
use --output with a fresh directory for an explicitly separate assembly attempt.
"""

from pathlib import Path
from fractions import Fraction
import argparse
import copy
import difflib
import hashlib
import json
import math
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
from caption_layout import compose, punctuate, quality

PUBLISHED_B_ROOT = PROJECT / "output/episodes/03-refraction/production-v1"
PUBLISHED_BASELINE_SHA256 = "2ba56e871bfecca948d331a9e0e712155b376ef745b65448db359ee755e1a215"
PUBLISHED_METADATA_SHA256 = "80119a26b02d3b1ffdfd4c2db100854ab75fa809bd5c34f4a0b6d6c8b5a6dacf"
WORKER_SHA256 = "55500c69d0529ded866c744d5242d1c9320625bece8eb56958b8086948e2beeb"
ASR_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
NORMALIZE_FILTER = "loudnorm=I=-17:TP=-2:LRA=11"
RESERVED = (
    ".thermal-assembly-lock.json", "asr-review.json", "caption-quality.json",
    "timeline.json", "props.json", "clean-shorts-props.json", "shorts-props.json",
    "captions.srt", "captions.vtt", "transcript.txt", "concat.txt", "narration.wav",
    "voice-binding.json", "review.json", "assembly-manifest.json",
)


class QualificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise QualificationError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value, *, as_json=True):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
                     if as_json else value)


def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?|\d+", text.lower().replace("’", "'"))


def differences(expected, recognized):
    a, b = tokens(expected), tokens(recognized)
    return [{"tag": tag, "expected": a[i:j], "recognized": b[k:l]}
            for tag, i, j, k, l in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
            if tag != "equal"]


def published_b_reference():
    baseline_path = PUBLISHED_B_ROOT / "baseline-job.json"
    metadata_path = PUBLISHED_B_ROOT / "imported/raw/s01.wav.json"
    require(sha(baseline_path) == PUBLISHED_BASELINE_SHA256, "Published B baseline changed")
    require(sha(metadata_path) == PUBLISHED_METADATA_SHA256, "Published B recipe evidence changed")
    require(sha(BASE / "vendor/qwen_worker.py") == WORKER_SHA256, "Pinned narration worker changed")
    return load(baseline_path), load(metadata_path)


def validate_baseline(baseline):
    reference, _ = published_b_reference()
    require(baseline == reference, "baseline-job.json is not the exact published Spoon B baseline")
    return reference


def probe_wav(path):
    result = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a", "-show_streams",
        "-show_format", "-of", "json", str(path),
    ], text=True))
    require(len(result.get("streams", [])) == 1, "Expected one audio stream")
    stream = result["streams"][0]
    sample_rate = int(stream["sample_rate"])
    duration = (float(int(stream["duration_ts"]) * Fraction(stream["time_base"]))
                if "duration_ts" in stream else float(result["format"]["duration"]))
    require(math.isfinite(duration) and duration > 0, "Invalid actual WAV duration")
    return {"sample_rate": sample_rate, "channels": int(stream["channels"]),
            "codec": stream["codec_name"], "duration": duration,
            "samples": round(duration * sample_rate)}


def validate_source(unit, wav, metadata, baseline):
    """Verify actual WAV, all voice controls, selected retry and provenance binding."""
    reference_baseline, reference_metadata = published_b_reference()
    require(baseline == reference_baseline, "Published B baseline mismatch")
    digest = sha(wav)
    require(metadata.get("wav_sha256") == digest, "Source WAV hash is stale")
    require(metadata.get("schema") == "earnalism.qwen.customvoice.v1" and
            metadata.get("segment_id") == unit["id"] and
            metadata.get("status") == "GENERATED_REQUIRES_REVIEW", "Invalid source generation record")
    settings = metadata["settings"]
    expected = copy.deepcopy(reference_metadata["settings"])
    for key in ("source_cache_key", "segment_id", "text", "provenance_binding"):
        expected[key] = settings.get(key)
    require(settings == expected, "B voice/generation/validation settings changed")
    require(settings.get("segment_id") == unit["id"] and settings.get("text") == unit["text"],
            "Source script/segment differs from current unit")
    require(re.fullmatch(r"[0-9a-f]{64}", settings.get("source_cache_key", "")) is not None,
            "Missing source cache identity")
    require(metadata.get("effective_key") == object_hash(settings), "Effective settings hash mismatch")

    provenance, binding = metadata["provenance"], settings["provenance_binding"]
    reference_provenance = reference_metadata["provenance"]
    for key in ("model_id", "model_revision", "worker_sha256", "dtype", "attention"):
        require(provenance.get(key) == reference_provenance[key], f"Pinned {key} changed")
    require(binding.get("model_id") == baseline["model_id"] and
            binding.get("model_revision") == baseline["model_revision"] and
            binding.get("worker_sha256") == WORKER_SHA256, "Provenance binding changed")
    model_path = Path(provenance.get("model_path", ""))
    require(model_path.is_absolute() and model_path.name == baseline["model_revision"] and
            model_path.parent.name == "snapshots" and model_path.parent.parent.name ==
            "models--" + baseline["model_id"].replace("/", "--"), "Wrong model snapshot path")
    snapshot = provenance["snapshot"]
    require(object_hash(snapshot["files"]) == snapshot["manifest_sha256"] ==
            reference_provenance["snapshot"]["manifest_sha256"] == binding.get("snapshot_sha256"),
            "Pinned snapshot manifest changed")
    environment = provenance["environment"]
    for key in ("python", "packages", "qwen_package_source_sha256", "torch_cuda_version", "torch_cudnn_version"):
        require(binding.get(key) == environment.get(key), "Environment/binding evidence disagrees: " + key)
    require(binding.get("hardware") == provenance.get("hardware"), "Hardware/binding evidence disagrees")
    require(provenance["hardware"].get("device") == "cuda:0", "Source used an unexpected CUDA device")
    require(environment.get("qwen_package_source_sha256") ==
            reference_provenance["environment"]["qwen_package_source_sha256"], "Qwen package source changed")
    for package in ("qwen-tts", "torch", "transformers", "torchaudio"):
        require(environment["packages"].get(package) ==
                reference_provenance["environment"]["packages"][package], "Pinned voice package changed: " + package)

    attempt = metadata.get("selected_attempt")
    require(isinstance(attempt, int) and not isinstance(attempt, bool) and 1 <= attempt <= 3,
            "Selected retry is outside the persistent bounded worker policy")
    seed = (baseline["segments"][0]["seed"] + attempt - 1) % (2**32)
    require(metadata.get("selected_seed") == seed, "Selected retry seed mismatch")
    selected = [a for a in metadata.get("attempts", []) if a.get("attempt") == attempt]
    require(len(selected) == 1 and selected[0].get("status") == "PASS" and
            selected[0].get("seed") == seed and selected[0].get("effective_key") == metadata["effective_key"] and
            selected[0].get("audio") == metadata["audio"], "Selected successful attempt is not bound to source")
    audio = metadata["audio"]
    require(audio.get("mechanical_checks") == "PASS" and not audio.get("failure_reasons") and
            audio.get("token_cap_suspicion") is False, "Source mechanical checks did not pass")
    actual = probe_wav(wav)
    require(actual["codec"] == "pcm_f32le" and actual["channels"] == 1 and
            actual["sample_rate"] == audio["sample_rate"] == 24000 and
            actual["samples"] == audio["samples"] and
            abs(actual["duration"] - audio["duration_seconds"]) < 1 / 24000,
            "Actual WAV stream does not match validated native recording")
    return {"audio_sha256": digest, "duration": actual["duration"], "stream": actual,
            "selected_attempt": attempt, "selected_seed": seed,
            "environment": environment, "new_recording_listening": "PENDING"}


def alignment_audit(unit, alignment, audio_sha256, duration):
    require(alignment.get("audio_sha256") == audio_sha256, "Alignment is stale for current WAV")
    require(alignment.get("model_revision") == ASR_REVISION, "ASR model revision changed")
    words = alignment.get("word_times")
    require(isinstance(words, list) and words, "Actual-audio word timestamps are required")
    previous_end = 0.0
    for word in words:
        require(isinstance(word.get("word"), str) and tokens(word["word"]), "Invalid ASR word text")
        start, end = word.get("start"), word.get("end")
        require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                    for v in (start, end)) and 0 <= start < end <= duration + 0.001 and
                start + 0.001 >= previous_end, "Invalid/out-of-range/overlapping actual word times")
        previous_end = end
    recognized = alignment.get("recognized")
    require(isinstance(recognized, str), "Missing raw recognized text")
    raw_differences = differences(unit["text"], recognized)
    word_differences = differences(recognized, " ".join(w["word"] for w in words))
    record = {"unit": unit["id"], "audio_sha256": audio_sha256,
              "expected": unit["text"], "recognized": recognized,
              "raw_differences": raw_differences, "word_time_differences": word_differences,
              "differences": raw_differences + word_differences,
              "resolution": None, "automatic_equivalence_applied": False,
              "source_validation": "PASS", "listening": "PENDING"}
    return record, punctuate(copy.deepcopy(words), unit["text"])


def actual_anchor(words, phrase):
    """Unique phrase onset from real word times; never estimate inside a word."""
    needle = tokens(phrase)
    require(needle, "Anchor phrase is empty")
    lexical, origin = [], []
    for index, word in enumerate(words):
        for token in tokens(word["word"]):
            lexical.append(token)
            origin.append(index)
    starts = [i for i in range(len(lexical) - len(needle) + 1)
              if lexical[i:i + len(needle)] == needle]
    require(len(starts) == 1, ("Missing" if not starts else "Ambiguous") + " actual-audio anchor: " + phrase)
    start = starts[0]
    require(start == 0 or origin[start] != origin[start - 1],
            "Anchor begins inside an unsplit recognized word; no subword time exists: " + phrase)
    return words[origin[start]]["start"]


def validate_units(units):
    require(isinstance(units, list) and len(units) == 6, "This episode needs six thought units")
    ids = []
    for unit in units:
        require(isinstance(unit, dict) and re.fullmatch(r"[A-Za-z0-9_-]+", unit.get("id", "")) and
                isinstance(unit.get("scene"), str) and unit["scene"].strip() and
                isinstance(unit.get("text"), str) and tokens(unit["text"]), "Invalid thought unit")
        require(not ({"start", "end", "marks"} & set(unit)), "Unit contains estimated final timing")
        anchors = unit.get("anchors", {})
        require(isinstance(anchors, dict) and all(isinstance(k, str) and
                re.fullmatch(r"[A-Za-z0-9_-]+", k) and isinstance(v, str) and tokens(v)
                for k, v in anchors.items()), "Invalid explicit anchor mapping")
        ids.append(unit["id"])
    require(len(set(ids)) == len(ids), "Thought-unit IDs must be unique")


def reserve_outputs(output):
    output = Path(output)
    require(not any((output / name).exists() for name in RESERVED),
            "Existing or partial assembly output preserved; choose a fresh --output directory")
    output.mkdir(parents=True, exist_ok=True)
    write_new(output / RESERVED[0], {"state": "EXCLUSIVE_NEW_ASSEMBLY", "publication_approved": False})


def concat_line(path):
    path = str(Path(path).resolve())
    require("\n" not in path and "\r" not in path, "Unsafe newline in concat input path")
    return "file '" + path.replace("'", "'\\''") + "'"


def stamp(seconds, separator):
    millis = round(seconds * 1000)
    return (f"{millis // 3600000:02}:{millis // 60000 % 60:02}:"
            f"{millis // 1000 % 60:02}{separator}{millis % 1000:03}")


def normalize_narration(concat_file, output_file):
    """Only concatenate and normalize; no tempo, pitch or pause editing."""
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "concat", "-safe", "0", "-i",
                    str(concat_file), "-af", NORMALIZE_FILTER, "-ar", "48000",
                    "-ac", "1", "-c:a", "pcm_f32le", str(output_file)], check=True)


def assemble(root, output_dir=None):
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root
    units, baseline = load(root / "units.json"), load(root / "baseline-job.json")
    validate_units(units)
    validate_baseline(baseline)
    try:
        from .recovery import verify_imported
    except ImportError:
        from thermal_touch.recovery import verify_imported
    recovery_sources, recovery_accounting = verify_imported(root, units, baseline)
    reserve_outputs(output)
    sources = {"units.json": sha(root / "units.json"), "baseline-job.json": sha(root / "baseline-job.json")}
    sources.update(recovery_sources)
    audits, validated = [], []
    for unit in units:
        wav = root / "imported/raw" / (unit["id"] + ".wav")
        metadata_path = Path(str(wav) + ".json")
        alignment_path = root / "imported/alignment" / (unit["id"] + ".json")
        audit = None
        try:
            source = validate_source(unit, wav, load(metadata_path), baseline)
            audit, words = alignment_audit(unit, load(alignment_path), source["audio_sha256"], source["duration"])
            audits.append(audit)
            if audit["differences"]:
                # Preserve every raw discrepancy even if its associated scene
                # anchor would be missing; do not reinterpret ASR errors away.
                continue
            marks = {name: actual_anchor(words, phrase) for name, phrase in unit.get("anchors", {}).items()}
            for path in (wav, metadata_path, alignment_path):
                sources[str(path.relative_to(root))] = sha(path)
            validated.append((unit, wav, source, words, marks))
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
            if audit is not None:
                audit["anchor_validation"] = "FAIL"
                audit["error"] = str(exc)
            else:
                audits.append({"unit": unit["id"], "source_validation": "FAIL", "error": str(exc),
                               "resolution": None, "listening": "PENDING"})
    write_new(output / "asr-review.json", audits)
    require(len(validated) == len(units) and all(not a.get("differences") and
            a.get("source_validation") == "PASS" for a in audits),
            "Unresolved source/ASR/anchor findings; inspect asr-review.json. No narration assembled.")

    words, scenes, offset = [], [], 0.0
    for unit, wav, source, actual_words, marks in validated:
        scenes.append({**unit, "start": offset, "end": offset + source["duration"], "marks": marks})
        words.extend(dict(w, start=w["start"] + offset, end=w["end"] + offset) for w in actual_words)
        offset += source["duration"]
    try:
        cues = compose(words)
        issues = quality(cues)
    except ValueError as exc:
        write_new(output / "caption-quality.json", {"issues": [str(exc)], "timing": "actual audio word timestamps"})
        raise QualificationError("Caption readability requires repair; no narration assembled") from exc
    write_new(output / "caption-quality.json", {"issues": issues, "cue_count": len(cues),
                                               "timing": "actual audio word timestamps"})
    require(not issues, "Caption readability requires repair")
    require(tokens(" ".join(c["text"] for c in cues)) == tokens(" ".join(u["text"] for u in units)),
            "Caption partition changed spoken words")

    write_new(output / "timeline.json", {"duration": offset, "timing": "actual WAV lengths and ASR word marks",
                                        "scenes": scenes})
    props = {"duration": offset, "scenes": scenes, "captions": cues, "burnCaptions": False, "outro": True}
    write_new(output / "props.json", props)
    write_new(output / "clean-shorts-props.json", props)
    write_new(output / "shorts-props.json", {**props, "burnCaptions": True})
    for extension, separator in (("srt", ","), ("vtt", ".")):
        body = "\n\n".join((str(i + 1) + "\n" if extension == "srt" else "") +
                            f"{stamp(c['start'], separator)} --> {stamp(c['end'], separator)}\n{c['text']}"
                            for i, c in enumerate(cues))
        write_new(output / ("captions." + extension),
                  ("WEBVTT\n\n" if extension == "vtt" else "") + body + "\n", as_json=False)
    write_new(output / "transcript.txt", "\n\n".join(u["text"] for u in units) + "\n", as_json=False)
    write_new(output / "concat.txt", "ffconcat version 1.0\n" +
              "\n".join(concat_line(wav) for _, wav, _, _, _ in validated) + "\n", as_json=False)
    normalize_narration(output / "concat.txt", output / "narration.wav")
    actual_output = probe_wav(output / "narration.wav")
    require(abs(actual_output["duration"] - offset) <= 0.02, "Unexpected normalization/concat timing change")
    require(all(sha(root / name) == digest for name, digest in sources.items()),
            "Source changed during assembly; output remains unqualified")
    write_new(output / "voice-binding.json", {
        "source": "Exact published Spoon B generation recipe; new thought-unit recording",
        "baseline_sha256": PUBLISHED_BASELINE_SHA256, "worker_sha256": WORKER_SHA256,
        "instruction_sha256": hashlib.sha256(baseline["segments"][0]["instruct"].encode()).hexdigest(),
        "generation": baseline["generation"], "dtype": baseline["dtype"], "attention": baseline["attention"],
        "seed_base": baseline["segments"][0]["seed"],
        "raw_audio": {u["id"]: source["audio_sha256"] for u, _, source, _, _ in validated},
        "input_files": sources, "narration_sha256": sha(output / "narration.wav"),
        "normalization_filter": NORMALIZE_FILTER, "output_sample_rate": 48000,
        "no_tempo_or_pitch_change": True, "source_wavs_preserved": True,
        "recovery_accounting": recovery_accounting,
        "new_recording": True, "new_recording_listening": "PENDING", "publication_approved": False,
    })
    write_new(output / "review.json", {
        "state": "PRIVATE_NEW_NARRATION_REQUIRES_REVIEW", "publication_approved": False,
        "facts": "PENDING", "graphics_captions": "PENDING", "rights": "PENDING",
        "listening_av": "PENDING", "technical_delivery": "PENDING",
        "note": "Mechanical/ASR assembly checks do not invent listening, graphical review or owner approval.",
    })
    write_new(output / "assembly-manifest.json", {
        "state": "ASSEMBLED_PRIVATE_REQUIRES_REVIEW", "source_root": str(root),
        "input_files": sources, "output_files": {name: sha(output / name) for name in RESERVED
                                                  if name != "assembly-manifest.json" and (output / name).is_file()},
        "new_recording_listening": "PENDING", "publication_approved": False,
    })
    return {"output": str(output), "duration": offset, "cue_count": len(cues),
            "new_recording_listening": "PENDING", "publication_approved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, help="Fresh output directory; default is production root")
    args = parser.parse_args()
    print(json.dumps(assemble(args.root, args.output), indent=2))
