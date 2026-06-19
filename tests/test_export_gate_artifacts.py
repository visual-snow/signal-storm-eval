from export_gate_artifacts import is_low_score


def test_is_low_score_handles_numeric_product_scores():
    assert is_low_score(0.2)
    assert is_low_score(0.79)
    assert not is_low_score(0.8)
    assert not is_low_score(1.0)
