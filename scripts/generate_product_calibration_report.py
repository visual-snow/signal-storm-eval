"""Generate an offline calibration report for product scorer anchor artifacts.

This intentionally uses synthetic LiveState snapshots and does not start docker.
It validates scorer spread for reference, partial, and bad artifacts before any
paid or CPU-heavy model calibration run.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

from signal_storm_bench.config import (
    KINDS,
    STORM_INTERVAL,
)
from signal_storm_bench.scorers import LiveState, decide

# All four investigation tasks calibrate in the storm world.
STORM_REC: dict[str, Any] = {
    "storm": {"storm_interval": STORM_INTERVAL},
    "world": "storm",
}

# Mirror tests/test_scorer_logic.py so reference anchors land high.
STORM_LIVE = LiveState(
    live_count=10800.0,
    live_peak_rate=110.0,
    capacity_rate=70.0,
    rejected_volume=4200.0,
)

# i3 normative grading needs no live values; use a default LiveState.
I3_LIVE = LiveState()


@dataclass(frozen=True)
class CalibrationCase:
    kind: str
    label: str
    artifact: dict[str, Any]
    verdict_score: float | None = field(default=None)


@dataclass(frozen=True)
class ScoredCase:
    kind: str
    label: str
    score: float
    components: dict[str, float]


@dataclass(frozen=True)
class KindSummary:
    kind: str
    case_count: int
    minimum: float
    maximum: float
    average: float
    spread: float
    distinct_scores: int


# ---------------------------------------------------------------------------
# Anchor artifacts
#
# STORM_LIVE: live_count=10800, live_peak_rate=110, capacity_rate=70,
#             rejected_volume=4200, success_ref=6600
#
# measure(v, ref, tol): full credit at ref, fades to 0 over tol*ref.
# Grade_i1 weights: request_count 0.25, peak_rate 0.30, success_count 0.20,
#                   deficit 0.25.
# Grade_i2 weights: peak_rate 0.30, deficit 0.30, verdict 0.40.
# Grade_i3 weights: selected_mechanisms 0.40, no_distractor 0.20,
#                   protected_traffic 0.20, rejected_traffic 0.20.
# Grade_i4 weights: deferred_volume 0.15, capacity_measurement 0.20,
#                   spread_present 0.10, retry_rate_consistency 0.20,
#                   backoff_safety 0.35.
# ---------------------------------------------------------------------------

CALIBRATION_CASES = (
    # ------------------------------------------------------------------
    # i1: storm measurement extract
    # STORM_LIVE: live_count=10800, live_peak_rate=110,
    #             rejected_volume=4200, success_ref=6600
    # tol for count/success/deficit=0.10; tol for peak=0.25
    # Scoring: request_count w=0.25, peak_rate w=0.30,
    #          success_count w=0.20, deficit w=0.25
    # ------------------------------------------------------------------
    CalibrationCase(
        "i1",
        "bad",
        {
            "request_count": 100,
            "peak_rate": 5,
            "success_count": 100,
            "deficit": 0,
        },
    ),
    CalibrationCase(
        "i1",
        "weak_partial",
        {
            "request_count": 10000,
            "peak_rate": 85,
            "success_count": 6200,
            "deficit": 3900,
        },
    ),
    CalibrationCase(
        "i1",
        "mid_partial",
        {
            "request_count": 10500,
            "peak_rate": 96,
            "success_count": 6400,
            "deficit": 4050,
        },
    ),
    CalibrationCase(
        "i1",
        "strong_partial",
        {
            "request_count": 10650,
            "peak_rate": 103,
            "success_count": 6500,
            "deficit": 4100,
        },
    ),
    CalibrationCase(
        "i1",
        "reference",
        {
            "request_count": 10800,
            "peak_rate": 110,
            "success_count": 6600,
            "deficit": 4200,
        },
    ),
    # ------------------------------------------------------------------
    # i2: load-state diagnosis
    # Weights: peak_rate 0.30, deficit 0.30, verdict 0.40
    # verdict is binary (precomputed judge score: 0.0 or 1.0)
    # Strategy: use measurement accuracy + verdict to produce 5 ordered
    # distinct scores.
    #   bad:           peak=0,   deficit=0,   verdict=0.0 -> 0.000
    #   weak_partial:  peak=85,  deficit=0,   verdict=0.0 -> ~0.027
    #   mid_partial:   peak=110, deficit=0,   verdict=0.0 -> 0.300
    #   strong_partial: peak=0,  deficit=0,   verdict=1.0 -> 0.400
    #   reference:     peak=110, deficit=4200, verdict=1.0 -> 1.000
    # ------------------------------------------------------------------
    CalibrationCase(
        "i2",
        "bad",
        {"peak_rate": 0, "deficit": 0, "load_state": "normal"},
        verdict_score=0.0,
    ),
    CalibrationCase(
        "i2",
        "weak_partial",
        {"peak_rate": 85, "deficit": 0, "load_state": "normal"},
        verdict_score=0.0,
    ),
    CalibrationCase(
        "i2",
        "mid_partial",
        {"peak_rate": 110, "deficit": 0, "load_state": "normal"},
        verdict_score=0.0,
    ),
    CalibrationCase(
        "i2",
        "strong_partial",
        {"peak_rate": 0, "deficit": 0, "load_state": "overloaded"},
        verdict_score=1.0,
    ),
    CalibrationCase(
        "i2",
        "reference",
        {"peak_rate": 110, "deficit": 4200, "load_state": "overloaded"},
        verdict_score=1.0,
    ),
    # ------------------------------------------------------------------
    # i3: flow-control selection (normative; no live values needed)
    # I3_CORRECT = (NGAP Overload Start, Traffic Load Reduction Indication,
    #               NAS congestion control back-off)
    # I3_DISTRACTORS = (AMF load-balancing Weight Factor, RACH back-off,
    #                   SMF Session-AMBR throttling)
    # I3_PROTECTED = (emergency, mobile terminated)
    # I3_REJECTED  = (mobile originated, other registrations)
    # ------------------------------------------------------------------
    CalibrationCase(
        "i3",
        "bad",
        {
            "mechanisms": [
                "AMF load-balancing Weight Factor",
                "RACH back-off (RAN admission)",
                "SMF Session-AMBR throttling",
            ],
            "protected_traffic": [],
            "rejected_traffic": ["all sessions"],
        },
    ),
    CalibrationCase(
        "i3",
        "weak_partial",
        {
            "mechanisms": ["NGAP Overload Start"],
            "protected_traffic": [],
            "rejected_traffic": [],
        },
    ),
    CalibrationCase(
        "i3",
        "mid_partial",
        {
            "mechanisms": [
                "NGAP Overload Start",
                "Traffic Load Reduction Indication",
            ],
            "protected_traffic": ["emergency"],
            "rejected_traffic": [],
        },
    ),
    CalibrationCase(
        "i3",
        "strong_partial",
        {
            "mechanisms": [
                "NGAP Overload Start",
                "Traffic Load Reduction Indication",
                "NAS congestion control back-off",
            ],
            "protected_traffic": ["emergency", "mobile terminated"],
            "rejected_traffic": [],
        },
    ),
    CalibrationCase(
        "i3",
        "reference",
        {
            "mechanisms": [
                "NGAP Overload Start",
                "Traffic Load Reduction Indication",
                "NAS congestion control back-off",
            ],
            "protected_traffic": ["emergency", "mobile terminated"],
            "rejected_traffic": ["mobile originated", "other registrations"],
        },
    ),
    # ------------------------------------------------------------------
    # i4: NAS back-off dispersion
    # STORM_LIVE: rejected_volume=4200, capacity_rate=70
    # resulting_rate = rejected_volume / spread
    # Weights: deferred_volume 0.15, capacity_measurement 0.20,
    #          spread_present 0.10, retry_rate_consistency 0.20, backoff_safety 0.35
    #
    # bad:            spread=0 -> all zero                           -> 0.000
    # weak_partial:   spread=200, deferred/cap off -> spread+safety  -> 0.450
    # mid_partial:    spread=100, deferred ok, cap off, rate=42      -> 0.800
    # strong_partial: spread=100, all ok, expect off by 8/17.5       -> 0.909
    # reference:      spread=60, rate=70 (at cap), all exact         -> 1.000
    # ------------------------------------------------------------------
    CalibrationCase(
        "i4",
        "bad",
        {
            "deferred_volume": 0,
            "capacity_rate": 0,
            "backoff_min": 5,
            "backoff_max": 5,
            "expected_retry_rate": 0,
        },
    ),
    CalibrationCase(
        "i4",
        "weak_partial",
        {
            "deferred_volume": 2000,
            "capacity_rate": 50,
            "backoff_min": 0,
            "backoff_max": 200,
            "expected_retry_rate": 50,
        },
    ),
    CalibrationCase(
        "i4",
        "mid_partial",
        {
            "deferred_volume": 4200,
            "capacity_rate": 50,
            "backoff_min": 0,
            "backoff_max": 100,
            "expected_retry_rate": 42,
        },
    ),
    CalibrationCase(
        "i4",
        "strong_partial",
        {
            "deferred_volume": 4200,
            "capacity_rate": 70,
            "backoff_min": 0,
            "backoff_max": 100,
            "expected_retry_rate": 50,
        },
    ),
    CalibrationCase(
        "i4",
        "reference",
        {
            "deferred_volume": 4200,
            "capacity_rate": 70,
            "backoff_min": 0,
            "backoff_max": 60,
            "expected_retry_rate": 70,
        },
    ),
)


def _live_for(kind: str) -> LiveState:
    return I3_LIVE if kind == "i3" else STORM_LIVE


def _components(metadata: dict[str, Any] | None) -> dict[str, float]:
    raw = (metadata or {}).get("components", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in raw.items()
        if isinstance(value, int | float)
    }


def score_cases(
    cases: tuple[CalibrationCase, ...] = CALIBRATION_CASES,
) -> list[ScoredCase]:
    rows: list[ScoredCase] = []
    for case in cases:
        score = decide(
            case.kind,
            json.dumps(case.artifact),
            STORM_REC,
            _live_for(case.kind),
            verdict_score=case.verdict_score,
        )
        rows.append(
            ScoredCase(
                kind=case.kind,
                label=case.label,
                score=float(score.value),
                components=_components(score.metadata),
            )
        )
    return rows


def summarize(rows: list[ScoredCase]) -> list[KindSummary]:
    by_kind: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_kind[row.kind].append(row.score)
    summaries = []
    for kind in KINDS:
        scores = by_kind[kind]
        summaries.append(
            KindSummary(
                kind=kind,
                case_count=len(scores),
                minimum=min(scores),
                maximum=max(scores),
                average=mean(scores),
                spread=max(scores) - min(scores),
                distinct_scores=len({round(score, 3) for score in scores}),
            )
        )
    return summaries


def _component_text(components: dict[str, float]) -> str:
    return ", ".join(f"{key}={value:.2f}" for key, value in sorted(components.items()))


def _scores_text(rows: list[ScoredCase], kind: str) -> str:
    return ", ".join(f"{row.label}={row.score:.3f}" for row in rows if row.kind == kind)


def render_report(rows: list[ScoredCase]) -> str:
    summaries = summarize(rows)
    lines = [
        "# Product Score Calibration",
        "",
        "Generated from `scripts/generate_product_calibration_report.py` using "
        "synthetic scorer inputs only; no docker services or model calls are "
        "started. This is scorer-anchor calibration, not a replacement for the "
        "paused model-roster calibration.",
        "",
        "## Per-task Distributions",
        "",
        "| Task | Cases | Min | Max | Mean | Spread | Distinct scores | Anchor scores |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary.kind} | {summary.case_count} | {summary.minimum:.3f} | "
            f"{summary.maximum:.3f} | {summary.average:.3f} | {summary.spread:.3f} | "
            f"{summary.distinct_scores} | {_scores_text(rows, summary.kind)} |"
        )

    lines.extend(
        [
            "",
            "## Component Scores",
            "",
            "| Task | Anchor | Score | Components |",
            "|---|---|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.kind} | {row.label} | {row.score:.3f} | "
            f"{_component_text(row.components)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Every retained task has five anchors: bad, three partials, and reference.",
            "- Reference anchors should score high and bad anchors should score low.",
            "- The score spread is a local scorer-distribution check. Full model "
            "calibration still requires a fresh product-scored roster run when "
            "Docker/model budget is available.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    report = render_report(score_cases())
    if output is None:
        print(report)
    else:
        output.write_text(report)
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
