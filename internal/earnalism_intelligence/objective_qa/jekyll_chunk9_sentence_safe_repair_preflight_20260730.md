# Jekyll `chunk_0009` sentence-safe repair preflight

Status: **PREFLIGHT PASS — no provider call; audio remains hidden**

The validated parent is the already-repaired 92-unit Charon candidate, not the
older baseline. Its manifest SHA-256 is
`616080b550edecc4320812ea09c0e0cf3f4f5afd96210247b5f1e6e3477a4632`.
The existing `chunk_0036` replacement remains bound to audio SHA-256
`d7d83110d869e2d40c59855e2d3e2252e9b642b6fa14e9790591cbb6c0d8702c`
and must remain byte-identical.

## Exact defect

`chunk_0009` is bound to source SHA-256
`24a85dbb2f4184ea9ffb86599c65777d5fcfccc343d3fdb6077884aa5c9557de`
and current audio SHA-256
`e2a34a5ccfc5bb78e121fdd32ff821e7f907afe7203521fc08517c9904c91ebf`.
The audio omits these 16 canonical tokens:

> obligation beyond the payment of a few small sums to the members of the doctor’s household

Measured source-blind timestamps bind the defective audio window from
`30.10s` at the clause-start word “and” to `31.92s` before the next sentence’s
“This”. There is no hidden audio interval containing the missing text.

## Sentence-safe repair design

Do not resynthesize the 1,542-character chunk. Make one private Google Charon
request at the local `en-GB`, rate `0.94`, pitch `0.0` settings using this
192-character context:

> without further delay and free from any burthen or obligation beyond the payment of a few small sums to the members of the doctor’s household. This document had long been the lawyer’s eyesore.

Source-blind ASR and forced alignment must recover the complete context. Then
extract only the exact clause beginning “and free” and ending “household.”,
including its natural terminal pause. Replace only the verified clause window
inside decoded `chunk_0009`; blind time-only cutting is forbidden.

The child candidate may differ from its parent only at index `9`. Relative to
the original root candidate its complete change set must be `[9, 36]`. The
other 91 files, including repaired `chunk_0036`, must match the preflight’s
preservation-set SHA-256
`ccebbbe37ff877cddb189ee459302e14b863b4514e20f22d75597b67c08f4920`.

## Cost and lock scope

The bounded estimate is 192 billable characters, or `$0.005760` at the
existing `$30 / million characters` planning rate. Projected title spend is
`$3.523530`; projected sprint spend is `$18.729620`.

Any later executor must acquire only:

`sprint1_jekyll_google_chunk9_sentence_safe_repair:jekyll-and-hyde:chunk_0009`

It must require the explicit chunk-9 approval and budget-stop environment
gates, make at most one context-window provider call, and restore
`paid_tts.lock` byte-for-byte. This preflight only read the lock; it did not
write or mutate it.

## Required evidence after repair

- Fresh strict objective evidence for changed `chunk_0009`.
- Fresh objective evidence for the already-repaired `chunk_0036`.
- Full-title ASR/source `>= 9.7`, coverage `>= 0.98`, exact ordered content,
  first/last words, and measured paragraph-or-better sync.
- Independent adjudication for the known ASR-sensitive `chunk_0045` and
  control `chunk_0071`.
- Fresh listening judgments for both changed units under
  `platform_audiobook_acceptance_v4_89`: every ordinary dimension and overall
  score `>= 8.9`, anti-robotic and anti-choppy `>= 9.2`, confidence `>= 0.90`,
  and no fatal flags.

Package-v2 eligibility remains false until the resulting full-title candidate
passes those gates and gains immutable package evidence, primary and DR
receipts, controlled release truth, Range behavior, endpoint validation, and
browser playback proof.

No synthesis, audio modification, upload, publication, release mutation, or
public exposure occurred.
