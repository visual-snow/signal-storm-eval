"""Rescore saved signal-storm logs with the current product scorer.

The saved `logs/p5` and `logs/p5b` trajectories predate product prompts and
numeric scoring. Their legacy scorer explanations still contain the live values
used at grade time, so this report reconstructs a `LiveState` from those
references and runs the current pure `decide()` scorer over each saved
completion. It does not start docker services or model calls.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from signal_storm_bench.scorers import LiveState, decide

KIND_ORDER = tuple(f"t{i}" for i in range(1, 11))
DEFAULT_INPUTS = ("logs/p5", "logs/p5b")
DEFAULT_OUTPUT = Path("docs/saved-log-product-calibration.md")

REFERENCE_RE = re.compile(
    r"\b(?P<name>live_count|live_peak_rate|capacity_rate|rejected_volume|"
    r"baseline_peak_rate)=(?P<value>-?\d+(?:\.\d+)?)"
)
REQUIRED_REFERENCE_FIELDS = {
    "t1": ("live_count",),
    "t2": ("live_peak_rate",),
    "t3": ("live_count", "rejected_volume"),
    "t4": ("live_peak_rate", "rejected_volume"),
    "t5": (),
    "t6": (),
    "t7": ("live_peak_rate", "capacity_rate"),
    "t8": ("rejected_volume", "capacity_rate"),
    "t9": ("live_peak_rate", "capacity_rate"),
    "t10": ("baseline_peak_rate",),
}


@dataclass(frozen=True)
class LiveReferences:
    live_count: float | None = None
    live_peak_rate: float | None = None
    capacity_rate: float | None = None
    rejected_volume: float | None = None
    baseline_peak_rate: float | None = None


@dataclass(frozen=True)
class ScoredSavedSample:
    log_name: str
    model: str
    sample_id: str
    kind: str
    score: float
    components: dict[str, float]
    legacy_value: str


@dataclass(frozen=True)
class TaskSummary:
    kind: str
    case_count: int
    minimum: float
    maximum: float
    average: float
    spread: float
    distinct_scores: int


def parse_references(explanation: str) -> LiveReferences:
    values: dict[str, float] = {}
    for match in REFERENCE_RE.finditer(explanation):
        values[match.group("name")] = float(match.group("value"))
    return LiveReferences(**values)


def _merge_references(*references: LiveReferences) -> LiveReferences:
    values: dict[str, float | None] = {
        "live_count": None,
        "live_peak_rate": None,
        "capacity_rate": None,
        "rejected_volume": None,
        "baseline_peak_rate": None,
    }
    for refs in references:
        for field in values:
            value = getattr(refs, field)
            if value is not None:
                values[field] = value
    return LiveReferences(**values)


def missing_required_references(kind: str, references: LiveReferences) -> list[str]:
    fields = REQUIRED_REFERENCE_FIELDS.get(kind)
    if fields is None:
        raise ValueError(f"unknown task kind: {kind}")
    return [field for field in fields if getattr(references, field) is None]


def _require(kind: str, references: LiveReferences) -> None:
    missing = missing_required_references(kind, references)
    if missing:
        raise ValueError(
            f"missing required live references for {kind}: {', '.join(missing)}"
        )


def _live_state_for(kind: str, references: LiveReferences) -> LiveState:
    _require(kind, references)
    if kind == "t1":
        return LiveState(live_count=float(references.live_count))
    if kind == "t2":
        return LiveState(live_peak_rate=float(references.live_peak_rate))
    if kind == "t3":
        return LiveState(
            live_count=float(references.live_count),
            rejected_volume=float(references.rejected_volume),
        )
    if kind == "t4":
        return LiveState(
            live_peak_rate=float(references.live_peak_rate),
            rejected_volume=float(references.rejected_volume),
        )
    if kind in ("t5", "t6"):
        return LiveState()
    if kind in ("t7", "t9"):
        return LiveState(
            live_peak_rate=float(references.live_peak_rate),
            capacity_rate=float(references.capacity_rate),
        )
    if kind == "t8":
        return LiveState(
            rejected_volume=float(references.rejected_volume),
            capacity_rate=float(references.capacity_rate),
        )
    if kind == "t10":
        return LiveState(
            baseline_peak_rate=float(references.baseline_peak_rate),
            rejected_volume=float(references.rejected_volume or 0.0),
        )
    raise ValueError(f"unknown task kind: {kind}")


def _components(metadata: dict[str, Any] | None) -> dict[str, float]:
    raw = (metadata or {}).get("components", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in raw.items()
        if isinstance(value, int | float)
    }


def rescore_legacy_completion(
    *,
    log_name: str,
    model: str,
    sample_id: str,
    kind: str,
    completion: str,
    metadata: dict[str, Any],
    references: LiveReferences,
    legacy_value: object | None = None,
) -> ScoredSavedSample:
    score = decide(kind, completion, metadata, _live_state_for(kind, references))
    return ScoredSavedSample(
        log_name=log_name,
        model=model,
        sample_id=sample_id,
        kind=kind,
        score=float(score.value),
        components=_components(score.metadata),
        legacy_value="" if legacy_value is None else str(legacy_value),
    )


def _legacy_score(sample: Any) -> Any:
    return next(iter(sample.scores.values()))


def _log_references(samples: list[Any]) -> LiveReferences:
    refs = LiveReferences()
    for sample in samples:
        legacy_score = _legacy_score(sample)
        refs = _merge_references(refs, parse_references(legacy_score.explanation))
    return refs


def load_scored_samples(input_names: list[str]) -> list[ScoredSavedSample]:
    from inspect_ai.log import list_eval_logs, read_eval_log

    rows: list[ScoredSavedSample] = []
    for input_name in input_names:
        for info in list_eval_logs(input_name):
            log = read_eval_log(info.name)
            if log.status != "success":
                continue
            samples = log.samples
            log_refs = _log_references(samples)
            for sample in samples:
                legacy_score = _legacy_score(sample)
                sample_refs = _merge_references(
                    log_refs, parse_references(legacy_score.explanation)
                )
                kind = sample.metadata["task_kind"]
                if missing_required_references(kind, sample_refs):
                    continue
                rows.append(
                    rescore_legacy_completion(
                        log_name=Path(info.name).name,
                        model=log.eval.model,
                        sample_id=str(sample.id),
                        kind=kind,
                        completion=sample.output.completion,
                        metadata=sample.metadata,
                        references=sample_refs,
                        legacy_value=legacy_score.value,
                    )
                )
    return rows


def summarize(rows: list[ScoredSavedSample]) -> list[TaskSummary]:
    by_kind: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_kind[row.kind].append(row.score)

    ordered_kinds = [kind for kind in KIND_ORDER if kind in by_kind]
    ordered_kinds.extend(sorted(kind for kind in by_kind if kind not in KIND_ORDER))

    summaries = []
    for kind in ordered_kinds:
        scores = by_kind[kind]
        summaries.append(
            TaskSummary(
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


def render_report(rows: list[ScoredSavedSample], input_names: list[str]) -> str:
    lines = [
        "# Saved Log Product Calibration",
        "",
        "Generated from `scripts/generate_saved_log_calibration_report.py` using "
        f"saved successful Inspect logs from {', '.join(input_names)}. This does "
        "not start docker services or model calls.",
        "",
        "These trajectories predate the product prompts, so this is calibration "
        "evidence from available saved outputs rescored with the current product "
        "scorer. It is not a substitute for a fresh product-prompt roster run.",
        "",
        "## Per-task Distributions",
        "",
        "| Task | Samples | Min | Max | Mean | Spread | Distinct scores |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summarize(rows):
        lines.append(
            f"| {summary.kind} | {summary.case_count} | {summary.minimum:.3f} | "
            f"{summary.maximum:.3f} | {summary.average:.3f} | "
            f"{summary.spread:.3f} | {summary.distinct_scores} |"
        )

    lines.extend(
        [
            "",
            "## Per-sample Scores",
            "",
            "| Task | Model | Sample | Score | Legacy | Components |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for row in sorted(rows, key=lambda item: (item.kind, item.model, item.sample_id)):
        lines.append(
            f"| {row.kind} | {row.model} | {row.sample_id} | {row.score:.3f} | "
            f"{row.legacy_value} | {_component_text(row.components)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Infrastructure-error logs are not included; only successful saved logs are rescored.",
            "- Saved samples that lack required live references in legacy explanations are omitted.",
            "- Low scores can reflect the old prompt schema as well as model weakness.",
            "- Fresh product-scored smoke and roster calibration remain required before claiming live model calibration.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    output = Path(args[0]) if args else DEFAULT_OUTPUT
    input_names = args[1:] or list(DEFAULT_INPUTS)
    rows = load_scored_samples(input_names)
    if not rows:
        raise ValueError(
            f"no successful saved samples found in {', '.join(input_names)}"
        )
    output.write_text(render_report(rows, input_names))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
