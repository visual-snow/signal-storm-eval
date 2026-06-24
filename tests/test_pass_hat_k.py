from pass_hat_k import is_pass_value, pass_hat_k  # scripts/ on sys.path via conftest


def test_is_pass_value_accepts_numeric_scores_above_threshold():
    assert is_pass_value(0.8)
    assert is_pass_value(0.95)
    assert not is_pass_value(0.79)
    assert not is_pass_value("I")


def test_all_pass_gives_one():
    # 3 samples, every epoch correct
    assert pass_hat_k({"s1": (3, 3), "s2": (3, 3), "s3": (3, 3)}, k=3) == 1.0


def test_all_fail_gives_zero():
    assert pass_hat_k({"s1": (0, 3), "s2": (0, 3)}, k=3) == 0.0


def test_flaky_sample_penalized_harder_with_larger_k():
    # one sample passing 2 of 3 epochs: C(2,k)/C(3,k)
    counts = {"s1": (2, 3)}
    k1 = pass_hat_k(counts, k=1)  # 2/3
    k2 = pass_hat_k(counts, k=2)  # C(2,2)/C(3,2) = 1/3
    k3 = pass_hat_k(counts, k=3)  # 0
    assert abs(k1 - 2 / 3) < 1e-9
    assert abs(k2 - 1 / 3) < 1e-9
    assert k3 == 0.0
    assert k1 > k2 > k3


def test_mixed_samples_average():
    # perfect sample and never-correct sample average to 0.5 at any k
    counts = {"good": (3, 3), "bad": (0, 3)}
    for k in (1, 2, 3):
        assert pass_hat_k(counts, k=k) == 0.5


def test_k_larger_than_epochs_raises():
    import pytest

    with pytest.raises(ValueError):
        pass_hat_k({"s1": (1, 1)}, k=2)
