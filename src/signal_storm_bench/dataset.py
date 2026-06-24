"""Sample construction for the signal_storm_bench investigation suite (i1..i4).

The suite walks the operator loop on a live Open5GS core: measure the storm off
live AMF counters (i1), diagnose load state under storm and baseline worlds (i2),
select the correct overload-control mechanisms (i3), and size a NAS back-off
dispersion worksheet (i4).

Each Sample carries its leak-closed prompt, the world the solver must bring up
(storm or baseline), and the hidden ground truth the scorer needs in metadata
only. Prompts state the JSON answer shape and the operator question; they never
carry a live count, rate, peak, correct/distractor label, verdict word, or the
metric name. The agent discovers all values off the live core.

i2 yields two samples (one per world: storm and baseline); every other kind is a
single storm sample; the suite totals five samples.

All shared values (storm knobs, windows, candidate list) come from config.py;
this module never imports an answer.
"""

from inspect_ai.dataset import Sample

from signal_storm_bench import config

_I3_CANDIDATE_LINES = "\n".join(f"- {c}" for c in config.I3_CANDIDATES)

# Prompts: operator question + JSON answer shape only. Braces escaped ({{ }}) so
# .format() collapses them to literal braces. No live values, no answers, no
# verdict words, no correct/distractor labels.
_PROMPTS = {
    "i1": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, produce a storm-interval measurement extract for the AMF "
        "initial registrations: how many were requested, the peak request rate, "
        "how many succeeded, and the shortfall.\n"
        "Submit your answer as JSON: "
        '{{"request_count": <number>, "peak_rate": <number>, '
        '"success_count": <number>, "deficit": <number>}}'
    ),
    "i2": (
        "You are on call for the 5G core. Working off the live metrics, assess "
        "the current registration load state and whether any operator action is "
        "warranted right now. Back your call with the measured numbers.\n"
        "Submit your answer as JSON: "
        '{{"load_state": "...", "action_needed": <true|false>, '
        '"peak_rate": <number>, "deficit": <number>, "rationale": "..."}}'
    ),
    "i3": (
        "The AMF is under a registration storm. From the candidate list below, "
        "select the mechanisms that are genuine core-network overload controls "
        "for this situation and exclude the ones that are not, then state which "
        "traffic the chosen action protects and which it sheds.\n"
        "Candidates:\n"
        f"{_I3_CANDIDATE_LINES}\n"
        "Submit your answer as JSON: "
        '{{"mechanisms": ["..."], "excluded": ["..."], '
        '"protected_traffic": ["..."], "rejected_traffic": ["..."]}}'
    ),
    "i4": (
        "The AMF is under a registration storm and a backlog of deferred retries "
        "has built up. Working off the live metrics, produce a NAS back-off "
        "dispersion worksheet that spreads the deferred retries so they arrive at "
        "a rate the AMF can absorb without re-synchronising.\n"
        "Submit your answer as JSON: "
        '{{"deferred_volume": <number>, "capacity_rate": <number>, '
        '"backoff_min": <number>, "backoff_max": <number>, '
        '"expected_retry_rate": <number>}}'
    ),
}

_SHAPES = {
    "i1": "measurement extract: request_count, peak_rate, success_count, deficit",
    "i2": "diagnosis: load_state, action_needed, peak_rate, deficit, rationale",
    "i3": "selection: mechanisms, excluded, protected_traffic, rejected_traffic",
    "i4": "back-off worksheet: deferred_volume, capacity_rate, backoff_min/max, expected_retry_rate",
}


def _storm_knobs() -> dict:
    return {
        "storm_rate": config.STORM_RATE,
        "ue_count": config.STORM_UE_COUNT,
        "duration_s": config.STORM_DURATION_S,
        "storm_interval": config.STORM_INTERVAL,
        "peak_window": config.PEAK_WINDOW,
        "scrape_interval_s": config.SCRAPE_INTERVAL_S,
    }


def _baseline_windows() -> dict:
    return {
        "storm_interval": config.STORM_INTERVAL,
        "peak_window": config.PEAK_WINDOW,
        "scrape_interval_s": config.SCRAPE_INTERVAL_S,
    }


def _metadata(kind: str, world: str) -> dict:
    metadata: dict = {
        "task_kind": kind,
        "world": world,
        "submission_shape": _SHAPES[kind],
    }
    if world == "storm":
        metadata["storm"] = _storm_knobs()
    else:
        metadata["baseline"] = _baseline_windows()
    if kind == "i3":
        metadata["candidates"] = list(config.I3_CANDIDATES)
    if kind == "i2":
        metadata["expected_state"] = config.I2_EXPECTED_STATE[world]
    return metadata


def _samples_for(kind: str) -> list[Sample]:
    """i2 yields one sample per world; every other kind is a single storm sample."""
    if kind == "i2":
        return [
            Sample(
                id=f"i2-{world}",
                input=_PROMPTS["i2"].format(),
                target="",
                metadata=_metadata("i2", world),
            )
            for world in config.I2_WORLDS
        ]
    return [
        Sample(
            id=kind,
            input=_PROMPTS[kind].format(),
            target="",
            metadata=_metadata(kind, "storm"),
        )
    ]


def build_samples(kinds: tuple[str, ...] | None = None) -> list[Sample]:
    """Build the investigation suite, optionally filtered to a subset of kinds."""
    selected = set(kinds) if kinds else set(config.KINDS)
    samples: list[Sample] = []
    for kind in config.KINDS:
        if kind in selected:
            samples.extend(_samples_for(kind))
    return samples
