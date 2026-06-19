"""Pure scoring logic. No sandbox access; fully unit-testable (P4).

The parsing and comparison helpers the scorer composes: pull a JSON submission
out of free text, normalise verdicts, score a number against a live reference,
match verdict phrases, and the small numeric rules (TLR holds, residual rate).
Kept free of sandbox access so the whole grading surface unit-tests without
docker.

Grading is outcome-only: ground truth lives in scorer-side metadata and live
probes, never here. Unparseable submissions yield None and never raise.
"""

import json
import re
from collections.abc import Iterable

from signal_storm_bench.config import TLR_MAX, TLR_MIN


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
    if not isinstance(parsed, dict):
        return None
    return {str(key).lower(): value for key, value in parsed.items()}


def normalize_verdict(s: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for verdict match."""
    lowered = str(s).lower()
    stripped = re.sub(r"[^a-z0-9 ]", " ", lowered)
    return re.sub(r"\s+", " ", stripped).strip()


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
    """Graded closeness in 0..1: 1.0 at the reference, fading to 0 by error_scale."""
    parsed = as_float(value)
    if parsed is None or error_scale <= 0:
        return 0.0
    return clamp01(1.0 - abs(parsed - reference) / error_scale)


def rel_scale(reference: float, fraction: float) -> float:
    """The error scale for a relative-tolerance measurement.

    A fraction of the reference, but never below 1.0 so the tolerance cannot
    collapse to zero on a tiny reference.
    """
    return max(abs(reference) * fraction, 1.0)


def measure(value: object, reference: float, tolerance_fraction: float = 0.25) -> float:
    """Score a submitted number against a live reference with relative tolerance.

    The grader's workhorse: full credit at the reference, fading out over
    tolerance_fraction of it. This is just numeric_score with the relative error
    scale, named so each grader reads as one line.
    """
    return numeric_score(value, reference, rel_scale(reference, tolerance_fraction))


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


def contains_normalized_phrase(text: object, phrase: str) -> bool:
    normalized_text = normalize_verdict(str(text))
    normalized_phrase = normalize_verdict(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    pattern = rf"(^| ){re.escape(normalized_phrase)}( |$)"
    return re.search(pattern, normalized_text) is not None


def matches_any_phrase(text: object, phrases: Iterable[str]) -> bool:
    """True when any phrase appears in text as a whole-token phrase.

    The shared verdict matcher: t4/t9/t10 all ask "does the model's wording
    contain one of these judgment phrases?". Empty text matches nothing.
    """
    normalized = normalize_verdict(str(text))
    if not normalized:
        return False
    return any(contains_normalized_phrase(normalized, phrase) for phrase in phrases)


def term_coverage(text: object, required_terms: set[str]) -> float:
    if not required_terms:
        return 1.0
    hits = sum(1 for term in required_terms if contains_normalized_phrase(text, term))
    return hits / len(required_terms)


def component_average(components: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    total = sum(
        clamp01(components.get(name, 0.0)) * weight for name, weight in weights.items()
    )
    return clamp01(total / total_weight)


def residual_rate(peak_rate: float, tlr_percent: float) -> float:
    """The load left after a Traffic Load Reduction of tlr_percent."""
    return peak_rate * (1 - tlr_percent / 100)


def tlr_holds(tlr: float, live_peak_rate: float, capacity_rate: float) -> bool:
    """t7: a Traffic Load Reduction percent that holds the live load to target.

    Valid range 1..99 AND the reduced peak rate stays within capacity.
    """
    if not TLR_MIN <= tlr <= TLR_MAX:
        return False
    return residual_rate(live_peak_rate, tlr) <= capacity_rate


def parse_judge_grade(text: str) -> str | None:
    """Pull the single verdict token out of a judge reply (`GRADE: <token>`).

    Returns the lowercased token (e.g. "storm", "normal", "unknown") or None when
    the reply carries no GRADE line. Ignores a `grade:` substring inside a larger
    word, so prose like "downgrade: to normal" does not false-positive. Pure;
    never raises.
    """
    match = re.search(r"(?<!\w)grade:\s*([a-z]+)", str(text), re.IGNORECASE)
    return match.group(1).lower() if match else None


def controlled_set_score(
    answer: Iterable[object],
    expected: Iterable[str],
    unsafe: Iterable[str] = (),
) -> float:
    """Recall of an expected term set, zeroed if any unsafe term is included.

    Used for i3 traffic classes: full credit for naming the protected/rejected
    classes, but an unsafe over-broad class (e.g. rejecting emergency traffic)
    voids the component. Phrase-boundary matching via term_coverage.
    """
    answer_text = " ".join(str(x) for x in answer)
    if any(contains_normalized_phrase(answer_text, term) for term in unsafe):
        return 0.0
    return term_coverage(answer_text, set(expected))
