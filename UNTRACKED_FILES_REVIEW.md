# Untracked Files Review

Generated: 2026-06-19

## Commands Run

```bash
git status --short --untracked-files=all
git ls-files --others --exclude-standard
```

After identifying local review-bundle artifacts, `.gitignore` was updated and the commands were run again.

## Initial Inventory Summary

The initial untracked inventory was very large because two local review/export bundle directories contained copied repository snapshots.

| Item | Git-visible untracked file count | Disk size | Classification | Reason | Action |
| --- | ---: | ---: | --- | --- | --- |
| `earnalism-main-line-review-bundle/` | 6,774 | 1.1G | IGNORE | Local review/export bundle with copied source, command outputs, generated artifacts, audio/text outputs, and report snapshots. Not production source. | Added to `.gitignore`; do not commit. Safe to delete only after human confirmation. |
| `earnalism-review-bundle-minimal/` | 220 | 2.8M | IGNORE | Local minimal review/export bundle with copied source and command outputs. Not production source. | Added to `.gitignore`; do not commit. Safe to delete only after human confirmation. |
| `EDITION_GENERATOR 2.md` | 1 | 8K | DELETE | Byte-for-byte duplicate of tracked `EDITION_GENERATOR.md`. | Do not commit; delete after review. |
| `PHASE5_VALIDATION_REPORT 2.md` | 1 | 4K | DELETE | Byte-for-byte duplicate of tracked `PHASE5_VALIDATION_REPORT.md`. | Do not commit; delete after review. |
| `backend/tests/test_edition_generator 2.py` | 1 | 16K | DELETE | Byte-for-byte duplicate of tracked `backend/tests/test_edition_generator.py`. | Do not commit; delete after review. |
| `scripts/edition_generator 2.py` | 1 | 8K | DELETE | Byte-for-byte duplicate of tracked `scripts/edition_generator.py`. | Do not commit; delete after review. |

The two review-bundle directories contain many more physical files than Git initially showed because existing ignore rules already excluded nested `output/**` and similar generated artifacts inside those bundles. A direct file count showed `30,862` files under both bundle directories combined.

## Post-Ignore Inventory

After adding the bundle-directory ignore rules, the visible untracked set is:

```text
EDITION_GENERATOR 2.md
PHASE5_VALIDATION_REPORT 2.md
UNTRACKED_FILES_REVIEW.md
backend/tests/test_edition_generator 2.py
scripts/edition_generator 2.py
```

Classification:

| Item | Classification | Reason | Action |
| --- | --- | --- | --- |
| `EDITION_GENERATOR 2.md` | DELETE | Byte-for-byte duplicate of tracked `EDITION_GENERATOR.md`. | Do not commit; delete after review. |
| `PHASE5_VALIDATION_REPORT 2.md` | DELETE | Byte-for-byte duplicate of tracked `PHASE5_VALIDATION_REPORT.md`. | Do not commit; delete after review. |
| `backend/tests/test_edition_generator 2.py` | DELETE | Byte-for-byte duplicate of tracked `backend/tests/test_edition_generator.py`. | Do not commit; delete after review. |
| `scripts/edition_generator 2.py` | DELETE | Byte-for-byte duplicate of tracked `scripts/edition_generator.py`. | Do not commit; delete after review. |
| `UNTRACKED_FILES_REVIEW.md` | COMMIT | This is the requested review artifact. | Commit only after classification is reviewed. |

The four duplicate files should not be ignored broadly because broad rules for names containing ` 2` could hide legitimate future files.

## `.gitignore` Decision

Added safe local-artifact ignore rules:

```gitignore
# Local review/export bundles
earnalism-main-line-review-bundle/
earnalism-review-bundle-minimal/
```

Confirmed with:

```bash
git check-ignore -v earnalism-main-line-review-bundle/catalog-audit.txt earnalism-review-bundle-minimal/git-status.txt
```

## Safety Checks

- No `.env`, secret, credential, token, virtualenv, `node_modules`, build/dist/cache, log, or binary media file is recommended for commit.
- No files were deleted.
- No files were staged or committed.
- `.gitignore` is modified but not staged.
- `UNTRACKED_FILES_REVIEW.md` is untracked and not staged.

## Recommended Next Step

After you review this classification:

```bash
rm "EDITION_GENERATOR 2.md" \
   "PHASE5_VALIDATION_REPORT 2.md" \
   "backend/tests/test_edition_generator 2.py" \
   "scripts/edition_generator 2.py"
```

Optionally remove the review bundles if you no longer need their local evidence snapshots:

```bash
rm -rf earnalism-main-line-review-bundle earnalism-review-bundle-minimal
```
