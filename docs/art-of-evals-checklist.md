# art-of-evals compliance checklist

Re-scored by the `eval-reviewer` agent at the end of every build-loop iteration,
from exported artefacts only. Standard of record: `BEST_PRACTICES.md`,
`EVALUATION_CHECKLIST.md`, and the inspect_evals best-practices guide. Current
product-scoring cleanup evidence is in
`docs/product-based-signal-storm-cleanup.md`. Status: MET / WIP / GAP / TODO.

| # | Rule | Status | Evidence / gap |
|---|---|---|---|
| 1 | Prompt requires tool-driven work; no domain-naive pass | MET | t1..t4/t7..t10 require live measurements; t5/t6 require 3GPP-grounded mechanism/action products |
| 2 | Prompt leak closed: no live peak, target, TLR, verdict, or t6 enum value | MET | dataset tests check product prompts avoid hidden thresholds/final answers |
| 3 | Ground truth only in scorer-side metadata, never agent-visible | MET | live values and hidden TLR/baseline metadata remain in scorer-side metadata |
| 4 | Outcome-led scoring: live state or product, never the trajectory | MET | `decide()` scores artifacts against `LiveState`/metadata only |
| 5 | Scoring deterministic; no LLM judge | MET | pure Python scorers and unit tests; no model judge |
| 6 | Scoring format-tolerant; unparseable scores 0, never errors | MET | parser accepts fenced/embedded JSON; unparseable path returns numeric 0.0 |
| 7 | Thresholds grounded; verbatim spec excerpts vendored | WIP | citations/bounds are recorded; verbatim excerpts still placeholders |
| 8 | Three judge fixes applied (t9 and t10 synonyms, t5 candidates, t8 units) | MET | product scorers cover t5 distractor, t8 retry units/range, t9/t10 verdict polarity |
| 9 | t7..t10 re-grounded to the live emergent peak, not a baked ceiling | MET | t7/t8/t9/t10 use live peak/capacity/baseline probes |
| 10 | Infra failures raise as errors; model gaps score 0 | MET | sandbox probe failures raise; parser/model gaps score numeric 0.0 |
| 11 | One primary bottleneck per task | WIP | each task now has one product, but t7/t8 still combine measurement and sizing components |
| 12 | Tool access matches a real NOC engineer (four primitives, ~40 messages) | MET | tools remain Prometheus/config/log/storm primitives; message limit is 50 |
| 13 | Both verdict polarities present incl. healthy baseline (t9, t10) | MET | t9 rejects undersized TLR; t10 rewards no-control baseline assessment |
| 14 | Difficulty spread: scores not clustered at 0 and 1 | WIP | anchor tests show ordered partials and saved-log rescoring shows per-task spread; fresh product-prompt roster calibration still needed |
| 15 | Bottleneck diversity across tasks (read, select, size, judge) | MET | measurement, mechanism selection, sizing, verification, and baseline judgment products |
| 16 | Reliability metric matches use case: pass^k over epochs >= 3 | WIP | `pass_hat_k.py` supports numeric pass threshold and parsed product-smoke numeric scores; needs fresh epochs>=3 roster run |
| 17 | Environment is the real recipe; deterministic storm across repeats | WIP | recipe contract test pins it |
| 18 | Fresh, isolated world per sample where feasible | MET | Inspect docker sandbox boots a fresh compose world per sample/epoch |
| 19 | Transcript fairness: failures read as capability gaps, not harness bugs | WIP | product-smoke export samples numeric model-output failure and keeps infra-error logs out of low-score transcript sampling; full roster review pending |
| 20 | Licensing and attribution recorded for vendored upstreams | TODO | NOTICE (P0, P6) |
