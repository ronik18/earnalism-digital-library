# Season 1 Launch Shelf Spec

This is a source-ready UX/content spec only. Do not implement without explicit product approval.

## Shelf 1: Listen Now

Purpose: Convert confidence into listening starts for approved audiobooks only.

Allowed titles:

- `book-2b9853ec52` / দুই বিঘা জমি
- `a-ghost-story` / A Ghost Story, after final browser/manifest route check for paid campaigns

Card requirements:

- Graphical cover.
- Title and author.
- Status badge: `Audiobook Approved`.
- CTA: `Listen`.
- Sync copy: `section-following narration` only for Bengali paragraph/stanza sync.
- No word-level sync claim.

## Shelf 2: Bengali Classics

Purpose: Make Bengali literature prominent and complete even when audio is hidden.

Card requirements:

- Separate `Audio Live` from `Reader Edition Live`.
- CTA: `Read`.
- For reader-only titles: “Reader edition live · audio appears after quality gates pass.”
- No shameful missing-audio language.

## Shelf 3: Coming To The Listening Room

Purpose: Build anticipation without false availability.

Allowed titles:

- মুচিরাম গুড়ের জীবনচরিত
- গিন্নি
- রামকানাইয়ের নির্বুদ্ধিতা
- পোস্টমাস্টার
- The Gift of the Magi
- The Tell-Tale Heart
- The Open Window
- Sredni Vashtar
- Désirée's Baby

CTA: `Read` or `Follow the release`.

No Listen CTA.

## Shelf 4: English Short Classics

Purpose: High-conversion, short-form discovery.

Include status badges:

- `Reader Ready`
- `Audiobook Approved`
- `Coming to the Listening Room`

## Shelf 5: Long-Form Classics

Purpose: SEO and authority.

CTA: `Read`.

Do not force long-form titles into audio marketing until QA/cost gates pass.

## Card System Requirements

- Graphical cover.
- Title.
- Author.
- Status badge.
- CTA: Read / Listen only if approved / Coming soon.
- No stale URL.
- No default A Ghost Story probe.
- No unapproved audio controls.
