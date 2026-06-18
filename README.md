# signal_storm_bench

A 5G core buckles when a re-registration surge floods the AMF faster than it can
process NAS. The on-call engineer has to read the storm off the live counters,
recommend standards-consistent flow control, and prove the setting would hold —
every time. This eval is being built to make an agent do exactly that, against a
live Open5GS core.

It is framed as a **production / mid-horizon** NOC-Bench eval: the deploy
question is not "can a model do this once?" but "can it do it *every* time?", so
the intended headline metric is **pass^k** over k epochs, not mean accuracy.

> **Status: work in progress.** The environment (below) is built, booted, and
> contract-tested. The Inspect task, the agent tools, and the scorers are **not
> implemented yet**, and **no models have been run** — so there is no results
> table here. This README documents the use case, the recipe, and the designed
> task suite; the scoring surface and roster land in a later phase.

## Use case

From the GSMA Foundry library: `china-unicom-henan-and-zte-simulating-signal-storms-and-setting-flow-controls`
— China Unicom Henan and ZTE used a digital twin to simulate signalling storms,
evaluate the peak load on the 5G core, recommend flow-control parameters, and
verify them before a risky operation (such as a disaster-recovery switchover).
This eval keeps the operator loop and drops the twin: a real storm is injected
against a real Open5GS core, the agent characterises it off live metrics
(t1–t4), recommends NGAP/NAS flow-control parameters (t5–t8), then verifies them
(t9–t10).

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

Top to bottom the suite walks the operator loop: characterise the storm off the
live core (t1–t4), recommend standards-consistent flow control (t5–t8), then
verify it (t9–t10). It was judged **SOLID** (3.8/5) as a design; the graders
below are the designed scoring surface, not yet implemented.

| ID | Task | What it tests | Grader |
|----|------|---------------|--------|
| t1 | Report the AMF initial-registration count over the storm interval | counter-scrape arithmetic off live Prometheus | numeric match on the live `reginitreq` counter |
| t2–t4 | Characterise the storm further off the live counters and NF logs (peak rate, success deficit, storm-vs-normal) | live-state reading + storm quantification | *being finalised — graded against live counters* |
| t5 | Name the genuine flow-control mechanism, excluding the non-control distractor | mechanism selection (NGAP Overload Start / Traffic Load Reduction vs an AMF load-balancing weight) | Set match against the flow-control mechanism set |
| t6 | Select the standards-defined overload action | overload-action selection | exact match vs TS 38.413 §9.3.1.105 enumeration |
| t7 | Size the Traffic Load Reduction percentage that holds the load to target | normative parameter sizing | procedural: any TLR ∈ 1..99 that satisfies the live-peak inequality (TS 38.413 §9.3.1.106) |
| t8 | Derive a NAS back-off range that de-synchronises the deferred retries | de-sync back-off derivation | procedural: range > 0 and rejected volume / spread within headroom (TS 23.501 §5.19.7) |
| t9 | Judge whether an undersized TLR setting holds the load | negative case (verdict must be "ineffective") | Composite: verdict + live-state check, synonym-normalised |
| t10 | Judge whether the no-storm baseline needs any control | negative case (verdict must be "no control needed") | Composite: verdict + live-state check, synonym-normalised |

> **Open WIP on the suite.** The original design assumed an operator-defined
> "ceiling" and a third "throttled" world; the environment de-slop removed both
> (no OSS 5GC enforces flow control). The t7–t10 graders are being re-grounded
> to score against the **live emergent peak** rather than a baked ceiling, and
> the t2–t4 read tasks and the t5/t9 synonym sets are being finalised per the
> judge report. See the [judge report](#more) for the per-task grounding and the
> three concrete grader improvements still to apply.

## Results — not yet run

No models have been evaluated. Once the Inspect task and scorers land, this
section will carry the standard NOC-Bench roster table (Model | Accuracy |
pass^k | Tokens in/out | $/M in→out | Cost | Time) and the three blueprint
figures (pass^k decay, reliability gap, capability heatmap), with cost computed
from the actual `.eval` logs against live OpenRouter prices.

## Reproduce

The environment is reproducible today; the eval is not yet. To boot the world
and read the emergent storm off the live core (full validated bring-up in the
recipe's [`LOCAL_BOOT.md`](https://github.com/visual-snow/env_recipes_telco/blob/main/recipes/open5gs_signaling_storm_sandbox/LOCAL_BOOT.md)):

```bash
# on a Linux k8s cluster with Multus + ovs-cni + a runc RuntimeClass
# (prepare with the upstream testbed-automator)
cd recipes/open5gs_signaling_storm_sandbox
make WORLD=storm up            # base + Prometheus + PacketRusher + subscriber seed
make test                      # SANDBOX_KUBE_CONTEXT=<ctx> for the cluster tests

# read the storm live: the registration counter climbs under load
kubectl exec -n open5gs deploy/prometheus -- \
  wget -qO- 'http://localhost:9090/api/v1/query?query=fivegs_amffunction_rm_reginitreq'

make WORLD=storm down
```

```bash
# once the Inspect task lands (placeholder — not wired yet):
# uv run inspect eval signal_storm_bench/signal_storm \
#   --model openrouter/<model> --epochs 3 --log-dir logs/report
```

## More

- [Environment recipe](https://github.com/visual-snow/env_recipes_telco/tree/main/recipes/open5gs_signaling_storm_sandbox)
  — `open5gs_signaling_storm_sandbox`: the Open5GS + PacketRusher + Prometheus
  substrate, its `DESIGN.md`, `UPSTREAM_FACTS.md`, and the pytest contract suite.
- Judge report — `china-unicom-henan-and-zte-simulating-signal-storms-and-sett`
  (NOC-Bench task-bounty review, verdict SOLID 3.8/5): the per-task grounding,
  citation spot-checks, and the open grader improvements.
- The Inspect task, scorers, `EVALUATION_REPORT.md`, and `TEMPLATE.md`
  scaffolding land with the next phase.
