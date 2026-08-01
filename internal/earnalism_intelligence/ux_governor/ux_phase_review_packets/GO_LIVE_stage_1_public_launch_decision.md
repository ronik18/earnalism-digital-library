# GO LIVE Stage 1 Public Launch Decision

Generated: 2026-07-11T02:03:44+05:30
Owner decision evaluated: `APPROVE_GO_LIVE_WITH_AUDIO_LIMITATIONS_AND_DEFER_BN_066_PUBLIC_AUDIO`
Evaluated main commit: `cafa4d8d2c03a8d0c4a7f3f9c65fee06855d2c48`

## Decision

`GO_LIVE_BLOCKED_BN_066_PUBLIC_AUDIO_EXPOSURE`

The production library, reader, Bengali slideshow, contact, and approved `book-2b9853ec52` audiobook surfaces passed the requested read-only checks. The requested audio-limited go-live sign-off cannot be granted because production currently exposes `bn-066` as an approved audiobook even though Stage 3D leaves it private and not release-ready.

Production may remain online, but launch closeout and any marketing claim that release truth is fully enforced must stay on hold until the `bn-066` public audio state is removed and revalidated.

## Main And Pull Request Status

- Latest eight `main` runs inspected were completed successfully; none was failed, cancelled, or in progress.
- Latest production observer: `Production monitoring`, success, commit `cafa4d8d`, <https://github.com/ronik18/earnalism-digital-library/actions/runs/29119094687>.
- Merge-run checks at `cafa4d8d` passed: regression suite, GO LIVE regression gate, Railway deploy, Vercel frontend deploy, production canary, and k6 production smoke.
- PR #91 is merged at `cafa4d8d`: <https://github.com/ronik18/earnalism-digital-library/pull/91>.
- Duplicate PR #92 was closed without merge and its branch was not deleted: <https://github.com/ronik18/earnalism-digital-library/pull/92>.

## Production Route And UX Validation

The following routes rendered on desktop and mobile without horizontal overflow:

- `/`
- `/library`
- `/book/book-2b9853ec52`
- `/reader/book-2b9853ec52`
- `/book/a-ghost-story`
- `/reader/a-ghost-story`
- `/book/book-d19e96859f`
- `/reader/book-d19e96859f`
- `/contact`
- `/about`
- `/pricing`

Additional `bn-066` routes were inspected specifically for release truth.

The homepage slideshow passed its intended behavior:

- Bengali titles lead the first slide; English classics appear on the second slide.
- Dracula is not the first or dominant slideshow story.
- Autoplay advanced from slide 1 to slide 2 when reduced motion was false and focus was outside the slideshow.
- Previous and next controls both worked, including wraparound.
- The slideshow did not overflow at 390x844, 430x932, or desktop widths.

Contact and brand checks passed:

- `sales@reoenterprise.org` is public.
- `sales@reoenterprise.in` was not found publicly.
- The production header uses the Earnalism tricolor brand asset at `/assets/brand/earnalism-logo-transparent-96.webp`.
- No exact Indian flag was found as the production default.

## Production API Release Truth

| Title | API result | Observed release state | Decision |
| --- | --- | --- | --- |
| `book-2b9853ec52` | Book and reader manifest HTTP 200 | Reader available; manifest-backed approved audio | Approved evidence-gated audiobook |
| `a-ghost-story` | Book and reader manifest HTTP 200 | Reader available; `audio.enabled=false`; no audio assets | Reader-first, audio-hidden |
| `book-d19e96859f` | Book HTTP 404 | No public book/audio state | Fail-closed |
| `bn-066` | Book and reader manifest HTTP 200 | Book metadata says audio unavailable, but reader manifest says `audio.enabled=true` and exposes legacy B2/Cloudinary evidence | P0 release-truth violation |

## bn-066 Blocking Evidence

The contradiction is concrete:

- `/api/books/bn-066` reports `audio_enabled=false`, `audiobook_enabled=false`, `audio_status=NOT_AVAILABLE`, and no public audio URL.
- `/api/reader/book/bn-066/manifest` reports `audio.enabled=true`, provider `b2`, voice `command:bn-IN-TanishaaNeural`, and public sidecar asset URLs.
- `/book/bn-066` renders `Audiobook Approved`, `Listen in Reader`, and `Listening room approved`.
- `/reader/bn-066` renders a Bengali narration control and `Paragraph/Stanza Sync` copy.
- A bounded range request to `/api/reader/book/bn-066/audiobook` returns HTTP 404, so the media endpoint is currently broken rather than safely hidden.
- Main commit `cafa4d8d` includes `bn-066` in `backend/data/controlled_launch.json` `audio_enabled_slugs` and retains legacy B2/Cloudinary audio fields in its packaged `public_book.json`.

This is not authorization to publish the private Sarvam/pooja Stage 2 audio. The private audio remains blocked by Stage 3D ASR language/normalization failure and must not replace the stale legacy assets.

## Required Hotfix Before Sign-Off

1. Remove `bn-066` from root and backend `audio_enabled_slugs` while keeping it reader-live.
2. Remove or neutralize legacy public audiobook fields/assets for `bn-066` in both controlled-publication data trees.
3. Make the reader manifest return `audio.enabled=false`, empty public audio assets, and no Listen-ready evidence for `bn-066`.
4. Preserve the private Stage 2 Sarvam/pooja artifact under internal-only paths; do not upload or publish it.
5. Add regression coverage proving contradictory book/manifest audio truth fails closed.
6. Deploy only the authorized backend/data repair, then recheck the API, Book Detail, Reader, and production DOM before go-live sign-off.

## Lock And Audio Governance

`paid_tts.lock` remains `status=active`, `current_holder=none`, and `allowed_next_holders=[]`. It was read only. No TTS, Sarvam, ASR, upload, publication, release-gate mutation, or paid Listen action ran.

Local commit `b3abe331` remains unpushed and is classified `POST_GO_LIVE_AUDIOBOOK_QA_TOOLING_BACKLOG`. It is not part of the production hotfix authorization.

## Next Owner Decision

Required authorization text:

`AUTHORIZE_GO_LIVE_BN_066_PUBLIC_AUDIO_HIDE_HOTFIX.`

Authorize a source/data-only hotfix that keeps `bn-066` reader-live but removes its public audio allowlist membership, legacy public audiobook assets, Listen CTA, player/narration controls, and audio structured data. Do not publish the private Stage 2 audiobook and do not alter any other title's approved release state.

## Next Exact Command

```bash
curl -sS https://api.theearnalism.com/api/reader/book/bn-066/manifest | jq '{enabled:.audio.enabled,provider:.audio.provider,voice:.audio.voice,url:.audio.url,assets:.audio.assets}'
```
