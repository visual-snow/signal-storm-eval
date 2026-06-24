# Product Score Calibration

Generated from `scripts/generate_product_calibration_report.py` using synthetic scorer inputs only; no docker services or model calls are started. This is scorer-anchor calibration, not a replacement for the paused model-roster calibration.

## Per-task Distributions

| Task | Cases | Min | Max | Mean | Spread | Distinct scores | Anchor scores |
|---|---:|---:|---:|---:|---:|---:|---|
| i1 | 5 | 0.000 | 1.000 | 0.534 | 1.000 | 5 | bad=0.000, weak_partial=0.242, mid_partial=0.628, strong_partial=0.799, reference=1.000 |
| i2 | 5 | 0.000 | 1.000 | 0.506 | 1.000 | 5 | bad=0.000, weak_partial=0.104, mid_partial=0.569, strong_partial=0.857, reference=1.000 |
| i3 | 5 | 0.000 | 1.000 | 0.564 | 1.000 | 5 | bad=0.000, weak_partial=0.400, mid_partial=0.620, strong_partial=0.800, reference=1.000 |
| i4 | 5 | 0.000 | 1.000 | 0.632 | 1.000 | 5 | bad=0.000, weak_partial=0.450, mid_partial=0.800, strong_partial=0.909, reference=1.000 |

## Component Scores

| Task | Anchor | Score | Components |
|---|---|---:|---|
| i1 | bad | 0.000 | deficit=0.00, peak_rate=0.00, request_count=0.00, success_count=0.00 |
| i1 | weak_partial | 0.242 | deficit=0.29, peak_rate=0.09, request_count=0.26, success_count=0.39 |
| i1 | mid_partial | 0.628 | deficit=0.64, peak_rate=0.49, request_count=0.72, success_count=0.70 |
| i1 | strong_partial | 0.799 | deficit=0.76, peak_rate=0.75, request_count=0.86, success_count=0.85 |
| i1 | reference | 1.000 | deficit=1.00, peak_rate=1.00, request_count=1.00, success_count=1.00 |
| i2 | bad | 0.000 | deficit=0.00, peak_rate=0.00, verdict=0.00 |
| i2 | weak_partial | 0.104 | deficit=0.00, peak_rate=0.35, verdict=0.00 |
| i2 | mid_partial | 0.569 | deficit=0.00, peak_rate=0.56, verdict=1.00 |
| i2 | strong_partial | 0.857 | deficit=0.52, peak_rate=1.00, verdict=1.00 |
| i2 | reference | 1.000 | deficit=1.00, peak_rate=1.00, verdict=1.00 |
| i3 | bad | 0.000 | no_distractor_selected=0.00, protected_traffic=0.00, rejected_traffic=0.00, selected_mechanisms=0.00 |
| i3 | weak_partial | 0.400 | no_distractor_selected=1.00, protected_traffic=0.00, rejected_traffic=0.00, selected_mechanisms=0.50 |
| i3 | mid_partial | 0.620 | no_distractor_selected=1.00, protected_traffic=0.50, rejected_traffic=0.00, selected_mechanisms=0.80 |
| i3 | strong_partial | 0.800 | no_distractor_selected=1.00, protected_traffic=1.00, rejected_traffic=0.00, selected_mechanisms=1.00 |
| i3 | reference | 1.000 | no_distractor_selected=1.00, protected_traffic=1.00, rejected_traffic=1.00, selected_mechanisms=1.00 |
| i4 | bad | 0.000 | backoff_safety=0.00, capacity_measurement=0.00, deferred_volume=0.00, retry_rate_consistency=0.00, spread_present=0.00 |
| i4 | weak_partial | 0.450 | backoff_safety=1.00, capacity_measurement=0.00, deferred_volume=0.00, retry_rate_consistency=0.00, spread_present=1.00 |
| i4 | mid_partial | 0.800 | backoff_safety=1.00, capacity_measurement=0.00, deferred_volume=1.00, retry_rate_consistency=1.00, spread_present=1.00 |
| i4 | strong_partial | 0.909 | backoff_safety=1.00, capacity_measurement=1.00, deferred_volume=1.00, retry_rate_consistency=0.54, spread_present=1.00 |
| i4 | reference | 1.000 | backoff_safety=1.00, capacity_measurement=1.00, deferred_volume=1.00, retry_rate_consistency=1.00, spread_present=1.00 |

## Interpretation

- Every retained task has five anchors: bad, three partials, and reference.
- Reference anchors should score high and bad anchors should score low.
- The score spread is a local scorer-distribution check. Full model calibration still requires a fresh product-scored roster run when Docker/model budget is available.
