"""Outcome-led scorers, faithful to the submission grader contracts (P4).

Each task kind has its own small grader (grade_t1 .. grade_t10); they are pure,
consuming the parsed submission plus a LiveState snapshot, so every grading rule
unit-tests without docker. decide() parses the submission once and dispatches to
the kind's grader through the GRADERS table. signal_storm_scorer() gathers the
LiveState by probing only what the kind needs, reads ground truth off
Sample.metadata and config.py, then calls decide. Infrastructure faults raise
RuntimeError (the sample errors, never a binary incorrect label, per the guide).

Grading is outcome-only: the agent's JSON answer is checked against live core
state (Prometheus counters off the running AMF) and the normative NGAP/NAS bounds
in config.py; never the path the agent took. Unparseable submissions score 0 and
never raise. Verdict matching is judgment-bearing only, so a content-free answer
cannot win by accidentally echoing the live state.
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
    component_average,
    contains_normalized_phrase,
    matches_any_phrase,
    measure,
    normalize_verdict,
    numeric_score,
    parse_submission,
    rel_scale,
    residual_rate,
    set_f1_score,
    term_coverage,
    tlr_holds,
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


def _unit_score(value: object, expected_unit: str) -> float:
    return term_coverage(value, {expected_unit})


def _window_score(value: object, expected_window: str) -> float:
    normalized = normalize_verdict(str(value))
    if contains_normalized_phrase(normalized, expected_window):
        return 1.0
    if contains_normalized_phrase(normalized, "storm interval"):
        return 1.0
    return 0.0


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

    cap, when given, is the most the score can be (a safety penalty: t10 caps an
    unsafe recommendation). extra_metadata is merged into the Score metadata.
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


def _required_tlr(live_peak_rate: float, capacity: float) -> float:
    """The smallest TLR percent that would hold the live peak to capacity."""
    if live_peak_rate <= 0:
        return float(config.TLR_MAX)
    needed = (1 - capacity / live_peak_rate) * 100
    return max(float(config.TLR_MIN), min(float(config.TLR_MAX), needed))


def _tlr_safety_score(
    tlr: float | None, live_peak_rate: float, capacity: float
) -> float:
    """Full credit when the TLR holds the load; partial credit as it nears it."""
    if tlr is None or not config.TLR_MIN <= tlr <= config.TLR_MAX:
        return 0.0
    if tlr_holds(tlr, live_peak_rate, capacity):
        return 1.0
    required = _required_tlr(live_peak_rate, capacity)
    return numeric_score(tlr, required, max(required, 1.0))


def _unsafe_control_recommendation(text: object) -> bool:
    """True when an idle-baseline answer wrongly recommends applying flow control."""
    normalized = normalize_verdict(str(text))
    if not normalized:
        return False
    if matches_any_phrase(normalized, config.T10_NO_CONTROL):
        return False
    unsafe_terms = {
        "apply",
        "traffic load reduction",
        "flow control needed",
        "control needed",
        "flow control required",
        "control required",
    }
    return any(contains_normalized_phrase(normalized, term) for term in unsafe_terms)


# --- per-task graders ------------------------------------------------------
#
# Each grader is pure: (parsed submission, sample metadata, live snapshot) -> a
# Score. measure(submitted, live_value[, tolerance]) is full credit at the live
# value, fading out over the tolerance fraction of it.


def grade_t1(fields: dict, record: dict, live: LiveState) -> Score:
    """Storm-interval registration-request count extract."""
    count = fields.get("count", fields.get("request_count"))
    storm = record["storm"]
    components = {
        "request_count": measure(count, live.live_count, 0.10),
        "unit": _unit_score(fields.get("unit"), "registrations"),
        "source_signal": term_coverage(
            fields.get("source_signal"), {"amf", "initial registration", "request"}
        ),
        "window": _window_score(fields.get("window"), storm["storm_interval"]),
    }
    weights = {
        "request_count": 0.75,
        "unit": 0.10,
        "source_signal": 0.10,
        "window": 0.05,
    }
    return _product_score("t1", fields, components, weights)


def grade_t2(fields: dict, record: dict, live: LiveState) -> Score:
    """Peak initial-registration rate extract."""
    components = {
        "peak_rate": measure(fields.get("peak_rate"), live.live_peak_rate),
        "unit": _unit_score(fields.get("unit"), "registrations per second"),
        "source_signal": term_coverage(
            fields.get("source_signal"),
            {"amf", "initial registration", "request", "rate"},
        ),
        "rate_window": _window_score(fields.get("rate_window"), config.PEAK_WINDOW),
    }
    weights = {
        "peak_rate": 0.75,
        "unit": 0.10,
        "source_signal": 0.10,
        "rate_window": 0.05,
    }
    return _product_score("t2", fields, components, weights)


def grade_t3(fields: dict, record: dict, live: LiveState) -> Score:
    """Registration deficit note: requests, successes, and their difference."""
    request_count = fields.get("request_count", fields.get("count"))
    success_count = fields.get("success_count")
    deficit = fields.get("deficit")
    live_success = live.live_count - live.rejected_volume

    both_numeric = isinstance(request_count, (int, float)) and isinstance(
        success_count, (int, float)
    )
    arithmetic_consistency = 0.0
    if both_numeric:
        expected_deficit = float(request_count) - float(success_count)
        arithmetic_consistency = measure(deficit, expected_deficit, 0.10)

    components = {
        "request_count": measure(request_count, live.live_count, 0.10),
        "success_count": measure(success_count, live_success, 0.10),
        "deficit": measure(deficit, live.rejected_volume, 0.10),
        "unit": _unit_score(fields.get("unit"), "registrations"),
        "arithmetic_consistency": arithmetic_consistency,
    }
    weights = {
        "request_count": 0.25,
        "success_count": 0.25,
        "deficit": 0.35,
        "unit": 0.10,
        "arithmetic_consistency": 0.05,
    }
    return _product_score("t3", fields, components, weights)


def grade_t4(fields: dict, record: dict, live: LiveState) -> Score:
    """Load-state assessment memo: a verdict backed by peak and deficit."""
    is_storm = live.live_peak_rate > config.IDLE_PEAK_THRESHOLD
    verdict_terms = (
        {"storm", "signalling storm", "overload", "overloaded"}
        if is_storm
        else {"normal", "idle", "baseline"}
    )
    components = {
        "peak_evidence": measure(fields.get("peak_rate"), live.live_peak_rate),
        "deficit_evidence": measure(fields.get("deficit"), live.rejected_volume, 0.10),
        "verdict": 1.0
        if matches_any_phrase(fields.get("verdict"), verdict_terms)
        else 0.0,
        "evidence_text": term_coverage(
            fields.get("evidence"), {"live", "peak rate", "deficit", "overload"}
        ),
    }
    weights = {
        "peak_evidence": 0.30,
        "deficit_evidence": 0.25,
        "verdict": 0.30,
        "evidence_text": 0.15,
    }
    return _product_score("t4", fields, components, weights)


def grade_t5(fields: dict, record: dict, live: LiveState) -> Score:
    """Flow-control mechanism recommendation: pick the two, exclude the distractor."""
    mechanisms = _as_list(fields.get("mechanisms"))
    excluded = _as_list(fields.get("excluded"))
    selected_distractor = term_coverage(_joined(mechanisms), {config.T5_DISTRACTOR})
    components = {
        "selected_mechanisms": set_f1_score(mechanisms, config.T5_EXPECTED),
        "excluded_distractor": term_coverage(excluded, {config.T5_DISTRACTOR}),
        "no_unsafe_selected_distractor": 0.0 if selected_distractor == 1.0 else 1.0,
        "rationale": term_coverage(
            fields.get("rationale"), {"ngap", "traffic load reduction", "flow control"}
        ),
    }
    weights = {
        "selected_mechanisms": 0.55,
        "excluded_distractor": 0.15,
        "no_unsafe_selected_distractor": 0.15,
        "rationale": 0.15,
    }
    return _product_score("t5", fields, components, weights)


def grade_t6(fields: dict, record: dict, live: LiveState) -> Score:
    """NGAP overload-action policy: protect emergency, reject the rest."""
    action = fields.get("overload_action", fields.get("action"))
    rejected_text = _joined(fields.get("rejected_traffic"))
    components = {
        "action": term_coverage(
            action, {"permit", "emergency", "mobile terminated", "only"}
        ),
        "protected_traffic": term_coverage(
            fields.get("protected_traffic"), {"emergency", "mobile terminated"}
        ),
        "rejected_traffic": max(
            term_coverage(rejected_text, {"non emergency", "mobile originated"}),
            term_coverage(rejected_text, {"other registrations"}),
            term_coverage(rejected_text, {"all other"}),
        ),
        "rationale": term_coverage(
            fields.get("rationale"),
            {"ngap", "overload", "emergency", "mobile terminated"},
        ),
    }
    weights = {
        "action": 0.25,
        "protected_traffic": 0.25,
        "rejected_traffic": 0.25,
        "rationale": 0.25,
    }
    return _product_score("t6", fields, components, weights)


def grade_t7(fields: dict, record: dict, live: LiveState) -> Score:
    """Traffic Load Reduction sizing worksheet that holds the peak to capacity."""
    tlr = as_float(fields.get("tlr_percent"))
    post_expected = residual_rate(live.live_peak_rate, tlr) if tlr is not None else 0.0
    post_rate_score = numeric_score(
        fields.get("post_control_rate"),
        post_expected,
        rel_scale(live.capacity_rate, 0.25),
    )
    formula_terms = term_coverage(
        fields.get("formula"), {"post control rate", "peak rate", "tlr percent"}
    )
    in_range = tlr is not None and config.TLR_MIN <= tlr <= config.TLR_MAX
    components = {
        "peak_measurement": measure(fields.get("peak_rate"), live.live_peak_rate),
        "capacity_measurement": measure(
            fields.get("capacity_rate"), live.capacity_rate
        ),
        "formula_consistency": (formula_terms + post_rate_score) / 2,
        "tlr_safety": _tlr_safety_score(tlr, live.live_peak_rate, live.capacity_rate),
        "range_sanity": 1.0 if in_range else 0.0,
    }
    weights = {
        "peak_measurement": 0.20,
        "capacity_measurement": 0.20,
        "formula_consistency": 0.20,
        "tlr_safety": 0.30,
        "range_sanity": 0.10,
    }
    return _product_score("t7", fields, components, weights)


def grade_t8(fields: dict, record: dict, live: LiveState) -> Score:
    """NAS back-off dispersion worksheet that spreads retries within capacity."""
    deferred_volume = fields.get("deferred_volume", fields.get("deficit"))
    capacity = fields.get("capacity_rate")
    bmin = as_float(fields.get("backoff_min"))
    bmax = as_float(fields.get("backoff_max"))
    expected_retry_rate = fields.get("expected_retry_rate")

    spread = bmax - bmin if bmin is not None and bmax is not None else 0.0
    submitted_deferred = as_float(deferred_volume)
    submitted_capacity = as_float(capacity)
    submitted_retry_rate = (
        submitted_deferred / spread
        if submitted_deferred is not None and spread > 0
        else None
    )
    required_spread = (
        live.rejected_volume / live.capacity_rate if live.capacity_rate > 0 else 0.0
    )

    expected_retry_score = (
        numeric_score(
            expected_retry_rate,
            submitted_retry_rate,
            rel_scale(submitted_capacity or live.capacity_rate, 0.25),
        )
        if submitted_retry_rate is not None
        else 0.0
    )

    expected_value = as_float(expected_retry_rate)
    backoff_safety = _backoff_safety(
        spread, submitted_capacity, expected_value, required_spread
    )

    components = {
        "deferred_volume": measure(deferred_volume, live.rejected_volume, 0.10),
        "capacity_measurement": measure(capacity, live.capacity_rate),
        "spread_order_sanity": 1.0 if spread > 0 else 0.0,
        "expected_retry_rate": expected_retry_score,
        "backoff_safety": backoff_safety,
    }
    weights = {
        "deferred_volume": 0.20,
        "capacity_measurement": 0.20,
        "spread_order_sanity": 0.15,
        "expected_retry_rate": 0.20,
        "backoff_safety": 0.25,
    }
    return _product_score("t8", fields, components, weights)


def _backoff_safety(
    spread: float,
    submitted_capacity: float | None,
    expected_value: float | None,
    required_spread: float,
) -> float:
    """Credit a back-off range that disperses retries within the AMF's capacity."""
    if spread <= 0:
        return 0.0
    if (
        submitted_capacity is not None
        and expected_value is not None
        and expected_value <= submitted_capacity
    ):
        return 1.0
    return numeric_score(spread, required_spread, max(required_spread, 1.0))


def grade_t9(fields: dict, record: dict, live: LiveState) -> Score:
    """Verification memo: the planted undersized TLR fails to hold the load."""
    given_tlr = record["given_tlr"]
    expected_residual = residual_rate(live.live_peak_rate, given_tlr)
    peak_score = measure(fields.get("peak_rate"), live.live_peak_rate)
    capacity_score = measure(fields.get("capacity_rate"), live.capacity_rate)
    components = {
        "given_tlr": numeric_score(
            fields.get("given_tlr_percent", fields.get("tlr_percent")),
            given_tlr,
            error_scale=1.0,
        ),
        "peak_capacity_measurements": (peak_score + capacity_score) / 2,
        "residual_rate": numeric_score(
            fields.get("residual_rate"),
            expected_residual,
            rel_scale(live.capacity_rate, 0.25),
        ),
        "verdict": 1.0
        if matches_any_phrase(fields.get("verdict"), config.T9_FAILS)
        else 0.0,
        "evidence": term_coverage(
            fields.get("evidence"), {"tlr", "residual", "capacity"}
        ),
    }
    weights = {
        "given_tlr": 0.05,
        "peak_capacity_measurements": 0.25,
        "residual_rate": 0.25,
        "verdict": 0.30,
        "evidence": 0.15,
    }
    return _product_score("t9", fields, components, weights)


def grade_t10(fields: dict, record: dict, live: LiveState) -> Score:
    """Baseline no-action assessment: the idle core needs no flow control."""
    recommendation = fields.get("recommendation", fields.get("verdict"))
    unsafe = _unsafe_control_recommendation(recommendation)
    baseline_deficit = max(live.rejected_volume, 0.0)
    components = {
        "baseline_peak": numeric_score(
            fields.get("peak_rate"),
            live.baseline_peak_rate,
            error_scale=max(config.IDLE_PEAK_THRESHOLD, 1.0),
        ),
        "deficit": measure(fields.get("deficit"), baseline_deficit, 0.10),
        "no_action_recommendation": 1.0
        if matches_any_phrase(recommendation, config.T10_NO_CONTROL)
        else 0.0,
        "evidence": 0.0
        if unsafe
        else term_coverage(fields.get("evidence"), {"idle", "below", "deficit"}),
    }
    weights = {
        "baseline_peak": 0.35,
        "deficit": 0.20,
        "no_action_recommendation": 0.30,
        "evidence": 0.15,
    }
    return _product_score(
        "t10",
        fields,
        components,
        weights,
        cap=0.25 if unsafe else None,
        extra_metadata={"unsafe_recommendation": unsafe},
    )


GRADERS = {
    "t1": grade_t1,
    "t2": grade_t2,
    "t3": grade_t3,
    "t4": grade_t4,
    "t5": grade_t5,
    "t6": grade_t6,
    "t7": grade_t7,
    "t8": grade_t8,
    "t9": grade_t9,
    "t10": grade_t10,
}


def decide(kind: str, completion: str, record: dict, live: LiveState) -> Score:
    """Parse the submission once, then grade it with the kind's grader.

    record is the sample metadata (storm knobs, t9 given_tlr, etc.). Unparseable
    submissions score 0 and never raise.
    """
    fields = parse_submission(completion)
    if fields is None:
        return Score(value=0.0, answer=None, explanation="unparseable submission")
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
