from check_kind_differentiation import _numeric, differentiated


def test_numeric_maps_product_and_legacy_scores() -> None:
    assert _numeric(0.73) == 0.73
    assert _numeric("0.41") == 0.41
    assert _numeric("C") == 1.0
    assert _numeric("I") == 0.0
    assert _numeric("not-a-score") == 0.0


def test_kind_differentiation_accepts_numeric_spread() -> None:
    ok, spread, bands = differentiated([0.12, 0.31, 0.52, 0.71, 0.92])

    assert ok
    assert spread == 0.80
    assert bands == 5


def test_kind_differentiation_rejects_clustered_scores() -> None:
    ok, spread, bands = differentiated([0.50, 0.51, 0.52, 0.53, 0.54])

    assert not ok
    assert spread < 0.25
    assert bands == 1
