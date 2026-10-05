#!/usr/bin/env bash
set -Eeuo pipefail
export PERF_READER_WORKTREE=${PERF_READER_WORKTREE:-/tmp/earnalism-reader-true-viewport-pagination}
node scripts/profile_reader_real_e2e.mjs
