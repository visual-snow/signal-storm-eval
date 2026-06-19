"""Differentiation gate from the design spec.

Spread >= 0.25 between best and worst suite means, and at least three means
pairwise separated by > 0.05.

Usage: python scripts/check_differentiation.py logs/iter-1
"""

import sys

SPREAD_MIN = 0.25
BAND_GAP = 0.05
BANDS_REQUIRED = 3
ROSTER_SIZE = 5


def differentiated(means: dict[str, float]) -> bool:
    values = sorted(means.values())
    if not values or values[-1] - values[0] < SPREAD_MIN:
        return False
    # greedy band count: walk sorted means, new band when gap > BAND_GAP
    bands = 1
    for prev, cur in zip(values, values[1:]):
        if cur - prev > BAND_GAP:
            bands += 1
    return bands >= BANDS_REQUIRED


def collect_means(log_dir: str) -> dict[str, float]:
    from inspect_ai.log import list_eval_logs, read_eval_log

    means: dict[str, float] = {}
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info.name, header_only=True)
        if log.status != "success" or not log.results:
            print(f"WARN: skipping {info.name} (status={log.status})")
            continue
        accuracy = next(
            (
                m.value
                for s in log.results.scores
                for name, m in s.metrics.items()
                if name == "accuracy"
            ),
            None,
        )
        if accuracy is not None:
            means[log.eval.model] = accuracy
    return means


def main() -> int:
    log_dir = sys.argv[1]
    means = collect_means(log_dir)
    print(f"{'model':55} mean")
    for model, mean in sorted(means.items(), key=lambda kv: -kv[1]):
        print(f"{model:55} {mean:.3f}")
    if len(means) < ROSTER_SIZE:
        print(
            f"\nFAIL: only {len(means)} of {ROSTER_SIZE} models produced a successful run"
        )
        return 1
    if differentiated(means):
        print("\nPASS: differentiation criteria met")
        return 0
    print("\nFAIL: scores do not differentiate (spread/bands)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
