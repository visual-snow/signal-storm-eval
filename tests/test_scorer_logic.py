"""Scoring-reliability matrix for decide() across every kind (t1..t10).

Goal: pin how decide() maps (submission, synthetic LiveState, sample metadata)
onto a score, so the score distribution is reproducible and a grading drift
surfaces as a test failure. Every kind gets a passing and a failing submission;
the negatives (t9/t10) also pin the tristate-verdict rule (unclear never scores
correct). No sandbox, no model: decide() is pure.

Mirrors transport_oam_bench/tests/test_scorer_logic.py.
"""

import json

import pytest
from inspect_ai.scorer import CORRECT, INCORRECT

from signal_storm_bench.scorers import (
    _T6_ACTION,
    LiveState,
    decide,
)

# Sample metadata the scorer reads: pinned storm window/scrape for the relative
# tolerance (t1/t3), and t9's undersized given_tlr. Mirrors dataset._STORM.
_STORM = {
    "storm_interval": "5m",
    "peak_window": "30s",
    "scrape_interval_s": 5,
}
STORM_REC: dict = {"storm": dict(_STORM)}
T9_REC: dict = {"storm": dict(_STORM), "given_tlr": 10}
BASELINE_REC: dict = {}

# Storm live snapshot: counters standing, a real deficit, capacity below peak.
STORM_LIVE = LiveState(
    live_count=10000.0,
    live_peak_rate=100.0,
    capacity_rate=40.0,
    rejected_volume=6000.0,
)
# Idle baseline: peak below the idle threshold (1.0 reg/s) -> no control needed.
IDLE_LIVE = LiveState(baseline_peak_rate=0.0)


def assert_score_between(score, low: float, high: float) -> None:
    assert low <= float(score.value) <= high, score.explanation
    assert score.metadata and "components" in score.metadata


# --- t1..t4: live-counter characterisation ------------------------------------


class TestT1Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "request_count": 10000,
                "unit": "registrations",
                "source_signal": "AMF initial-registration request counter",
                "window": "5m",
            }
        )
        assert float(decide("t1", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_partial_numeric_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "request_count": 9500,
                "unit": "registrations",
                "source_signal": "AMF initial-registration request counter",
                "window": "5m",
            }
        )
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.60, 0.70)

    def test_right_number_wrong_context_scores_partial(self) -> None:
        c = json.dumps(
            {
                "request_count": 10000,
                "unit": "packets",
                "source_signal": "CPU",
                "window": "now",
            }
        )
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.70, 0.80)

    def test_right_source_and_window_with_bad_count_scores_low_partial(self) -> None:
        c = json.dumps(
            {
                "request_count": 9000,
                "unit": "registrations",
                "source_signal": "AMF initial-registration request counter",
                "window": "5m",
            }
        )
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.20, 0.35)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "request_count": 500,
                "unit": "packets",
                "source_signal": "CPU",
                "window": "instant",
            }
        )
        assert_score_between(decide("t1", c, STORM_REC, STORM_LIVE), 0.0, 0.20)


class TestT2Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "unit": "registrations_per_second",
                "source_signal": "AMF initial-registration request rate",
                "rate_window": "30s",
            }
        )
        assert float(decide("t2", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_near_peak_scores_mid_high(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 90,
                "unit": "registrations_per_second",
                "source_signal": "AMF initial-registration request rate",
                "rate_window": "30s",
            }
        )
        assert_score_between(decide("t2", c, STORM_REC, STORM_LIVE), 0.65, 0.80)

    def test_offered_rate_guess_scores_partial(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 120,
                "unit": "registrations_per_second",
                "source_signal": "AMF initial-registration request rate",
                "rate_window": "30s",
            }
        )
        assert_score_between(decide("t2", c, STORM_REC, STORM_LIVE), 0.35, 0.50)

    def test_right_number_wrong_rate_context_scores_partial(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "unit": "registrations",
                "source_signal": "total request count",
                "rate_window": "5m",
            }
        )
        assert_score_between(decide("t2", c, STORM_REC, STORM_LIVE), 0.75, 0.90)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 10,
                "unit": "packets",
                "source_signal": "CPU",
                "rate_window": "instant",
            }
        )
        assert_score_between(decide("t2", c, STORM_REC, STORM_LIVE), 0.0, 0.20)


class TestT3Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "request_count": 10000,
                "success_count": 4000,
                "deficit": 6000,
                "unit": "registrations",
            }
        )
        assert float(decide("t3", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_wrong_deficit_with_right_counts_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "request_count": 10000,
                "success_count": 4000,
                "deficit": 5500,
                "unit": "registrations",
            }
        )
        assert_score_between(decide("t3", c, STORM_REC, STORM_LIVE), 0.60, 0.75)

    def test_right_deficit_missing_counts_scores_partial(self) -> None:
        c = json.dumps({"deficit": 6000, "unit": "registrations"})
        assert_score_between(decide("t3", c, STORM_REC, STORM_LIVE), 0.35, 0.50)

    def test_right_numbers_wrong_unit_scores_high_partial(self) -> None:
        c = json.dumps(
            {
                "request_count": 10000,
                "success_count": 4000,
                "deficit": 6000,
                "unit": "packets",
            }
        )
        assert_score_between(decide("t3", c, STORM_REC, STORM_LIVE), 0.85, 0.95)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "request_count": 500,
                "success_count": 500,
                "deficit": 0,
                "unit": "packets",
            }
        )
        assert_score_between(decide("t3", c, STORM_REC, STORM_LIVE), 0.0, 0.15)


class TestT4Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "verdict": "signalling storm",
                "peak_rate": 100,
                "deficit": 6000,
                "evidence": "live peak rate and registration deficit show overload",
            }
        )
        assert float(decide("t4", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_verdict_only_scores_low_partial(self) -> None:
        c = json.dumps({"verdict": "storm"})
        assert_score_between(decide("t4", c, STORM_REC, STORM_LIVE), 0.25, 0.40)

    def test_correct_measurements_wrong_verdict_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "verdict": "normal",
                "peak_rate": 100,
                "deficit": 6000,
                "evidence": "live peak rate and registration deficit measured",
            }
        )
        assert_score_between(decide("t4", c, STORM_REC, STORM_LIVE), 0.60, 0.75)

    def test_right_verdict_with_partial_measurements_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "verdict": "storm",
                "peak_rate": 90,
                "deficit": 0,
                "evidence": "live peak rate indicates overload",
            }
        )
        assert_score_between(decide("t4", c, STORM_REC, STORM_LIVE), 0.55, 0.70)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "verdict": "normal",
                "peak_rate": 0,
                "deficit": 0,
                "evidence": "no issue",
            }
        )
        assert_score_between(decide("t4", c, STORM_REC, STORM_LIVE), 0.0, 0.20)


# --- t5/t6: normative graders (no live probe) ---------------------------------


class TestT5Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                ],
                "excluded": ["AMF load-balancing Weight Factor"],
                "rationale": (
                    "NGAP overload control can signal traffic load reduction; "
                    "load-balancing weight is not a storm flow-control mechanism."
                ),
            }
        )
        assert float(decide("t5", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_one_genuine_mechanism_scores_partial(self) -> None:
        c = json.dumps(
            {
                "mechanisms": ["NGAP Overload Start"],
                "excluded": ["AMF load-balancing Weight Factor"],
                "rationale": "NGAP overload and traffic load reduction are flow control.",
            }
        )
        assert_score_between(decide("t5", c, STORM_REC, STORM_LIVE), 0.75, 0.85)

    def test_correct_mechanisms_without_exclusion_scores_partial(self) -> None:
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                ],
                "excluded": [],
                "rationale": "NGAP overload and traffic load reduction are flow control.",
            }
        )
        assert_score_between(decide("t5", c, STORM_REC, STORM_LIVE), 0.80, 0.90)

    def test_correct_selection_with_weak_rationale_scores_partial(self) -> None:
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                ],
                "excluded": ["AMF load-balancing Weight Factor"],
                "rationale": "these are better choices",
            }
        )
        assert_score_between(decide("t5", c, STORM_REC, STORM_LIVE), 0.82, 0.90)

    def test_unsafe_selected_distractor_scores_low(self) -> None:
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                    "AMF load-balancing Weight Factor",
                ],
                "excluded": [],
                "rationale": "NGAP overload and traffic load reduction are flow control.",
            }
        )
        assert_score_between(decide("t5", c, STORM_REC, STORM_LIVE), 0.0, 0.75)


class TestT6Product:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "action": _T6_ACTION,
                "protected_traffic": [
                    "emergency sessions",
                    "mobile terminated services",
                ],
                "rejected_traffic": [
                    "non emergency traffic",
                    "mobile originated registrations",
                ],
                "rationale": (
                    "NGAP overload control protects emergency and mobile "
                    "terminated services while rejecting non emergency mobile "
                    "originated traffic."
                ),
            }
        )
        assert float(decide("t6", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_action_only_scores_partial(self) -> None:
        c = json.dumps({"action": "permit emergency sessions only"})
        assert_score_between(decide("t6", c, STORM_REC, STORM_LIVE), 0.15, 0.25)

    def test_protected_traffic_only_scores_partial(self) -> None:
        c = json.dumps(
            {
                "action": "",
                "protected_traffic": [
                    "emergency sessions",
                    "mobile terminated services",
                ],
                "rejected_traffic": [],
                "rationale": "",
            }
        )
        assert_score_between(decide("t6", c, STORM_REC, STORM_LIVE), 0.20, 0.30)

    def test_action_and_protected_traffic_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "action": _T6_ACTION,
                "protected_traffic": [
                    "emergency sessions",
                    "mobile terminated services",
                ],
                "rejected_traffic": [],
                "rationale": "",
            }
        )
        assert_score_between(decide("t6", c, STORM_REC, STORM_LIVE), 0.45, 0.55)

    def test_reject_answer_scores_low_with_useful_rationale(self) -> None:
        c = json.dumps(
            {
                "action": "reject",
                "protected_traffic": [],
                "rejected_traffic": ["all sessions"],
                "rationale": "overload control is needed",
            }
        )
        assert_score_between(decide("t6", c, STORM_REC, STORM_LIVE), 0.0, 0.25)


# --- t7/t8: sized recommendations graded against the live inequality ----------


class TestT7Worksheet:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "capacity_rate": 40,
                "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
                "tlr_percent": 60,
                "post_control_rate": 40,
            }
        )
        assert float(decide("t7", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_near_miss_tlr_scores_high_partial(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "capacity_rate": 40,
                "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
                "tlr_percent": 55,
                "post_control_rate": 45,
            }
        )
        assert_score_between(decide("t7", c, STORM_REC, STORM_LIVE), 0.90, 0.99)

    def test_safe_tlr_with_wrong_residual_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "capacity_rate": 40,
                "formula": "guess",
                "tlr_percent": 70,
                "post_control_rate": 10,
            }
        )
        assert_score_between(decide("t7", c, STORM_REC, STORM_LIVE), 0.75, 0.85)

    def test_correct_formula_with_wrong_peak_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 80,
                "capacity_rate": 40,
                "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
                "tlr_percent": 60,
                "post_control_rate": 40,
            }
        )
        assert_score_between(decide("t7", c, STORM_REC, STORM_LIVE), 0.80, 0.90)

    def test_bad_tlr_worksheet_scores_low(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 0,
                "capacity_rate": 0,
                "formula": "",
                "tlr_percent": 10,
                "post_control_rate": 0,
            }
        )
        assert_score_between(decide("t7", c, STORM_REC, STORM_LIVE), 0.0, 0.30)


class TestT8Worksheet:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "deferred_volume": 6000,
                "capacity_rate": 40,
                "backoff_min": 0,
                "backoff_max": 150,
                "expected_retry_rate": 40,
            }
        )
        assert float(decide("t8", c, STORM_REC, STORM_LIVE).value) >= 0.95

    def test_too_narrow_spread_scores_high_partial(self) -> None:
        c = json.dumps(
            {
                "deferred_volume": 6000,
                "capacity_rate": 40,
                "backoff_min": 0,
                "backoff_max": 100,
                "expected_retry_rate": 60,
            }
        )
        assert_score_between(decide("t8", c, STORM_REC, STORM_LIVE), 0.85, 0.95)

    def test_safe_spread_with_wrong_retry_rate_scores_partial(self) -> None:
        c = json.dumps(
            {
                "deferred_volume": 6000,
                "capacity_rate": 40,
                "backoff_min": 0,
                "backoff_max": 200,
                "expected_retry_rate": 10,
            }
        )
        assert_score_between(decide("t8", c, STORM_REC, STORM_LIVE), 0.75, 0.85)

    def test_ordered_backoff_with_weak_measurements_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "deferred_volume": 3000,
                "capacity_rate": 80,
                "backoff_min": 0,
                "backoff_max": 100,
                "expected_retry_rate": 30,
            }
        )
        assert_score_between(decide("t8", c, STORM_REC, STORM_LIVE), 0.55, 0.65)

    def test_zero_spread_scores_low(self) -> None:
        c = json.dumps(
            {
                "deferred_volume": 0,
                "capacity_rate": 0,
                "backoff_min": 5,
                "backoff_max": 5,
                "expected_retry_rate": 0,
            }
        )
        assert_score_between(decide("t8", c, STORM_REC, STORM_LIVE), 0.0, 0.20)


# --- t9/t10: negative cases, tristate verdict + live agreement ----------------


class TestT9VerificationMemo:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "given_tlr_percent": 10,
                "peak_rate": 100,
                "capacity_rate": 40,
                "residual_rate": 90,
                "verdict": "the proposed setting is ineffective",
                "evidence": "10% TLR leaves residual load 90 above capacity 40.",
            }
        )
        assert float(decide("t9", c, T9_REC, STORM_LIVE).value) >= 0.95

    def test_verdict_only_scores_low(self) -> None:
        c = json.dumps({"verdict": "insufficient"})
        assert_score_between(decide("t9", c, T9_REC, STORM_LIVE), 0.25, 0.35)

    def test_correct_measurements_with_wrong_residual_scores_partial(self) -> None:
        c = json.dumps(
            {
                "given_tlr_percent": 10,
                "peak_rate": 100,
                "capacity_rate": 40,
                "residual_rate": 50,
                "verdict": "ineffective",
                "evidence": "TLR residual load still exceeds capacity.",
            }
        )
        assert_score_between(decide("t9", c, T9_REC, STORM_LIVE), 0.70, 0.80)

    def test_correct_residual_with_wrong_verdict_scores_midrange(self) -> None:
        c = json.dumps(
            {
                "given_tlr_percent": 10,
                "peak_rate": 100,
                "capacity_rate": 40,
                "residual_rate": 90,
                "verdict": "this holds the load fine",
                "evidence": "TLR residual load remains above capacity.",
            }
        )
        assert_score_between(decide("t9", c, T9_REC, STORM_LIVE), 0.60, 0.75)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "given_tlr_percent": 10,
                "peak_rate": 0,
                "capacity_rate": 0,
                "residual_rate": 0,
                "verdict": "sufficient",
                "evidence": "works",
            }
        )
        assert_score_between(decide("t9", c, T9_REC, STORM_LIVE), 0.0, 0.15)


class TestT10BaselineAssessment:
    def test_reference_scores_high(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 0,
                "deficit": 0,
                "recommendation": "no flow control needed",
                "evidence": "idle baseline below threshold with no deficit",
            }
        )
        assert float(decide("t10", c, BASELINE_REC, IDLE_LIVE).value) >= 0.95

    def test_recommendation_only_scores_low(self) -> None:
        c = json.dumps({"recommendation": "no flow control required"})
        assert_score_between(decide("t10", c, BASELINE_REC, IDLE_LIVE), 0.25, 0.35)

    def test_correct_peak_with_missing_deficit_scores_partial(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 0,
                "recommendation": "no flow control needed",
                "evidence": "",
            }
        )
        assert_score_between(decide("t10", c, BASELINE_REC, IDLE_LIVE), 0.60, 0.70)

    def test_unsafe_recommendation_with_evidence_scores_low(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 0,
                "deficit": 0,
                "recommendation": "apply flow control",
                "evidence": "idle baseline below threshold with no deficit",
            }
        )
        assert_score_between(decide("t10", c, BASELINE_REC, IDLE_LIVE), 0.0, 0.30)

    def test_bad_artifact_scores_low(self) -> None:
        c = json.dumps(
            {
                "peak_rate": 100,
                "deficit": 6000,
                "recommendation": "apply traffic load reduction now",
                "evidence": "storm",
            }
        )
        assert_score_between(decide("t10", c, BASELINE_REC, IDLE_LIVE), 0.0, 0.20)


# --- cross-cutting: unparseable never errors, unknown kind raises -------------


class TestUnparseableNeverErrors:
    @pytest.mark.parametrize(
        "kind",
        [pytest.param(f"t{i}", id=f"t{i}") for i in range(1, 11)],
    )
    @pytest.mark.parametrize(
        "completion",
        [
            pytest.param("", id="empty"),
            pytest.param("not json at all {", id="garbage"),
        ],
    )
    def test_garbage_scores_incorrect(self, kind: str, completion: str) -> None:
        rec = T9_REC if kind == "t9" else (BASELINE_REC if kind == "t10" else STORM_REC)
        live = IDLE_LIVE if kind == "t10" else STORM_LIVE
        assert decide(kind, completion, rec, live).value == INCORRECT

    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown task kind"):
            decide("t99", '{"x": 1}', STORM_REC, STORM_LIVE)
