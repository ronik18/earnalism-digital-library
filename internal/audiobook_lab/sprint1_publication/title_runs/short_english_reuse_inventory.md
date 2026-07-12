# Short English Private Reuse Inventory

Generated: `2026-07-12T21:00:48Z`

## Verdict

All four titles have readable full-book audio in the original workspace, but none is policy-safe for private reuse QA yet. Text rights pass for every title. The blocking layer is provider/model/selected-voice commercial and internal-evaluation evidence, plus incomplete hash binding for several assets. Public audio remains fail-closed and hidden.

No provider call ran, no audio was copied, and no release state was changed.

| Slug | Technically strongest local candidate | SHA256 | Duration | Source compatibility | Provider/commercial evidence | Private reuse QA |
| --- | --- | --- | ---: | --- | --- | --- |
| `sredni-vashtar` | OpenAI `verse` final | `2b328a80b90684ddf2fe3df1a1447481067c6cb277484f97432e882c7844d31a` | 636.840 s | Exact generation source SHA matches current sanitized SHA | OpenAI internal eval and selected voice remain `HOLD_PROVIDER_REVIEW`; historical listening score was 9.4 under the applied 9.7 gate | `BLOCKED` |
| `the-gift-of-the-magi` | Historical Piper asset | `0062fd225d5fb5ed12e4f6223a9d37897bdf19484ffd08a0c067146aeb042594` | 652.109206 s | Derived normalized body matches exactly after removing the spoken title; no generation-time source SHA exists | Piper `en_US-lessac-medium` per-voice commercial/speaker rights remain `HOLD_VOICE_RIGHTS`; historical ASR score 6.7837 | `BLOCKED` |
| `dsires-baby` | Historical Piper asset | `b1848e8cd120a83d4d69e716735c43a412efe21fc8094d205d9884a6241bb98f` | 708.034467 s | Derived normalized body matches exactly after removing the spoken title; no generation-time source SHA exists | Piper `en_US-lessac-medium` per-voice commercial/speaker rights remain `HOLD_VOICE_RIGHTS`; historical ASR score 9.4039 | `BLOCKED` |
| `the-tell-tale-heart` | OpenAI `marin` final | `cefb2d1ac40d4779b8571678ca41b3fd88fa21e69f139f8573f43c8c6433c2b1` | 699.768 s | Exact generation source SHA matches current sanitized SHA | OpenAI internal eval and selected voice remain `HOLD_PROVIDER_REVIEW`; last-word and 8.4 listening QA gates failed | `BLOCKED` |

## Evidence Summary

- Every listed MP3 exists and passes local `ffprobe` duration inspection. Duplicate paths listed in the JSON are byte-identical by SHA256.
- Current sanitized narration hashes are `44e3...fd21`, `67c1...ea7`, `5874...4a89`, and `8e72...7bdb` in title order.
- The Sredni Vashtar and Tell-Tale Heart OpenAI manifests are exactly bound to the current sanitized hashes.
- All four historical Piper timestamp bodies normalize to the current sanitized bodies exactly after removing only the spoken title prefix. This is derived compatibility evidence, not a generation-time SHA binding.
- The `command` assets record `en-IN-NeerjaNeural` and `centralindia`, but the generating implementation is only labeled `command`; exact provider invocation and entitlement are not preserved. Azure-like provider evidence remains on hold.
- The Tell-Tale Heart Edge and enhanced derivative assets lack approved commercial/voice evidence. The enhanced copy also lacks a direct source-audio hash binding.
- The public-domain source/right reports pass content and audiobook use. Separately, each report's historical source hash differs from the current `content/books/<slug>/raw/source.txt` byte hash, so those packets are not byte-bound to the current raw files.
- Historical reconstructed approval files claiming `PUBLIC_AUDIO_RELEASE_APPROVED` are superseded by the active `FAIL_CLOSED` and `AUDIO_HIDDEN` state.
- All inspected audio and sanitized source artifacts are untracked, original-worktree-only files. The clean clone does not contain them; this inventory does not copy them.

## Candidate Notes

| Asset | Provider record | SHA/source status | Existing QA status |
| --- | --- | --- | --- |
| Sredni Piper | `piper`, `en_US-lessac-medium.onnx` | No generation SHA; derived normalized body match | Rejected historical ASR path |
| Sredni command polish | `command`, `en-IN-NeerjaNeural` | Prepared SHA differs; 0.9948 normalized token similarity | Heuristic 9.60, not release QA |
| Sredni OpenAI | `gpt-4o-mini-tts`, `verse` | Exact sanitized SHA match | ASR/sync 9.7997; listening 9.4; terminal for that attempt |
| Gift Piper | `piper`, `en_US-lessac-medium.onnx` | No generation SHA; derived normalized body match | ASR 6.7837, blocked |
| Gift command polish | `command`, `en-IN-NeerjaNeural` | Prepared SHA differs; 0.9986 normalized token similarity | Heuristic 9.57, not release QA |
| Desiree Piper | `piper`, `en_US-lessac-medium.onnx` | No generation SHA; derived normalized body match | ASR 9.4039, blocked |
| Desiree command polish | `command`, `en-IN-NeerjaNeural` | Prepared SHA differs; normalized body matches after control removal | Heuristic 9.57, not release QA |
| Tell Piper | `piper`, `en_US-lessac-medium.onnx` | No generation SHA; derived normalized body match | ASR 9.5558; synthetic sync; rejected |
| Tell command polish | `command`, `en-IN-NeerjaNeural` | Prepared SHA differs; normalized body matches after control removal | Heuristic 9.52, not release QA |
| Tell Edge polish | `edge`, `en-IN-NeerjaNeural` | Prepared SHA differs; normalized body matches after control removal | Heuristic 9.40, not release QA |
| Tell enhanced derivative | Unbound Edge-derived candidate | No direct source/provider hash binding | No hash-bound release QA found |
| Tell OpenAI | `gpt-4o-mini-tts`, `marin` | Exact sanitized SHA match | ASR 9.9219 but last words failed; listening 8.4 |

## Required Clearance

Before any asset is admitted to private reuse QA, record approved commercial/internal-evaluation and selected-voice rights for its exact provider and voice. Then rebuild a current source-rights hash binding and, for non-OpenAI assets, a generation-source hash packet. Do not repeat an already failed provider/settings/text-hash attempt or expose any asset publicly.

## Next Exact Command

```bash
jq -r '.titles[] | [.slug, .private_reuse_qa_verdict, .technically_preferred_asset_id, (.blockers | join("; "))] | @tsv' internal/audiobook_lab/sprint1_publication/title_runs/short_english_reuse_inventory.json
```
