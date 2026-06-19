# Product Cleanup Acceptance Audit

Date: 2026-06-19.

This audits the product-based cleanup against the requested stopping criteria.
It is intentionally evidence-based: items marked `Pending` are not complete just
because the implementation is ready.

| Criterion | Status | Evidence |
|---|---|---|
| Every retained t1..t10 has a validated identity | Met | `docs/product-based-signal-storm-cleanup.md` retained-scope table maps each task to Open5GS/3GPP grounding. |
| Every retained task asks for one concrete product artifact | Met | `src/signal_storm_bench/dataset.py`; enforced by `tests/test_dataset.py::test_prompts_request_product_artifacts`. |
| No prompt leakage of hidden thresholds/final answers | Met | `tests/test_dataset.py` leakage tests cover metric names, t6 enum answer, t9/t10 verdicts, and sizing answers. |
| No binary-only "did they say X" scoring | Met | `src/signal_storm_bench/scorers.py` returns float scores with component metadata; `tests/test_scorer_logic.py` asserts reference/partial/bad ranges. |
| Product-based scorer returns numeric 0.0..1.0 with component metadata | Met | `tests/test_scorer_logic.py::TestUnparseableNeverErrors::test_reference_products_return_float_scores` and `assert_score_between`. |
| Reference, bad, and at least three partial artifacts per task | Met | `tests/test_scorer_logic.py`; summarized by `docs/product-score-calibration.md`. |
| Partial scores are meaningfully ordered and not just buckets | Met | `tests/test_product_calibration_report.py` requires five anchors, high reference, low bad, and at least four distinct scores per task. |
| Inspect metrics use numeric scoring | Met | `src/signal_storm_bench/scorers.py` uses `mean()` and `stderr()`. |
| Result scripts parse numeric scores | Met | `tests/test_differentiation.py`, `tests/test_kind_differentiation.py`, `tests/test_pass_hat_k.py`, and `tests/test_export_gate_artifacts.py`. |
| No scorer relies on fragile substring matching unless the string is itself product evidence | Met | Numeric/set scorers dominate. Product-text components use normalized phrase-boundary matching over submitted artifact fields; `tests/test_logic.py::test_term_coverage_uses_token_boundaries` pins the boundary behavior. |
| `uv run pytest` passes | Met for latest full run | Full suite passed earlier in cleanup (`199 passed, 1 skipped`). Latest targeted non-Docker suite passed after final doc/tooling edits. |
| Ruff and mypy pass | Met | Latest `ruff check`, `ruff format --check`, and `mypy src tests` passed during cleanup; latest targeted Ruff checks passed after final edits. |
| Smoke eval runs without infra failures counted as model failures | Pending | Product smoke was intentionally paused after laptop load. Use `scripts/run_product_smoke.sh` when Docker use is safe. |
| Local calibration report shows per-task score distributions | Met for scorer anchors | `docs/product-score-calibration.md` shows per-task reference/partial/bad score spread without Docker/model calls. |
| Calibration across product-scored model outputs or saved trajectories | Pending | Existing `logs/p5`/`logs/p5b` predate product scoring. Fresh product-scored logs are required. |
| Cleanup doc records retained/dropped rationale, formulas, grounding, anchors, risks | Met | `docs/product-based-signal-storm-cleanup.md` and this audit. |

## Pending Live Commands

Run only when Docker/model use is acceptable:

```bash
scripts/run_product_smoke.sh openrouter/anthropic/claude-haiku-4.5
uv run python scripts/check_differentiation.py logs/product-smoke
uv run python scripts/pass_hat_k.py logs/product-smoke
```

Full roster calibration remains budget/runtime gated:

```bash
MAX_SANDBOXES=1 bash scripts/run_iteration.sh product-p1 3
uv run python scripts/check_differentiation.py logs/product-p1
uv run python scripts/check_kind_differentiation.py logs/product-p1
uv run python scripts/pass_hat_k.py logs/product-p1
```
