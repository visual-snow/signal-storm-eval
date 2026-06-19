"""Unit tests for the pure scoring helpers (no sandbox, no model, no docker).

Pins parse_submission, normalize_verdict, and the numeric/set/phrase helpers the
scorer composes. These are the whole grading surface below decide(), so a
regression here surfaces as a fast test failure.

Mirrors transport_oam_bench/tests/test_logic.py.
"""

import pytest

from signal_storm_bench.logic import (
    clamp01,
    component_average,
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

# --- parse_submission ---------------------------------------------------------


def test_parse_plain_json_lowercases_keys():
    assert parse_submission('{"Count": 12}') == {"count": 12}


def test_parse_fenced_json():
    text = 'Here:\n```json\n{"verdict": "storm"}\n```'
    assert parse_submission(text) == {"verdict": "storm"}


def test_parse_widest_brace_span_from_prose():
    text = 'My answer is {"peak_rate": 42.5} as computed.'
    assert parse_submission(text) == {"peak_rate": 42.5}


def test_parse_preserves_list_and_numeric_values():
    parsed = parse_submission('{"mechanisms": ["A", "B"], "tlr_percent": 30}')
    assert parsed == {"mechanisms": ["A", "B"], "tlr_percent": 30}


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param("no json at all", id="prose"),
        pytest.param("{not valid json", id="broken_brace"),
        pytest.param("[1, 2, 3]", id="json_array_not_object"),
        pytest.param('"a bare string"', id="json_scalar"),
    ],
)
def test_parse_unparseable_returns_none_never_raises(text: str):
    assert parse_submission(text) is None


# --- normalize_verdict --------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("STORM", "storm", id="lowercase"),
        pytest.param("Not Capped!", "not capped", id="strip_punctuation"),
        pytest.param("  ceiling   exceeded  ", "ceiling exceeded", id="collapse_ws"),
        pytest.param("no-control_needed", "no control needed", id="separators"),
    ],
)
def test_normalize_verdict(raw: str, expected: str):
    assert normalize_verdict(raw) == expected


# --- numeric scoring ----------------------------------------------------------


def test_numeric_score_is_gradual():
    assert numeric_score(100, 100, error_scale=50) == 1.0
    assert numeric_score(125, 100, error_scale=50) == 0.5
    assert numeric_score(200, 100, error_scale=50) == 0.0


def test_numeric_score_handles_non_numeric_as_zero():
    assert numeric_score("bad", 100, error_scale=50) == 0.0
    assert numeric_score(None, 100, error_scale=50) == 0.0


def test_rel_scale_floors_at_one_and_uses_magnitude():
    assert rel_scale(100.0, 0.10) == 10.0
    assert rel_scale(2.0, 0.10) == 1.0  # floor so tolerance never collapses
    assert rel_scale(-50.0, 0.10) == 5.0  # magnitude, not sign


def test_measure_scores_relative_to_the_reference():
    assert measure(100, 100) == 1.0
    assert measure(110, 100, 0.25) == pytest.approx(0.6)  # scale 25, off by 10
    assert measure(0.4, 0.0, 0.10) == pytest.approx(0.6)  # scale floored to 1.0


# --- set / phrase coverage ----------------------------------------------------


def test_set_f1_score_rewards_partial_sets():
    assert set_f1_score(["a", "b"], ["a", "b"]) == 1.0
    assert set_f1_score(["a"], ["a", "b"]) == pytest.approx(2 / 3)
    assert set_f1_score(["x"], ["a", "b"]) == 0.0


def test_term_coverage_is_gradual():
    assert (
        term_coverage(
            "permit emergency and mobile terminated traffic",
            {"emergency", "mobile terminated"},
        )
        == 1.0
    )
    assert (
        term_coverage("permit emergency traffic", {"emergency", "mobile terminated"})
        == 0.5
    )


def test_term_coverage_uses_token_boundaries():
    assert term_coverage("teamf telemetry", {"amf"}) == 0.0
    assert term_coverage("AMF telemetry", {"amf"}) == 1.0


def test_matches_any_phrase():
    assert matches_any_phrase("the setting is ineffective", {"ineffective"})
    assert not matches_any_phrase("it works fine", {"ineffective"})
    assert not matches_any_phrase("", {"ineffective"})


def test_component_average_clamps_and_weights():
    assert clamp01(1.5) == 1.0
    assert component_average(
        {"a": 1.0, "b": 0.5}, {"a": 0.75, "b": 0.25}
    ) == pytest.approx(0.875)


# --- TLR / residual rate (t7) -------------------------------------------------


def test_residual_rate_is_the_load_left_after_a_reduction():
    assert residual_rate(100.0, 10) == pytest.approx(90.0)
    assert residual_rate(100.0, 60) == pytest.approx(40.0)


def test_tlr_holds_in_range_and_capping():
    # peak 100, capacity 50: needs >=50% reduction to hold.
    assert tlr_holds(60, 100.0, 50.0)
    assert not tlr_holds(40, 100.0, 50.0)


@pytest.mark.parametrize("tlr", [0, 100, -5, 150])
def test_tlr_holds_out_of_range_fails(tlr: int):
    assert not tlr_holds(tlr, 100.0, 1.0)
