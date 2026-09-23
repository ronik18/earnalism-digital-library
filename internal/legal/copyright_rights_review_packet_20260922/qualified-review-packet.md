# Copyright / Rights qualified-review packet

> This is an evidence package, not legal advice, a rights decision, a publication approval, or a release instruction.

## Binding and scope

- Assessed technical candidate: `2c70f35ad2810da19dc36017fc0ae834899cb4c0` (tree `5397b78b4475bdef5a22f52ff1125a4fe4e77dca`).
- Production-surface fingerprint: `314c040f16aaf12931b1b340ae1d222bb87037e6291f1e3752173b98365326d0`.
- Generator revision: `2c70f35ad2810da19dc36017fc0ae834899cb4c0` (tree `5397b78b4475bdef5a22f52ff1125a4fe4e77dca`).
- Full repository-controlled inventory: 163 titles and 1261 component rows in `copyright-rights-inventory.json`.
- The four-title pilot remains the review priority; all other controlled titles are inventory-only and remain held.
- Customer/accounting acceptance, rights acceptance, publication activation, deployment, and production mutation are outside this packet.

## Technical fail-closed evidence

| Gate | Evidence | Result |
| --- | --- | --- |
| Reader exposure | `data/controlled_launch.json` | `False` |
| Audio exposure | `data/controlled_launch.json` | `False` |
| Live title allowlist | `data/controlled_launch.json` | `[]` |
| Accepted rights records | `backend/data/rights_decision_registry.json` | `0` |
| Root/backend parity | controlled-launch SHA-256 bindings | `True` |
| Hold evidence | registry disposition bindings | `PASS` |

## Pilot title disposition package

| Title | Text | Covers | Other assets | Jurisdictions | Release status |
| --- | --- | --- | --- | --- | --- |
| A Ghost Story (`a-ghost-story`) | EVIDENCE_READY_FOR_REVIEW | HOLD | HOLD | IN, US, GB, CA, AU, DE, AE, BD, SG, SA | `HOLD` |
| রাধারাণী (`radharani`) | EVIDENCE_READY_FOR_REVIEW | HOLD | HOLD | IN, US, GB, CA, AU, DE, AE, BD, SG, SA | `HOLD` |
| The Tell-Tale Heart (`the-tell-tale-heart`) | EVIDENCE_READY_FOR_REVIEW | HOLD | HOLD | IN, US, GB, CA, AU, DE, AE, BD, SG, SA | `HOLD` |
| যুগলাঙ্গুরীয় (`yugalanguriya`) | EVIDENCE_READY_FOR_REVIEW | HOLD | HOLD | IN, US, GB, CA, AU, DE, AE, BD, SG, SA | `HOLD` |

## Jurisdiction material for qualified review

The following India materials are official legal inputs, not automated legal conclusions:

- [Copyright Act, 1957, Chapter III (protected work categories)](https://copyright.gov.in/Copyright_Act_1957/chapter_iii.html)
- [Copyright Act, 1957, Chapter V (terms, including sections 22 and 27)](https://copyright.gov.in/Copyright_Act_1957/chapter_v.html)
- [Copyright Rules, 2013](https://www.copyright.gov.in/Copyright_Rules_2013/index.html)

For the remaining pilot countries, the reviewer must determine the applicable law, governing facts, permitted acts, territory, licence effect, and any notice obligation. A source label is not treated as global clearance.

## Required reviewer decisions

- Is the underlying text authorised for each intended act and territory?
- Is the exact delivered transcription, edition, translation, or adaptation authorised?
- Are cover and other artistic assets independently authorised?
- Are any licence conditions, notices, and attribution obligations satisfied?
- Is commercial digital distribution within the documented scope?
- Does each proposed decision contain the exact component hashes, operator identity, uses, territories, validity, evidence, and reviewer attribution required by backend/rights_decision_gate.py?
- Do unresolved facts require the title to remain HOLD?

## Current conclusion

`COPYRIGHT_EVIDENCE_INCOMPLETE` — The repository records zero accepted rights decisions, all four pilot dispositions are HOLD, and component provenance/territory/licence facts remain incomplete for qualified review.

No component is ACCEPTED by this packet. Each title stays HOLD until an authorised human reviewer supplies a hash-bound decision record under the repository rights-decision schema.
