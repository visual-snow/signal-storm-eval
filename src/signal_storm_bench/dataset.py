"""Sample construction: one Sample per signalling-storm task (t1..t10).

The suite walks the operator loop on a live Open5GS core: characterise the storm
off the live AMF counters (t1..t4), recommend standards-consistent flow control
(t5..t8), then verify it (t9..t10). Each Sample carries its leak-closed prompt,
the world the `world_setup()` solver must bring up (`storm` or `baseline`), and
the hidden ground truth the scorer needs in `metadata` only. Prompts state the
JSON answer shape and the operator question; they never carry a live count,
rate, peak, target, capacity, the correct TLR, the back-off pair, the t6 enum,
the expected verdicts, the t5 distractor, or the metric name. The agent
discovers all of that off the live core.

Every shared value (storm knobs, windows, the t5 candidate list, the planted
t9 TLR) comes from config.py; this module never imports an answer.

Mirrors transport_oam_bench/dataset.py.
"""

from inspect_ai.dataset import Sample

from signal_storm_bench import config

# The t5 candidate list, published neutrally in the prompt. Rendered from the one
# definition in config so the prompt can never drift from what the scorer grades.
_T5_CANDIDATE_LINES = "\n".join(f"- {candidate}" for candidate in config.T5_CANDIDATES)


# Prompts: operator question + JSON answer shape only. Braces escaped ({{ }}) so
# .format() collapses them to literal braces; no live values, no answers leaked.
_PROMPTS = {
    "t1": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, produce a storm-interval measurement extract for the AMF "
        "initial-registration requests. Include the request count, unit, source "
        "signal description, and time window.\n"
        "Submit your answer as JSON: "
        '{{"request_count": <number>, "unit": "...", '
        '"source_signal": "...", "window": "..."}}'
    ),
    "t2": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, produce a peak-load measurement extract for the AMF "
        "initial-registration rate. Include the peak rate, unit, source signal "
        "description, and rate window.\n"
        "Submit your answer as JSON: "
        '{{"peak_rate": <number>, "unit": "...", '
        '"source_signal": "...", "rate_window": "..."}}'
    ),
    "t3": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, produce a registration deficit note for the storm interval. "
        "Include request count, success count, deficit, and unit.\n"
        "Submit your answer as JSON: "
        '{{"request_count": <number>, "success_count": <number>, '
        '"deficit": <number>, "unit": "..."}}'
    ),
    "t4": (
        "Working off the live metrics, produce a load-state assessment memo for "
        "the current 5G core load. Include your verdict, measured peak rate, "
        "measured deficit, and evidence.\n"
        "Submit your answer as JSON: "
        '{{"verdict": "...", "peak_rate": <number>, '
        '"deficit": <number>, "evidence": "..."}}'
    ),
    "t5": (
        "The AMF is under a registration storm. From the candidate list below, "
        "produce a flow-control mechanism recommendation. Include selected "
        "mechanisms, excluded candidates, and a brief rationale.\n"
        "Candidates:\n"
        f"{_T5_CANDIDATE_LINES}\n"
        "Submit your answer as JSON: "
        '{{"mechanisms": ["..."], "excluded": ["..."], "rationale": "..."}}'
    ),
    "t6": (
        "The AMF is under a registration storm. Produce an NGAP overload-action "
        "policy proposal for this load. Include the action, protected traffic "
        "classes, rejected traffic classes, and standards rationale.\n"
        "Submit your answer as JSON: "
        '{{"action": "...", "protected_traffic": ["..."], '
        '"rejected_traffic": ["..."], "rationale": "..."}}'
    ),
    "t7": (
        "The AMF is under a registration storm. Working off the live peak and "
        "the AMF's emergent processing throughput, produce a Traffic Load "
        "Reduction sizing worksheet that holds the offered load down to what "
        "the AMF can absorb. Include measurements, formula, proposed percentage, "
        "and expected post-control rate.\n"
        "Submit your answer as JSON: "
        '{{"peak_rate": <number>, "capacity_rate": <number>, '
        '"formula": "...", "tlr_percent": <number>, '
        '"post_control_rate": <number>}}'
    ),
    "t8": (
        "The AMF is under a registration storm and a backlog of deferred "
        "retries has built up. Working off the live metrics, produce a NAS "
        "back-off dispersion worksheet that spreads deferred retries so they "
        "arrive at a rate the AMF can absorb without re-synchronising.\n"
        "Submit your answer as JSON: "
        '{{"deferred_volume": <number>, "capacity_rate": <number>, '
        '"backoff_min": <number>, "backoff_max": <number>, '
        '"expected_retry_rate": <number>}}'
    ),
    "t9": (
        "The AMF is under a registration storm. A Traffic Load Reduction of "
        f"{config.GIVEN_TLR} percent has been proposed. Working off the live peak "
        "and the AMF's emergent processing throughput, produce a verification "
        "memo for whether this setting holds the offered load down to what the "
        "AMF can absorb.\n"
        "Submit your answer as JSON: "
        f'{{{{"given_tlr_percent": {config.GIVEN_TLR}, "peak_rate": <number>, '
        '"capacity_rate": <number>, "residual_rate": <number>, '
        '"verdict": "...", "evidence": "..."}}'
    ),
    "t10": (
        "The 5G core is running with no storm in progress. Working off the live "
        "metrics, produce a baseline no-action assessment. Include measured "
        "load, deficit, recommendation, and evidence.\n"
        "Submit your answer as JSON: "
        '{{"peak_rate": <number>, "deficit": <number>, '
        '"recommendation": "...", "evidence": "..."}}'
    ),
}

# Short note on the expected submission shape, for trajectory triage. Not graded.
_SHAPES = {
    "t1": "measurement extract with request_count, unit, source_signal, window",
    "t2": "measurement extract with peak_rate, unit, source_signal, rate_window",
    "t3": "deficit note with request_count, success_count, deficit, unit",
    "t4": "assessment memo with verdict, peak_rate, deficit, evidence",
    "t5": "recommendation with mechanisms, excluded, rationale",
    "t6": "policy proposal with action, protected_traffic, rejected_traffic, rationale",
    "t7": "sizing worksheet with peak_rate, capacity_rate, formula, tlr_percent, post_control_rate",
    "t8": "dispersion worksheet with deferred_volume, capacity_rate, backoff_min, backoff_max, expected_retry_rate",
    "t9": "verification memo with given_tlr_percent, peak_rate, capacity_rate, residual_rate, verdict, evidence",
    "t10": "baseline assessment with peak_rate, deficit, recommendation, evidence",
}


def _storm_knobs() -> dict:
    """The pinned storm the scorer windows its live reads against (storm worlds)."""
    return {
        "storm_rate": config.STORM_RATE,
        "ue_count": config.STORM_UE_COUNT,
        "duration_s": config.STORM_DURATION_S,
        "storm_interval": config.STORM_INTERVAL,
        "peak_window": config.PEAK_WINDOW,
        "scrape_interval_s": config.SCRAPE_INTERVAL_S,
    }


def _baseline_windows() -> dict:
    """The read windows the t10 idle baseline reuses (no storm to inject)."""
    return {
        "storm_interval": config.STORM_INTERVAL,
        "peak_window": config.PEAK_WINDOW,
        "scrape_interval_s": config.SCRAPE_INTERVAL_S,
    }


def _build_metadata(kind: str) -> dict:
    """The hidden ground truth for one task: world, read windows, and per-kind knobs."""
    # t10 is the only no-storm negative case; every other kind reads a storm.
    world = "baseline" if kind == "t10" else "storm"
    metadata: dict = {
        "task_kind": kind,
        "world": world,
        "submission_shape": _SHAPES[kind],
    }
    if world == "storm":
        metadata["storm"] = _storm_knobs()
    if world == "baseline":
        metadata["baseline"] = _baseline_windows()
    if kind == "t5":
        metadata["candidates"] = list(config.T5_CANDIDATES)
    if kind == "t9":
        metadata["given_tlr"] = config.GIVEN_TLR
    return metadata


def build_samples(kinds: tuple[str, ...] | None = None) -> list[Sample]:
    """Build the suite, optionally filtered to a subset of task kinds.

    kinds=None builds all ten tasks (the full suite); a subset (e.g.
    ("t1", "t7")) builds only those, for fast single-task iteration.
    """
    selected = set(kinds) if kinds else set(config.KINDS)
    samples = []
    for kind in config.KINDS:
        if kind not in selected:
            continue
        sample_id = "t9-undersized" if kind == "t9" else kind
        samples.append(
            Sample(
                id=sample_id,
                # .format() collapses the {{ }} escapes to literal braces.
                input=_PROMPTS[kind].format(),
                target="",
                metadata=_build_metadata(kind),
            )
        )
    return samples
