# Audiobook Readiness Report

Status: `PASS_WITH_WARNINGS`

| Asset Signal | Value |
| --- | --- |
| public_audio_dir_exists | True |
| file_count | 25 |
| total_bytes | 102094631 |
| mp3_count | 5 |
| timestamp_json_count | 15 |
| vtt_count | 5 |

| Guard | Present |
| --- | --- |
| remote_upload_guard_present | True |
| voice_pipeline_dry_run_only | True |
| package_contains_non_dry_audio_scripts | True |
| remote_guard_test_detected | True |

Detailed asset audit: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/audio_asset_audit.json`

## Public Audio Asset Audit

| File | Book | Lang | Bytes | Duration ms | Rights | QA | Timestamps | VTT | Waveform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frontend/public/audio/ben/book-0deb35c750.mp3 | book-0deb35c750 | ben | 4331433 | 721816 | UNKNOWN | NEEDS_SYNC_OR_WAVEFORM_REVIEW | True | True | False |
| frontend/public/audio/ben/book-63afd5e9be.mp3 | book-63afd5e9be | ben | 5195041 | 865733 | UNKNOWN | NEEDS_SYNC_OR_WAVEFORM_REVIEW | True | True | False |
| frontend/public/audio/ben/book-d19e96859f.mp3 | book-d19e96859f | ben | 2791515 | 465154 | UNKNOWN | NEEDS_SYNC_OR_WAVEFORM_REVIEW | True | True | False |
| frontend/public/audio/ben/ginni.mp3 | ginni | ben | 2873487 | 478800 | UNKNOWN | NEEDS_SYNC_OR_WAVEFORM_REVIEW | True | True | False |
| frontend/public/audio/en/bharat-at-the-crossroads.mp3 | bharat-at-the-crossroads | en | 82189079 | 13698074 | UNKNOWN | NEEDS_SYNC_OR_WAVEFORM_REVIEW | True | True | False |

Full audiobook launch remains blocked until each candidate has linked approved rights, QA-passed audio, and explicit storage/provider publish confirmation.
