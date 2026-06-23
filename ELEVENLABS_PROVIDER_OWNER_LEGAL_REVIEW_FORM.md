# ElevenLabs Provider Owner/Legal Review Form

This form is for manual evidence collection only. It does not approve internal generation, production use, public audio, or provider API calls.

## Current Gate State

- Provider ID: `elevenlabs`
- Display name: ElevenLabs
- Current provider decision: `HOLD_PROVIDER_REVIEW`
- Current internal-eval status: `HOLD_PROVIDER_REVIEW`
- Current production status: `PRODUCTION_BLOCKED`
- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- Real audio generated: `false`
- Decision must remain HOLD until every required field below is completed and reviewed.
- Decision: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED

## Evidence Fields

| Field | Current / Required Value | Owner/Legal Entry |
| --- | --- | --- |
| Provider account/plan | Paid plan required: `True`. Attach plan evidence URL or invoice reference. |  |
| Plan evidence status | Current: `HOLD_REVIEW`. Must become APPROVED or RECORDED. |  |
| Selected voice | Current: `21m00Tcm4TlvDq8ikWAM`. Select exact voice ID and display name. |  |
| Selected voice type | Current: `platform_voice`. Must be platform/provider voice or approved generated voice. |  |
| Selected voice rights summary | Current: Proposed ElevenLabs platform voice for owner/legal review only; internal evaluation is blocked until selected voice rights, plan, attribution, restrictions, and account terms are manually approved.. Must be owner/legal reviewed. |  |
| Official commercial-use evidence | https://help.elevenlabs.io/hc/en-us/articles/13313564663441-Can-I-publish-the-content-I-generate-on-the-platform plus owner/legal notes. |  |
| Beta features excluded | Current: `False`. Must remain false. |  |
| Beta exclusion evidence | Current: General-availability provider use only; beta, experimental, or preview voice features are excluded unless separately approved.. Must become APPROVED or RECORDED. |  |
| Standalone audio distribution evidence | Current: `HOLD_REVIEW`. Attach reviewed evidence. |  |
| Commercial internal-eval permission | Current: `HOLD_REVIEW`. Must become APPROVED or ALLOWED. |  |
| Attribution rules | Current: `HOLD_REVIEW`. Record exact requirement. |  |
| Selected voice attribution | Current: `HOLD_REVIEW`. Record exact requirement. |  |
| Selected voice restrictions | Current: `HOLD_REVIEW`. Record exact restrictions. |  |
| Provider terms review | Current: `HOLD_REVIEW`. Must become APPROVED. |  |
| Data retention review | Current: `HOLD_REVIEW`. Must become APPROVED. |  |
| Data/privacy notes | Account, privacy, voice-library, and data-retention settings require owner/legal review before internal generation. |  |
| Voice license evidence | https://elevenlabs.io/terms plus selected voice evidence. |  |
| Owner approval | REQUIRED: reviewer name, date, and decision. |  |
| Legal/internal review | REQUIRED: reviewer name, date, and decision. |  |
| Decision | Choose one: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED. | HOLD |
| Notes | REQUIRED: rationale and unresolved questions. |  |
| Required next action | REQUIRED: smallest next evidence or review step. |  |

## Safety Confirmation

- No provider API may be called from this form alone.
- No real audio may be generated from this form alone.
- No public audio URL, public listening CTA, or public audio JSON-LD metadata may be created.
- Production status remains `PRODUCTION_BLOCKED`.
- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
