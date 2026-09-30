"""Reject a blocked catalogue worker before reporting evidence exhaustion."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def validate_receipt(receipt_path: Path, batch_path: Path, expected_head: str) -> dict:
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("worker execution receipt is missing or is a symlink")
    receipt = json.loads(receipt_path.read_text())
    batch_bytes = batch_path.read_bytes()
    batch = json.loads(batch_bytes)
    if receipt.get("execution_status") != "COMPLETED":
        raise ValueError("worker assessment did not complete")
    if receipt.get("source_head") != expected_head:
        raise ValueError("worker receipt belongs to a different source head")
    if receipt.get("batch_sha256") != hashlib.sha256(batch_bytes).hexdigest():
        raise ValueError("worker receipt belongs to a different batch")
    candidates = batch.get("candidates") or []
    allowed = {item["slug"] for item in candidates}
    if (batch.get("schema_version") != 1 or batch.get("max_titles_to_modify") != 5
            or batch.get("candidate_count") != len(candidates)
            or len(candidates) != len(allowed) or len(candidates) > 20):
        raise ValueError("controller batch violates the approved bounds")
    examined = receipt.get("examined_slugs")
    if (not isinstance(examined, list) or not examined
            or any(not isinstance(slug, str) for slug in examined)
            or len(examined) != len(set(examined)) or not set(examined) <= allowed):
        raise ValueError("worker did not record actual candidate assessment")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        receipt = validate_receipt(args.receipt, args.batch, args.expected_head)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Catalogue implementation execution failed: {error}\n")
    print(f"Verified completed worker assessment: {len(receipt['examined_slugs'])} candidate slugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
