# Request, authorization, and tenant boundary map

No identities, tokens, private object keys, or signed URLs are recorded.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| /api/home, /api/books, /api/books/{slug} | public; Redis: public cache | backend/server.py:5275-5879 |
| /api/reader/book/{slug}/manifest and chapters | public reader metadata/content; Redis: reader manifest/content cache | backend/server.py:2127-2185, 2880-2971, 5700-5799 |
| /api/reader/book/{slug}/audiobook and package segments | protected; Redis: manifest metadata cache | backend/server.py:8431-8939; backend/tests/test_zero_public_audio_contract.py |
| /api/reading-pass/* | protected; Redis: user/session/wallet cache | backend/server.py:9391-9600 |
| /api/admin/books/* | admin; Redis: public generation invalidation | backend/server.py:5880-7600 |
| /api/payments/* and wallet admin | protected/admin/webhook; Redis: wallet/payment state cache | backend/server.py:10145-10791 |
