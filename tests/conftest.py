"""Shared test configuration and fixtures."""

import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

# Task construction resolves model_roles eagerly. Provide a stub key so
# static wiring tests can call signal_storm() without a real API credential.
# Actual eval runs must set ANTHROPIC_API_KEY in the environment.
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = "test-placeholder-not-for-inference"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    logging.basicConfig(level=logging.INFO)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    run_slow = config.getoption("--runslow") or os.environ.get(
        "RUN_SLOW_TESTS", ""
    ).lower() in ("1", "true", "yes", "on")

    run_dataset_download = os.environ.get(
        "RUN_DATASET_DOWNLOAD_TESTS", "1"
    ).lower() not in ("0", "false", "no", "off")

    skip_slow = pytest.mark.skip(reason="Need --runslow or RUN_SLOW_TESTS=1 to run")
    skip_dataset = pytest.mark.skip(reason="RUN_DATASET_DOWNLOAD_TESTS=0")

    for item in items:
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)
        if "dataset_download" in item.keywords and not run_dataset_download:
            item.add_marker(skip_dataset)
