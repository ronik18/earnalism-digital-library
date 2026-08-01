# Earnalism Growth Tracking Plan

Generated: 2026-07-07T18:30:00Z

## Tracking Rule

Use first-party events by default. Do not load third-party tracking unless enabled by environment/config, such as `REACT_APP_ENABLE_POSTHOG=true`.

## Core Events

- `homepage_cta_click`: CTA label, destination, language context.
- `season_1_shelf_view`: shelf id, shelf title, release-truth group, visible book count.
- `library_filter_used`: filter type, selected value, results count.
- `book_detail_view`: slug, language, reader status, audiobook approved true/false.
- `reader_start`: slug, language, source surface.
- `listen_start`: slug, provider, approved gate version; fire only for approved audio.
- `listen_30_seconds`: slug, elapsed, playback speed.
- `listen_3_minutes`: slug, elapsed, playback speed.
- `audio_completion`: slug, completion percent, duration.
- `signup`: source route, campaign, language interest.
- `share_click`: slug, surface, channel.
- `return_visit_7d`: anonymous cohort or user id where consent allows.

## Funnel Views

1. Homepage to library.
2. Library to book detail.
3. Detail to reader.
4. Reader to listen start where approved.
5. Reader/listen to signup.

## Paid Media Guardrails

- No ad spend before events are visible in logs/dashboard.
- No listen_start optimization unless approved audiobook endpoints exist.
- Separate Bengali reader-only campaigns from audiobook campaigns.
- Use title-specific landing pages so search ads match customer intent.
- `a-ghost-story` paid listen ads require a final production browser/manifest route check because the local controlled-publication assets are approved but guessed public API audiobook/manifest paths returned 404 in the launch activation probe.

## Privacy

- No source repository URLs in customer-facing analytics labels.
- No sensitive manuscript/source metadata in event payloads.
- Respect opt-out and avoid third-party scripts by default.

## Season 1 Release-Truth Event Rules

- `listen_start`, `listen_30_seconds`, `listen_3_minutes`, and `audio_completion` may fire only for live approved audiobooks.
- Coming-soon audiobook candidates may emit `book_detail_view`, `reader_start`, `share_click`, and `season_1_shelf_view`, but not listen events.
- Reader-first Bengali titles should include `audio_hidden_reason=quality_gates_pending` only internally; do not show customer-hostile missing-audio language.
