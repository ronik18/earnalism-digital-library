#!/usr/bin/env python3
"""Offline proposal only. No downloads, provider calls, synthesis or approval writes."""
import argparse
import json
from pathlib import Path

ROSTER = Path(__file__).resolve().parents[1] / "references" / "voice-roster.json"

def _base_plan(title, language="en", theme="literary", presentation=None):
    roster = json.loads(ROSTER.read_text())
    if language.lower() not in {"en", "english"}:
        return {"status": "HOLD_LANGUAGE_QUALIFICATION", "language": language,
                "next_action": "Use the applicable language campaign and qualified voice evidence; no fallback TTS.",
                "generation_authorized": False, "network_requests": 0}
    if theme not in roster["theme_directions"]:
        raise ValueError("Unknown theme")
    # This roster is a nonauthoritative locator, never a title-name approval.
    # Current canonical evidence must confirm even a listed retained package.
    title_key = title.strip().lower()
    for profile in roster["profiles"]:
        bindings = profile.get("accepted_title_bindings", [])
        # Retain compatibility with older local rosters.
        if not bindings and profile.get("accepted_title"):
            bindings = [{"title": profile["accepted_title"],
                         "package": profile.get("accepted_package"),
                         "evidence_locator": profile.get("evidence_locator")}]
        binding = next((x for x in bindings if x["title"] == title_key), None)
        if binding:
            return {"status": "VERIFY_EXISTING_ACCEPTED_BINDING", "profile_id": profile["profile_id"],
                    "accepted_package": binding["package"],
                    "evidence_locator": binding.get("evidence_locator"),
                    "requested_direction_not_applied": True,
                    "next_action": "Match the actual edition/manuscript/package and current authority before reuse; title name alone is not sufficient. Preserve accepted audio; no new audition merely to resume it.",
                    "generation_authorized": False, "network_requests": 0}
    p = next(p for p in roster["profiles"] if p["gender_presentation"] == (presentation or "male"))
    return {"status": "DIRECTION_PROPOSAL_NOT_QUALIFIED", "title": title,
            "model_id": roster["model_id"], "model_revision": roster["model_revision"],
            "profile_id": p["profile_id"], "speaker": p["speaker"], "language": "English",
            "selection_basis": "Explicit presentation preference" if presentation else "Prepared English-native candidate; final choice requires actual applicable audition evidence",
            "native_language": p["native_language"], "qualification": p["status"],
            "supported_request_fields": {"speaker": p["speaker"], "language": "English",
                                         "instruct": p["base_direction"] + " " + roster["theme_directions"][theme]},
            "next_action": "First inspect current canonical title records and retained masters; this roster may be incomplete. If no applicable accepted audio exists, bind the edition and actual runtime/budget authority, resolve revisions and qualify representative passages before full generation.",
            "generation_authorized": False, "network_requests": 0}

def plan(title, language="en", theme="literary", presentation=None):
    result = _base_plan(title, language, theme, presentation)
    result["editorial_preflight"] = {
        "status": "NOT_ASSESSED_BY_THIS_TITLE_ONLY_PLANNER",
        "guide": str(ROSTER.parent / "voice-engineering.md"),
        "required_before_new_or_repaired_audio": [
            "Full-book interpretation and source-mapped TTS text, with layout wraps distinguished from structure",
            "Stable narrator reference and contextual phrase/scene direction using supported controls",
            "Consecutive-unit identity, grammatical pauses and complete narration listening",
            "Licensed content-led cue sheet and complete exact scored-mix owner review",
        ],
        "base_request_is_not_a_completed_performance_plan": True,
        "known_material_findings_override_historical_acceptance": True,
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--theme", choices=["literary", "suspense", "reflective", "adventure", "nonfiction", "poetry"], default="literary")
    parser.add_argument("--presentation", choices=["male", "female"])
    args = parser.parse_args()
    print(json.dumps(plan(args.title, args.language, args.theme, args.presentation), indent=2))
