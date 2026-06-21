# Audiobook Governance

Local model synthesis is disabled unless the operator creates an explicit local
approval file such as:

`data/audiobook_governance/dracula.local_generation_approval.json`

The approval file is intentionally not created as approved in this PR. Required
fields for a future local internal-only run:

```json
{
  "approved": true,
  "scope": "LOCAL_INTERNAL_REVIEW_ONLY",
  "book_slug": "dracula",
  "owner": "named operator",
  "expires_at": "YYYY-MM-DD"
}
```

No approval file may enable public audio, upload audio, or turn on Listen Now.

