"""Per-kind differentiation gate.

The suite-level gate (check_differentiation.py) asks whether the roster spreads
on the whole-suite mean. This asks the same of one task kind at a time: a kind
"differentiates" when its per-model mean spans >= 0.25 best-to-worst across at
least three bands (gaps > 0.05). Use it to verify that t1 and t6, in isolation,
stopped returning one constant number for every model.

Usage:
    python scripts/check_kind_differentiation.py logs/<dir> [t1,t6]
"""

import sys
from collections import defaultdict

from signal_storm_bench.config import (
    DIFF_BAND_GAP,
    DIFF_BANDS_REQUIRED,
    DIFF_SPREAD_MIN,
)


def _numeric(value: object) -> float:
    """Map a Score value to [0, 1]; legacy C/I logs remain readable."""
    if isinstance(value, (int, float)):
        return float(value)
    if value == "C":
        return 1.0
    if value == "I":
        return 0.0
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def per_kind_means(log_dir: str) -> dict[str, dict[str, float]]:
    from inspect_ai.log import list_eval_logs, read_eval_log

    raw: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info.name)
        if log.status != "success":
            print(f"WARN: skipping {info.name} (status={log.status})")
            continue
        for sample in log.samples or []:
            kind = sample.metadata.get("task_kind")
            if not sample.scores or kind is None:
                continue
            value = next(iter(sample.scores.values())).value
            raw[log.eval.model][kind].append(_numeric(value))
    return {
        model: {kind: sum(xs) / len(xs) for kind, xs in kinds.items()}
        for model, kinds in raw.items()
    }


def differentiated(means: list[float]) -> tuple[bool, float, int]:
    values = sorted(means)
    spread = values[-1] - values[0] if values else 0.0
    bands = 1
    for prev, cur in zip(values, values[1:]):
        if cur - prev > DIFF_BAND_GAP:
            bands += 1
    ok = bool(values) and spread >= DIFF_SPREAD_MIN and bands >= DIFF_BANDS_REQUIRED
    return ok, spread, bands


def main() -> int:
    log_dir = sys.argv[1]
    wanted = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    data = per_kind_means(log_dir)
    if not data:
        print("no successful logs found")
        return 1
    kinds = wanted or sorted({k for m in data.values() for k in m})
    models = sorted(data)

    print(f"{'model':48} " + " ".join(f"{k:>6}" for k in kinds))
    columns: dict[str, list[float]] = defaultdict(list)
    for model in models:
        cells = []
        for kind in kinds:
            mean = data[model].get(kind)
            if mean is not None:
                columns[kind].append(mean)
                cells.append(f"{mean:6.2f}")
            else:
                cells.append("   -- ")
        print(f"{model:48} " + " ".join(cells))

    print()
    all_pass = True
    for kind in kinds:
        ok, spread, bands = differentiated(columns[kind])
        all_pass = all_pass and ok
        print(
            f"{kind}: spread={spread:.3f} bands={bands} "
            f"-> {'PASS' if ok else 'FAIL'} (need spread>={DIFF_SPREAD_MIN}, bands>={DIFF_BANDS_REQUIRED})"
        )
    print("\n" + ("PASS: all requested kinds differentiate" if all_pass else "FAIL"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
