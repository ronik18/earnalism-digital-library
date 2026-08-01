#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

TARGETS_ARG="${*:-}"
if [[ -z "$TARGETS_ARG" ]]; then
  TARGETS="radharani muchiram-gurer-jibanchorit book-d19e96859f book-f5d593e1f4 book-edfcf810c5 the-tell-tale-heart the-yellow-wallpaper the-necklace"
else
  TARGETS="$TARGETS_ARG"
fi

if [[ ! -f ".secrets/earnalism-import.env" ]]; then
  echo "Missing .secrets/earnalism-import.env (Cloudinary creds)." >&2
  exit 2
fi

set -a
source .secrets/earnalism-import.env
set +a

if [[ -z "${CLOUDINARY_CLOUD_NAME:-}" || -z "${CLOUDINARY_API_KEY:-}" || -z "${CLOUDINARY_API_SECRET:-}" ]]; then
  echo "Cloudinary credentials not loaded." >&2
  exit 2
fi

read -r -a TARGETS_ARRAY <<< "$TARGETS"
export TARGETS_ARG="$TARGETS"

python3 - <<'PY'
import json
import os
import urllib.request
from urllib.error import URLError
from urllib.parse import urlparse
from pathlib import Path
import cloudinary
import cloudinary.uploader

TARGETS = set(os.environ.get("TARGETS_ARG", "").split())
inv = json.load(open("internal/audiobook_lab/storage_containment/unapproved_direct_audio_inventory.json"))
rows = [
    r
    for r in inv["objects"] + inv["supporting_assets"]
    if r.get("slug") in TARGETS
    and r.get("recommended_action") == "MOVE_TO_PRIVATE_QA_BUCKET"
    and r.get("storage_provider") == "Cloudinary"
]

if not rows:
    print("No MOVE_TO_PRIVATE_QA_BUCKET Cloudinary rows found for", ", ".join(sorted(TARGETS)))
    raise SystemExit(0)

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)

def source_for(row):
    pub = row["storage_locator"]["public_id"]
    slug = row["slug"]
    resource_type = row["storage_locator"].get("resource_type", "video")
    base = Path("output")
    candidates = []

    # Baseline candidates from exact Cloudinary-derived filename
    if resource_type == "raw":
        raw_name = Path(row["storage_locator"].get("public_id", f"{row['object_id']}.raw")).name
        candidates.extend([
            base / "open_source_audiobooks" / "en" / slug / raw_name,
            base / "open_source_audiobooks" / "en" / raw_name,
            base / "open_source_audiobooks" / "ben" / slug / raw_name,
            base / "open_source_audiobooks" / "ben" / raw_name,
            base / "bengali_audiobooks" / "generated_sarvam" / "ben" / slug / raw_name,
            base / "bengali_audiobooks" / "generated_sarvam" / "ben" / raw_name,
            base / raw_name,
        ])

    # Common slug-based mp3 candidates
    if "-bengali-polish-queue-v1" in pub:
        candidates.append(base / "bengali_audiobook_polish" / "bengali-polish-queue-v1" / "bundles" / "ben" / slug / f"{slug}.mp3")
    elif "-english-polish-queue-v1" in pub:
        candidates.append(base / "english_audiobook_polish" / "english-polish-queue-v1" / "bundles" / "en" / slug / f"{slug}.mp3")
    elif "-english-polish-edge-queue-v1" in pub:
        candidates.append(base / "english_audiobook_polish" / "english-polish-edge-queue-v1" / "bundles" / "en" / slug / f"{slug}.mp3")
        candidates.append(base / "english_audiobook_polish" / "english-polish-edge-below9-v1" / "bundles" / "en" / slug / f"{slug}.mp3")
    elif "/eng/" in pub or "/en/" in pub:
        candidates.append(base / "open_source_audiobooks" / "en" / f"{slug}.mp3")
    elif "/ben/" in pub or "/bn/" in pub or "/ben/" in row.get("direct_url", ""):
        candidates.append(base / "open_source_audiobooks" / "ben" / f"{slug}.mp3")
        candidates.append(base / "bengali_audiobooks" / "generated_sarvam" / "ben" / f"{slug}.mp3")
    else:
        candidates.append(base / "open_source_audiobooks" / "en" / f"{slug}.mp3")
        candidates.append(base / "open_source_audiobooks" / "ben" / f"{slug}.mp3")
        candidates.append(base / "bengali_audiobooks" / "generated_sarvam" / "ben" / f"{slug}.mp3")
        candidates.append(base / "open_source_audiobooks" / slug / f"{slug}.mp3")

    # raw uploads often lose strict variant names; probe direct slug mp3 fallback too
    if resource_type == "raw":
        candidates.append(base / "open_source_audiobooks" / "en" / f"{slug}.mp3")
        candidates.append(base / "open_source_audiobooks" / "ben" / f"{slug}.mp3")
        candidates.append(base / "open_source_audiobooks" / f"{slug}.mp3")

    # Also check wildcard/legacy filename variants for direct IDs embedded in public_id
    slug_stems = list({
        f"{slug}.mp3",
        f"{slug}_mp3_{row['object_id']}.mp3",
        f"{slug}_mp3_{row['object_id'][:8]}.mp3",
    })
    for stem in slug_stems:
        candidates.extend(
            [
                base / "open_source_audiobooks" / "en" / stem,
                base / "open_source_audiobooks" / "ben" / stem,
                base / "open_source_audiobooks" / slug / stem,
                base / "open_source_audiobooks" / row.get('slug', '').replace('/', '_') / stem,
            ]
        )

    candidates.append(base / "open_source_audiobooks" / f"{row.get('slug', '').replace('/', '_')}.mp3")

    for c in candidates:
        if c.exists():
            return str(c), [str(x) for x in candidates]

    # Last-resort pattern match for slug/objected files in open source tree.
    # Handles variants like a-ghost-story_mp3_<id>.mp3 when explicit paths miss.
    fallback_patterns = []
    en_root = base / "open_source_audiobooks" / "en"
    ben_root = base / "open_source_audiobooks" / "ben"
    if en_root.exists():
        fallback_patterns.extend([f"{slug}*.mp3", f"*{slug}*.mp3"])
    if ben_root.exists():
        fallback_patterns.extend([f"{slug}*.mp3", f"*{slug}*.mp3"])
    if base.joinpath("open_source_audiobooks").exists():
        fallback_patterns.extend([f"{slug}*.mp3", f"*{slug}*.mp3", f"{slug}/{slug}*.mp3", f"{slug}/*{slug}*.mp3"])

    pattern_seen = set()
    for pattern in fallback_patterns:
        if pattern in pattern_seen:
            continue
        pattern_seen.add(pattern)
        for root in [en_root, ben_root, base / "open_source_audiobooks"]:
            try:
                for found in sorted((r for r in root.glob(pattern) if r.is_file()), key=lambda p: p.as_posix()):
                    return str(found), [str(x) for x in candidates] + [str(found)]
            except Exception:
                continue

    # For raw assets, prefer Cloudinary download fallback only if local lookup fails.
    if resource_type == "raw":
        return None, [str(x) for x in candidates]

    return None, [str(c) for c in candidates]


missing = []
for row in rows:
    pub = row["storage_locator"]["public_id"]
    resource_type = row["storage_locator"].get("resource_type", "video")
    local, candidates = source_for(row)

    if not local:
        if resource_type == "raw" and row.get("direct_url"):
            direct_url = row["direct_url"]
            direct_name = Path(urlparse(direct_url).path).name
            if direct_name:
                tmp = Path("/tmp") / direct_name
            else:
                tmp = Path("/tmp") / f"{row['object_id']}.raw"
            tmp_created = True
            try:
                with urllib.request.urlopen(direct_url) as source, tmp.open("wb") as output:
                    output.write(source.read())
                local = str(tmp)
            except URLError as exc:
                if tmp_created and tmp.exists():
                    tmp.unlink()
                missing.append((row["slug"], row["object_id"], pub, candidates, str(exc)))
                continue
        else:
            missing.append((row["slug"], row["object_id"], pub, candidates))
            continue

    print(f"[restore] {row['slug']} {row['object_id']} -> {pub} from {local}")
    with open(local, "rb") as fh:
        result = cloudinary.uploader.upload(
            fh,
            resource_type=resource_type,
            public_id=pub,
            overwrite=True,
            use_filename=False,
            unique_filename=False,
            invalidate=True,
        )
    print("  ok:", result.get("secure_url"), "bytes=", result.get("bytes"))
    if resource_type == "raw" and local and local.startswith("/tmp/"):
        Path(local).unlink(missing_ok=True)

if missing:
    print("Missing local source candidates:")
    for item in missing:
        if len(item) == 4:
            slug, oid, pub, cands = item
            err = None
        else:
            slug, oid, pub, cands, err = item
        print(" ", slug, oid, pub)
        if err:
            print("   error:", err)
        for c in cands:
            print("   ", c)
    raise SystemExit(2)
PY