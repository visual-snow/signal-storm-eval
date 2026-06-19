"""pass^k: the reliability headline for this suite.

O&M repair is a reliability use case: an operator cares whether the agent
fixes the fault every time, not at least once. pass^k for a sample with c
correct epochs out of n is the unbiased without-replacement estimator
C(c, k) / C(n, k); the suite value is the mean over samples.

Usage: python scripts/pass_hat_k.py logs/iter-2
"""

import sys
from math import comb

PASS_THRESHOLD = 0.8


def is_pass_value(value: object, threshold: float = PASS_THRESHOLD) -> bool:
    if value == "C":
        return True
    if value == "I":
        return False
    if isinstance(value, int | float):
        return float(value) >= threshold
    return False


def pass_hat_k(counts: dict[str, tuple[int, int]], k: int) -> float:
    """Mean over samples of C(c, k)/C(n, k).

    Args:
        counts: sample id -> (correct epochs c, total epochs n)
        k: required consecutive-success count; must satisfy k <= n
    """
    if not counts:
        raise ValueError("no samples")
    total = 0.0
    for sample_id, (c, n) in counts.items():
        if k > n:
            raise ValueError(f"k={k} exceeds epochs n={n} for sample {sample_id}")
        total += comb(c, k) / comb(n, k)
    return total / len(counts)


def collect_counts(log_dir: str) -> dict[str, dict[str, tuple[int, int]]]:
    """Per model: sample id -> (correct epochs, total epochs)."""
    from collections import defaultdict

    from inspect_ai.log import list_eval_logs, read_eval_log

    by_model: dict[str, dict[str, tuple[int, int]]] = {}
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info.name)
        if log.status != "success":
            print(f"WARN: skipping {info.name} (status={log.status})")
            continue
        tally: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for smp in log.samples or []:
            if smp.error:
                continue
            value = next(iter(smp.scores.values())).value if smp.scores else "I"
            tally[str(smp.id)][1] += 1
            if is_pass_value(value):
                tally[str(smp.id)][0] += 1
        by_model[log.eval.model] = {
            sid: (c, n) for sid, (c, n) in tally.items() if n > 0
        }
    return by_model


def main() -> int:
    log_dir = sys.argv[1]
    by_model = collect_counts(log_dir)
    for model, counts in sorted(by_model.items()):
        n_epochs = min(n for _, n in counts.values())
        ks = [k for k in (1, 2, 3, 5) if k <= n_epochs]
        cells = "  ".join(f"pass^{k}={pass_hat_k(counts, k):.3f}" for k in ks)
        print(f"{model:55} {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
