# The Tell-Tale Heart private editorial cover candidate

## Decision

This is a private, pending-review front/back candidate for **The Tell-Tale Heart** by **Edgar Allan Poe**. It is not canonical, has not been exposed publicly, and cannot change reader or audiobook release truth.

## Source and rights

- Source artwork: Odilon Redon, *The Tell-Tale Heart* (1883), charcoal on brown paper.
- Rights status: Public Domain Mark 1.0, bound to `source_rights_evidence.json`.
- Exact source SHA-256: `075f2c285d2f546076e8f1f50f03da43184f4c51d47746fbabc2358f9d37ed56`.
- Composition: deterministic Pillow crop, tonal treatment, borders, and catalog text overlay.
- AI-generated imagery: no.
- Placeholder art: no.

## Technical checks

- Front: 1600 × 2400 JPEG, `474742edf3427ac414565c05b170cb83e855b223951be3ed22cc597ddf6f673d`, 738942 bytes.
- Back: 1600 × 2400 JPEG, `540a24ebdfef56fefe99f23aba4166c3ada20dd421132480eaf3546b07b8934d`, 349471 bytes.
- Exact canonical title/author and canonical short description used.
- Geometry validation: zero text-box overlaps; all text remains inside the 120 px safe margin.
- Both files pass the backend cover validator and remain below the 4 MiB admin limit.
- Both controlled-publication mirrors remained byte-for-byte unchanged.

## Pending review

Owner/editorial review must approve the finished pair before private admin upload. An authenticated upload must remain `ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW`; canonical promotion is a separate, hash-bound decision.

## Next exact command

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/cover_candidates/the-tell-tale-heart/candidate_manifest.json >/dev/null
```
