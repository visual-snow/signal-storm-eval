"""Generate an offline calibration report for product scorer anchor artifacts.

This intentionally uses synthetic LiveState snapshots and does not start docker.
It validates scorer spread for reference, partial, and bad artifacts before any
paid or CPU-heavy model calibration run.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from signal_storm_bench.config import (
    GIVEN_TLR,
    KINDS,
    PEAK_WINDOW,
    SCRAPE_INTERVAL_S,
    STORM_INTERVAL,
    T6_ACTION,
)
from signal_storm_bench.scorers import LiveState, decide

STORM_REC: dict[str, Any] = {
    "storm": {
        "storm_interval": STORM_INTERVAL,
        "peak_window": PEAK_WINDOW,
        "scrape_interval_s": SCRAPE_INTERVAL_S,
    }
}
T9_REC: dict[str, Any] = {**STORM_REC, "given_tlr": GIVEN_TLR}
BASELINE_REC: dict[str, Any] = {}

STORM_LIVE = LiveState(
    live_count=10000.0,
    live_peak_rate=100.0,
    capacity_rate=40.0,
    rejected_volume=6000.0,
)
IDLE_LIVE = LiveState(baseline_peak_rate=0.0)


@dataclass(frozen=True)
class CalibrationCase:
    kind: str
    label: str
    artifact: dict[str, Any]


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


CALIBRATION_CASES = (
    CalibrationCase(
        "t1",
        "bad",
        {
            "request_count": 500,
            "unit": "packets",
            "source_signal": "CPU",
            "window": "instant",
        },
    ),
    CalibrationCase(
        "t1",
        "weak_partial",
        {
            "request_count": 9000,
            "unit": "registrations",
            "source_signal": "AMF initial-registration request counter",
            "window": "5m",
        },
    ),
    CalibrationCase(
        "t1",
        "mid_partial",
        {
            "request_count": 9500,
            "unit": "registrations",
            "source_signal": "AMF initial-registration request counter",
            "window": "5m",
        },
    ),
    CalibrationCase(
        "t1",
        "strong_partial",
        {
            "request_count": 10000,
            "unit": "packets",
            "source_signal": "CPU",
            "window": "now",
        },
    ),
    CalibrationCase(
        "t1",
        "reference",
        {
            "request_count": 10000,
            "unit": "registrations",
            "source_signal": "AMF initial-registration request counter",
            "window": "5m",
        },
    ),
    CalibrationCase(
        "t2",
        "bad",
        {
            "peak_rate": 10,
            "unit": "packets",
            "source_signal": "CPU",
            "rate_window": "instant",
        },
    ),
    CalibrationCase(
        "t2",
        "weak_partial",
        {
            "peak_rate": 120,
            "unit": "registrations_per_second",
            "source_signal": "AMF initial-registration request rate",
            "rate_window": "30s",
        },
    ),
    CalibrationCase(
        "t2",
        "mid_partial",
        {
            "peak_rate": 90,
            "unit": "registrations_per_second",
            "source_signal": "AMF initial-registration request rate",
            "rate_window": "30s",
        },
    ),
    CalibrationCase(
        "t2",
        "strong_partial",
        {
            "peak_rate": 100,
            "unit": "registrations",
            "source_signal": "total request count",
            "rate_window": "5m",
        },
    ),
    CalibrationCase(
        "t2",
        "reference",
        {
            "peak_rate": 100,
            "unit": "registrations_per_second",
            "source_signal": "AMF initial-registration request rate",
            "rate_window": "30s",
        },
    ),
    CalibrationCase(
        "t3",
        "bad",
        {
            "request_count": 500,
            "success_count": 500,
            "deficit": 0,
            "unit": "packets",
        },
    ),
    CalibrationCase("t3", "weak_partial", {"deficit": 6000, "unit": "registrations"}),
    CalibrationCase(
        "t3",
        "mid_partial",
        {
            "request_count": 10000,
            "success_count": 4000,
            "deficit": 5500,
            "unit": "registrations",
        },
    ),
    CalibrationCase(
        "t3",
        "strong_partial",
        {
            "request_count": 10000,
            "success_count": 4000,
            "deficit": 6000,
            "unit": "packets",
        },
    ),
    CalibrationCase(
        "t3",
        "reference",
        {
            "request_count": 10000,
            "success_count": 4000,
            "deficit": 6000,
            "unit": "registrations",
        },
    ),
    CalibrationCase(
        "t4",
        "bad",
        {
            "verdict": "normal",
            "peak_rate": 0,
            "deficit": 0,
            "evidence": "no issue",
        },
    ),
    CalibrationCase("t4", "weak_partial", {"verdict": "storm"}),
    CalibrationCase(
        "t4",
        "mid_partial",
        {
            "verdict": "storm",
            "peak_rate": 90,
            "deficit": 0,
            "evidence": "live peak rate indicates overload",
        },
    ),
    CalibrationCase(
        "t4",
        "strong_partial",
        {
            "verdict": "normal",
            "peak_rate": 100,
            "deficit": 6000,
            "evidence": "live peak rate and registration deficit measured",
        },
    ),
    CalibrationCase(
        "t4",
        "reference",
        {
            "verdict": "signalling storm",
            "peak_rate": 100,
            "deficit": 6000,
            "evidence": "live peak rate and registration deficit show overload",
        },
    ),
    CalibrationCase(
        "t5",
        "bad",
        {
            "mechanisms": ["AMF load-balancing Weight Factor"],
            "excluded": [],
            "rationale": "load balancing weight factor fixes this",
        },
    ),
    CalibrationCase(
        "t5",
        "weak_partial",
        {
            "mechanisms": [],
            "excluded": ["AMF load-balancing Weight Factor"],
            "rationale": "NGAP overload and traffic load reduction are flow control.",
        },
    ),
    CalibrationCase(
        "t5",
        "mid_partial",
        {
            "mechanisms": ["NGAP Overload Start"],
            "excluded": ["AMF load-balancing Weight Factor"],
            "rationale": "NGAP overload and traffic load reduction are flow control.",
        },
    ),
    CalibrationCase(
        "t5",
        "strong_partial",
        {
            "mechanisms": ["NGAP Overload Start", "Traffic Load Reduction Indication"],
            "excluded": ["AMF load-balancing Weight Factor"],
            "rationale": "these are better choices",
        },
    ),
    CalibrationCase(
        "t5",
        "reference",
        {
            "mechanisms": ["NGAP Overload Start", "Traffic Load Reduction Indication"],
            "excluded": ["AMF load-balancing Weight Factor"],
            "rationale": (
                "NGAP overload control can signal traffic load reduction; "
                "load-balancing weight is not a storm flow-control mechanism."
            ),
        },
    ),
    CalibrationCase(
        "t6",
        "bad",
        {
            "action": "reject",
            "protected_traffic": [],
            "rejected_traffic": ["all sessions"],
            "rationale": "overload control is needed",
        },
    ),
    CalibrationCase("t6", "weak_partial", {"action": "permit emergency sessions only"}),
    CalibrationCase(
        "t6",
        "mid_partial",
        {
            "action": "",
            "protected_traffic": ["emergency sessions", "mobile terminated services"],
            "rejected_traffic": [],
            "rationale": "",
        },
    ),
    CalibrationCase(
        "t6",
        "strong_partial",
        {
            "action": T6_ACTION,
            "protected_traffic": ["emergency sessions", "mobile terminated services"],
            "rejected_traffic": [],
            "rationale": "",
        },
    ),
    CalibrationCase(
        "t6",
        "reference",
        {
            "action": T6_ACTION,
            "protected_traffic": ["emergency sessions", "mobile terminated services"],
            "rejected_traffic": [
                "non emergency traffic",
                "mobile originated registrations",
            ],
            "rationale": (
                "NGAP overload control protects emergency and mobile terminated "
                "services while rejecting non emergency mobile originated traffic."
            ),
        },
    ),
    CalibrationCase(
        "t7",
        "bad",
        {
            "peak_rate": 0,
            "capacity_rate": 0,
            "formula": "",
            "tlr_percent": 10,
            "post_control_rate": 0,
        },
    ),
    CalibrationCase(
        "t7",
        "weak_partial",
        {
            "peak_rate": 100,
            "capacity_rate": 40,
            "formula": "guess",
            "tlr_percent": 70,
            "post_control_rate": 10,
        },
    ),
    CalibrationCase(
        "t7",
        "mid_partial",
        {
            "peak_rate": 80,
            "capacity_rate": 40,
            "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
            "tlr_percent": 60,
            "post_control_rate": 40,
        },
    ),
    CalibrationCase(
        "t7",
        "strong_partial",
        {
            "peak_rate": 100,
            "capacity_rate": 40,
            "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
            "tlr_percent": 55,
            "post_control_rate": 45,
        },
    ),
    CalibrationCase(
        "t7",
        "reference",
        {
            "peak_rate": 100,
            "capacity_rate": 40,
            "formula": "post_control_rate = peak_rate * (1 - tlr_percent/100)",
            "tlr_percent": 60,
            "post_control_rate": 40,
        },
    ),
    CalibrationCase(
        "t8",
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
        "t8",
        "weak_partial",
        {
            "deferred_volume": 3000,
            "capacity_rate": 80,
            "backoff_min": 0,
            "backoff_max": 100,
            "expected_retry_rate": 30,
        },
    ),
    CalibrationCase(
        "t8",
        "mid_partial",
        {
            "deferred_volume": 6000,
            "capacity_rate": 40,
            "backoff_min": 0,
            "backoff_max": 200,
            "expected_retry_rate": 10,
        },
    ),
    CalibrationCase(
        "t8",
        "strong_partial",
        {
            "deferred_volume": 6000,
            "capacity_rate": 40,
            "backoff_min": 0,
            "backoff_max": 100,
            "expected_retry_rate": 60,
        },
    ),
    CalibrationCase(
        "t8",
        "reference",
        {
            "deferred_volume": 6000,
            "capacity_rate": 40,
            "backoff_min": 0,
            "backoff_max": 150,
            "expected_retry_rate": 40,
        },
    ),
    CalibrationCase(
        "t9",
        "bad",
        {
            "given_tlr_percent": 10,
            "peak_rate": 0,
            "capacity_rate": 0,
            "residual_rate": 0,
            "verdict": "sufficient",
            "evidence": "works",
        },
    ),
    CalibrationCase("t9", "weak_partial", {"verdict": "insufficient"}),
    CalibrationCase(
        "t9",
        "mid_partial",
        {
            "given_tlr_percent": 10,
            "peak_rate": 100,
            "capacity_rate": 40,
            "residual_rate": 90,
            "verdict": "this holds the load fine",
            "evidence": "TLR residual load remains above capacity.",
        },
    ),
    CalibrationCase(
        "t9",
        "strong_partial",
        {
            "given_tlr_percent": 10,
            "peak_rate": 100,
            "capacity_rate": 40,
            "residual_rate": 50,
            "verdict": "ineffective",
            "evidence": "TLR residual load still exceeds capacity.",
        },
    ),
    CalibrationCase(
        "t9",
        "reference",
        {
            "given_tlr_percent": 10,
            "peak_rate": 100,
            "capacity_rate": 40,
            "residual_rate": 90,
            "verdict": "the proposed setting is ineffective",
            "evidence": "10% TLR leaves residual load 90 above capacity 40.",
        },
    ),
    CalibrationCase(
        "t10",
        "bad",
        {
            "peak_rate": 100,
            "deficit": 6000,
            "recommendation": "apply traffic load reduction now",
            "evidence": "storm",
        },
    ),
    CalibrationCase(
        "t10", "weak_partial", {"recommendation": "no flow control required"}
    ),
    CalibrationCase(
        "t10",
        "mid_partial",
        {
            "deficit": 0,
            "recommendation": "",
            "evidence": "idle below threshold with no deficit",
        },
    ),
    CalibrationCase(
        "t10",
        "strong_partial",
        {
            "peak_rate": 0,
            "recommendation": "no flow control needed",
            "evidence": "",
        },
    ),
    CalibrationCase(
        "t10",
        "reference",
        {
            "peak_rate": 0,
            "deficit": 0,
            "recommendation": "no flow control needed",
            "evidence": "idle baseline below threshold with no deficit",
        },
    ),
)


def _record_for(kind: str) -> dict[str, Any]:
    if kind == "t9":
        return T9_REC
    if kind == "t10":
        return BASELINE_REC
    return STORM_REC


def _live_for(kind: str) -> LiveState:
    return IDLE_LIVE if kind == "t10" else STORM_LIVE


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
            _record_for(case.kind),
            _live_for(case.kind),
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
