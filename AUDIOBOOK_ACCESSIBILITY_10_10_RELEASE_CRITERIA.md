# Audiobook Accessibility 10/10 Release Criteria

This is an internal release standard for future Earnalism audiobooks. It is not a public claim of WCAG compliance, blind-user testing, screen-reader certification, fully accessible audiobook platform status, or public audiobook availability.

Current launch truth:

- Dracula remains the only approved core public reading release.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks are not public/live.
- No public Listen Now CTA, AudioObject metadata, or audiobook URL may appear before explicit owner approval.

## 10/10 Definition

A 10/10 audiobook release means a blind, low-vision, dyslexic, elderly, keyboard-only, mobile assistive-technology, commuter, and premium audiobook listener can independently discover, understand, buy access, open, listen, navigate, pause, resume, bookmark, recover from errors, and complete the audiobook with a rights-clean and emotionally restrained literary experience.

The standard is evidence-based. A score cannot reach 10/10 until every mandatory gate below has current-branch evidence.

## Mandatory Release Gates

| Gate | Required Evidence | Blocks Release If Missing |
| --- | --- | --- |
| Public audio disabled until approval | `audio_enabled_slugs` empty, no Listen Now CTA, no AudioObject, no public audio URL | yes |
| Source text approval | source URL, source name, source license, source hash, content hash, provenance hash | yes |
| Derivative audiobook rights | explicit derivative/audiobook approval for the exact edition and region | yes |
| Commercial model permission | model/provider license allows commercial audiobook use | yes |
| Voice rights | voice/provider/narrator rights evidence, no real-person voice cloning risk | yes |
| Owner approval | owner signs exact book, language, voice, release scope, and rollback path | yes |
| Human listening QA | Bengali and English QA scores at or above 9.5 where relevant | yes |
| Transcript | transcript exists when required and is reachable from the player | yes |
| Text/audio sync | measured tolerance at or below 250 ms | yes |
| Rollback safety | owner, route disablement, metadata removal, and takedown instructions | yes |

## Blind-User Journey Standard

- The audiobook state must be announced clearly before purchase.
- The play, pause, speed, rewind, forward, chapter, bookmark, transcript, and help controls must have accessible names.
- The current chapter and playback state must be announced without requiring visual context.
- Locked, loading, error, payment, and retry states must be announced through live regions or equivalent.
- The user must be able to resume listening and recover location without seeing a progress bar.
- No public claim may say blind-user tested until actual blind-user test evidence exists.

## Low-Vision Journey Standard

- Controls must remain readable and operable at high zoom.
- Focus indicators must be visible and not rely only on color.
- Transcript and chapter controls must preserve contrast and spacing.
- Mobile layout must keep player controls reachable without overlap.

## Dyslexic and Non-Reading User Journey Standard

- The listener can start with a short sample internally before full release approval.
- Transcript access must support line breaks and clear paragraph structure.
- Playback speed controls must include a slower pace.
- The player must not require reading dense instructions to recover from errors.

## Keyboard-Only Playback Standard

Required controls:

- play or pause
- 10-second rewind
- 30-second forward
- playback speed
- previous chapter
- next chapter
- transcript
- bookmark
- resume
- report issue or support

All controls must be reachable by keyboard in a logical order. Focus must not be trapped or lost.

## Screen-Reader Announcement Standard

The player must announce:

- audiobook title
- author
- chapter number and title
- current playback state
- elapsed and remaining time in an understandable form
- current speed
- bookmark saved
- chapter change
- payment or wallet lock state
- failed load or low-network state

Announcements must be concise and not repeat so often that they interrupt listening.

## Mobile Assistive-Technology Standard

- TalkBack and VoiceOver must be manually checked before public release.
- Tap targets must be large enough for elderly and motor-impaired users.
- The transcript and chapter drawer must not hide controls from screen readers.
- Sleep timer and resume controls must have stable names.

## Bengali Narration Standard

Minimum evidence:

- Bengali human listening QA score at or above 9.5.
- Pronunciation guide reviewed for names, Sanskritized terms, Persian/Arabic words, English loan words, and literary archaisms.
- Punctuation-aware pauses for commas, danda, dialogue, poetry, and chapter headings.
- Emotional restraint suitable for literary narration.
- No public Kshudhita Pashan or Bengali audiobook release until source, derivative rights, model license, QA, owner approval, and rollback pass.

## English Narration Standard

Minimum evidence:

- English human listening QA score at or above 9.5.
- Gothic/literary tone for Dracula and similar works.
- Proper handling of names, epistolary headings, dated letters, dialogue, and quoted material.
- No fake human narration claim.
- No "no AI touch" claim if AI generation or enhancement is used.

## Chapter Navigation Standard

- Chapter list is available non-visually.
- The current chapter is announced.
- The listener can move to previous and next chapter by keyboard.
- The current chapter can be resumed after reload or sign-in.
- Chapter 1 free preview rules and locked later chapters are explained clearly.

## Transcript and Sync Standard

- Transcript must be available when required.
- Text/audio highlighting must not be required for basic listening, but if present it must stay within 250 ms tolerance before a 10/10 score.
- Transcript mismatch, missing paragraphs, repeated lines, and skipped sections block release.

## Low-Network and Error-State Standard

- The user is told when audio cannot load.
- Retry, support, and fallback options are clear.
- The player must not display broken controls or silent failure.
- No public audio route may return a playable asset before release approval.

## Rights, Model License, and Voice Safety

Blocked until all are proven:

- source text approval
- derivative audiobook rights
- model commercial-use permission
- model license evidence
- voice/narrator rights
- real-person voice cloning risk resolution
- storage/provider publish approval

## Owner Approval

Owner approval must name:

- book slug and title
- language
- edition/source hash
- provider/model/voice
- QA score
- release region
- public copy
- rollback owner
- rollback instructions

## Current Decision

Current status is `PUBLIC_AUDIO_RELEASE_BLOCKED`. This is the correct and safe state until the evidence above exists.
