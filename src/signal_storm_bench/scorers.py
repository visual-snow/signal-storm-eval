"""Outcome-led scorers, faithful to the submission grader contracts.

Each investigation kind has its own small grader (grade_i1, grade_i2, grade_i3,
grade_i4); they are pure, consuming the parsed submission plus a LiveState
snapshot, so every grading rule unit-tests without docker. decide() parses the
submission once and dispatches to the kind's grader through the GRADERS table.
signal_storm_scorer() gathers the LiveState by probing only what the kind needs,
reads ground truth off Sample.metadata and config.py, then calls decide.
Infrastructure faults raise RuntimeError (the sample errors, never a binary
incorrect label, per the guide).

Grading is outcome-only: the agent's JSON answer is checked against live core
state (Prometheus counters off the running AMF) and the normative NGAP/NAS bounds
in config.py; never the path the agent took. Unparseable submissions score 0 and
never raise. i2 verdict matching is judgment-bearing (precomputed by async judge);
the rest are pure numeric.
"""

import asyncio
import json
from dataclasses import dataclass

from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState

from signal_storm_bench import config
from signal_storm_bench.logic import (
    as_float,
    clamp01,
    component_average,
    controlled_set_score,
    measure,
    numeric_score,
    parse_submission,
    rel_scale,
    set_f1_score,
    term_coverage,
)
from signal_storm_bench.sandbox_ops import (
    capacity_rate,
    live_count,
    live_peak_rate,
    rejected_volume,
)


@dataclass(frozen=True)
class LiveState:
    """Snapshot of the live core state the per-kind graders consume.

    Probed off Prometheus at grade time; only the fields a kind needs are read,
    the rest keep safe zero defaults.
    """

    live_count: float = 0.0
    live_peak_rate: float = 0.0
    capacity_rate: float = 0.0
    rejected_volume: float = 0.0
    baseline_peak_rate: float = 0.0


# --- small grading helpers -------------------------------------------------


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _joined(value: object) -> str:
    return " ".join(str(item) for item in _as_list(value))


def _product_score(
    kind: str,
    fields: dict,
    components: dict[str, float],
    weights: dict[str, float],
    cap: float | None = None,
    extra_metadata: dict | None = None,
) -> Score:
    """Combine weighted components into one 0..1 product Score.

    cap, when given, is the most the score can be (a safety penalty).
    extra_metadata is merged into the Score metadata.
    """
    score = component_average(components, weights)
    if cap is not None:
        score = min(score, cap)
    metadata = {"components": components}
    if extra_metadata:
        metadata.update(extra_metadata)
    return Score(
        value=score,
        answer=json.dumps(fields, sort_keys=True),
        explanation=f"{kind} product score={score:.3f}; components={components}",
        metadata=metadata,
    )


# --- per-task graders ------------------------------------------------------
#
# Each grader is pure: (parsed submission, sample metadata, live snapshot) -> a
# Score. measure(submitted, live_value[, tolerance]) is full credit at the live
# value, fading out over the tolerance fraction of it.


def grade_i1(fields: dict, record: dict, live: LiveState) -> Score:
    """Storm measurement extract: request count, peak rate, successes, deficit."""
    success_ref = live.live_count - live.rejected_volume
    components = {
        "request_count": measure(fields.get("request_count"), live.live_count, 0.10),
        "peak_rate": measure(fields.get("peak_rate"), live.live_peak_rate),
        "success_count": measure(fields.get("success_count"), success_ref, 0.10),
        "deficit": measure(fields.get("deficit"), live.rejected_volume, 0.10),
    }
    weights = {
        "request_count": 0.25,
        "peak_rate": 0.30,
        "success_count": 0.20,
        "deficit": 0.25,
    }
    return _product_score("i1", fields, components, weights)


def grade_i2(
    fields: dict, record: dict, live: LiveState, verdict_score: float = 0.0
) -> Score:
    """Load-state diagnosis: measured evidence (deterministic) + judge verdict.

    verdict_score is precomputed by the async judge in the scorer (1.0 if the
    agent's load_state agrees with the live-forced state, 0.0 otherwise/Unknown).
    The measurement components are graded against the live snapshot of the world
    this sample ran in (storm or baseline).
    """
    components = {
        "peak_rate": measure(fields.get("peak_rate"), live.live_peak_rate),
        "deficit": measure(fields.get("deficit"), live.rejected_volume, 0.10),
        "verdict": clamp01(verdict_score),
    }
    weights = {"peak_rate": 0.30, "deficit": 0.30, "verdict": 0.40}
    return _product_score("i2", fields, components, weights)


def grade_i3(fields: dict, record: dict, live: LiveState) -> Score:
    """Flow-control selection: mechanisms (vs distractors) + traffic classes."""
    mechanisms = _as_list(fields.get("mechanisms"))
    components = {
        "selected_mechanisms": set_f1_score(mechanisms, config.I3_CORRECT),
        "no_distractor_selected": 1.0
        - term_coverage(_joined(mechanisms), set(config.I3_DISTRACTORS)),
        "protected_traffic": controlled_set_score(
            _as_list(fields.get("protected_traffic")), config.I3_PROTECTED
        ),
        "rejected_traffic": controlled_set_score(
            _as_list(fields.get("rejected_traffic")),
            config.I3_REJECTED,
            unsafe=config.I3_PROTECTED,
        ),
    }
    weights = {
        "selected_mechanisms": 0.40,
        "no_distractor_selected": 0.20,
        "protected_traffic": 0.20,
        "rejected_traffic": 0.20,
    }
    return _product_score("i3", fields, components, weights)


def grade_i4(fields: dict, record: dict, live: LiveState) -> Score:
    """NAS back-off dispersion sized against the live backlog and capacity.

    Scored against live-derived ground truth, not the agent's own submission:
    the resulting retry rate is the live backlog over the submitted spread, and
    safety is that rate staying within the live capacity.
    """
    bmin = as_float(fields.get("backoff_min"))
    bmax = as_float(fields.get("backoff_max"))
    spread = bmax - bmin if bmin is not None and bmax is not None else 0.0
    resulting_rate = live.rejected_volume / spread if spread > 0 else None
    expected = as_float(fields.get("expected_retry_rate"))

    retry_consistency = (
        numeric_score(expected, resulting_rate, rel_scale(live.capacity_rate, 0.25))
        if resulting_rate is not None and expected is not None
        else 0.0
    )
    if resulting_rate is None:
        backoff_safety = 0.0
    elif resulting_rate <= live.capacity_rate:
        backoff_safety = 1.0
    else:
        backoff_safety = numeric_score(
            resulting_rate, live.capacity_rate, rel_scale(live.capacity_rate, 1.0)
        )
    components = {
        "deferred_volume": measure(
            fields.get("deferred_volume"), live.rejected_volume, 0.10
        ),
        "capacity_measurement": measure(
            fields.get("capacity_rate"), live.capacity_rate
        ),
        "spread_present": 1.0 if spread > 0 else 0.0,
        "retry_rate_consistency": retry_consistency,
        "backoff_safety": backoff_safety,
    }
    weights = {
        "deferred_volume": 0.15,
        "capacity_measurement": 0.20,
        "spread_present": 0.10,
        "retry_rate_consistency": 0.20,
        "backoff_safety": 0.35,
    }
    return _product_score("i4", fields, components, weights)


GRADERS = {"i1": grade_i1, "i3": grade_i3, "i4": grade_i4}


def decide(
    kind: str,
    completion: str,
    record: dict,
    live: LiveState,
    verdict_score: float | None = None,
) -> Score:
    """Parse the submission once, then grade it with the kind's grader.

    i2 takes a precomputed verdict_score from the async judge; the rest are pure.
    Unparseable submissions score 0 and never raise.
    """
    fields = parse_submission(completion)
    if fields is None:
        return Score(value=0.0, answer=None, explanation="unparseable submission")
    if kind == "i2":
        return grade_i2(fields, record, live, verdict_score or 0.0)
    grader = GRADERS.get(kind)
    if grader is None:
        raise ValueError(f"unknown task kind: {kind}")
    return grader(fields, record, live)


async def _gather_live_state(kind: str, record: dict) -> LiveState:
    """Probe only what the kind's grading rule needs; default the rest to zero.

    Independent probes for a kind are gathered concurrently: they are pure reads
    of the same Prometheus snapshot, so order cannot change the result.
    """
    if kind == "t10":
        # Baseline world: the idle peak rate (and any residual deficit) are the
        # only ground truth needed. Same windows as the storm so the read repeats.
        baseline = record["baseline"]
        peak, deficit = await asyncio.gather(
            live_peak_rate(
                baseline["storm_interval"],
                baseline["peak_window"],
                baseline["scrape_interval_s"],
            ),
            rejected_volume(baseline["storm_interval"]),
        )
        return LiveState(baseline_peak_rate=peak, rejected_volume=deficit)

    storm = record["storm"]
    window = storm["storm_interval"]
    peak_window = storm["peak_window"]
    step = storm["scrape_interval_s"]

    if kind == "t1":
        return LiveState(live_count=await live_count(window))
    if kind == "t2":
        return LiveState(live_peak_rate=await live_peak_rate(window, peak_window, step))
    if kind == "t3":
        count, deficit = await asyncio.gather(
            live_count(window), rejected_volume(window)
        )
        return LiveState(live_count=count, rejected_volume=deficit)
    if kind == "t4":
        peak, deficit = await asyncio.gather(
            live_peak_rate(window, peak_window, step), rejected_volume(window)
        )
        return LiveState(live_peak_rate=peak, rejected_volume=deficit)
    if kind in ("t7", "t9"):
        peak, cap = await asyncio.gather(
            live_peak_rate(window, peak_window, step),
            capacity_rate(window, peak_window, step),
        )
        return LiveState(live_peak_rate=peak, capacity_rate=cap)
    if kind == "t8":
        deficit, cap = await asyncio.gather(
            rejected_volume(window), capacity_rate(window, peak_window, step)
        )
        return LiveState(rejected_volume=deficit, capacity_rate=cap)
    # t5, t6: normative-only graders need no live probe.
    return LiveState()


@scorer(metrics=[mean(), stderr()])
def signal_storm_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        kind = state.metadata["task_kind"]
        live = await _gather_live_state(kind, state.metadata)
        return decide(kind, state.output.completion, state.metadata, live)

    return score
