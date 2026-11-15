"""Build reusable, lossless text context for the existing production orchestrator.

This indexes source spans; it is not an emotion classifier, measured audio timing,
model training or editorial acceptance. Genre notes must come from an editor.
No hosted model, provider, network or publishing call is made here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

SCHEMA = "earnalism.content_context.v1"
SENTENCE = re.compile(r"[.!?।]+[\"'”’»]*(?:\s+|$)")
PHRASE = re.compile(r"[,;:—–]+(?:\s+|$)")
ABBREVIATION = re.compile(r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc)|\b[A-Z])\.$", re.I)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def partitions(text, start, end, pattern, *, sentences=False):
    """Candidate punctuation boundaries; retain every character, including spaces."""
    previous = start
    for match in pattern.finditer(text, start, end):
        cut = match.end()
        if sentences and ABBREVIATION.search(text[max(start, match.start()-12):match.start()+1]):
            continue
        if previous < cut < end:
            yield previous, cut
            previous = cut
    if previous < end:
        yield previous, end


def build(source, output, *, expected_sha256, title, language, genre_notes=(), page_size=256):
    source, raw_output = Path(source).resolve(), Path(output).expanduser().absolute()
    if raw_output.is_symlink():
        raise ValueError("Preserve symlink context destination")
    output = raw_output.resolve()
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        raise ValueError("Private source context must remain outside a Git checkout")
    if language not in {"en", "bn"} or not isinstance(title, str) or not title.strip():
        raise ValueError("Exact title and English/Bengali language required")
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not 32 <= page_size <= 512:
        raise ValueError("Context page size must be 32..512 units")
    if not isinstance(genre_notes, (list, tuple)) or any(not isinstance(x, str) for x in genre_notes):
        raise ValueError("Genre notes must be explicit editorial strings")
    if source.stat().st_size > 32 * 1024**2:
        raise ValueError("Split a source above 32 MiB into its actual volumes")
    raw = source.read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", str(expected_sha256)) or digest(raw) != expected_sha256:
        raise ValueError("Exact source bytes changed")
    text = raw.decode("utf-8")
    if not text.strip():
        raise ValueError("Empty source")
    recipe = {"schema": SCHEMA, "source_sha256": expected_sha256, "title": title,
              "language": language, "genre_notes": list(genre_notes), "page_size": page_size}
    recipe_sha = digest(json.dumps(recipe, ensure_ascii=False, sort_keys=True).encode())
    manifest_path = output / "context.json"
    if output.exists():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError("Preserve existing incomplete or unowned context directory")
        retained = json.loads(manifest_path.read_text())
        source_ref = {"path": str(source), "sha256": expected_sha256, "bytes": len(raw)}
        if (retained.get("recipe_sha256") != recipe_sha or retained.get("source") != source_ref
                or any(retained.get(k) != v for k, v in recipe.items())
                or retained.get("semantic_review") != "UNASSESSED"
                or retained.get("production_ready") is not False
                or retained.get("audio_timing") != "UNMEASURED"
                or retained.get("model_weights_trained") is not False
                or retained.get("publication_performed") is not False
                or type(retained.get("codex_api_calls_by_indexer")) is not int
                or retained.get("codex_api_calls_by_indexer") != 0
                or retained.get("work") != {"id": "work", "start_char": 0, "end_char": len(text),
                                             "start_byte": 0, "end_byte": len(raw)}):
            raise ValueError("Preserve earlier context; source or editorial recipe differs")
        units = []
        for index, page in enumerate(retained["pages"], 1):
            if page.get("path") != f"units-{index:05d}.json":
                raise ValueError("Retained context page escapes its exact inventory")
            path = output / page["path"]
            if (path.is_symlink() or not path.is_file() or path.stat().st_size != page["bytes"]
                    or digest(path.read_bytes()) != page["sha256"]):
                raise ValueError("Preserve missing or changed retained context page")
            value = json.loads(path.read_text())
            if value.get("source_sha256") != expected_sha256 or not isinstance(value.get("units"), list):
                raise ValueError("Retained context source differs")
            size = len(value["units"])
            if not 1 <= size <= page_size or (index < len(retained["pages"]) and size != page_size):
                raise ValueError("Retained context page exceeds or changes its bounded layout")
            units.extend(value["units"])
        verify_units(text, units, retained["counts"])
        return {"path": str(manifest_path), "sha256": digest(manifest_path.read_bytes()),
                "reused": True, "counts": retained["counts"], "semantic_review": "UNASSESSED"}
    # UTF-8 offsets are exact. Splits occur after punctuation/space, never within
    # a Bengali mark sequence; no normalization or rewriting is applied.
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + len(character.encode("utf-8")))
    units, counts = [], {"block": 0, "sentence_candidate": 0, "phrase_candidate": 0}

    def add(kind, start, end, parent):
        if len(units) >= 524288:
            raise ValueError("Split oversized context into its actual source volumes")
        counts[kind] += 1
        identity = kind + "-" + str(counts[kind]).zfill(7)
        units.append({"id": identity, "kind": kind, "parent": parent,
                      "start_char": start, "end_char": end,
                      "start_byte": offsets[start], "end_byte": offsets[end],
                      "text_sha256": digest(text[start:end].encode()),
                      "direction_status": "UNASSESSED", "timing_status": "TEXT_ONLY_UNMEASURED"})
        return identity

    # A serialized text block is not necessarily an authorial paragraph: some
    # retained plain texts place blank lines after wrapped lines. Keep this fact.
    blocks = partitions(text, 0, len(text), re.compile(r"\n[\t ]*\n+"))
    for left, right in blocks:
        block = add("block", left, right, "work")
        for start, end in partitions(text, left, right, SENTENCE, sentences=True):
            sentence = add("sentence_candidate", start, end, block)
            for a, b in partitions(text, start, end, PHRASE):
                add("phrase_candidate", a, b, sentence)
    output.parent.mkdir(parents=True, exist_ok=True)
    pages = []
    with tempfile.TemporaryDirectory(prefix=".content-context-", dir=output.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        for index in range(0, len(units), page_size):
            name = "units-" + str(index // page_size + 1).zfill(5) + ".json"
            page_raw = (json.dumps({"source_sha256": expected_sha256,
                                   "units": units[index:index+page_size]}, ensure_ascii=False,
                                  separators=(",", ":")) + "\n").encode()
            (staging / name).write_bytes(page_raw)
            pages.append({"path": name, "sha256": digest(page_raw), "bytes": len(page_raw)})
        manifest = {**recipe, "recipe_sha256": recipe_sha,
                    "source": {"path": str(source), "sha256": expected_sha256, "bytes": len(raw)},
                    "work": {"id": "work", "start_char": 0, "end_char": len(text),
                             "start_byte": 0, "end_byte": len(raw)},
                    "counts": counts, "pages": pages,
                    "structure_basis": "Serialized blocks and punctuation candidates; verify authorial paragraph/sentence boundaries before performance use",
                    "genre_note_provenance": "Explicit editorial notes, not inferred labels",
                    "semantic_review": "UNASSESSED", "audio_timing": "UNMEASURED",
                    "model_weights_trained": False, "codex_api_calls_by_indexer": 0,
                    "production_ready": False, "publication_performed": False}
        (staging / "context.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
        staging.rename(output)
    return {"path": str(manifest_path), "sha256": digest(manifest_path.read_bytes()),
            "reused": False, "counts": counts, "semantic_review": "UNASSESSED"}


def verify_units(text, units, counts):
    """Validate lossless hierarchy on reuse, independently of claimed page hashes."""
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + len(character.encode("utf-8")))
    nodes = {"work": {"kind": "work", "start_char": 0, "end_char": len(text)}}
    observed = {"block": 0, "sentence_candidate": 0, "phrase_candidate": 0}
    children = {}
    parent_kinds = {"block": "work", "sentence_candidate": "block", "phrase_candidate": "sentence_candidate"}
    for unit in units:
        kind, identity = unit["kind"], unit["id"]
        a, b, parent = unit["start_char"], unit["end_char"], unit["parent"]
        if (kind not in observed or identity in nodes or type(a) is not int or type(b) is not int
                or not 0 <= a < b <= len(text) or parent not in nodes
                or nodes[parent]["kind"] != parent_kinds[kind]
                or unit.get("direction_status") != "UNASSESSED"
                or unit.get("timing_status") != "TEXT_ONLY_UNMEASURED"
                or unit["start_byte"] != offsets[a] or unit["end_byte"] != offsets[b]
                or unit["text_sha256"] != digest(text[a:b].encode())):
            raise ValueError("Retained context spans or acceptance fields changed")
        if identity != kind + "-" + str(observed[kind] + 1).zfill(7):
            raise ValueError("Retained stable context identities changed")
        nodes[identity] = unit
        observed[kind] += 1
        children.setdefault(parent, []).append(unit)
    if observed != counts or not units:
        raise ValueError("Retained context coverage counts differ")
    for identity, node in nodes.items():
        if node["kind"] == "phrase_candidate":
            continue
        position = node["start_char"]
        for child in children.get(identity, []):
            if child["start_char"] != position:
                raise ValueError("Retained context has missing, reordered or duplicate source")
            position = child["end_char"]
        if position != node["end_char"]:
            raise ValueError("Retained context hierarchy is incomplete")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--language", choices=("en", "bn"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--genre-note", action="append", default=[])
    args = parser.parse_args(argv)
    print(json.dumps(build(args.source, args.output, expected_sha256=args.sha256,
                           title=args.title, language=args.language, genre_notes=args.genre_note)))


if __name__ == "__main__":
    main()
