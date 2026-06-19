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

Mirrors transport_oam_bench/dataset.py. No import of logic (prompts are pure
strings); ground truth lives in metadata and live probes.
"""

from inspect_ai.dataset import Sample

# Pinned storm knobs (topology/compose.yaml packetrusher service + storm.sh). The
# storm runs DURATION_S seconds at STORM_RATE reg/s over UE_COUNT UEs. Recorded
# in scorer-side metadata so the live PromQL reads are reproducible across epochs
# for pass^k; the scorer windows `increase(...)`/`rate(...)` with these. The
# offered rate sits well above the cpu-capped AMF's emergent throughput, so the
# storm leaves a sustained, permanent reginitreq > reginitsucc deficit (see
# docs/topology-notes.md "Sustained-overload tuning").
_STORM = {
    "storm_rate": 120,
    "ue_count": 6000,
    "duration_s": 90,
    # PromQL window spanning the whole storm for `increase(...)` (t1, t3); the
    # outer max_over_time range for the peak/capacity reads. Generous enough that
    # the storm stays in-window through grading latency.
    "storm_interval": "5m",
    # Inner rate() sub-window for the peak/capacity reads (t2, t7, t9), and the
    # scrape interval that drives t1's relative tolerance (~one scrape).
    "peak_window": "30s",
    "scrape_interval_s": 5,
}

# The baseline world (t10) carries no storm, but t10 reads live_peak_rate with the
# same window shape, so reuse the storm windows for a reproducible idle read.
_BASELINE = {
    "storm_interval": _STORM["storm_interval"],
    "peak_window": _STORM["peak_window"],
    "scrape_interval_s": _STORM["scrape_interval_s"],
}

# t9's undersized Traffic Load Reduction percent, hidden in metadata. Small
# enough that live_peak_rate * (1 - given_tlr/100) still exceeds capacity_rate,
# so the only correct verdict is that it fails to hold the load.
_T9_GIVEN_TLR = 10

# t5 candidate list, published neutrally. The instruction does NOT hint which is
# the distractor (`AMF load-balancing Weight Factor`); the agent decides.
_T5_CANDIDATES = (
    "NGAP Overload Start",
    "Traffic Load Reduction Indication",
    "AMF load-balancing Weight Factor",
)


# Prompts: operator question + JSON answer shape only. Braces escaped ({{ }}) so
# .format() collapses them to literal braces; no live values, no answers leaked.
_PROMPTS = {
    "t1": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, report how many initial-registration requests the AMF "
        "received over the storm interval.\n"
        'Submit your answer as JSON: {{"count": <integer>}}'
    ),
    "t2": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, report the peak initial-registration rate, in registrations "
        "per second, reached during the storm.\n"
        'Submit your answer as JSON: {{"peak_rate": <number>}}'
    ),
    "t3": (
        "A registration surge is hitting the 5G core. Working off the live "
        "metrics, report how far successful registrations lagged behind the "
        "requests over the storm interval (the deficit).\n"
        'Submit your answer as JSON: {{"deficit": <number>}}'
    ),
    "t4": (
        "Working off the live metrics, classify the current load on the 5G "
        "core as a signalling storm or as normal traffic.\n"
        'Submit your answer as JSON: {{"verdict": "storm"}} or '
        '{{"verdict": "normal"}}'
    ),
    "t5": (
        "The AMF is under a registration storm. From the candidate list below, "
        "name only the genuine NGAP/NAS flow-control mechanism(s); leave out "
        "anything that is not flow control.\n"
        "Candidates:\n"
        "- NGAP Overload Start\n"
        "- Traffic Load Reduction Indication\n"
        "- AMF load-balancing Weight Factor\n"
        'Submit your answer as JSON: {{"mechanisms": ["...", "..."]}}'
    ),
    "t6": (
        "The AMF is under a registration storm. Name the standards-defined NGAP "
        "overload action for this load.\n"
        'Submit your answer as JSON: {{"overload_action": "..."}}'
    ),
    "t7": (
        "The AMF is under a registration storm. Working off the live peak and "
        "the AMF's emergent processing throughput, size the Traffic Load "
        "Reduction percentage that holds the offered load down to what the AMF "
        "can absorb.\n"
        'Submit your answer as JSON: {{"tlr_percent": <integer 1..99>}}'
    ),
    "t8": (
        "The AMF is under a registration storm and a backlog of deferred "
        "retries has built up. Working off the live metrics, derive a NAS "
        "back-off time range that disperses the deferred retries so they arrive "
        "at a rate the AMF can absorb without re-synchronising.\n"
        'Submit your answer as JSON: '
        '{{"backoff_min": <seconds>, "backoff_max": <seconds>}}'
    ),
    "t9": (
        "The AMF is under a registration storm. A Traffic Load Reduction of "
        f"{_T9_GIVEN_TLR} percent has been proposed. Working off the live peak "
        "and the AMF's emergent processing throughput, judge whether this "
        "setting holds the offered load down to what the AMF can absorb.\n"
        'Submit your answer as JSON: {{"verdict": "..."}}'
    ),
    "t10": (
        "The 5G core is running with no storm in progress. Working off the live "
        "metrics, judge whether the current load calls for any flow control to "
        "be applied.\n"
        'Submit your answer as JSON: {{"verdict": "..."}}'
    ),
}

# World per task (per-task table): t1..t9 read an active storm; t10 is the
# no-storm baseline negative case.
_WORLDS = {
    "t1": "storm",
    "t2": "storm",
    "t3": "storm",
    "t4": "storm",
    "t5": "storm",
    "t6": "storm",
    "t7": "storm",
    "t8": "storm",
    "t9": "storm",
    "t10": "baseline",
}

# Short note on the expected submission shape, for trajectory triage. Not graded.
_SHAPES = {
    "t1": "object with integer count",
    "t2": "object with numeric peak_rate",
    "t3": "object with numeric deficit",
    "t4": "object with verdict in {storm, normal}",
    "t5": "object with mechanisms list of strings",
    "t6": "object with overload_action string",
    "t7": "object with integer tlr_percent in 1..99",
    "t8": "object with numeric backoff_min and backoff_max",
    "t9": "object with verdict string (negative case)",
    "t10": "object with verdict string (negative case)",
}

# Sample id per kind; t9 carries the variant suffix per the contract example.
_IDS = {k: ("t9-undersized" if k == "t9" else k) for k in _PROMPTS}

_KINDS = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10")


def build_samples(kinds: tuple[str, ...] | None = None) -> list[Sample]:
    """Build the suite, optionally filtered to a subset of task kinds.

    kinds=None builds all ten tasks (the full suite); a subset (e.g.
    ("t1", "t7")) builds only those, for fast single-task iteration.
    """
    selected = set(kinds) if kinds else set(_KINDS)
    samples = []
    for kind in _KINDS:
        if kind not in selected:
            continue
        world = _WORLDS[kind]
        metadata: dict = {
            "task_kind": kind,
            "world": world,
            "submission_shape": _SHAPES[kind],
        }
        # Storm samples carry the pinned knobs/windows so the scorer's live reads
        # are deterministic; the baseline sample carries only the read windows.
        if world == "storm":
            metadata["storm"] = dict(_STORM)
        else:
            metadata["baseline"] = dict(_BASELINE)
        if kind == "t5":
            metadata["candidates"] = list(_T5_CANDIDATES)
        if kind == "t9":
            metadata["given_tlr"] = _T9_GIVEN_TLR
        samples.append(
            Sample(
                id=_IDS[kind],
                # .format() collapses the {{ }} escapes to literal braces.
                input=_PROMPTS[kind].format(),
                target="",
                metadata=metadata,
            )
        )
    return samples
