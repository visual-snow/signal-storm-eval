# signal_storm_bench

A 5G core buckles when a re-registration surge floods the AMF faster than it can
process NAS. The on-call engineer has to read the storm off the live counters,
recommend standards-consistent flow control, and prove the setting would hold —
every time. This eval is being built to make an agent do exactly that, against a
live Open5GS core.

It is framed as a **production / mid-horizon** NOC-Bench eval: the deploy
question is not "can a model do this once?" but "can it do it *every* time?", so
the intended headline metric is **pass^k** over k epochs, not mean accuracy.

> **Status: product-scoring cleanup built.** The local docker-compose
> environment, Inspect task, agent tools, and numeric product scorers are
> implemented. Reference, bad, and partial artifacts for i1..i4 are tested, and
> offline scorer-anchor calibration is recorded in
> `docs/product-score-calibration.md`. A fresh product-scored
> live smoke passed; full product-prompt roster calibration is still pending.

## Use case

From the GSMA Foundry library: `china-unicom-henan-and-zte-simulating-signal-storms-and-setting-flow-controls`
— China Unicom Henan and ZTE used a digital twin to simulate signalling storms,
evaluate the peak load on the 5G core, recommend flow-control parameters, and
verify them before a risky operation (such as a disaster-recovery switchover).
This eval keeps the operator loop and drops the twin: a real storm is injected
against a real Open5GS core, the agent measures it off live metrics (i1), diagnoses the load state (i2), selects NGAP/NAS flow control (i3), and sizes the NAS back-off (i4). The apply-and-verify step is a follow-up plan (P1).

Each sample is one step of that loop. Only the **outcome** is graded — the JSON
answer the agent submitted, checked against the live core state and the
normative bounds — never the path it took. The agent investigates the running
core through Prometheus and the AMF config; it must not guess. The core enforces
no flow control of its own (see Environment), so the recommend tasks are graded
as reasoning against the live peak and the live `amfcfg.yaml`, not as a setting
the core acts on.

## Capabilities

To solve this use case the agent has to:

- **Characterise the storm** — scrape the AMF registration counters off
  Prometheus and quantify the surge: how many initial-registration requests
  arrived over the storm interval, and how far successful registrations lagged
  under load.
- **Pick the right control** — distinguish the genuine NGAP/NAS flow-control
  mechanisms (NGAP Overload Start, Traffic Load Reduction) from a non-control
  distractor knob, and select the standards-defined overload action for the
  situation.
- **Size the parameters** — derive a Traffic Load Reduction percentage that
  holds the offered load down to target, and a NAS back-off range that
  de-synchronises the deferred retries — both within their normative bounds.
- **Verify the control** — judge whether an undersized setting actually holds
  the load (it must not), and whether a no-storm baseline needs any control at
  all (it must not).

Underneath: 3GPP NGAP/NAS overload-control fluency (TS 38.413, TS 23.501),
reading live Prometheus counters and a real `amfcfg.yaml`, reasoning over live
state rather than recall, and emitting the structured JSON answer each task
specifies.

### Agent access

The toolset is the four live-state primitives a core NOC engineer would reach
for, with the standard per-incident message budget (~40 messages):

- `query_prometheus_metrics` — read the AMF registration counters
  (`fivegs_amffunction_rm_reginitreq` / `…_reginitsucc`) and their per-second
  rate off the live Prometheus API
- `read_amf_config` — read the running `amfcfg.yaml` (the flow-control surface
  the recommendation is reasoned against)
- `read_nf_log_file` — read an NF log on a named pod (the AMF log is the
  human-readable view of the same surge)
- `run_ue_storm_simulator` — run/replay the UE registration storm against the
  AMF on demand (the PacketRusher injector)

The grader never reads these tool calls. Outcomes are scored from the live core
state (the Prometheus counters, the running config) and the submitted JSON, plus
the normative spec bounds, so the agent cannot pass by narrating — it has to
read the real storm.

## Environment

One environment for the whole suite, loaded from the
[`open5gs_signaling_storm_sandbox`](https://github.com/visual-snow/env_recipes_telco/tree/main/recipes/open5gs_signaling_storm_sandbox)
recipe: a live Open5GS 5G core on Kubernetes (`niloysh/open5gs-k8s`, vendored
byte-for-byte at a pinned commit, on Multus + ovs-cni with a `runc`
RuntimeClass), with **PacketRusher** flooding the AMF with NGAP/NAS
registrations over SCTP and **Prometheus** scraping the AMF metrics endpoint.
It is the smallest world where a real registration storm drives a real AMF
counter, and the registration peak is *emergent* — read live off Prometheus, not
baked into the environment.

![Simulated components](agent_artefacts/signal_storm_bench_1A/evalreport/figures/env_simulated_components.png)

Two worlds, one stack, knob-driven: `storm` runs the injector
(`STORM_RATE`/`UE_COUNT` drive knobs; the peak they produce is emergent) and
`baseline` runs none (the AMF stays idle). A shared `identity` ConfigMap
single-sources the PLMN, keys, and IMSI base for both the PacketRusher UEs and
the MongoDB subscriber seed, so registered UEs always fall inside the seeded
pool. Crucially, **no open-source 5GC enforces NGAP overload control / Traffic
Load Reduction / NAS back-off** — Open5GS does not, and the recipe does not
pretend it does. There is no operator "ceiling" or "throttled" world baked in;
recommending flow-control parameters is a reasoning task against the live peak
and the live config. `my5G-RANTester` is the tool named in the original
benchmark stack and is kept as cited provenance; PacketRusher is its maintained
fork, chosen for a native rate flag, `int` UE ids, and Open5GS v2.7 interop.

## Task suite

The suite walks the operator's read-only investigation loop: measure the storm off the live core (i1), diagnose the load state in both an overloaded and an idle world (i2), select the flow-control mechanism and overload action (i3), and size the NAS back-off (i4). Each task asks for a concrete JSON product artifact and returns a numeric 0.0..1.0 score with component metadata. The old binary checks were replaced with weighted product scorers.

| ID | Task | What it tests | Grader |
|----|------|---------------|--------|
| i1 | Storm measurement extract | request count, peak rate, successes, and deficit read off live Prometheus | weighted measure() of request_count, peak_rate, success_count, and deficit against the live snapshot |
| i2 | Load-state diagnosis (storm + baseline worlds) | reading the live load state and whether action is warranted, in both an overloaded and an idle world | deterministic peak/deficit measurement plus a single temperature-0 LLM-judge verdict (Unknown scores 0) |
| i3 | Flow-control selection | picking the genuine NGAP/NAS overload controls from a candidate pool and naming protected vs shed traffic | set F1 over the correct mechanisms, a distractor penalty, and controlled-set traffic classes |
| i4 | NAS back-off sizing | sizing a back-off spread that disperses the live backlog within live capacity | live-derived retry-rate consistency and back-off safety against live capacity |

The TLR apply-and-verify task (P1) is built in a follow-up plan; the investigation suite above is the read-only loop. The earlier TLR-sizing and TLR-verify tasks (old t7/t9) are folded into that forthcoming P1.

The cleanup audit, formulas, score anchors, and residual risks are in
`docs/product-based-signal-storm-cleanup.md`.

## Results

No fresh product-scored model roster has been run yet. Local scorer-anchor
calibration is available in `docs/product-score-calibration.md`; each retained
task has bad, three partial, and reference anchors with visible per-task score
spread.

A guarded product-scored smoke run succeeded on 2026-06-19:
`logs/product-smoke/2026-06-19T15-19-38-00-00_signal-storm_3hsWR5QsWi6CpWhcHyhhSb.eval`
has status `success`, score `0.648`, and component metadata for t1. The next
live step is an epochs >= 3 roster run for pass^k and per-task product-prompt
distributions.

## Reproduce

Offline scorer validation does not start Docker:

```bash
uv run pytest tests/test_scorer_logic.py tests/test_product_calibration_report.py -q
uv run python scripts/generate_product_calibration_report.py docs/product-score-calibration.md
```

To rerun the live smoke, use the guarded wrapper so interrupted runs clean up
their docker sandboxes:

```bash
scripts/run_product_smoke.sh openrouter/anthropic/claude-haiku-4.5
scripts/stop_signal_storm_sandboxes.sh  # cleanup after manual interruption
```

For a full product-scored roster, run only after budget/runtime is approved:

```bash
MAX_SANDBOXES=1 bash scripts/run_iteration.sh product-p1 3
uv run python scripts/check_differentiation.py logs/product-p1
uv run python scripts/check_kind_differentiation.py logs/product-p1
uv run python scripts/pass_hat_k.py logs/product-p1
```

## More

- [Environment recipe](https://github.com/visual-snow/env_recipes_telco/tree/main/recipes/open5gs_signaling_storm_sandbox)
  — `open5gs_signaling_storm_sandbox`: the Open5GS + PacketRusher + Prometheus
  substrate, its `DESIGN.md`, `UPSTREAM_FACTS.md`, and the pytest contract suite.
- Judge report — `china-unicom-henan-and-zte-simulating-signal-storms-and-sett`
  (NOC-Bench task-bounty review, verdict SOLID 3.8/5): the per-task grounding,
  citation spot-checks, and the open grader improvements.
- `docs/product-based-signal-storm-cleanup.md` — retained-task rationale,
  scorer formulas, anchors, and residual risks.
- `docs/product-score-calibration.md` — offline per-task scorer-anchor spread.
