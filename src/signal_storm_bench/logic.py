"""Pure scoring logic. No sandbox access; fully unit-testable (P4).

The parsing and comparison helpers the scorer needs: extract a JSON submission
format-tolerantly, normalise verdicts, and the per-task numeric/set/enum checks
the scorer grades against live counters and the normative bounds. Kept free of
sandbox access so the whole grading surface unit-tests without docker.

Grading is outcome-only: ground truth lives in scorer-side metadata and live
probes, never here. Unparseable submissions yield None and never raise; verdict
helpers are tristate so an unclear submission (None) never scores correct.
"""

import json
import re
from collections.abc import Iterable, Mapping

# TS 38.413 Traffic Load Reduction Indication is an integer percent in 1..99.
_TLR_MIN = 1
_TLR_MAX = 99


def parse_submission(text: str) -> dict | None:
    """Pull a JSON object out of a submission; None when none can be parsed.

    Tries a fenced ```json block first, then the widest brace span. Keys are
    lowercased for tolerant lookups; values are left intact so list-valued
    fields (t5 "mechanisms") and numeric fields (t1 "count", t7 "tlr_percent")
    survive. Never raises.
    """
    candidate = text
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            candidate = brace.group(0)
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict):
        return {str(k).lower(): v for k, v in parsed.items()}
    return None


def normalize_verdict(s: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for verdict match."""
    lowered = str(s).lower()
    stripped = re.sub(r"[^a-z0-9 ]", " ", lowered)
    return re.sub(r"\s+", " ", stripped).strip()


def numeric_within(value: float, ref: float, rel_tol: float) -> bool:
    """t1/t2/t3: True when value is within rel_tol (fraction) of ref.

    Tolerance is relative to |ref|; when ref is zero, only an exact zero passes.
    """
    if ref == 0:
        return value == 0
    return abs(value - ref) <= abs(ref) * rel_tol


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None


def numeric_score(value: object, reference: float, error_scale: float) -> float:
    parsed = as_float(value)
    if parsed is None or error_scale <= 0:
        return 0.0
    return clamp01(1.0 - abs(parsed - reference) / error_scale)


def set_equal_normalized(
    answer_set: list[str] | set[str], expected_set: list[str] | set[str]
) -> bool:
    """t5: True when the normalised answer set equals the normalised expected set."""
    a = {normalize_verdict(x) for x in answer_set}
    b = {normalize_verdict(x) for x in expected_set}
    return a == b


def set_f1_score(answer: Iterable[object], expected: Iterable[object]) -> float:
    answer_set = {normalize_verdict(str(x)) for x in answer if str(x).strip()}
    expected_set = {normalize_verdict(str(x)) for x in expected if str(x).strip()}
    if not answer_set and not expected_set:
        return 1.0
    if not answer_set or not expected_set:
        return 0.0
    true_pos = len(answer_set & expected_set)
    precision = true_pos / len(answer_set)
    recall = true_pos / len(expected_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def term_coverage(text: object, required_terms: set[str]) -> float:
    if not required_terms:
        return 1.0
    normalized = normalize_verdict(str(text))
    hits = sum(1 for term in required_terms if normalize_verdict(term) in normalized)
    return hits / len(required_terms)


def component_average(
    components: Mapping[str, float], weights: Mapping[str, float]
) -> float:
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    total = sum(
        clamp01(components.get(name, 0.0)) * weight for name, weight in weights.items()
    )
    return clamp01(total / total_weight)


def enum_match(answer: str, enum_value: str) -> bool:
    """t6: format-tolerant equality of a single enum action (lowercase+strip)."""
    return normalize_verdict(answer) == normalize_verdict(enum_value)


def tlr_holds(tlr: float, live_peak_rate: float, capacity_rate: float) -> bool:
    """t7: a Traffic Load Reduction percent that holds the live load to target.

    Valid range 1..99 AND the reduced peak rate stays within capacity.
    """
    if not _TLR_MIN <= tlr <= _TLR_MAX:
        return False
    return live_peak_rate * (1 - tlr / 100) <= capacity_rate


def backoff_ok(
    bmin: float, bmax: float, rejected_volume: float, capacity_rate: float
) -> bool:
    """t8: a NAS back-off range that disperses the deferred retries.

    Spread must be positive AND the deferred volume, spread over the window,
    must arrive at a rate the AMF can absorb.
    """
    spread = bmax - bmin
    if spread <= 0:
        return False
    return rejected_volume / spread <= capacity_rate


def verdict_in(synonyms: set[str], text: str) -> bool | None:
    """t9/t10 tristate: True if a synonym is present, None when the verdict is unclear.

    Reads the submission "verdict" field; True when any normalised synonym is a
    substring, otherwise None (an unclear verdict must never score correct, so a
    content-free submission cannot win by accidentally matching the live probe).
    """
    parsed = parse_submission(text)
    if parsed is None:
        return None
    verdict = parsed.get("verdict")
    if verdict is None:
        return None
    normalized = normalize_verdict(verdict)
    if not normalized:
        return None
    for synonym in synonyms:
        if normalize_verdict(synonym) in normalized:
            return True
    return None
