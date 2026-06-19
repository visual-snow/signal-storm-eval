# signal_storm_bench: build status

The single source of truth for what is built and what is missing. Re-read this
before any build step; update it after every step. The canonical requirements
live in `EVALUATION_CHECKLIST.md` (the inspect_evals bible, copied verbatim);
this file is the live status overlay on it, and the rest of `docs/` is the
build-loop memory.

## Current state (2026-06-19)

- Environment: BUILT locally in `src/signal_storm_bench/topology/`. Inspect
  attaches the docker-compose Open5GS AIO, MongoDB/subscriber seed, Prometheus,
  and PacketRusher storm injector as a docker sandbox. The AMF is CPU-capped so
  storm runs form a request/success deficit.
- Inspect eval: BUILT. `signal_storm_bench/signal_storm` has t1..t10 product
  prompts, NOC tools, scorer-side live probes, and deterministic numeric
  product scorers with component metadata.
- Scoring cleanup: BUILT for local scorer validation. Reference, bad, and three
  partial artifacts per task are tested in `tests/test_scorer_logic.py`, and
  `docs/product-score-calibration.md` records offline per-task score spread.
- Results: Product-scored live smoke has passed; full model-roster calibration
  is still pending. Historical
  `logs/p5` and `logs/p5b` predate product prompts; their successful saved
  completions have been rescored with the current product scorer in
  `docs/saved-log-product-calibration.md`. The fresh smoke log
  `logs/product-smoke/2026-06-19T15-19-38-00-00_signal-storm_3hsWR5QsWi6CpWhcHyhhSb.eval`
  has status `success`, score `0.648`, and component metadata. Fresh
  product-prompt roster logs are still needed for current multi-model
  capability evidence.

## House-style template

`transport_oam_bench` (repo `zhejiang-transport-eval`, visual-snow org) is the
reference for package layout, scorer style, the build loop, and the report.
Mirror it. `son_energy_bench` is NOT a reference; do not use it.

## Settled decisions

The overriding goal is reproducibility: the benchmark must run on a single
machine with no cluster, so anyone can reproduce it. Decisions follow from that.

1. Substrate: a local docker-compose topology, shipped inside the eval
   (`topology/compose.yaml`), attached as `sandbox=("docker", compose_file)`.
   The k8s recipe is NOT attached. We assemble the environment from the upstream
   docker assets the recipe already vendors (`base/open5gs-aio/docker-compose.yaml`,
   the open5gs / metrics Dockerfiles) plus the recipe's Prometheus, subscriber
   seed, and PacketRusher injector adapted to compose.
2. Feasibility confirmed (2026-06-18): SCTP is available to unprivileged
   containers on this machine's Docker backend (OrbStack, kernel 6.17.8, SCTP
   built-in). A real NGAP-over-SCTP storm runs locally. Anyone whose Docker
   backend has an SCTP-capable Linux kernel can reproduce it.
3. Fidelity: this is a substrate change (k8s to docker-compose), not a component
   swap. Open5GS, PacketRusher, Prometheus, and MongoDB are unchanged. Recorded
   as a deliberate deviation in FIDELITY.md.

Resolved (2026-06-18):

- Agent message budget: 50 (owner directive; run with `--message-limit 50`,
  `DEFAULT_MESSAGE_LIMIT = 50`). This overrides the README's earlier ~40.
- P5 roster: six over OpenRouter (gpt-5.5, claude-haiku-4.5, gemini-3-flash,
  deepseek-v4-flash, qwen3.7-plus, minimax-m3). gpt-5.5 added by owner directive
  2026-06-18; all slugs verified against the live catalog.
- P5 execution: full loop within a budget (default cap $5/model unless changed).

Gate before any paid run: model credentials must be available in `.env` or the
environment. Implementation, scorer validation, and offline calibration need no
model key and do not boot docker.

## Master checklist status

Keyed to `EVALUATION_CHECKLIST.md`. Status: DONE / WIP / TODO / BLOCKED.

| Checklist item | Status | Note |
|---|---|---|
| Eval runs with `inspect eval ... --limit 1` | DONE | fresh product-scored smoke passed via `scripts/run_product_smoke.sh`; cleanup removed sandboxes |
| Trajectory analysis on a small run | WIP | product-smoke transcript/export reviewed for t1; full roster transcript review pending |
| Manually examined checks (best practices) | WIP | cleanup docs, scorer anchors, saved-log calibration, and product-smoke transcript reviewed; full roster review pending |
| Name validity | DONE | `signal_storm_bench` matches the use case |
| Dataset validity (each sample passable and failable) | DONE | product prompts plus reference/bad/partial scorer anchors for t1..t10 |
| Scoring validity (measures completion, not a proxy) | WIP | numeric product scorers, scorer-anchor calibration, saved-log rescoring, and product-smoke scoring pass; full roster review pending |
| Evaluation report, two or more models | TODO | needs fresh product-scored roster |
| `report_config.yaml` committed | TODO | P5 |
| Code quality, lint, types | DONE | `ruff check`, `ruff format --check`, and `mypy src tests` pass after saved-log calibration |
| Unit tests (solvers, scorers, tools) | DONE | latest default suite passed with `uv run --no-sync pytest -q` (`223 passed, 1 skipped`) |
| End-to-end tests per variant | TODO | P6 |
| Pytest marks (docker / k8s) | TODO | P6 |
| Licensing and attribution (NOTICE) | TODO | vendored env provenance, P0 and P6 |
| Register submission (eval.yaml plus README) | TODO | P7 |

## Sequential build plan

Each phase is a dynamic workflow: a generator step writes the artefact, then the
`eval-reviewer` critique step scores it against `BEST_PRACTICES.md`. Phases run
in order; later phases depend on earlier ones. Implementation agents load
`karpathy-guidelines` for clean, surgical code.

- P0 Scaffold: src package, `pyproject.toml`, `eval.yaml` stub, `NOTICE`, and
  the loop scripts (`check_differentiation`, `pass_hat_k`,
  `export_gate_artifacts`) plus the `eval-reviewer` agent ported from the
  template. Memory docs (this set) seeded.
- P1 Dataset plus prompts: one Sample per task t1..t10, with world variants for
  the negative cases. Hidden ground truth in `Sample.metadata`; prompts
  leak-closed.
- P2 Environment topology: assemble a local docker-compose world in
  `src/signal_storm_bench/topology/` (Open5GS AIO, MongoDB, subscriber seed,
  Prometheus, PacketRusher injector). Prove it boots locally and a real storm
  drives the AMF `reginitreq` counter, then attach it as
  `sandbox=("docker", compose_file)`. This de-risks the whole build and is done
  early, right after P0.
- P3 Tools plus scorers: the four tools (`query_prometheus_metrics`,
  `read_amf_config`, `read_nf_log_file`, `run_ue_storm_simulator`) over a
  `sandbox_ops` layer; pure `decide()` scorers per the judge-report contracts,
  re-grounded to the live emergent peak. Apply the three judge fixes (t9 and t10
  synonyms, t5 candidate set, t8 units). Finalise t2..t4.
- P4 Local validation: a single `--limit 1` run against the live local world;
  fix until a valid submission scores. Must also tune the storm so the AMF is
  genuinely overloaded (live_peak_rate > capacity_rate robustly), since at the
  recipe default of 100 reg/s the AMF keeps up and t7/t8/t9 would degenerate.
  Options: raise STORM_RATE/UE_COUNT, or cap the AMF container CPU so capacity is
  bounded below the offered load. Validated here, not on a cluster.
- P5 Differentiation loop: run the roster at epochs >= 3, measure with
  `check_differentiation` (spread >= 0.25 over >= 3 bands, roster >= 5) and
  pass^k; iterate scenario difficulty until the gate passes. This is the exit
  condition.
- P6 Hardening: full test coverage, pytest marks, lint, types, NOTICE.
- P7 Report plus submission: `EVALUATION_REPORT.md`, figures, register entry,
  and `METHODOLOGY.md`. The latter documents exactly HOW the environment was
  configured so anyone can reproduce and reason about it: the source k8s recipe
  and why it cannot run on macOS, the decision to adapt to a local
  docker-compose substrate (a substrate change, not a component swap), the SCTP
  feasibility check on OrbStack, the components and their pins (Open5GS AIO
  v2.7.0, MongoDB plus subscriber seed, Prometheus, PacketRusher at its pinned
  ref), the concrete adaptations (AIO collapse, NGAP on n2 10.10.2.2, metrics
  bind 127.0.0.5 to 0.0.0.0, the bare-integer `-tr` flag, amd64 emulation), the
  sustained-overload tuning that makes capacity_rate fall below live_peak_rate,
  and how Inspect attaches the world (`sandbox=("docker", compose)`, the tools
  over `sandbox().exec`, the world_setup solver, storm vs baseline selection).
  Drafted once P4 locks the env config; finalised here.

## Grounded facts

- Metrics: `fivegs_amffunction_rm_reginitreq` and
  `fivegs_amffunction_rm_reginitsucc` on the AMF `/metrics` at port 9090,
  scraped by Prometheus.
- AMF config: `/open5gs/config/amfcfg.yaml`; AMF log:
  `/open5gs/install/var/log/open5gs/amf.log`; pod selector `app=open5gs,nf=amf`,
  namespace `open5gs`. Read via `kubectl exec ... cat`, not `kubectl logs` (the
  AMF has no stdout sink).
- Storm injector: PacketRusher Job `storm-injector`; rerun means delete then
  reapply the overlay. Worlds: `storm` and `baseline` only.
- Normative bounds and citations: see `docs/grounding/normative-sources.md`.

## Provenance caveat

The verbatim per-task `submission.json` was never checked in for this slug. The
authoritative grader contracts are the fragments quoted in the judge report
(`task-designer/judge-reports/china-unicom-...-sett.md`) plus the task table in
`README.md`. Treat the superseded `gsma-eval-designs` draft and the empty
`case_packet.json` as non-authoritative.
