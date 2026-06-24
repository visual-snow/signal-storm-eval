# Product-based signal storm eval cleanup design

Date: 2026-06-19
Status: approved design, pending implementation plan

## Goal

Rebuild `signal_storm_bench` so each surviving task measures the product the
agent produced, not a bare answer token. The Open5GS environment remains the
suite substrate. Task identities `t1..t10` are retained only when they can be
made real and validated under the art-of-evals task and suite guidance.

The target is a capability-style RL environment: each task should produce a
verifiable reward in `[0, 1]` with enough gradation to distinguish bad,
incomplete, mostly correct, and excellent artifacts.

## Sources

- `../art-of-evals/content/docs/02-evaluation-model/03-environment.md`
- `../art-of-evals/content/docs/02-evaluation-model/04-suite.md`
- `../art-of-evals/content/docs/02-evaluation-model/05-task.md`
- `../task-designer/judge-reports/china-unicom-henan-and-zte-simulating-signal-storms-and-sett.md`
- `src/signal_storm_bench/`
- `logs/p5`, `logs/p5b`, and `gate_exports/p5/summary.md`

The original `submission.json` for this task-designer slug is not present under
`../task-designer/gsma_task_bounty/china-unicom-henan-and-zte-simulating-signal-storms-and-sett/`.
The authoritative local design source is therefore the judge report plus the
task-designer guide and the current implementation. Keep that provenance caveat
visible in future reports.

## Current Failure

The current suite can pass aggregate differentiation while individual tasks are
not valid capability measurements.

- `t5` saturates: `6/6` on `logs/p5b`.
- `t6` floors: `0/6` on `logs/p5b`.
- `t1`, `t2`, `t7`, and `t8` are near-floor and noisy.
- `t4`, `t9`, and `t10` rely heavily on binary verdicts.
- The aggregate suite means separate models, but that separation can come from
broken or brittle tasks rather than real per-task capability signal.
- No task has a reference product artifact proving that the scorer accepts a
known-good solution.

The fix is not to tune binary thresholds. The fix is to make each task ask for a
concrete operator artifact and score artifact quality gradually.

## Design Principles

1. Preserve the environment unless it causes scoring noise.
2. Keep task identities only when they are real and validated.
3. Score products, not tokens.
4. Return continuous or fine-grained scores wherever possible.
5. Treat `0.0`, `0.3`, `0.5`, `0.8`, and `1.0` as explanatory anchors, not the
   only score values.
6. Write reference artifacts before trusting model scores.
7. Calibrate per task, not only at suite mean.
8. Keep scorer-only ground truth hidden from the agent.

## Retention Gate

Each task identity must pass this gate before implementation:

- It maps to the original signal-storm use case.
- It asks for one concrete product artifact.
- The product has one primary bottleneck.
- The scorer can inspect live state, hidden references, or grounded normative
  criteria.
- A reference artifact can score at least `0.95`.
- Bad and partial artifacts produce distinguishable scores between `0` and `1`.
- The prompt does not leak final values, expected labels, hidden thresholds, or
  scoring weights.

If a task cannot pass this gate without becoming fake or binary-only, drop it
from the suite and document why.

## Task Products

| id | Product artifact | Product-based score shape |
|---|---|---|
| `t1` | Storm interval measurement extract: request count, unit, source signal, time window | Numeric closeness to live request count plus credit for correct signal, unit, and interval semantics |
| `t2` | Peak-load measurement extract: peak rate, unit, source signal, rate window | Continuous error against live peak rate plus credit for using rate semantics rather than total count |
| `t3` | Registration deficit note: requests, successes, deficit, unit | Score requests, successes, and deficit separately so measurement and arithmetic mistakes are distinguishable |
| `t4` | Load-state assessment memo: verdict, measured evidence, reason | Score measured evidence and classification; no one-bit-only verdict grader |
| `t5` | Flow-control mechanism recommendation: selected mechanisms, excluded distractors, rationale | Set F1/Jaccard for selected mechanisms, penalty for unsafe distractors, and rationale credit for NGAP/NAS flow-control grounding |
| `t6` | Overload-action policy proposal: action, protected traffic class, rejected traffic class, standards rationale | Component scoring for semantic equivalence to the 3GPP action, not exact enum string matching |
| `t7` | TLR sizing worksheet: peak, capacity, formula, proposed TLR, expected post-control load | Score measurement quality, formula consistency, proposed TLR safety, and post-control calculation |
| `t8` | NAS backoff dispersion worksheet: deferred volume, absorbable rate, min/max, spread, expected retry rate | Score measurement quality and continuous safety margin of retry rate versus capacity |
| `t9` | Proposed-control verification memo: given TLR, measured peak/capacity, computed residual load, verdict | Score evidence, recomputation, and verdict; a correct word such as "insufficient" earns little without the product evidence |
| `t10` | Baseline no-action assessment: measured load, threshold comparison, action recommendation | Score baseline evidence and no-action recommendation; avoid string matching on "no" or "not required" |

## Scoring Model

Scorers should return floats in `[0, 1]`. They may use weighted components when
the components are part of one artifact. They should not average unrelated
subtasks.

Recommended primitives:

- Numeric distance: `max(0, 1 - abs(answer - reference) / error_scale)`.
- Set agreement: F1 or Jaccard, with explicit penalties for unsafe extras.
- Range/sizing safety: full credit for safe satisfying values, partial credit for
  near misses, strong penalty for unsafe over-action or under-protection.
- Evidence completeness: small but meaningful credit for correct metric/window,
  unit, formula, and source fields.
- Semantic normalization: normalize known telecom concepts without requiring one
  exact string when the artifact meaning is correct.

Unparseable artifacts should score `0` but never crash scoring. Infrastructure
failures should raise and error the sample rather than score as model failure.

## Implementation Shape

- `dataset.py`: update prompts from single-value answers to structured artifact
  schemas. Keep hidden references and scoring weights out of prompts.
- `logic.py`: add reusable scoring primitives for numeric distance, set
  agreement, range safety, evidence completeness, and telecom concept
  normalization.
- `scorers.py`: replace binary `CORRECT`/`INCORRECT` task scoring with
  product-scoring floats.
- `tests/test_scorer_logic.py`: add reference, bad, and partial artifact cases
  for every surviving task.
- Documentation: record formulas, score anchors, reference artifacts, task
  retention decisions, and calibration results.

## Validation Gates

Before running the full model roster:

- Every surviving task has a reference artifact scoring `>= 0.95`.
- Every surviving task has a known-bad artifact scoring low.
- Every surviving task has at least three partial examples with distinct scores.
- No surviving task returns only `{0, 1}` across its scorer unit tests.
- Live-state tasks have health gates that prevent degenerate worlds from
  becoming model failures.

Before calling the eval fixed:

- Report per-task model score distributions, not only aggregate mean.
- Use repeated epochs for reliability metrics when runtime permits.
- Confirm no task is saturated at `1.0` or floored at `0.0` across the target
  model roster unless the design explicitly accepts that as a regression case.
- Document any dropped `tN` identities and why they failed the retention gate.

## Out of Scope For This Cleanup

- Replacing the Open5GS docker-compose environment.
- Adding unrelated telecom use cases.
- Adding an LLM judge as the primary runtime scorer.
- Optimizing the suite to pass the existing aggregate differentiation script
  without per-task validation.
