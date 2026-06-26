# Homepage Social And Pipeline Visual Audit

Status: `PASS_WITH_OWNER_REVIEW_RECOMMENDED`

## Kshudhita / Pipeline Treatment

Exact repository spelling: `Kshudhita Pashan`

Bengali title used in code: `KSHUDHITA_PASHAN_PIPELINE.titleBn`

Public title used in the homepage pipeline card: `The Hungry Stones`

Kshudhita Pashan cover status: `OWNER_PROVIDED_COVER_READY`

Owner-provided Kshudhita Pashan front and back cover art is now committed as optimized WebP assets for the pipeline preview:

- `frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp`
- `frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-back.webp`

The homepage uses the real front cover as the primary visual object and keeps the back cover as a subtle secondary layer. The candidate remains pipeline-only.

Pipeline safety:

- No public reading CTA.
- No payment CTA.
- No audio CTA.
- No public reader route claim.
- No public audiobook claim.

## Social Icon Integration

No fake social links are rendered.

Homepage social links are filtered through `normalizeSocialUrl`. If owner-reviewed profile URLs are configured, refined icon links appear with accessible labels, `target="_blank"`, and `rel="noopener noreferrer"`. If URLs are missing, the homepage renders an owner-review note instead of empty or broken icons.

## Visual Result

- Kshudhita Pashan is visually secondary to Dracula.
- Pipeline typography is no longer oversized.
- The actual owner-provided cover art supports curiosity without making the title public or payable.
- Social trust is present without visual noise or fake proof.

## Remaining Owner Inputs

- Configure official social profile URLs before showing icons as live public links.
