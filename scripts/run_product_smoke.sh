#!/usr/bin/env bash
# Run one guarded product-scored smoke eval and clean up docker sandboxes on exit.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

MODEL="${1:-${MODEL:-${INSPECT_EVAL_MODEL:-}}}"
if [ -z "${MODEL}" ]; then
  echo "usage: scripts/run_product_smoke.sh <model>" >&2
  echo "or set MODEL / INSPECT_EVAL_MODEL" >&2
  exit 2
fi

LOG_DIR="${LOG_DIR:-logs/product-smoke}"
LIMIT="${LIMIT:-1}"
MESSAGE_LIMIT="${MESSAGE_LIMIT:-50}"
MAX_SANDBOXES="${MAX_SANDBOXES:-1}"
FAIL_ON_ERROR="${FAIL_ON_ERROR:-0.25}"
KINDS="${KINDS:-}"

cleanup() {
  trap - EXIT INT TERM
  scripts/stop_signal_storm_sandboxes.sh || true
}

trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

cmd=(
  uv run inspect eval signal_storm_bench/signal_storm
  --model "${MODEL}"
  --limit "${LIMIT}"
  --message-limit "${MESSAGE_LIMIT}"
  --max-sandboxes "${MAX_SANDBOXES}"
  --log-dir "${LOG_DIR}"
  --fail-on-error "${FAIL_ON_ERROR}"
)

if [ -n "${KINDS}" ]; then
  cmd+=(-T "kinds=${KINDS}")
fi

"${cmd[@]}"
