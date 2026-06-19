# Build loop

Each iteration: build or fix one artefact, run the roster, read transcripts, run
the two gates, fix the highest-impact gap, log it, repeat. Exit only when all
three hold at once:

1. Every roster model completes error-free (status success, zero sample errors).
2. The suite differentiates: `scripts/check_differentiation.py` passes (spread
   >= 0.25 between best and worst, at least three bands separated by > 0.05,
   roster >= 5).
3. The `eval-reviewer` agent has read the exported run summary and transcripts
   and signed off. It scores the work against `BEST_PRACTICES.md` and
   `EVALUATION_CHECKLIST.md`, returning a 1..10 score plus a per-row verdict;
   sign-off requires the target score and no failing load-bearing row.

## Rules

- The environment is the real recipe; never stub, mock, or swap a named
  component. Any infrastructure error is fixed first and blocks everything.
- Ground truth lives only in scorer-side metadata; prompts stay leak-closed.
- Every error, the rule it broke, and the fix go in `docs/iteration-log.md`.
- Scorer or threshold changes re-verify against `docs/grounding/`.

## Run

    bash scripts/run_iteration.sh <name> [epochs]   # ported in P0

Roster: five models over OpenRouter, pinned in P0. Epochs: 1 while iterating,
and >= 3 for the reliability pass (pass^k is the headline metric).

## Gates

    uv run python scripts/check_differentiation.py logs/<iter>
    uv run python scripts/pass_hat_k.py logs/<iter>
    uv run python scripts/export_gate_artifacts.py logs/<iter> gate_exports/<iter>

`check_differentiation` applies exit criterion 2. `pass_hat_k` reports the
headline reliability metric (unbiased estimator C(c,k)/C(n,k), mean over
samples; correct means full credit). `export_gate_artifacts` produces the
hermetic input for the reviewer.

## Reviewer (generator and critique)

Export first; the reviewer judges only what is on disk. Then dispatch the
`eval-reviewer` agent (read-only: Read, Grep, Glob, spec-corpus search) on the
export, the repo, and the checklist. It scores against `BEST_PRACTICES.md` and
returns a 1..10 score with per-row PASS or FAIL. Append its verdict to
`docs/iteration-log.md` under the iteration heading. Any failing load-bearing
row blocks the next iteration.
