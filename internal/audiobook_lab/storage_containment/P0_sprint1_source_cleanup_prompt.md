# P0 Remove Sprint 1 Unapproved Direct Audio References From Public Source

## Prompt ID

`P0_REMOVE_SPRINT1_UNAPPROVED_DIRECT_AUDIO_REFERENCES_FROM_PUBLIC_SOURCE`

## Execution Gate

Do not execute this cleanup until `sprint1_scoped_containment_execution_results.json` reports `SPRINT1_STORAGE_BYPASS_CONTAINED`. That containment gate now passes, but source cleanup remains separately owner-gated and is not authorized by the storage-containment decision.

## Goal

After retention-first remote containment succeeds, remove stale or unapproved direct Cloudinary/B2 audio and sidecar URLs from Sprint 1 runtime/public source records. Preserve the exact approved proxy-backed packages for `book-2b9853ec52` and `a-ghost-story`.

## Exact Runtime/Public Source Files

- `backend/data/controlled_publications/alices-adventures-in-wonderland/public_book.json`
- `backend/data/controlled_publications/bn-066/public_book.json`
- `backend/data/controlled_publications/nishkriti/public_book.json`
- `data/controlled_publications/alices-adventures-in-wonderland/public_book.json`
- `data/controlled_publications/book-d19e96859f/public_book.json`
- `data/controlled_publications/book-edfcf810c5/public_book.json`
- `data/controlled_publications/book-f5d593e1f4/public_book.json`
- `data/controlled_publications/dsires-baby/public_book.json`
- `data/controlled_publications/muchiram-gurer-jibanchorit/public_book.json`
- `data/controlled_publications/nishkriti/public_book.json`
- `data/controlled_publications/radharani/public_book.json`
- `data/controlled_publications/sredni-vashtar/public_book.json`
- `data/controlled_publications/the-call-of-the-wild/public_book.json`
- `data/controlled_publications/the-cop-and-the-anthem/public_book.json`
- `data/controlled_publications/the-gift-of-the-magi/public_book.json`
- `data/controlled_publications/the-last-leaf/public_book.json`
- `data/controlled_publications/the-masque-of-the-red-death/public_book.json`
- `data/controlled_publications/the-monkeys-paw/public_book.json`
- `data/controlled_publications/the-necklace/public_book.json`
- `data/controlled_publications/the-open-window/public_book.json`
- `data/controlled_publications/the-tell-tale-heart/public_book.json`
- `data/controlled_publications/the-time-machine/public_book.json`
- `data/controlled_publications/the-yellow-wallpaper/public_book.json`

## Required Changes

1. Remove direct unapproved audio and sidecar URLs from public/runtime fields.
2. Keep private retention references only in internal evidence, never in public book records.
3. Preserve reader availability and all non-audio metadata.
4. Preserve approved `book-2b9853ec52` and `a-ghost-story` release state and proxy routes.
5. Keep all other Sprint 1 titles audio-hidden unless their independent release gates pass.
6. Do not add static `/audio/` fallbacks, browser speech, word-level sync claims, or unapproved `AudioObject` data.
7. Do not mutate `paid_tts.lock`.

## Validation

```bash
python3 -m json.tool internal/audiobook_lab/storage_containment/sprint1_scoped_containment_execution_results.json >/dev/null
rg -n 'res\.cloudinary\.com|backblazeb2\.com|audiobook_assets|audio_url' \
  backend/data/controlled_publications data/controlled_publications
pytest -q backend/tests/test_b2_audiobook_routing.py
npm test --prefix frontend -- --watchAll=false --runTestsByPath src/lib/audioReleaseSafety.test.js
git diff --check
```

Production recheck must prove approved proxies return 206, hidden proxies return 404, and no newly exposed Listen control exists.
