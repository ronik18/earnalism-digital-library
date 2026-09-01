# Media lifecycle map

Audio is a protected proxy/stream contract. PDF is not an active customer product delivery path.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| Audio release truth | Manifest returns empty assets/URL; playback is resolved only after authorization. | backend/server.py:2780-2878; backend/tests/test_zero_public_audio_contract.py |
| Audio delivery | B2 HEAD/GET streamed through a 1 MiB iterator with Range validation. | backend/server.py:8217-8675 |
| PDF | EXISTING_INTERNAL_OR_REPORT_PDF_ONLY | backend/source_ingestion.py; scripts/bulk_publishing_pipeline.py |
