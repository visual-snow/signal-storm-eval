"""Dataset invariants for the signal_storm_bench investigation suite (no sandbox, no model).

Pins the four task kinds (i1..i4), unique ids, the hidden ground truth carried only in
Sample.metadata, and the leakage rules: a prompt must never carry the metric name,
verdict words, correct/distractor labels, or the i3 traffic-class terms.
"""

from signal_storm_bench.dataset import build_samples

ALL_KINDS = ("i1", "i2", "i3", "i4")
_METRIC_NAMES = (
    "fivegs_amffunction_rm_reginitreq",
    "fivegs_amffunction_rm_reginitsucc",
)


def _metadata(sample):
    assert sample.metadata is not None
    return sample.metadata


def _prompt(sample):
    assert isinstance(sample.input, str)
    return sample.input


def test_five_samples_unique_ids_all_kinds():
    samples = build_samples()
    assert len(samples) == 5  # i1, i2-storm, i2-baseline, i3, i4
    assert len({s.id for s in samples}) == 5
    kinds = {_metadata(s)["task_kind"] for s in samples}
    assert kinds == set(ALL_KINDS)


def test_i2_runs_in_both_worlds():
    i2 = [s for s in build_samples() if _metadata(s)["task_kind"] == "i2"]
    worlds = {_metadata(s)["world"] for s in i2}
    assert worlds == {"storm", "baseline"}


def test_prompts_never_leak_metric_or_answer():
    for s in build_samples():
        prompt = _prompt(s).lower()
        for metric in _METRIC_NAMES:
            assert metric not in prompt
        # i3 must not paraphrase the overload action's distinctive terms
        assert "emergency" not in prompt
        assert "mobile terminated" not in prompt
        # no leaked verdict words for the diagnosis task
        assert "overloaded" not in prompt
        # no leaked correct/distractor labels
        assert "distractor" not in prompt


def test_prompts_render_format_escapes():
    for s in build_samples():
        prompt = _prompt(s)
        assert "{{" not in prompt and "}}" not in prompt


def test_prompts_request_product_artifacts():
    by_kind = {_metadata(s)["task_kind"]: s for s in build_samples()}
    expected_fields = {
        "i1": ["request_count", "peak_rate", "success_count", "deficit"],
        "i2": ["load_state", "action_needed", "peak_rate", "deficit", "rationale"],
        "i3": ["mechanisms", "excluded", "protected_traffic", "rejected_traffic"],
        "i4": ["deferred_volume", "capacity_rate", "backoff_min",
               "backoff_max", "expected_retry_rate"],
    }
    for kind, fields in expected_fields.items():
        prompt = _prompt(by_kind[kind])
        for field in fields:
            assert field in prompt
        assert "Submit your answer as JSON" in prompt


def test_i3_candidate_list_is_published():
    i3 = next(s for s in build_samples() if _metadata(s)["task_kind"] == "i3")
    prompt = _prompt(i3)
    from signal_storm_bench import config
    for candidate in config.I3_CANDIDATES:
        assert candidate in prompt
