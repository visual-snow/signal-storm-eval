"""Unit tests for the pure scoring helpers (no sandbox, no model, no docker).

Pins parse_submission, normalize_verdict, and the per-task numeric/set/enum/
inequality/back-off helpers the scorer composes. These are the whole grading
surface below decide(), so a regression here surfaces as a fast test failure.

Mirrors transport_oam_bench/tests/test_logic.py.
"""

import pytest

from signal_storm_bench.logic import (
    backoff_ok,
    clamp01,
    component_average,
    enum_match,
    normalize_verdict,
    numeric_score,
    numeric_within,
    parse_submission,
    set_f1_score,
    set_equal_normalized,
    term_coverage,
    tlr_holds,
    verdict_in,
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


# --- numeric_within -----------------------------------------------------------


def test_numeric_within_inside_and_outside_tolerance():
    assert numeric_within(102.0, 100.0, 0.10)
    assert numeric_within(90.0, 100.0, 0.10)
    assert not numeric_within(120.0, 100.0, 0.10)


def test_numeric_within_zero_ref_only_exact_zero():
    assert numeric_within(0.0, 0.0, 0.10)
    assert not numeric_within(0.01, 0.0, 0.10)


def test_numeric_score_is_gradual():
    assert numeric_score(100, 100, error_scale=50) == 1.0
    assert numeric_score(125, 100, error_scale=50) == 0.5
    assert numeric_score(200, 100, error_scale=50) == 0.0


def test_numeric_score_handles_non_numeric_as_zero():
    assert numeric_score("bad", 100, error_scale=50) == 0.0
    assert numeric_score(None, 100, error_scale=50) == 0.0


# --- set_equal_normalized (t5) ------------------------------------------------


def test_set_equal_normalized_ignores_case_and_punctuation():
    assert set_equal_normalized(
        ["ngap overload start!", "Traffic Load Reduction"],
        ["NGAP Overload Start", "traffic load reduction"],
    )


def test_set_equal_normalized_rejects_distractor_or_missing():
    expected = ["NGAP Overload Start", "Traffic Load Reduction"]
    # distractor included
    assert not set_equal_normalized(
        [*expected, "AMF load-balancing Weight Factor"], expected
    )
    # a genuine mechanism dropped
    assert not set_equal_normalized(["NGAP Overload Start"], expected)


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


def test_component_average_clamps_and_weights():
    assert clamp01(1.5) == 1.0
    assert component_average(
        {"a": 1.0, "b": 0.5}, {"a": 0.75, "b": 0.25}
    ) == pytest.approx(0.875)


# --- enum_match (t6) ----------------------------------------------------------


def test_enum_match_format_tolerant():
    enum = "Permit Emergency Sessions and mobile terminated services only"
    assert enum_match("permit emergency sessions and mobile terminated services only", enum)
    assert not enum_match("reject all sessions", enum)


# --- tlr_holds (t7) -----------------------------------------------------------


def test_tlr_holds_in_range_and_capping():
    # peak 100, capacity 50: needs >=50% reduction to hold.
    assert tlr_holds(60, 100.0, 50.0)
    assert not tlr_holds(40, 100.0, 50.0)


@pytest.mark.parametrize("tlr", [0, 100, -5, 150])
def test_tlr_holds_out_of_range_fails(tlr: int):
    assert not tlr_holds(tlr, 100.0, 1.0)


# --- backoff_ok (t8) ----------------------------------------------------------


def test_backoff_ok_positive_spread_disperses_deficit():
    # 1000 rejected over a 40s spread = 25/s, within 30/s capacity.
    assert backoff_ok(10.0, 50.0, 1000.0, 30.0)


def test_backoff_ok_zero_or_negative_spread_fails():
    assert not backoff_ok(20.0, 20.0, 100.0, 30.0)
    assert not backoff_ok(50.0, 10.0, 100.0, 30.0)


def test_backoff_ok_too_narrow_spread_fails():
    # 1000 rejected over a 10s spread = 100/s, above 30/s capacity.
    assert not backoff_ok(10.0, 20.0, 1000.0, 30.0)


# --- verdict_in (t9/t10 tristate) ---------------------------------------------

_SYNONYMS = {"ineffective", "not capped", "ceiling exceeded", "overloaded"}


def test_verdict_in_true_on_synonym_substring():
    assert verdict_in(_SYNONYMS, '{"verdict": "the setting is ineffective"}') is True


@pytest.mark.parametrize(
    "completion",
    [
        pytest.param('{"verdict": "it works fine"}', id="wrong_verdict"),
        pytest.param('{"verdict": ""}', id="empty_verdict"),
        pytest.param('{"other": "ineffective"}', id="no_verdict_field"),
        pytest.param("not json", id="unparseable"),
    ],
)
def test_verdict_in_unclear_returns_none(completion: str):
    assert verdict_in(_SYNONYMS, completion) is None
