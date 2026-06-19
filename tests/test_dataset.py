"""Dataset invariants for the signal_storm suite (no sandbox, no model).

Pins the ten task kinds, unique ids, the hidden ground truth carried only in
Sample.metadata, and the leakage rules: a prompt must never carry the metric
name, the t6 enum answer, the expected t9/t10 verdicts, a live value, the
correct TLR, or the back-off pair. The t5 candidate list is published neutrally
(the distractor is named as a candidate), so the leak check excludes it.

Mirrors transport_oam_bench/tests/test_dataset.py.
"""

from typing import Any

import pytest

from signal_storm_bench.dataset import build_samples
from signal_storm_bench.scorers import (
    _T6_ACTION,
    _T9_FAILS,
    _T10_NO_CONTROL,
)

ALL_KINDS = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10")

# Prometheus series the agent must discover for itself; never named in a prompt.
_METRIC_NAMES = (
    "fivegs_amffunction_rm_reginitreq",
    "fivegs_amffunction_rm_reginitsucc",
)


def _metadata(sample: Any) -> dict[str, Any]:
    assert sample.metadata is not None
    return sample.metadata


def _prompt(sample: Any) -> str:
    assert isinstance(sample.input, str)
    return sample.input


def test_ten_samples_unique_ids_all_kinds():
    samples = build_samples()
    assert len(samples) == 10
    assert len({s.id for s in samples}) == 10
    kinds = {_metadata(s)["task_kind"] for s in samples}
    assert kinds == set(ALL_KINDS)


def test_metadata_carries_world_and_storm_knobs():
    for s in build_samples():
        metadata = _metadata(s)
        kind = metadata["task_kind"]
        assert metadata["world"] in ("storm", "baseline")
        if kind == "t10":
            assert metadata["world"] == "baseline"
            assert "storm" not in metadata
        else:
            assert metadata["world"] == "storm"
            storm = metadata["storm"]
            assert storm["storm_interval"] and storm["peak_window"]
            assert storm["scrape_interval_s"] > 0


def test_t5_candidates_and_t9_given_tlr_hidden_in_metadata():
    by_kind = {_metadata(s)["task_kind"]: s for s in build_samples()}
    candidates = _metadata(by_kind["t5"])["candidates"]
    assert "AMF load-balancing Weight Factor" in candidates  # the distractor
    assert _metadata(by_kind["t9"])["given_tlr"] == 10


def test_prompts_render_format_escapes():
    """Double-brace escapes collapse to real braces in every prompt."""
    for s in build_samples():
        prompt = _prompt(s)
        assert "{{" not in prompt and "}}" not in prompt


def test_prompt_never_leaks_the_metric_name():
    for s in build_samples():
        prompt = _prompt(s).lower()
        for metric in _METRIC_NAMES:
            assert metric not in prompt


def test_prompt_never_leaks_the_t6_enum_answer():
    for s in build_samples():
        assert _T6_ACTION.lower() not in _prompt(s).lower()


def test_prompts_request_product_artifacts():
    by_kind = {_metadata(s)["task_kind"]: s for s in build_samples()}
    expected_fields = {
        "t1": ["request_count", "unit", "source_signal", "window"],
        "t2": ["peak_rate", "unit", "source_signal", "rate_window"],
        "t3": ["request_count", "success_count", "deficit", "unit"],
        "t4": ["verdict", "peak_rate", "deficit", "evidence"],
        "t5": ["mechanisms", "excluded", "rationale"],
        "t6": ["action", "protected_traffic", "rejected_traffic", "rationale"],
        "t7": [
            "peak_rate",
            "capacity_rate",
            "formula",
            "tlr_percent",
            "post_control_rate",
        ],
        "t8": [
            "deferred_volume",
            "capacity_rate",
            "backoff_min",
            "backoff_max",
            "expected_retry_rate",
        ],
        "t9": [
            "given_tlr_percent",
            "peak_rate",
            "capacity_rate",
            "residual_rate",
            "verdict",
            "evidence",
        ],
        "t10": ["peak_rate", "deficit", "recommendation", "evidence"],
    }
    for kind, fields in expected_fields.items():
        prompt = _prompt(by_kind[kind])
        for field in fields:
            assert field in prompt
        assert "Submit your answer as JSON" in prompt


def test_t6_prompt_never_paraphrases_the_enum_answer():
    """t6 must not echo the enum's distinctive terms (catches the paraphrase leak).

    The enum value names "emergency" and "mobile terminated" services; the prompt
    must keep both out so the action is discovered from the standard, not the prompt.
    """
    t6 = next(s for s in build_samples() if _metadata(s)["task_kind"] == "t6")
    prompt = _prompt(t6).lower()
    assert "emergency" not in prompt
    assert "mobile terminated" not in prompt
    assert "mobile-terminated" not in prompt


@pytest.mark.parametrize(
    ("kind", "synonyms"),
    [
        pytest.param("t9", _T9_FAILS, id="t9"),
        pytest.param("t10", _T10_NO_CONTROL, id="t10"),
    ],
)
def test_negative_prompts_never_leak_the_expected_verdict(
    kind: str, synonyms: set[str]
):
    sample = next(s for s in build_samples() if _metadata(s)["task_kind"] == kind)
    prompt = _prompt(sample).lower()
    for synonym in synonyms:
        assert synonym not in prompt


def test_sizing_prompts_ask_for_the_answer_without_supplying_it():
    """t7/t8 must request the sizing answer as a placeholder, never a value.

    The TLR percent (t7) and the back-off pair (t8) are the graded answers; the
    prompt may name the JSON shape but must keep the slots as placeholders so no
    correct value is supplied.
    """
    by_kind = {_metadata(s)["task_kind"]: s for s in build_samples()}
    t7 = _prompt(by_kind["t7"]).lower()
    assert "tlr_percent" in t7 and "post_control_rate" in t7
    assert "1..99" not in t7
    t8 = _prompt(by_kind["t8"]).lower()
    assert "backoff_min" in t8 and "backoff_max" in t8
    assert "expected_retry_rate" in t8
