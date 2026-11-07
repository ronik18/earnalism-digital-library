"""Fresh-only private thermal-touch score, fixed soundtrack and copied-audio mux.

The new F#–A–E motif follows heat transfer, then reverses at the warm-object
thought. Acoustic one-shot performances are from the existing hash-pinned CC0
VCSL collection; no composition or timings are borrowed from earlier episodes.
Nothing here synthesizes or time/pitch-edits narration, grants listening approval,
or publishes. The original standard nonverbal ident is appended after body-only
mastering, with decoded sample equality checked before delivery encoding.
"""
from pathlib import Path
import argparse
import array
import hashlib
import json
import math
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
import acoustic_score
try:
    from .assemble import QualificationError, load, probe_wav, require, sha, write_new
except ImportError:
    from thermal_touch.assemble import QualificationError, load, probe_wav, require, sha, write_new

RATE = 48000
FPS = 30
IDENT_ROOT = BASE / "assets/standard-intro/v1"
IDENT_MANIFEST_SHA256 = "b1443346d98df717d7a399dd72c00a7d21347f4de1748c601c4093305672fa28"
# An episode-specific starting mix target, not a universal aesthetic/listening gate.
SCORE_FILTER = "loudnorm=I=-30:TP=-9:LRA=10"
MIX_FILTER = "[0:a][1:a]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
SCORE_FILES = (
    ".thermal-finish-lock.json", "score-plan.json", "score-piano.wav", "score-harp.wav",
    "score-unmastered.wav", "score.wav", "score.provenance.json", "mix.wav",
    "soundtrack.wav", "dry-soundtrack.wav", "soundtrack.m4a", "dry-soundtrack.m4a",
    "mix-provenance.json",
)
SCENE_KINDS = ("question", "flow", "material", "temperature", "reverse", "callback")
REQUIRED_MARKS = {"question": ("equal",), "flow": ("touch",),
                  "material": ("metal", "wood", "cooling"),
                  "temperature": ("stores", "touch"),
                  "reverse": ("warm", "reverse", "hotter", "safety"),
                  "callback": ("callback", "next")}


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def validate_timeline(timeline):
    seconds = timeline.get("duration")
    require(isinstance(seconds, (int, float)) and math.isfinite(seconds) and seconds > 0,
            "Invalid actual narration duration")
    scenes = timeline.get("scenes", [])
    require(tuple(s.get("scene") for s in scenes) == SCENE_KINDS,
            "Expected the current six thermal-touch thoughts in order")
    last = 0.0
    for scene in scenes:
        start, end = scene.get("start"), scene.get("end")
        require(all(isinstance(t, (int, float)) and math.isfinite(t) for t in (start, end)) and
                abs(start - last) < .001 and end > start, "Noncontiguous actual scene timings")
        marks = scene.get("marks", {})
        expected = REQUIRED_MARKS[scene["scene"]]
        require(all(m in marks for m in expected), f"Missing explicit {scene['scene']} score anchor")
        for name, value in marks.items():
            require(isinstance(value, (int, float)) and math.isfinite(value) and
                    0 <= value < end - start, f"Invalid relative audio mark {name}")
        require(all(marks[a] < marks[b] for a, b in zip(expected, expected[1:])),
                "Spoken thought anchors are out of order")
        last = end
    require(abs(last - seconds) < .001, "Scene end does not match actual narration length")
    return seconds, scenes


def mark(scene, name):
    """Marks are relative actual ASR onsets, never invented sentence timings."""
    return scene["start"] + scene["marks"][name]


def phrase_plan(timeline):
    seconds, scenes = validate_timeline(timeline)
    by_kind = {s["scene"]: s for s in scenes}
    q, contact, material, caveat, reverse, callback = (by_kind[k] for k in SCENE_KINDS)
    rests = [
        {"reason": "opening question", "start": 0.0, "end": q["end"]},
        {"reason": "first contact", "start": max(contact["start"], mark(contact, "touch") - .25),
         "end": min(contact["end"], mark(contact, "touch") + 2.4)},
        {"reason": "key wood/skin contrast", "start": max(material["start"], mark(material, "wood") - .2),
         "end": min(material["end"], mark(material, "cooling") + 1.5)},
        {"reason": "reversal and safety", "start": max(reverse["start"], mark(reverse, "reverse") - .3),
         "end": reverse["end"]},
        {"reason": "callback into nonverbal ident", "start": mark(callback, "next"), "end": seconds},
    ]
    # Only intentional fixed rests/slow phrase shoulders; no speech-envelope ducking.
    intervals = [(r["start"], r["end"]) for r in rests]
    events = []

    def add(at, notes, instrument, velocity, duration, phrase):
        for i, midi in enumerate(notes):
            t = at + i * .11
            if 0 <= t < seconds - .8 and shoulder(t, intervals) > .08:
                events.append({"time": round(t, 6), "midi": midi, "instrument": instrument,
                               "velocity": velocity * (1 - .06 * i), "duration": duration,
                               "phrase": phrase, "pan": -.10 if instrument == "piano" else .10})

    # A few warm open voicings and a sparse recurring three-note thought. Their
    # placements derive from this recording's words and scene spans, not wall times.
    add(contact["start"] + .8, [50, 57, 59, 66], "piano", .31, 5.8, "D sixth/open warmth")
    add(mark(material, "metal") + .4, [52, 59, 66], "piano", .30, 5.6, "energy carried away")
    add(caveat["start"] + .5, [50, 57, 66], "piano", .30, 6.0, "conducting and storing")
    add(reverse["start"] + .35, [52, 57, 64], "piano", .28, 5.0, "a change of direction")
    add(callback["start"] + .6, [50, 57, 66], "piano", .32, 6.0, "same initial temperature")
    motif_specs = [
        (material, "metal", [66, 69, 64], "F sharp A E: a transfer question"),
        (caveat, "stores", [66, 69, 64], "F sharp A E: thoughtful return"),
        (reverse, "warm", [64, 69, 66], "E A F sharp: the direction reverses"),
        (callback, "callback", [66, 64, 62], "F sharp E D: return to the thermometers"),
    ]
    for scene, anchor, notes, description in motif_specs:
        for dt, midi, velocity in zip((.75, 2.6, 4.8), notes, (.30, .25, .28)):
            at = mark(scene, anchor) + dt
            if at < scene["end"] - .7:
                add(at, [midi], "harp", velocity, 4.2, description)
    return {"title": "Between Touch and Temperature", "version": "thermal-touch-original-v1",
            "duration": seconds, "events": sorted(events, key=lambda e: e["time"]),
            "rests": rests, "quiet_intervals": intervals,
            "fade_out_seconds": 3.2, "fade_in_seconds": 4.5,
            "composition": "Original F sharp A E transfer motif, reversed E A F sharp response, "
                           "F sharp E D callback over sparse open D-sixth/E voicings",
            "timing_source": "Current actual WAV scene lengths and explicit ASR phrase onsets",
            "listening": "PENDING", "resemblance_review": "PENDING", "publication_approved": False}


def smoothstep(value):
    x = min(1.0, max(0.0, value))
    return x * x * x * (x * (x * 6 - 15) + 10)


def shoulder(t, rests, fade_out=3.2, fade_in=4.5):
    """C2-continuous phrase curves; genuine zeros throughout each authored rest.

    Multiply overlapping shoulders: taking their minimum creates a derivative
    cusp where a return meets the next fade, despite smooth individual curves.
    """
    require(fade_out > 0 and fade_in > 0, "Fade lengths must be positive")
    gain = 1.0
    for a, b in rests:
        require(0 <= a < b, "Invalid authored rest")
        if a <= t <= b:
            return 0.0
        if t < a:
            gain *= smoothstep((a - t) / fade_out)
        else:
            gain *= smoothstep((t - b) / fade_in)
    return gain


def validate_ident(root=IDENT_ROOT):
    root = Path(root)
    require(sha(root / "manifest.json") == IDENT_MANIFEST_SHA256, "Standard ident manifest changed")
    manifest = load(root / "manifest.json")
    require(manifest.get("seconds") == 3, "Wrong standard ident length")
    for name, digest in manifest["files"].items():
        require(Path(name).name == name and sha(root / name) == digest, "Standard ident asset changed")
    require(load(root / "sound-provenance.json").get("original_synthesis") is True,
            "Standard nonverbal sound provenance changed")
    info = probe_wav(root / "source-sound.wav")
    require(info["sample_rate"] == RATE and info["channels"] == 2 and info["samples"] == RATE * 3,
            "Standard ident PCM dimensions changed")
    return manifest


def validate_inputs(root):
    root = Path(root)
    manifest = load(root / "assembly-manifest.json")
    binding = load(root / "voice-binding.json")
    require(manifest.get("state") == "ASSEMBLED_PRIVATE_REQUIRES_REVIEW", "No qualified new assembly")
    for name in ("timeline.json", "narration.wav", "voice-binding.json", "asr-review.json",
                 "caption-quality.json"):
        require(manifest.get("output_files", {}).get(name) == sha(root / name),
                f"Stale assembly output: {name}")
    require(binding.get("narration_sha256") == sha(root / "narration.wav") and
            binding.get("no_tempo_or_pitch_change") is True, "Voice binding mismatch")
    source = Path(manifest["source_root"])
    require(all(sha(source / name) == digest for name, digest in manifest["input_files"].items()),
            "Original narration source/evidence changed")
    require(all(a.get("source_validation") == "PASS" and not a.get("differences")
                for a in load(root / "asr-review.json")), "Unresolved ASR finding")
    require(not load(root / "caption-quality.json").get("issues"), "Caption issue remains")
    timeline = load(root / "timeline.json")
    seconds, _ = validate_timeline(timeline)
    info = probe_wav(root / "narration.wav")
    require(info["sample_rate"] == RATE and abs(info["duration"] - seconds) < .02,
            "Narration length/sample rate differs from actual timeline")
    return timeline, {name: sha(root / name) for name in
                      ("assembly-manifest.json", "timeline.json", "voice-binding.json", "narration.wav")}


def reserve_outputs(root, names=SCORE_FILES):
    root = Path(root)
    require(not any((root / name).exists() for name in names),
            "Existing or partial finishing outputs preserved; use a fresh assembled candidate")
    write_new(root / names[0], {"state": "EXCLUSIVE_PRIVATE_NEW_FINISH", "publication_approved": False})


def render_score(root, plan, asset_root=acoustic_score.ASSETS):
    """Reuse pinned sample decoding/rights validation, with a new local event plan.

    Deliberately does not replace acoustic_score.plan or score.quiet_gain globals,
    and never copies the older composer's Moon-specific title/provenance.
    """
    root, asset_root = Path(root), Path(asset_root)
    manifest = acoustic_score.validate_assets(asset_root)
    rate = 24000
    frames = round(plan["duration"] * rate)
    stems = {name: array.array("f", [0.0]) * (frames * 2) for name in ("piano", "harp")}
    cache, used = {}, {}
    for event in plan["events"]:
        key = (event["instrument"], event["midi"])
        if key not in cache:
            row = min((r for r in manifest["samples"] if r["instrument"] == key[0]),
                      key=lambda r: abs(r["root_midi"] - key[1]))
            shift = key[1] - row["root_midi"]
            require(abs(shift) <= 2, "Acoustic note exceeds approved two-semitone sample range")
            ratio = 2 ** (shift / 12)
            raw = array.array("f", subprocess.check_output([
                "ffmpeg", "-v", "error", "-i", str(asset_root / row["file"]), "-af",
                f"aresample={rate},asetrate={rate * ratio},aresample={rate},highpass=f=85,lowpass=f=7000",
                "-ar", str(rate), "-ac", "2", "-f", "f32le", "-"]))
            if sys.byteorder != "little":
                raw.byteswap()
            peak = max(abs(x) for x in raw)
            require(peak > 1e-7, "Silent source acoustic sample")
            cache[key], used[row["file"]] = (raw, .075 / peak), row
        raw, amplitude = cache[key]
        first = round(event["time"] * rate)
        length = min(len(raw) // 2, round((event["duration"] + .9) * rate), frames - first)
        left = math.cos((event["pan"] + 1) * math.pi / 4) * math.sqrt(2)
        right = math.sin((event["pan"] + 1) * math.pi / 4) * math.sqrt(2)
        for i in range(length):
            dt = i / rate
            envelope = min(1, dt / .012, max(0, (event["duration"] + .9 - dt) / .9))
            gain = amplitude * event["velocity"] * envelope
            index = (first + i) * 2
            stems[key[0]][index] += raw[i * 2] * gain * left
            stems[key[0]][index + 1] += raw[i * 2 + 1] * gain * right
    for instrument, pcm in stems.items():
        acoustic_score._wav(root / f"score-{instrument}.wav", pcm, rate)
    mixed = array.array("f", [0.0]) * (frames * 2)
    for i in range(frames):
        t = i / rate
        gain = shoulder(t, plan["quiet_intervals"], plan["fade_out_seconds"], plan["fade_in_seconds"])
        for channel in (0, 1):
            index = i * 2 + channel
            mixed[index] = (stems["piano"][index] + stems["harp"][index]) * gain
    acoustic_score._wav(root / "score-unmastered.wav", mixed, rate)
    run("ffmpeg", "-v", "error", "-n", "-i", root / "score-unmastered.wav", "-af", SCORE_FILTER,
        "-ar", RATE, "-ac", "2", "-c:a", "pcm_f32le", root / "score.wav")
    return {"sample_collection": "VCSL", "license": "CC0-1.0", "revision": manifest["revision"],
            "third_party_samples": list(used.values()), "external_compositions": [],
            "asset_manifest_sha256": sha(asset_root / "manifest.json"),
            "license_sha256": sha(asset_root / "LICENSE"), "readme_sha256": sha(asset_root / "README.md"),
            "composer_sha256": sha(__file__), "sample_engine_sha256": sha(BASE / "acoustic_score.py"),
            "performance": "Computer-arranged acoustic one-shot notes; not a live human ensemble",
            "mastering": SCORE_FILTER, "recording_sha256": sha(root / "score.wav"),
            "stems": {f"score-{name}.wav": sha(root / f"score-{name}.wav")
                      for name in ("piano", "harp", "unmastered")}}


def pcm(path):
    return acoustic_score._pcm(path, RATE)


def rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else 0.0


def db(value):
    return 20 * math.log10(value) if value > 0 else None


def passage_evidence(narration, music, timeline, plan):
    """Numeric passage evidence only: no pretend naturalness/music acceptance."""
    voice, score = pcm(narration), pcm(music)
    require(abs(len(voice) - len(score)) <= RATE * 2 * .02, "Score/narration lengths differ")
    measurements = []
    for scene in timeline["scenes"]:
        boundaries = sorted(set([scene["start"], scene["end"]] +
                                [mark(scene, key) for key in scene["marks"]]))
        for a, b in zip(boundaries, boundaries[1:]):
            if b - a < .25:
                continue
            start, end = round(a * RATE) * 2, round(b * RATE) * 2
            v, m = rms(voice[start:end]), rms(score[start:end])
            measurements.append({"scene": scene["scene"], "start": a, "end": b,
                                 "voice_rms_dbfs": db(v), "score_rms_dbfs": db(m),
                                 "score_minus_voice_db": db(m / v) if v else None,
                                 "interpretation": "MEASUREMENT_ONLY_LISTENING_PENDING"})
    rests = []
    for rest in plan["rests"]:
        # Exclude just 10 ms at boundaries to ignore resampling-filter footprints.
        a, b = rest["start"] + .01, rest["end"] - .01
        require(b > a, "Rest too short for silence check")
        samples = score[round(a * RATE) * 2:round(b * RATE) * 2]
        peak = max((abs(v) for v in samples), default=0)
        require(peak < 1e-8, "Authored score rest is not digitally silent")
        rests.append({**rest, "measured_interior_peak": peak, "score_silence": "PASS"})
    return {"passages": measurements, "authored_rests": rests,
            "listening": "PENDING", "resemblance_review": "PENDING"}


def append_ident_command(body, ident, output, padded_seconds):
    return ["ffmpeg", "-v", "error", "-n", "-i", str(body), "-i", str(ident),
            "-filter_complex", f"[0:a]apad=whole_dur={padded_seconds:.9f},"
            f"atrim=duration={padded_seconds:.9f},aresample={RATE},aformat=channel_layouts=stereo[a];"
            f"[1:a]aresample={RATE},aformat=channel_layouts=stereo[b];"
            "[a][b]concat=n=2:v=0:a=1[out]", "-map", "[out]", "-ar", str(RATE),
            "-ac", "2", "-c:a", "pcm_f32le", str(output)]


def verify_ident_tail(soundtrack, ident, body_samples):
    actual, reference = pcm(soundtrack), pcm(ident)
    tail = actual[body_samples * 2:]
    require(tail.tobytes() == reference.tobytes(), "Standard nonverbal ident sample equality failed")
    return {"decoded_pcm_sha256": hashlib.sha256(tail.tobytes()).hexdigest(),
            "ident_pcm_sha256": hashlib.sha256(reference.tobytes()).hexdigest(),
            "samples_per_channel": len(reference) // 2, "exact_decoded_pcm_match": True}


def finish(root):
    root = Path(root).resolve()
    timeline, inputs = validate_inputs(root)
    ident_manifest = validate_ident()
    plan = phrase_plan(timeline)
    reserve_outputs(root)
    write_new(root / "score-plan.json", plan)
    rights = render_score(root, plan)
    evidence = passage_evidence(root / "narration.wav", root / "score.wav", timeline, plan)
    write_new(root / "score.provenance.json", {**plan, **rights,
              "measurements": evidence, "rights_scope": "Pinned CC0 sample provenance; not a legal opinion "
              "or musical-resemblance verdict", "publication_approved": False})
    run("ffmpeg", "-v", "error", "-n", "-i", root / "narration.wav", "-i", root / "score.wav",
        "-filter_complex", MIX_FILTER, "-map", "[a]", "-ar", RATE, "-ac", "2", "-c:a",
        "pcm_f32le", root / "mix.wav")
    body_samples = math.ceil(timeline["duration"] * FPS) * (RATE // FPS)
    padded_seconds = body_samples / RATE
    ident = IDENT_ROOT / "source-sound.wav"
    tails = {}
    for name, body in (("soundtrack", "mix.wav"), ("dry-soundtrack", "narration.wav")):
        run(*append_ident_command(root / body, ident, root / f"{name}.wav", padded_seconds))
        tails[name] = verify_ident_tail(root / f"{name}.wav", ident, body_samples)
        # One common encode reused verbatim by landscape and both portrait deliveries.
        run("ffmpeg", "-v", "error", "-n", "-i", root / f"{name}.wav", "-c:a", "aac",
            "-b:a", "192k", "-ar", RATE, "-ac", "2", "-movflags", "+faststart", root / f"{name}.m4a")
    require(all(sha(root / name) == digest for name, digest in inputs.items()),
            "Accepted assembly/narration changed during finishing")
    write_new(root / "mix-provenance.json", {
        "state": "PRIVATE_NEW_SCORE_REQUIRES_LISTENING", "inputs": inputs,
        "narration_sha256": inputs["narration.wav"], "narration_source_unchanged": True,
        "pitch_or_tempo_changed": False, "pause_edits": False, "reactive_ducking": False,
        "body_mix_filter": MIX_FILTER, "normalization_scope": "Body mix only; narration gain can change "
        "in the scored mix. The source narration file and its phrasing remain untouched.",
        "body_duration": timeline["duration"], "body_frame_padding": padded_seconds - timeline["duration"],
        "final_duration": padded_seconds + 3, "ident_manifest": ident_manifest,
        "ident_manifest_sha256": sha(IDENT_ROOT / "manifest.json"), "ident_tail_checks": tails,
        "score_sha256": sha(root / "score.wav"), "measurements": evidence,
        "output_files": {name: sha(root / name) for name in SCORE_FILES
                         if name != "mix-provenance.json" and (root / name).is_file()},
        "human_listening": "PENDING", "audiovisual_acceptance": "PENDING", "publication_approved": False})
    return {"output": str(root), "duration": padded_seconds + 3,
            "listening": "PENDING", "publication_approved": False}


def stream_audio_hash(path):
    return subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
                                    "-c:a", "copy", "-f", "hash", "-hash", "sha256", "-"], text=True).strip()


def mux(root, fmt):
    root = Path(root).resolve()
    require(fmt in ("landscape", "shorts", "clean-shorts"), "Unknown private format")
    folder = root / fmt
    animation = folder / "animation.mp4"
    evidence = load(root / "mix-provenance.json")
    require(evidence.get("narration_sha256") == sha(root / "narration.wav"), "Narration changed")
    for name, digest in evidence["output_files"].items():
        require(sha(root / name) == digest, "Soundtrack source/evidence changed before mux")
    outputs = (".thermal-mux-lock.json", "video.mp4", "narration-only.mp4", "technical.json")
    reserve_outputs(folder, outputs)
    data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                               "-of", "json", str(animation)], text=True))
    video = [s for s in data["streams"] if s["codec_type"] == "video"]
    require(len(video) == 1 and not any(s["codec_type"] == "audio" for s in data["streams"]),
            "Animation must have exactly one video stream and no competing soundtrack")
    expected_size = (1920, 1080) if fmt == "landscape" else (1080, 1920)
    require((video[0]["width"], video[0]["height"]) == expected_size, "Wrong composition dimensions")
    require(abs(float(data["format"]["duration"]) - evidence["final_duration"]) <= 1 / FPS + .005,
            "Rendered animation length differs from frame-padded narration and standard ident")
    result = {}
    for sound, name in (("soundtrack.m4a", "video.mp4"), ("dry-soundtrack.m4a", "narration-only.mp4")):
        run("ffmpeg", "-v", "error", "-n", "-i", animation, "-i", root / sound, "-map", "0:v:0",
            "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", folder / name)
        require(stream_audio_hash(folder / name) == stream_audio_hash(root / sound),
                "Delivered AAC packets differ from the common soundtrack")
        delivery = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
            str(folder / name)], text=True))
        delivered_video = next(s for s in delivery["streams"] if s["codec_type"] == "video")
        delivered_audio = next(s for s in delivery["streams"] if s["codec_type"] == "audio")
        gap = abs(float(delivered_video["duration"]) - float(delivered_audio["duration"]))
        require(gap < .1, "Delivery audio/video duration gap exceeds tolerance")
        require(abs(float(delivery["format"]["duration"]) - evidence["final_duration"]) < .1,
                "Delivery is truncated or unexpectedly padded")
        run("ffmpeg", "-v", "error", "-i", folder / name, "-f", "null", "-")
        result[name] = {"sha256": sha(folder / name), "decode": "PASS",
                        "video_duration": float(delivered_video["duration"]),
                        "audio_duration": float(delivered_audio["duration"]),
                        "audio_video_duration_gap": gap,
                        "common_audio_packet_hash": stream_audio_hash(root / sound),
                        "soundtrack_stream_copy": True}
    write_new(folder / "technical.json", {"format": fmt, "outputs": result,
              "width": expected_size[0], "height": expected_size[1], "duration": evidence["final_duration"],
              "narration_source_unchanged": True, "listening_av": "PENDING", "publication_approved": False})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("score", "mux"))
    parser.add_argument("root", type=Path)
    parser.add_argument("format", nargs="?", choices=("landscape", "shorts", "clean-shorts"))
    args = parser.parse_args()
    require(args.action == "score" or args.format is not None, "mux needs a format")
    print(json.dumps(finish(args.root) if args.action == "score" else mux(args.root, args.format), indent=2))
