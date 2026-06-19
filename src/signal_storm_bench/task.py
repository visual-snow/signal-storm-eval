"""signal_storm: the Inspect @task entry point (P3).

Assembles the suite from the other modules: the dataset
(signal_storm_bench.dataset), the world-setup solver
(signal_storm_bench.solvers), the agent tool surface
(signal_storm_bench.tools), and the outcome scorer
(signal_storm_bench.scorers), wired into a single basic_agent loop over the live
Open5GS core. Exposes the @task that __init__.py re-exports so
`inspect eval signal_storm_bench/signal_storm` resolves.

Mirrors transport_oam_bench/task.py.
"""

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.solver import basic_agent, system_message

from signal_storm_bench.dataset import build_samples
from signal_storm_bench.scorers import signal_storm_scorer
from signal_storm_bench.solvers import world_setup
from signal_storm_bench.tools import agent_tools

COMPOSE_FILE = str(Path(__file__).parent / "topology" / "compose.yaml")

SYSTEM_PROMPT = """
You are a NOC engineer for a 5G core network operations centre. The core is an
all-in-one Open5GS deployment (AMF, SMF, UPF, and the other NFs) carrying live
NGAP/NAS registration traffic; Prometheus scrapes the AMF metrics. You have tool
access to the live metrics, the AMF config and NF logs, and the UE storm
simulator. Investigate the live core; do not guess. When confident, submit your
answer in the JSON format the task specifies.
""".strip()

DEFAULT_MESSAGE_LIMIT = 50


@task
def signal_storm(
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
    kinds: str | list[str] | None = None,
) -> Task:
    """5G-core signalling-storm NOC suite: investigate the live core (measure, diagnose, select, size).

    kinds: optional task-kind filter to run a slice; default runs all four
    investigation tasks (i2 runs in both the storm and baseline worlds, so the
    full suite is five samples). Inspect passes `-T kinds=i1,i4` as a list and
    `-T kinds=i2` as a string, so accept both.
    """
    if kinds is None:
        kind_filter: tuple[str, ...] | None = None
    elif isinstance(kinds, str):
        kind_filter = tuple(k.strip() for k in kinds.split(","))
    else:
        kind_filter = tuple(kinds)
    return Task(
        dataset=build_samples(kind_filter),
        solver=[
            world_setup(),
            basic_agent(
                init=system_message(SYSTEM_PROMPT),
                tools=agent_tools(),
                message_limit=message_limit,
            ),
        ],
        scorer=signal_storm_scorer(),
        sandbox=("docker", COMPOSE_FILE),
        # The i2 load-state judge defaults to Haiku; override with
        # --model-roles judge=... on the command line.
        model_roles={"judge": "anthropic/claude-haiku-4-5-20251001"},
    )
