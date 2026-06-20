"""signal_storm: the Inspect @task entry point (P3).

Assembles the suite from the other modules: the dataset
(signal_storm_bench.dataset), the world-setup solver
(signal_storm_bench.solvers), the agent tool surface
(signal_storm_bench.tools), and the outcome scorer
(signal_storm_bench.scorers), wired into a single react agent loop over the live
Open5GS core. Exposes the @task that __init__.py re-exports so
`inspect eval signal_storm_bench/signal_storm` resolves.

Mirrors transport_oam_bench/task.py.
"""

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import AgentState, as_solver, react

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

# Start urging a final submission once the conversation is within this many
# messages of the limit. A model that fans out many tool calls per turn (heavy
# parallel investigation) would otherwise be cut off mid-loop and submit nothing,
# scoring 0 for running out of budget rather than for a wrong answer. The margin
# leaves room for one more turn so the urged submission lands before the cap.
SUBMIT_BUDGET_MARGIN = 12


def budget_aware_continue(message_limit: int):
    """A react on_continue hook that forces a submission as the budget runs out.

    react calls this every turn. Returning a string injects it as a user message
    (even after tool calls), so once the message budget is nearly spent the model
    is told to stop investigating and submit its best answer. This makes an
    out-of-budget run score the agent's actual answer instead of an empty one.
    """
    urge_threshold = max(2, message_limit - SUBMIT_BUDGET_MARGIN)

    async def on_continue(state: AgentState) -> bool | str:
        if len(state.messages) >= urge_threshold:
            return (
                "You are almost out of your investigation budget. Do not call any "
                "more tools. Call the {submit} tool now with your best answer in "
                "the exact JSON format the task asked for, using what you have "
                "already measured."
            )
        return True

    return on_continue


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

    The agent is a react loop with a single submit attempt; a budget-aware
    on_continue forces a final submission before message_limit so a model that
    over-investigates still scores its answer, not an empty one. The i2 load-state
    judge defaults to Haiku in the scorer (scorers.DEFAULT_JUDGE_MODEL); override
    it with `--model-roles judge=...`.
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
            as_solver(
                react(
                    prompt=SYSTEM_PROMPT,
                    tools=agent_tools(),
                    attempts=1,
                    on_continue=budget_aware_continue(message_limit),
                )
            ),
        ],
        scorer=signal_storm_scorer(),
        sandbox=("docker", COMPOSE_FILE),
        message_limit=message_limit,
    )
