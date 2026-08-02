#!/usr/bin/env python3
"""Reproducible, allowlisted Gitanjali source acquisition.

This tool only stages and verifies source material. It does not import or
publish a book. Production mutation belongs to the existing reviewed release
pipeline after source, text, audio, and alignment gates pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ITEM = "gitanjali_1002_librivox"
BASE = f"https://archive.org/download/{ITEM}/"
METADATA_URL = f"https://archive.org/metadata/{ITEM}"
EXPECTED_TRACKS = [f"gitanjali_{i:02d}_tagore.mp3" for i in range(1, 12)]
EXPECTED_M4B = "Gitanjali_librivox.m4b"
ALLOWED_HOSTS = {
    "archive.org", "www.archive.org", "en.wikisource.org", "commons.wikimedia.org",
    "standardebooks.org", "www.standardebooks.org", "librivox.org", "www.librivox.org",
}
USER_AGENT = "Earnalism-Gitanjali-Importer/1.0 (+https://theearnalism.com)"


def url_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_HOSTS or host.endswith(".archive.org") or host == "raw.githubusercontent.com"


def fetch(url: str, *, timeout: int = 30) -> tuple[bytes, dict[str, str]]:
    if not url_allowed(url):
        raise ValueError(f"disallowed source host: {url}")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:
        return response.read(), {str(k): str(v) for k, v in response.headers.items()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata(output: Path) -> dict:
    target = output / "source" / "metadata" / "internet-archive-audio-metadata.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))
    body, _ = fetch(METADATA_URL)
    target.write_bytes(body)
    return json.loads(body)


def validate_inventory(data: dict) -> dict[str, dict]:
    if data.get("metadata", {}).get("identifier") != ITEM:
        raise ValueError("Internet Archive identifier mismatch")
    files = data.get("files") or []
    by_name: dict[str, dict] = {}
    for item in files:
        name = item.get("name")
        if name in by_name:
            raise ValueError(f"duplicate metadata filename: {name}")
        if name:
            by_name[name] = item
    required = [*EXPECTED_TRACKS, EXPECTED_M4B]
    missing = [name for name in required if name not in by_name]
    if missing:
        raise ValueError("missing required source files: " + ", ".join(missing))
    for name in EXPECTED_TRACKS:
        if "64kb" in name.lower() or by_name[name].get("source") == "derivative":
            raise ValueError(f"wrong audio derivative selected: {name}")
    return by_name


def download(url: str, target: Path, expected: dict) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        actual = sha256(target)
        if expected.get("size") and target.stat().st_size != int(expected["size"]):
            raise ValueError(f"cached size mismatch: {target}")
        return {"status": "reused", "bytes": target.stat().st_size, "sha256": actual}
    part = target.with_suffix(target.suffix + ".part")
    if part.exists():
        part.unlink()
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response, part.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            handle.write(block)
    if expected.get("size") and part.stat().st_size != int(expected["size"]):
        part.unlink(missing_ok=True)
        raise ValueError(f"size mismatch for {target.name}")
    os.replace(part, target)
    return {"status": "downloaded", "bytes": target.stat().st_size, "sha256": sha256(target)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("var/import/gitanjali"))
    args = parser.parse_args()
    if sum(bool(x) for x in (args.dry_run, args.execute, args.verify)) != 1:
        parser.error("choose exactly one of --dry-run, --execute, or --verify")

    data = metadata(args.output)
    inventory = validate_inventory(data)
    entries = []
    for name in [*EXPECTED_TRACKS, EXPECTED_M4B]:
        folder = "vbr" if name.endswith(".mp3") else "whole-book"
        path = args.output / "source" / "audio" / folder / name
        entry = {"source_id": name, "url": BASE + quote(name), "path": str(path), "required": True, **inventory[name]}
        if args.execute:
            entry.update(download(entry["url"], path, inventory[name]))
        elif args.verify:
            if not path.exists():
                entry.update({"status": "missing"})
            else:
                entry.update({"status": "verified", "bytes": path.stat().st_size, "sha256": sha256(path)})
        else:
            entry["status"] = "planned"
        entries.append(entry)
    manifest = {"item": ITEM, "source_metadata_url": METADATA_URL, "files": entries}
    manifest_path = args.output / "manifests" / "source-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "execute" if args.execute else "verify" if args.verify else "dry-run", "files": len(entries), "manifest": str(manifest_path), "statuses": {s: sum(e["status"] == s for e in entries) for s in {e["status"] for e in entries}}}, sort_keys=True))
    return 0 if all(e["status"] not in {"missing"} for e in entries) else 2


if __name__ == "__main__":
    raise SystemExit(main())
