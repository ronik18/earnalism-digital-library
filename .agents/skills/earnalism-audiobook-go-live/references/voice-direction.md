# Voice discovery, direction and qualification

The Qwen pair below is historical, nonexhaustive configuration, not a requirement to use that provider or a claim that recordings or GPU runtimes are currently loaded. Use `voice-roster.json` as nonsecret configuration. The local `scripts/plan_voice.py` prints a direction proposal; it never synthesizes, downloads weights, spends money or changes qualification. It accepts only its narrow roster/language interface; do not use its absence of Girija, Cedar or another explicitly chosen voice as proof that the voice is unavailable, or let its default suggestion replace that selection.

Before voice selection or new narration/repair, apply [narrative performance and final scored review](narrative-performance.md): full-book comprehension, phrase-level syntax/emotion, stable identity across units, meaningful pause consistency and the final scored-mix listening gate. Reuse of an accepted profile/master does not override a new material owner finding.

## Historical configured Qwen pair

- **Ryan, male:** Qwen CustomVoice narrator with historical Open Window and Selfish Giant recording locators. Verify the current edition and active voice/package; a later accepted narrator can supersede an old locator. Acceptance binds the exact recording/use, not every future title or parameter change.
- **Serena, female:** Qwen CustomVoice preset configured as the second candidate. Officially described as warm/gentle with Chinese as native language. The model supports English, but English accent/intelligibility and literary quality are UNVERIFIED until an actual audition passes. Do not describe her as production-ready for English or substitute a rejected pilot.

Both profiles use built-in identities, not a clone or imitation of a real person. The target is `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`; resolve and record exact model/tokenizer/package revisions before inference. The official model lists language and instruction controls, including tone/rate/emotion. Use only runtime-supported fields and discover supported speakers/languages with the real adapter. Do not invent `pitch`, `speed`, `emotion` numeric API arguments. The 0.6B preset does not have the same instruction-control contract. Do not silently switch it in.

Sources checked 26 October 2026: [official model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice), [official project](https://github.com/QwenLM/Qwen3-TTS). Apache-2.0 model metadata does not establish source-text rights, a new voice consent, all output rights or campaign quality. Recheck relevant terms when model/revision/use changes. Bengali is not among this model's documented ten languages; follow the separate Bengali campaign, never route it here as fallback.

## Choose by the work

First preserve an accepted title's narrator/master. For a new title, compare genuinely qualified profiles for target language/accent, clarity of names, natural long-sentence cadence, dialogue separation, fatigue over duration and thematic fit. Respect an explicit owner preference, including a named narrator outside this roster. Resolve provider + voice ID + model/revision + actual generation provenance + applicable rights/consent; the same display name may exist across providers or custom voices. Never borrow a different provider's Girija licence/qualification, relabel a Roopa asset or silently substitute a fallback. Search current retained assets and actual supported adapters before proposing new synthesis. An unavailable or unqualified selected voice remains a documented dependency while independent preparation continues. Do not choose male for authority or female for tenderness simply because of gender; the same delivery settings apply to either profile.

Use restrained direction, keeping identity, accent and intelligibility stable:

| Content | Direction target | Avoid |
|---|---|---|
| Literary irony / dry humour | clear, conversational, lightly understated; preserve reveal | announcing the joke or exaggerating sarcasm |
| Gothic / suspense | measured, calm tension; natural phrase pauses | whispering that loses words, extreme pitch, horror effects |
| Reflective / contemplative | warm, unhurried, precise | uniformly slow cadence or excessive silence |
| Adventure / children's fiction | lively but controlled; gentle dialogue distinction | cartoon voices, breathless speed, age impersonation |
| Practical nonfiction | clear, steady emphasis and navigable lists | sales pitch or flat list-reading rhythm |
| Poetry | follow syntax, line/stanza meaning and measured evidence | invented beat, sung text, forced rhyme cadence |

Do not time-stretch an accepted master to impersonate a new delivery. Regenerate only a demonstrated defective passage when authorized; preserve hashes/history and recheck its neighbours, measured sync and affected package. Customer playback speed is a player/accounting test, not a narration generation attribute.

## Source preparation and continuity engineering

Apply [the engineering method](voice-engineering.md) before new or repaired audio: audit the actual worker text and transformations, distinguish narrator identity from scene/character expression and recording level, retain a stable base direction with contextual changes, and assess consecutive units together. Identical speaker IDs, seeds or request fields do not certify equal performances. The offline planner supplies a base proposal only; it does not read the book, perform a phrasing plan or establish listening/mix acceptance.

## Qualification before full generation

Prepare the source-specific audition plan offline first. Use a confirmed existing free runtime or approved paid allowance; do not allocate paid compute or download large models speculatively. In one bounded pass test opening, ending, dialogue, names/numbers and an emotionally difficult passage. Retain exact text/model/voice/direction hashes, measured audio, ASR comparison and listening findings. Compare only within the approved audition budget. Material changes create a new recorded attempt, not an erased failure.

Apply the current campaign thresholds, rather than inventing a score or a universal threshold. No missing/reordered/duplicated content, robotic texture, mechanical cadence, choppy joins or fallback TTS. Objective tests do not stand in for actual listening. If human listening is explicitly required and unavailable, expose that one missing evidence item; do not call another agent's inference a human approval. When delegation to a reviewer is authorized, reuse one evidence-bound review rather than asking at each chunk.

Promote qualification only from retained real evidence for language/model/revision/use and actual applicable approval. Scope matters: Ryan's existing accepted title audio remains reusable without another audition when current bindings match; Serena's profile remains candidate-only until qualified. A failed or plateaued pilot is parked with its reason. Do not revive the rejected Kokoro `bf_emma` Secret Garden pilot as an approved female default.

The roster’s `accepted_title_bindings` are discovery hints, not the authoritative release registry. Confirm the exact edition/manuscript/package and current rights/revocation state before reuse. An unlisted title may also have accepted masters: inspect its current canonical evidence before proposing generation. A listed title does not inherit current runtime access or spending authority.
