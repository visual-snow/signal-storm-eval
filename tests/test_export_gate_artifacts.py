from dataclasses import dataclass

import pytest
from export_gate_artifacts import is_low_score, select_transcript_sample


@dataclass(frozen=True)
class SampleScore:
    value: object


@dataclass(frozen=True)
class GateSample:
    id: str
    error: object | None
    scores: dict[str, SampleScore]


def test_is_low_score_handles_numeric_product_scores():
    assert is_low_score(0.2)
    assert is_low_score(0.79)
    assert not is_low_score(0.8)
    assert not is_low_score(1.0)


@pytest.fixture
def infra_error_sample() -> GateSample:
    return GateSample(
        id="infra-error", error=RuntimeError("prometheus down"), scores={}
    )


@pytest.mark.parametrize(
    "score_value",
    [
        pytest.param(0.2, id="numeric_low"),
        pytest.param("I", id="legacy_incorrect"),
    ],
)
def test_select_transcript_sample_prefers_model_failure_over_infra_error(
    infra_error_sample: GateSample, score_value: object
) -> None:
    model_failure = GateSample(
        id="model-failure",
        error=None,
        scores={"signal_storm_scorer": SampleScore(score_value)},
    )

    assert (
        select_transcript_sample([infra_error_sample, model_failure]) is model_failure
    )


def test_select_transcript_sample_skips_infra_error_when_any_scored_sample_exists(
    infra_error_sample: GateSample,
) -> None:
    passing_sample = GateSample(
        id="passing",
        error=None,
        scores={"signal_storm_scorer": SampleScore(0.95)},
    )

    assert (
        select_transcript_sample([infra_error_sample, passing_sample]) is passing_sample
    )


def test_select_transcript_sample_returns_none_for_only_infra_errors(
    infra_error_sample: GateSample,
) -> None:
    assert select_transcript_sample([infra_error_sample]) is None
