# bn-066 Fast-Path Report

Status: `NOT_PUBLISHED`

`bn-066` was evaluated first because an existing private full TTS package exists. The title remains a public reader and audio-hidden.

## ASR Calibration

- Command class: bounded ASR language calibration on existing private audio
- Provider calls ran: `true`
- Estimated spend: `$0.1047`
- Best language option: `auto`
- Calibration usable for full ASR plan: `false`
- Opening score: `0.0/10`
- Middle score: `0.0/10`
- Ending score: `4.375/10`
- First/last checks: `FAIL`
- Result: `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED`

## Decision

Do not publish. Do not expose Listen. Do not reuse the existing private TTS for public release.

Next command:

```bash
python3 internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py --slug bn-066 --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets
```
