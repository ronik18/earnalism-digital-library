#!/usr/bin/env python3
"""Render private, source-bound illustrated book films with local FFmpeg only.

This deliberately small composer uses authored per-format image/motion-clip
layouts and measured cue anchors. Camera movement is not character animation.
It never creates rights, subjective review, owner acceptance or publication.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import wave

try:
    from .audiobook_score import load_json, validate_input
except ImportError:
    from audiobook_score import load_json, validate_input


SCHEMA = "earnalism.book_av_render.v1"
REPORT_SCHEMA = "earnalism.book_av_render_report.v1"
PROTOCOLS = ["-protocol_whitelist", "file,pipe"]
MEDIA_FORMATS = "wav,mp3,flac,mov,matroska,png_pipe,jpeg_pipe,image2"


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _obj(value, required, optional=(), label="object"):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"Invalid {label} keys")
    return value


def _num(value, label, low, high, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not low <= value <= high
            or (integer and not isinstance(value, int))):
        raise ValueError(f"Invalid {label}")
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {label}")
    return value


def _items(value, label, low=1, high=512):
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise ValueError(f"Invalid {label} count")
    return value


def _ref(value, base, label, extra=()):
    _obj(value, ("path", "sha256", *extra), label=label)
    path = base / _text(value["path"], label + " path")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a physical local file")
    sha = value["sha256"]
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha) or digest(path) != sha:
        raise ValueError(f"{label} checksum mismatch")
    return {**value, "path": str(path.resolve())}


def _run(args, *, timeout=120, binary=False):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=not binary,
                            timeout=timeout, check=False)
    if result.returncode:
        detail = result.stderr.decode(errors="replace") if binary else result.stderr
        raise ValueError("FFmpeg/FFprobe failed: " + detail[-1800:])
    return result.stdout


def _probe(path):
    return json.loads(_run(["ffprobe", "-v", "error", *PROTOCOLS,
                           "-format_whitelist", MEDIA_FORMATS, "-show_streams",
                           "-show_format", "-of", "json", path]))


def _stream(probe, kind):
    streams = [s for s in probe["streams"] if s["codec_type"] == kind]
    if len(streams) != 1:
        raise ValueError(f"Exactly one {kind} stream required")
    return streams[0]


def _duration(probe, kind):
    stream = _stream(probe, kind)
    seconds = float(stream.get("duration", probe.get("format", {}).get("duration", "nan")))
    _num(seconds, kind + " duration", 0.001, 86400)
    return seconds * 1000


def _box(value, width, height, label):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"Invalid {label}")
    x, y, w, h = [_num(v, label, 0, 7680, True) for v in value]
    if w < 2 or h < 2 or x + w > width or y + h > height or w % 2 or h % 2:
        raise ValueError(f"{label} must fit the canvas with even dimensions")
    return x, y, w, h


def _overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def display_caption_text(text):
    """Collapse source whitespace for display without editing bound cue text."""
    return " ".join(_text(text, "caption text").split())


def validate(job_path):
    """Recheck local bytes and supported contracts; no subjective acceptance."""
    job_path = Path(job_path).resolve()
    base, raw = job_path.parent, load_json(job_path)
    _obj(raw, ("schema", "title", "territory", "manuscript", "narration", "scored_audio",
               "timing", "assets", "scenes", "branding", "outputs"),
         ("fixture_mode", "captions"), "render job")
    if raw["schema"] != SCHEMA or not isinstance(raw.get("fixture_mode", False), bool):
        raise ValueError("Unsupported schema or fixture mode")
    _text(raw["title"], "title")
    fixture = raw.get("fixture_mode", False)
    manuscript = _ref(raw["manuscript"], base, "manuscript", ("language",))
    if manuscript["language"] not in {"bn", "en"}:
        raise ValueError("Supported languages are bn and en")
    narration = _ref(raw["narration"], base, "narration", ("duration_ms",))
    timing_ref = _ref(raw["timing"], base, "timing")
    audio = _ref(raw["scored_audio"], base, "scored_audio", ("duration_ms",))
    # PCM24 stereo WAV stays below RIFF's 4GiB ceiling. Longer works need
    # separately bound chapters; never silently truncate a full-title job.
    duration = _num(audio["duration_ms"], "body duration (maximum three hours)", 1, 10_800_000, True)
    if audio["duration_ms"] != narration["duration_ms"]:
        raise ValueError("Scored audio must retain the narration clock")
    # Reuse the established scorer's full source/Unicode coverage and timing
    # validation rather than introducing a permissive parallel cue parser.
    source = {"schema": "earnalism.audiobook_score.input.v1", "manuscript": manuscript,
              "narration": narration, "timing": timing_ref, "territory": raw["territory"],
              "assets": [], "fixture_mode": fixture}
    with tempfile.TemporaryDirectory(prefix="book-av-source-") as folder:
        source_path = Path(folder) / "source.json"
        source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        validate_input(source_path)
    if Path(audio["path"]).suffix.lower() not in {".wav", ".mp3", ".flac"}:
        raise ValueError("Scored audio must be WAV, MP3 or FLAC")
    if abs(_duration(_probe(audio["path"]), "audio") - duration) > 80:
        raise ValueError("Scored audio duration mismatch")
    timing = load_json(Path(timing_ref["path"]))
    cues = {c["id"]: c for c in timing["cues"]}
    assets = {}
    for asset in _items(raw["assets"], "assets"):
        _obj(asset, ("id", "kind", "path", "sha256", "rights"), label="visual asset")
        aid = _text(asset["id"], "asset id")
        if aid in assets or asset["kind"] not in {"image", "video"}:
            raise ValueError("Duplicate asset or unsupported visual kind")
        ref = _ref({k: asset[k] for k in ("path", "sha256")}, base, "visual asset")
        suffixes = {"image": {".png", ".jpg", ".jpeg"}, "video": {".mp4", ".mov", ".mkv"}}
        if Path(ref["path"]).suffix.lower() not in suffixes[asset["kind"]]:
            raise ValueError("Visual asset must be a physical image or motion clip")
        proof = _ref(asset["rights"], base, "visual rights")
        rights = load_json(Path(proof["path"]))
        if (rights.get("schema") != "earnalism.book_av_visual_rights.v1"
                or rights.get("asset_sha256") != ref["sha256"]
                or rights.get("scope") != "commercial_audiovisual"
                or rights.get("approval_status") != ("SYNTHETIC_FIXTURE" if fixture else "APPROVED")
                or not all(rights.get(k) is True for k in ("commercial_use", "distribution", "derivative_use"))
                or not isinstance(rights.get("territories"), list)
                or not all(isinstance(t, str) and re.fullmatch(r"[A-Z]{2}", t) for t in rights["territories"])
                or raw["territory"] not in rights["territories"]
                or not all(isinstance(rights.get(k), str) and rights[k].strip()
                           for k in ("rights_holder", "license_id", "attribution", "approval_ref"))):
            raise ValueError("Visual rights absent, stale or outside intended use")
        probe = _probe(ref["path"])
        stream = _stream(probe, "video")
        if stream["width"] > 7680 or stream["height"] > 7680:
            raise ValueError("Visual asset exceeds supported dimensions")
        assets[aid] = {**asset, **ref, "probe": probe, "rights": proof, "rights_record": rights}
    scenes, previous, seen = [], 0, set()
    for scene in _items(raw["scenes"], "scenes"):
        _obj(scene, ("id", "cue_id", "start_ms", "end_ms"), label="scene")
        sid = _text(scene["id"], "scene id")
        start = _num(scene["start_ms"], "scene start", 0, duration - 1, True)
        end = _num(scene["end_ms"], "scene end", start + 1, duration, True)
        if sid in seen or scene["cue_id"] not in cues or start != previous:
            raise ValueError("Scene IDs/anchors must cover the clock once in order")
        anchor = cues[scene["cue_id"]]["start_ms"]
        if start != anchor and not (start == 0 and scene is raw["scenes"][0]):
            raise ValueError("Scene must begin at its measured cue anchor")
        scenes.append(scene)
        seen.add(sid)
        previous = end
    if previous != duration:
        raise ValueError("Storyboard must cover the complete scored audio")
    brand = _ref(raw["branding"], base, "branding", ("approval_ref",))
    _text(brand["approval_ref"], "branding approval reference")
    if Path(brand["path"]).suffix.lower() != ".png":
        raise ValueError("Branding must be the approved transparent PNG")
    brand_stream = _stream(_probe(brand["path"]), "video")
    if brand_stream["width"] * brand_stream["height"] > 4_000_000:
        raise ValueError("Brand image too large")
    rgba = _run(["ffmpeg", "-v", "error", *PROTOCOLS, "-i", brand["path"],
                 "-frames:v", "1", "-pix_fmt", "rgba", "-f", "rawvideo", "pipe:1"], binary=True)
    alpha = rgba[3::4]
    if not alpha or min(alpha) == 255 or max(alpha) == 0:
        raise ValueError("Brand must contain visible artwork and actual transparency")
    outputs, names = [], set()
    for output in _items(raw["outputs"], "outputs", 1, 2):
        _obj(output, ("name", "width", "height", "fps", "scenes", "watermark", "end_clip"),
             ("canvas_color",), label="output")
        name = output["name"]
        if name not in {"landscape", "portrait"} or name in names:
            raise ValueError("Outputs must have unique landscape/portrait names")
        width = _num(output["width"], "width", 64, 3840, True)
        height = _num(output["height"], "height", 64, 3840, True)
        if width % 2 or height % 2 or (width > height) != (name == "landscape") or width == height:
            raise ValueError("Output dimensions must match the named composition")
        fps = output["fps"]
        if isinstance(fps, bool) or not isinstance(fps, int) or fps not in (24, 25, 30, 60):
            raise ValueError("Supported fps: 24, 25, 30, 60")
        canvas_color = output.get("canvas_color", "#071724")
        if not isinstance(canvas_color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", canvas_color):
            raise ValueError("canvas_color must be a #RRGGBB color")
        watermark = _obj(output["watermark"], ("box", "halo_px"), label="watermark")
        bx, by, bw, bh = _box(watermark["box"], width, height, "watermark box")
        halo = _num(watermark["halo_px"], "watermark halo", 2, 30, True)
        if bx - halo < 0 or by - halo < 0 or bx + bw + halo > width or by + bh + halo > height:
            raise ValueError("Complete watermark halo must fit the canvas")
        if abs(bw / bh - brand_stream["width"] / brand_stream["height"]) > 0.02:
            raise ValueError("Do not distort the full brand lockup")
        factor = min(width / (1920 if name == "landscape" else 1080),
                     height / (1080 if name == "landscape" else 1920))
        if bw < 180 * factor:
            raise ValueError("Complete brand lettering is below the established minimum size")
        if halo < math.ceil(3 * 0.45 * factor):
            raise ValueError("Watermark halo must contain the complete three-sigma blur")
        protected = (bx - halo, by - halo, bw + 2 * halo, bh + 2 * halo)
        layouts = _items(output["scenes"], "output scenes")
        if [s.get("scene_id") for s in layouts] != [s["id"] for s in scenes]:
            raise ValueError("Each format requires its complete ordered scene composition")
        for scene, layout in zip(scenes, layouts):
            _obj(layout, ("scene_id", "asset_id", "box", "zoom_start", "zoom_end", "source_offset_ms"), label="scene layout")
            box = _box(layout["box"], width, height, "artwork box")
            if _overlap(box, protected):
                raise ValueError("Artwork collides with reserved watermark halo")
            if layout["asset_id"] not in assets:
                raise ValueError("Unknown scene visual asset")
            asset = assets[layout["asset_id"]]
            for key in ("zoom_start", "zoom_end"):
                _num(layout[key], key, 1, 1.15)
            offset = _num(layout["source_offset_ms"], "source offset", 0, 86_400_000, True)
            frames = round(scene["end_ms"] * fps / 1000) - round(scene["start_ms"] * fps / 1000)
            if frames < 1:
                raise ValueError("Scene is shorter than one output frame")
            if asset["kind"] == "image" and offset:
                raise ValueError("Images do not have a temporal source offset")
            if asset["kind"] == "video":
                if layout["zoom_start"] != 1 or layout["zoom_end"] != 1:
                    raise ValueError("Motion clips retain their authored camera; zoom unsupported")
                if offset + frames * 1000 / fps > _duration(asset["probe"], "video") + 0.1:
                    raise ValueError("Motion clip has insufficient finite source capacity")
        end = _ref(output["end_clip"], base, "END clip", ("duration_ms", "approval_ref"))
        _text(end["approval_ref"], "END approval reference")
        ep = _probe(end["path"])
        ev = _stream(ep, "video")
        if (end["duration_ms"] != 3000 or abs(_duration(ep, "video") - 3000) > 1
                or abs(_duration(ep, "audio") - 3000) > 1
                or ev["width"] != width or ev["height"] != height):
            raise ValueError("END must be the approved native-size three-second clip with sound")
        outputs.append({**output, "end_clip": end, "canvas_color": canvas_color})
        names.add(name)
    captions = raw.get("captions", False)
    if not isinstance(captions, bool):
        raise ValueError("captions must be boolean")
    if captions:
        for cue in cues.values():
            chars, seconds = len(display_caption_text(cue["text"])), (cue["end_ms"] - cue["start_ms"]) / 1000
            if seconds < 1 or chars > 72 or chars / seconds > 22:
                raise ValueError("Measured cues are too coarse/fast for readable caption sidecars")
    return {**raw, "job_path": str(job_path), "job_sha256": digest(job_path), "manuscript": manuscript,
            "narration": narration, "scored_audio": audio, "timing": timing_ref,
            "timing_data": timing, "assets_by_id": assets, "branding": brand, "outputs": outputs,
            "fixture_mode": fixture, "captions": captions}


def _ffmpeg_inputs(path, *, image=False):
    return [*PROTOCOLS, "-format_whitelist", MEDIA_FORMATS,
            *(["-loop", "1"] if image else []), "-i", str(path)]


def _encode_video_args():
    return ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]


def _timestamp(ms, comma=False):
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}{',' if comma else '.'}{ms % 1000:03}"


def _decode_pcm(path, output):
    _run(["ffmpeg", "-v", "error", "-nostdin", "-n", *_ffmpeg_inputs(path),
          "-map", "0:a:0", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le",
          "-f", "s24le", output], timeout=1800)
    return Path(output).stat().st_size


def _decode_end_pcm(path, output):
    """Preserve the approved END's native 48k stereo presentation timeline.

    A raw PCM muxer concatenates decoded frames and discards timestamp gaps.
    Reconstruct those *existing* silent presentation intervals explicitly; do
    not move sound, stretch samples, trim frames or invent trailing padding.
    """
    output = Path(output)
    if output.exists():
        raise ValueError("END timeline output already exists")
    probe = json.loads(_run(["ffprobe", "-v", "error", *PROTOCOLS,
                            "-format_whitelist", MEDIA_FORMATS, "-select_streams", "a:0",
                            "-show_streams", "-show_frames", "-show_entries",
                            "stream=codec_type,sample_rate,channels,channel_layout,time_base,duration_ts:frame=pts,nb_samples",
                            "-of", "json", path]))
    stream = _stream(probe, "audio")
    if (stream.get("sample_rate") != "48000" or stream.get("channels") != 2
            or stream.get("channel_layout") != "stereo"):
        raise ValueError("END timeline reconstruction supports native 48k stereo only; no resampling")
    try:
        base = Fraction(stream["time_base"])
        duration = int(stream["duration_ts"]) * base * 48000
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("END requires exact stream time base and duration") from exc
    if duration.denominator != 1 or duration != 144000 or base <= 0:
        raise ValueError("END presentation timeline must be exactly three seconds")
    mapping, gaps, cursor, physical_frames = [], [], 0, 0
    frames = _items(probe.get("frames"), "END decoded audio frames", 1, 10000)
    for frame in frames:
        pts = frame.get("pts")
        count = frame.get("nb_samples")
        if (isinstance(pts, bool) or not isinstance(pts, int)
                or isinstance(count, bool) or not isinstance(count, int) or count <= 0):
            raise ValueError("END audio requires exact integer frame PTS and sample counts")
        start = pts * base * 48000
        if start.denominator != 1:
            raise ValueError("END PTS is not on the native 48k sample grid")
        start = int(start)
        if start < cursor or start + count > 144000:
            raise ValueError("END decoded frames overlap or exceed the approved timeline")
        if start > cursor:
            gaps.append({"start_frame": cursor, "end_frame": start})
        mapping.append({"start_frame": start, "frames": count})
        cursor = start + count
        physical_frames += count
    if cursor != 144000:
        raise ValueError("END final decoded frame must reach the exact timeline end; no invented tail")
    with tempfile.TemporaryDirectory(prefix=".end-timeline-", dir=output.parent) as temporary:
        physical = Path(temporary) / "physical.pcm"
        physical_size = _decode_pcm(path, physical)
        if physical_size != physical_frames * 6:
            raise ValueError("END decoded physical sample count differs from measured frame map")
        physical_sha = digest(physical)
        with physical.open("rb") as source, output.open("xb") as target:
            cursor = 0
            for frame in mapping:
                if frame["start_frame"] > cursor:
                    target.write(bytes((frame["start_frame"] - cursor) * 6))
                target.write(source.read(frame["frames"] * 6))
                cursor = frame["start_frame"] + frame["frames"]
            if source.read(1):
                raise ValueError("Unmapped END samples remain")
    return {"physical_frames": physical_frames, "playable_frames": 144000,
            "gap_frames": 144000 - physical_frames, "gaps": gaps,
            "decoded_frame_count": len(mapping), "physical_pcm_sha256": physical_sha,
            "timeline_pcm_sha256": digest(output),
            "frame_map_sha256": hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def _aac_payload(path):
    # ADTS carries the actual encoded AAC access units, independently of MP4
    # timestamps, filenames or metadata. No decoded-PCM/MP3 identity claim.
    payload = _run(["ffmpeg", "-v", "error", "-nostdin", *_ffmpeg_inputs(path),
                    "-map", "0:a:0", "-c:a", "copy", "-f", "adts", "pipe:1"],
                   timeout=1800, binary=True)
    return hashlib.sha256(payload).hexdigest()


def render(job_path, output_dir):
    job = validate(job_path)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise ValueError("Output directory already exists; preserve earlier candidates")
    # Generated/private media must stay outside every git worktree.
    if any((p / ".git").exists() for p in [output_dir, *output_dir.parents]):
        raise ValueError("Private media output must be outside git")
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs, caption_files = [], []
    try:
        with tempfile.TemporaryDirectory(prefix=".render-", dir=output_dir) as temporary:
            work = Path(temporary)
            source_pcm = work / "scored-source.pcm"
            source_size = _decode_pcm(job["scored_audio"]["path"], source_pcm)
            body_bytes = job["scored_audio"]["duration_ms"] * 48 * 6
            if source_size % 6 or abs(source_size - body_bytes) > 48 * 6:
                raise ValueError("Decoded scored audio differs from measured clock by more than 1ms")
            end_pcm = work / "END-source.pcm"
            end_timeline = _decode_end_pcm(job["outputs"][0]["end_clip"]["path"], end_pcm)
            end_size = end_pcm.stat().st_size
            end_digest = digest(end_pcm)
            for index, output in enumerate(job["outputs"][1:], 1):
                comparison = work / f"END-{index}.pcm"
                _decode_end_pcm(output["end_clip"]["path"], comparison)
                if digest(comparison) != end_digest:
                    raise ValueError("Per-format approved END clips have different soundtracks")
            master = output_dir / "soundtrack.wav"
            with wave.open(str(master), "wb") as target:
                target.setnchannels(2)
                target.setsampwidth(3)
                target.setframerate(48000)
                with source_pcm.open("rb") as source:
                    # Preserve every decoded score frame. Integer-ms measured
                    # cues may differ by <=1ms; that never permits a trim or pad.
                    for block in iter(lambda: source.read(1024 * 1024 // 6 * 6), b""):
                        target.writeframesraw(block)
                with end_pcm.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024 // 6 * 6), b""):
                        target.writeframesraw(block)
            soundtrack = {"path": str(master), "sha256": digest(master), "sample_rate": 48000,
                          "channels": 2, "sample_width_bytes": 3,
                          "scored_source_pcm_sha256": digest(source_pcm),
                          "end_source_pcm_sha256": end_digest,
                          "scored_source_frames": source_size // 6,
                          "body_frames": source_size // 6, "end_frames": end_size // 6,
                          "measured_body_frames": body_bytes // 6,
                          "source_vs_measured_clock_delta_ms": (source_size - body_bytes) / (48 * 6),
                          "decoded_scored_audio_preserved_complete": True,
                          "end_timeline": end_timeline,
                          "source_scored_audio_sha256": job["scored_audio"]["sha256"],
                          "end_clip_sha256": job["outputs"][0]["end_clip"]["sha256"]}
            encoded = output_dir / "soundtrack.m4a"
            _run(["ffmpeg", "-v", "error", "-nostdin", "-n", *_ffmpeg_inputs(master),
                  "-map", "0:a:0", "-c:a", "aac", "-b:a", "192k", encoded], timeout=1800)
            audio_payload = _aac_payload(encoded)
            encoded_soundtrack = {"path": str(encoded), "sha256": digest(encoded),
                                  "audio_payload_sha256": audio_payload}
            for output in job["outputs"]:
                name, width, height, fps = (output[k] for k in ("name", "width", "height", "fps"))
                canvas = "0x" + output["canvas_color"][1:]
                parts = []
                for index, (scene, layout) in enumerate(zip(job["scenes"], output["scenes"])):
                    asset = job["assets_by_id"][layout["asset_id"]]
                    x, y, w, h = layout["box"]
                    bx, by, bw, bh = output["watermark"]["box"]
                    halo = output["watermark"]["halo_px"]
                    count = round(scene["end_ms"] * fps / 1000) - round(scene["start_ms"] * fps / 1000)
                    z0, z1 = layout["zoom_start"], layout["zoom_end"]
                    art = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={canvas},setsar=1"
                    if asset["kind"] == "image":
                        art += f",zoompan=z='{z0}+({z1}-{z0})*on/{max(1,count-1)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps={fps}"
                    else:
                        art = f"trim=start={layout['source_offset_ms']/1000},setpts=PTS-STARTPTS,fps={fps}," + art
                    art += f",pad={width}:{height}:{x}:{y}:color={canvas}"
                    sigma = 0.45 * min(width / 1920, height / 1080) if name == "landscape" else 0.45 * min(width / 1080, height / 1920)
                    graph = (f"[0:v]{art}[art];[1:v]scale={bw}:{bh},format=rgba,"
                             f"pad={bw+2*halo}:{bh+2*halo}:{halo}:{halo}:color=0x00000000,"
                             f"gblur=sigma={max(.01,sigma)}[brand];[art][brand]overlay={bx-halo}:{by-halo}:eof_action=repeat,format=yuv420p[v]")
                    part = work / f"{name}-{index:04}.mp4"
                    _run(["ffmpeg", "-v", "error", "-nostdin", "-n", "-filter_complex_threads", "1",
                          *_ffmpeg_inputs(asset["path"], image=asset["kind"] == "image"),
                          *_ffmpeg_inputs(job["branding"]["path"], image=True), "-filter_complex", graph,
                          "-map", "[v]", "-frames:v", count, "-r", fps, *_encode_video_args(), part],
                         timeout=min(1800, max(120, count / fps * 20)))
                    parts.append(part)
                end_part = work / f"{name}-END.mp4"
                _run(["ffmpeg", "-v", "error", "-nostdin", "-n", *_ffmpeg_inputs(output["end_clip"]["path"]),
                      "-map", "0:v:0", "-vf", f"fps={fps},setsar=1", "-frames:v", fps * 3,
                      *_encode_video_args(), end_part])
                parts.append(end_part)
                listing = work / f"{name}-concat.txt"
                listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
                picture = work / f"{name}-picture.mp4"
                _run(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "concat", "-safe", "1", "-i", listing,
                      "-map", "0:v:0", "-c:v", "copy", picture], timeout=1800)
                final = output_dir / f"{name}.mp4"
                _run(["ffmpeg", "-v", "error", "-nostdin", "-n", *_ffmpeg_inputs(picture), *_ffmpeg_inputs(encoded),
                      "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
                      "-movflags", "+faststart", final], timeout=1800)
                probe = _probe(final)
                video, audio = _stream(probe, "video"), _stream(probe, "audio")
                expected = job["scored_audio"]["duration_ms"] + 3000
                if (video["codec_name"] != "h264" or audio["codec_name"] != "aac"
                        or abs(_duration(probe, "video") - expected) > 1000 / fps + 1
                        or abs(_duration(probe, "audio") - expected) > 2
                        or (video["width"], video["height"]) != (width, height)):
                    raise ValueError("Final streams do not match the authored delivery")
                _run(["ffmpeg", "-v", "error", "-nostdin", "-xerror", *_ffmpeg_inputs(final),
                      "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], timeout=1800)
                if _aac_payload(final) != audio_payload:
                    raise ValueError("Final video does not contain the shared encoded soundtrack")
                outputs.append({"name": name, "path": str(final), "sha256": digest(final),
                                "width": width, "height": height, "fps": fps,
                                "duration_ms": float(probe["format"]["duration"]) * 1000,
                                "video_codec": video["codec_name"], "audio_codec": audio["codec_name"],
                                "audio_payload_sha256": audio_payload,
                                "decode": "PASS", "end_clip_sha256": output["end_clip"]["sha256"],
                                "maximum_anchor_quantization_ms": 500 / fps})
            if job["captions"]:
                cues = job["timing_data"]["cues"]
                (output_dir / "captions.srt").write_text("\n\n".join(
                    f"{i+1}\n{_timestamp(c['start_ms'], True)} --> {_timestamp(c['end_ms'], True)}\n{html.escape(display_caption_text(c['text']), quote=False)}"
                    for i, c in enumerate(cues)) + "\n", encoding="utf-8")
                (output_dir / "captions.vtt").write_text("WEBVTT\n\n" + "\n\n".join(
                    f"{_timestamp(c['start_ms'])} --> {_timestamp(c['end_ms'])}\n{html.escape(display_caption_text(c['text']), quote=False)}"
                    for c in cues) + "\n", encoding="utf-8")
                caption_files = [{"format": suffix, "path": str(output_dir / f"captions.{suffix}"),
                                  "sha256": digest(output_dir / f"captions.{suffix}")} for suffix in ("srt", "vtt")]
        # Detect concurrent source changes rather than sealing stale provenance.
        current = validate(job_path)
        if current["job_sha256"] != job["job_sha256"]:
            raise ValueError("Render job changed during execution")
        report = {"schema": REPORT_SCHEMA, "state": "PRIVATE_TECHNICALLY_RENDERED",
                  "job_path": job["job_path"], "job_sha256": job["job_sha256"],
                  "scored_audio_sha256": job["scored_audio"]["sha256"],
                  "timing_sha256": job["timing"]["sha256"], "fixture_mode": job["fixture_mode"],
                  "outputs": outputs, "soundtrack": soundtrack,
                  "encoded_soundtrack": encoded_soundtrack, "release_approved": False,
                  "caption_files": caption_files,
                  "publication_approved": False, "full_listening_av_review": "UNPERFORMED",
                  "rights_acceptance": "SUPPLIED_ASSERTIONS_NOT_INDEPENDENT_LEGAL_REVIEW",
                  "motion_treatment": sorted({"illustration-camera-motion" if a["kind"] == "image"
                                              else "supplied-motion-clip-unassessed-character-naturalness"
                                              for a in job["assets_by_id"].values()}),
                  "source_visuals": [{"asset_id": aid, "kind": asset["kind"],
                                      "sha256": asset["sha256"],
                                      "width": _stream(asset["probe"], "video")["width"],
                                      "height": _stream(asset["probe"], "video")["height"]}
                                     for aid, asset in job["assets_by_id"].items()],
                  "captions": "MEASURED_TIMING_SIDECARS_NOT_BURNED_IN" if job["captions"] else "NOT_DELIVERED",
                  "limits": ["Hard scene cuts; no generated acting or model-weight training.",
                             "Maximum three-hour body per package; longer works require separately bound chapters.",
                             "Layout validates contained artwork boxes and brand halo, not perceptual image/text quality.",
                             "Every decoded scored-audio frame retained; its at-most-1ms difference from the integer-ms measured clock is recorded without trimming or padding.",
                             "END is transcoded at native picture size with its source sound; final AAC is re-encoded.",
                             "Native END audio frame PTS are retained; zeros represent only existing timestamp gaps, never relocated sound or invented trailing padding.",
                             "Caption sidecars require a verified delivery consumer; no native-platform acceptance is implied.",
                             "No primary editorial, listening, rights, owner or publication acceptance follows from decoding."],
                  "credits": [{"asset_id": aid, **asset["rights_record"]} for aid, asset in job["assets_by_id"].items()]}
        (output_dir / "render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    except Exception as exc:
        # Preserve partial candidates and honest failure evidence; never overwrite.
        (output_dir / "FAILED.json").write_text(json.dumps({"release_approved": False,
            "state": "FAILED_PRIVATE_RENDER", "error": str(exc), "job_sha256": job["job_sha256"]}, indent=2) + "\n")
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            job = validate(args.job)
            result = {"schema": REPORT_SCHEMA, "state": "PRIVATE_INPUTS_VALIDATED_NOT_RENDERED",
                      "job_sha256": job["job_sha256"], "release_approved": False}
        else:
            if args.output_dir is None:
                raise ValueError("--output-dir is required for rendering")
            result = render(args.job, args.output_dir)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"book AV render: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
