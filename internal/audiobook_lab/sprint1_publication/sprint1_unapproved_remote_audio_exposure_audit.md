# Sprint 1 Unapproved Remote Audio Exposure Audit

Status: `REMOTE_STORAGE_REVOCATION_OWNER_DECISION_REQUIRED`

Current repository truth is fail closed: no affected title's current API, reader manifest, or frontend release state references these historical objects. Direct object storage remains a separate external control surface.

Live unauthenticated probes found at least nine tracked MP3 variants returning HTTP 200 across six unapproved titles: `bn-066`, `nishkriti`, `alices-adventures-in-wonderland`, `the-tell-tale-heart`, `the-yellow-wallpaper`, and `the-necklace`.

No current approved revocation command exists. The historical cleanup utility was removed by revert and would require revalidation, credentials, a complete object/sidecar allowlist, private-QA retention proof, dry-run review, and a separate owner decision before irreversible deletion.

No remote object, release gate, provider, or paid lock was mutated by this audit.

Next exact command:

```bash
git show 4373839:scripts/audio/cleanupAudiobookStorage.js | sed -n '1,240p'
```
