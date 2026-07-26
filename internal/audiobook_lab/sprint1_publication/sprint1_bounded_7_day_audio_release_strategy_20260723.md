# Sprint 1 bounded seven-day audiobook release strategy

Status date: 2026-07-23

Scope: all 32 canonical Sprint 1 titles

Policy: fastest safe per-title release; no subjective numeric score is the sole release decision

## Current production truth

The production curated-home payload reports 32 public readers and four public
audiobooks. The current YES+YES audiobook set is:

| Slug | Language |
|---|---|
| `book-2b9853ec52` | Bengali |
| `a-ghost-story` | English |
| `the-open-window` | English |
| `sredni-vashtar` | English |

Twenty-eight titles remain reader-first/audio-hidden: nine Bengali and nineteen
English.

### Remaining Bengali titles

1. `bn-066`
2. `radharani`
3. `nishkriti`
4. `muchiram-gurer-jibanchorit`
5. `book-d19e96859f`
6. `book-f5d593e1f4`
7. `pather-panchali`
8. `devdas`
9. `book-edfcf810c5`

### Remaining English titles

1. `dracula`
2. `frankenstein`
3. `jekyll-and-hyde`
4. `picture-of-dorian-gray`
5. `the-time-machine`
6. `the-call-of-the-wild`
7. `white-fang`
8. `pride-and-prejudice`
9. `the-secret-garden`
10. `alices-adventures-in-wonderland`
11. `the-gift-of-the-magi`
12. `the-tell-tale-heart`
13. `dsires-baby`
14. `the-cop-and-the-anthem`
15. `the-last-leaf`
16. `the-masque-of-the-red-death`
17. `the-yellow-wallpaper`
18. `the-monkeys-paw`
19. `the-necklace`

## Release decision contract

Quality scores remain useful diagnostics, but no aggregate listening score can
compensate for a hard failure. A title is GO only when every item below passes:

1. The canonical title, author, source-rights evidence, text hash, chapter order,
   TOC, and public cover are exact and internally recorded.
2. The synthesis-input manifest proves every canonical paragraph/stanza occurs
   exactly once, in order, with no extra repository, source, or generated text.
3. Independent ASR confirms the manuscript and satisfies the repository's
   objective ASR/manuscript evidence requirement; opening and closing spans match
   exactly, with no missing, duplicated, or reordered passages.
4. Timing is measured from audio/segment evidence at paragraph or stanza
   resolution. Estimated sync and unsupported word-level-sync claims are
   prohibited.
5. The assembled audio has no corruption, clipping, abnormal silence, audible
   boundary clicks, loudness jumps, truncated phonemes, or chapter-order errors.
6. Two independent listening judges evaluate the opening, ending, dialogue,
   emotional, punctuation-heavy, and randomly selected middle passages. Both
   must return a binary **premium-ready** verdict, and Bengali candidates must
   also retain the active repository minimum of `9.2` with confidence `>= 0.90`.
   The number is an additional screen, never the sole release decision. A
   disagreement triggers one bounded repair/audition, not publication.
7. Any robotic texture, mechanical cadence, list-reading rhythm, persistent
   pronunciation error, meaning-changing stress, choppy join, hallucination,
   omission, fallback TTS, or unstable pace/pitch is fatal.
8. The exact model, voice/preset, license/provenance, synthesis parameters,
   source hash, output hashes, and required AI-narration disclosure are bound to
   the delivery manifest. Admin curation cannot waive this gate.
9. The private B2 object checksum matches the approved package. No audio is
   copied into `frontend/public`, `frontend/build`, or another public static
   directory.
10. Metadata and release state agree; direct playback, `HEAD`/range delivery,
    authenticated/private-media binding, production endpoint, and browser player
    pass. The blocker list is empty before Listen is exposed.

If a title fails, it stays public as a reader with audio hidden and receives one
specific repair task. There is no broad retry loop and no release-gate mutation
to make a failed artifact appear ready.

## Provider and title-archetype decisions

Use a small representative audition per archetype, then generate each title
with the lowest-cost provider/voice that earns the binary premium-ready verdict.
Do not execute every provider against every full book.

| Titles/archetype | Primary route | Bounded alternative | Decision notes |
|---|---|---|---|
| `book-d19e96859f`, `book-f5d593e1f4` | Sarvam Bulbul v3, reusing all hash-valid groups | Regenerate only the contaminated final group; Google Gemini TTS only if the repaired assembly fails | These are repair jobs, not full regenerations. |
| `muchiram-gurer-jibanchorit`, `book-edfcf810c5` | Sarvam Bulbul v3 with title pronunciation dictionary | Gemini TTS Bangla audition | Short-title fast lane; bind the exact West Bengali pronunciation verdict. |
| `nishkriti`, `devdas` | Sarvam Bulbul v3 with Sarat Chandra name/term lexicon | Gemini TTS Bangla audition using a different failed-attempt signature | Do not repeat a provider, voice, settings, and text-hash combination already recorded as failed. |
| `radharani`, `bn-066`, `pather-panchali` | Sarvam Bulbul v3 with work-specific lexicon and measured paragraph sync | Gemini TTS Bangla audition; human exception only after the autonomous alternatives are exhausted | Regional terms and prose rhythm require dialogue/emotion and difficult-name samples before full generation. |
| Gothic/psychological: `the-tell-tale-heart`, `the-masque-of-the-red-death`, `the-monkeys-paw`, `the-yellow-wallpaper`, `jekyll-and-hyde`, `dracula`, `frankenstein`, `picture-of-dorian-gray` | Google Gemini 2.5 Flash TTS; Pro only for passages where Flash lacks controlled emotion | Google WaveNet/Chirp 3 HD or pinned Kokoro preset | Require restrained narration; reject theatrical instability and synthetic horror effects. |
| Adventure/fantasy: `the-time-machine`, `the-call-of-the-wild`, `white-fang`, `alices-adventures-in-wonderland` | Gemini 2.5 Flash TTS | WaveNet/Chirp 3 HD or pinned Kokoro preset | Prefer consistent pace and clean dialogue over exaggerated character voices. |
| Social/romance: `the-gift-of-the-magi`, `dsires-baby`, `the-cop-and-the-anthem`, `the-last-leaf`, `the-necklace`, `pride-and-prejudice`, `the-secret-garden` | Lowest-cost WaveNet/Chirp 3 HD or Gemini Flash audition winner | Gemini Pro only for a failed emotional passage; pinned Kokoro preset | Warm, unobtrusive long-form delivery; keep one stable narrator per title. |

Provider constraints:

- Sarvam is the critical Bengali lane because Bulbul v3 officially supports
  `bn-IN`, pronunciation dictionaries, pace, temperature, and 48 kHz output.
- Google Gemini TTS is the first cloud alternative because it is documented for
  audiobook/recitation work and accepts natural-language control of style,
  accent, tone, pace, and emotion. Its current Bangla locale is `bn-BD`, so an
  actual West Bengali pronunciation audition is mandatory before selecting it.
- Google WaveNet/Chirp 3 HD and Kokoro are cost-control auditions, not automatic
  winners. Kokoro requires an exact pinned Apache-2.0 model revision and
  hash-bound official voice asset; its public preset must not be represented as
  a human performer.
- ElevenLabs and Azure are optional exception lanes, not dependencies for this
  seven-day plan, because their credentials are not presently available in the
  repository environment.
- OpenAI is used for independent transcription/audio judgement, not as the
  default generator. Do not expand a deprecated generation model into a
  production dependency.

## Dependency-based seven-day schedule

Elapsed times begin only after the credentials, campaign budget variables, and
paid-provider lock preflight pass. Releases happen per title in daily canaries;
they do not wait for a 28-title batch.

| Window | Parallel work and release target | Required dependency |
|---|---|---|
| T+0–6 hours | Freeze the 32-title truth matrix; verify source/rights/cover/hash manifests; probe Sarvam and Google capabilities without synthesis; verify B2/endpoint/browser test path; add/test the Gemini adapter and binary hard-gate policy in a focused change | Existing Google ADC principal has Cloud TTS plus Vertex `aiplatform.endpoints.predict`; billing/APIs enabled; paid lock is free; exact campaign caps are present |
| Wave 1, T+6–24 hours | Repair `book-d19e96859f` and `book-f5d593e1f4`; generate `muchiram-gurer-jibanchorit` and `book-edfcf810c5`; run one English archetype bake-off, then process the nine short English titles: `the-gift-of-the-magi`, `the-tell-tale-heart`, `dsires-baby`, `the-cop-and-the-anthem`, `the-last-leaf`, `the-masque-of-the-red-death`, `the-yellow-wallpaper`, `the-monkeys-paw`, `the-necklace` | Representative auditions pass; canonical inputs and covers pass; private upload and browser gate available |
| Wave 2, T+24–48 hours | Process `nishkriti` and `radharani`; process `jekyll-and-hyde`, `the-time-machine`, `the-call-of-the-wild`, and `alices-adventures-in-wonderland` | Wave-1 assembly/QA is stable; no repeated failed-attempt signatures |
| Wave 3, T+48–96 hours | Process `bn-066`, `devdas`, and `pather-panchali`; begin the six long English titles in parallel by chapter | Exact public cover linkage for `devdas` and `pather-panchali`; work-specific pronunciation dictionaries; validated chunk assembly |
| Wave 4, T+96–168 hours | Complete `dracula`, `frankenstein`, `picture-of-dorian-gray`, `white-fang`, `pride-and-prejudice`, and `the-secret-garden`; run full ASR/anomaly scans, private B2 uploads, checksum verification, canaries, endpoint checks, and browser proof | No unresolved content, rights, listening, upload, or player blocker per title |

The bounded target is to attempt all 28 remaining titles and deploy every
individually passing title within seven calendar days. It is not safe or honest
to promise that every unseen full-length artifact will pass. A failure cannot
silently broaden the schedule: it remains reader-only and the report records one
owner-visible repair, replacement-provider, or editorial-exception action.

## Cost and throughput controls

- Sarvam's official price is INR 30 per 10,000 characters. The complete
  ten-title Bengali catalog is approximately 650,904 canonical characters, or
  about INR 1,953 for one clean base synthesis before retries; the remaining
  nine-title cost is lower because `book-2b9853ec52` is already live.
- Google WaveNet pricing includes a published monthly free-character allowance
  and then low per-character pricing. Use it only where the audition is
  premium-ready; free is not a quality argument.
- Gemini 2.5 Flash TTS is the default expressive cloud audition. Use Pro only on
  a title or chapter for which the lower-cost route has a recorded fatal
  listening defect.
- Kokoro is local and provider-cost-free, but CPU time and provenance are not
  zero-cost. Run one English archetype pilot from a pinned revision; do not build
  all English books before it passes the same hard gates.
- Serialize paid synthesis behind `paid_tts.lock`. Parallelize canonical
  manifests, cover/rights checks, ASR, signal analysis, independent listening
  reviews, B2 verification, endpoint checks, and browser smoke tests.

## Fastest safe external unblock

The repository environment has Google credentials but not the optional
ElevenLabs or Azure credentials. The single highest-leverage unblock is to:

1. Enable Cloud Text-to-Speech and Vertex AI in the configured Google project.
2. Grant the exact ADC service-account principal `roles/aiplatform.user`
   (`aiplatform.endpoints.predict`) and retain least privilege.
3. Verify billing/quota and the Gemini TTS regional endpoint.

The 2026-07-23 read-only local probe found
`google-cloud-texttospeech==2.36.0`, but no installed `google-genai`, Kokoro, or
Sarvam Python SDK. A Google voice/service query did not return a completed
capability result and was terminated; therefore Google IAM/API reachability is
still unproven and must be closed before it is placed on the paid critical path.
Sarvam can continue through the repository's existing HTTP/provider adapter;
SDK absence is not evidence that the provider is unavailable.

## Official primary sources

- Sarvam Bulbul v3 model and languages:
  https://docs.sarvam.ai/api/getting-started/models/bulbul
- Sarvam TTS parameters:
  https://docs.sarvam.ai/api-reference/text-to-speech/convert
- Sarvam pronunciation dictionaries:
  https://docs.sarvam.ai/api-reference/pronunciation-dictionary/create
- Sarvam pricing and rate limits:
  https://docs.sarvam.ai/api/getting-started/pricing and
  https://docs.sarvam.ai/api/getting-started/ratelimits
- Sarvam Saaras v3 and batch transcription:
  https://docs.sarvam.ai/api/getting-started/models/saaras and
  https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/batch-api
- Google Gemini TTS:
  https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
- Google Cloud TTS voices and pricing:
  https://cloud.google.com/text-to-speech/docs/voices and
  https://cloud.google.com/text-to-speech/pricing
- Google Speech-to-Text pricing, language support, and Chirp:
  https://cloud.google.com/speech-to-text/pricing,
  https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages,
  and https://docs.cloud.google.com/speech-to-text/v2/docs/chirp-model
- Google Cloud service terms:
  https://cloud.google.com/terms/service-terms/index-20240715
- ElevenLabs models, audiobooks, alignment, and pricing:
  https://elevenlabs.io/docs/overview/models,
  https://elevenlabs.io/docs/eleven-creative/products/audiobooks,
  https://elevenlabs.io/docs/overview/capabilities/forced-alignment,
  and https://elevenlabs.io/pricing/api
- Kokoro official repository and model card:
  https://github.com/hexgrad/kokoro and
  https://huggingface.co/hexgrad/Kokoro-82M
- Azure language support and batch synthesis:
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
  and https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-synthesis
- OpenAI model catalog, transcription, and timestamp output:
  https://developers.openai.com/api/docs/models,
  https://developers.openai.com/api/docs/models/gpt-4o-transcribe,
  https://developers.openai.com/api/docs/models/whisper-1,
  and https://platform.openai.com/docs/api-reference/audio/json-object
- Gemini audio understanding for the second independent audio judgement:
  https://ai.google.dev/gemini-api/docs/audio

## Next exact commands

Read-only API enablement check:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
gcloud services list --enabled --project "$GOOGLE_CLOUD_PROJECT" \
  --filter='name:(texttospeech.googleapis.com aiplatform.googleapis.com)' \
  --format='value(name)'
```

After securely resolving the ADC JSON's exact `client_email`, the authorized
least-privilege IAM command is:

```bash
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
  --member="serviceAccount:<EXACT_ADC_SERVICE_ACCOUNT>" \
  --role="roles/aiplatform.user"
```

Do not invent or guess the service-account member. After API/IAM verification,
resume the campaign from its authoritative state and run only the first bounded
representative title; do not start the 28-title generation wave:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library
PYTHONDONTWRITEBYTECODE=1 python3 -m json.tool \
  internal/earnalism_intelligence/bengali_audiobook_campaign_state.json >/dev/null
```
