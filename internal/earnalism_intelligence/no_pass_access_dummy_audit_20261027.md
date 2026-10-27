# No-pass access and corrupt-balance local qualification

Catalogue tests now reflect the current allowlist and separate primary/mirror Ginni checksums. Ginni remains held; synthetic tamper detection and no-database-fallback checks remain enforced. A White Heron and The Selfish Giant remain commercial Reader editions under current registry authority.

Corrupt negative wallet balances now return controlled 503 BALANCE_UNAVAILABLE without normalizing the balance, starting a session, setting media cookies or recording a debit. Valid zero balances still require a pass. Existing India pilot free Reader entitlements remain unchanged and cannot authorize audio.

Local qualification: 146 passed, no skips, with a disposable authenticated loopback MongoDB replica set. Includes both formerly skipped budget atomicity scenarios, wallet/start/transfer HTTP error checks, free Reader entitlement cases, zero public audio and page-boundary tests. No paid sessions, provider requests, ledger repairs, refunds or production changes.

The test-only cap installer source fixture is reused from reviewed Listener PR568; frozen production pins and the disabled installer remain untouched. The hosted regression command now requires the new error-handling and catalogue tests alongside real Mongo integrations.

This focused PR excludes international compliance commit57e518c, Listener runtime changes, and unrelated local ledger/history edits. Owner explicitly authorized one separate PR/branch exception. CI/review results must be read at the exact pushed head; local evidence is not deployment acceptance. No merge/deployment is authorized by this packet.
