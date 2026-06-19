"""Outcome-led scorers, faithful to the submission grader contracts (P4).

decide() is pure: it consumes the parsed submission plus a LiveState snapshot,
so every grading rule unit-tests without docker. signal_storm_scorer() gathers
the LiveState by calling sandbox_ops probes for only what the kind needs, reads
ground truth off Sample.metadata, then calls decide. Infrastructure faults raise
RuntimeError (the sample errors, never INCORRECT, per the guide).

Grading is outcome-only: the agent's JSON answer is checked against live core
state (Prometheus counters off the running AMF) and the normative NGAP/NAS
bounds; never the path the agent took. Unparseable submissions score 0 and never
raise. Verdict helpers are tristate (None never scores correct).
"""

import json
from dataclasses import dataclass

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState

from signal_storm_bench.logic import (
    as_float,
    component_average,
    normalize_verdict,
    numeric_score,
    parse_submission,
    set_f1_score,
    term_coverage,
    verdict_in,
)
from signal_storm_bench.sandbox_ops import (
    capacity_rate,
    live_count,
    live_peak_rate,
    rejected_volume,
)

# Scorer-side ground truth (kept out of prompts per the leakage rules; sourced
# from docs/grounding/normative-sources.md).

# t5: the genuine NGAP/NAS flow-control mechanisms; the candidate
# "AMF load-balancing Weight Factor" is the distractor and must be excluded.
# Wording matches the published candidate text so a verbatim copy normalizes equal.
_T5_EXPECTED = ("NGAP Overload Start", "Traffic Load Reduction Indication")
_T5_DISTRACTOR = "AMF load-balancing Weight Factor"

# t6: TS 38.413 sec 9.3.1.105 Overload Action enumeration value.
_T6_ACTION = "Permit Emergency Sessions and mobile terminated services only"

# t9/t10 verdict synonym sets (normalised by lowercasing + stripping punctuation;
# verdict_in does substring containment). Both tasks have a constant live half
# (the storm is always overloaded, the baseline always idle), so the verdict match
# is the sole discriminator: it must accept how models actually phrase the right
# call yet still reject the opposite polarity. Hence only judgment-bearing phrases
# ("insufficient", "not needed"), never bare state words ("overloaded", "no flow
# control") that occur in both a correct and an incorrect answer.
_T9_FAILS = {
    "ineffective", "not effective",
    "insufficient", "not sufficient",
    "inadequate", "not adequate",
    "not enough",
    "too low",
    "does not hold", "doesn t hold", "will not hold", "won t hold",
    "cannot hold", "can t hold", "fails to hold",
    "not capped", "does not cap", "will not cap", "won t cap",
    "ceiling exceeded", "still overloaded", "remains overloaded",
}
_T10_NO_CONTROL = {
    "no control needed", "no flow control needed", "no flow control is needed",
    "no control required", "no flow control required", "no flow control is required",
    "flow control is not needed", "flow control not needed",
    "flow control is not required", "flow control not required",
    "control is not needed", "control not needed",
    "not needed", "not required", "not necessary",
    "none needed", "none required",
    "no action needed", "no action required",
    "unnecessary", "unwarranted",
    "below ceiling", "below threshold", "below the idle",
}

# Live peak below this (reg/s) is idle/normal load; above it is a storm. Used by
# t4 (storm world must read above it) and t10 (baseline must read below it).
_IDLE_PEAK_THRESHOLD = 1.0


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


def _text_matches_any(text: object, synonyms: set[str]) -> bool | None:
    normalized = normalize_verdict(str(text))
    if not normalized:
        return None
    for synonym in synonyms:
        if normalize_verdict(synonym) in normalized:
            return True
    return None


def _unit_score(value: object, expected_unit: str) -> float:
    return term_coverage(value, {expected_unit})


def _window_score(value: object, expected_window: str) -> float:
    normalized = normalize_verdict(str(value))
    if normalize_verdict(expected_window) in normalized:
        return 1.0
    if "storm interval" in normalized:
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
    kind: str, fields: dict, components: dict[str, float], weights: dict[str, float]
) -> Score:
    score = component_average(components, weights)
    return Score(
        value=score,
        answer=json.dumps(fields, sort_keys=True),
        explanation=f"{kind} product score={score:.3f}; components={components}",
        metadata={"components": components},
    )


def _required_tlr(live_peak_rate: float, capacity: float) -> float:
    if live_peak_rate <= 0:
        return 99.0
    return max(1.0, min(99.0, (1 - capacity / live_peak_rate) * 100))


def _tlr_safety_score(tlr: float | None, live_peak_rate: float, capacity: float) -> float:
    if tlr is None or not 1 <= tlr <= 99:
        return 0.0
    required = _required_tlr(live_peak_rate, capacity)
    if live_peak_rate * (1 - tlr / 100) <= capacity:
        return 1.0
    return numeric_score(tlr, required, error_scale=max(required, 1.0))


def decide(kind: str, completion: str, record: dict, live: LiveState) -> Score:
    """Pure grader: parse the submission, then grade the kind per the spec table.

    record is the sample metadata (storm knobs, t9 given_tlr, etc.). Unparseable
    submissions score 0 and never raise.
    """
    fields = parse_submission(completion)
    if fields is None:
        return Score(value=INCORRECT, answer=None, explanation="unparseable submission")

    if kind == "t1":
        count = fields.get("count", fields.get("request_count"))
        storm = record["storm"]
        components = {
            "request_count": numeric_score(
                count, live.live_count, max(live.live_count * 0.10, 1.0)
            ),
            "unit": _unit_score(fields.get("unit"), "registrations"),
            "source_signal": term_coverage(
                fields.get("source_signal"),
                {"amf", "initial registration", "request"},
            ),
            "window": _window_score(fields.get("window"), storm["storm_interval"]),
        }
        return _product_score(
            "t1",
            fields,
            components,
            {
                "request_count": 0.75,
                "unit": 0.10,
                "source_signal": 0.10,
                "window": 0.05,
            },
        )

    if kind == "t2":
        peak = fields.get("peak_rate")
        components = {
            "peak_rate": numeric_score(
                peak, live.live_peak_rate, max(live.live_peak_rate * 0.25, 1.0)
            ),
            "unit": _unit_score(fields.get("unit"), "registrations per second"),
            "source_signal": term_coverage(
                fields.get("source_signal"),
                {"amf", "initial registration", "request", "rate"},
            ),
            "rate_window": _window_score(fields.get("rate_window"), "30s"),
        }
        return _product_score(
            "t2",
            fields,
            components,
            {
                "peak_rate": 0.75,
                "unit": 0.10,
                "source_signal": 0.10,
                "rate_window": 0.05,
            },
        )

    if kind == "t3":
        request_count = fields.get("request_count", fields.get("count"))
        success_count = fields.get("success_count")
        deficit = fields.get("deficit")
        live_success = live.live_count - live.rejected_volume
        arithmetic_ref = 0.0
        arithmetic_scale = 1.0
        if isinstance(request_count, (int, float)) and isinstance(
            success_count, (int, float)
        ):
            arithmetic_ref = float(request_count) - float(success_count)
            arithmetic_scale = max(abs(arithmetic_ref) * 0.10, 1.0)
        components = {
            "request_count": numeric_score(
                request_count, live.live_count, max(live.live_count * 0.10, 1.0)
            ),
            "success_count": numeric_score(
                success_count, live_success, max(abs(live_success) * 0.10, 1.0)
            ),
            "deficit": numeric_score(
                deficit, live.rejected_volume, max(live.rejected_volume * 0.10, 1.0)
            ),
            "unit": _unit_score(fields.get("unit"), "registrations"),
            "arithmetic_consistency": (
                numeric_score(deficit, arithmetic_ref, arithmetic_scale)
                if isinstance(request_count, (int, float))
                and isinstance(success_count, (int, float))
                else 0.0
            ),
        }
        return _product_score(
            "t3",
            fields,
            components,
            {
                "request_count": 0.25,
                "success_count": 0.25,
                "deficit": 0.35,
                "unit": 0.10,
                "arithmetic_consistency": 0.05,
            },
        )

    if kind == "t4":
        verdict = fields.get("verdict")
        is_storm = live.live_peak_rate > _IDLE_PEAK_THRESHOLD
        verdict_terms = (
            {"storm", "signalling storm", "overload", "overloaded"}
            if is_storm
            else {"normal", "idle", "baseline"}
        )
        components = {
            "peak_evidence": numeric_score(
                fields.get("peak_rate"),
                live.live_peak_rate,
                max(live.live_peak_rate * 0.25, 1.0),
            ),
            "deficit_evidence": numeric_score(
                fields.get("deficit"),
                live.rejected_volume,
                max(live.rejected_volume * 0.10, 1.0),
            ),
            "verdict": 1.0 if _text_matches_any(verdict, verdict_terms) else 0.0,
            "evidence_text": term_coverage(
                fields.get("evidence"), {"live", "peak rate", "deficit", "overload"}
            ),
        }
        return _product_score(
            "t4",
            fields,
            components,
            {
                "peak_evidence": 0.30,
                "deficit_evidence": 0.25,
                "verdict": 0.30,
                "evidence_text": 0.15,
            },
        )

    if kind == "t5":
        mechanisms = _as_list(fields.get("mechanisms"))
        excluded = _as_list(fields.get("excluded"))
        selected_text = _joined(mechanisms)
        components = {
            "selected_mechanisms": set_f1_score(mechanisms, _T5_EXPECTED),
            "excluded_distractor": term_coverage(excluded, {_T5_DISTRACTOR}),
            "no_unsafe_selected_distractor": 0.0
            if term_coverage(selected_text, {_T5_DISTRACTOR}) == 1.0
            else 1.0,
            "rationale": term_coverage(
                fields.get("rationale"),
                {"ngap", "traffic load reduction", "flow control"},
            ),
        }
        return _product_score(
            "t5",
            fields,
            components,
            {
                "selected_mechanisms": 0.55,
                "excluded_distractor": 0.15,
                "no_unsafe_selected_distractor": 0.15,
                "rationale": 0.15,
            },
        )

    if kind == "t6":
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
        return _product_score(
            "t6",
            fields,
            components,
            {
                "action": 0.25,
                "protected_traffic": 0.25,
                "rejected_traffic": 0.25,
                "rationale": 0.25,
            },
        )

    if kind == "t7":
        tlr = as_float(fields.get("tlr_percent"))
        post_expected = live.live_peak_rate * (1 - tlr / 100) if tlr is not None else 0.0
        post_rate_score = numeric_score(
            fields.get("post_control_rate"),
            post_expected,
            error_scale=max(live.capacity_rate * 0.25, 1.0),
        )
        formula_terms = term_coverage(
            fields.get("formula"), {"post control rate", "peak rate", "tlr percent"}
        )
        components = {
            "peak_measurement": numeric_score(
                fields.get("peak_rate"),
                live.live_peak_rate,
                max(live.live_peak_rate * 0.25, 1.0),
            ),
            "capacity_measurement": numeric_score(
                fields.get("capacity_rate"),
                live.capacity_rate,
                max(live.capacity_rate * 0.25, 1.0),
            ),
            "formula_consistency": (formula_terms + post_rate_score) / 2,
            "tlr_safety": _tlr_safety_score(tlr, live.live_peak_rate, live.capacity_rate),
            "range_sanity": 1.0 if tlr is not None and 1 <= tlr <= 99 else 0.0,
        }
        return _product_score(
            "t7",
            fields,
            components,
            {
                "peak_measurement": 0.20,
                "capacity_measurement": 0.20,
                "formula_consistency": 0.20,
                "tlr_safety": 0.30,
                "range_sanity": 0.10,
            },
        )

    if kind == "t8":
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
                error_scale=max((submitted_capacity or live.capacity_rate) * 0.25, 1.0),
            )
            if submitted_retry_rate is not None
            else 0.0
        )
        expected_value = as_float(expected_retry_rate)
        if spread <= 0:
            backoff_safety = 0.0
        elif submitted_capacity is not None and expected_value is not None and expected_value <= submitted_capacity:
            backoff_safety = 1.0
        else:
            backoff_safety = numeric_score(
                spread, required_spread, error_scale=max(required_spread, 1.0)
            )
        components = {
            "deferred_volume": numeric_score(
                deferred_volume,
                live.rejected_volume,
                max(live.rejected_volume * 0.10, 1.0),
            ),
            "capacity_measurement": numeric_score(
                capacity, live.capacity_rate, max(live.capacity_rate * 0.25, 1.0)
            ),
            "spread_order_sanity": 1.0 if spread > 0 else 0.0,
            "expected_retry_rate": expected_retry_score,
            "backoff_safety": backoff_safety,
        }
        return _product_score(
            "t8",
            fields,
            components,
            {
                "deferred_volume": 0.20,
                "capacity_measurement": 0.20,
                "spread_order_sanity": 0.15,
                "expected_retry_rate": 0.20,
                "backoff_safety": 0.25,
            },
        )

    if kind == "t9":
        # Negative case: pass only by judging the undersized TLR ineffective AND
        # the live state agreeing it still exceeds capacity. Unclear -> None -> fail.
        verdict_ok = verdict_in(_T9_FAILS, completion)
        given_tlr = record["given_tlr"]
        live_fails = live.live_peak_rate * (1 - given_tlr / 100) > live.capacity_rate
        ok = verdict_ok is True and live_fails
        return Score(
            value=CORRECT if ok else INCORRECT,
            answer=fields.get("verdict"),
            explanation=(
                f"verdict_ineffective={verdict_ok}, given_tlr={given_tlr}, "
                f"live_peak_rate={live.live_peak_rate}, capacity_rate={live.capacity_rate}, "
                f"live_fails={live_fails}"
            ),
        )

    if kind == "t10":
        # Negative case: pass only by judging no control needed AND the live
        # baseline confirming low load. Unclear -> None -> fail.
        verdict_ok = _text_matches_any(
            fields.get("verdict", fields.get("recommendation")), _T10_NO_CONTROL
        )
        below_idle = live.baseline_peak_rate < _IDLE_PEAK_THRESHOLD
        ok = verdict_ok is True and below_idle
        return Score(
            value=CORRECT if ok else INCORRECT,
            answer=fields.get("verdict"),
            explanation=(
                f"verdict_no_control={verdict_ok}, "
                f"baseline_peak_rate={live.baseline_peak_rate}, below_idle={below_idle}"
            ),
        )

    raise ValueError(f"unknown task kind: {kind}")


async def _gather_live_state(kind: str, record: dict) -> LiveState:
    """Probe only what the kind's grading rule needs; default the rest to zero."""
    if kind == "t10":
        # Baseline world: the idle peak rate is the only ground truth needed.
        # The baseline sample carries the same windows so the read reproduces.
        baseline = record["baseline"]
        return LiveState(
            baseline_peak_rate=await live_peak_rate(
                baseline["storm_interval"],
                baseline["peak_window"],
                baseline["scrape_interval_s"],
            )
        )

    storm = record["storm"]
    window = storm["storm_interval"]
    peak_window = storm["peak_window"]
    step = storm["scrape_interval_s"]

    if kind == "t1":
        return LiveState(live_count=await live_count(window))
    if kind == "t2":
        return LiveState(live_peak_rate=await live_peak_rate(window, peak_window, step))
    if kind == "t3":
        return LiveState(
            live_count=await live_count(window),
            rejected_volume=await rejected_volume(window),
        )
    if kind == "t4":
        return LiveState(
            live_peak_rate=await live_peak_rate(window, peak_window, step),
            rejected_volume=await rejected_volume(window),
        )
    if kind in ("t7", "t9"):
        return LiveState(
            live_peak_rate=await live_peak_rate(window, peak_window, step),
            capacity_rate=await capacity_rate(window, peak_window, step),
        )
    if kind == "t8":
        return LiveState(
            rejected_volume=await rejected_volume(window),
            capacity_rate=await capacity_rate(window, peak_window, step),
        )
    # t5, t6: normative-only graders need no live probe.
    return LiveState()


@scorer(metrics=[accuracy(), stderr()])
def signal_storm_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        kind = state.metadata["task_kind"]
        live = await _gather_live_state(kind, state.metadata)
        return decide(kind, state.output.completion, state.metadata, live)

    return score
