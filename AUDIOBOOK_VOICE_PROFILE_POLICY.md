# Audiobook Voice Profile Policy

Earnalism voice profiles are style and safety records. They are not permission to clone or imitate a real person.

## Rules

- No unauthorized voice cloning.
- No celebrity or public-figure voice imitation.
- No use of a real person's voice likeness without explicit written consent.
- Do not claim "human narrated" unless the audio is fully human-recorded and a contract/proof reference is stored internally.
- Do not claim "no AI touch" if AI generation, AI enhancement, synthetic speech, or AI mastering is used.
- Generated or regenerated narration must be disclosed internally.
- Public disclosure copy must be truthful and approved before release.

## Sample Profile

`data/audiobook_voice_profiles/bengali-gothic-literary-female.sample.json` is a style profile only. It is not a named person, celebrity, actor, public figure, or human narrator record.

Default status:

- `consent_status = NOT_APPLICABLE_STYLE_PROFILE`
- `allowed_for_generation = false`
- `allowed_for_public_release = false`
- `owner_approved = false`

The sample profile cannot be used for actual generation until a separate approval changes those fields in a reviewed PR.
