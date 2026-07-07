# Earnalism Book Import Instructions

When asked to import books, use the existing Earnalism book upload/admin API.

Always:
- Read book_import_manifest.json unless another manifest path is provided.
- Download only legally cleared sources.
- Strip repository/license/trademark/source boilerplate from reader-facing content.
- Validate commercial-use rights before upload.
- Upload only passing books.
- Use draft mode by default.
- Keep source URLs and rights evidence internal/admin-only.
- Do not include source repository names or URLs in reader-facing metadata unless legally required.
- Print uploaded IDs/slugs and skipped-book reasons.

# Earnalism Autonomous Intelligence Layer

Before book production, audiobook, catalog, publishing, or UX release work:

- Read the active files under `internal/earnalism_intelligence/`.
- Preserve release-gate truth and fail closed when evidence is incomplete.
- Do not expose unapproved audio, stale audio URLs, fallback audio, or estimated sync as release-ready.
- Do not repeat failed provider/settings/text-hash attempts; use the provider memory and campaign ledgers.
- Prefer the cheapest safe next action that advances customer-facing availability or release confidence.
- Persist every material learning in the decision ledger, sprint learnings, title history, and relevant campaign state.
- Produce the next exact command or next generated prompt at the end of every run.

## Bengali Audiobook Completion Campaign

Continue Bengali audiobook work from the saved campaign state:

- Campaign policy: `internal/earnalism_intelligence/bengali_audiobook_campaign_policy.md`.
- Campaign state: `internal/earnalism_intelligence/bengali_audiobook_campaign_state.json`.
- Campaign queue: `internal/earnalism_intelligence/bengali_audiobook_campaign_queue.json`.
- Campaign ledger: `internal/earnalism_intelligence/bengali_audiobook_campaign_ledger.jsonl`.

Non-negotiable Bengali audiobook release gates:

- Listening score must be `>= 9.2`, confidence `>= 0.90`, with no fatal red flags.
- Fatal red flags are robotic texture, mechanical cadence, list-reading rhythm, choppy joins, and fallback TTS.
- Objective gates remain strict: content/TOC, rights, covers, ASR/manuscript `>= 9.7`, first/last words, no missing/duplicated/reordered content, measured paragraph/stanza sync or better, no estimated sync, upload/checksum, metadata, endpoint, browser gate, and empty blocker list.

Campaign rules:

- Never publish based on one isolated high-scoring sample.
- Do not generate all 31 Bengali audiobooks before one full pilot passes every gate.
- Do not damage the existing Bengali reader-only/audio-hidden state.
- Do not run paid provider calls without explicit campaign approval and budget env vars.
- If automated TTS plateaus, create human narration or licensed audio import packets instead of looping.
