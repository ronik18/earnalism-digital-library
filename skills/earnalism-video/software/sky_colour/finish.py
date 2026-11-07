"""Fresh-only private sky-colour score, fixed soundtrack and copied-audio mux.

An original sparse acoustic motif accompanies one Sun and two light paths. Acoustic one-shot performances are from the existing hash-pinned CC0
VCSL collection; no composition or timings are borrowed from earlier episodes.
Nothing here synthesizes or time/pitch-edits narration, grants listening approval,
or publishes. The original standard nonverbal ident is appended after body-only
mixing, with decoded sample equality checked before delivery encoding.
"""
from pathlib import Path
import argparse
import array
import hashlib
import json
import math
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
import acoustic_score
try:
    from ..thermal_touch.assemble import QualificationError, load, probe_wav, require, sha, write_new
except ImportError:
    from thermal_touch.assemble import QualificationError, load, probe_wav, require, sha, write_new

RATE = 48000
FPS = 30
IDENT_ROOT = BASE / "assets/standard-intro/v1"
IDENT_MANIFEST_SHA256 = "b1443346d98df717d7a399dd72c00a7d21347f4de1748c601c4093305672fa28"
# Episode-specific starting targets, not universal aesthetic/listening gates.
# loudnorm is used only to measure discarded output. The delivered score uses
# one constant gain, preserving the authored envelope instead of adapting after it.
SCORE_TARGET_LUFS = -30.0
SCORE_TRUE_PEAK_CEILING = -9.0
SCORE_ANALYSIS_FILTER = "loudnorm=I=-30:TP=-9:LRA=10:print_format=json"
MIX_FILTER = "[0:a]aformat=channel_layouts=stereo[v];[v][1:a]amix=inputs=2:normalize=0[a]"
SCORE_FILES = (
    ".sky-finish-lock.json", "score-plan.json", "score-piano.wav", "score-harp.wav",
    "score-unmastered.wav", "score.wav", "score.provenance.json", "mix.wav",
    "soundtrack.wav", "dry-soundtrack.wav", "soundtrack.m4a", "dry-soundtrack.m4a",
    "mix-provenance.json",
)
SCENE_KINDS = ('question','scattering','sky_path','prediction','sunset_path','callback')
REQUIRED_MARKS = {'question':('question','light'),'scattering':('mixed','redirect','shorter','red'),'sky_path':('away','toward','direct'),'prediction':('lower','longer','predict'),'sunset_path':('scatter','warm','identity','mixture'),'callback':('variation','sky','direct','callback')}


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def validate_timeline(timeline):
    seconds = timeline.get("duration")
    require(isinstance(seconds, (int, float)) and math.isfinite(seconds) and seconds > 0,
            "Invalid actual narration duration")
    scenes = timeline.get("scenes", [])
    require(tuple(s.get("scene") for s in scenes) == SCENE_KINDS,
            "Expected the current six sky-colour thoughts in order")
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
    q, scattering, sky, prediction, sunset, callback = scenes
    rests = [
      {'reason':'opening misconception','start':0.,'end':q['end']},
      {'reason':'viewer prediction','start':max(prediction['start'],mark(prediction,'predict')-.2),'end':prediction['end']},
      {'reason':'wavelength identity distinction','start':max(sunset['start'],mark(sunset,'identity')-.2),'end':sunset['end']},
      {'reason':'final two-path callback','start':max(callback['start'],mark(callback,'callback')-.2),'end':seconds}]
    intervals=[(r['start'],r['end']) for r in rests];events=[]
    def add(at,notes,instrument,velocity,duration,phrase):
      for i,note in enumerate(notes):
        ti=at+i*.17
        if ti<seconds-.7 and not any(a<=ti<=b for a,b in intervals):
          events.append({'time':ti,'midi':note,'instrument':instrument,'velocity':velocity*(1-i*.06),'duration':duration,'phrase':phrase,'pan':-.10 if instrument=='piano' else .10})
    # Literal rests alone reject attacks. The C2 rest envelope is applied once
    # during rendering; an early quiet attack must not discard its later decay.
    # Original sparse E/B/F-sharp/G-sharp motif: clear light, two paths, warm
    # return. Existing pinned CC0 acoustic performances; no trending composition.
    for scene,anchor in [(scattering,'mixed'),(sky,'away'),(prediction,'lower'),(sunset,'warm'),(callback,'sky')]:
      add(mark(scene,anchor)+.55,[52,59,66],'piano',.25,5.8,'E open ninth: one source, two paths')
    for scene,anchor in [(scattering,'redirect'),(sky,'toward'),(sunset,'scatter')]:
      for dt,note in zip((.65,2.8,5.2),(64,71,68)):
        if mark(scene,anchor)+dt<scene['end']-.5:
          add(mark(scene,anchor)+dt,[note],'harp',.23,3.8,'E B G sharp: scattered light and warm answer')
    return {'title':'One Sun, Two Paths','version':'sky-colour-original-v1','duration':seconds,
      'events':sorted(events,key=lambda e:e['time']),'rests':rests,'quiet_intervals':intervals,
      'fade_out_seconds':3.2,'fade_in_seconds':4.5,
      'composition':'Original restrained E B F sharp G sharp acoustic motif; no external composition',
      'timing_source':'New actual WAV lengths and actual-ASR semantic anchors, independent of generation-group boundaries',
      'listening':'PENDING','resemblance_review':'PENDING','publication_approved':False}


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
            "Original new narration source/evidence changed")
    audits=load(root / 'asr-review.json');groups=load(root / 'units.json')
    require(isinstance(audits,list) and len(audits)==len(groups)==4 and
            {a.get('unit') for a in audits}=={g['id'] for g in groups} and
            all(a.get('source_validation')=='PASS' and not a.get('differences') for a in audits), 'Unresolved/missing generation-group ASR finding')
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


def measure_score(path, constant_gain_db=None):
    """Read EBU R128 input measurements; discard all filter output."""
    prefix = (f'volume={constant_gain_db:.9f}dB:precision=double:eval=once,'
              if constant_gain_db is not None else '')
    analysis_filter = prefix + f'aresample={RATE},aformat=channel_layouts=stereo,' + SCORE_ANALYSIS_FILTER
    measured = subprocess.run([
        'ffmpeg', '-hide_banner', '-i', str(path), '-af', analysis_filter,
        '-f', 'null', '-'], capture_output=True, text=True, check=True)
    matches = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', measured.stderr)
    require(bool(matches), 'Missing score loudness measurements')
    values = json.loads(matches[-1])
    result = {name: float(values[name]) for name in ('input_i', 'input_tp', 'input_lra')}
    require(all(math.isfinite(value) for value in result.values()),
            'Score is silent or below measurable loudness; preserve it for review')
    return result


def choose_static_score_gain(measurement):
    require(all(name in measurement and math.isfinite(measurement[name])
                for name in ('input_i', 'input_tp')), 'Invalid score measurements')
    loudness_gain = SCORE_TARGET_LUFS - measurement['input_i']
    peak_gain = SCORE_TRUE_PEAK_CEILING - measurement['input_tp']
    return min(loudness_gain, peak_gain)


def verify_static_score_gain(source, output, gain_db):
    """Check every decoded sample against the declared constant multiplier.

    Resampling roundoff is allowed; a progressive/adaptive level ramp is not.
    This is not an audibility, musical quality or listener-acceptance verdict.
    """
    original, delivered = pcm(source), pcm(output)
    require(len(original) == len(delivered), 'Score mastering changed duration')
    multiplier = 10 ** (gain_db / 20)
    peak_error = max((abs(y - x * multiplier) for x, y in zip(original, delivered)), default=0.)
    expected_peak = max((abs(x * multiplier) for x in original), default=0.)
    require(peak_error <= max(1e-7, expected_peak * 2e-5),
            'Score mastering changed the authored envelope with nonconstant gain')
    return {'declared_gain_db': gain_db, 'decoded_sample_count_stereo': len(original),
            'peak_error': peak_error, 'expected_peak': expected_peak,
            'constant_gain_verified': True,
            'scope': 'Samplewise engineering check; listening remains pending'}


def master_score(source, output):
    """Apply a single measured peak-limited gain after the authored C2 curves."""
    source, output = Path(source), Path(output)
    require(not output.exists(), 'Preserve an existing/partial score master')
    before = measure_score(source)
    gain_db = choose_static_score_gain(before)
    # EBU's absolute gate can admit quiet tails after an overall lift. Resolve
    # that measurement change offline, with a bounded number of probes. The
    # delivered file still receives one scalar once, never time-varying gain.
    probes = []
    peak_limited = False
    for attempt in range(3):
        predicted = measure_score(source, gain_db)
        probes.append({'gain_db': gain_db, 'measurements': predicted})
        error = SCORE_TARGET_LUFS - predicted['input_i']
        peak_margin = SCORE_TRUE_PEAK_CEILING - predicted['input_tp']
        peak_limited = error > .08 and peak_margin <= .02
        if abs(error) <= .08 or peak_limited:
            break
        require(attempt < 2, 'Static score target did not converge within three offline probes')
        gain_db += min(error, peak_margin)
    audio_filter = f'volume={gain_db:.9f}dB:precision=double:eval=once'
    run('ffmpeg', '-v', 'error', '-n', '-i', source, '-af', audio_filter,
        '-ar', RATE, '-ac', '2', '-c:a', 'pcm_f32le', output)
    after = measure_score(output)
    require(after['input_tp'] <= SCORE_TRUE_PEAK_CEILING + .02,
            'Static score master exceeds its measured true-peak ceiling')
    require(abs(after['input_i'] - predicted['input_i']) <= .08,
            'Static score output differs from its measured offline prediction')
    require(abs(after['input_i'] - SCORE_TARGET_LUFS) <= .15 or
            peak_limited and after['input_i'] <= SCORE_TARGET_LUFS,
            'Static score output misses both loudness target and documented peak limitation')
    proof = verify_static_score_gain(source, output, gain_db)
    return {'method': 'MEASURED_SINGLE_CONSTANT_GAIN', 'gain_db': gain_db,
            'target_lufs': SCORE_TARGET_LUFS, 'true_peak_ceiling_db': SCORE_TRUE_PEAK_CEILING,
            'peak_limited': peak_limited, 'analysis_probes': probes,
            'analysis_only_filter': SCORE_ANALYSIS_FILTER, 'delivered_filter': audio_filter,
            'input_measurements': before, 'output_measurements': after,
            'authored_envelope_preserved': True, 'adaptive_gain': False,
            'constant_gain_verification': proof, 'listening': 'PENDING'}


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
    mastering = master_score(root / "score-unmastered.wav", root / "score.wav")
    return {"sample_collection": "VCSL", "license": "CC0-1.0", "revision": manifest["revision"],
            "third_party_samples": list(used.values()), "external_compositions": [],
            "asset_manifest_sha256": sha(asset_root / "manifest.json"),
            "license_sha256": sha(asset_root / "LICENSE"), "readme_sha256": sha(asset_root / "README.md"),
            "composer_sha256": sha(__file__), "sample_engine_sha256": sha(BASE / "acoustic_score.py"),
            "performance": "Computer-arranged acoustic one-shot notes; not a live human ensemble",
            "mastering": mastering, "recording_sha256": sha(root / "score.wav"),
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
    import re
    meters={}
    for name in ('soundtrack.m4a','dry-soundtrack.m4a'):
        check=subprocess.run(['ffmpeg','-hide_banner','-i',str(root/name),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
        values=json.loads(re.findall(r'\{[^{}]*\"input_i\"[^{}]*\}',check.stderr)[-1])
        meters[name]={k:values[k] for k in ('input_i','input_tp','input_lra')}
        require(float(values['input_tp'])<=-1.5,'Encoded mix lacks headroom; preserve output and adjust only in a fresh declared candidate')
    require(all(sha(root / name) == digest for name, digest in inputs.items()),
            "Accepted assembly/narration changed during finishing")
    write_new(root / "mix-provenance.json", {
        "state": "PRIVATE_NEW_SCORE_REQUIRES_LISTENING", "inputs": inputs,
        "narration_sha256": inputs["narration.wav"], "narration_source_unchanged": True,
        "pitch_or_tempo_changed": False, "pause_edits": False, "reactive_ducking": False,
        "body_mix_filter": MIX_FILTER, "normalization_scope": "One upstream assembly normalization. Finishing uses fixed equal-power mono-to-stereo routing identically in scored and dry outputs; no output normalization, pitch, tempo, pause, EQ or compression.",
        "body_duration": timeline["duration"], "body_frame_padding": padded_seconds - timeline["duration"],
        "final_duration": padded_seconds + 3, "ident_manifest": ident_manifest,
        "ident_manifest_sha256": sha(IDENT_ROOT / "manifest.json"), "ident_tail_checks": tails,
        "score_sha256": sha(root / "score.wav"), "measurements": evidence, "encoded_loudness_measurements":meters,
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
    outputs = (".sky-mux-lock.json", "video.mp4", "narration-only.mp4", "technical.json")
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
