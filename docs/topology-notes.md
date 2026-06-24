# Topology notes: the local docker-compose substrate (P2)

The signal_storm_bench eval runs against a real Open5GS 5G core booted locally with
docker-compose. A PacketRusher injector drives a real NGAP-over-SCTP registration storm
that climbs the live AMF Prometheus counters. No Kubernetes. This file documents the
tool interface the Inspect eval (P3) builds on, plus every deviation from the upstream
k8s recipe and its provenance.

Substrate location: `src/signal_storm_bench/topology/` (compose.yaml + config/).
Validation status: PASS (see "Validation evidence" at the end).

## Sandbox spec

`task.py` lives at `src/signal_storm_bench/task.py`; `topology/` is its sibling, so:

```python
from pathlib import Path
sandbox = ("docker", str(Path(__file__).parent / "topology" / "compose.yaml"))
```

Bring-up resolves dependencies in order: mongodb (healthy) -> seed (one-shot, exits 0)
-> open5gs-aio (healthy: NGAP 38412 + metrics 9090 both listening) -> prometheus +
packetrusher (idle). The eval's `wait_for_boot` should poll until the AMF metrics
endpoint answers (Prometheus target `up`), which is the same gate the AMF healthcheck
uses.

## Compose services

| service        | image                                | role |
|----------------|--------------------------------------|------|
| `mongodb`      | `mongo`                              | subscriber DB (open5gs.subscribers) |
| `seed`         | `python:3.11-slim`                   | one-shot; seeds POOL_SIZE subscribers, then exits |
| `open5gs-aio`  | `ghcr.io/niloysh/open5gs:v2.7.0`    | the 5G core (NRF, SCP, AMF, SMF, AUSF, UDM, UDR, PCF, NSSF, BSF, UPF) |
| `prometheus`   | `prom/prometheus:v2.54.1`           | scrapes the AMF metrics endpoint |
| `packetrusher` | `packetrusher:storm` (built locally) | the storm injector; idle by default |

The core image is amd64-only; it runs under OrbStack x86 emulation (verified). The
injector is built for the host arch (arm64); it interoperates with the amd64 AMF over
the bridge networks regardless of arch.

## Tool interface for the eval (P3)

### read_amf_config

```
docker compose exec open5gs-aio cat /open5gs/config/amf.yaml
```

- compose service name: **`open5gs-aio`**
- config path: **`/open5gs/config/amf.yaml`** (other NFs are siblings in the same dir:
  smf.yaml, nrf.yaml, scp.yaml, ausf.yaml, udm.yaml, udr.yaml, pcf.yaml, nssf.yaml,
  bsf.yaml, upf.yaml)

### read_nf_log_file

The AMF has no stdout sink (`docker logs open5gs-aio` is empty for AMF lines), so read
the on-disk log:

```
docker compose exec open5gs-aio cat /open5gs/install/var/log/open5gs/amf.log
```

- log dir: **`/open5gs/install/var/log/open5gs/`**; per-NF files `amf.log`, `smf.log`,
  `nrf.log`, etc. (`logger.file` in each NF yaml).

### query_prometheus_metrics

Prometheus is reachable from inside the sandbox network by service DNS:

- base URL (inside sandbox): **`http://prometheus:9090`**
- base URL (from the host): `http://localhost:9091` (host 9091 -> container 9090; host
  9090 is the AMF metrics passthrough)

HTTP API: `GET http://prometheus:9090/api/v1/query?query=<PromQL>`.

Metric names (AMF NGAP registration surface):

- `fivegs_amffunction_rm_reginitreq`  cumulative initial-registration **requests** (the
  storm signal)
- `fivegs_amffunction_rm_reginitsucc` cumulative successful registrations (lags
  reginitreq under load)

Example PromQL:

- instant value (cumulative count): `fivegs_amffunction_rm_reginitreq`
- count over the storm window: `increase(fivegs_amffunction_rm_reginitreq[2m])`
- peak rate during the storm: `rate(fivegs_amffunction_rm_reginitreq[30s])`

Counters are cumulative across storms in a session; per-sample logic should snapshot the
counter before the storm and diff, not assume it starts at 0 (a fresh `up -v` does start
at 0).

### run_ue_storm_simulator (inject_storm)

The injector is idle by default (renders its config, then `sleep infinity`). The eval
fires one storm on demand with:

```
docker compose exec \
  -e STORM_RATE=<rate> -e UE_COUNT=<n> -e DURATION_S=<secs> \
  packetrusher /storm.sh run
```

`/storm.sh run` (config/storm.sh) renders `/tmp/config.yml` from the identity env with
`envsubst`, then runs the bounded storm:

```
timeout -s INT $DURATION_S \
  packetrusher --config /tmp/config.yml multi-ue -n $UE_COUNT -tr $((1000/STORM_RATE))
```

`-tr` is a plain integer in ms (PacketRusher `multi-ue --help`: "The time in ms, between
UE registration"), so `1000/STORM_RATE` ms => STORM_RATE reg/s. Tunnel stays off
(control-plane storm; no gtp5g). `timeout -s INT` gives a clean deregistering stop.

### World selection per sample (storm vs baseline)

Selected by the `STORM_RATE`/`UE_COUNT` env on the exec, NOT by a separate compose file:

- **storm world**: `STORM_RATE=100 UE_COUNT=200 DURATION_S=120` (compose defaults on the
  packetrusher service; matches overlays/storm). The injector floods the AMF.
- **baseline world**: `STORM_RATE=0 UE_COUNT=0` (override at exec). `/storm.sh run`
  detects `STORM_RATE=0`, sleeps `DURATION_S`, and registers nothing, so the counter
  stays flat (matches overlays/baseline).

Debug knobs that were verified to work: `UE_COUNT=50 STORM_RATE=50 DURATION_S=30`.

### wait_storm_manifest

After firing the storm, poll `fivegs_amffunction_rm_reginitreq` until it rises above the
pre-storm snapshot (or until `increase(...[window])` is clearly nonzero). At 100 reg/s
the full UE_COUNT registers in ~2 s, so the counter plateaus quickly; gate on
"delta >= some threshold of UE_COUNT", not on a sustained rate.

## Identity (single source of truth)

From overlays/common/identity.yaml; set on both `seed` and `packetrusher` via the
`&identity` YAML anchor in compose.yaml, so seeded subscribers and registered UEs cannot
drift.

| key | value |
|-----|-------|
| MCC / MNC | `001` / `01` |
| MSIN_BASE | `0000000001` |
| POOL_SIZE | `500` (subscribers seeded; over-provisioned above UE_COUNT) |
| KEY | `465B5CE8B199B49FAA5F0A2EE238A6BC` |
| OPC | `E8ED289DEBA952E4283B54E88E6183CA` |
| AMF_FIELD | `8000` (3GPP auth management field) |
| SST / SST_STR / SD | `1` / `01` / `000001` |
| AMF_NGAP_IP / PORT | `10.10.2.2` / `38412` (compose world; see deviation below) |

IMSI = MCC + MNC + 10-digit MSIN, e.g. first subscriber `001010000000001`.

## Networks and addresses

Three bridge networks carry the static IPs the NF configs expect, plus `default`:

- `n2network` 10.10.2.0/24 -- AMF NGAP `10.10.2.2:38412` (SCTP); injector gNB
  `10.10.2.50`
- `n3network` 10.10.3.0/24 -- UPF GTP-U `10.10.3.2` (unused by the control-plane storm)
- `n4network` 10.10.4.0/24 -- defined for fidelity with the AIO compose; PFCP actually
  runs on container loopback
- SBI/PFCP/GTP-C between NFs all use 127.0.0.x loopback inside the AIO container
  (upstream config; unchanged).

## Deviations from the k8s recipe (for NOTICE / FIDELITY)

| deviation | rationale |
|-----------|-----------|
| substrate k8s -> docker-compose | mission P2: a local, single-machine world reproducible on any SCTP-capable Docker backend; no cluster |
| 11 NFs collapsed into one AIO container | upstream `base/open5gs-aio` is the known-good single-container core; minimal change beats re-splitting into per-NF services |
| AMF metrics bind `127.0.0.5` -> `0.0.0.0` (config/amf.yaml) | the ONLY NF-config change; a separate prometheus container must reach 9090 over the bridge (container loopback is unreachable cross-container). Upstream k8s already assumed 0.0.0.0 (overlays/common/prometheus.yaml) |
| NGAP target on n2 (`10.10.2.2`) not n3 (`10.10.3.200`) | the AIO `amf.yaml` binds NGAP on n2network `10.10.2.2`; the k8s identity's `AMF_NGAP_IP=10.10.3.200` came from a k8s NAD that does not exist in compose. Injector gNB controlif/dataif + amfif moved to n2 to match (config/config.yml.tmpl) |
| subscriber seed: k8s Job -> compose one-shot `seed` service | same embedded python (config/seed.py), made idempotent (skips if already seeded); `service_completed_successfully` gates the core |
| injector: k8s Job -> idle long-lived service + on-demand `exec` | the eval needs to replay the storm per sample; an idle container with `/storm.sh run` is simpler than re-creating a Job each time |
| AMF healthcheck via `ss` not `curl` | the open5gs image ships no curl; `ss` (iproute2) confirms NGAP 38412 + metrics 9090 are listening |
| `-tr` passed as bare int ms (no `ms` suffix) | the pinned PacketRusher build takes `-tr` as an integer ms (verified via `multi-ue --help`); a `ms` suffix is rejected |

## Provenance of vendored assets

All copied/adapted from
`env_recipes_telco/recipes/open5gs_signaling_storm_sandbox/`:

- `config/{amf,ausf,bsf,nrf,nssf,pcf,scp,smf,udm,udr,upf}.yaml`, `init.sh`, `run.sh`,
  `mongo-init.js` <- `base/open5gs-aio/config/` (byte-faithful except the amf.yaml
  metrics bind)
- `compose.yaml` networks/services <- `base/open5gs-aio/docker-compose.yaml` (+ the
  k8s overlays for seed/prometheus/injector)
- `config/prometheus.yml` <- `overlays/common/prometheus.yaml` (ConfigMap -> file;
  target = service `open5gs-aio:9090`)
- `config/config.yml.tmpl` <- `overlays/common/injector.yaml` injector-config (gNB/AMF
  IPs moved to n2)
- `config/seed.py` <- `overlays/common/subscriber-seed.yaml` embedded python
- identity values <- `overlays/common/identity.yaml`
- `packetrusher.Dockerfile` <- `injector/Dockerfile` (PacketRusher pinned ref
  `5bf8b4ed9350a4dfc732eb6a6074aa97d1426308`, `CGO_ENABLED=0` static build)
- core image `ghcr.io/niloysh/open5gs:v2.7.0` (pulled, not built)

## Confirmations (measured on this machine; OrbStack)

- **SCTP works locally**: the amd64 open5gs container shows SCTP + SCTPv6 in
  `/proc/net/protocols`; the AMF NGAP endpoint listens on `10.10.2.2:38412`
  (`/proc/net/sctp/eps`); PacketRusher completes the full NGAP/NAS registration over
  SCTP and the AMF accepts it.
- **packetrusher build time**: ~60 s (clone + static Go build, cold).
- **image sizes**: open5gs 410 MB, prometheus 269 MB, python:3.11-slim 150 MB,
  packetrusher:storm 117 MB, mongo 934 MB.
- **bring-up time**: ~18 s from `up -d` to AMF healthy + 500 subscribers seeded
  (images pre-pulled, injector pre-built). **teardown** ~22 s.

## Validation evidence (the success gate: PASS)

Storm (UE_COUNT=150 at 100 reg/s), AMF metrics sampled live every 0.5 s, showing the
counter climb and reginitsucc lagging reginitreq under load:

```
baseline before: reginitreq=250 reginitsucc=250
t+2.0s  reginitreq=261  reginitsucc=250   <- succ lags req by 11
t+2.5s  reginitreq=318  reginitsucc=303
t+3.0s  reginitreq=373  reginitsucc=353
t+3.5s  reginitreq=400  reginitsucc=400   <- 150 UEs registered (250+150)
```

Default storm (UE_COUNT=200 at 100 reg/s, 120 s) ran full duration, delta exactly 200
requests / 200 successes, clean deregistration.

Baseline world (STORM_RATE=0): counter held at 400 -> 400 (no storm).

Fresh `up -v`: counter starts at 0, 500 subscribers seeded. Teardown clean.
