#!/bin/sh
# PacketRusher storm driver. Two roles, selected by argv[1]:
#
#   idle   (default container command) renders /tmp/config.yml from the identity +
#          storm-params env, then sleeps forever so the eval can exec storms on demand.
#
#   run    (invoked by run_ue_storm_simulator via `compose exec packetrusher
#          /storm.sh run`) runs ONE storm: multi-ue registers UE_COUNT UEs, one every
#          1000/STORM_RATE ms (=> STORM_RATE reg/s), bounded by timeout -s INT
#          DURATION_S for a clean deregistering stop. STORM_RATE=0 is the baseline
#          world: no storm, just sleep DURATION_S so the AMF counter stays ~0.
#
# Knobs come from the env (compose.yaml sets defaults; override per exec with -e).
# Logic ported from overlays/common/injector.yaml (the storm-injector Job args).
set -e

render() {
  envsubst < /config-tmpl/config.yml.tmpl > /tmp/config.yml
}

case "${1:-idle}" in
  idle)
    render
    echo "packetrusher idle: config rendered to /tmp/config.yml; awaiting storm exec"
    exec sleep infinity
    ;;
  run)
    render
    if [ "${STORM_RATE:-0}" -eq 0 ]; then
      echo "baseline world: no storm (STORM_RATE=0), sleeping ${DURATION_S}s"
      sleep "${DURATION_S}"
      exit 0
    fi
    # -tr is a plain integer in ms (PacketRusher multi-ue --help: "The time in ms,
    # between UE registration"), so NO 'ms' suffix. 1000/STORM_RATE ms => STORM_RATE
    # reg/s. Tunnel stays off by default (control-plane storm, no gtp5g).
    TR_MS=$((1000 / STORM_RATE))
    echo "storm: UE_COUNT=${UE_COUNT} STORM_RATE=${STORM_RATE}reg/s (-tr ${TR_MS}ms) DURATION_S=${DURATION_S}"
    timeout -s INT "${DURATION_S}" \
      packetrusher --config /tmp/config.yml multi-ue -n "${UE_COUNT}" -tr "${TR_MS}" || true
    echo "storm finished"
    ;;
  *)
    echo "usage: storm.sh [idle|run]" >&2
    exit 2
    ;;
esac
