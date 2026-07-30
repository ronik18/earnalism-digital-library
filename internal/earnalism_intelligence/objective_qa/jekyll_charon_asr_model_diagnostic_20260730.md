# Jekyll Charon objective-ASR model diagnostic

Status: **BLOCKED — do not run full-title MLX inference**

The completed `medium.en` full-title report is valid evidence, not a release
pass. Its exact report SHA-256 is
`b31eab68e0bd79c6469617cb8a2a9908d0b5ef2966121f6c723eda0e81dbd812`.
It measured ASR/source `9.8831`, coverage `0.9873`, and precision `0.9894`,
with matching title boundaries, but failed ordered content integrity.
Objective QA stopped before listening, upload, publication, or release
mutation.

Two source-blind MLX models then evaluated only the two weakest chunks and
three exact-pass controls:

| Model | Exact revision | Result | Full 92-unit run |
| --- | --- | --- | --- |
| `whisper-large-v3-turbo` | `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb` | Targets and controls did not all strict-pass | Blocked |
| `whisper-large-v3-mlx` | `49e6aa286ad60c14352c404340ded53710378a11` | Targets and controls did not all strict-pass | Blocked |

The full large-v3 weights are MIT-tagged and privately cached with SHA-256
`05ff791ce3630fae47e7c51004e9666204d786246ec07cac6110af768099b40d`.
The turbo diagnostic report SHA-256 is
`ef86c6ae2d1db6857aa209304173b8d2f74aded90caf3f66133e7db9ed185ec9`;
the full large-v3 diagnostic report SHA-256 is
`7328d462aca42550d728187e1676f0c1a587f4d3b71033133920e9dbb4ba7a93`.

## Finding

`chunk_0045` is substantially a `medium.en` recognition limitation. Full
large-v3 improved it from `9.4698 / 0.9184` to `9.8940 / 0.9929` and recovered
both boundaries, although duplicate/unexpected tokens still prevent a strict
pass.

`chunk_0009` contains an actual narration omission. The source contains:

> obligation beyond the payment of a few small sums to the members of the doctor's household

All three independent recognizers skip the same 16-token span. The MLX word
timestamps move directly from `or` ending at `31.92s` to `this` starting at
`31.92s`, proving there is no unrecognized audio interval to recover.

Full large-v3 also regressed control `chunk_0071` with duplicate words and a
zero-duration word timestamp. It therefore fails the strong-control contract
independently of the real `chunk_0009` omission.

## Release decision

Keep Jekyll audio hidden. Do not run a 92-unit MLX pass, listening QA, upload,
publication, or release mutation from this evidence. No paid-provider lock was
read or changed.

Next exact action: prepare a no-provider-call sequential bounded-repair
preflight for `chunk_0009` against the repaired Jekyll manifest. Bind the
exact omission and all source/audio/report hashes, preserve every other audio
file byte-for-byte, and require a sentence-boundary-safe synthesis plan plus
fresh objective QA before any provider call.
