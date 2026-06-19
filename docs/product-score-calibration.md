# Product Score Calibration

Generated from `scripts/generate_product_calibration_report.py` using synthetic scorer inputs only; no docker services or model calls are started. This is scorer-anchor calibration, not a replacement for the paused model-roster calibration.

## Per-task Distributions

| Task | Cases | Min | Max | Mean | Spread | Distinct scores | Anchor scores |
|---|---:|---:|---:|---:|---:|---:|---|
| t1 | 5 | 0.000 | 1.000 | 0.525 | 1.000 | 5 | bad=0.000, weak_partial=0.250, mid_partial=0.625, strong_partial=0.750, reference=1.000 |
| t2 | 5 | 0.000 | 1.000 | 0.575 | 1.000 | 5 | bad=0.000, weak_partial=0.400, mid_partial=0.700, strong_partial=0.775, reference=1.000 |
| t3 | 5 | 0.050 | 1.000 | 0.613 | 0.950 | 5 | bad=0.050, weak_partial=0.450, mid_partial=0.667, strong_partial=0.900, reference=1.000 |
| t4 | 5 | 0.000 | 1.000 | 0.511 | 1.000 | 5 | bad=0.000, weak_partial=0.300, mid_partial=0.593, strong_partial=0.662, reference=1.000 |
| t5 | 5 | 0.000 | 1.000 | 0.623 | 1.000 | 5 | bad=0.000, weak_partial=0.450, mid_partial=0.817, strong_partial=0.850, reference=1.000 |
| t6 | 5 | 0.062 | 1.000 | 0.400 | 0.938 | 5 | bad=0.062, weak_partial=0.188, mid_partial=0.250, strong_partial=0.500, reference=1.000 |
| t7 | 5 | 0.150 | 1.000 | 0.753 | 0.850 | 5 | bad=0.150, weak_partial=0.800, mid_partial=0.840, strong_partial=0.975, reference=1.000 |
| t8 | 5 | 0.000 | 1.000 | 0.663 | 1.000 | 5 | bad=0.000, weak_partial=0.600, mid_partial=0.800, strong_partial=0.917, reference=1.000 |
| t9 | 5 | 0.050 | 1.000 | 0.560 | 0.950 | 5 | bad=0.050, weak_partial=0.300, mid_partial=0.700, strong_partial=0.750, reference=1.000 |
| t10 | 5 | 0.000 | 1.000 | 0.460 | 1.000 | 5 | bad=0.000, weak_partial=0.300, mid_partial=0.350, strong_partial=0.650, reference=1.000 |

## Component Scores

| Task | Anchor | Score | Components |
|---|---|---:|---|
| t1 | bad | 0.000 | request_count=0.00, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | weak_partial | 0.250 | request_count=0.00, source_signal=1.00, unit=1.00, window=1.00 |
| t1 | mid_partial | 0.625 | request_count=0.50, source_signal=1.00, unit=1.00, window=1.00 |
| t1 | strong_partial | 0.750 | request_count=1.00, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | reference | 1.000 | request_count=1.00, source_signal=1.00, unit=1.00, window=1.00 |
| t2 | bad | 0.000 | peak_rate=0.00, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | weak_partial | 0.400 | peak_rate=0.20, rate_window=1.00, source_signal=1.00, unit=1.00 |
| t2 | mid_partial | 0.700 | peak_rate=0.60, rate_window=1.00, source_signal=1.00, unit=1.00 |
| t2 | strong_partial | 0.775 | peak_rate=1.00, rate_window=0.00, source_signal=0.25, unit=0.00 |
| t2 | reference | 1.000 | peak_rate=1.00, rate_window=1.00, source_signal=1.00, unit=1.00 |
| t3 | bad | 0.050 | arithmetic_consistency=1.00, deficit=0.00, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | weak_partial | 0.450 | arithmetic_consistency=0.00, deficit=1.00, request_count=0.00, success_count=0.00, unit=1.00 |
| t3 | mid_partial | 0.667 | arithmetic_consistency=0.17, deficit=0.17, request_count=1.00, success_count=1.00, unit=1.00 |
| t3 | strong_partial | 0.900 | arithmetic_consistency=1.00, deficit=1.00, request_count=1.00, success_count=1.00, unit=0.00 |
| t3 | reference | 1.000 | arithmetic_consistency=1.00, deficit=1.00, request_count=1.00, success_count=1.00, unit=1.00 |
| t4 | bad | 0.000 | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=0.00 |
| t4 | weak_partial | 0.300 | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | mid_partial | 0.593 | deficit_evidence=0.00, evidence_text=0.75, peak_evidence=0.60, verdict=1.00 |
| t4 | strong_partial | 0.662 | deficit_evidence=1.00, evidence_text=0.75, peak_evidence=1.00, verdict=0.00 |
| t4 | reference | 1.000 | deficit_evidence=1.00, evidence_text=1.00, peak_evidence=1.00, verdict=1.00 |
| t5 | bad | 0.000 | excluded_distractor=0.00, no_unsafe_selected_distractor=0.00, rationale=0.00, selected_mechanisms=0.00 |
| t5 | weak_partial | 0.450 | excluded_distractor=1.00, no_unsafe_selected_distractor=1.00, rationale=1.00, selected_mechanisms=0.00 |
| t5 | mid_partial | 0.817 | excluded_distractor=1.00, no_unsafe_selected_distractor=1.00, rationale=1.00, selected_mechanisms=0.67 |
| t5 | strong_partial | 0.850 | excluded_distractor=1.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | reference | 1.000 | excluded_distractor=1.00, no_unsafe_selected_distractor=1.00, rationale=1.00, selected_mechanisms=1.00 |
| t6 | bad | 0.062 | action=0.00, protected_traffic=0.00, rationale=0.25, rejected_traffic=0.00 |
| t6 | weak_partial | 0.188 | action=0.75, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | mid_partial | 0.250 | action=0.00, protected_traffic=1.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | strong_partial | 0.500 | action=1.00, protected_traffic=1.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | reference | 1.000 | action=1.00, protected_traffic=1.00, rationale=1.00, rejected_traffic=1.00 |
| t7 | bad | 0.150 | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=0.17 |
| t7 | weak_partial | 0.800 | capacity_measurement=1.00, formula_consistency=0.00, peak_measurement=1.00, range_sanity=1.00, tlr_safety=1.00 |
| t7 | mid_partial | 0.840 | capacity_measurement=1.00, formula_consistency=1.00, peak_measurement=0.20, range_sanity=1.00, tlr_safety=1.00 |
| t7 | strong_partial | 0.975 | capacity_measurement=1.00, formula_consistency=1.00, peak_measurement=1.00, range_sanity=1.00, tlr_safety=0.92 |
| t7 | reference | 1.000 | capacity_measurement=1.00, formula_consistency=1.00, peak_measurement=1.00, range_sanity=1.00, tlr_safety=1.00 |
| t8 | bad | 0.000 | backoff_safety=0.00, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=0.00 |
| t8 | weak_partial | 0.600 | backoff_safety=1.00, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=1.00, spread_order_sanity=1.00 |
| t8 | mid_partial | 0.800 | backoff_safety=1.00, capacity_measurement=1.00, deferred_volume=1.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | strong_partial | 0.917 | backoff_safety=0.67, capacity_measurement=1.00, deferred_volume=1.00, expected_retry_rate=1.00, spread_order_sanity=1.00 |
| t8 | reference | 1.000 | backoff_safety=1.00, capacity_measurement=1.00, deferred_volume=1.00, expected_retry_rate=1.00, spread_order_sanity=1.00 |
| t9 | bad | 0.050 | evidence=0.00, given_tlr=1.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=0.00 |
| t9 | weak_partial | 0.300 | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | mid_partial | 0.700 | evidence=1.00, given_tlr=1.00, peak_capacity_measurements=1.00, residual_rate=1.00, verdict=0.00 |
| t9 | strong_partial | 0.750 | evidence=1.00, given_tlr=1.00, peak_capacity_measurements=1.00, residual_rate=0.00, verdict=1.00 |
| t9 | reference | 1.000 | evidence=1.00, given_tlr=1.00, peak_capacity_measurements=1.00, residual_rate=1.00, verdict=1.00 |
| t10 | bad | 0.000 | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=0.00 |
| t10 | weak_partial | 0.300 | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | mid_partial | 0.350 | baseline_peak=0.00, deficit=1.00, evidence=1.00, no_action_recommendation=0.00 |
| t10 | strong_partial | 0.650 | baseline_peak=1.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | reference | 1.000 | baseline_peak=1.00, deficit=1.00, evidence=1.00, no_action_recommendation=1.00 |

## Interpretation

- Every retained task has five anchors: bad, three partials, and reference.
- Reference anchors should score high and bad anchors should score low.
- The score spread is a local scorer-distribution check. Full model calibration still requires a fresh product-scored roster run when Docker/model budget is available.
