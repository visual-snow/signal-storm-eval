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


class TestT5Mechanisms:
    def test_genuine_set_verbatim_candidate_scores_correct(self) -> None:
        # Copying the published candidate wording verbatim must score correct.
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                ]
            }
        )
        assert decide("t5", c, STORM_REC, STORM_LIVE).value == CORRECT

    def test_including_distractor_scores_incorrect(self) -> None:
        c = json.dumps(
            {
                "mechanisms": [
                    "NGAP Overload Start",
                    "Traffic Load Reduction Indication",
                    "AMF load-balancing Weight Factor",
                ]
            }
        )
        assert decide("t5", c, STORM_REC, STORM_LIVE).value == INCORRECT


class TestT6OverloadAction:
    def test_exact_enum_scores_correct(self) -> None:
        c = json.dumps({"overload_action": _T6_ACTION})
        assert decide("t6", c, STORM_REC, STORM_LIVE).value == CORRECT

    def test_accepts_product_action_during_migration(self) -> None:
        c = json.dumps(
            {
                "action": _T6_ACTION,
                "protected_traffic": [],
                "rejected_traffic": [],
                "rationale": "",
            }
        )
        assert decide("t6", c, STORM_REC, STORM_LIVE).value == CORRECT

    def test_wrong_action_scores_incorrect(self) -> None:
        c = json.dumps({"overload_action": "Reject all sessions"})
        assert decide("t6", c, STORM_REC, STORM_LIVE).value == INCORRECT


# --- t7/t8: sized recommendations graded against the live inequality ----------


class TestT7Tlr:
    def test_in_range_holding_load_scores_correct(self) -> None:
        # peak 100, capacity 40: need >=60% reduction.
        assert decide("t7", json.dumps({"tlr_percent": 70}), STORM_REC, STORM_LIVE).value == CORRECT

    def test_undersized_tlr_scores_incorrect(self) -> None:
        assert decide("t7", json.dumps({"tlr_percent": 30}), STORM_REC, STORM_LIVE).value == INCORRECT


class TestT8Backoff:
    def test_wide_enough_spread_scores_correct(self) -> None:
        # 6000 rejected over a 200s spread = 30/s, within 40/s capacity.
        c = json.dumps({"backoff_min": 0, "backoff_max": 200})
        assert decide("t8", c, STORM_REC, STORM_LIVE).value == CORRECT

    def test_zero_spread_scores_incorrect(self) -> None:
        c = json.dumps({"backoff_min": 5, "backoff_max": 5})
        assert decide("t8", c, STORM_REC, STORM_LIVE).value == INCORRECT


# --- t9/t10: negative cases, tristate verdict + live agreement ----------------


class TestT9UndersizedTlr:
    def test_ineffective_verdict_with_live_agreeing_scores_correct(self) -> None:
        # given_tlr 10: 100 * 0.9 = 90 > 40 capacity, so it genuinely fails.
        c = json.dumps({"verdict": "the proposed setting is ineffective"})
        assert decide("t9", c, T9_REC, STORM_LIVE).value == CORRECT

    def test_says_it_works_scores_incorrect(self) -> None:
        c = json.dumps({"verdict": "this holds the load fine"})
        assert decide("t9", c, T9_REC, STORM_LIVE).value == INCORRECT

    def test_unclear_verdict_never_correct(self) -> None:
        assert decide("t9", "hard to say", T9_REC, STORM_LIVE).value == INCORRECT

    # Regression: real model phrasings the original narrow set wrongly rejected.
    @pytest.mark.parametrize(
        "verdict",
        [
            pytest.param("No. The 10% Traffic Load Reduction is insufficient.", id="insufficient"),
            pytest.param("not sufficient", id="not_sufficient"),
            pytest.param("a 10% reduction will not hold the load", id="will_not_hold"),
            pytest.param("the offered rate is not capped by 10%", id="not_capped"),
        ],
    )
    def test_real_ineffective_phrasings_score_correct(self, verdict: str) -> None:
        c = json.dumps({"verdict": verdict})
        assert decide("t9", c, T9_REC, STORM_LIVE).value == CORRECT

    # Precision: opposite-polarity answers (the TLR works) must still fail.
    @pytest.mark.parametrize(
        "verdict",
        [
            pytest.param("the 10% TLR is sufficient and the AMF is no longer overloaded", id="sufficient"),
            pytest.param("this caps offered load below capacity, load is held", id="caps_held"),
        ],
    )
    def test_says_it_works_variants_score_incorrect(self, verdict: str) -> None:
        c = json.dumps({"verdict": verdict})
        assert decide("t9", c, T9_REC, STORM_LIVE).value == INCORRECT


class TestT10Baseline:
    def test_no_control_verdict_with_idle_live_scores_correct(self) -> None:
        c = json.dumps({"verdict": "no control needed"})
        assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == CORRECT

    def test_accepts_recommendation_during_migration(self) -> None:
        c = json.dumps(
            {
                "recommendation": "no flow control needed",
                "peak_rate": 0,
                "deficit": 0,
                "evidence": "idle",
            }
        )
        assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == CORRECT

    def test_recommending_control_scores_incorrect(self) -> None:
        c = json.dumps({"verdict": "apply traffic load reduction now"})
        assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == INCORRECT

    def test_unclear_verdict_never_correct(self) -> None:
        assert decide("t10", "not sure", BASELINE_REC, IDLE_LIVE).value == INCORRECT

    # Regression: every roster model said "no flow control needed"; the original
    # set required the exact "no control needed" and rejected all six.
    @pytest.mark.parametrize(
        "verdict",
        [
            pytest.param("no flow control needed", id="plain"),
            pytest.param("no_flow_control_needed", id="underscored"),
            pytest.param("No flow control is needed. All AMF counters are 0.", id="is_needed_longform"),
            pytest.param("Flow control is not required at this time.", id="not_required"),
            pytest.param("no flow control required", id="no_flow_control_required"),
        ],
    )
    def test_real_no_control_phrasings_score_correct(self, verdict: str) -> None:
        c = json.dumps({"verdict": verdict})
        assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == CORRECT

    # Precision: recommending control (incl. "no flow control configured, add it")
    # must still fail; that is why bare "no flow control" is not a synonym.
    @pytest.mark.parametrize(
        "verdict",
        [
            pytest.param("flow control is needed; apply a Traffic Load Reduction", id="needed_apply"),
            pytest.param("there is no flow control configured, so we should add it", id="configured_add_it"),
        ],
    )
    def test_recommending_control_variants_score_incorrect(self, verdict: str) -> None:
        c = json.dumps({"verdict": verdict})
        assert decide("t10", c, BASELINE_REC, IDLE_LIVE).value == INCORRECT


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
