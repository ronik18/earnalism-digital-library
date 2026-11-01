"""Derive private-provider narrator metadata for one genuinely adopted native package.

Called only inside proof-bound promotion. It never stages, uploads or publishes.
Historical profile metadata remains unchanged.
"""
from __future__ import annotations
import copy
import json
import native_scored_package as native

# Compact creator-requested attribution; full exact track/change credits remain
# in the unchanged accepted MP3 and protected metadata asset.
DISCLOSURE = 'AI voice: Cedar. Music: Heartwarming/Heartbreaking, Kevin MacLeod (https://incompetech.com), CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; edited.'


def metadata_for_package(package, descriptor_sha256, controlled_language):
    if package.get("release_evidence_version") != native.POLICY:
        return None
    native.require(package.get("schema_version") == "audiobook_package_manifest.v2"
        and isinstance(package.get("package_version"), str), "Finalized native package required before narrator metadata")
    path = native.REGISTRY.parent / "selfish-giant-cedar-20261102/release-descriptor.json"
    descriptor = json.loads(path.read_text())
    native.require(native.sha(native.canonical(descriptor)) == descriptor_sha256
        == package.get("release_descriptor_sha256"), "Native narrator metadata descriptor changed")
    native.validate(descriptor, package, controlled_language, native.legacy.DOWNSTREAM)
    audio = package["tracks"][0]["chunks"][0]["assets"]["audio"]
    native.require(audio["sha256"] == descriptor["master_mp3_sha256"], "Native narrator metadata audio changed")
    native.require(len(DISCLOSURE) <= 160, "Native attribution exceeds served disclosure limit")
    return {
        "audiobook_provider": "",  # Supported protected-package identity; provider stays internal.
        "audiobook_voice": "Cedar",
        "narration_disclosure": DISCLOSURE,
        "duration_ms": package["duration_ms"],
        "size_bytes": audio["size_bytes"],
    }


def apply_to_document(document, metadata):
    # The caller's atomic promotion already selected the exact approved package.
    document.update({key: metadata[key] for key in ("audiobook_provider", "audiobook_voice", "narration_disclosure")})
    nested = copy.deepcopy(document.get("audiobook")) if isinstance(document.get("audiobook"), dict) else {}
    nested.update(provider="", model="", voice=metadata["audiobook_voice"],
        narration_disclosure=metadata["narration_disclosure"], duration_ms=metadata["duration_ms"], size=metadata["size_bytes"])
    document["audiobook"] = nested
