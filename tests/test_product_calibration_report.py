from generate_product_calibration_report import score_cases, summarize


def test_product_calibration_cases_cover_every_task() -> None:
    rows = score_cases()
    by_kind = {summary.kind: summary for summary in summarize(rows)}

    assert set(by_kind) == {f"t{i}" for i in range(1, 11)}
    for summary in by_kind.values():
        assert summary.case_count == 5
        assert summary.maximum >= 0.85
        assert summary.minimum <= 0.20
        assert summary.spread >= 0.70
        assert summary.distinct_scores >= 4


def test_product_calibration_references_and_bad_anchors() -> None:
    rows = score_cases()
    for kind in {f"t{i}" for i in range(1, 11)}:
        reference = next(
            row for row in rows if row.kind == kind and row.label == "reference"
        )
        bad = next(row for row in rows if row.kind == kind and row.label == "bad")
        partials = [
            row for row in rows if row.kind == kind and row.label.endswith("_partial")
        ]

        assert reference.score >= 0.85
        assert bad.score <= 0.20
        assert len(partials) == 3
        assert len({round(row.score, 3) for row in partials}) == 3
