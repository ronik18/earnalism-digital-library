#!/usr/bin/env python3
"""Private, content-aware audiobook scoring; no inference, synthesis or publication calls.

Contextual interpretation is supplied by the approved director workflow. This module
binds it to measured narration, chooses licensed stems and plans absolute placements.
The renderer never guesses emotion or derives timing from a reading-speed estimate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

INPUT_SCHEMA = "earnalism.audiobook_score.input.v1"
TIMING_SCHEMA = "earnalism.audiobook_score.timing.v1"
DIRECTION_SCHEMA = "earnalism.audiobook_score.direction.v1"
PLAN_SCHEMA = "earnalism.audiobook_score.plan.v1"
EDIT_SCHEMA = "earnalism.audiobook_score.edit.v1"
EMOTIONS = {"joy", "amusement", "sadness", "anger", "fear", "calm", "neutral", "unknown"}
TONES = {"serious", "playful", "reflective", "tense", "neutral"}
ACTS = {"statement", "question", "exclamation", "command", "narration", "unknown"}
MOODS = {"joy", "amusement", "sadness", "serious", "tension", "calm", "reflective", "neutral"}
DEFAULT_POLICY = {
    "confidence_floor": 0.8, "min_dwell_ms": 6000, "crossfade_ms": 1200,
    "hard_turn_fade_ms": 240, "music_lufs": -34.0, "target_lufs": -18.0,
    "max_true_peak_dbfs": -1.5, "duck_threshold_db": -32.0,
    "duck_ratio": 6.0, "duck_attack_ms": 15.0, "duck_release_ms": 500.0,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    def invalid(value):
        raise ValueError(f"nonfinite JSON number: {value}")
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            return invalid(value)
        return result
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=invalid, parse_float=finite_float)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _object(data, required, optional=(), name="object"):
    if not isinstance(data, dict):
        raise ValueError(f"{name} must be an object")
    missing = set(required) - data.keys()
    unknown = data.keys() - set(required) - set(optional)
    if missing or unknown:
        raise ValueError(f"{name}: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _string(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _number(value, name, low, high, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not low <= value <= high
            or (integer and not isinstance(value, int))):
        raise ValueError(f"invalid {name}: expected {'integer' if integer else 'number'} in [{low}, {high}]")
    return value


def _enum(value, choices, name):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"invalid {name}: {value!r}")
    return value


def _digest(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"invalid {name}: expected SHA-256")
    return value


def _list(value, name, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{name} must be {'a nonempty' if nonempty else 'a'} list")
    return value


def _file_ref(ref, base, name, extra=()):
    _object(ref, ("path", "sha256", *extra), name=name)
    raw = _string(ref["path"], f"{name}.path")
    if "://" in raw or "\x00" in raw:
        raise ValueError(f"{name} must refer to a local retained file")
    path = (base / raw).resolve()
    expected = _digest(ref["sha256"], f"{name}.sha256")
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"{name} file missing or checksum mismatch: {path}")
    return {**ref, "path": str(path)}


def _policy(raw):
    _object(raw, (), DEFAULT_POLICY.keys(), name="policy")
    result = {**DEFAULT_POLICY, **raw}
    bounds = {
        "confidence_floor": (0.5, 1), "min_dwell_ms": (0, 60000),
        "crossfade_ms": (20, 5000), "hard_turn_fade_ms": (20, 500),
        "music_lufs": (-42, -28), "target_lufs": (-24, -16),
        "max_true_peak_dbfs": (-6, -1), "duck_threshold_db": (-48, -12),
        "duck_ratio": (2, 20), "duck_attack_ms": (1, 100),
        "duck_release_ms": (100, 2000),
    }
    for key, (low, high) in bounds.items():
        _number(result[key], f"policy.{key}", low, high, key.endswith("_ms") and key in {
            "min_dwell_ms", "crossfade_ms", "hard_turn_fade_ms"})
    if result["music_lufs"] > result["target_lufs"] - 10:
        raise ValueError("music must target at least 10 LU below the final mix")
    return result


def validate_input(path: Path) -> dict:
    """Verify immutable files, complete source coverage, timing and music rights.

    Evidence labels are retained assertions from the timing/rights workflow, not
    independent acoustic measurement or a legal certification by this parser.
    """
    path = path.resolve()
    base = path.parent
    raw = load_json(path)
    _object(raw, ("schema", "manuscript", "narration", "timing", "territory", "assets"),
            ("fixture_mode", "policy"), "score input")
    _enum(raw["schema"], {INPUT_SCHEMA}, "input schema")
    fixture = raw.get("fixture_mode", False)
    if not isinstance(fixture, bool):
        raise ValueError("fixture_mode must be boolean")
    territory = raw["territory"]
    if not isinstance(territory, str) or not re.fullmatch(r"[A-Z]{2}", territory):
        raise ValueError("territory must be an explicit two-letter country code")
    manuscript = _file_ref(raw["manuscript"], base, "manuscript", ("language",))
    _string(manuscript["language"], "manuscript.language")
    text = Path(manuscript["path"]).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("empty manuscript")
    narration = _file_ref(raw["narration"], base, "narration", ("duration_ms",))
    duration = _number(narration["duration_ms"], "narration.duration_ms", 1, 172800000, True)
    timing_ref = _file_ref(raw["timing"], base, "timing")
    timing = load_json(Path(timing_ref["path"]))
    _object(timing, ("schema", "manuscript_sha256", "narration_sha256", "duration_ms",
                     "method", "provenance", "cues"), name="timing")
    _enum(timing["schema"], {TIMING_SCHEMA}, "timing schema")
    methods = {"synthetic_fixture"} if fixture else {"measured_word_alignment", "human_verified_audio"}
    _enum(timing["method"], methods, "timing method")
    _number(timing["duration_ms"], "timing.duration_ms", 1, 172800000, True)
    if (timing["manuscript_sha256"] != manuscript["sha256"]
            or timing["narration_sha256"] != narration["sha256"]
            or timing["duration_ms"] != duration):
        raise ValueError("timing is stale or bound to a different candidate")
    _object(timing["provenance"], ("tool", "version", "boundary_validation"), name="timing provenance")
    for key, value in timing["provenance"].items():
        _string(value, f"timing provenance.{key}")
    _enum(timing["provenance"]["boundary_validation"],
          {"synthetic_fixture"} if fixture else {"accepted"}, "timing boundary validation")
    cues = _list(timing["cues"], "timing.cues")
    seen, previous_end, previous_text_end = set(), 0, 0
    for cue in cues:
        _object(cue, ("id", "start_ms", "end_ms", "text_start", "text_end", "text"), name="cue")
        cid = _string(cue["id"], "cue.id")
        if cid in seen:
            raise ValueError(f"duplicate cue id: {cid}")
        seen.add(cid)
        start = _number(cue["start_ms"], "cue.start_ms", previous_end, duration - 1, True)
        end = _number(cue["end_ms"], "cue.end_ms", start + 1, duration, True)
        ts = _number(cue["text_start"], "cue.text_start", previous_text_end, len(text) - 1, True)
        te = _number(cue["text_end"], "cue.text_end", ts + 1, len(text), True)
        if (text[previous_text_end:ts].strip() or cue["text"] != text[ts:te]
                or not isinstance(cue["text"], str) or not cue["text"].strip()):
            raise ValueError(f"cue {cid}: source mismatch, omission or reordered text")
        previous_end, previous_text_end = end, te
    if text[previous_text_end:].strip():
        raise ValueError("timing does not cover the complete manuscript")
    assets, asset_ids = [], set()
    for asset in _list(raw["assets"], "assets", False):
        _object(asset, ("id", "path", "sha256", "duration_ms", "moods", "energy",
                        "transition_group", "rights"),
                ("loop", "entry_offset_ms", "entry_fade_ms"), "asset")
        aid = _string(asset["id"], "asset.id")
        if aid in asset_ids:
            raise ValueError(f"duplicate asset id: {aid}")
        asset_ids.add(aid)
        media = _file_ref({k: asset[k] for k in ("path", "sha256", "duration_ms")},
                          base, f"asset {aid}", ("duration_ms",))
        _number(asset["duration_ms"], "asset.duration_ms", 1, 172800000, True)
        for mood in _list(asset["moods"], "asset.moods"):
            _enum(mood, MOODS, "asset mood")
        _number(asset["energy"], "asset.energy", 0, 1)
        _string(asset["transition_group"], "asset.transition_group")
        rights_ref = _file_ref(asset["rights"], base, f"asset {aid} rights")
        rights = load_json(Path(rights_ref["path"]))
        _object(rights, ("schema", "asset_sha256", "rights_holder", "license_id", "scope",
                         "territories", "commercial_use", "distribution", "derivative_mixing",
                         "instrumental", "approval_status", "approved_by", "approval_ref"), name="music rights")
        _enum(rights["schema"], {"earnalism.audiobook_music_rights.v1"}, "rights schema")
        for key in ("rights_holder", "license_id", "approved_by", "approval_ref"):
            _string(rights[key], f"rights.{key}")
        if (rights["asset_sha256"] != asset["sha256"] or rights["scope"] != "commercial_audiobook"
                or rights["approval_status"] != "APPROVED"
                or any(rights[k] is not True for k in ("commercial_use", "distribution", "derivative_mixing", "instrumental"))
                or territory not in _list(rights["territories"], "rights.territories")):
            raise ValueError(f"asset {aid}: missing candidate-bound instrumental/commercial/mixing/distribution rights")
        loop = asset.get("loop")
        if loop is not None:
            _object(loop, ("start_ms", "end_ms", "evidence"), name="asset loop")
            ls = _number(loop["start_ms"], "loop.start_ms", 0, asset["duration_ms"] - 1, True)
            le = _number(loop["end_ms"], "loop.end_ms", ls + 1, asset["duration_ms"], True)
            lr = _file_ref(loop["evidence"], base, "loop evidence")
            proof = load_json(Path(lr["path"]))
            _object(proof, ("schema", "asset_sha256", "start_ms", "end_ms", "seam_verified", "provenance"), name="loop evidence")
            if (proof["schema"] != "earnalism.audiobook_music_loop.v1"
                    or proof["asset_sha256"] != asset["sha256"]
                    or proof["start_ms"] != ls or proof["end_ms"] != le
                    or proof["seam_verified"] is not True):
                raise ValueError("loop evidence is stale or seam is unverified")
            _string(proof["provenance"], "loop evidence provenance")
            loop = {"start_ms": ls, "end_ms": le, "evidence": lr}
        # Offsets are measured within the physical file, or relative to the
        # beginning of an explicitly approved loop interval. They never grant
        # looping or an implicit restart when a finite source is exhausted.
        offset_limit = loop["end_ms"] - loop["start_ms"] if loop else asset["duration_ms"]
        _number(asset.get("entry_offset_ms", 0), "asset.entry_offset_ms", 0, offset_limit - 1, True)
        if "entry_fade_ms" in asset:
            _number(asset["entry_fade_ms"], "asset.entry_fade_ms", 20, 5000, True)
        assets.append({**asset, **media, "rights": rights_ref, "loop": loop})
    return {"path": str(path), "input_sha256": sha256_file(path), "fixture_mode": fixture,
            "territory": territory, "manuscript": manuscript, "text": text,
            "narration": narration, "timing": timing, "timing_ref": timing_ref,
            "assets": assets, "policy": _policy(raw.get("policy", {}))}


DIRECTOR_INSTRUCTIONS = """Interpret the complete work and its surrounding scene, not isolated keywords.
Return only JSON matching direction_template, with exactly one annotation per cue.
Preserve cue IDs, hashes and source text. Never estimate timestamps or change narration.
Distinguish expressed/quoted emotion, narrator attitude, and the scene's intended tone.
Handle negation, ironic laughter, sarcasm, rhetorical questions, and changes of speaker.
Emotion and speech act are independent: a question is not automatically suspenseful.
Keep music restrained under speech. Use score='silence' for intentional silence.
Set emotion='unknown' or uncertain=true when context/language/performance is ambiguous;
do not invent certainty. Confidence is an interpretation estimate, not a listening score.
Use transition='strong' for real abrupt pivots, 'gentle' for gradual change, else 'auto'.
Include the current and relevant surrounding cue IDs, and a concrete contextual rationale.
If no audio was assessed, explicitly state text-only interpretation in provenance; do not
claim acoustic emotion recognition, measured timing acceptance or release/listening PASS.
This packet authorizes no provider request, spending, rights approval or publication.
"""


def prepare_director(input_path: Path) -> dict:
    data = validate_input(input_path)
    return {"schema": "earnalism.audiobook_score.director_packet.v1",
            "instructions": DIRECTOR_INSTRUCTIONS,
            "complete_manuscript": data["text"], "language": data["manuscript"]["language"],
            "narration": data["narration"], "cues": data["timing"]["cues"],
            "vocabulary": {"emotion": sorted(EMOTIONS), "narrative_tone": sorted(TONES),
                           "speech_act": sorted(ACTS)},
            "direction_template": {"schema": DIRECTION_SCHEMA,
                "manuscript_sha256": data["manuscript"]["sha256"],
                "narration_sha256": data["narration"]["sha256"],
                "timing_sha256": data["timing_ref"]["sha256"],
                "provenance": {"method": "contextual_model", "agent_or_model": "REQUIRED",
                               "assessment_basis": "text_only", "version": "REQUIRED"},
                "annotations": [{"cue_id": cue["id"], "emotion": "unknown",
                    "narrative_tone": "neutral", "speech_act": "unknown", "intensity": 0,
                    "confidence": 0, "uncertain": True, "score": "silence",
                    "transition": "auto", "context_cue_ids": [cue["id"]],
                    "rationale": "REPLACE with contextual interpretation or explicit uncertainty"}
                    for cue in data["timing"]["cues"]]}}


def _direction(path: Path, data: dict) -> dict:
    raw = load_json(path)
    _object(raw, ("schema", "manuscript_sha256", "narration_sha256", "timing_sha256",
                  "provenance", "annotations"), name="direction")
    if (raw["schema"] != DIRECTION_SCHEMA
            or raw["manuscript_sha256"] != data["manuscript"]["sha256"]
            or raw["narration_sha256"] != data["narration"]["sha256"]
            or raw["timing_sha256"] != data["timing_ref"]["sha256"]):
        raise ValueError("direction schema/bindings differ from the measured candidate")
    _object(raw["provenance"], ("method", "agent_or_model", "assessment_basis", "version"), name="direction provenance")
    _enum(raw["provenance"]["method"], {"contextual_model", "editor"}, "direction method")
    _enum(raw["provenance"]["assessment_basis"], {"text_only", "text_and_audio"}, "assessment basis")
    for key in ("agent_or_model", "version"):
        value = _string(raw["provenance"][key], f"direction provenance.{key}")
        if value == "REQUIRED":
            raise ValueError("replace director template provenance before planning")
    cue_ids = {c["id"] for c in data["timing"]["cues"]}
    annotations = {}
    for item in _list(raw["annotations"], "annotations"):
        _object(item, ("cue_id", "emotion", "narrative_tone", "speech_act", "intensity",
                       "confidence", "uncertain", "score", "transition", "context_cue_ids", "rationale"), name="annotation")
        cid = item["cue_id"]
        _enum(cid, cue_ids, "annotation cue_id")
        if cid in annotations:
            raise ValueError(f"duplicate annotation: {cid}")
        for key, choices in (("emotion", EMOTIONS), ("narrative_tone", TONES), ("speech_act", ACTS),
                             ("score", {"music", "silence"}), ("transition", {"auto", "gentle", "strong"})):
            _enum(item[key], choices, key)
        for key in ("intensity", "confidence"):
            _number(item[key], key, 0, 1)
        if not isinstance(item["uncertain"], bool):
            raise ValueError("annotation.uncertain must be boolean")
        context = _list(item["context_cue_ids"], "context_cue_ids")
        if any(not isinstance(cid, str) for cid in context) or not set(context) <= cue_ids or cid not in context:
            raise ValueError("context must include current cue and reference existing cues")
        _string(item["rationale"], "rationale")
        if item["rationale"].startswith("REPLACE"):
            raise ValueError("replace director template rationale before planning")
        annotations[cid] = item
    if annotations.keys() != cue_ids:
        raise ValueError("direction must cover every cue exactly once")
    return {"annotations": annotations, "provenance": raw["provenance"], "sha256": sha256_file(path)}


def _mood(a):
    emotion, tone = a["emotion"], a["narrative_tone"]
    if tone == "serious" and emotion in {"joy", "amusement", "neutral", "calm"}:
        return "serious"
    if emotion in {"fear", "anger"} or tone == "tense":
        return "tension"
    if emotion == "neutral" and tone == "reflective":
        return "reflective"
    return emotion


def _hard_turn(old, new, annotation):
    return annotation["transition"] == "strong" or (
        old in {"joy", "amusement"} and new in {"sadness", "serious", "tension"}) or (
        new in {"joy", "amusement"} and old in {"sadness", "serious", "tension"}) or (
        new in {"sadness", "tension"} and old is not None and old != new) or (
        old in {"sadness", "tension"} and new == "serious")


def plan_score(input_path: Path, direction_path: Path) -> dict:
    data = validate_input(input_path)
    direction_path = direction_path.resolve()
    direction = _direction(direction_path, data)
    policy, duration, cues = data["policy"], data["narration"]["duration_ms"], data["timing"]["cues"]
    decisions, review, runs = [], [], []
    current, current_mood, changed_at = None, None, -policy["min_dwell_ms"]
    assets_by_id = {a["id"]: a for a in data["assets"]}
    for index, cue in enumerate(cues):
        a = direction["annotations"][cue["id"]]
        anchor = cue["start_ms"]
        next_anchor = cues[index + 1]["start_ms"] if index + 1 < len(cues) else duration
        mood, desired, issue = _mood(a), None, None
        hard = _hard_turn(current_mood, mood, a)
        if a["uncertain"] or a["emotion"] == "unknown" or a["confidence"] < policy["confidence_floor"]:
            issue = "UNCERTAIN_INTERPRETATION"
        elif a["score"] == "music":
            # Preserve source continuity while a stem has capacity. A short
            # scene need not provide a stem as long as the entire audiobook.
            def enough(x):
                origin = runs[-1]["start_ms"] if runs and x["id"] == current else anchor
                return (x["loop"] is not None
                        or x["duration_ms"] - x.get("entry_offset_ms", 0) >= next_anchor - origin)
            eligible = [x for x in data["assets"] if mood in x["moods"] and enough(x)]
            old_asset = assets_by_id.get(current)
            def rank(x):
                compatibility = 0 if old_asset and x["transition_group"] == old_asset["transition_group"] else 1
                return (0 if x["id"] == current else 1, compatibility,
                        abs(x["energy"] - a["intensity"]), x["id"])
            if eligible:
                desired = min(eligible, key=rank)["id"]
            else:
                issue = "NO_SUITABLE_LICENSED_STEM"
        if issue:
            review.append({"cue_id": cue["id"], "reason": issue,
                           "composition_brief": {"mood": mood, "energy": a["intensity"],
                            "speech_act": a["speech_act"], "instrumental_only": True,
                            "territory": data["territory"], "required_from_ms": anchor,
                            "required_until_ms": next_anchor, "context": a["rationale"]}})
        # Do not retain an old mood beneath uncertainty or an explicit silence.
        old_asset = assets_by_id.get(current)
        old_has_capacity = (old_asset is not None and (old_asset["loop"] is not None
                            or old_asset["duration_ms"] - old_asset.get("entry_offset_ms", 0)
                            >= next_anchor - runs[-1]["start_ms"]))
        dwell = (desired is not None and current is not None and desired != current
                 and old_has_capacity and not hard and anchor - changed_at < policy["min_dwell_ms"])
        if dwell:
            desired = current
        action = "SILENCE" if desired is None else ("KEEP" if desired == current else "CHANGE")
        decisions.append({"cue_id": cue["id"], "anchor_ms": anchor, "mood": mood,
                          "speech_act": a["speech_act"], "asset_id": desired,
                          "action": action, "dwell_suppressed": dwell, "hard_turn": hard,
                          "reason": issue or a["rationale"], "confidence": a["confidence"]})
        if not runs or desired != current:
            if runs:
                runs[-1]["end_ms"] = anchor
            runs.append({"asset_id": desired, "start_ms": anchor, "end_ms": duration,
                         "anchor_cue_id": cue["id"], "hard_turn": hard,
                         "gain_db": round(-4.0 * (1 - a["intensity"]), 3)})
            changed_at = anchor
        current = desired
        if not dwell:
            current_mood = mood
    placements = []
    # Absolute placement means overlaps never shorten or shift later cues.
    for i, run in enumerate(runs):
        if run["asset_id"] is None:
            continue
        asset = assets_by_id[run["asset_id"]]
        start, end = run["start_ms"], run["end_ms"]
        fade_in = min(policy["crossfade_ms"], (end - start) // 2)
        fade_out = min(policy["crossfade_ms"], (end - start) // 2)
        if i:
            previous = runs[i - 1]
            prev_asset = assets_by_id.get(previous["asset_id"])
            compatible = prev_asset and prev_asset["transition_group"] == asset["transition_group"]
            if not compatible:
                fade_in = min(fade_in, policy["hard_turn_fade_ms"])
            if run["hard_turn"]:
                fade_in = min(fade_in, policy["hard_turn_fade_ms"])
        if "entry_fade_ms" in asset:
            # A quiet first attack can enter gently even at an abrupt mood
            # change. The outgoing incompatible mood still ends at its anchor.
            fade_in = min(asset["entry_fade_ms"], (end - start) // 2)
        if i + 1 < len(runs):
            following = runs[i + 1]
            next_asset = assets_by_id.get(following["asset_id"])
            compatible = next_asset and next_asset["transition_group"] == asset["transition_group"]
            if compatible and not following["hard_turn"]:
                overlap = min(policy["crossfade_ms"], (end - start) // 2,
                              (following["end_ms"] - following["start_ms"]) // 2)
                # Nonloop asset capacity also constrains an overlapping tail.
                if asset["loop"] is None:
                    overlap = min(overlap, max(0, asset["duration_ms"]
                                              - asset.get("entry_offset_ms", 0) - (end - start)))
                if overlap:
                    end += overlap
                    fade_out = overlap
            else:
                # Incompatible keys and abrupt pivots fade through the anchor,
                # not a long cheerful tail beneath a serious revelation.
                fade_out = min(fade_out, policy["hard_turn_fade_ms"])
        placements.append({"asset_id": run["asset_id"], "start_ms": start, "end_ms": end,
                           "source_offset_ms": asset.get("entry_offset_ms", 0),
                           "fade_in_ms": fade_in, "fade_out_ms": fade_out,
                           "gain_db": run["gain_db"], "anchor_cue_id": run["anchor_cue_id"]})
    for previous, following in zip(placements, placements[1:]):
        overlap = previous["end_ms"] - following["start_ms"]
        if overlap > 0:
            following["fade_in_ms"] = overlap
    used = {p["asset_id"] for p in placements}
    return {"schema": PLAN_SCHEMA, "status": "PRIVATE_PLAN_WITH_UNRESOLVED_CUES" if review else "PRIVATE_PLAN",
            "release_approved": False, "fixture_mode": data["fixture_mode"],
            "input_sha256": data["input_sha256"], "manuscript": data["manuscript"],
            "narration": data["narration"], "timing": data["timing_ref"],
            "direction": {"path": str(direction_path), "sha256": direction["sha256"],
                          "provenance": direction["provenance"]},
            "territory": data["territory"], "policy": policy,
            "assets": [asset for asset in data["assets"] if asset["id"] in used],
            "placements": placements, "decisions": decisions, "review_items": review,
            "acceptance": {"emotional_appropriateness": "UNPERFORMED", "listening": "UNPERFORMED",
                           "release": "NOT_EVALUATED"}}


def apply_editorial_edits(input_path: Path, plan_path: Path, plan: dict, edit_path: Path) -> dict:
    """Bind explicit feedback placements to the validated baseline and sources.

    The renderer checks physical placement bounds, fades and finite capacity.
    Baseline interpretation is retained separately from the editor's decisions.
    """
    edit_path = edit_path.resolve()
    edit = load_json(edit_path)
    _object(edit, ("schema", "base_plan_sha256", "feedback", "placements"), name="editorial edit")
    _enum(edit["schema"], {EDIT_SCHEMA}, "edit schema")
    if _digest(edit["base_plan_sha256"], "base_plan_sha256") != sha256_file(plan_path):
        raise ValueError("editorial edit is bound to a different baseline plan")
    _string(edit["feedback"], "edit.feedback")
    data = validate_input(input_path)
    if data["input_sha256"] != plan["input_sha256"]:
        raise ValueError("candidate changed while preparing editorial edits")
    assets = {asset["id"]: asset for asset in data["assets"]}
    cues = {cue["id"] for cue in data["timing"]["cues"]}
    placements = _list(edit["placements"], "edit.placements", nonempty=False)
    for placement in placements:
        _object(placement, ("asset_id", "start_ms", "end_ms", "source_offset_ms",
                           "fade_in_ms", "fade_out_ms", "gain_db", "anchor_cue_id"), name="edited placement")
        _enum(placement["asset_id"], assets, "edited asset_id")
        _enum(placement["anchor_cue_id"], cues, "edited anchor_cue_id")
    used = {placement["asset_id"] for placement in placements}
    result = {**plan, "status": "PRIVATE_EDITORIAL_PLAN",
              "assets": [asset for asset in data["assets"] if asset["id"] in used],
              "placements": placements,
              "baseline_decisions": plan["decisions"],
              "review_items_scope": "Baseline interpretation; editorial placements do not certify resolution.",
              "editorial_override": {"feedback": edit["feedback"],
                  "base_plan_sha256": edit["base_plan_sha256"],
                  "edit": {"path": str(edit_path), "sha256": sha256_file(edit_path)}}}
    result.pop("decisions")
    return result


def _write_new(path: Path, data):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace a prior scored candidate or operator packet.
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare-director", "plan", "render"):
        p = sub.add_parser(command)
        p.add_argument("--input", required=True, type=Path)
        if command != "prepare-director":
            p.add_argument("--direction", required=True, type=Path)
        if command == "render":
            p.add_argument("--plan", required=True, type=Path)
            p.add_argument("--edits", type=Path, help="Explicit, baseline-bound editorial placements from feedback")
            p.add_argument("--output-dir", required=True, type=Path)
        else:
            p.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-director":
            _write_new(args.output, prepare_director(args.input))
        else:
            plan = plan_score(args.input, args.direction)
            if args.command == "plan":
                _write_new(args.output, plan)
            else:
                supplied = load_json(args.plan)
                if supplied != plan:
                    raise ValueError("plan changed or became stale; replan to a new file before rendering")
                if args.edits:
                    plan = apply_editorial_edits(args.input, args.plan, plan, args.edits)
                if __package__:
                    from .audiobook_score_renderer import render_score
                else:
                    from audiobook_score_renderer import render_score
                report = render_score(plan, args.output_dir)
                print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"audiobook score: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
