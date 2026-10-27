"""Read-only qualification of retained text editions, never publication approval.

This opt-in local adapter executes reuse checks instead of translating generator
READY labels into ingestion history. It does not persist workflow fields, read a
database, generate content, or grant activation. Final QA is deliberately not
inferred from the retained source/art preparation reviews.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from PIL import Image

from publication_manifest import validate_manifest
from rights_decision_gate import evaluate_accepted_record, load_production_registry


def _digest(data):
    return sha256(data).hexdigest()


def _path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("invalid artifact path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("artifact path escapes its root")
    return path


def _read(root, name):
    value = json.loads(_path(root, name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact must be an object")
    return value


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _normalized(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def validate_retained_edition(artifact_dir, *, repository_root, source_bytes, now=None, source_revision=None):
    """Return newly executed, edition-bound local findings without any writes.

    source_bytes must be the actual retained/retrieved source, not a claimed hash.
    Trust comes from the existing independent rights registry, never this caller.
    Outcomes are proposed local evaluator inputs, not persisted phase receipts.
    """
    root, repository = Path(artifact_dir).resolve(), Path(repository_root).resolve()
    clock = now or datetime.now(timezone.utc)
    result = {
        "schema": "earnalism.retained-edition-validation.v1",
        "scope": "LOCAL_REUSE_ONLY_INDIA_TEXT",
        "phase_4": "UNVERIFIED", "phase_5": "UNVERIFIED", "phase_6": "UNVERIFIED",
        "final_publication_qa": "UNVERIFIED", "ready_for_release": False,
        "production_observed": False, "mutations": [], "checks": {},
        "blockers": [], "evidence": {}, "observed_at": clock.isoformat(),
        "inspected_source_revision": source_revision or "UNVERIFIED",
    }
    try:
        _require(root.is_relative_to(repository), "edition directory outside repository")
        public = _read(root, "public_book.json")
        reader = _read(root, "reader_manifest.json")
        source = _read(root, "source_evidence.json")
        manifest = _read(root, "publication_manifest.json")
        authorization = _read(root, "publication_authorization.json")
        decision = _read(root, "rights_decision.json")
        approval = _read(root, "approval_evidence.json")
        derivation = _read(root, "cover_delivery_derivation.json")
        slug = public["slug"]
        result["slug"] = slug
        _require(all(item.get("slug") == slug for item in
                     (reader, source, manifest, authorization, derivation)), "edition slug mismatch")
        _require(all(public.get(key) and public[key] == reader.get(key)
                     for key in ("title", "author")), "Reader metadata mismatch")
        _require(reader.get("language") in ("en", "bn"), "Reader language missing")
        _require(not validate_manifest(manifest), "invalid publication manifest")
        result["evidence"]["publication_manifest_sha256"] = manifest["manifest_sha256"]
        assets = derivation["assets"]
        _require(isinstance(assets, list) and len(assets) == 2
                 and {asset["kind"] for asset in assets} == {"front", "back"}, "cover pair missing")
        _require({"public_book", "reader_manifest", "source_evidence", "approval_evidence",
                  "publication_manifest", "publication_authorization", "checksum_manifest",
                  "cover_delivery_derivation", "owner_artwork_declaration"}.issubset(decision["components"]),
                 "required rights components absent")
        components = {}
        for name in decision["components"]:
            if name in {"cover_front_asset", "cover_back_asset"}:
                path = _path(root, "covers/" + name.split("_")[1] + ".png")
            elif name in {"cover_front_delivery", "cover_back_delivery"}:
                asset = next(a for a in assets if a["kind"] == name.split("_")[1])
                path = _path(repository, asset["delivery_file"])
            elif name in {"acceptance_review_a", "acceptance_review_b"}:
                path = _path(root, "evidence/" + name.removeprefix("acceptance_") + ".json")
            else:
                path = _path(root, name + ".json")
            components[name] = _digest(path.read_bytes())
        accepted, revoked = load_production_registry()
        for use in ("reader_delivery", "reading_pass_session", "cover_display"):
            verdict = evaluate_accepted_record(
                decision, edition_id=slug, operator_id="reo-enterprise", country="IN",
                country_trusted=True, use=use, required_components=components,
                accepted_records=accepted, revoked_decision_ids=revoked,
                now=clock,
            )
            _require(verdict.passed, "rights " + use + ": " + ",".join(verdict.reasons))
        result["checks"]["india_rights"] = "PASS"
        _require(authorization.get("publication_authorized") is True
                 and authorization.get("audio_authorized") is False
                 and authorization.get("territories") == ["IN"]
                 and authorization.get("scope") == "TEXT_READER_CATALOG_METADATA_AND_EXACT_COVER_DISPLAY"
                 and authorization.get("rights_decision_id") == decision["decision_id"]
                 and authorization.get("edition") == source.get("source_name"), "authorization binding invalid")
        _require(isinstance(source_bytes, bytes) and bool(source_bytes), "actual source bytes required")
        source_hash = _digest(source_bytes)
        _require(source_hash == source["source_hash"] == manifest["content"]["source_hash"]
                 == authorization["source_sha256"], "exact source digest mismatch")
        _require(source["content_hash"] == manifest["content"]["content_hash"]
                 == authorization["content_sha256"], "content identity mismatch")
        proof = _read(root, "source_integrity_validation.json")
        reviews = {}
        for name in ("review_a", "review_b"):
            binding = approval["independent_reviews"][name]
            _require(_digest(_path(root, binding["file"]).read_bytes()) == binding["sha256"],
                     "independent review digest mismatch")
            reviews[name] = _read(root, binding["file"])
            _require(reviews[name].get("slug") == slug, "review edition mismatch")
        reviewed = reviews["review_a"]["source_proof_actual_reproduction"]
        _require(proof.get("slug") == slug and proof.get("source_sha256") == source_hash
                 and proof.get("source_hash_exact") is True
                 and proof.get("unclassified_narrative_gaps") == []
                 and reviewed["raw_sha256"] == source_hash
                 and reviewed.get("all_gaps_reproduced") is True, "complete source review missing")
        index = manifest["content"]["chapters"]
        _require(isinstance(index, list) and bool(index), "empty chapter index")
        identities = [(c["id"], c["order"], c["title"]) for c in index]
        _require(len({c[0] for c in identities}) == len(index)
                 and [c[1] for c in identities] == list(range(1, len(index) + 1))
                 and all(type(c[1]) is int for c in identities), "invalid chapter ordering")
        for item in (public, reader):
            _require([(c["id"], c["order"], c["title"]) for c in item["chapters"]] == identities,
                     "canonical chapter structure mismatch")
        _require(all(c.get("language_hint") == reader["language"] for c in reader["chapters"]),
                 "chapter language mismatch")
        _require(len(index) == proof["chapter_count"] == reader["chapter_count"]
                 == manifest["content"]["chapter_count"] == len(proof["matched_chapters"])
                 == len(reviewed["complete_ordered_bodies"]), "chapter count mismatch")
        text, cursor = _normalized(source_bytes.decode("utf-8-sig")), 0
        chapter_hashes = {}
        for entry, match, review in zip(index, proof["matched_chapters"], reviewed["complete_ordered_bodies"]):
            chapter_path = _path(root, "chapters/" + entry["id"] + ".json")
            _require(_digest(chapter_path.read_bytes()) == entry["sha256"], "chapter file digest mismatch")
            chapter = _read(root, "chapters/" + entry["id"] + ".json")
            _require((chapter["id"], chapter["order"], chapter["title"]) ==
                     (entry["id"], entry["order"], entry["title"])
                     and chapter["bookSlug"] == slug and chapter["sourceSha256"] == source_hash,
                     "chapter edition binding mismatch")
            digest = _digest(chapter["content"].encode("utf-8"))
            _require(digest == chapter["content_hash"] == match["content_sha256"], "chapter content digest mismatch")
            chapter_hashes[entry["id"]] = digest
            _require(all(match[key] == review[key] for key in ("id", "start", "length", "source_gap_before"))
                     and match["id"] == entry["id"], "unreviewed source transformation")
            start, body = match["start"], _normalized(chapter["content"])
            _require(type(start) is int and start >= cursor and len(body) == match["length"]
                     and text[start:start + len(body)] == body
                     and text[cursor:start] == match["source_gap_before"], "source/chapter fidelity mismatch")
            cursor = start + len(body)
        _require(chapter_hashes == authorization["chapter_sha256"], "authorized chapters mismatch")
        _require(_digest(text[cursor:].encode("utf-8")) == proof["tail_sha256"], "source tail mismatch")
        # Retained review records a bounded tail excerpt, not the full license.
        _require(isinstance(reviewed.get("tail"), str) and bool(reviewed["tail"])
                 and text[cursor:].startswith(reviewed["tail"]), "reviewed tail excerpt mismatch")
        for name, expected in manifest["artifacts"].items():
            _require(_digest(_path(root, name + ".json").read_bytes()) == expected, "manifest artifact mismatch")
        inventory = _read(root, "checksum_manifest.json")["files"]
        _require(any(item.get("file") == "source_integrity_validation.json" for item in inventory),
                 "source integrity proof not bound in checksum inventory")
        for item in inventory:
            _require(_digest(_path(root, item["file"]).read_bytes()) == item["sha256"], "checksum inventory mismatch")
        result["phase_4"] = "CLEANED"
        result["phase_5"] = "READY_FOR_REVIEW"
        result["checks"]["exact_source_and_canonical_chapters"] = "PASS"
        result["evidence"]["source_sha256"] = source_hash
        result["evidence"]["chapter_content_sha256"] = chapter_hashes
        policy = _read(repository, "internal/earnalism_intelligence/cover_acceptance_policy.json")
        for asset in assets:
            for prefix, base in (("source", root), ("delivery", repository)):
                path = _path(base, asset[prefix + "_file"])
                _require(_digest(path.read_bytes()) == asset[prefix + "_sha256"]
                         and path.stat().st_size == asset[prefix + "_bytes"], "cover bytes mismatch")
                with Image.open(path) as image:
                    _require(list(image.size) == asset[prefix + "_dimensions"], "cover dimensions mismatch")
                    image.verify()
            sw, sh = asset["source_dimensions"]
            dw, dh = asset["delivery_dimensions"]
            _require(sw > 0 and sh > 0 and dw > 0 and dh > 0 and sw * dh == sh * dw,
                     "cover aspect ratio changed")
            # Targets are observations, not additional approval gates. Covers
            # over the card target must not be silently redesigned or relabelled.
            result["checks"]["cover_" + asset["kind"] + "_thumbnail_target"] = (
                "PASS" if asset["delivery_bytes"] <=
                policy["performance_budget"]["card_thumbnail_target_kb"] * 1024 else "OVER_TARGET")
        _require(reviews["review_a"].get("fresh_actual_png_webp_visual_review") ==
                 "PASS_LEGIBLE_THEMATIC_GRAPHICS_AND_CREDITS"
                 and reviews["review_b"].get("visual_delivery") == "PASS", "retained visual review unavailable")
        result["checks"]["existing_cover_technical_and_retained_visual"] = "PASS"
        # The policy additionally requires browser smoke/build/audio-safety and
        # final exact release binding. Local byte checks cannot attest to those.
        result["phase_6"] = "PARTIAL_DRY_RUN"
        result["checks"]["current_cover_browser_acceptance"] = "UNVERIFIED"
        audio = manifest["audio_release"]
        result["checks"]["text_only_audio_exception"] = (
            "PASS" if audio.get("required_for_reader_release") is False
            and audio.get("exposed") is False and audio.get("status") == "NOT_REQUESTED" else "UNVERIFIED")
        result["blockers"] = ["CURRENT_COVER_POLICY_RELEASE_CHECKS_NOT_EXECUTED",
                              "FINAL_EXACT_PUBLICATION_QA_NOT_ESTABLISHED",
                              "PAID_READER_ACCEPTANCE_NOT_ESTABLISHED"]
    except (OSError, ValueError, KeyError, TypeError, StopIteration, UnicodeError) as error:
        # No manuscript, URLs, credential material or arbitrary exception text.
        result["blockers"].append(str(error) if isinstance(error, ValueError)
                                  and not isinstance(error, (json.JSONDecodeError, UnicodeError))
                                  else "REQUIRED_EVIDENCE_MISSING_OR_MALFORMED")
    return result
