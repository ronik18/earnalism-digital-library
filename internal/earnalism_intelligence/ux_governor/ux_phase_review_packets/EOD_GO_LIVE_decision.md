# Earnalism EOD Go-Live Decision

Decision: `EOD_GO_LIVE_APPROVED_WITH_AUDIO_LIMITATIONS`
Evaluated: `2026-07-14T09:58:11Z`

## Launch Scope

The public launch is approved for all 32 active Sprint 1 digital readers and the two production-approved audiobooks. This decision does not claim that all Sprint 1 audiobooks are live.

Public audiobooks:

- `book-2b9853ec52`: `APPROVED`, `QA_PASSED`, range `206`.
- `a-ghost-story`: `APPROVED`, `QA_PASSED`, range `206`.

All other active Sprint 1 titles remain audio-hidden unless and until their production release evidence passes. Great Expectations and Jane Eyre remain deferred and excluded from the active Sprint 1 audio target.

## Sredni Vashtar Stretch

Sredni Vashtar passed the bounded reuse-first technical and quality path: ASR/source `9.8426`, first/last PASS, six listening samples at `9.4-9.5`, confidence `0.95`, no fatal flags, measured sync `9.7997`, sidecars PASS, manifest PASS, and checksum-verified B2 package PASS. No new TTS ran and deterministic `10/10` is not claimed.

PR #121 merged the release package as `b337300763b874b434938ee09519208512be34bb`. Three Railway backend deploy attempts did not reach production; the final backend-root archive upload returned HTTP `500`. Production therefore remains correctly fail-closed with `audio.enabled=false` and audiobook proxy `404`. Sredni is not counted as public or YES+YES.

## Release Truth

- Active readers: `32/32` public and renderable.
- Public audiobooks: `2/32`.
- Sprint 1 scoped storage bypass: contained; `135/135` reviewed URLs inaccessible and zero reachable Sprint 1 direct URLs.
- Stale Sprint 1 runtime public audio references: removed.
- Hidden sampled manifests: disabled with empty provider, voice, URL, and assets; proxies return `404`.
- No static `/audio` fallback, browser speech fallback, word-level sync claim, non-approved `AudioObject`, or private frontend audio was introduced.
- `paid_tts.lock`: active, current holder `none`, allowed next holders empty.

## Workflow And UX Evidence

PR #121 regression, GO LIVE, Vercel preview, and full regression checks passed. Main regression, GO LIVE gate, Vercel deploy, and production canary passed. The k6 run completed `18,792/18,792` functional checks with `0%` request failures; catalog and reader p95 targets remain a non-P0 performance backlog.

Desktop and 390/430 px mobile checks covered Home, Library, approved and hidden Book/Reader routes, Contact, About, and Pricing. No horizontal overflow or console errors appeared; the Bengali slideshow and mobile menu worked; approved Listen controls were truthful; hidden titles showed no Listen control; the public contact was `sales@reoenterprise.org` with no `.in` contact address.

## Exact Continuation

```bash
cd /tmp/earnalism-eod-go-live/backend && \
railway up . --path-as-root \
  --project a8533934-35c4-463e-9f43-577a9ac391ee \
  --environment production \
  --service earnalism \
  --ci \
  --message "Retry Sredni Vashtar approved reuse package b337300 from backend root"
```

After a successful deploy, production manifest, proxy range, Book UI, and Reader UI validation are mandatory before changing Sredni to YES+YES.
