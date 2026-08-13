# PR #269 Dracula Edge Voice-Rights Review

Status: `BLOCKED_NO_CHECKSUM_BOUND_COMMERCIAL_ENTITLEMENT`

## Candidate binding

- Master SHA-256: `132c19e72a6e6107f8cc91908590eaac17da042e5436dec426b24c7f6746d863`
- Provider metadata: `edge-tts`
- Voice metadata: `en-IN-NeerjaNeural`
- Generated: `2026-06-13T20:59:38.012Z`

## Evidence reviewed

- The retained bundle identifies `edge-tts` as the generation provider and does
  not retain an Azure Speech resource, paid-tier subscription, request ID,
  invoice, generation transaction, or provider-side immutable output record.
- The edge-tts project describes itself as a client for Microsoft Edge's online
  text-to-speech service that does not require an API key:
  https://github.com/rany2/edge-tts
- Microsoft documents audiobook creation as an Azure Speech use case and
  directs standard-voice customers to create an Azure subscription and Speech
  resource:
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech
- Microsoft states that text-to-speech use is subject to the terms applicable
  to the customer's Azure subscription:
  https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/transparency-note

## Decision

The Azure documentation supports audiobook use through a properly entitled
Azure Speech customer workflow. It does not retroactively bind that entitlement
to this exact file, which was generated through the separate Edge online
service without preserved customer-subscription evidence. A shared voice name
is not proof of generation rights.

Therefore the exact historical file is not approved for a private preview or
public release. It may be reconsidered only if contemporaneous provider/account
records prove the exact generation transaction and commercial output rights for
the checksum above. No new TTS generation is authorized by this review.
