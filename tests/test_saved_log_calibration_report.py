import pytest
from generate_saved_log_calibration_report import (
    LiveReferences,
    ScoredSavedSample,
    missing_required_references,
    parse_references,
    rescore_legacy_completion,
    summarize,
)


@pytest.fixture
def scored_saved_samples() -> list[ScoredSavedSample]:
    return [
        ScoredSavedSample(
            log_name="a.eval",
            model="m1",
            sample_id="t1",
            kind="t1",
            score=0.25,
            components={},
            legacy_value="I",
        ),
        ScoredSavedSample(
            log_name="b.eval",
            model="m2",
            sample_id="t1",
            kind="t1",
            score=0.75,
            components={},
            legacy_value="C",
        ),
    ]


@pytest.mark.parametrize(
    ("explanation", "expected"),
    [
        pytest.param(
            "count=6000 vs live_count=6034.7982600869955 (rel_tol=0.017)",
            {"live_count": 6034.7982600869955},
            id="live_count",
        ),
        pytest.param(
            "tlr_percent=89, live_peak_rate=107.4, capacity_rate=26.215",
            {"live_peak_rate": 107.4, "capacity_rate": 26.215},
            id="peak_and_capacity",
        ),
        pytest.param(
            "backoff=[618, 1236], rejected_volume=5292.8897, capacity_rate=25.4485",
            {"rejected_volume": 5292.8897, "capacity_rate": 25.4485},
            id="deficit_and_capacity",
        ),
    ],
)
def test_parse_references_from_legacy_explanations(
    explanation: str, expected: dict[str, float]
) -> None:
    refs = parse_references(explanation)

    for field, value in expected.items():
        assert getattr(refs, field) == pytest.approx(value)


def test_rescore_legacy_completion_uses_current_product_scorer() -> None:
    row = rescore_legacy_completion(
        log_name="example.eval",
        model="model-a",
        sample_id="t1",
        kind="t1",
        completion='{"count": 6000}',
        metadata={"storm": {"storm_interval": "5m"}},
        references=LiveReferences(live_count=6000),
    )

    assert row.score == pytest.approx(0.75)
    assert row.components["request_count"] == 1.0


@pytest.mark.parametrize(
    ("kind", "references"),
    [
        pytest.param("t1", LiveReferences(), id="t1_missing_live_count"),
        pytest.param(
            "t7", LiveReferences(live_peak_rate=100), id="t7_missing_capacity"
        ),
        pytest.param("t8", LiveReferences(capacity_rate=40), id="t8_missing_deficit"),
    ],
)
def test_rescore_legacy_completion_fails_fast_on_missing_required_reference(
    kind: str, references: LiveReferences
) -> None:
    with pytest.raises(
        ValueError, match=f"missing required live references for {kind}"
    ):
        rescore_legacy_completion(
            log_name="example.eval",
            model="model-a",
            sample_id=kind,
            kind=kind,
            completion="{}",
            metadata={"storm": {"storm_interval": "5m"}},
            references=references,
        )


@pytest.mark.parametrize(
    ("kind", "references", "expected"),
    [
        pytest.param("t1", LiveReferences(), ["live_count"], id="t1_count"),
        pytest.param(
            "t7",
            LiveReferences(live_peak_rate=100),
            ["capacity_rate"],
            id="t7_capacity",
        ),
        pytest.param(
            "t8",
            LiveReferences(capacity_rate=40),
            ["rejected_volume"],
            id="t8_deficit",
        ),
        pytest.param("t5", LiveReferences(), [], id="t5_no_live_reference"),
    ],
)
def test_missing_required_references_identifies_unrescorable_samples(
    kind: str, references: LiveReferences, expected: list[str]
) -> None:
    assert missing_required_references(kind, references) == expected


def test_summarize_reports_per_task_distribution(
    scored_saved_samples: list[ScoredSavedSample],
) -> None:
    summaries = summarize(scored_saved_samples)

    assert len(summaries) == 1
    assert summaries[0].kind == "t1"
    assert summaries[0].case_count == 2
    assert summaries[0].minimum == pytest.approx(0.25)
    assert summaries[0].maximum == pytest.approx(0.75)
    assert summaries[0].spread == pytest.approx(0.5)
    assert summaries[0].distinct_scores == 2


def test_rendered_report_describes_saved_trajectory_source(
    scored_saved_samples: list[ScoredSavedSample],
) -> None:
    from generate_saved_log_calibration_report import render_report

    report = render_report(scored_saved_samples, input_names=["logs/p5", "logs/p5b"])

    assert "# Saved Log Product Calibration" in report
    assert "logs/p5, logs/p5b" in report
    assert "| t1 | 2 | 0.250 | 0.750 | 0.500 | 0.500 | 2 |" in report
