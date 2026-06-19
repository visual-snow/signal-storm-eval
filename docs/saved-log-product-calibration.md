# Saved Log Product Calibration

Generated from `scripts/generate_saved_log_calibration_report.py` using saved successful Inspect logs from logs/p5, logs/p5b. This does not start docker services or model calls.

These trajectories predate the product prompts, so this is calibration evidence from available saved outputs rescored with the current product scorer. It is not a substitute for a fresh product-prompt roster run.

## Per-task Distributions

| Task | Samples | Min | Max | Mean | Spread | Distinct scores |
|---|---:|---:|---:|---:|---:|---:|
| t1 | 12 | 0.363 | 0.716 | 0.614 | 0.353 | 11 |
| t2 | 12 | 0.000 | 0.726 | 0.360 | 0.726 | 9 |
| t3 | 12 | 0.000 | 0.338 | 0.258 | 0.338 | 12 |
| t4 | 12 | 0.000 | 0.300 | 0.250 | 0.300 | 2 |
| t5 | 12 | 0.517 | 0.700 | 0.685 | 0.183 | 2 |
| t6 | 12 | 0.000 | 0.125 | 0.026 | 0.125 | 3 |
| t7 | 11 | 0.000 | 0.400 | 0.158 | 0.400 | 4 |
| t8 | 11 | 0.000 | 0.394 | 0.111 | 0.394 | 6 |
| t9 | 11 | 0.000 | 0.300 | 0.245 | 0.300 | 2 |
| t10 | 12 | 0.000 | 0.300 | 0.275 | 0.300 | 2 |

## Per-sample Scores

| Task | Model | Sample | Score | Legacy | Components |
|---|---|---|---:|---|---|
| t1 | openrouter/anthropic/claude-haiku-4.5 | t1 | 0.716 | C | request_count=0.95, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/anthropic/claude-haiku-4.5 | t1 | 0.614 | I | request_count=0.82, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/deepseek/deepseek-v4-flash | t1 | 0.707 | C | request_count=0.94, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/deepseek/deepseek-v4-flash | t1 | 0.574 | I | request_count=0.77, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/google/gemini-3-flash-preview | t1 | 0.363 | I | request_count=0.48, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/google/gemini-3-flash-preview | t1 | 0.605 | I | request_count=0.81, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/minimax/minimax-m3 | t1 | 0.675 | C | request_count=0.90, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/minimax/minimax-m3 | t1 | 0.580 | I | request_count=0.77, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/openai/gpt-5.5 | t1 | 0.707 | C | request_count=0.94, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/openai/gpt-5.5 | t1 | 0.429 | I | request_count=0.57, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/qwen/qwen3.7-plus | t1 | 0.699 | C | request_count=0.93, source_signal=0.00, unit=0.00, window=0.00 |
| t1 | openrouter/qwen/qwen3.7-plus | t1 | 0.702 | C | request_count=0.94, source_signal=0.00, unit=0.00, window=0.00 |
| t10 | openrouter/anthropic/claude-haiku-4.5 | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/anthropic/claude-haiku-4.5 | t10 | 0.300 | C | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/deepseek/deepseek-v4-flash | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/deepseek/deepseek-v4-flash | t10 | 0.300 | C | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/google/gemini-3-flash-preview | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/google/gemini-3-flash-preview | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/minimax/minimax-m3 | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/minimax/minimax-m3 | t10 | 0.300 | C | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/openai/gpt-5.5 | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/openai/gpt-5.5 | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/qwen/qwen3.7-plus | t10 | 0.300 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=1.00 |
| t10 | openrouter/qwen/qwen3.7-plus | t10 | 0.000 | I | baseline_peak=0.00, deficit=0.00, evidence=0.00, no_action_recommendation=0.00 |
| t2 | openrouter/anthropic/claude-haiku-4.5 | t2 | 0.359 | I | peak_rate=0.48, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/anthropic/claude-haiku-4.5 | t2 | 0.374 | I | peak_rate=0.50, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/deepseek/deepseek-v4-flash | t2 | 0.000 | I |  |
| t2 | openrouter/deepseek/deepseek-v4-flash | t2 | 0.000 | I |  |
| t2 | openrouter/google/gemini-3-flash-preview | t2 | 0.725 | C | peak_rate=0.97, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/google/gemini-3-flash-preview | t2 | 0.365 | I | peak_rate=0.49, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/minimax/minimax-m3 | t2 | 0.726 | C | peak_rate=0.97, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/minimax/minimax-m3 | t2 | 0.372 | I | peak_rate=0.50, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/openai/gpt-5.5 | t2 | 0.708 | C | peak_rate=0.94, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/openai/gpt-5.5 | t2 | 0.697 | C | peak_rate=0.93, rate_window=0.00, source_signal=0.00, unit=0.00 |
| t2 | openrouter/qwen/qwen3.7-plus | t2 | 0.000 | I |  |
| t2 | openrouter/qwen/qwen3.7-plus | t2 | 0.000 | I |  |
| t3 | openrouter/anthropic/claude-haiku-4.5 | t3 | 0.283 | I | arithmetic_consistency=0.00, deficit=0.81, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/anthropic/claude-haiku-4.5 | t3 | 0.279 | I | arithmetic_consistency=0.00, deficit=0.80, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/deepseek/deepseek-v4-flash | t3 | 0.261 | I | arithmetic_consistency=0.00, deficit=0.75, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/deepseek/deepseek-v4-flash | t3 | 0.252 | I | arithmetic_consistency=0.00, deficit=0.72, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/google/gemini-3-flash-preview | t3 | 0.226 | I | arithmetic_consistency=0.00, deficit=0.65, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/google/gemini-3-flash-preview | t3 | 0.000 | I | arithmetic_consistency=0.00, deficit=0.00, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/minimax/minimax-m3 | t3 | 0.338 | C | arithmetic_consistency=0.00, deficit=0.97, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/minimax/minimax-m3 | t3 | 0.318 | C | arithmetic_consistency=0.00, deficit=0.91, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/openai/gpt-5.5 | t3 | 0.266 | I | arithmetic_consistency=0.00, deficit=0.76, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/openai/gpt-5.5 | t3 | 0.326 | C | arithmetic_consistency=0.00, deficit=0.93, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/qwen/qwen3.7-plus | t3 | 0.241 | I | arithmetic_consistency=0.00, deficit=0.69, request_count=0.00, success_count=0.00, unit=0.00 |
| t3 | openrouter/qwen/qwen3.7-plus | t3 | 0.304 | C | arithmetic_consistency=0.00, deficit=0.87, request_count=0.00, success_count=0.00, unit=0.00 |
| t4 | openrouter/anthropic/claude-haiku-4.5 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/anthropic/claude-haiku-4.5 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/deepseek/deepseek-v4-flash | t4 | 0.000 | I | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=0.00 |
| t4 | openrouter/deepseek/deepseek-v4-flash | t4 | 0.000 | I | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=0.00 |
| t4 | openrouter/google/gemini-3-flash-preview | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/google/gemini-3-flash-preview | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/minimax/minimax-m3 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/minimax/minimax-m3 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/openai/gpt-5.5 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/openai/gpt-5.5 | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/qwen/qwen3.7-plus | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t4 | openrouter/qwen/qwen3.7-plus | t4 | 0.300 | C | deficit_evidence=0.00, evidence_text=0.00, peak_evidence=0.00, verdict=1.00 |
| t5 | openrouter/anthropic/claude-haiku-4.5 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/anthropic/claude-haiku-4.5 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/deepseek/deepseek-v4-flash | t5 | 0.517 | I | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=0.67 |
| t5 | openrouter/deepseek/deepseek-v4-flash | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/google/gemini-3-flash-preview | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/google/gemini-3-flash-preview | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/minimax/minimax-m3 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/minimax/minimax-m3 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/openai/gpt-5.5 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/openai/gpt-5.5 | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/qwen/qwen3.7-plus | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t5 | openrouter/qwen/qwen3.7-plus | t5 | 0.700 | C | excluded_distractor=0.00, no_unsafe_selected_distractor=1.00, rationale=0.00, selected_mechanisms=1.00 |
| t6 | openrouter/anthropic/claude-haiku-4.5 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/anthropic/claude-haiku-4.5 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/deepseek/deepseek-v4-flash | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/deepseek/deepseek-v4-flash | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/google/gemini-3-flash-preview | t6 | 0.125 | I | action=0.50, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/google/gemini-3-flash-preview | t6 | 0.062 | I | action=0.25, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/minimax/minimax-m3 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/minimax/minimax-m3 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/openai/gpt-5.5 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/openai/gpt-5.5 | t6 | 0.000 | I | action=0.00, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/qwen/qwen3.7-plus | t6 | 0.062 | I | action=0.25, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t6 | openrouter/qwen/qwen3.7-plus | t6 | 0.062 | I | action=0.25, protected_traffic=0.00, rationale=0.00, rejected_traffic=0.00 |
| t7 | openrouter/anthropic/claude-haiku-4.5 | t7 | 0.400 | C | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=1.00 |
| t7 | openrouter/anthropic/claude-haiku-4.5 | t7 | 0.400 | C | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=1.00 |
| t7 | openrouter/deepseek/deepseek-v4-flash | t7 | 0.000 | I |  |
| t7 | openrouter/deepseek/deepseek-v4-flash | t7 | 0.000 | I |  |
| t7 | openrouter/google/gemini-3-flash-preview | t7 | 0.400 | C | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=1.00 |
| t7 | openrouter/google/gemini-3-flash-preview | t7 | 0.158 | I | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=0.19 |
| t7 | openrouter/minimax/minimax-m3 | t7 | 0.382 | I | capacity_measurement=0.00, formula_consistency=0.00, peak_measurement=0.00, range_sanity=1.00, tlr_safety=0.94 |
| t7 | openrouter/openai/gpt-5.5 | t7 | 0.000 | I |  |
| t7 | openrouter/openai/gpt-5.5 | t7 | 0.000 | I |  |
| t7 | openrouter/qwen/qwen3.7-plus | t7 | 0.000 | I |  |
| t7 | openrouter/qwen/qwen3.7-plus | t7 | 0.000 | I |  |
| t8 | openrouter/anthropic/claude-haiku-4.5 | t8 | 0.151 | I | backoff_safety=0.00, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | openrouter/anthropic/claude-haiku-4.5 | t8 | 0.160 | I | backoff_safety=0.04, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | openrouter/deepseek/deepseek-v4-flash | t8 | 0.211 | I | backoff_safety=0.24, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | openrouter/deepseek/deepseek-v4-flash | t8 | 0.000 | I |  |
| t8 | openrouter/google/gemini-3-flash-preview | t8 | 0.000 | I |  |
| t8 | openrouter/google/gemini-3-flash-preview | t8 | 0.394 | I | backoff_safety=0.98, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | openrouter/minimax/minimax-m3 | t8 | 0.000 | I |  |
| t8 | openrouter/openai/gpt-5.5 | t8 | 0.150 | C | backoff_safety=0.00, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t8 | openrouter/openai/gpt-5.5 | t8 | 0.000 | I |  |
| t8 | openrouter/qwen/qwen3.7-plus | t8 | 0.000 | I |  |
| t8 | openrouter/qwen/qwen3.7-plus | t8 | 0.150 | C | backoff_safety=0.00, capacity_measurement=0.00, deferred_volume=0.00, expected_retry_rate=0.00, spread_order_sanity=1.00 |
| t9 | openrouter/anthropic/claude-haiku-4.5 | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/anthropic/claude-haiku-4.5 | t9-undersized | 0.300 | C | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/deepseek/deepseek-v4-flash | t9-undersized | 0.000 | I |  |
| t9 | openrouter/deepseek/deepseek-v4-flash | t9-undersized | 0.000 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=0.00 |
| t9 | openrouter/google/gemini-3-flash-preview | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/google/gemini-3-flash-preview | t9-undersized | 0.300 | C | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/minimax/minimax-m3 | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/openai/gpt-5.5 | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/openai/gpt-5.5 | t9-undersized | 0.300 | C | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/qwen/qwen3.7-plus | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |
| t9 | openrouter/qwen/qwen3.7-plus | t9-undersized | 0.300 | I | evidence=0.00, given_tlr=0.00, peak_capacity_measurements=0.00, residual_rate=0.00, verdict=1.00 |

## Interpretation

- Infrastructure-error logs are not included; only successful saved logs are rescored.
- Saved samples that lack required live references in legacy explanations are omitted.
- Low scores can reflect the old prompt schema as well as model weakness.
- Fresh product-scored smoke and roster calibration remain required before claiming live model calibration.
