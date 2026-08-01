#!/usr/bin/env bash
# Source this file before running the Wave-1 guarded migration.
# Replace ... with runtime credentials in your secure shell.

export ALLOW_REMOTE_MUTATION=true
# For run_wave1_with_guard.sh (default scoped targets path), keep this token:
export OWNER_APPROVAL_TOKEN='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'
# If using run_wave1_one_by_one_with_postcheck.sh with explicit slugs, use:
# AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.
export REVIEWED_INVENTORY_SHA256='21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c'
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true

# Private destination (production/QA private)
export B2_ACCESS_KEY_ID='REPLACE_WITH_PRIVATE_B2_ACCESS_KEY_ID'
export B2_SECRET_ACCESS_KEY='REPLACE_WITH_PRIVATE_B2_SECRET_ACCESS_KEY'
export B2_S3_ENDPOINT='REPLACE_WITH_PRIVATE_B2_S3_ENDPOINT'
export B2_REGION='REPLACE_WITH_PRIVATE_B2_REGION'
export B2_PRIVATE_QA_BUCKET='REPLACE_WITH_PRIVATE_QA_BUCKET'
export B2_PRIVATE_QA_ACCESS_KEY_ID="$B2_ACCESS_KEY_ID"
export B2_PRIVATE_QA_SECRET_ACCESS_KEY="$B2_SECRET_ACCESS_KEY"
export B2_PRIVATE_QA_S3_ENDPOINT="$B2_S3_ENDPOINT"
export B2_PRIVATE_QA_REGION="$B2_REGION"

# Public/source fallback storage creds (only if migrating Cloudinary-sourced objects)
export B2_SOURCE_ACCESS_KEY_ID='REPLACE_WITH_SOURCE_B2_ACCESS_KEY_ID'
export B2_SOURCE_SECRET_ACCESS_KEY='REPLACE_WITH_SOURCE_B2_SECRET_ACCESS_KEY'
export B2_SOURCE_S3_ENDPOINT='REPLACE_WITH_SOURCE_B2_S3_ENDPOINT'
export B2_SOURCE_REGION='REPLACE_WITH_SOURCE_B2_REGION'

echo "Wave-1 env bootstrap loaded. Fill in credential values before running migration." 
