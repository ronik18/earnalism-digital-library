# Reuse-only edition validation — local and uncommitted

Base cdd006ce91f98327a1b3de31b856f25e532eff88 remains intact, one commit ahead
of origin/main d79acb1952161cd56395e9bb4d7c1001ceaa69bb. No production writes.

## Contract

Native source ingestion returns READY/UNCHANGED, not the publication contract's
INGESTED/CLEANED. Generation-oriented edition/visual paths do not establish reuse
history. The new pure retained_edition_validation.py executes explicit local
reuse checks, rather than converting READY or persisting workflow statuses.
The canonical evaluator and runtime remain unchanged.

Independent registry acceptance/revocation/expiry, IN delivery/Reading Pass/cover
uses, exact component hashes and authorization are required. Actual source bytes
must reproduce reviewed full ordered chapter bodies/gaps/tail, canonical chapter
metadata and checksum inventory. Existing covers are decoded and checked against
exact source/delivery hashes, dimensions and aspect ratio. Independent retained
visual reviews remain preparation evidence, not final publication QA.

## Newly executed results

| Edition | Phase 4 | Phase 5 | Phase 6 | Final publication QA |
|---|---|---|---|---|
| The Principles of Scientific Management, PG6435 | CLEANED | READY_FOR_REVIEW | PARTIAL_DRY_RUN | UNVERIFIED |
| My Life and Work, PG7213 | CLEANED | READY_FOR_REVIEW | PARTIAL_DRY_RUN | UNVERIFIED |
| The Gift of the Magi, retained legacy edition | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

Actual official-source GET/adapter observations UTC:
Scientific 2026-10-10T18:48:07.701327+00:00; My Life 2026-10-10T18:48:11.614500+00:00.
Source SHA256 respectively:
1f504a9abe674ee616f13bf1db66ec25cbb1be0ff5fd9bfe70ab8593aa08a3b2
f01c925ba4a15ccc6a5aa706418cf94149ddd7d8f390c65d132b8675435b00cf.
Canonical local publication-manifest checksums respectively:
c544e0d4908a4a0058a30e4b3fb3852137d8476074a0a8eb284b73f6a05836e9
6f95ce27b0f8ab76f827ba16ef63d3ff46db6dab0a2c5c2325819d744a73ad79.
These are NOT production Reader manifest IDs. Prior production Reader identities
68e1c58e915f9b2a5f652c91 (78 segments) and 5f48e68e388ec093d54c75f0
(174 segments) are inherited retained-integrity-readback findings, not freshly
fetched production evidence. Canonical chapters remain 4 and 20; no regenerated
text. Prior Phase 3 21.35/21.35 retained; no invented original publication year.

Rights, exact-source/chapter fidelity, bound manifest/checksums and existing-cover
technical/retained visual checks PASS for both. Text-only NOT_REQUESTED exception
is supported by actual exposed=false/required_for_reader_release=false manifests;
no audio settings changed. My Life back cover exceeds the policy's 80KiB card
TARGET: OVER_TARGET recorded, no invented hard gate or cover replacement.

Phase 6 remains PARTIAL_DRY_RUN because policy also requires current normal-zoom
browser smoke, build/audio safety and performance guardrail where available.
Source/art QA_PASSED is not final exact publication QA. READY_FOR_RELEASE = 0.
First two still require those release checks, final exact package QA/binding and
authorized paid-Reader acceptance. No fabricated reviews or approval receipts.

## Gift digest provenance

Targeted investigation found content/books/the-gift-of-the-magi/raw/source.txt:
11,389 bytes, SHA256 c85f9eb55e492e899f6525ce2070e1ff5ee607c7a68c6f52c248bf7f30839f95.
Whitespace-folded narrative equals the retained canonical chapter; import chapter
content SHA256 be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e
is exact. Approved legacy origin digest
490b76d444db0d952f5286f60c4ec2834ab91731d47e42dc94a3639d9183d295
remains unreproduced. Raw introduced bc7c8b44c; controlled evidence faf85878f,
amended 94d9865d4. No retained bytes or documented deterministic transform to
that digest found. Do not substitute a sourceSha256 claim for actual bytes.
Details: /tmp/earnalism-paid-reader-programme-20261010/gate-01-gift-retained-raw-investigation.json.

## Qualification and scaling

34 new adapter tests + 69 existing rights/manifest tests = 103 PASS.
Initial fixture execution: 25 PASS / 2 FAIL (fixture evidence_sha256 incorrectly
scalar; corrected to existing list-valued contract without weakening a gate).
Independent gate_01 review found no bypass; requested reviewed-gap/tail guards,
proof-tampering regression and observation provenance, all included.
Canonical evaluator test confirms blocker remains "QA pass is required."

Preserved R shortlist has 35 books, 29 prior exact-reference matches; excluding
three pilots leaves 26 other potential candidates for this method, NOT 26 passes.
No catalogue rescan, registry backfill, production writes or artifact changes.
Each requires its own source bytes and supported independently bound evidence.

Next authorization: scoped local commit after review; separately obtain actual
final release/browser and authorized sandbox paid-access evidence. No book
publication is presently justified. Exact local check:

`PYTHONPATH=backend /tmp/earnalism-lease-readonly.pYoBkn/venv/bin/python -m pytest backend/tests/test_retained_edition_validation.py backend/tests/test_rights_decision_gate.py backend/tests/test_publication_manifest.py -q`
