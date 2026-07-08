# Release-Gate UX Policy

Audiobook UI must fail closed.

Rules:
- No audio controls unless manifest and endpoint evidence prove approval.
- No unapproved audio URLs.
- No stale audio.
- No browser/system speech fallback presented as an audiobook.
- No A Ghost Story default audio probe.
- Bengali reader-only titles stay audio-hidden.
- `book-2b9853ec52` can show audio only when manifest and endpoint pass.
- Paragraph/stanza sync customer copy is: section-following narration.
- Never claim word-level sync for paragraph/stanza sync.
