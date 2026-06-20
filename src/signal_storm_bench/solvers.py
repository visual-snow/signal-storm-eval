"""World preparation solver: boot -> inject storm -> manifest gate (P3).

Prepares the live Open5GS world for each sample before the agent runs. Waits for
the core to settle, then for a storm sample drives the PacketRusher injector to
fire the pinned registration storm and gates on the storm standing in the live
counters as a real deficit. A baseline sample (t10) fires nothing, so the
counters stay flat and the negative case holds.

Mirrors transport_oam_bench/solvers.py; the only module besides sandbox_ops that
shapes the world, and it does so through sandbox_ops alone.
"""

from inspect_ai.solver import Generate, Solver, TaskState, solver

from signal_storm_bench.config import MIN_STORM_PEAK_RATE
from signal_storm_bench.sandbox_ops import (
    LIVE_SNAPSHOT_KEY,
    capture_live_snapshot,
    run_storm,
    wait_for_boot,
    wait_storm_manifest,
)

# The injector occasionally under-delivers a storm (a handful of registrations
# instead of thousands); replay it until it stands as a real overload so no
# sample is graded against a degenerate world.
STORM_ATTEMPTS = 3


async def _freeze_snapshot(state: TaskState, windows: dict) -> None:
    """Snapshot the live ground truth at handoff and store it for the scorer.

    The scorer grades against this frozen snapshot, so an agent action during the
    episode (e.g. re-firing the storm) cannot move the ground truth it is graded
    against. Called once per sample, after the world is prepared.
    """
    state.store.set(LIVE_SNAPSHOT_KEY, await capture_live_snapshot(windows))


@solver
def world_setup() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        world = state.metadata["world"]
        await wait_for_boot()
        if world == "baseline":
            # No-storm negative case (t10): leave the injector idle so the
            # counters stay flat and the live peak reads below the idle band.
            # Freeze the idle snapshot so the scorer grades the negative case.
            await _freeze_snapshot(state, state.metadata["baseline"])
            return state
        # Storm world (t1..t9): fire the pinned storm so the counters stand, then
        # gate on a severe overload before handing control to the agent. Replay if
        # the injector under-fires, so the agent never meets a degenerate world.
        storm = state.metadata["storm"]
        for _ in range(STORM_ATTEMPTS):
            await run_storm(
                rate=storm["storm_rate"],
                ue_count=storm["ue_count"],
                duration_s=storm["duration_s"],
                timeout=storm["duration_s"] + 60,
            )
            if await wait_storm_manifest(
                storm["storm_interval"],
                storm["peak_window"],
                storm["scrape_interval_s"],
            ):
                # Freeze ground truth now, before the agent can touch the core.
                await _freeze_snapshot(state, storm)
                return state
        raise RuntimeError(
            f"storm failed to overload the AMF after {STORM_ATTEMPTS} attempts "
            f"(live peak stayed below {MIN_STORM_PEAK_RATE} reg/s)"
        )

    return solve
