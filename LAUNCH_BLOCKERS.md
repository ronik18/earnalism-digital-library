# Launch Blockers

| Area | Severity | Blocker | Fix |
| --- | --- | --- | --- |
| seo | HIGH | Homepage raw HTML failed check: dracula_first. | Make the static homepage snapshot Dracula-first and remove broad catalog claims. |
| ux_conversion | HIGH | Missing UX/conversion signal: book_buy_cta. | Restore the missing CTA or trust statement. |
| security | CRITICAL | Potential committed secrets in ['backend/tests/test_b2_audiobook_routing.py', 'internal/audiobook_lab/scripts/test_cloudinary_credentials_and_cover_hook.py', 'internal/audiobook_lab/storage_containment/ensure_wave1_b2_destination_key.sh', 'internal/audiobook_lab/storage_containment/run_wave1_one_by_one_auto.sh', 'internal/audiobook_lab/storage_containment/run_wave1_restore_then_migrate.sh', 'internal/audiobook_lab/storage_containment/run_wave1_with_guard.sh', 'internal/audiobook_lab/storage_containment/unapproved_direct_audio_remediation_commands.sh', 'internal/earnalism_intelligence/bengali_audiobook_package_v2_wave1_env_bootstrap.sh']. | Rotate and remove secrets immediately. |
| rights_source_readiness | HIGH | First batch has no approved real source metadata in the dry-run evidence. | Backfill source_url, source_license, source_hash, content_hash, and provenance_hash before publication. |
