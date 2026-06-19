#!/usr/bin/env bash
# Remove signal-storm Inspect docker sandboxes left behind by interrupted runs.
set -euo pipefail

if ! CONTAINER_IDS="$(
  docker ps -a --format '{{.ID}} {{.Names}}' 2>/dev/null |
    awk '$2 ~ /^inspect-signal_storm-/ {print $1}'
)"; then
  echo "docker unavailable; no signal-storm sandboxes stopped"
  exit 0
fi

NETWORK_IDS="$(
  docker network ls --format '{{.ID}} {{.Name}}' |
    awk '$2 ~ /^inspect-signal_storm-/ {print $1}'
)"
VOLUME_NAMES="$(
  docker volume ls --format '{{.Name}}' |
    awk '$1 ~ /^inspect-signal_storm-/ {print $1}'
)"

REMOVED=0
if [ -n "${CONTAINER_IDS}" ]; then
  COUNT="$(printf '%s\n' "${CONTAINER_IDS}" | wc -l | tr -d ' ')"
  # Container ids are newline-delimited hex strings from docker, so word
  # splitting is intentional here.
  docker rm -f ${CONTAINER_IDS}
  REMOVED=$((REMOVED + COUNT))
  echo "removed ${COUNT} signal-storm sandbox container(s)"
fi

if [ -n "${NETWORK_IDS}" ]; then
  COUNT="$(printf '%s\n' "${NETWORK_IDS}" | wc -l | tr -d ' ')"
  docker network rm ${NETWORK_IDS}
  REMOVED=$((REMOVED + COUNT))
  echo "removed ${COUNT} signal-storm sandbox network(s)"
fi

if [ -n "${VOLUME_NAMES}" ]; then
  COUNT="$(printf '%s\n' "${VOLUME_NAMES}" | wc -l | tr -d ' ')"
  docker volume rm ${VOLUME_NAMES}
  REMOVED=$((REMOVED + COUNT))
  echo "removed ${COUNT} signal-storm sandbox volume(s)"
fi

if [ "${REMOVED}" -eq 0 ]; then
  echo "no signal-storm sandboxes running"
fi
