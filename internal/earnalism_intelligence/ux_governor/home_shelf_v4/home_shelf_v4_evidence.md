# Home Shelf Architecture v4

Implemented a data-driven `/api/home/curated` response and responsive Home shelf renderer. Shelf membership comes from public book metadata or admin-ready `editorial_shelf_ids`; React contains only shelf vocabulary and layout rules, not Sprint 1 title arrays. Selected Listening is populated only after the canonical reader manifest reports enabled audio with an asset URL.

Audiobook generation, ASR, auditions, uploads, release gates, and `paid_tts.lock` were not changed.

Validation pending: frontend unit/build, backend route tests, production visual review.
