# art-of-evals compliance checklist

Re-scored by the `eval-reviewer` agent at the end of every build-loop iteration,
from exported artefacts only. Standard of record: `BEST_PRACTICES.md`,
`EVALUATION_CHECKLIST.md`, and the inspect_evals best-practices guide. The loop
exits only when every row is MET with reviewer sign-off. Status: MET / WIP /
GAP / TODO.

| # | Rule | Status | Evidence / gap |
|---|---|---|---|
| 1 | Prompt requires tool-driven work; no domain-naive pass | TODO | prompts not written (P1) |
| 2 | Prompt leak closed: no live peak, target, TLR, verdict, or t6 enum value | TODO | P1 |
| 3 | Ground truth only in scorer-side metadata, never agent-visible | TODO | P1, P3 |
| 4 | Outcome-led scoring: live state or product, never the trajectory | TODO | P3 |
| 5 | Scoring deterministic; no LLM judge | TODO | P3 |
| 6 | Scoring format-tolerant; unparseable scores 0, never errors | TODO | P3 |
| 7 | Thresholds grounded; verbatim spec excerpts vendored | WIP | `docs/grounding/` seeded; excerpts to paste |
| 8 | Three judge fixes applied (t9 and t10 synonyms, t5 candidates, t8 units) | TODO | P3 |
| 9 | t7..t10 re-grounded to the live emergent peak, not a baked ceiling | TODO | P3 |
| 10 | Infra failures raise as errors; model gaps score 0 | TODO | P3 |
| 11 | One primary bottleneck per task | TODO | P1 review |
| 12 | Tool access matches a real NOC engineer (four primitives, ~40 messages) | TODO | P3 |
| 13 | Both verdict polarities present incl. healthy baseline (t9, t10) | TODO | P1 |
| 14 | Difficulty spread: scores not clustered at 0 and 1 | TODO | P5 (check_differentiation) |
| 15 | Bottleneck diversity across tasks (read, select, size, judge) | TODO | P1 |
| 16 | Reliability metric matches use case: pass^k over epochs >= 3 | TODO | P5 |
| 17 | Environment is the real recipe; deterministic storm across repeats | WIP | recipe contract test pins it |
| 18 | Fresh, isolated world per sample where feasible | TODO | P2 (sandbox) |
| 19 | Transcript fairness: failures read as capability gaps, not harness bugs | TODO | P5 |
| 20 | Licensing and attribution recorded for vendored upstreams | TODO | NOTICE (P0, P6) |
