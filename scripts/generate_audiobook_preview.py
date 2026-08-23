#!/usr/bin/env python3
"""Fail closed: Earnalism does not generate public audiobook previews."""

from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--source")
    parser.add_argument("--master-packet")
    parser.add_argument("--output-dir")
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "book_slug": args.slug,
                "duration_seconds": 0,
                "status": "AUDIO_PREVIEW_DISABLED",
                "message": "Public audiobook previews are disabled. Playback requires an approved audiobook and an active Reading Pass.",
            }
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
