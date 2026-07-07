# Sprint Go-Live Dashboard

## PR87

- Luxury UX source package: validated locally.
- Lighthouse: performance 96, LCP 2803ms, accessibility 100, SEO 100.
- Cover audit: PASS, 0 typography-only customer-facing covers.
- Audio safety: PASS, no unapproved audio controls by unit coverage and visual smoke.
- Bengali reader-only/audio-hidden state: preserved; no production mutations rerun.
- Sarvam/Bengali audio: not run; provider lane remains paused.
- Preview: Vercel ignore fix is ready; preview requires commit/push and rerun. Use latest Vercel CLI through `npx --yes vercel@latest` if manual inspection is needed.

## Next Action

Commit and push the PR87 blocker rescue patch, then verify Vercel preview and required GitHub checks.
## Bengali Audiobook Pilot Endpoint Materialization

- Pilot: `book-2b9853ec52` / `দুই বিঘা জমি`.
- Current source status: narrow backend materialization patch deployed from clean worktree.
- Upload/checksum: PASS.
- Metadata API: PASS.
- Endpoint before deploy: 404.
- Endpoint after deploy: 206.
- Reader manifest audio: enabled for pilot only.
- Non-pilot Bengali sample: audio hidden, endpoint 404.
- Root cause: deployed backend truth gate cannot materialize the approved DB audio record because production source/deploy lacks the narrow materialization path and DB metadata lacks top-level source/provenance hashes.
- Fix summary: `audio_materialization_slugs=["book-2b9853ec52"]`, runtime audio exposure and controlled artifact evidence fallback for that slug only, DB/admin audio URLs preserved, estimated/unknown sync blocked.
- Backend deploy: PASS (`9f39fb50-26e1-47a7-b339-91fe217cff3c`).
- Browser gate: BLOCKED because production frontend bundle is stale and does not render reader-manifest audio controls.
- Next gate: deploy/merge frontend bundle with Reader manifest-audio support, then rerun metadata/browser-only resume.
