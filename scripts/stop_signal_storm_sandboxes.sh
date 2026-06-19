#!/usr/bin/env bash
# Remove signal-storm Inspect docker sandboxes left behind by interrupted runs.
set -euo pipefail

if ! IDS="$(
  docker ps -aq --format '{{.ID}} {{.Names}}' 2>/dev/null |
    awk '$2 ~ /^inspect-signal_storm-/ {print $1}'
)"; then
  echo "docker unavailable; no signal-storm sandboxes stopped"
  exit 0
fi

if [ -z "${IDS}" ]; then
  echo "no signal-storm sandboxes running"
  exit 0
fi

COUNT="$(printf '%s\n' "${IDS}" | wc -l | tr -d ' ')"
# Container ids are newline-delimited hex strings from docker, so word splitting
# is intentional here.
docker rm -f ${IDS}
echo "removed ${COUNT} signal-storm sandbox container(s)"
