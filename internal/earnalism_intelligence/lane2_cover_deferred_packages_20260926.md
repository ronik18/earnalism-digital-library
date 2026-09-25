# Lane 2 cover-deferred publication packages

Date: 2026-09-26

Owner decision: cover work is deferred. These packages remain private and must
not be served until cover provenance is supplied and the normal publication
gate is rerun. The package edits below remove unresolved cover URLs from the
public metadata and set explicit non-serving flags; they do not alter source
text, rights evidence, chapter payloads, entitlement rules, or audio state.

| Title | Slug | Package state | Source/text evidence | Cover state | Exact remaining issue |
| --- | --- | --- | --- | --- | --- |
| Alice's Adventures in Wonderland | `alices-adventures-in-wonderland` | `COVER_DEFERRED_NOT_SERVED` | Project Gutenberg source and existing content hashes retained | `DEFERRED_NOT_SERVED` | Cover provenance and publication approval |
| Pride and Prejudice | `pride-and-prejudice` | `COVER_DEFERRED_NOT_SERVED` | Project Gutenberg source and existing content hashes retained | `DEFERRED_NOT_SERVED` | Cover provenance and publication approval |
| Frankenstein | `frankenstein` | `COVER_DEFERRED_NOT_SERVED` | Historical import evidence retained; source-layer reconciliation still required | `DEFERRED_NOT_SERVED` | Reconcile historical-import provenance/manifest binding, then cover provenance and publication approval |

## Deterministic evidence bindings

These hashes are the post-change package inputs used for review. The existing
chapter and source evidence files are not rewritten.

| Slug | `source_evidence.json` | `public_book.json` | `reader_manifest.json` |
| --- | --- | --- | --- |
| `alices-adventures-in-wonderland` | `62b59134df986b6deaa654c0a1c6012250260cd60d0fa35ea8ed3cefa4117384` | `51481f2b45c62cd3902ed79c1caa6fb8e6af400d567f3458499c86eb647f1484` | `ae5b59118890b75403bb24f4a77f9d2ca9307d6a85a1c4dd06c30234ce837796` |
| `pride-and-prejudice` | `d4a5487f1f345401943306b8d556321982998c0528dfae19bed961bcb87040ac` | `d2de263f8421cfbc5cb681d9fc653582db211b00a1c11c13d3afc9638a49d533` | `3143d06f52799d583d8bc241ebf200295e9f9428aae8d09285cb7a7494b95dac` |
| `frankenstein` | `053ee21353bb348aca0e8d360252ed144ce9d7d0659004b292187088e33810c1` | `f232ec1a257ff3172f3b05fb98925b0440830189ad3566f2ba6243684372e4ce` | `2bcfb02c4180c4361f242bcd2ec7f36189c4bcce07b093713daaa215168c3915` |

Validation: all three edited JSON files parse successfully. No title is
exposed, added to the sitemap, enabled for checkout, or enabled for audio.
