#!/usr/bin/env python3
"""Generate a hash-bound public audiobook preview limited to 180 seconds.

The command writes a local candidate only.  Upload and activation remain a
separate authenticated admin/storage operation so a generated file can never
silently become public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from audiobook_master_gate import MasterGateError, validate_master_packet


PREVIEW_SECONDS = 180


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--master-packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error("--source must be an existing approved local audio file")
    try:
        master_gate = validate_master_packet(
            args.master_packet,
            source_path=args.source,
            expected_slug=args.slug,
        )
    except MasterGateError as exc:
        parser.error("master packet failed closed: " + ", ".join(exc.blockers))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{args.slug}.preview-180s.mp3"
    command = [
        args.ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(args.source),
        "-t",
        str(PREVIEW_SECONDS),
        "-vn",
        "-ac",
        "1",
        "-b:a",
        "96k",
        str(output),
    ]
    subprocess.run(command, check=True)
    manifest = {
        "schema_version": "earnalism.audiobook-preview.v1",
        "book_slug": args.slug,
        "duration_seconds": PREVIEW_SECONDS,
        "source_sha256": sha256_file(args.source),
        "master_packet_sha256": master_gate["packet_sha256"],
        "master_approval_status": master_gate["status"],
        "preview_sha256": sha256_file(output),
        "preview_bytes": output.stat().st_size,
        "preview_file": output.name,
        "status": "LOCAL_CANDIDATE_NOT_UPLOADED_NOT_ACTIVE",
    }
    manifest_path = args.output_dir / f"{args.slug}.preview-180s.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
