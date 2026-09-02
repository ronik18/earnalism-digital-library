# A4 coalescing configuration

Process-local singleflight has a fixed built-in maximum of 256 identities. At capacity it bypasses coalescing and loads normally; correctness is unchanged. There is no distributed lock configuration because distributed coalescing is `NOT_JUSTIFIED` and disabled. No Railway change is required.
