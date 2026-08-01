# Storage Containment Canary Report

## Verdict

**PASS** for `bn-066`. The reviewed five-object package was copied to the confirmed-private B2 QA bucket and verified before public delivery was revoked.

- Inventory SHA-256: `21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c`
- Retained privately: **5/5**
- Old URLs returning 404: **5/5**
- Failed objects: **0**
- Providers: **1 B2**, **4 Cloudinary**
- Release-gate mutations: **none**
- `paid_tts.lock`: **untouched**

## Execution

A first local transfer attempt was interrupted before mutation because the local uplink stalled during the private B2 multipart upload. No private multipart remained and no public source was deleted. The canonical canary then ran inside the linked Railway backend instance using the same frozen inventory, owner token, and separate source/destination credential mappings.

Each private object has matching byte size and source SHA-256 metadata. Only after that verification did the executor revoke the corresponding old public delivery.

## Control Checks

- `book-2b9853ec52`: manifest enabled and QA passed; approved proxy returned **206** with `bytes 0-1023/5233965`.
- `a-ghost-story`: manifest enabled and QA passed; approved proxy returned **206** with `bytes 0-1023/7047789`.
- `bn-066`: manifest remained `audio.enabled=false`, public audio fields stayed empty, and proxy returned **404**.

The canary therefore authorized the full reviewed 606-target containment run.
