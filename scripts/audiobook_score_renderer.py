#!/usr/bin/env python3
"""Private, deterministic rendering of an already validated audiobook score plan.

The planner owns interpretation, measured cue evidence and commercial rights.
This module rechecks media bindings and performs signal processing only. Its
report is technical evidence, never editorial approval or a release receipt.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


SAMPLE_RATE = 48_000
SCHEMA = "earnalism.audiobook_score.plan.v1"
DURATION_TOLERANCE_MS = 80
# A checksum-bound local playlist must never turn a private render into remote
# I/O. Permit physical audio containers and local file/pipe protocols only.
INPUT_OPTIONS = [
    "-protocol_whitelist", "file,pipe",
    "-format_whitelist", "wav,mp3,flac,mov,ogg,aac,matroska",
]


class ScoreRenderError(ValueError):
    """The plan or media cannot be rendered safely and truthfully."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreRenderError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ScoreRenderError(f"{name} must be finite and between {low} and {high}")
    return value


def _ms(value: Any, name: str, low: int = 0, high: int = 604_800_000) -> int:
    _number(value, name, low, high)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ScoreRenderError(f"{name} must be integer milliseconds")
    return value


def _run(command: list[str], *, timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScoreRenderError(f"Media command failed: {type(exc).__name__}") from exc
    if result.returncode:
        raise ScoreRenderError(f"Media command failed: {result.stderr[-2500:]}")
    return result


def _graph_file_option(help_text: str) -> str:
    """Select a file-backed graph option from the installed FFmpeg's help.

    FFmpeg 6.1 supports the legacy option; newer releases removed it in favor
    of the generic slash-prefixed file-option syntax.
    """
    if re.search(r"(?:^|\s)-filter_complex_script(?:\s|$)", help_text):
        return "-filter_complex_script"
    return "-/filter_complex"


@lru_cache(maxsize=8)
def _ffmpeg_graph_file_option(executable: str) -> str:
    result = _run([executable, "-hide_banner", "-h", "full"], timeout=15)
    return _graph_file_option(result.stdout + "\n" + result.stderr)


def _probe(path: Path, ffprobe: str) -> float:
    result = _run([
        ffprobe, "-v", "error", *INPUT_OPTIONS, "-select_streams", "a:0", "-show_entries",
        "stream=codec_type,duration:format=duration", "-of", "json", str(path),
    ])
    try:
        payload = json.loads(result.stdout)
        streams = payload["streams"]
        if len(streams) != 1 or streams[0].get("codec_type") != "audio":
            raise ValueError("missing audio")
        value = streams[0].get("duration", payload.get("format", {}).get("duration"))
        seconds = float(value)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("invalid duration")
        return seconds * 1000
    except (KeyError, TypeError, ValueError) as exc:
        raise ScoreRenderError(f"Cannot measure audio duration: {path.name}") from exc


def _media(record: dict, name: str, ffprobe: str) -> tuple[Path, float]:
    if not isinstance(record, dict):
        raise ScoreRenderError(f"{name} must be a media object")
    supplied = record.get("path")
    if not isinstance(supplied, str) or not Path(supplied).is_absolute():
        raise ScoreRenderError(f"{name}.path must be absolute")
    try:
        path = Path(supplied).resolve(strict=True)
    except OSError as exc:
        raise ScoreRenderError(f"{name} media is missing") from exc
    if not path.is_file():
        raise ScoreRenderError(f"{name} must reference a regular file")
    expected = record.get("sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ScoreRenderError(f"{name} requires SHA-256")
    if _sha256(path) != expected:
        raise ScoreRenderError(f"{name} checksum mismatch")
    declared = _ms(record.get("duration_ms"), f"{name}.duration_ms", 1)
    actual = _probe(path, ffprobe)
    if abs(actual - declared) > DURATION_TOLERANCE_MS:
        raise ScoreRenderError(f"{name} measured duration differs from its plan")
    return path, actual


def _loudness(path: Path, ffmpeg: str, policy: dict, *, filters: str = "", timeout: float = 60) -> dict:
    loudnorm = (
        f"loudnorm=I={policy['target_lufs']}:TP={policy['max_true_peak_dbfs']}:"
        "LRA=11:print_format=json"
    )
    result = _run([
        ffmpeg, "-hide_banner", "-nostdin", *INPUT_OPTIONS, "-i", str(path), "-map", "0:a:0",
        "-af", f"{filters},{loudnorm}" if filters else loudnorm,
        "-f", "null", "-",
    ], timeout=timeout)
    matches = re.findall(r"\{\s*\"input_i\".*?\}", result.stderr, flags=re.DOTALL)
    if not matches:
        raise ScoreRenderError("FFmpeg did not return measured loudness")
    try:
        data = json.loads(matches[-1])
        fields = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
        measured = {key: float(data[key]) for key in fields}
        if not all(math.isfinite(value) for value in measured.values()):
            raise ValueError("nonfinite loudness")
        return measured
    except (KeyError, TypeError, ValueError) as exc:
        raise ScoreRenderError("Silent or nonfinite audio cannot be loudness normalized") from exc


def _policy(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ScoreRenderError("A mixing policy is required")
    bounds = {
        "music_lufs": (-60, -20), "target_lufs": (-30, -10),
        "max_true_peak_dbfs": (-9, -0.1), "duck_threshold_db": (-60, -6),
        "duck_ratio": (1, 20), "duck_attack_ms": (0.1, 2000),
        "duck_release_ms": (10, 9000),
    }
    policy = {key: _number(raw.get(key), f"policy.{key}", *limits) for key, limits in bounds.items()}
    if policy["music_lufs"] > policy["target_lufs"] - 10:
        raise ScoreRenderError("Music reference must be at least 10 LU below the voice target")
    return policy


def render_score(plan: dict, output_dir: Path, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> dict:
    """Render private WAV stems and a measured report without modifying inputs.

    Loop offsets are relative to the approved loop interval; nonloop offsets
    are relative to the complete asset. Placement fades and overlaps are used
    exactly as planned. No timing estimation, semantic inference or release
    approval takes place here. Existing output directories are refused.
    """
    output_dir = Path(output_dir).absolute()
    if output_dir.exists() or output_dir.is_symlink():
        raise ScoreRenderError("Output already exists; refusing to overwrite")
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ScoreRenderError("Unsupported score plan schema")
    if plan.get("release_approved") is not False or not isinstance(plan.get("fixture_mode"), bool):
        raise ScoreRenderError("Only explicitly private score plans can be rendered")
    ffmpeg_path, ffprobe_path = shutil.which(ffmpeg), shutil.which(ffprobe)
    if not ffmpeg_path or not ffprobe_path:
        raise ScoreRenderError("ffmpeg and ffprobe must both be installed")
    policy = _policy(plan.get("policy"))
    narration, measured_duration = _media(plan.get("narration"), "narration", ffprobe_path)
    declared_duration = plan["narration"]["duration_ms"]
    # Preserve a measured tail if the millisecond-rounded plan is slightly short.
    duration_ms = max(declared_duration, math.ceil(measured_duration))
    sample_count = duration_ms * 48
    timeout = max(60, min(1800, duration_ms / 1000 * 6 + 30))

    raw_assets, placements = plan.get("assets"), plan.get("placements")
    if not isinstance(raw_assets, list) or not isinstance(placements, list):
        raise ScoreRenderError("assets and placements must be arrays")
    if len(raw_assets) > 256 or len(placements) > 4096:
        raise ScoreRenderError("Score exceeds the bounded renderer capacity")
    assets: dict[str, dict] = {}
    for index, item in enumerate(raw_assets):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ScoreRenderError("Every asset requires an ID")
        if item["id"] in assets:
            raise ScoreRenderError("Duplicate asset ID")
        path, actual = _media(item, f"asset {index}", ffprobe_path)
        loop = item.get("loop")
        if loop is not None:
            if not isinstance(loop, dict):
                raise ScoreRenderError("An asset loop must be an interval")
            lo = _ms(loop.get("start_ms"), "loop.start_ms")
            hi = _ms(loop.get("end_ms"), "loop.end_ms", 1)
            if hi <= lo or hi > min(item["duration_ms"], actual) + 0.5:
                raise ScoreRenderError("Asset loop is outside the measured media")
        assets[item["id"]] = {"record": item, "path": path, "actual_ms": actual, "uses": []}

    checked_placements = []
    for index, placement in enumerate(placements):
        if not isinstance(placement, dict) or placement.get("asset_id") not in assets:
            raise ScoreRenderError("Placement references an unknown asset")
        start = _ms(placement.get("start_ms"), "placement.start_ms")
        end = _ms(placement.get("end_ms"), "placement.end_ms", 1)
        offset = _ms(placement.get("source_offset_ms"), "placement.source_offset_ms")
        fade_in = _ms(placement.get("fade_in_ms"), "placement.fade_in_ms")
        fade_out = _ms(placement.get("fade_out_ms"), "placement.fade_out_ms")
        gain = _number(placement.get("gain_db"), "placement.gain_db", -6, 0)
        if end <= start or end > declared_duration or fade_in > end - start or fade_out > end - start:
            raise ScoreRenderError("Placement timing or fade is outside the narration")
        if not isinstance(placement.get("anchor_cue_id"), str) or not placement["anchor_cue_id"]:
            raise ScoreRenderError("Placement requires its measured cue anchor")
        asset = assets[placement["asset_id"]]
        loop = asset["record"].get("loop")
        if loop:
            if offset >= loop["end_ms"] - loop["start_ms"]:
                raise ScoreRenderError("Placement offset is outside its authorized loop")
        elif offset + end - start > min(asset["record"]["duration_ms"], asset["actual_ms"]) + 0.5:
            raise ScoreRenderError("Nonloop asset is too short for the placement")
        item = {**placement, "gain_db": gain, "index": index}
        asset["uses"].append(item)
        checked_placements.append(item)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.render-", dir=output_dir.parent))
    try:
        measurement_layout = f"aresample={SAMPLE_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo"
        narration_measurements = _loudness(
            narration, ffmpeg_path, policy, filters=measurement_layout, timeout=timeout,
        )
        desired_voice_gain = policy["target_lufs"] - narration_measurements["input_i"]
        voice_peak_headroom = policy["max_true_peak_dbfs"] - narration_measurements["input_tp"]
        voice_gain = min(desired_voice_gain, voice_peak_headroom)
        if voice_gain > 24:
            raise ScoreRenderError("Narration normalization would require an excessive boost above 24 dB")
        voice_reference_lufs = narration_measurements["input_i"] + voice_gain
        if voice_reference_lufs < policy["target_lufs"] - 3:
            raise ScoreRenderError("Narration crest factor prevents a safe voice reference level")
        measurements = {}
        used_assets = [(key, value) for key, value in assets.items() if value["uses"]]
        input_args = [*INPUT_OPTIONS, "-i", str(narration)]
        graph = [
            f"[0:a:0]aresample={SAMPLE_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=whole_len={sample_count},atrim=end_sample={sample_count},asetpts=N/SR/TB,"
            f"volume={voice_gain}dB,asplit=2[voice][sideinput]",
            # Keep sidechain EOF later than the finite music bed. Otherwise
            # framesync can stop music early when another sink drains voice.
            f"[sideinput]apad=whole_len={sample_count + SAMPLE_RATE}[side]",
            f"anullsrc=r={SAMPLE_RATE}:cl=stereo,atrim=end_sample={sample_count}[silence]",
        ]
        music_labels = ["[silence]"]
        for input_index, (asset_id, asset) in enumerate(used_assets, 1):
            input_args += [*INPUT_OPTIONS, "-i", str(asset["path"])]
            loop = asset["record"].get("loop")
            measurement_filters = (
                f"atrim=start={loop['start_ms']/1000}:end={loop['end_ms']/1000},asetpts=N/SR/TB,"
                if loop else ""
            ) + measurement_layout
            measured = _loudness(asset["path"], ffmpeg_path, policy, filters=measurement_filters, timeout=timeout)
            normalization_gain = policy["music_lufs"] - measured["input_i"]
            if normalization_gain > 24:
                raise ScoreRenderError("Asset normalization would require an excessive boost")
            measurements[asset_id] = {**measured, "normalization_gain_db": normalization_gain}
            labels = "".join(f"[src{item['index']}]" for item in asset["uses"])
            graph.append(
                f"[{input_index}:a:0]aresample={SAMPLE_RATE},"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo,asplit={len(asset['uses'])}{labels}"
            )
            for item in asset["uses"]:
                index = item["index"]
                length = (item["end_ms"] - item["start_ms"]) * 48
                offset = item["source_offset_ms"] * 48
                filters = []
                if loop:
                    loop_start, loop_end = loop["start_ms"] * 48, loop["end_ms"] * 48
                    filters += [
                        f"atrim=start_sample={loop_start}:end_sample={loop_end}",
                        "asetpts=N/SR/TB", f"aloop=loop=-1:size={loop_end-loop_start}:start=0",
                    ]
                filters += [
                    f"atrim=start_sample={offset}:end_sample={offset+length}", "asetpts=N/SR/TB",
                    f"volume={normalization_gain + item['gain_db']}dB",
                ]
                if item["fade_in_ms"]:
                    filters.append(f"afade=t=in:ss=0:ns={item['fade_in_ms']*48}:curve=qsin")
                if item["fade_out_ms"]:
                    fade = item["fade_out_ms"] * 48
                    filters.append(f"afade=t=out:ss={length-fade}:ns={fade}:curve=qsin")
                filters.append(f"adelay={item['start_ms']*48}S:all=1")
                graph.append(f"[src{index}]" + ",".join(filters) + f"[cue{index}]")
                music_labels.append(f"[cue{index}]")
        threshold = 10 ** (policy["duck_threshold_db"] / 20)
        graph += [
            "".join(music_labels) + f"amix=inputs={len(music_labels)}:normalize=0:duration=first[bed]",
            f"[bed][side]sidechaincompress=threshold={threshold}:ratio={policy['duck_ratio']}:"
            f"attack={policy['duck_attack_ms']}:release={policy['duck_release_ms']}:makeup=1,"
            "asplit=2[ducked][mixmusic]",
            "[voice][mixmusic]amix=inputs=2:normalize=0:duration=first[rawmix]",
        ]
        graph_path = stage / "render.filters"
        graph_path.write_text(";\n".join(graph), encoding="utf-8")
        music_path, raw_path, final_path = stage / "music_stem.wav", stage / "raw_mix.wav", stage / "final_mix.wav"
        _run([
            ffmpeg_path, "-hide_banner", "-nostdin", "-n", *input_args,
            _ffmpeg_graph_file_option(ffmpeg_path), str(graph_path), "-map", "[ducked]", "-c:a", "pcm_f32le",
            "-ar", str(SAMPLE_RATE), "-rf64", "auto", str(music_path), "-map", "[rawmix]", "-c:a", "pcm_f32le",
            "-ar", str(SAMPLE_RATE), "-rf64", "auto", str(raw_path),
        ], timeout=timeout)
        initial = _loudness(raw_path, ffmpeg_path, policy, timeout=timeout)
        normalizer = (
            f"loudnorm=I={policy['target_lufs']}:TP={policy['max_true_peak_dbfs']}:LRA=11:"
            f"measured_I={initial['input_i']}:measured_TP={initial['input_tp']}:"
            f"measured_LRA={initial['input_lra']}:measured_thresh={initial['input_thresh']}:"
            f"offset={initial['target_offset']}:linear=true"
        )
        _run([
            ffmpeg_path, "-hide_banner", "-nostdin", "-n", *INPUT_OPTIONS, "-i", str(raw_path), "-map", "0:a:0",
            "-af", normalizer, "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s24le", "-rf64", "auto", str(final_path),
        ], timeout=timeout)
        final_measurements = _loudness(final_path, ffmpeg_path, policy, timeout=timeout)
        final_duration = _probe(final_path, ffprobe_path)
        music_duration = _probe(music_path, ffprobe_path)
        if abs(final_duration - duration_ms) > DURATION_TOLERANCE_MS or abs(music_duration - duration_ms) > DURATION_TOLERANCE_MS:
            raise ScoreRenderError("Rendered duration does not preserve the narration timeline")
        if final_measurements["input_tp"] > policy["max_true_peak_dbfs"] + 0.1:
            raise ScoreRenderError("Final measured true peak exceeds its ceiling")
        if abs(final_measurements["input_i"] - policy["target_lufs"]) > 1:
            raise ScoreRenderError("Final measured loudness misses the configured target")
        # Detect source changes during rendering; do not retain a misleading report.
        for name, record in [("narration", plan["narration"]), *[(key, value["record"]) for key, value in assets.items()]]:
            if _sha256(Path(record["path"])) != record["sha256"]:
                raise ScoreRenderError(f"{name} changed during rendering")
        effective_plan_path = stage / "effective-plan.json"
        effective_plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        report = {
            "schema": "earnalism.audiobook_score.render.v1", "status": "PRIVATE_RENDERED",
            "fixture_mode": plan["fixture_mode"], "release_approved": False,
            "subjective_emotional_appropriateness": "UNPERFORMED",
            "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
            "dry_narration": dict(plan["narration"]),
            "dry_narration_measurements": narration_measurements,
            "voice_gain_db": voice_gain, "voice_reference_lufs": voice_reference_lufs,
            "measurement_channel_layout": "stereo at 48000 Hz, identical to the rendered voice and music paths",
            "tools": {
                "ffmpeg": _run([ffmpeg_path, "-version"], timeout=10).stdout.splitlines()[0],
                "ffprobe": _run([ffprobe_path, "-version"], timeout=10).stdout.splitlines()[0],
            },
            "source_assets": [{"id": item["id"], "sha256": item["sha256"]} for item in raw_assets],
            "policy": policy, "asset_loudness": measurements,
            "raw_mix_measurements": initial, "final_mix_measurements": final_measurements,
            "duration_ms": final_duration, "placement_count": len(checked_placements),
            "outputs": {
                "effective_plan": {"path": str(output_dir / effective_plan_path.name), "sha256": _sha256(effective_plan_path)},
                "music_stem": {"path": str(output_dir / music_path.name), "sha256": _sha256(music_path), "ducked": True, "duration_ms": music_duration},
                "final_mix": {"path": str(output_dir / final_path.name), "sha256": _sha256(final_path)},
            },
        }
        (stage / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raw_path.unlink()
        graph_path.unlink()
        if output_dir.exists() or output_dir.is_symlink():
            raise ScoreRenderError("Output appeared during rendering; refusing to overwrite")
        os.rename(stage, output_dir)
        return report
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
