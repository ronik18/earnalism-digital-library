#!/usr/bin/env python3
"""Write the truth-gated homepage catalog snapshot consumed before API hydration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.home_curation import build_home_curated_payload  # noqa: E402


OUTPUT = ROOT / "frontend" / "src" / "data" / "homeCuratedSprint1.json"


def _serialized_payload() -> str:
    payload = build_home_curated_payload()
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the checked-in snapshot differs from canonical data.",
    )
    args = parser.parse_args()
    serialized = _serialized_payload()

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != serialized:
            raise SystemExit(
                "homepage snapshot is stale; run "
                "python3 scripts/generate_home_curated_frontend_snapshot.py"
            )
        print(f"verified {OUTPUT.relative_to(ROOT)}")
        return

    payload = json.loads(serialized)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        serialized,
        encoding="utf-8",
    )
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{len(payload['hero']['featured_books'])} featured, "
        f"{len(payload['shelves']['approved_audiobooks'])} approved audiobooks"
    )


if __name__ == "__main__":
    main()
