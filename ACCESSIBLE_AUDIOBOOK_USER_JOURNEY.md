# Accessible Audiobook User Journey

This is an internal journey map for future Earnalism audiobooks. It does not enable public audio and does not claim WCAG compliance, blind-user testing, screen-reader certification, or a fully accessible audiobook platform.

Current truth:

- Dracula is the only approved core public reading release.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks are not public/live.
- Any sample listening is internal-only until rights, QA, owner approval, and rollback pass.

## 1. Home Discovery

The non-visual user should understand:

- The Earnalism is a quiet digital reading room.
- Dracula is the only live approved reading title today.
- Audiobooks are not available publicly yet.
- Bengali Gothic and other classics are moving through a rights-safe pipeline.

Required future audiobook cues:

- If an audiobook is approved later, the home page must say exactly what is listenable.
- No Listen Now CTA may appear for unapproved titles.
- Pipeline-only titles may offer Notify Me or Reading Circle interest only.

## 2. Book Detail

The book page must explain:

- title and author
- source/rights note
- what is free
- what requires reading time
- whether audio is available or not available
- how to continue later

Future audiobook release requires:

- an accessible sample player only after approval
- transcript availability
- chapter count
- voice/provider disclosure where legally required
- no fake human narration or "no AI touch" claim

## 3. Internal Sample Listening

Sample listening remains internal-only until the release gate passes.

Internal reviewer steps:

1. Open the internal sample.
2. Confirm title, author, language, and chapter are announced.
3. Play, pause, rewind 10 seconds, and forward 30 seconds by keyboard.
4. Change speed and confirm the new speed is announced.
5. Move to another chapter and confirm the new chapter is announced.
6. Open transcript and confirm it is reachable non-visually.
7. Create a bookmark and confirm it is announced.
8. Reload and confirm resume position is preserved.
9. Trigger a simulated low-network state and confirm recovery instructions are announced.

## 4. Login and Signup

The user should understand:

- Chapter 1 can be previewed free where approved.
- Sign-in lets reading or listening progress travel with the account.
- Reading time is wallet time, not a subscription.
- No public audiobook access is granted unless a specific audiobook is approved.

Required states:

- labeled email field
- labeled password field
- clear validation messages
- live error announcement
- no hidden-only critical instructions

## 5. Wallet and Payment

The future audiobook journey must preserve the current reading-time truth:

- Reading time is credited after confirmation.
- It is not an autorenewing subscription.
- Secure payment is by Razorpay where existing payment integration supports it.
- Payment errors must be announced.
- Wallet balance and lock states must be understandable without vision.

No live payment provider call is required for this internal journey map.

## 6. Library Access

The library should separate:

- live approved titles
- pipeline-only future titles
- locked states
- audio-unavailable states

Future audiobook release must show approved audio only for the exact book/language/version that passed the release gate.

## 7. Audiobook Player

Required controls:

- play/pause
- 10-second rewind
- 30-second forward
- speed
- previous chapter
- next chapter
- chapter list
- transcript
- bookmark
- sleep timer
- support/report issue

Required accessible behavior:

- all controls are buttons or links with useful accessible names
- keyboard order follows visual order
- focus indicator is visible
- current chapter is announced
- state changes use concise announcements
- disabled states explain why they are disabled
- no broken player appears while audio is disabled

## 8. Chapter Navigation

The listener must be able to:

- hear the current chapter name
- move to the next chapter
- move to the previous chapter
- jump from chapter list
- understand when a chapter is locked
- return later to the same place

Chapter navigation must not rely on a visual waveform.

## 9. Resume Listening

Resume must work for:

- same browser session
- signed-in return
- interrupted network
- mobile return

The user should hear:

- book title
- chapter
- approximate position
- resume confirmation

## 10. Bookmarks

Bookmarks must:

- be creatable by keyboard
- announce success
- include chapter and position
- be reachable later
- avoid exposing private notes publicly

## 11. Transcript Access

Transcript must:

- be reachable from player controls
- have a clear heading
- preserve chapter and paragraph structure
- support screen-reader navigation
- avoid claiming perfect sync unless measured

## 12. Support and Error States

The journey must explain:

- audio unavailable
- rights or QA hold
- failed audio load
- low bandwidth
- payment failure
- expired session
- contact/support path

The user should never be left with a silent broken player.

## 13. Poor-Network Handling

Required future behavior:

- announce buffering or retry
- avoid repeatedly restarting from chapter start
- preserve resume state
- offer transcript fallback if permitted
- avoid exposing raw storage URLs in public UI

## 14. Non-Visual Completion Flow

At completion, the user should be able to:

- hear that the book or chapter is complete
- move to next chapter or finish
- save or clear bookmark
- return to library
- understand whether more reading time is needed
- contact support if completion was incorrect

## Current Readiness

Current state is foundation-only:

- Public audio remains disabled.
- No public audiobook metadata or Listen Now CTA should be exposed.
- Existing public audio files require quarantine/review until rights and QA are proven.
- Manual NVDA, VoiceOver, and TalkBack testing is still required before public claims.
