"""Task-wiring invariants for signal_storm (no docker, no model).

Inspects the assembled @task statically: the solver chain must be exactly
system_message + world_setup + the basic_agent loop; the sandbox must be the
docker compose tuple pointing at topology/compose.yaml; the message limit must
default to 50; and `kinds` must filter the dataset for both Inspect -T forms.

Mirrors transport_oam_bench/tests/test_task_wiring.py.
"""

import inspect
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.solver import Solver

from signal_storm_bench.task import (
    COMPOSE_FILE,
    DEFAULT_MESSAGE_LIMIT,
    SYSTEM_PROMPT,
    signal_storm,
)

# Inspect's default ReAct system message (basic_agent injects this when no
# `init` is passed). Its presence alongside SYSTEM_PROMPT is the duplication
# bug this suite guards against.
_INSPECT_DEFAULT_PHRASE = "helpful assistant attempting to submit"


def _metadata(sample: Any) -> dict[str, Any]:
    assert sample.metadata is not None
    return sample.metadata


@pytest.fixture
def chain_names() -> list[str]:
    """Registry names of the assembled, flattened task solver chain."""
    chain = cast(Iterable[Solver], signal_storm().solver)
    return [registry_info(s).name for s in chain]


class TestSolverChainComposition:
    @pytest.mark.parametrize(
        ("registry_name", "expected_count"),
        [
            pytest.param("inspect_ai/system_message", 1, id="single_system_message"),
            pytest.param("signal_storm_bench/world_setup", 1, id="world_setup_present"),
            pytest.param("inspect_ai/basic_agent_loop", 1, id="agent_loop_present"),
        ],
    )
    def test_chain_has_expected_solver_counts(
        self, chain_names: list[str], registry_name: str, expected_count: int
    ) -> None:
        assert chain_names.count(registry_name) == expected_count

    def test_world_setup_precedes_agent_loop(self, chain_names: list[str]) -> None:
        assert chain_names.index("signal_storm_bench/world_setup") < chain_names.index(
            "inspect_ai/basic_agent_loop"
        )

    def test_domain_prompt_is_not_inspect_default(self) -> None:
        assert _INSPECT_DEFAULT_PHRASE not in SYSTEM_PROMPT
        assert SYSTEM_PROMPT.strip()


class TestSandboxAndLimits:
    def test_sandbox_is_docker_compose_tuple(self) -> None:
        sandbox = signal_storm().sandbox
        assert sandbox is not None
        assert sandbox.type == "docker"
        assert sandbox.config == COMPOSE_FILE
        compose = Path(COMPOSE_FILE)
        assert compose.name == "compose.yaml"
        assert compose.parent.name == "topology"

    def test_default_message_limit_is_fifty(self) -> None:
        # The limit is wired into basic_agent (not the Task), so assert the
        # public constant and the @task signature default carry 50.
        assert DEFAULT_MESSAGE_LIMIT == 50
        default = inspect.signature(signal_storm).parameters["message_limit"].default
        assert default == 50


def test_task_builds_five_sample_investigation_suite():
    from signal_storm_bench.task import signal_storm
    t = signal_storm()
    assert len(t.dataset) == 5


class TestKindsFilter:
    """`kinds` accepts Inspect's -T forms: a string (one value) or a list (csv)."""

    @pytest.mark.parametrize(
        ("kinds", "expected_kinds"),
        [
            pytest.param(None, {"i1", "i2", "i3", "i4"}, id="all"),
            pytest.param("i3", {"i3"}, id="single_string"),
            pytest.param("i1,i4", {"i1", "i4"}, id="csv_string"),
            pytest.param(["i1", "i4"], {"i1", "i4"}, id="list_from_inspect"),
        ],
    )
    def test_filters_dataset(
        self, kinds: str | list[str] | None, expected_kinds: set[str]
    ) -> None:
        task = signal_storm(kinds=kinds)
        got = {_metadata(s)["task_kind"] for s in task.dataset}
        assert got == expected_kinds
