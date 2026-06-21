# Audiobook Provider Adapter Policy

Status: dry-run interface only.

## Current Behavior

`backend/audiobook_generation/provider_adapter.py` defines a provider interface and a `DryRunNarrationProvider`. The dry-run provider:

- performs no network calls
- requires no API keys
- generates no voice
- uploads no audio
- marks all assets as not publishable
- returns explicit metadata-only cost estimates

## Future Provider Integration

Provider integration is future work. Any real provider integration must arrive in a separate PR with:

- owner approval
- rights approval
- source-text approval
- voice-style approval
- consent validation
- explicit credentials configuration
- budget/cost estimate before generation
- human listening QA
- public disclosure review

No OpenAI, AI4Bharat, Piper, STT, FFmpeg mastering, voice cloning, music, or external audio API is called in this PR.
