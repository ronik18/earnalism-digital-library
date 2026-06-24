# Audiobook Narration Editorial Policy

Status: `INTERNAL_POLICY`
Default narration mode: `premium_audiobook`
Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`

## Source Fidelity Text

Source fidelity text is the preserved source or sync text used for audit, sentence IDs, alignment, and rights review. It may contain original headings, diary labels, editorial notes, markdown-like Gutenberg formatting, source punctuation, asterism separators, and other paratext.

Source fidelity text must remain available in:

- `full_chapter_sync_source_with_ids.txt`
- `sentence_map.json` as `source_text`
- sync manifests used for manual alignment review

## Premium Narration Text

Premium narration text is the text intended for a narration provider. It should preserve story meaning and literary order while removing or transforming source formatting that weakens audiobook UX.

Premium narration text must not contain:

- sentence ID markers
- source comments
- markdown or Gutenberg formatting
- asterism separators
- internal release notes
- metadata-only paratext such as "Kept in shorthand."

## Narration Decisions

Every source sentence receives a `narration_decision`:

- `speak`: narrate the cleaned source text as story content.
- `transform`: narrate a faithful audiobook form of the source text.
- `metadata_only`: preserve the source text for sync and audit, but do not narrate it.
- `silence_pause`: preserve a source break as timing metadata, not spoken words.

## Transformation Rules

- Chapter headings may be made speakable: `CHAPTER I. JONATHAN HARKER'S JOURNAL` becomes `Chapter One. Jonathan Harker's Journal.`
- Diary dates may be made speakable: `3 May. Bistritz.` becomes `May the third. Bistritz.`
- Memorandum notes may be narrated naturally when they carry story meaning, for example `Mem., get recipe for Mina.` becomes `Memorandum: get recipe for Mina.`
- Asterism separators are converted to `silence_pause` metadata.
- Pure editorial/paratactic source notes that do not help the listener, such as `(_Kept in shorthand._)`, become `metadata_only`.
- Transformations must not invent story content, modernize aggressively, or remove narrative meaning.

## Dracula Chapter 1 Examples

| Source ID | Source Fidelity Text | Premium Narration Text | Decision |
| --- | --- | --- | --- |
| `s001` | `CHAPTER I. JONATHAN HARKER'S JOURNAL` | `Chapter One. Jonathan Harker's Journal.` | `transform` |
| `s002` | `(_Kept in shorthand._)` |  | `metadata_only` |
| `s003` | `_3 May.` | `May the third. Bistritz.` | `transform` |
| `s004` | `Bistritz._--Left Munich at 8:35 P. M....` | `Left Munich at 8:35 P.M....` | `transform` |
| `s084` | `* * * * *` |  | `silence_pause` |

## Future Book Automation

Future audiobook onboarding should run the chapter pipeline in `premium_audiobook` mode by default. Use `full_fidelity` only when the owner explicitly wants every source paratext element spoken.

The pipeline must preserve original source text in sync artifacts, write clean narration text for generation, and expose every editorial decision in `sentence_map.json` for human review.
