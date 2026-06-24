"""The hidden answer key the scorer grades against (no prompt may import these)."""

from signal_storm_bench import config


def test_i3_answer_key_partitions_the_candidates():
    correct = set(config.I3_CORRECT)
    distractors = set(config.I3_DISTRACTORS)
    candidates = set(config.I3_CANDIDATES)
    assert correct.isdisjoint(distractors)
    assert correct | distractors == candidates
    assert len(correct) >= 2 and len(distractors) >= 2


def test_i3_traffic_classes_present():
    assert config.I3_PROTECTED and config.I3_REJECTED
    assert set(config.I3_PROTECTED).isdisjoint(config.I3_REJECTED)


def test_i2_expected_states_cover_both_worlds():
    assert set(config.I2_EXPECTED_STATE) == {"storm", "baseline"}
    assert config.I2_EXPECTED_STATE["storm"] == "overloaded"
    assert config.I2_EXPECTED_STATE["baseline"] == "normal"
