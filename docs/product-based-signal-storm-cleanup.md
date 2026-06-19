# Product-based signal storm cleanup

Date: 2026-06-19. Branch: `eval-environment-and-harness`.

This records the cleanup from binary final-answer grading to product artifacts
with numeric component scores. The original external `submission.json` is not in
this repository; retained task identities are reconstructed from
`docs/superpowers/specs/2026-06-18-task-suite-design.md`, the current Inspect
dataset, and the grounding in `docs/grounding/normative-sources.md`.

## Retained and dropped scope

No numbered task IDs were dropped. All t1..t10 are retained because each now has
a concrete product artifact, a validated identity grounded in the local Open5GS
storm or 3GPP overload-control context, and a scorer that returns a numeric
0.0..1.0 product score with component metadata. What was dropped is the old
binary "did the model say the expected final answer" contract.

| Task | Retained product | Grounding | Rationale |
|---|---|---|---|
| t1 | Registration request count artifact | Live `fivegs_amffunction_rm_reginitreq` increase over storm interval | Measures whether the agent can identify the storm signal and count the requests. |
| t2 | Peak registration-rate artifact | Live `rate(reginitreq)` over the configured peak window | Measures live load characterization without exposing the hidden peak. |
| t3 | Registration deficit worksheet | Live request count, success count, and AMF rejection volume | Captures overload impact as arithmetic, not a single phrase. |
| t4 | Storm diagnosis memo | Live peak rate plus registration deficit | Requires a verdict supported by quantitative evidence. |
| t5 | Flow-control mechanism selection | TS 38.413 / TS 23.501 overload-control context | Separates genuine overload-control mechanisms from the load-balancing distractor. |
| t6 | Overload-action recommendation | TS 38.413 sec 9.3.1.105 and TS 23.501 sec 5.19.5.2 | Requires the protected and rejected traffic classes, not just enum recall. |
| t7 | Traffic Load Reduction worksheet | TS 38.413 sec 9.3.1.106 range 1..99 plus live capacity | Sizes TLR against live peak and capacity. |
| t8 | NAS backoff worksheet | TS 23.501 sec 5.19.7 plus live deferred volume/capacity | Converts deferred load into a desynchronised retry-rate product. |
| t9 | TLR verification memo | Given TLR, live peak/capacity, residual-rate arithmetic | Tests whether an undersized setting is rejected for the right reason. |
| t10 | Healthy-baseline assessment | Baseline live peak/deficit | Provides the opposite polarity: no flow control when the system is idle. |

## Scorer formulas

All task scores are weighted component averages. Numeric components use
`numeric_score(value, expected, error_scale)`, a clipped linear score in [0, 1].
Set/list components use set F1 or term coverage. Unparseable submissions score
0.0 and never raise.

| Task | Formula |
|---|---|
| t1 | `0.75 * request_count + 0.10 * unit + 0.10 * source_signal + 0.05 * window`; count tolerance is max(10% of live count, 1). |
| t2 | `0.75 * peak_rate + 0.10 * unit + 0.10 * source_signal + 0.05 * rate_window`; peak tolerance is max(25% of live peak, 1). |
| t3 | `0.25 * request_count + 0.25 * success_count + 0.35 * deficit + 0.10 * unit + 0.05 * arithmetic_consistency`; count/deficit tolerances are 10%. |
| t4 | `0.30 * peak_evidence + 0.25 * deficit_evidence + 0.30 * verdict + 0.15 * evidence_text`. |
| t5 | `0.55 * selected_mechanisms + 0.15 * excluded_distractor + 0.15 * no_unsafe_selected_distractor + 0.15 * rationale`. |
| t6 | Equal weights over action, protected traffic, rejected traffic, and rationale term coverage. |
| t7 | `0.20 * peak_measurement + 0.20 * capacity_measurement + 0.20 * formula_consistency + 0.30 * tlr_safety + 0.10 * range_sanity`; safety requires `peak * (1 - tlr / 100) <= capacity`. |
| t8 | `0.20 * deferred_volume + 0.20 * capacity_measurement + 0.15 * spread_order_sanity + 0.20 * expected_retry_rate + 0.25 * backoff_safety`; safety checks retry rate against submitted/live capacity or required spread. |
| t9 | `0.05 * given_tlr + 0.25 * peak_capacity_measurements + 0.25 * residual_rate + 0.30 * verdict + 0.15 * evidence`. |
| t10 | `0.35 * baseline_peak + 0.20 * deficit + 0.30 * no_action_recommendation + 0.15 * evidence`; unsafe control recommendations cap the total at 0.25. |

## Score anchors

The reference artifacts in `tests/test_scorer_logic.py` score high for every
task, and bad artifacts score low. Every task also has at least three distinct
partial artifacts to check ordering between bad and reference behavior.

| Anchor | Expected score range | Meaning |
|---|---:|---|
| Reference artifact | ideally >= 0.85 | Complete product with correct measurement, normative identity, and supporting context. |
| Strong partial | about 0.65..0.85 | Core numeric product is right but one context/rationale component is weak. |
| Mid partial | about 0.35..0.65 | Some meaningful work is present, but an important component is missing or wrong. |
| Weak partial | about 0.20..0.35 | Isolated useful evidence or a correct verdict without enough artifact content. |
| Bad/unparseable artifact | ideally <= 0.20 | Wrong product, unsafe recommendation, distractor selection, or no parseable JSON. |

The exact score values are intentionally not in prompts. Prompts request only
the product fields; hidden thresholds, final answers, and scorer weights remain
in code and documentation.

## Tooling changes

- Inspect scorer metrics now use `mean()` and `stderr()`, so suite results are
  numeric product means rather than binary accuracy.
- `scripts/check_differentiation.py` reads `mean` first and falls back to
  `accuracy` for old logs.
- `scripts/pass_hat_k.py` treats numeric scores >= 0.8 as passes and still
  accepts old C/I logs.
- `scripts/export_gate_artifacts.py` exports numeric per-kind means and samples
  scores below 0.8 as review failures.

## Calibration evidence

Local unit calibration is encoded in `tests/test_scorer_logic.py`: for each
task, a reference artifact, a bad artifact, and at least three ordered partial
artifacts exercise the full numeric scoring range. The saved roster logs
`logs/p5` and `logs/p5b` predate product scoring, so their binary scores are
historical only and are not valid product-score distributions. A fresh product
smoke/calibration run should write to `logs/product-smoke` and then the scripts
above can generate numeric summaries.

## Residual risks

- Verbatim 3GPP excerpts in `docs/grounding/normative-sources.md` are still
  placeholders; the cited sections and bounds are present, but the offline
  reviewer cannot yet verify exact source text.
- Full roster calibration across model outputs is still budget-dependent. Until
  a fresh product-scored roster exists, the strongest calibration evidence is
  the local anchor distribution in scorer tests plus smoke-run transcripts.
- t5/t6 remain sensitive to terminology. The scorer now grades components and
  term coverage instead of exact strings, but synonym coverage should be checked
  against fresh transcripts.
- Live scorers depend on stable Prometheus readings. Infrastructure failures
  should raise sample errors; they must not be interpreted as model failures.
