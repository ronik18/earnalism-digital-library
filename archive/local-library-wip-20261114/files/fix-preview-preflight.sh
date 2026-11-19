#!/usr/bin/env bash

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

SCRIPT="repair-and-verify-uat12.sh"
TEST_FILE="tests/e2e/earnalism-real-user-journey.spec.js"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"

[[ -f "$SCRIPT" ]] || {
  echo "ERROR: Missing $SCRIPT" >&2
  exit 1
}

cp "$SCRIPT" "$SCRIPT.before-preview-fix-$STAMP"

if [[ -f "$TEST_FILE" ]]; then
  cp "$TEST_FILE" "$TEST_FILE.before-preview-fix-$STAMP"
fi

python3 <<'PY'
from pathlib import Path

script_path = Path("repair-and-verify-uat12.sh")
text = script_path.read_text(encoding="utf-8")

###############################################################################
# 1. Replace the strict preview_page_limit-only preflight with a schema-aware
#    validator.
###############################################################################

start = text.find("preview_limit = (")

if start == -1:
    raise SystemExit(
        "Could not locate the preview_limit preflight block."
    )

end_marker = "\n\nmanifest_audio = manifest.get(\"audio\") or {}"
end = text.find(end_marker, start)

if end == -1:
    raise SystemExit(
        "Could not locate the end of the preview preflight block."
    )

replacement = r'''preview_limit = (
    manifest.get("preview_page_limit")
    or (manifest.get("book") or {}).get(
        "preview_page_limit"
    )
    or (manifest.get("preview") or {}).get(
        "page_count"
    )
)

preview_chapters = [
    chapter
    for chapter in (manifest.get("chapters") or [])
    if (
        chapter.get("is_preview") is True
        or chapter.get("is_free_preview") is True
    )
]

strict_page_contract = (
    os.environ.get(
        "STRICT_CANONICAL_PAGE_PREVIEW",
        "0",
    )
    == "1"
)

if preview_limit is not None:
    try:
        normalized_preview_limit = int(preview_limit)
    except (TypeError, ValueError):
        errors.append(
            "preview_page_limit is not an integer: "
            f"{preview_limit!r}"
        )
    else:
        if normalized_preview_limit != 3:
            errors.append(
                "preview_page_limit="
                f"{normalized_preview_limit!r}"
            )
        else:
            print(
                "PREVIEW_CONTRACT_MODE=canonical_page"
            )
else:
    if strict_page_contract:
        errors.append(
            "canonical preview-page policy is absent; "
            "the manifest exposes no preview_page_limit"
        )
    elif len(preview_chapters) != 3:
        errors.append(
            "manifest exposes neither preview_page_limit=3 "
            "nor exactly 3 explicitly previewable chapters; "
            f"preview_chapter_count={len(preview_chapters)}"
        )
    else:
        print(
            "PREVIEW_CONTRACT_MODE="
            "legacy_preview_chapters"
        )
        print(
            "WARNING: Current API is chapter-preview based. "
            "This validates the existing 12-scenario contract, "
            "not the final server-defined three-page architecture."
        )'''

text = text[:start] + replacement + text[end:]

###############################################################################
# 2. Prevent the repair script from converting the existing chapter-based E2E
#    contract into a field that the current API does not expose.
###############################################################################

text = text.replace(
    '''test_source = test_source.replace(
    "preview_chapter_count: 3,",
    "preview_page_count: 3,",
)
''',
    '''test_source = test_source.replace(
    "preview_page_count: 3,",
    "preview_chapter_count: 3,",
)
''',
)

old_assertion_conversion = '''test_source = test_source.replace(
    \'''  expect(manifest.chapters.filter((chapter) => chapter?.is_preview === true)).toHaveLength(DRACULA_RELEASE_CONTRACT.preview_chapter_count);
\''',
    \'''  const previewPageLimit =
    manifest.preview_page_limit
    ?? manifest.book?.preview_page_limit
    ?? manifest.preview?.page_count;

  expect(previewPageLimit).toBe(
    DRACULA_RELEASE_CONTRACT.preview_page_count,
  );
\''',
)
'''

new_assertion_conversion = '''test_source = test_source.replace(
    \'''  const previewPageLimit =
    manifest.preview_page_limit
    ?? manifest.book?.preview_page_limit
    ?? manifest.preview?.page_count;

  expect(previewPageLimit).toBe(
    DRACULA_RELEASE_CONTRACT.preview_page_count,
  );
\''',
    \'''  const previewChapters = manifest.chapters.filter(
    (chapter) => (
      chapter?.is_preview === true
      || chapter?.is_free_preview === true
    ),
  );

  expect(previewChapters).toHaveLength(
    DRACULA_RELEASE_CONTRACT.preview_chapter_count,
  );
\''',
)
'''

if old_assertion_conversion in text:
    text = text.replace(
        old_assertion_conversion,
        new_assertion_conversion,
        1,
    )

###############################################################################
# 3. Add a final normalization immediately before the E2E file is written,
#    making the patch safe even if an earlier transformation already ran.
###############################################################################

write_marker = "write(test_path, test_source)"

normalizer = r'''test_source = test_source.replace(
    "preview_page_count: 3,",
    "preview_chapter_count: 3,",
)

test_source = test_source.replace(
    """  const previewPageLimit =
    manifest.preview_page_limit
    ?? manifest.book?.preview_page_limit
    ?? manifest.preview?.page_count;

  expect(previewPageLimit).toBe(
    DRACULA_RELEASE_CONTRACT.preview_page_count,
  );
""",
    """  const previewChapters = manifest.chapters.filter(
    (chapter) => (
      chapter?.is_preview === true
      || chapter?.is_free_preview === true
    ),
  );

  expect(previewChapters).toHaveLength(
    DRACULA_RELEASE_CONTRACT.preview_chapter_count,
  );
""",
)

'''

if normalizer not in text:
    marker_position = text.find(write_marker)

    if marker_position == -1:
        raise SystemExit(
            "Could not locate E2E write marker."
        )

    text = (
        text[:marker_position]
        + normalizer
        + text[marker_position:]
    )

script_path.write_text(text, encoding="utf-8")

###############################################################################
# 4. Normalize the currently checked-out E2E file too.
###############################################################################

test_path = Path(
    "tests/e2e/earnalism-real-user-journey.spec.js"
)

if test_path.exists():
    test_source = test_path.read_text(
        encoding="utf-8"
    )

    test_source = test_source.replace(
        "preview_page_count: 3,",
        "preview_chapter_count: 3,",
    )

    test_source = test_source.replace(
        """  const previewPageLimit =
    manifest.preview_page_limit
    ?? manifest.book?.preview_page_limit
    ?? manifest.preview?.page_count;

  expect(previewPageLimit).toBe(
    DRACULA_RELEASE_CONTRACT.preview_page_count,
  );
""",
        """  const previewChapters = manifest.chapters.filter(
    (chapter) => (
      chapter?.is_preview === true
      || chapter?.is_free_preview === true
    ),
  );

  expect(previewChapters).toHaveLength(
    DRACULA_RELEASE_CONTRACT.preview_chapter_count,
  );
""",
    )

    test_path.write_text(
        test_source,
        encoding="utf-8",
    )

print("Preview preflight and current E2E contract patched.")
PY

bash -n "$SCRIPT"

node --check "$TEST_FILE"

echo
echo "Preview-related references:"
grep -nE \
  'preview_(page|chapter)_(limit|count)|previewChapters|PREVIEW_CONTRACT_MODE' \
  "$SCRIPT" \
  "$TEST_FILE" \
  | head -n 120

echo
echo "PATCH_COMPLETED"
