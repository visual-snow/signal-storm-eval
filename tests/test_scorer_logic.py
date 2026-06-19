"""Scoring-reliability matrix for decide() across every investigation kind (i1..i4).

Goal: pin how decide() maps (submission, synthetic LiveState, sample metadata)
onto a score, so the score distribution is reproducible and a grading drift
surfaces as a test failure. No sandbox, no model: decide() is pure.
"""

import json

from signal_storm_bench import config
from signal_storm_bench.scorers import LiveState, decide

# Live snapshots the graders read (synthetic; no docker, no model).
STORM_LIVE = LiveState(
    live_count=10800.0,
    live_peak_rate=110.0,
    capacity_rate=70.0,
    rejected_volume=4200.0,
)
IDLE_LIVE = LiveState(baseline_peak_rate=0.0, rejected_volume=0.0)

STORM_REC = {"storm": {"storm_interval": config.STORM_INTERVAL}}
BASELINE_REC = {"baseline": {}}


def _score(kind, fields, rec=STORM_REC, live=STORM_LIVE, verdict_score=None):
    return decide(kind, json.dumps(fields), rec, live, verdict_score=verdict_score)


# ---- i1 measurement -------------------------------------------------------

def test_i1_reference_scores_high():
    s = _score("i1", {"request_count": 10800, "peak_rate": 110,
                      "success_count": 6600, "deficit": 4200})
    assert s.value >= 0.95


def test_i1_wrong_numbers_score_low():
    s = _score("i1", {"request_count": 10, "peak_rate": 1,
                      "success_count": 9, "deficit": 1})
    assert s.value <= 0.2


def test_i1_partial_one_field_wrong():
    s = _score("i1", {"request_count": 10800, "peak_rate": 110,
                      "success_count": 6600, "deficit": 0})
    assert 0.3 < s.value < 0.95


def test_i1_unparseable_scores_zero():
    assert decide("i1", "no json here", STORM_REC, STORM_LIVE).value == 0.0


# ---- i3 selection ---------------------------------------------------------

def test_i3_reference_scores_high():
    s = _score("i3", {
        "mechanisms": list(config.I3_CORRECT),
        "excluded": list(config.I3_DISTRACTORS),
        "protected_traffic": list(config.I3_PROTECTED),
        "rejected_traffic": list(config.I3_REJECTED),
    })
    assert s.value >= 0.95


def test_i3_picking_a_distractor_scores_lower():
    s = _score("i3", {
        "mechanisms": list(config.I3_CORRECT) + [config.I3_DISTRACTORS[0]],
        "excluded": [],
        "protected_traffic": list(config.I3_PROTECTED),
        "rejected_traffic": list(config.I3_REJECTED),
    })
    assert s.value < 0.95


def test_i3_empty_scores_low():
    s = _score("i3", {"mechanisms": [], "excluded": [],
                      "protected_traffic": [], "rejected_traffic": []})
    assert s.value <= 0.2


# ---- i4 NAS back-off ------------------------------------------------------

def test_i4_reference_scores_high():
    # required spread to land the 4200 backlog within 70 reg/s capacity is 60s;
    # a 90s spread yields 46.7 reg/s <= capacity (safe), retry rate consistent.
    s = _score("i4", {"deferred_volume": 4200, "capacity_rate": 70,
                      "backoff_min": 0, "backoff_max": 90,
                      "expected_retry_rate": 46.7})
    assert s.value >= 0.9


def test_i4_too_tight_a_spread_is_unsafe():
    # 5s spread -> 840 reg/s, far above capacity -> backoff safety fails
    s = _score("i4", {"deferred_volume": 4200, "capacity_rate": 70,
                      "backoff_min": 0, "backoff_max": 5,
                      "expected_retry_rate": 840})
    assert s.value < 0.7


def test_i4_wrong_measurements_score_low():
    s = _score("i4", {"deferred_volume": 1, "capacity_rate": 1,
                      "backoff_min": 0, "backoff_max": 0,
                      "expected_retry_rate": 1})
    assert s.value <= 0.3
