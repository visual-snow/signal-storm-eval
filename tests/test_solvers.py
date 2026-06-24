"""World-setup freeze invariants (no docker, no model).

The scorer must grade against the live state as it stood at handoff, never a
fresh read taken after the agent has acted, so an agent action during the episode
cannot move the ground truth it is graded against. These tests pin that:
world_setup probes the live snapshot once, with the correct per-world windows,
and stores it; the scorer reads that frozen snapshot back (and refuses to grade
without one). The probing itself is exercised against patched Prometheus reads.
"""

import asyncio

import pytest

from signal_storm_bench import sandbox_ops, scorers, solvers
from signal_storm_bench.sandbox_ops import LIVE_SNAPSHOT_KEY
from signal_storm_bench.scorers import LiveState

STORM_WINDOWS = {"storm_interval": "5m", "peak_window": "30s", "scrape_interval_s": 5}
FROZEN = {
    "live_count": 6000.0,
    "live_peak_rate": 120.0,
    "rejected_volume": 5855.0,
    "capacity_rate": 145.0,
}


def _const_coro(value):
    """An async stand-in that ignores its args and returns a fixed value."""

    async def _coro(*args, **kwargs):
        return value

    return _coro


class _FakeStore:
    """Minimal per-sample store: just the get/set world_setup and score() use."""

    def __init__(self, data=None):
        self._data = dict(data or {})

    def set(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)


class _FakeState:
    def __init__(self, metadata, store=None):
        self.metadata = metadata
        self.store = store or _FakeStore()


def test_capture_live_snapshot_reads_all_four_primitives(monkeypatch):
    monkeypatch.setattr(sandbox_ops, "live_count", _const_coro(6000.0))
    monkeypatch.setattr(sandbox_ops, "live_peak_rate", _const_coro(120.0))
    monkeypatch.setattr(sandbox_ops, "rejected_volume", _const_coro(5855.0))
    monkeypatch.setattr(sandbox_ops, "capacity_rate", _const_coro(145.0))
    snap = asyncio.run(sandbox_ops.capture_live_snapshot(STORM_WINDOWS))
    assert snap == FROZEN


def test_world_setup_freezes_storm_snapshot_using_storm_windows(monkeypatch):
    seen = {}

    async def fake_capture(windows):
        seen["windows"] = windows
        return dict(FROZEN)

    storm = {**STORM_WINDOWS, "storm_rate": 120, "ue_count": 6000, "duration_s": 90}
    state = _FakeState({"world": "storm", "storm": storm})
    monkeypatch.setattr(solvers, "wait_for_boot", _const_coro(None))
    monkeypatch.setattr(solvers, "run_storm", _const_coro(None))
    monkeypatch.setattr(solvers, "wait_storm_manifest", _const_coro(True))
    monkeypatch.setattr(solvers, "capture_live_snapshot", fake_capture)

    asyncio.run(solvers.world_setup()(state, None))

    assert seen["windows"] is storm
    assert state.store.get(LIVE_SNAPSHOT_KEY) == FROZEN


def test_world_setup_baseline_freezes_idle_snapshot_without_firing(monkeypatch):
    seen = {}
    fired = {"count": 0}

    async def fake_capture(windows):
        seen["windows"] = windows
        return {k: 0.0 for k in FROZEN}

    async def fake_run_storm(*args, **kwargs):
        fired["count"] += 1

    baseline = dict(STORM_WINDOWS)
    state = _FakeState({"world": "baseline", "baseline": baseline})
    monkeypatch.setattr(solvers, "wait_for_boot", _const_coro(None))
    monkeypatch.setattr(solvers, "run_storm", fake_run_storm)
    monkeypatch.setattr(solvers, "capture_live_snapshot", fake_capture)

    asyncio.run(solvers.world_setup()(state, None))

    assert fired["count"] == 0  # baseline never fires the injector
    assert seen["windows"] is baseline
    assert state.store.get(LIVE_SNAPSHOT_KEY)["live_peak_rate"] == 0.0


def test_frozen_live_state_reads_snapshot_from_store():
    state = _FakeState({}, _FakeStore({LIVE_SNAPSHOT_KEY: dict(FROZEN)}))
    live = scorers._frozen_live_state(state)
    assert isinstance(live, LiveState)
    assert live.live_count == 6000.0
    assert live.rejected_volume == 5855.0
    assert live.capacity_rate == 145.0


def test_frozen_live_state_raises_when_snapshot_missing():
    state = _FakeState({}, _FakeStore())
    with pytest.raises(RuntimeError, match="snapshot missing"):
        scorers._frozen_live_state(state)
