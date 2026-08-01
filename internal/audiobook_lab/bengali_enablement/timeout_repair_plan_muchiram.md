# Timeout Repair Plan: muchiram-gurer-jibanchorit

Generated: 2026-07-09T05:54:16Z

## Classification

`NEEDS_SEGMENTATION_REPAIR`

The title has source, rights, content, and prior release-gate evidence, but it is not selected for paid execution until a compact split sample is prepared.

## Repair Plan

1. Build a compact opening sample from clean reader text.
2. Split the sample into smaller chunks before provider submission.
3. Keep the first paid retry below the sprint cap and stop on repeated timeout.
4. Do not run full-book TTS.
5. Do not expose audio UI or update public release gates.

## Next Action

Create the compact split audition sample and rerun only after paid env gates are present.
