# Bengali Gothic Voice Config Report

Profile: `data/audiobook_voice_profiles/bengali-gothic-premium-v1.json`

Scope: `INTERNAL_REVIEW_ONLY`.

## Target Voice

The desired voice is a refined Bengali literary narrator: warm, intelligent, calm, restrained, intimate, and eerie. The presentation may be female or androgynous-warm, but must not imitate any real person, celebrity, public figure, or unconsented reference voice.

## Defaults

- Target loudness: `-18 LUFS`
- Peak ceiling: `-1.5 dB`
- Target chunk duration: `18 seconds`
- Chunk bounds: `8-28 seconds`
- Speaking rate: `0.90`
- Emotion intensity max: `0.55`
- Short pause: `250 ms`
- Medium pause: `550 ms`
- Long pause: `900 ms`
- Suspense pause: `1200 ms`
- Max silence: `1800 ms`

## Style Rules

- Gothic mood must be subtle, not theatrical.
- Fear is quiet tension, not screaming.
- Sorrow is breath-weighted, not melodramatic.
- Anger has sharper rhythm, not shouting.
- Laughter or sobbing is blocked unless the text explicitly requires it.
- Dialogue may have gentle distinction but not cartoon acting.

## Release Guard

The profile has `no_public_release=true`. It cannot be used to publish Kshudhita Pashan audio without separate listening QA, license review, rights review, and owner approval.
