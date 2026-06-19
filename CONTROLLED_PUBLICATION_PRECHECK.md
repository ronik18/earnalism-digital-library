# Controlled Publication Precheck

Recommendation: `HOLD_FOR_FIXES`

- Public publishing flags must remain disabled until a separate activation prompt.
- Approved Tier A publication list is empty in Phase 13 evidence.
- Tier B items must remain India/region-gated.
- Tier C items must remain blocked.
- First-batch source evidence must be real before publication.
- Payment/revenue flow needs controlled Razorpay test-mode smoke.
- `APPROVED_TO_PUBLISH.md` must exist and pass `npm run controlled-publication:precheck` before any publication phase.
- Payment smoke evidence must be attached to every approved item before controlled publication.
- Rollback plan must be confirmed with the release operator.
