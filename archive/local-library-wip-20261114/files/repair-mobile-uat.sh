#!/usr/bin/env bash

# Earnalism mobile-UAT repair and verification orchestrator.
#
# This script:
#   1. Lets Codex repair validated application, test, and Playwright-config defects.
#   2. Prevents obvious test weakening and title-specific backend hacks.
#   3. Builds and deploys/starts the patched application.
#   4. Installs matching Chromium, Firefox, and WebKit binaries.
#   5. Runs targeted, contrast, Chromium, Firefox, and WebKit tests.
#   6. Runs the authoritative full UAT regression.
#   7. Reports 10/10 only when the real final report proves it.
#
# Required:
#   UAT_BASE_URL
#
# For a local environment, also provide UAT_START_CMD unless Playwright's
# config already has a webServer configuration.
#
# For a remote UAT environment, provide UAT_DEPLOY_CMD.
#
# Examples:
#
#   Local:
#     UAT_BASE_URL="http://127.0.0.1:8000" \
#     UAT_START_CMD="npm run uat:start" \
#     bash repair-mobile-uat.sh
#
#   Remote UAT:
#     UAT_BASE_URL="https://uat.example.com" \
#     UAT_DEPLOY_CMD="./scripts/deploy-uat.sh" \
#     bash repair-mobile-uat.sh
#
# Optional:
#   CODEX_MODEL=gpt-5.3-codex-spark
#   MAX_REPAIR_ROUNDS=3
#   UAT_HEALTH_URL=https://uat.example.com/health
#   UAT_FULL_COMMAND='npm run uat:full'
#   HTTPS_PROXY=...
#   PLAYWRIGHT_DOWNLOAD_HOST=...
#
# Never point UAT_BASE_URL to production.

set -Eeuo pipefail
IFS=$'\n\t'

###############################################################################
# Configuration
###############################################################################

ROOT="${REPO_ROOT:-$(pwd)}"
MODEL="${CODEX_MODEL:-gpt-5.3-codex-spark}"
MAX_REPAIR_ROUNDS="${MAX_REPAIR_ROUNDS:-3}"
UAT_BASE_URL="${UAT_BASE_URL:-}"
UAT_HEALTH_URL="${UAT_HEALTH_URL:-$UAT_BASE_URL}"
UAT_START_CMD="${UAT_START_CMD:-}"
UAT_DEPLOY_CMD="${UAT_DEPLOY_CMD:-}"
UAT_FULL_COMMAND="${UAT_FULL_COMMAND:-npm run uat:full}"
UAT_ALREADY_DEPLOYED="${UAT_ALREADY_DEPLOYED:-0}"

REAL_USER_SPEC="tests/e2e/earnalism-real-user-journey.spec.js"
CONTRAST_SCRIPT="frontend/scripts/reader-typography-contrast.mjs"
SHARED_BROWSERS="$ROOT/.playwright-browsers"

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')"
EVIDENCE_ROOT="$ROOT/uat/evidence/automated-repair-$RUN_ID"
ORCHESTRATOR_REPORT="$ROOT/uat/orchestrator-report-$RUN_ID.json"

SERVER_PID=""
SUCCESS=0
LAST_FAILURE_DIR=""

###############################################################################
# Helpers
###############################################################################

log() {
  printf '\n[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

die() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    log "Stopping locally started UAT process: $SERVER_PID"
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT
trap 'printf "\nInterrupted at line %s\n" "$LINENO" >&2' INT TERM

run_logged() {
  local output_file="$1"
  shift

  mkdir -p "$(dirname "$output_file")"

  set +e
  "$@" 2>&1 | tee "$output_file"
  local status=${PIPESTATUS[0]}
  set -e

  printf '\nEXIT_CODE=%s\n' "$status" >> "$output_file"
  return "$status"
}

run_shell_logged() {
  local output_file="$1"
  local command_string="$2"

  mkdir -p "$(dirname "$output_file")"

  set +e
  bash -lc "$command_string" 2>&1 | tee "$output_file"
  local status=${PIPESTATUS[0]}
  set -e

  printf '\nEXIT_CODE=%s\n' "$status" >> "$output_file"
  return "$status"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    die "Required command is unavailable: $1"
}

has_npm_script() {
  local directory="$1"
  local script_name="$2"

  (
    cd "$directory"

    SCRIPT_NAME="$script_name" node -e '
      const pkg = require("./package.json");
      const name = process.env.SCRIPT_NAME;
      process.exit(pkg.scripts && pkg.scripts[name] ? 0 : 1);
    '
  )
}

dependency_fingerprint() {
  {
    git -C "$ROOT" ls-files
    git -C "$ROOT" ls-files --others --exclude-standard
  } |
    awk '
      /(^|\/)(package\.json|package-lock\.json|npm-shrinkwrap\.json|pnpm-lock\.yaml|yarn\.lock)$/ {
        print
      }
    ' |
    sort -u |
    while IFS= read -r relative_path; do
      if [[ -f "$ROOT/$relative_path" ]]; then
        shasum -a 256 "$ROOT/$relative_path"
      fi
    done |
    shasum -a 256 |
    awk '{print $1}'
}

install_locked_dependencies() {
  local directory="$1"

  [[ -f "$directory/package.json" ]] || return 0

  log "Synchronizing dependencies in $directory"

  if [[ -f "$directory/pnpm-lock.yaml" ]]; then
    require_command pnpm
    run_logged \
      "$EVIDENCE_ROOT/dependencies/$(basename "$directory")-pnpm.log" \
      pnpm --dir "$directory" install --frozen-lockfile
  elif [[ -f "$directory/package-lock.json" ]]; then
    run_logged \
      "$EVIDENCE_ROOT/dependencies/$(basename "$directory")-npm.log" \
      npm --prefix "$directory" install --no-audit --no-fund
  elif [[ -f "$directory/yarn.lock" ]]; then
    require_command yarn
    run_logged \
      "$EVIDENCE_ROOT/dependencies/$(basename "$directory")-yarn.log" \
      yarn --cwd "$directory" install --frozen-lockfile
  else
    die "No lockfile found for dependency changes in $directory"
  fi
}

host_from_url() {
  URL_VALUE="$1" python3 - <<'PY'
import os
from urllib.parse import urlparse

value = os.environ["URL_VALUE"]
print((urlparse(value).hostname or "").lower())
PY
}

is_local_host() {
  local host="$1"

  case "$host" in
    localhost | 127.0.0.1 | ::1)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

playwright_config_has_webserver() {
  rg -q \
    'webServer[[:space:]]*:' \
    playwright.config.* \
    2>/dev/null
}

wait_for_url() {
  local url="$1"
  local attempts="${2:-60}"

  log "Waiting for UAT endpoint: $url"

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if curl \
      --silent \
      --show-error \
      --fail \
      --max-time 10 \
      "$url" \
      >/dev/null 2>&1; then
      log "UAT endpoint is reachable."
      return 0
    fi

    sleep 2
  done

  return 1
}

###############################################################################
# Preconditions
###############################################################################

cd "$ROOT"

[[ -d .git ]] || die "Run this script from the Git repository root."
[[ -n "$UAT_BASE_URL" ]] || die "UAT_BASE_URL must be supplied."
[[ -f "$REAL_USER_SPEC" ]] ||
  die "Missing real-user specification: $REAL_USER_SPEC"
[[ -f "$CONTRAST_SCRIPT" ]] ||
  die "Missing contrast script: $CONTRAST_SCRIPT"
[[ -f docs/MOBILE_UAT_MASTER.md ]] ||
  die "Missing docs/MOBILE_UAT_MASTER.md"

require_command git
require_command node
require_command npm
require_command python3
require_command curl
require_command codex
require_command rg
require_command tee
require_command shasum

UAT_HOST="$(host_from_url "$UAT_BASE_URL")"

case "$UAT_HOST" in
  theearnalism.com | www.theearnalism.com)
    die "Production UAT is prohibited. Supply a local, preview, staging, or UAT URL."
    ;;
esac

mkdir -p "$EVIDENCE_ROOT"

export UAT_BASE_URL
export E2E_BASE_URL="$UAT_BASE_URL"
export PLAYWRIGHT_BASE_URL="$UAT_BASE_URL"

log "Repository: $ROOT"
log "UAT target: $UAT_BASE_URL"
log "Codex model: $MODEL"
log "Evidence: $EVIDENCE_ROOT"

git status --short \
  > "$EVIDENCE_ROOT/pre-run-git-status.log"

git diff --binary \
  > "$EVIDENCE_ROOT/pre-run-working-tree.patch"

git rev-parse HEAD \
  > "$EVIDENCE_ROOT/pre-run-commit.txt"

###############################################################################
# Dependency preflight
###############################################################################

if [[ ! -d "$ROOT/node_modules" ]]; then
  install_locked_dependencies "$ROOT"
fi

if [[ -f "$ROOT/frontend/package.json" ]] &&
   [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  install_locked_dependencies "$ROOT/frontend"
fi

PW_CLI="$ROOT/node_modules/.bin/playwright"
[[ -x "$PW_CLI" ]] ||
  die "Pinned root Playwright CLI is unavailable at $PW_CLI"

###############################################################################
# Codex repair prompt
###############################################################################

write_codex_prompt() {
  local round="$1"
  local previous_evidence="$2"
  local prompt_file="$3"

  cat > "$prompt_file" <<PROMPT
You are repairing the Earnalism mobile UAT implementation.

MODEL MODE
Work efficiently with short deterministic repository-inspection loops.
Do not run Playwright or launch browsers inside the Codex sandbox. The host
script executes browser validation outside Codex.

READ FIRST
- AGENTS.md, when present
- docs/MOBILE_UAT_MASTER.md
- docs/reading-pass-access.md, when present
- uat/final-report.json, when present
- uat/evidence/commands.log, when present
- tests/e2e/earnalism-real-user-journey.spec.js
- frontend/scripts/reader-typography-contrast.mjs
- Playwright configuration
- root and frontend package manifests
- backend/catalog_truth.py
- frontend/src/pages/BookDetail.jsx
- homepage, pricing, reader, paywall, and audiobook components
- current git diff
- previous repair evidence: ${previous_evidence:-none}

CURRENT APPROVED PRODUCT CONTRACT
- The first 3 server-defined canonical text pages are public.
- The first 180 seconds of each approved audiobook are public.
- Protected continuation requires authentication and positive Reading Pass
  balance.
- Reading Pass time is usable across any eligible book or audiobook.
- Dracula's current controlled release contract has text reading enabled and
  audio disabled.
- Controlled-publication truth must override conflicting database or editorial
  release fields.
- Tests must target UAT_BASE_URL and must never silently fall back to
  production.

CURRENT CONFIRMED FAILURES
- The Dracula backend response exposes audio_enabled=true although the
  independent controlled release contract requires false.
- Dracula book and reader states may expose approved-audio badges or controls
  while release copy says audio is unavailable or in preparation.
- Homepage tests contain brittle whole-body marketing-string assertions instead
  of validating visible CTA behavior.
- Customer-facing homepage and pricing copy still describes Chapter 1 as the
  preview instead of the first 3 canonical pages.
- Pricing must explain the first 3 pages, first 3 audiobook minutes, and
  cross-title Reading Pass use accurately.
- Playwright currently defines only a Chromium project; Firefox and WebKit
  projects are required.
- The contrast script and root test runner must resolve one exact Playwright
  version and a caller-supplied PLAYWRIGHT_BROWSERS_PATH.
- The authoritative full UAT command must be executable non-interactively and
  must regenerate uat/final-report.json.

REQUIRED APPLICATION FIXES
1. Correct the generic controlled-publication merge order.
   Controlled release fields must have final authority over all release-
   sensitive database/editorial values.

2. When controlled audio is disabled, atomically normalize every related public
   field using actual project field names:
   - audio_enabled=false
   - audiobook_enabled=false
   - audiobook=null
   - audiobook_assets={}
   - no provider identifiers
   - no audio URLs or manifests
   - no audio duration or preview asset
   - no approved-audio badge
   - no listening CTA eligibility

3. Do not add a Dracula-specific production conditional. Dracula must be a
   fixture proving the generic controlled-release rule.

4. Make frontend audio availability require a complete, internally consistent
   approved audio record. A Boolean alone must not reveal controls.

5. Remove contradictory Dracula states. When audio is disabled, do not render:
   - Audiobook approved
   - Listening room approved
   - Listen in reader
   - Begin listening
   - provider-backed audio approval copy
   - audio player, manifest, URL, or hidden payload

6. Replace stale preview and entitlement copy throughout customer-facing
   surfaces:
   - no "Chapter 1 remains free"
   - no "Read Chapter 1 free"
   - no "Chapter 1 is on us"
   - no "Begin every book with Chapter 1"
   - no incompatible seven-day pass wording
   Use first 3 canonical pages, first 3 approved-audio minutes, and cross-title
   Reading Pass language accurately.

7. Make pricing products title-neutral. Do not describe a pass as being only
   for Dracula when it applies to any eligible title.

REQUIRED TEST FIXES
1. Preserve strict independent release-contract assertions. Do not derive
   expected values from the API response under test.

2. Replace whole-document marketing-substring assertions with scoped,
   role-based visible CTA assertions:
   - "Enter the Library" links to /library
   - "Browse the Complete Library" links to /library when that CTA exists
   Scope duplicate names to the intended page section.

3. Add or preserve regression coverage proving that conflicting database audio
   fields cannot override controlled no-audio truth.

4. Add or preserve tests proving disabled audio removes metadata, assets,
   controls, badges, URLs, and manifests.

5. Keep strict tests for:
   - first 3 public text pages
   - blocked page 4 without entitlement
   - first 180 public audiobook seconds for approved audio
   - protected continuation
   - cross-title Reading Pass wording

6. Configure Playwright projects named exactly:
   - chromium
   - firefox
   - webkit
   Preserve all existing baseURL, webServer, video, trace, screenshot, timeout,
   and output settings.

7. Make Playwright require UAT_BASE_URL. Production fallback is prohibited.

8. Ensure npm run uat:full exists. It must invoke the existing authoritative
   complete UAT regression and regenerate uat/final-report.json. If an
   equivalent runner already exists, preserve it and add only a stable alias.
   It must return nonzero for failed, blocked, skipped, unverified, or untested
   required cases.

ANTI-GAMING RULES
Never:
- skip, disable, filter out, soften, or delete a required test;
- change an assertion merely to accept incorrect current behavior;
- add test.only, test.skip, test.fixme, describe.skip, or expect.soft;
- lower contrast thresholds;
- blindly update screenshots or snapshots;
- edit UAT totals or scores manually;
- mark unexecuted or blocked cases PASS;
- hard-code Dracula in generic backend release logic;
- expose protected text or audio;
- use production data or live financial operations;
- overwrite unrelated user changes.

IMPLEMENTATION STANDARD
- Make minimal reusable changes.
- Preserve existing architecture and conventions.
- Add tests with each root-cause fix.
- Do not stop after describing a plan.
- Do not attempt browser execution.
- Run only safe static checks when useful.

At completion report:
- validated root causes;
- files changed;
- application fixes;
- test/configuration fixes;
- dependency changes;
- exact host-shell validation commands.
PROMPT
}

run_codex_round() {
  local round="$1"
  local previous_evidence="$2"
  local round_dir="$EVIDENCE_ROOT/round-$round"
  local prompt_file="$round_dir/codex-prompt.txt"
  local codex_log="$round_dir/codex.jsonl"

  mkdir -p "$round_dir"
  write_codex_prompt "$round" "$previous_evidence" "$prompt_file"

  local before_fingerprint
  local after_fingerprint

  before_fingerprint="$(dependency_fingerprint)"

  log "Codex repair round $round"

  if ! run_logged \
    "$codex_log" \
    codex exec \
      --model "$MODEL" \
      --sandbox workspace-write \
      -c 'approval_policy="never"' \
      --json \
      -c 'model_reasoning_effort="low"' \
      "$(cat "$prompt_file")"; then
    return 1
  fi

  after_fingerprint="$(dependency_fingerprint)"

  if [[ "$before_fingerprint" != "$after_fingerprint" ]]; then
    log "Dependency manifests changed; synchronizing locked dependencies."
    install_locked_dependencies "$ROOT"

    if [[ -f "$ROOT/frontend/package.json" ]]; then
      install_locked_dependencies "$ROOT/frontend"
    fi
  fi

  LAST_FAILURE_DIR="$round_dir"
  return 0
}

###############################################################################
# Patch integrity checks
###############################################################################

validate_patch_integrity() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/integrity"

  mkdir -p "$output_dir"

  if ! run_logged \
    "$output_dir/git-diff-check.log" \
    git diff --check; then
    return 1
  fi

  git diff --name-only \
    > "$output_dir/changed-files.log"

  git diff --unified=20 \
    > "$output_dir/current.patch"

  if git diff -U0 -- tests frontend/scripts playwright.config.* 2>/dev/null |
     grep -E \
       '^\+.*(test|describe)\.(skip|fixme|only)|^\+.*expect\.soft' \
       > "$output_dir/prohibited-test-changes.log"; then
    printf 'Prohibited test weakening was detected.\n' >&2
    return 1
  fi

  if git diff --name-only |
     grep -E '(^|/)(__snapshots__|.*\.snap$)' \
     > "$output_dir/snapshot-changes.log"; then
    printf 'Snapshot changes require explicit human review and are rejected.\n' >&2
    return 1
  fi

  if [[ -f backend/catalog_truth.py ]] &&
     git diff -U0 -- backend/catalog_truth.py |
     grep -Ei '^\+.*(slug|book_id|book_slug).*dracula' \
     > "$output_dir/dracula-special-case.log"; then
    printf 'A Dracula-specific backend conditional was detected.\n' >&2
    return 1
  fi

  local stale_copy_regex
  stale_copy_regex='chapter 1 remains free|read chapter 1 free|chapter 1 is on us|begin every book with chapter 1|chapter 1 stays free|7[- ]day reading pass'

  if rg -n -i \
    "$stale_copy_regex" \
    frontend/src \
    > "$output_dir/stale-product-copy.log" 2>&1; then
    printf 'Stale Chapter 1 or seven-day product copy remains.\n' >&2
    return 1
  fi

  return 0
}

###############################################################################
# Static validation
###############################################################################

run_static_validation() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/static"

  mkdir -p "$output_dir"

  if [[ -f backend/catalog_truth.py ]]; then
    run_logged \
      "$output_dir/backend-compile.log" \
      python3 -m py_compile backend/catalog_truth.py ||
      return 1
  fi

  if [[ -f frontend/package.json ]] &&
     has_npm_script frontend build; then
    run_logged \
      "$output_dir/frontend-build.log" \
      npm --prefix frontend run build ||
      return 1
  fi

  if has_npm_script "$ROOT" lint; then
    run_logged \
      "$output_dir/root-lint.log" \
      npm run lint ||
      return 1
  fi

  return 0
}

###############################################################################
# Playwright preparation
###############################################################################

playwright_version() {
  local directory="$1"

  (
    cd "$directory"
    node -e '
      for (const candidate of [
        "playwright-core/package.json",
        "playwright/package.json",
        "@playwright/test/package.json",
      ]) {
        try {
          console.log(require(candidate).version);
          process.exit(0);
        } catch {}
      }
      process.exit(1);
    '
  )
}

prepare_playwright() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/playwright"

  mkdir -p "$output_dir" "$SHARED_BROWSERS"

  local root_version
  local frontend_version=""

  root_version="$(playwright_version "$ROOT")" ||
    {
      printf 'Root Playwright package is unavailable.\n' >&2
      return 1
    }

  if [[ -f frontend/package.json ]]; then
    frontend_version="$(playwright_version "$ROOT/frontend")" ||
      {
        printf 'Frontend Playwright package is unavailable.\n' >&2
        return 1
      }
  fi

  {
    printf 'root=%s\n' "$root_version"
    printf 'frontend=%s\n' "$frontend_version"
  } | tee "$output_dir/versions.log"

  if [[ -n "$frontend_version" ]] &&
     [[ "$root_version" != "$frontend_version" ]]; then
    printf \
      'Root and frontend Playwright versions differ: %s vs %s\n' \
      "$root_version" \
      "$frontend_version" \
      >&2
    return 1
  fi

  log "Installing matching Playwright browsers into $SHARED_BROWSERS"

  if ! run_logged \
    "$output_dir/browser-install.log" \
    env \
      PLAYWRIGHT_BROWSERS_PATH="$SHARED_BROWSERS" \
      "$PW_CLI" install chromium firefox webkit; then

    if rg -q \
      'ENOTFOUND|EAI_AGAIN|certificate|proxy|timed out|network' \
      "$output_dir/browser-install.log"; then
      die "Playwright browser download is blocked by DNS/network policy. Configure HTTPS_PROXY or PLAYWRIGHT_DOWNLOAD_HOST, then rerun."
    fi

    return 1
  fi

  run_logged \
    "$output_dir/browser-list.log" \
    env \
      PLAYWRIGHT_BROWSERS_PATH="$SHARED_BROWSERS" \
      "$PW_CLI" install --list ||
    return 1

  run_logged \
    "$output_dir/project-list.log" \
    env \
      UAT_BASE_URL="$UAT_BASE_URL" \
      E2E_BASE_URL="$UAT_BASE_URL" \
      PLAYWRIGHT_BASE_URL="$UAT_BASE_URL" \
      PLAYWRIGHT_BROWSERS_PATH="$SHARED_BROWSERS" \
      "$PW_CLI" test "$REAL_USER_SPEC" --list ||
    return 1

  for project in chromium firefox webkit; do
    if ! grep -q "\[$project\]" "$output_dir/project-list.log"; then
      printf 'Missing Playwright project: %s\n' "$project" >&2
      return 1
    fi
  done

  set +e

  (
    cd "$ROOT"

    PLAYWRIGHT_BROWSERS_PATH="$SHARED_BROWSERS" \
      node <<'NODE'
const fs = require("node:fs");

const candidates = [
  "@playwright/test",
  "playwright",
  "playwright-core",
];

let playwright;
let loadedPackage;

for (const candidate of candidates) {
  try {
    const value = require(candidate);

    if (
      value &&
      value.chromium &&
      value.firefox &&
      value.webkit
    ) {
      playwright = value;
      loadedPackage = candidate;
      break;
    }
  } catch {
    // Continue.
  }
}

if (!playwright) {
  throw new Error("No installed Playwright package exposes browser launchers.");
}

console.log(`Loaded package: ${loadedPackage}`);

const browserTypes = {
  chromium: playwright.chromium,
  firefox: playwright.firefox,
  webkit: playwright.webkit,
};

(async () => {
  let failures = 0;

  for (const [name, browserType] of Object.entries(browserTypes)) {
    let browser;

    try {
      const executable = browserType.executablePath();

      console.log(`${name} executable: ${executable}`);
      console.log(`${name} exists: ${fs.existsSync(executable)}`);

      if (!fs.existsSync(executable)) {
        throw new Error(`Missing executable: ${executable}`);
      }

      browser = await browserType.launch({ headless: true });

      const page = await browser.newPage({
        viewport: {
          width: 390,
          height: 844,
        },
      });

      await page.setContent(`
        <!doctype html>
        <html lang="en">
          <body>
            <h1>Earnalism Playwright smoke test</h1>
          </body>
        </html>
      `);

      const heading = await page.locator("h1").textContent();

      if (heading !== "Earnalism Playwright smoke test") {
        throw new Error(`Unexpected heading: ${String(heading)}`);
      }

      console.log(`${name}: PASS`);
    } catch (error) {
      failures += 1;
      console.error(`${name}: FAIL`);
      console.error(error?.stack || error);
    } finally {
      await browser?.close().catch(() => undefined);
    }
  }

  process.exitCode = failures === 0 ? 0 : 1;
})();
NODE
  ) 2>&1 | tee "$output_dir/browser-smoke.log"

  local smoke_status=${PIPESTATUS[0]}
  set -e

  return "$smoke_status"
}

###############################################################################
# Runtime deployment/start
###############################################################################

refresh_runtime() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/runtime"

  mkdir -p "$output_dir"

  if [[ -n "$UAT_DEPLOY_CMD" ]]; then
    log "Deploying the patched application to UAT."

    run_shell_logged \
      "$output_dir/deploy.log" \
      "$UAT_DEPLOY_CMD" ||
      return 1
  fi

  if [[ -n "$UAT_START_CMD" ]]; then
    if [[ -n "$SERVER_PID" ]] &&
       kill -0 "$SERVER_PID" 2>/dev/null; then
      kill "$SERVER_PID" 2>/dev/null || true
      wait "$SERVER_PID" 2>/dev/null || true
    fi

    log "Starting local UAT application."

    (
      cd "$ROOT"
      bash -lc "$UAT_START_CMD"
    ) > "$output_dir/local-server.log" 2>&1 &

    SERVER_PID=$!
  fi

  if is_local_host "$UAT_HOST"; then
    if [[ -z "$UAT_START_CMD" ]] &&
       ! playwright_config_has_webserver; then
      printf \
        'Local UAT requires UAT_START_CMD or Playwright webServer configuration.\n' \
        >&2
      return 1
    fi
  else
    if [[ -z "$UAT_DEPLOY_CMD" ]] &&
       [[ "$UAT_ALREADY_DEPLOYED" != "1" ]]; then
      printf \
        'Remote UAT requires UAT_DEPLOY_CMD or explicit UAT_ALREADY_DEPLOYED=1.\n' \
        >&2
      return 1
    fi
  fi

  if playwright_config_has_webserver &&
     is_local_host "$UAT_HOST" &&
     [[ -z "$UAT_START_CMD" ]]; then
    log "Playwright webServer will start the local application."
    return 0
  fi

  wait_for_url "$UAT_HEALTH_URL" 90 ||
    {
      printf 'UAT endpoint did not become healthy.\n' >&2
      return 1
    }

  return 0
}

###############################################################################
# Targeted and browser gates
###############################################################################

log_contains_skipped_cases() {
  local file="$1"

  grep -Ei \
    '(^|[^a-z])(skipped|not run|untested|unverified)([^a-z]|$)' \
    "$file" \
    >/dev/null 2>&1
}

run_browser_gates() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/browser-gates"

  mkdir -p "$output_dir"

  local common_env=(
    env
    UAT_BASE_URL="$UAT_BASE_URL"
    E2E_BASE_URL="$UAT_BASE_URL"
    PLAYWRIGHT_BASE_URL="$UAT_BASE_URL"
    PLAYWRIGHT_BROWSERS_PATH="$SHARED_BROWSERS"
  )

  log "Running the five previously failing cases."

  if ! run_logged \
    "$output_dir/targeted-five.log" \
    "${common_env[@]}" \
    "$PW_CLI" test \
      "$REAL_USER_SPEC" \
      --project=chromium \
      --grep \
      'backend catalog truth gate|homepage desktop|Dracula book page|Dracula reader page|pricing page' \
      --reporter=line \
      --workers=1; then
    return 1
  fi

  if log_contains_skipped_cases "$output_dir/targeted-five.log"; then
    printf 'Targeted suite contains skipped or unverified cases.\n' >&2
    return 1
  fi

  log "Running reader typography contrast assertions."

  if ! run_logged \
    "$output_dir/contrast.log" \
    "${common_env[@]}" \
    node "$CONTRAST_SCRIPT"; then
    return 1
  fi

  log "Running complete Chromium real-user audit."

  if ! run_logged \
    "$output_dir/chromium-real-user-audit.log" \
    "${common_env[@]}" \
    npm run ux:real-user-video-audit -- --reporter=line; then
    return 1
  fi

  if log_contains_skipped_cases "$output_dir/chromium-real-user-audit.log"; then
    printf 'Chromium audit contains skipped or unverified cases.\n' >&2
    return 1
  fi

  log "Running Firefox and WebKit real-user audits."

  if ! run_logged \
    "$output_dir/firefox-webkit.log" \
    "${common_env[@]}" \
    "$PW_CLI" test \
      "$REAL_USER_SPEC" \
      --project=firefox \
      --project=webkit \
      --reporter=line \
      --workers=1; then
    return 1
  fi

  if log_contains_skipped_cases "$output_dir/firefox-webkit.log"; then
    printf 'Cross-browser audit contains skipped or unverified cases.\n' >&2
    return 1
  fi

  return 0
}

###############################################################################
# Full regression and final-report verification
###############################################################################

run_full_regression() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/full-regression"

  mkdir -p "$output_dir"

  log "Running authoritative complete UAT regression."

  local quoted_base
  local quoted_browser_path

  printf -v quoted_base '%q' "$UAT_BASE_URL"
  printf -v quoted_browser_path '%q' "$SHARED_BROWSERS"

  local command_string
  command_string="
    cd $(printf '%q' "$ROOT")
    export UAT_BASE_URL=$quoted_base
    export E2E_BASE_URL=$quoted_base
    export PLAYWRIGHT_BASE_URL=$quoted_base
    export PLAYWRIGHT_BROWSERS_PATH=$quoted_browser_path
    $UAT_FULL_COMMAND
  "

  run_shell_logged \
    "$output_dir/full-regression.log" \
    "$command_string"
}

verify_final_report() {
  local round="$1"
  local output_dir="$EVIDENCE_ROOT/round-$round/final-verification"
  local report="$ROOT/uat/final-report.json"

  mkdir -p "$output_dir"

  [[ -f "$report" ]] ||
    {
      printf 'Missing authoritative report: %s\n' "$report" >&2
      return 1
    }

  python3 - "$report" "$ORCHESTRATOR_REPORT" <<'PY'
import json
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

data = json.loads(source_path.read_text(encoding="utf-8"))


def normalize_key(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def walk(value):
    if isinstance(value, dict):
        yield value

        for nested in value.values():
            yield from walk(nested)

    elif isinstance(value, list):
        for nested in value:
            yield from walk(nested)


def as_nonnegative_int(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)

    if isinstance(value, str):
        cleaned = value.strip()

        if cleaned.isdigit():
            return int(cleaned)

    return None


aliases = {
    "pass": {"pass", "passed", "passes"},
    "failed": {"failed", "fail", "failures"},
    "blocked": {"blocked", "blocks"},
    "untested": {
        "untested",
        "not_run",
        "notrun",
        "not_executed",
        "unverified",
        "skipped",
    },
}

candidates = []

for mapping in walk(data):
    normalized = {
        normalize_key(key): value
        for key, value in mapping.items()
    }

    counts = {}

    for canonical, names in aliases.items():
        found = None

        for name in names:
            if name in normalized:
                found = as_nonnegative_int(normalized[name])

                if found is not None:
                    break

        if found is not None:
            counts[canonical] = found

    if all(name in counts for name in ("pass", "failed", "blocked", "untested")):
        total = sum(counts.values())

        if total > 0:
            candidates.append((total, counts))

if not candidates:
    print(
        "Unable to locate PASS/FAILED/BLOCKED/UNTESTED totals "
        "in uat/final-report.json",
        file=sys.stderr,
    )
    sys.exit(2)

_, counts = max(candidates, key=lambda item: item[0])
total = sum(counts.values())
score = 10.0 * counts["pass"] / total

open_high_priority = []
closed_statuses = {
    "closed",
    "resolved",
    "fixed",
    "passed",
    "pass",
    "done",
    "verified",
}

for mapping in walk(data):
    normalized = {
        normalize_key(key): value
        for key, value in mapping.items()
    }

    severity = str(normalized.get("severity", "")).upper()
    status = normalize_key(normalized.get("status", ""))

    if severity in {"P0", "P1", "P2"} and status not in closed_statuses:
        identifier = (
            normalized.get("id")
            or normalized.get("defect_id")
            or normalized.get("test_id")
            or "unknown"
        )

        open_high_priority.append(
            {
                "id": str(identifier),
                "severity": severity,
                "status": status or "unknown",
            }
        )

summary = {
    "source_report": str(source_path),
    "totals": counts,
    "total": total,
    "score": round(score, 6),
    "open_p0_p2": open_high_priority,
    "valid_10_out_of_10": (
        counts["pass"] == total
        and counts["failed"] == 0
        and counts["blocked"] == 0
        and counts["untested"] == 0
        and not open_high_priority
        and abs(score - 10.0) < 1e-9
    ),
}

output_path.write_text(
    json.dumps(summary, indent=2) + "\n",
    encoding="utf-8",
)

print(json.dumps(summary, indent=2))

if not summary["valid_10_out_of_10"]:
    sys.exit(1)
PY
}

###############################################################################
# Main repair loop
###############################################################################

previous_evidence=""

for ((round = 1; round <= MAX_REPAIR_ROUNDS; round += 1)); do
  log "============================================================"
  log "Repair and validation round $round of $MAX_REPAIR_ROUNDS"
  log "============================================================"

  round_dir="$EVIDENCE_ROOT/round-$round"
  mkdir -p "$round_dir"

  if ! run_codex_round "$round" "$previous_evidence"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! validate_patch_integrity "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! run_static_validation "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! prepare_playwright "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! refresh_runtime "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! run_browser_gates "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! run_full_regression "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  if ! verify_final_report "$round"; then
    previous_evidence="$round_dir"
    continue
  fi

  SUCCESS=1
  break
done

###############################################################################
# Final output
###############################################################################

git status --short \
  > "$EVIDENCE_ROOT/post-run-git-status.log"

git diff --check \
  > "$EVIDENCE_ROOT/post-run-diff-check.log" 2>&1 || true

git diff --binary \
  > "$EVIDENCE_ROOT/final-working-tree.patch"

if [[ "$SUCCESS" -eq 1 ]]; then
  log "============================================================"
  log "FINAL UAT RESULT: PASSED"
  log "SCORE: 10.00 / 10.00"
  log "Evidence: $EVIDENCE_ROOT"
  log "Report: $ORCHESTRATOR_REPORT"
  log "============================================================"

  cat "$ORCHESTRATOR_REPORT"
  exit 0
fi

log "============================================================"
log "FINAL UAT RESULT: NOT 10/10"
log "The script preserved the truthful failure or blocker state."
log "Evidence: $EVIDENCE_ROOT"
log "Last failure evidence: ${previous_evidence:-unavailable}"
log "No UAT score was manually changed."
log "============================================================"

if [[ -f "$ROOT/uat/final-report.json" ]]; then
  printf '\nCurrent authoritative report:\n'
  cat "$ROOT/uat/final-report.json"
fi

exit 1
