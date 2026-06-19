from check_differentiation import differentiated  # scripts/ on sys.path via conftest


def test_clear_spread_passes():
    assert differentiated({"a": 0.9, "b": 0.6, "c": 0.4, "d": 0.3, "e": 0.1})


def test_clustered_fails():
    assert not differentiated({"a": 0.5, "b": 0.5, "c": 0.5, "d": 0.52, "e": 0.51})


def test_spread_without_three_bands_fails():
    # spread 0.30 but only two distinct bands
    assert not differentiated({"a": 0.8, "b": 0.8, "c": 0.8, "d": 0.5, "e": 0.5})


def test_all_zero_fails():
    assert not differentiated({m: 0.0 for m in "abcde"})
