# Task suite design: signal_storm_bench t1..t10

Date: 2026-06-18
Status: design; the source of truth for P1 (dataset and prompts) and P3 (tools
and scorers). The `eval-reviewer` grades the implementation against this spec.

## Sources of authority

The grader contracts are the fragments quoted in the judge report
(`task-designer/judge-reports/china-unicom-...-sett.md`) plus the task table in
`README.md`. The verbatim per-task `submission.json` was never checked in for
this slug, so the JSON schemas below are the faithful reconstruction. The empty
`case_packet.json` and the pre-judge `gsma-eval-designs` draft are NOT
authoritative. Normative bounds live in `docs/grounding/normative-sources.md`.

## Grading philosophy

Outcome-only. The agent submits a JSON object; the scorer parses it
format-tolerantly (unparseable scores 0, never raises), then grades against
(a) live core state read at grade time off Prometheus and the running
`amf.yaml`, and (b) the normative bounds. Ground truth (expected verdicts, the
t6 enum, the t5 distractor, the live-derived target) lives only in scorer-side
`Sample.metadata` and live probes; never in the prompt. Verdict helpers are
tristate: unclear maps to None, and None never scores correct. Headline metric
is pass^k over epochs; correct means score 1.0. Infrastructure errors raise and
error the sample; model mistakes score 0.

## Live-state model (the re-grounding)

The original design assumed a baked operator "ceiling" and a "throttled" world;
the env de-slop removed both because no open-source 5GC enforces flow control.
Every sized or verify task reads the emergent storm live:

- `live_count` = `increase(fivegs_amffunction_rm_reginitreq[storm_interval])`
  (registrations).
- `live_peak_rate` = max sustained `rate(fivegs_amffunction_rm_reginitreq[30s])`
  over the storm window (registrations/second).
- `capacity_rate` = max sustained
  `rate(fivegs_amffunction_rm_reginitsucc[30s])` (registrations/second). This is
  the AMF's emergent processing throughput under load; the live target.
- `rejected_volume` = `live_count - increase(fivegs_amffunction_rm_reginitsucc[storm_interval])`
  (registrations); the deferred retries the back-off must disperse.

Empirical dependency: the storm must overload the all-in-one AMF enough to make
a real deficit (`reginitreq > reginitsucc`). If it does not, raise
`STORM_RATE` / `UE_COUNT` in P5. P2 (env bring-up) and P5 (differentiation)
validate this; the storm window and knobs are recorded in scorer-side metadata
so the live reads are reproducible across epochs for pass^k.

## Worlds

- `storm`: the injector has run; counters are populated and a deficit is
  present. Tasks t1..t9.
- `baseline`: the injector is idle; counters stay near zero. Task t10.

The world is a per-sample property. The `world_setup()` solver runs the storm
for storm samples before the agent starts (counters standing); the
`run_ue_storm_simulator` tool lets the agent replay or extend it. t10 runs in
`baseline` and never triggers the injector.

## Per-task contracts

Tools key: PROM `query_prometheus_metrics`, CFG `read_amf_config`, LOG
`read_nf_log_file`, SIM `run_ue_storm_simulator`. All graders are binary
(score 1.0 or 0.0) unless noted.

| id | world | prompt intent (leak-closed) | answer JSON | scorer decide() | tools |
|----|-------|------------------------------|-------------|-----------------|-------|
| t1 | storm | how many initial-registration requests arrived over the storm interval | `{"count": int}` | `abs(count - live_count)` within relative tolerance (~one scrape interval) | PROM, LOG |
| t2 | storm | the peak registration rate during the storm | `{"peak_rate": number}` | within +/-10% of `live_peak_rate` | PROM |
| t3 | storm | how far successful registrations lagged (the deficit) | `{"deficit": number}` | within tolerance of `rejected_volume` | PROM |
| t4 | storm | classify current load as storm or normal | `{"verdict": "storm"\|"normal"}` | normalized verdict equals whether live counters exceed the baseline band (storm world -> "storm") | PROM |
| t5 | storm | from the candidate list, name the genuine flow-control mechanism(s) | `{"mechanisms": [str]}` | normalized set equals `{NGAP Overload Start, Traffic Load Reduction}`; the distractor `AMF load-balancing Weight Factor` excluded | CFG, PROM |
| t6 | storm | the standards-defined overload action for this load | `{"overload_action": str}` | format-tolerant match vs TS 38.413 sec 9.3.1.105 value "Permit Emergency Sessions and mobile terminated services only" | CFG, PROM |
| t7 | storm | size the Traffic Load Reduction percent that holds load to target | `{"tlr_percent": int}` | `1 <= tlr <= 99` AND `live_peak_rate * (1 - tlr/100) <= capacity_rate` | PROM, CFG |
| t8 | storm | derive a NAS back-off range that de-synchronises the deferred retries | `{"backoff_min": number, "backoff_max": number}` | `spread = max - min`; `spread > 0` AND `rejected_volume / spread <= capacity_rate` | PROM, CFG |
| t9 | storm | judge whether a proposed (undersized) TLR holds the load | `{"verdict": str}` | verdict normalized in {ineffective, not capped, ceiling exceeded, overloaded} AND `live_peak_rate * (1 - given_tlr/100) > capacity_rate` (given_tlr in metadata) | PROM, CFG |
| t10 | baseline | judge whether the no-storm baseline needs any control | `{"verdict": str}` | verdict normalized in {no control needed, not required, below ceiling} AND `live_peak_rate` below the idle threshold | PROM |

## Resolved open questions

1. The deleted `ceiling` / `seeded_peak` become the live `capacity_rate` and
   `live_peak_rate` above. t7 and t9 grade against them.
2. t8 units reconcile cleanly: `rejected_volume` (registrations) divided by
   `spread` (seconds) compared to `capacity_rate` (registrations/second). The
   deferred retries, spread over the back-off window, must arrive at a rate the
   AMF can absorb. `range > 0` carries the TS 23.501 sec 5.19.7 de-sync rule.
3. t5 candidate list is published neutrally: NGAP Overload Start, Traffic Load
   Reduction Indication, AMF load-balancing Weight Factor. The instruction does
   NOT hint which is the distractor.
4. t9 and t10 adopt the synonym sets above; normalize by lowercasing and
   stripping punctuation; unclear maps to None and fails.
5. t2..t4 schemas and graders are defined above, all against live counters with
   relative tolerance.
6. t1 uses a relative tolerance (about one scrape interval); TS 28.552 sec 5.2
   is not vendored because no normative measurement definition was confirmed.
7. Determinism: pin the storm config; record the storm window and knobs in
   scorer-side metadata.
8. `run_ue_storm_simulator` is driven by `world_setup()` for storm samples; the
   agent may replay it; t10 baseline never runs it.

## Leakage rules

Prompts must NOT contain: any live count, rate, peak, target, or capacity value;
the correct TLR; the back-off pair; the t6 enum answer; the expected t9 or t10
verdict; or the metric name (the agent discovers
`fivegs_amffunction_rm_reginitreq` through PROM). The t5 instruction stays
neutral. Ground truth lives only in `Sample.metadata` and live probes.

## Dataset validity (each sample passable and failable)

- t1..t4: pass by reading live counters with correct PromQL; fail by guessing,
  mis-windowing the interval, or keying on the wrong metric.
- t5: pass by naming the genuine set; fail by including the distractor or
  dropping a real mechanism.
- t6: pass with the exact enum action; fail with a wrong or non-enum action.
- t7: pass with any in-range TLR satisfying the live inequality; fail when out
  of range or under-reducing.
- t8: pass with a non-zero spread wide enough to disperse the deficit; fail with
  a single timer or too narrow a spread.
- t9 (negative): pass only by judging it ineffective AND the live state agreeing;
  fail by saying it works.
- t10 (negative): pass only by judging no control needed AND the live baseline
  confirming low load; fail by recommending control.
