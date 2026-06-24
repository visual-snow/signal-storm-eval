# Product-Based Signal Storm Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current binary/brittle `signal_storm_bench` task scoring with product-based, gradual `[0, 1]` scorers and reference-backed tests for every surviving task identity.

**Architecture:** Keep the Open5GS docker-compose environment, task entry point, tools, and live-state probes. Change the agent-facing prompts to request structured operator artifacts, add pure scoring primitives in `logic.py`, convert `scorers.py` to return numeric product scores with component metadata, and update result scripts to understand numeric scores.

**Tech Stack:** Python 3.11, Inspect AI scorers (`Score.value: float`, `mean()`, `stderr()`), `uv`, pytest, ruff, docker-compose sandbox for live smoke runs.

---

## File Structure

- Modify `src/signal_storm_bench/logic.py`: generic pure helpers for numeric distance, set agreement, term coverage, range safety, and component aggregation.
- Modify `src/signal_storm_bench/dataset.py`: prompts and `submission_shape` metadata for product artifacts instead of single-value answers.
- Modify `src/signal_storm_bench/scorers.py`: task-specific product scorers, numeric `Score.value`, component metadata, and `mean()` metric.
- Modify `src/signal_storm_bench/sandbox_ops.py`: add a success-count probe if needed for `t3` product scoring.
- Modify `tests/test_logic.py`: helper-level tests for gradual scoring primitives.
- Modify `tests/test_dataset.py`: product-schema and leakage tests.
- Replace most of `tests/test_scorer_logic.py`: reference, bad, and partial artifact tests for each task.
- Modify `scripts/check_differentiation.py`: collect numeric `mean` metric as well as legacy `accuracy`.
- Modify `scripts/pass_hat_k.py`: support numeric scores with a quality threshold, default `>= 0.8`.
- Modify `scripts/export_gate_artifacts.py`: report numeric product means and sample low-scoring transcripts correctly.
- Modify `tests/test_differentiation.py` and `tests/test_pass_hat_k.py`: script behavior tests.
- Create `tests/test_export_gate_artifacts.py`: unit tests for numeric score helper behavior in export artifacts.
- Modify `src/signal_storm_bench/README.md`, `HANDOVER.md`, and `docs/art-of-evals-checklist.md`: document product scoring status and remaining calibration work.

Do not change `src/signal_storm_bench/topology/` unless live validation proves the world is still degenerating.

## Shared Conventions

Use these artifact field names unless implementation discovers a strong reason to adjust:

- `t1`: `{"request_count": number, "unit": "registrations", "source_signal": string, "window": string}`
- `t2`: `{"peak_rate": number, "unit": "registrations_per_second", "source_signal": string, "rate_window": string}`
- `t3`: `{"request_count": number, "success_count": number, "deficit": number, "unit": "registrations"}`
- `t4`: `{"verdict": string, "peak_rate": number, "deficit": number, "evidence": string}`
- `t5`: `{"mechanisms": [string], "excluded": [string], "rationale": string}`
- `t6`: `{"action": string, "protected_traffic": [string], "rejected_traffic": [string], "rationale": string}`
- `t7`: `{"peak_rate": number, "capacity_rate": number, "formula": string, "tlr_percent": number, "post_control_rate": number}`
- `t8`: `{"deferred_volume": number, "capacity_rate": number, "backoff_min": number, "backoff_max": number, "expected_retry_rate": number}`
- `t9`: `{"given_tlr_percent": number, "peak_rate": number, "capacity_rate": number, "residual_rate": number, "verdict": string, "evidence": string}`
- `t10`: `{"peak_rate": number, "deficit": number, "recommendation": string, "evidence": string}`

Use weighted component scoring. Store component values in `Score.metadata["components"]` and include a short explanation showing the decisive live references.

Each surviving task must have one reference artifact, one bad artifact, and at least three partial artifacts with distinct non-binary scores in `tests/test_scorer_logic.py`.

---

### Task 1: Add Gradual Scoring Primitives

**Files:**
- Modify: `tests/test_logic.py`
- Modify: `src/signal_storm_bench/logic.py`

- [ ] **Step 1: Write failing tests for numeric and component scoring**

Add tests near the numeric helper section in `tests/test_logic.py`:

```python
from signal_storm_bench.logic import (
    clamp01,
    component_average,
    numeric_score,
    set_f1_score,
    term_coverage,
)


def test_numeric_score_is_gradual():
    assert numeric_score(100, 100, error_scale=50) == 1.0
    assert numeric_score(125, 100, error_scale=50) == 0.5
    assert numeric_score(200, 100, error_scale=50) == 0.0


def test_numeric_score_handles_non_numeric_as_zero():
    assert numeric_score("bad", 100, error_scale=50) == 0.0
    assert numeric_score(None, 100, error_scale=50) == 0.0


def test_set_f1_score_rewards_partial_sets():
    assert set_f1_score(["a", "b"], ["a", "b"]) == 1.0
    assert set_f1_score(["a"], ["a", "b"]) == pytest.approx(2 / 3)
    assert set_f1_score(["x"], ["a", "b"]) == 0.0


def test_term_coverage_is_gradual():
    assert term_coverage("permit emergency and mobile terminated traffic", {"emergency", "mobile terminated"}) == 1.0
    assert term_coverage("permit emergency traffic", {"emergency", "mobile terminated"}) == 0.5


def test_component_average_clamps_and_weights():
    assert clamp01(1.5) == 1.0
    assert component_average({"a": 1.0, "b": 0.5}, {"a": 0.75, "b": 0.25}) == pytest.approx(0.875)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_logic.py -q`

Expected: FAIL because the new helper functions do not exist.

- [ ] **Step 3: Implement minimal helpers**

Add to `src/signal_storm_bench/logic.py`:

```python
from collections.abc import Iterable, Mapping


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None


def numeric_score(value: object, reference: float, error_scale: float) -> float:
    parsed = as_float(value)
    if parsed is None or error_scale <= 0:
        return 0.0
    return clamp01(1.0 - abs(parsed - reference) / error_scale)


def set_f1_score(answer: Iterable[object], expected: Iterable[object]) -> float:
    answer_set = {normalize_verdict(str(x)) for x in answer if str(x).strip()}
    expected_set = {normalize_verdict(str(x)) for x in expected if str(x).strip()}
    if not answer_set and not expected_set:
        return 1.0
    if not answer_set or not expected_set:
        return 0.0
    true_pos = len(answer_set & expected_set)
    precision = true_pos / len(answer_set)
    recall = true_pos / len(expected_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def term_coverage(text: object, required_terms: set[str]) -> float:
    if not required_terms:
        return 1.0
    normalized = normalize_verdict(str(text))
    hits = sum(1 for term in required_terms if normalize_verdict(term) in normalized)
    return hits / len(required_terms)


def component_average(
    components: Mapping[str, float], weights: Mapping[str, float]
) -> float:
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    total = sum(clamp01(components.get(name, 0.0)) * weight for name, weight in weights.items())
    return clamp01(total / total_weight)
```

- [ ] **Step 4: Run helper tests**

Run: `uv run pytest tests/test_logic.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/signal_storm_bench/logic.py tests/test_logic.py
git commit -m "feat: add product scoring primitives"
```

---

### Task 2: Convert Dataset Prompts To Product Artifact Schemas

**Files:**
- Modify: `src/signal_storm_bench/dataset.py`
- Modify: `src/signal_storm_bench/scorers.py`
- Modify: `tests/test_dataset.py`
- Modify: `tests/test_scorer_logic.py`

- [ ] **Step 1: Write failing dataset tests for product fields**

Add a test in `tests/test_dataset.py`:

```python
def test_prompts_request_product_artifacts():
    by_kind = {s.metadata["task_kind"]: s for s in build_samples()}
    expected_fields = {
        "t1": ["request_count", "unit", "source_signal", "window"],
        "t2": ["peak_rate", "unit", "source_signal", "rate_window"],
        "t3": ["request_count", "success_count", "deficit", "unit"],
        "t4": ["verdict", "peak_rate", "deficit", "evidence"],
        "t5": ["mechanisms", "excluded", "rationale"],
        "t6": ["action", "protected_traffic", "rejected_traffic", "rationale"],
        "t7": ["peak_rate", "capacity_rate", "formula", "tlr_percent", "post_control_rate"],
        "t8": ["deferred_volume", "capacity_rate", "backoff_min", "backoff_max", "expected_retry_rate"],
        "t9": ["given_tlr_percent", "peak_rate", "capacity_rate", "residual_rate", "verdict", "evidence"],
        "t10": ["peak_rate", "deficit", "recommendation", "evidence"],
    }
    for kind, fields in expected_fields.items():
        prompt = by_kind[kind].input
        for field in fields:
            assert field in prompt
        assert "Submit your answer as JSON" in prompt
```

Update existing tests that expect old field names, especially `test_sizing_prompts_ask_for_the_answer_without_supplying_it`.

- [ ] **Step 2: Run dataset tests to verify failure**

Run: `uv run pytest tests/test_dataset.py -q`

Expected: FAIL because prompts still request bare answers.

- [ ] **Step 3: Add temporary scorer field aliases**

Before changing prompts, make the current binary scorer tolerate both old and new product field names so this commit remains live-eval compatible while later tasks convert scoring formulas.

Add tests in `tests/test_scorer_logic.py` proving aliases work during migration:

```python
def test_t1_accepts_product_request_count_during_migration() -> None:
    c = json.dumps({"request_count": 10100, "unit": "registrations", "source_signal": "AMF requests", "window": "5m"})
    assert decide("t1", c, STORM_REC, STORM_LIVE).value == CORRECT


def test_t6_accepts_product_action_during_migration() -> None:
    c = json.dumps({"action": _T6_ACTION, "protected_traffic": [], "rejected_traffic": [], "rationale": ""})
    assert decide("t6", c, STORM_REC, STORM_LIVE).value == CORRECT


def test_t10_accepts_recommendation_during_migration() -> None:
    c = json.dumps({"recommendation": "no flow control needed", "peak_rate": 0, "deficit": 0, "evidence": "idle"})
    assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == CORRECT
```

Implement small field lookups such as `fields.get("count", fields.get("request_count"))`, `fields.get("overload_action", fields.get("action"))`, and a t10 verdict helper that reads `verdict` or `recommendation`. Do not change scoring weights yet.

- [ ] **Step 4: Run scorer compatibility tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS. Existing binary behavior still works, and new artifact fields are accepted.

- [ ] **Step 5: Update `_PROMPTS` and `_SHAPES`**

In `src/signal_storm_bench/dataset.py`, rewrite each prompt to ask for the product artifact fields listed in Shared Conventions. Keep all leakage rules:

- Do not reveal metric names.
- Do not reveal the `t6` enum answer.
- Do not reveal expected `t9`/`t10` conclusions.
- Do not reveal live values or correct sizing outputs.

Use language such as:

```python
"Produce a storm-interval measurement extract from the live metrics. "
"Include the request count, unit, source signal description, and time window. "
'Submit your answer as JSON: {"request_count": <number>, "unit": "...", '
'"source_signal": "...", "window": "..."}'
```

- [ ] **Step 6: Run dataset and scorer tests**

Run: `uv run pytest tests/test_dataset.py tests/test_scorer_logic.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/signal_storm_bench/dataset.py src/signal_storm_bench/scorers.py tests/test_dataset.py tests/test_scorer_logic.py
git commit -m "feat: request product artifacts in signal storm prompts"
```

---

### Task 3: Convert t1-t4 To Product Scorers

**Files:**
- Modify: `tests/test_scorer_logic.py`
- Modify: `src/signal_storm_bench/scorers.py`
- Modify: `src/signal_storm_bench/sandbox_ops.py` if a dedicated success-count helper is cleaner

- [ ] **Step 1: Write reference, bad, and partial tests for t1-t4**

Replace the old `TestT1Count`, `TestT2PeakRate`, `TestT3Deficit`, and `TestT4Classify` binary assertions with product score assertions:

```python
def assert_score_between(score, low: float, high: float) -> None:
    assert low <= float(score.value) <= high, score.explanation


class TestT1Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps({
            "request_count": 10000,
            "unit": "registrations",
            "source_signal": "AMF initial-registration request counter",
            "window": "5m",
        })
        assert float(decide("t1", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_partial_numeric_scores_midrange(self) -> None:
        c = json.dumps({
            "request_count": 9000,
            "unit": "registrations",
            "source_signal": "AMF initial-registration request counter",
            "window": "5m",
        })
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.65, 0.95)

    def test_wrong_source_scores_low(self) -> None:
        c = json.dumps({"request_count": 10000, "unit": "packets", "source_signal": "CPU", "window": "now"})
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.0, 0.7)
```

Add equivalent high/mid/low tests for:

- `t2`: correct peak rate vs offered-rate constant should be distinguishable.
- `t3`: correct requests/successes/deficit vs arithmetic mismatch.
- `t4`: correct storm assessment with evidence vs verdict-only answer.

For each of `t1`, `t2`, `t3`, and `t4`, include at least three partial artifacts with distinct scores. Example partial dimensions: wrong number but right unit/source, right number but wrong unit/source, right evidence but incomplete arithmetic.

- [ ] **Step 2: Run scorer tests to verify failure**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: FAIL because `decide()` still expects old field names and returns binary values.

- [ ] **Step 3: Implement t1-t4 component scoring**

In `src/signal_storm_bench/scorers.py`, import `component_average`, `numeric_score`, and `term_coverage`.

Use these default weights:

- `t1`: `request_count` 0.75, unit 0.10, source signal 0.10, window 0.05.
- `t2`: `peak_rate` 0.75, unit 0.10, source signal 0.10, rate window 0.05.
- `t3`: request count 0.25, success count 0.25, deficit 0.35, unit 0.10, arithmetic consistency 0.05.
- `t4`: peak evidence 0.30, deficit evidence 0.25, verdict 0.30, explanation/evidence text 0.15.

Use error scales that create useful gradients:

- Counts/deficits: `max(reference * 0.10, 1.0)`.
- Peak rates/capacity rates: `max(reference * 0.25, 1.0)`.

For `t3`, derive `success_count` as `live.live_count - live.rejected_volume` unless a new live success probe is added.

Return:

```python
return Score(
    value=score,
    answer=json.dumps(fields, sort_keys=True),
    explanation=f"t1 product score={score:.3f}; components={components}",
    metadata={"components": components},
)
```

- [ ] **Step 4: Update live gathering for t3 and t4**

Ensure `_gather_live_state()` provides all live fields used by `t3` and `t4`:

- `t3`: `live_count` and `rejected_volume`
- `t4`: `live_peak_rate` and `rejected_volume`

Do not add extra probes to normative-only tasks `t5` and `t6`.

- [ ] **Step 5: Run focused scorer tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS for the whole file. Keep old t5-t10 tests passing until those tasks are converted in later commits.

- [ ] **Step 6: Commit**

```bash
git add src/signal_storm_bench/scorers.py src/signal_storm_bench/sandbox_ops.py tests/test_scorer_logic.py
git commit -m "feat: score storm measurement products"
```

---

### Task 4: Convert t5-t6 To Product Scorers

**Files:**
- Modify: `tests/test_scorer_logic.py`
- Modify: `src/signal_storm_bench/scorers.py`

- [ ] **Step 1: Write product scorer tests for t5**

Add tests where:

- Reference artifact includes both genuine mechanisms, excludes the distractor, and explains NGAP/NAS flow control; score `>= 0.95`.
- At least three partial artifacts score differently, such as one genuine mechanism only, correct mechanisms without exclusion, and correct selection with weak rationale.
- Unsafe artifact includes the distractor as selected mechanism; score below `0.75`.

Example:

```python
c = json.dumps({
    "mechanisms": ["NGAP Overload Start", "Traffic Load Reduction Indication"],
    "excluded": ["AMF load-balancing Weight Factor"],
    "rationale": "NGAP overload control can signal traffic load reduction; load-balancing weight is not a storm flow-control mechanism.",
})
assert float(decide("t5", c, STORM_REC, STORM_LIVE).value) >= 0.95
```

- [ ] **Step 2: Write product scorer tests for t6**

Add tests where:

- Reference artifact describes permitting emergency sessions and mobile-terminated services while rejecting other traffic; score `>= 0.95`.
- At least three partial artifacts score differently, such as correct protected class only, correct rejected class only, and correct action phrase with weak rationale.
- Exact old wrong answers such as `"reject"` score low but not necessarily zero if they include useful rationale.

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: FAIL for t5/t6 product tests.

- [ ] **Step 4: Implement t5 scoring**

Use weights:

- selected mechanisms F1: 0.55
- excluded distractor present in `excluded`: 0.15
- no unsafe selected distractor: 0.15
- rationale term coverage for `ngap`, `traffic load reduction`, and `flow control`: 0.15

Keep `_T5_EXPECTED` and the distractor constant scorer-side.

- [ ] **Step 5: Implement t6 scoring**

Use weights:

- action semantic coverage: 0.25
- protected traffic coverage: 0.25
- rejected traffic coverage: 0.25
- standards/rationale coverage: 0.25

Required protected terms: `emergency`, `mobile terminated`.

Rejected/non-protected terms can include `non emergency`, `mobile originated`, `other registrations`, or equivalent normalized phrases. Do not require exact enum string equality.

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS for t5/t6 product tests.

- [ ] **Step 7: Commit**

```bash
git add src/signal_storm_bench/scorers.py tests/test_scorer_logic.py
git commit -m "feat: score flow-control recommendation products"
```

---

### Task 5: Convert t7-t8 To Sizing Worksheet Scorers

**Files:**
- Modify: `tests/test_scorer_logic.py`
- Modify: `src/signal_storm_bench/scorers.py`
- Modify: `src/signal_storm_bench/logic.py` if sizing helpers should be shared

- [ ] **Step 1: Write t7 worksheet tests**

Add high, partial, and low examples:

- Reference: peak 100, capacity 40, TLR 60 or higher, post-control rate consistent; score `>= 0.95`.
- At least three partial artifacts score differently, such as near-miss TLR with correct measurements, safe TLR with wrong residual calculation, and correct formula with one wrong live measurement.
- Bad: TLR 10 with no formula; score below `0.5`.

- [ ] **Step 2: Write t8 worksheet tests**

Add high, partial, and low examples:

- Reference: deferred volume 6000, capacity 40, spread at least 150 seconds, expected retry rate <= 40; score `>= 0.95`.
- At least three partial artifacts score differently, such as correct volume/capacity with too narrow spread, safe spread with wrong expected retry rate, and correct min/max order with weak measurements.
- Bad: zero spread or reversed min/max; score below `0.4`.

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: FAIL for t7/t8 product tests.

- [ ] **Step 4: Implement t7 component scoring**

Use weights:

- peak measurement: 0.20
- capacity measurement: 0.20
- formula or residual consistency: 0.20
- TLR safety/closeness: 0.30
- range/unit sanity: 0.10

Recommended helper behavior:

```python
required_tlr = max(1.0, min(99.0, (1 - live.capacity_rate / live.live_peak_rate) * 100))
tlr_safety = 1.0 if tlr_holds(tlr, live.live_peak_rate, live.capacity_rate) else numeric_score(tlr, required_tlr, error_scale=required_tlr)
post_rate_score = numeric_score(post_control_rate, live.live_peak_rate * (1 - tlr / 100), error_scale=max(live.capacity_rate * 0.25, 1.0))
```

- [ ] **Step 5: Implement t8 component scoring**

Use weights:

- deferred volume measurement: 0.20
- capacity measurement: 0.20
- spread/order sanity: 0.15
- expected retry-rate consistency: 0.20
- backoff safety/closeness: 0.25

Score safety as full when `expected_retry_rate <= capacity_rate` and the submitted `backoff_max > backoff_min`. Give partial credit when the spread is close but insufficient.

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS for t7/t8 product tests.

- [ ] **Step 7: Commit**

```bash
git add src/signal_storm_bench/logic.py src/signal_storm_bench/scorers.py tests/test_scorer_logic.py
git commit -m "feat: score flow-control sizing worksheets"
```

---

### Task 6: Convert t9-t10 To Verification Memo Scorers

**Files:**
- Modify: `tests/test_scorer_logic.py`
- Modify: `src/signal_storm_bench/scorers.py`

- [ ] **Step 1: Write t9 verification memo tests**

Add tests where:

- Full artifact includes given TLR, peak, capacity, residual rate, and ineffective verdict; score `>= 0.95`.
- At least three partial artifacts score differently, such as verdict-only, correct measurements with wrong residual, and correct residual with wrong verdict.
- Verdict-only `"insufficient"` scores low, below `0.35`.
- Correct measurements with wrong verdict lands midrange, not zero.

- [ ] **Step 2: Write t10 baseline no-action tests**

Add tests where:

- Full artifact includes near-zero peak/deficit and recommends no flow control; score `>= 0.95`.
- At least three partial artifacts score differently, such as recommendation-only, correct peak with missing deficit, and correct evidence with unsafe recommendation.
- `"no"` or `"no flow control required"` without measurements scores low.
- Recommending control on idle baseline scores low even if measurements are present.

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: FAIL for t9/t10 product tests.

- [ ] **Step 4: Implement t9 scoring**

Use weights:

- given TLR value: 0.05
- peak/capacity measurements: 0.25
- residual-rate recomputation: 0.25
- verdict polarity: 0.30
- evidence text: 0.15

Correct verdict means the proposed TLR does not hold the live load. Do not score a verdict-only answer high.

- [ ] **Step 5: Implement t10 scoring**

Use weights:

- baseline peak measurement: 0.35
- deficit measurement: 0.20
- no-action recommendation: 0.30
- evidence text and no unsafe extra action: 0.15

Use `_IDLE_PEAK_THRESHOLD` as scorer-side reference. Keep prompt leakage tests passing.

- [ ] **Step 6: Gather baseline deficit for t10**

Update `_gather_live_state()` so the baseline world provides both `baseline_peak_rate` and `rejected_volume` for `t10`:

```python
return LiveState(
    baseline_peak_rate=await live_peak_rate(...),
    rejected_volume=await rejected_volume(baseline["storm_interval"]),
)
```

If `rejected_volume()` can return tiny negative jitter in an idle world, clamp only the baseline deficit component to zero in the scorer, not in the raw probe.

- [ ] **Step 7: Run tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS for all scorer product tests.

- [ ] **Step 8: Commit**

```bash
git add src/signal_storm_bench/scorers.py tests/test_scorer_logic.py
git commit -m "feat: score verification memo products"
```

---

### Task 7: Switch Metrics And Result Scripts To Numeric Scores

**Files:**
- Modify: `src/signal_storm_bench/scorers.py`
- Modify: `scripts/check_differentiation.py`
- Modify: `scripts/pass_hat_k.py`
- Modify: `scripts/export_gate_artifacts.py`
- Modify: `tests/test_differentiation.py`
- Modify: `tests/test_pass_hat_k.py`
- Create: `tests/test_export_gate_artifacts.py`

- [ ] **Step 1: Write tests for numeric metric collection**

In `tests/test_differentiation.py`, add a direct test for the helper if practical:

```python
def test_numeric_scores_still_differentiate():
    assert differentiated({"a": 0.92, "b": 0.71, "c": 0.52, "d": 0.31, "e": 0.12})
```

In `tests/test_pass_hat_k.py`, add a numeric threshold test:

```python
from pass_hat_k import is_pass_value


def test_is_pass_value_accepts_numeric_scores_above_threshold():
    assert is_pass_value(0.8)
    assert is_pass_value(0.95)
    assert not is_pass_value(0.79)
    assert not is_pass_value("I")
```

If `collect_counts()` is easy to unit-test with fake data, add a helper function that converts score values to pass/fail with threshold `0.8` and test it directly.

- [ ] **Step 2: Add cross-cutting numeric score tests**

In `tests/test_scorer_logic.py`, update the unparseable tests so every task returns numeric `0.0`, not `INCORRECT`:

```python
def test_garbage_scores_numeric_zero(self, kind: str, completion: str) -> None:
    rec = T9_REC if kind == "t9" else (BASELINE_REC if kind == "t10" else STORM_REC)
    live = IDLE_LIVE if kind == "t10" else STORM_LIVE
    score = decide(kind, completion, rec, live)
    assert score.value == 0.0
```

Add a guard that no normal product scorer returns `"C"` or `"I"`:

```python
def test_reference_products_return_float_scores() -> None:
    # Use one reference artifact per kind from the task-specific tests.
    # Assert isinstance(score.value, float) for all ten kinds.
```

Remove `CORRECT`/`INCORRECT` assertions from scorer tests once all tasks are converted.

- [ ] **Step 3: Update scorer unparseable path and metrics**

Change the unparseable return in `decide()`:

```python
return Score(value=0.0, answer=None, explanation="unparseable submission")
```

Remove unused `CORRECT`, `INCORRECT`, and `accuracy` imports from `src/signal_storm_bench/scorers.py` after all task branches return floats.

Then replace:

In `src/signal_storm_bench/scorers.py`, replace:

```python
from inspect_ai.scorer import accuracy, stderr

@scorer(metrics=[accuracy(), stderr()])
```

with:

```python
from inspect_ai.scorer import mean, stderr

@scorer(metrics=[mean(), stderr()])
```

- [ ] **Step 4: Update `check_differentiation.py`**

Modify metric collection to prefer `mean`, falling back to legacy `accuracy`:

```python
metric_value = next(
    (
        m.value
        for s in log.results.scores
        for name, m in s.metrics.items()
        if name in ("mean", "accuracy")
    ),
    None,
)
```

- [ ] **Step 5: Update `pass_hat_k.py` for numeric values**

Add:

```python
PASS_THRESHOLD = 0.8


def is_pass_value(value: object, threshold: float = PASS_THRESHOLD) -> bool:
    if value == "C":
        return True
    if isinstance(value, (int, float)):
        return float(value) >= threshold
    return False
```

Use `is_pass_value(value)` in `collect_counts()`.

- [ ] **Step 6: Update `export_gate_artifacts.py` for numeric values**

Add small helper functions in `scripts/export_gate_artifacts.py`:

```python
PRODUCT_PASS_THRESHOLD = 0.8


def metric_value(metrics: dict) -> float | None:
    for name in ("mean", "accuracy"):
        if name in metrics:
            return float(metrics[name].value)
    return None


def is_low_score(value: object, threshold: float = PRODUCT_PASS_THRESHOLD) -> bool:
    if value == "I":
        return True
    if value == "C":
        return False
    return float(value) < threshold
```

Update the summary table header from `accuracy` to `score`, preferring `mean` over legacy `accuracy`. Update transcript sampling so numeric values below `0.8` count as low-score examples, not only values different from `1.0`.

- [ ] **Step 7: Add export helper tests**

Create `tests/test_export_gate_artifacts.py` with direct helper tests:

```python
from export_gate_artifacts import is_low_score


def test_is_low_score_handles_numeric_product_scores():
    assert is_low_score(0.2)
    assert is_low_score(0.79)
    assert not is_low_score(0.8)
    assert not is_low_score(1.0)
```

- [ ] **Step 8: Run script tests**

Run: `uv run pytest tests/test_differentiation.py tests/test_pass_hat_k.py tests/test_export_gate_artifacts.py -q`

Expected: PASS.

- [ ] **Step 9: Run scorer numeric guard tests**

Run: `uv run pytest tests/test_scorer_logic.py -q`

Expected: PASS. All `Score.value` values in scorer unit tests are floats.

- [ ] **Step 10: Commit**

```bash
git add src/signal_storm_bench/scorers.py scripts/check_differentiation.py scripts/pass_hat_k.py scripts/export_gate_artifacts.py tests/test_differentiation.py tests/test_pass_hat_k.py tests/test_export_gate_artifacts.py tests/test_scorer_logic.py
git commit -m "feat: report numeric product scores"
```

---

### Task 8: Refresh Documentation And Checklist Status

**Files:**
- Modify: `src/signal_storm_bench/README.md`
- Modify: `HANDOVER.md`
- Modify: `docs/art-of-evals-checklist.md`
- Optionally modify: `docs/grounding/normative-sources.md`

- [ ] **Step 1: Update README scoring description**

Replace stale TODO wording in `src/signal_storm_bench/README.md` with:

- product artifact summary
- numeric product scoring summary
- note that pass^k treats scores `>= 0.8` as high-quality passes

- [ ] **Step 2: Update handover**

In `HANDOVER.md`, replace “binary-only grading” as the current state after implementation. Keep a short historical note that PR #2 originally shipped invalid binary scoring.

- [ ] **Step 3: Update art-of-evals checklist**

Mark items that are satisfied by implementation as WIP or MET only if the code and tests prove them. Do not mark calibration/differentiation MET until a fresh roster run exists.

- [ ] **Step 4: Run docs-related tests**

Run: `uv run pytest tests/test_generate_readmes.py tests/test_dataset.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/signal_storm_bench/README.md HANDOVER.md docs/art-of-evals-checklist.md docs/grounding/normative-sources.md
git commit -m "docs: document product-based signal storm scoring"
```

---

### Task 9: Full Local Verification

**Files:**
- No planned source changes unless verification finds a defect.

- [ ] **Step 1: Run focused unit tests**

Run:

```bash
uv run pytest tests/test_logic.py tests/test_dataset.py tests/test_scorer_logic.py tests/test_differentiation.py tests/test_pass_hat_k.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full unit suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run ruff**

Run:

```bash
uv run ruff check .
```

Expected: PASS.

- [ ] **Step 4: Verify every scorer has non-binary examples**

Run a small ad hoc check or inspect `tests/test_scorer_logic.py` manually:

- Each surviving `tN` has reference, bad, and at least three partial tests.
- Each surviving `tN` has at least three distinct score values across tests.
- No task test matrix is only `{0.0, 1.0}`.

- [ ] **Step 5: Commit any verification fixes**

Only if Step 1-4 required changes:

```bash
git add <changed-files>
git commit -m "fix: stabilize product scoring verification"
```

---

### Task 10: Live Smoke And Calibration Prep

**Files:**
- Modify only if live smoke reveals an implementation defect.

- [ ] **Step 1: Run one cheap live smoke slice**

Use the user’s configured model; do not hardcode a paid model unless requested:

```bash
uv run inspect eval signal_storm_bench/signal_storm \
  --limit 1 \
  --message-limit 50 \
  --max-sandboxes 1 \
  --log-dir logs/product-smoke \
  --fail-on-error 0.25
```

Expected: `status: success`, no infra errors, numeric score present.

- [ ] **Step 2: Run one targeted hard-task smoke if budget allows**

Pick a task that previously failed hard, e.g. `t6`:

```bash
uv run inspect eval signal_storm_bench/signal_storm \
  -T kinds=t6 \
  --limit 1 \
  --message-limit 50 \
  --max-sandboxes 1 \
  --log-dir logs/product-smoke-t6 \
  --fail-on-error 0.25
```

Expected: `status: success`; score may be low, but scorer explanation should show product components rather than binary rejection.

- [ ] **Step 3: Run differentiation scripts on smoke logs**

Run:

```bash
uv run python scripts/check_differentiation.py logs/product-smoke
uv run python scripts/pass_hat_k.py logs/product-smoke
```

Expected: scripts do not crash on numeric scores. Differentiation may fail with one model; that is acceptable for smoke.

- [ ] **Step 4: Prepare full calibration command but do not run without budget confirmation**

Command for later:

```bash
MAX_SANDBOXES=1 bash scripts/run_iteration.sh product-p1 3
uv run python scripts/check_differentiation.py logs/product-p1
uv run python scripts/pass_hat_k.py logs/product-p1
```

Expected after a real calibration run: per-task distributions are inspectable and no task is obviously saturated/floored across the roster.

- [ ] **Step 5: Commit live-smoke fixes only if needed**

```bash
git add <changed-files>
git commit -m "fix: product scorer live smoke issues"
```

---

## Final Acceptance Criteria

- `uv run pytest -q` passes.
- `uv run ruff check .` passes.
- Every surviving task returns numeric product scores in `[0, 1]`.
- Every surviving task has reference, bad, and at least three partial artifact tests.
- Every surviving task has at least three distinct non-binary score values in unit tests.
- No surviving task is binary-only in unit tests.
- Scorer metadata includes component scores for debugging.
- Prompt leakage tests still pass.
- Result scripts and gate artifact export handle numeric scores.
- At least one live smoke run succeeds without infra errors.
- Full roster calibration is ready, with explicit budget/runtime confirmation before execution.
