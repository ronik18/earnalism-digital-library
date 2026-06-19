#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
BACKEND_DIR="${ROOT_DIR}/backend"

COMMIT_MESSAGE="${COMMIT_MESSAGE:-}"
BRANCH="${BRANCH:-}"
YES=0
DRY_RUN=0
SKIP_CHECKS=0
SKIP_COMMIT=0
SKIP_PUSH=0
SKIP_FRONTEND=0
SKIP_BACKEND=0
SKIP_SMOKE=0
DETACH=0

RAILWAY_SERVICE="${RAILWAY_SERVICE:-${RAILWAY_SERVICE_ID:-earnalism}}"
RAILWAY_ENVIRONMENT="${RAILWAY_ENVIRONMENT:-production}"
RAILWAY_PROJECT_ID="${RAILWAY_PROJECT_ID:-}"
FRONTEND_URL="${FRONTEND_URL:-https://theearnalism.com}"
API_URL="${API_URL:-https://api.theearnalism.com}"
POST_DEPLOY_WAIT_SECONDS="${POST_DEPLOY_WAIT_SECONDS:-45}"
RAILWAY_DEPLOY_RETRIES="${RAILWAY_DEPLOY_RETRIES:-2}"
RAILWAY_RETRY_DELAY_SECONDS="${RAILWAY_RETRY_DELAY_SECONDS:-20}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/commit_push_deploy.sh -m "Commit message" [options]

What it does:
  1. Runs deploy checks.
  2. Stages and commits current repo changes.
  3. Pushes the current branch to origin.
  4. Deploys backend to Railway.
  5. Deploys frontend to Vercel.
  6. Smoke-checks production frontend/backend.

Options:
  -m, --message TEXT      Commit/deploy message. Defaults to a timestamped message.
  -b, --branch NAME       Branch to push. Defaults to the current branch.
  -y, --yes               Do not prompt before staging/committing.
      --dry-run           Print commands without executing them.
      --skip-checks       Skip git diff/build/py_compile checks.
      --skip-commit       Do not stage or commit changes.
      --skip-push         Do not push to origin.
      --skip-frontend     Do not deploy frontend to Vercel.
      --skip-backend      Do not deploy backend to Railway.
      --frontend-only     Deploy only frontend; also skips backend.
      --backend-only      Deploy only backend; also skips frontend.
      --skip-smoke        Skip post-deploy curl smoke checks.
      --detach            Start Railway deploy without attaching to logs.
  -h, --help              Show this help.

Environment overrides:
  RAILWAY_SERVICE=earnalism
  RAILWAY_ENVIRONMENT=production
  RAILWAY_PROJECT_ID=<optional>
  VERCEL_TOKEN=<optional>
  VERCEL_SCOPE=<optional>
  FRONTEND_URL=https://theearnalism.com
  API_URL=https://api.theearnalism.com
  POST_DEPLOY_WAIT_SECONDS=45
  RUN_BACKEND_TESTS=1
  RUN_FRONTEND_TESTS=1
  RAILWAY_DEPLOY_RETRIES=2
  RAILWAY_RETRY_DELAY_SECONDS=20
USAGE
}

log() {
  printf '\n==> %s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

print_command() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
}

run() {
  print_command "$@"
  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi
  "$@"
}

confirm() {
  local prompt="$1"
  if [[ "${YES}" == "1" || "${DRY_RUN}" == "1" ]]; then
    return 0
  fi
  printf '%s [y/N] ' "${prompt}"
  read -r answer
  case "${answer}" in
    y|Y|yes|YES) return 0 ;;
    *) die "Aborted by user." ;;
  esac
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

is_railway_transient_timeout() {
  local file="$1"
  grep -Eiq 'reqwest error|operation timed out|timed out|error sending request|backboard\.railway\.com/graphql' "${file}"
}

railway_upload_was_handed_off() {
  local file="$1"
  grep -Eq 'Build Logs:|Uploaded' "${file}"
}

run_railway_backend_deploy() {
  local attempt=1
  local status=0
  local output_file
  output_file="$(mktemp -t earnalism-railway-deploy.XXXXXX)"
  trap 'rm -f "${output_file}"' RETURN

  while (( attempt <= RAILWAY_DEPLOY_RETRIES )); do
    if (( RAILWAY_DEPLOY_RETRIES > 1 )); then
      log "Railway deploy attempt ${attempt}/${RAILWAY_DEPLOY_RETRIES}"
    fi
    : > "${output_file}"
    print_command railway "${railway_args[@]}"
    if [[ "${DRY_RUN}" == "1" ]]; then
      return 0
    fi

    set +e
    railway "${railway_args[@]}" 2>&1 | tee "${output_file}"
    status=${PIPESTATUS[0]}
    set -e

    if [[ "${status}" == "0" ]]; then
      return 0
    fi

    if is_railway_transient_timeout "${output_file}" && railway_upload_was_handed_off "${output_file}"; then
      echo "WARNING: Railway CLI timed out after upload/build handoff. The deployment likely started; continuing to frontend deploy and smoke checks."
      echo "         Check Railway dashboard/build logs if smoke checks fail."
      return 0
    fi

    if is_railway_transient_timeout "${output_file}" && (( attempt < RAILWAY_DEPLOY_RETRIES )); then
      echo "WARNING: transient Railway CLI/network timeout. Retrying in ${RAILWAY_RETRY_DELAY_SECONDS}s..."
      sleep "${RAILWAY_RETRY_DELAY_SECONDS}"
      attempt=$((attempt + 1))
      continue
    fi

    return "${status}"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    -b|--branch)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      BRANCH="$2"
      shift 2
      ;;
    -y|--yes)
      YES=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-checks)
      SKIP_CHECKS=1
      shift
      ;;
    --skip-commit)
      SKIP_COMMIT=1
      shift
      ;;
    --skip-push)
      SKIP_PUSH=1
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    --skip-backend)
      SKIP_BACKEND=1
      shift
      ;;
    --frontend-only)
      SKIP_BACKEND=1
      shift
      ;;
    --backend-only)
      SKIP_FRONTEND=1
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      shift
      ;;
    --detach)
      DETACH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

cd "${ROOT_DIR}"
need_command git
need_command npm
need_command python3
need_command curl

[[ -d "${FRONTEND_DIR}" ]] || die "Frontend directory not found: ${FRONTEND_DIR}"
[[ -d "${BACKEND_DIR}" ]] || die "Backend directory not found: ${BACKEND_DIR}"
git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not inside a git repository."

if [[ -z "${BRANCH}" ]]; then
  BRANCH="$(git -C "${ROOT_DIR}" branch --show-current)"
fi
[[ -n "${BRANCH}" ]] || die "Could not determine current branch. Pass --branch explicitly."

if [[ -z "${COMMIT_MESSAGE}" ]]; then
  COMMIT_MESSAGE="Production deploy $(date '+%Y-%m-%d %H:%M:%S %Z')"
fi

if [[ "${SKIP_CHECKS}" != "1" ]]; then
  log "Running pre-deploy checks"
  run git -C "${ROOT_DIR}" diff --check
  run python3 -m py_compile "${BACKEND_DIR}/server.py"
  if [[ "${RUN_BACKEND_TESTS:-0}" == "1" ]]; then
    run env PYTHONPATH="${BACKEND_DIR}" python3 -m pytest "${BACKEND_DIR}/tests" -q
  fi
  if [[ "${RUN_FRONTEND_TESTS:-0}" == "1" ]]; then
    run env CI=true npm --prefix "${FRONTEND_DIR}" test -- --watchAll=false --passWithNoTests
  fi
  run npm --prefix "${FRONTEND_DIR}" run build
else
  log "Skipping pre-deploy checks"
fi

if [[ "${SKIP_COMMIT}" != "1" ]]; then
  log "Preparing git commit"
  if [[ -z "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
    echo "No local changes to commit."
  else
    git -C "${ROOT_DIR}" status --short
    confirm "Stage all shown changes and commit?"
    run git -C "${ROOT_DIR}" add -A
    run git -C "${ROOT_DIR}" diff --cached --check
    if [[ "${DRY_RUN}" != "1" ]]; then
      if git -C "${ROOT_DIR}" diff --cached --quiet; then
        echo "No staged changes to commit."
      else
        run git -C "${ROOT_DIR}" commit -m "${COMMIT_MESSAGE}"
      fi
    else
      run git -C "${ROOT_DIR}" commit -m "${COMMIT_MESSAGE}"
    fi
  fi
else
  log "Skipping commit"
fi

if [[ "${SKIP_PUSH}" != "1" ]]; then
  log "Pushing branch ${BRANCH}"
  run git -C "${ROOT_DIR}" push origin "${BRANCH}"
else
  log "Skipping push"
fi

COMMIT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || true)"
DEPLOY_MESSAGE="${COMMIT_MESSAGE}"
if [[ -n "${COMMIT_SHA}" ]]; then
  DEPLOY_MESSAGE="${DEPLOY_MESSAGE} (${COMMIT_SHA})"
fi

if [[ "${SKIP_BACKEND}" != "1" ]]; then
  log "Deploying backend to Railway"
  need_command railway
  railway_args=(up "${BACKEND_DIR}" --path-as-root --service "${RAILWAY_SERVICE}" --environment "${RAILWAY_ENVIRONMENT}" --message "${DEPLOY_MESSAGE}")
  if [[ -n "${RAILWAY_PROJECT_ID}" ]]; then
    railway_args+=(--project "${RAILWAY_PROJECT_ID}")
  fi
  if [[ "${DETACH}" == "1" ]]; then
    railway_args+=(--detach)
  fi
  run_railway_backend_deploy
else
  log "Skipping backend deploy"
fi

if [[ "${SKIP_FRONTEND}" != "1" ]]; then
  log "Deploying frontend to Vercel"
  vercel_cmd=()
  if command -v vercel >/dev/null 2>&1; then
    vercel_cmd=(vercel)
  else
    vercel_cmd=(npx --yes vercel@latest)
  fi
  vercel_args=(--prod --yes)
  if [[ -n "${VERCEL_TOKEN:-}" ]]; then
    vercel_args+=(--token "${VERCEL_TOKEN}")
  fi
  if [[ -n "${VERCEL_SCOPE:-}" ]]; then
    vercel_args+=(--scope "${VERCEL_SCOPE}")
  fi
  run "${vercel_cmd[@]}" "${vercel_args[@]}"
else
  log "Skipping frontend deploy"
fi

if [[ "${SKIP_SMOKE}" != "1" ]]; then
  log "Running post-deploy smoke checks"
  if [[ "${DRY_RUN}" != "1" && "${POST_DEPLOY_WAIT_SECONDS}" != "0" ]]; then
    sleep "${POST_DEPLOY_WAIT_SECONDS}"
  fi
  run curl -fsSL -o /dev/null "${FRONTEND_URL}"
  run curl -fsSL -o /dev/null "${API_URL%/}/healthz"
else
  log "Skipping smoke checks"
fi

log "Done"
echo "Branch: ${BRANCH}"
echo "Commit: ${COMMIT_SHA:-unknown}"
echo "Frontend: ${FRONTEND_URL}"
echo "Backend: ${API_URL}"
