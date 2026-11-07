"""Safely retain and import one complete, exact-source Colab narration ZIP.

Only original per-unit WAV, generation JSON and actual-audio alignment JSON enter
``imported``. All other original logs/environment/licence records remain in the
retained byte-identical ZIP. This transfer is not listening or publication
acceptance. Any ASR discrepancy is recorded unresolved and still blocks assembly.
No archive extraction API is used; prevalidated files are copied to fresh names.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import tempfile
import zipfile

try:
    from . import assemble
except ImportError:
    import assemble

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 128
MAX_MANIFEST_BYTES = 64 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_RATIO = 200
CHUNK = 1024 * 1024
ROOT_RECORDS = {"units.json", "qwen_snapshot.json", "qwen_environment.json", "qwen-job.json", "asr-model.json", "recovery-accounting.json"}
LOG_RECORDS = {"logs/qwen.jsonl", "logs/qwen-report.json"}
PROVENANCE_RECORDS = {"provenance/Qwen-pinned-model-README.md", "provenance/Qwen-pinned-model-LICENSE",
                      "provenance/Qwen-code-LICENSE.txt"}
RESERVED = (".thermal-import-lock.json", "imported", "narration-transfer", "transfer-receipt.json")
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *[f"com{i}" for i in range(1, 10)],
                    *[f"lpt{i}" for i in range(1, 10)]}


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def strict_json(raw):
    def pairs(rows):
        result = {}
        for name, value in rows:
            assemble.require(name not in result, "Duplicate JSON object key")
            result[name] = value
        return result

    def constant(value):
        raise assemble.QualificationError("Nonfinite JSON value: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def safe_member(info):
    name = info.filename
    assemble.require(name == info.orig_filename and len(name) <= 240 and
                     not info.is_dir() and "\\" not in name and "\x00" not in name,
                     "Unsafe or noncanonical ZIP member")
    path = PurePosixPath(name)
    assemble.require(not path.is_absolute() and path.as_posix() == name and path.parts,
                     "ZIP traversal or noncanonical path")
    for part in path.parts:
        assemble.require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", part) is not None and
                         not part.endswith(".") and part.split(".")[0].lower() not in WINDOWS_RESERVED,
                         "Unsafe/reserved ZIP path component")
    mode = (info.external_attr >> 16) & 0o170000
    assemble.require(mode in (0, stat.S_IFREG), "ZIP links/devices/directories are not permitted")
    assemble.require(not info.flag_bits & 1 and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                     "Encrypted/unsupported ZIP compression")
    assemble.require(0 <= info.file_size <= MAX_MEMBER_BYTES and info.compress_size >= 0,
                     "ZIP member exceeds transfer limits")
    if info.file_size:
        assemble.require(info.compress_size > 0 and
                         (info.file_size <= 1024 * 1024 or info.file_size / info.compress_size <= MAX_RATIO),
                         "Suspicious ZIP expansion ratio")
    return name


def read_limited(archive, name, limit):
    info = archive.getinfo(name)
    assemble.require(info.file_size <= limit, "JSON transfer record exceeds size limit")
    with archive.open(info) as handle:
        result = handle.read(limit + 1)
    assemble.require(len(result) <= limit and len(result) == info.file_size,
                     "ZIP record length differs from central directory")
    return result


def required_paths(units):
    return [name for unit in units for name in (f"raw/{unit['id']}.wav", f"raw/{unit['id']}.wav.json",
                                               f"alignment/{unit['id']}.json")]


def preflight_zip_container(path):
    """Bound central-directory parsing before zipfile allocates member objects."""
    path = Path(path)
    size = path.stat().st_size
    assemble.require(22 <= size <= MAX_ARCHIVE_BYTES, "Invalid or oversized source archive")
    with path.open("rb") as handle:
        handle.seek(max(0, size - 65557))
        tail = handle.read(65557)
    index = tail.rfind(b"PK\x05\x06")
    assemble.require(index >= 0 and len(tail) - index >= 22, "Missing ZIP end record")
    signature, disk, directory_disk, count_disk, count, length, offset, comment = struct.unpack(
        "<4s4H2LH", tail[index:index + 22])
    assemble.require(disk == directory_disk == 0 and count_disk == count and 0 < count <= MAX_MEMBERS and
                     length <= MAX_MANIFEST_BYTES * 4 and offset != 0xffffffff and length != 0xffffffff,
                     "Multidisk/ZIP64 or excessive central directory is not a supported Colab transfer")
    end_offset = size - len(tail) + index
    assemble.require(index + 22 + comment == len(tail) and offset + length == end_offset,
                     "Unexpected ZIP overlay or inconsistent central directory")


def inspect_archive(archive, units, recovery_plan=None):
    """Bound ZIP work and verify *every* original file before creating outputs."""
    infos = archive.infolist()
    assemble.require(0 < len(infos) <= MAX_MEMBERS, "Unexpected ZIP member count")
    names = [safe_member(info) for info in infos]
    assemble.require(len(set(names)) == len(names) and len({n.casefold() for n in names}) == len(names),
                     "Duplicate or case-colliding ZIP members")
    assemble.require(sum(info.file_size for info in infos) <= MAX_TOTAL_BYTES, "ZIP expansion exceeds transfer limit")
    assemble.require("transfer-manifest.json" in names, "Missing transfer manifest")
    raw_manifest = read_limited(archive, "transfer-manifest.json", MAX_MANIFEST_BYTES)
    manifest = strict_json(raw_manifest)
    assemble.require(isinstance(manifest, dict) and set(names) == set(manifest) | {"transfer-manifest.json"} and
                     "transfer-manifest.json" not in manifest, "Transfer manifest/member set differs")
    required = set(required_paths(units))
    if recovery_plan is not None:
        assemble.require({"recovery-accounting.json", "logs/qwen.jsonl", "qwen-job.json"} <= set(manifest),
                         "Recovery archive is missing actual attempt accounting")
    else:
        assemble.require("recovery-accounting.json" not in manifest, "Recovery export needs its local bounded plan")
    assemble.require(required | {"units.json"} <= set(manifest), "Incomplete aligned narration transfer")
    allowed = required | ROOT_RECORDS | LOG_RECORDS | PROVENANCE_RECORDS
    assemble.require(set(manifest) <= allowed, "Unexpected/reserved output in narration archive")
    for name, digest in manifest.items():
        if name.endswith(".json"):
            assemble.require(archive.getinfo(name).file_size <= MAX_JSON_BYTES, "Oversized JSON transfer record")
        assemble.require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
                         "Invalid transfer digest")
        actual, size = hashlib.sha256(), 0
        with archive.open(name) as handle:
            while block := handle.read(CHUNK):
                size += len(block)
                assemble.require(size <= MAX_MEMBER_BYTES, "Expanded member exceeds transfer limit")
                actual.update(block)
        assemble.require(size == archive.getinfo(name).file_size and actual.hexdigest() == digest,
                         "Transfer manifest hash mismatch: " + name)
    exported_units = strict_json(read_limited(archive, "units.json", MAX_JSON_BYTES))
    assemble.require(exported_units == units, "Exported units differ from the current prepared script/anchors")
    return manifest, raw_manifest


def preflight_destination(root):
    root = Path(root)
    assemble.require(root.is_dir(), "Prepared production folder does not exist")
    assemble.require(not any(os.path.lexists(root / name) for name in RESERVED),
                     "Existing or partial import preserved; use a separate prepared production folder")


def copy_stream_new(source, target):
    with Path(target).open("xb") as handle:
        shutil.copyfileobj(source, handle, length=CHUNK)


def import_narration(archive_path, root):
    root, archive_path = Path(root).resolve(), Path(archive_path).resolve()
    preflight_destination(root)
    units_path, baseline_path = root / "units.json", root / "baseline-job.json"
    units, baseline = strict_json(units_path.read_bytes()), strict_json(baseline_path.read_bytes())
    assemble.validate_units(units)
    assemble.validate_baseline(baseline)
    assemble.require(archive_path.is_file(), "Source archive does not exist")
    preflight_zip_container(archive_path)
    archive_digest = file_hash(archive_path)
    input_hashes = {"units.json": file_hash(units_path), "baseline-job.json": file_hash(baseline_path)}
    plan_path = root / "recovery-accounting.json"
    recovery_plan = strict_json(plan_path.read_bytes()) if plan_path.is_file() else None
    assemble.require(recovery_plan is not None or "v2-recovery" not in root.name,
                     "Recovery destination is missing its bounded plan")
    if recovery_plan is not None:
        try:
            from . import recovery
        except ImportError:
            import recovery
        recovery.validate_plan(recovery_plan, units, baseline)
        input_hashes["recovery-accounting.json"] = file_hash(plan_path)
    with zipfile.ZipFile(archive_path) as archive:
        manifest, raw_manifest = inspect_archive(archive, units, recovery_plan)
        selected = required_paths(units)
        with tempfile.TemporaryDirectory(prefix=".thermal-import-verify-", dir=root) as temporary:
            stage = Path(temporary)
            for folder in ("raw", "alignment"):
                (stage / folder).mkdir()
            for name in selected:
                with archive.open(name) as source:
                    copy_stream_new(source, stage / name)
                assemble.require(file_hash(stage / name) == manifest[name], "Staged source bytes changed")
            audits = []
            for unit in units:
                wav = stage / "raw" / f"{unit['id']}.wav"
                metadata = strict_json((stage / "raw" / f"{unit['id']}.wav.json").read_bytes())
                alignment = strict_json((stage / "alignment" / f"{unit['id']}.json").read_bytes())
                source = assemble.validate_source(unit, wav, metadata, baseline)
                audit, _ = assemble.alignment_audit(unit, alignment, source["audio_sha256"], source["duration"])
                audits.append(audit)
            recovered = None
            if recovery_plan is not None:
                recovered = strict_json(read_limited(archive, "recovery-accounting.json", MAX_JSON_BYTES))
                journal = read_limited(archive, "logs/qwen.jsonl", MAX_JSON_BYTES)
                job = strict_json(read_limited(archive, "qwen-job.json", MAX_JSON_BYTES))
                recovery.validate_observation(recovered, recovery_plan, journal, job, units,
                    {u["id"]: strict_json((stage / "raw" / f"{u['id']}.wav.json").read_bytes()) for u in units})
            assemble.require(file_hash(archive_path) == archive_digest, "Source archive changed during verification")
            assemble.require(all(file_hash(root / name) == digest for name, digest in input_hashes.items()),
                             "Prepared script/baseline changed during transfer")
            preflight_destination(root)
            # Exclusive lock is retained after a partial failure. No implicit resume,
            # directory replacement, or previously imported file overwrite is allowed.
            assemble.write_new(root / RESERVED[0], {"state": "EXCLUSIVE_PRIVATE_NARRATION_IMPORT",
                                                     "archive_sha256": archive_digest,
                                                     "publication_approved": False})
            destination, retention = root / "imported", root / "narration-transfer"
            destination.mkdir()
            retention.mkdir()
            for folder in ("raw", "alignment"):
                (destination / folder).mkdir()
            for name in selected:
                with (stage / name).open("rb") as source:
                    copy_stream_new(source, destination / name)
            with archive_path.open("rb") as source:
                copy_stream_new(source, retention / "source.zip")
            assemble.require(file_hash(retention / "source.zip") == archive_digest,
                             "Retained archive byte identity failed")
            with (retention / "transfer-manifest.json").open("xb") as handle:
                handle.write(raw_manifest)
            with archive.open("units.json") as source:
                copy_stream_new(source, retention / "original-units.json")
            if recovered is not None:
                for original, retained in (("recovery-accounting.json", "recovery-observation.json"),
                                           ("logs/qwen.jsonl", "recovery-qwen.jsonl"),
                                           ("qwen-job.json", "recovery-job.json")):
                    with archive.open(original) as source:
                        copy_stream_new(source, retention / retained)
            assemble.require(all(file_hash(destination / name) == manifest[name] for name in selected),
                             "Imported source byte identity failed")
            receipt = {"state": "IMPORTED_PRIVATE_SOURCE_REQUIRES_ASSEMBLY_AND_REVIEW",
                       "archive_original_path": str(archive_path), "archive_retained_path": "narration-transfer/source.zip",
                       "archive_sha256": archive_digest, "archive_bytes": archive_path.stat().st_size,
                       "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
                       "members_verified": len(manifest), "units_verified": len(units),
                       "prepared_inputs": input_hashes,
                       "imported_files": {name: manifest[name] for name in selected},
                       "archive_only_records": {name: digest for name, digest in manifest.items() if name not in selected},
                       "source_validation": "PASS", "asr_audits": audits,
                       "asr_differences_unresolved": sum(len(a["differences"]) for a in audits),
                       "original_source_records_unchanged": True, "new_recording_listening": "PENDING",
                       "publication_approved": False,
                       "note": "Transfer integrity and exact B recipe only. Every ASR difference remains unresolved; "
                       "assembly still enforces factual words, anchors, caption timing and readability."}
            if recovered is not None:
                receipt["recovery_accounting"] = recovered
                receipt["recovery_observation_sha256"] = file_hash(retention / "recovery-observation.json")
            assemble.write_new(root / "transfer-receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = import_narration(args.archive, args.root)
    print(json.dumps({key: result[key] for key in ("state", "archive_sha256", "members_verified", "units_verified",
                                                  "asr_differences_unresolved", "new_recording_listening",
                                                  "publication_approved")}, indent=2))
