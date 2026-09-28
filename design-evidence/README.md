# Option B visual QA

Captured 2026-09-28 using the authenticated Chrome session. The production images are the current `https://theearnalism.com/` baseline before this branch; the Option B images are the built branch at the same CSS viewport widths. The owner-provided reference mock remains in the conversation and is not copied into this repository.

| Viewport | Production before | Option B branch |
| --- | --- | --- |
| 1440 px | [production-before-1440.png](production-before-1440.png) | [option-b-1440.png](option-b-1440.png) |
| 1024 px | [production-before-1024.png](production-before-1024.png) | [option-b-1024.png](option-b-1024.png) |
| 390 px | [production-before-390.png](production-before-390.png) | [option-b-390.png](option-b-390.png) |

The local build uses the repository's default release flags, so production-supplied Reading Pass offers are verified separately against the live page after deployment. Production currently serves four offers at ₹49 / ₹89 / ₹239 / ₹499 for 30 / 60 / 180 / 600 minutes.
