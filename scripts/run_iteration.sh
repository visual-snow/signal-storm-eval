#!/usr/bin/env bash
# Run one build-loop iteration: the whole roster, then the differentiation gate.
# Mirrors docs/build-loop.md: epochs=1 while iterating, >= 3 for the
# reliability (pass^k) pass.
# Usage: scripts/run_iteration.sh <name> [epochs]   (epochs default 1)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

cleanup() {
  trap - EXIT INT TERM
  scripts/stop_signal_storm_sandboxes.sh || true
}

trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

NAME=${1:?usage: run_iteration.sh <name> [epochs]}
EPOCHS=${2:-1}
LOG_DIR="logs/${NAME}"
MESSAGE_LIMIT="${MESSAGE_LIMIT:-40}"
MAX_SAMPLES="${MAX_SAMPLES:-1}"
KINDS="${KINDS:-}"

# Concurrent sandboxes. Default 1: the topology pins fixed network subnets
# (the AMF NGAP IP 10.10.2.2 is hardcoded in the NF configs), and Docker rejects
# two networks on the same subnet ("Pool overlaps"), so parallel worlds collide.
# Raise only after the topology is reworked to auto-assigned subnets.
MAX_SANDBOXES=${MAX_SANDBOXES:-1}
# Concurrent samples. Keep this aligned with MAX_SANDBOXES for fixed-subnet
# worlds; Inspect otherwise tries to initialize multiple compose projects.

# Roster: six OpenRouter models (slugs verified against the live catalog).
ROSTER=(
  "openrouter/openai/gpt-5.5"
  "openrouter/qwen/qwen3.7-plus"
  "openrouter/deepseek/deepseek-v4-flash"
  "openrouter/minimax/minimax-m3"
  "openrouter/google/gemini-3-flash-preview"
  "openrouter/anthropic/claude-haiku-4.5"
)

for model in "${ROSTER[@]}"; do
  echo "=== ${model} ==="
  cmd=(
    uv run inspect eval signal_storm_bench/signal_storm
    --model "${model}" \
    --epochs "${EPOCHS}" \
    --message-limit "${MESSAGE_LIMIT}" \
    --max-samples "${MAX_SAMPLES}" \
    --log-dir "${LOG_DIR}" \
    --max-sandboxes "${MAX_SANDBOXES}" \
    --fail-on-error 0.25
  )
  if [ -n "${KINDS}" ]; then
    cmd+=(-T "kinds=${KINDS}")
  fi
  "${cmd[@]}"
done

uv run python scripts/check_differentiation.py "${LOG_DIR}"
