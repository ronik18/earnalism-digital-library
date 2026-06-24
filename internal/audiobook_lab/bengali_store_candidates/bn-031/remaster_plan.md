# Internal Remaster Plan: মহেশ

Candidate slug: `bn-031`
Triage rank: `35`

Recommended internal-only actions:
- Create an ignored review copy under `improved_internal/audio/`.
- Apply conservative leading/trailing silence trim.
- Apply loudness normalization for review consistency.
- Repair VTT/JSON sidecar formatting without inventing alignment.

Blocked actions:
- Public release.
- Speech-content alteration.
- Narration regeneration.
- External API calls.
- Public audio CTA or structured audio metadata.
