# Pather Panchali Audio Repair Requirements

## Current State

- Reader: public, 12 local chapters, clean Bengali text.
- Audio: none approved.
- Clean audiobook text: available.
- Release gate: blocked.
- Paid audition: not run.

## Owner Documents Required

1. A written editorial scope decision confirming either:
   - the 12 chapters are an intentionally complete/abridged Earnalism audiobook edition, with truthful marketing language; or
   - the missing continuation/thirteenth chapter and complete source scope have been obtained and verified.
2. A written commercial audiobook rights/territory decision covering the intended public regions; the existing source note retains a jurisdiction caveat.
3. Approved graphical front and back covers with stable production URLs and usage rights.
4. Final title/edition metadata confirming that the audiobook will not be marketed as the complete work unless completeness is proven.

Classification: `OWNER_DOCUMENT_REQUIRED`.

## Transition to Audition

After all four items pass, set the title to `READY_FOR_REPRESENTATIVE_AUDITION` and run one bounded representative sample. Do not generate full-book audio before that sample passes.

## Next Exact Command

```bash
python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug pather-panchali --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com
```
