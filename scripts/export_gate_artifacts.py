"""Export run summary and sampled transcripts for the eval-reviewer gate.

The reviewer is hermetic (Read/Grep/Glob only), so everything it judges must
exist as plain files. Writes to gate_exports/iter-<n>/:
  summary.md                    per-model means, errors, epochs
  transcripts/<model>__<sample>__epoch<k>.md   sampled transcripts

Usage: python scripts/export_gate_artifacts.py logs/iter-1 gate_exports/iter-1
"""

import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log

# Sampling policy: per model, export one scored model-output transcript per kind,
# preferring low scores when available. Infrastructure/sample errors stay in the
# run summary; they are not sampled as model failures.
PER_MODEL_CAP = 4
PRODUCT_PASS_THRESHOLD = 0.8


def _short_model(model: str) -> str:
    return model.split("/")[-1]


def _render_sample(sample, model: str) -> str:
    lines = [
        f"# Transcript: {sample.id} (epoch {sample.epoch})",
        f"model: {model}",
        f"score: {sample.scores}",
        "",
    ]
    if sample.error:
        lines.append(f"SAMPLE ERROR: {sample.error.message}")
        lines.append("")
    for msg in sample.messages:
        role = msg.role
        content = msg.text if hasattr(msg, "text") else str(msg.content)
        lines.append(f"## {role}")
        lines.append(content or "(empty)")
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                lines.append(f"[tool call] {tc.function}({tc.arguments})")
        lines.append("")
    return "\n".join(lines)


def _numeric_value(value: object) -> float:
    if value == "C":
        return 1.0
    if value == "I":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def is_low_score(value: object, threshold: float = PRODUCT_PASS_THRESHOLD) -> bool:
    if value == "C":
        return False
    if value == "I":
        return True
    try:
        return float(value) < threshold
    except (TypeError, ValueError):
        return True


def _metric_value(metrics: dict) -> float | None:
    for name in ("mean", "accuracy"):
        if name in metrics:
            return metrics[name].value
    return None


def _score_value(sample) -> object | None:
    if not sample.scores:
        return None
    return next(iter(sample.scores.values())).value


def select_transcript_sample(samples: list) -> object | None:
    scored_samples = [sample for sample in samples if not sample.error]
    if not scored_samples:
        return None
    return next(
        (
            sample
            for sample in scored_samples
            if (value := _score_value(sample)) is not None and is_low_score(value)
        ),
        scored_samples[0],
    )


def export(log_dir: str, out_dir: str) -> None:
    out = Path(out_dir)
    (out / "transcripts").mkdir(parents=True, exist_ok=True)

    def _numeric(s) -> float:
        value = _score_value(s)
        if value is None:
            return float("nan")
        return _numeric_value(value)

    kinds = [f"t{i}" for i in range(1, 11)]
    summary_rows = []
    perkind_rows = []
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info.name)
        model = log.eval.model
        suite_score = None
        if log.results:
            for eval_score in log.results.scores:
                value = _metric_value(eval_score.metrics)
                if value is not None:
                    suite_score = value
                    break
        n_samples = len(log.samples or [])
        n_errors = sum(1 for smp in (log.samples or []) if smp.error)
        epochs = log.eval.config.epochs or 1
        summary_rows.append(
            f"| {model} | {log.status} | "
            f"{'n/a' if suite_score is None else f'{suite_score:.3f}'} | "
            f"{n_samples} | {n_errors} | {epochs} |"
        )

        # Stratify by task kind so the reviewer sees every kind (especially
        # the hard t5/t6/t7/t8), then prefer failures within each kind for the
        # fairness check. One epoch per (kind) per model keeps the set small.
        by_kind: dict[str, list] = defaultdict(list)
        for s in log.samples or []:
            kind = str(s.id).split("-")[0]
            by_kind[kind].append(s)

        # Per-kind mean (over all epochs/samples) so the reviewer can verify
        # the difficulty-spread row without re-running anything.
        means = {}
        for k in by_kind:
            scored = [
                s for s in by_kind[k] if not s.error and _score_value(s) is not None
            ]
            if scored:
                means[k] = sum(_numeric(s) for s in scored) / len(scored)
        cells = " | ".join(f"{means.get(k, float('nan')):.2f}" for k in kinds)
        perkind_rows.append(f"| {_short_model(model)} | {cells} |")

        for kind in sorted(by_kind):
            samples = by_kind[kind]
            chosen = select_transcript_sample(samples)
            if chosen is None:
                continue
            name = f"{_short_model(model)}__{chosen.id}__epoch{chosen.epoch}.md"
            (out / "transcripts" / name).write_text(_render_sample(chosen, model))

    perkind_header = "| model | " + " | ".join(kinds) + " |\n"
    perkind_sep = "|---|" + "---|" * len(kinds) + "\n"
    (out / "summary.md").write_text(
        "# Run summary\n\n"
        f"source: {log_dir}\n\n"
        "| model | status | score | samples | errors | epochs |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(summary_rows) + "\n\n"
        "## Per-kind means (all epochs)\n\n"
        + perkind_header
        + perkind_sep
        + "\n".join(perkind_rows)
        + "\n"
    )
    n_transcripts = len(list((out / "transcripts").glob("*.md")))
    print(f"exported {len(summary_rows)} runs, {n_transcripts} transcripts -> {out}")


if __name__ == "__main__":
    export(sys.argv[1], sys.argv[2])
