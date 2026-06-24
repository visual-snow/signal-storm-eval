# Signal Storm Bench

A live Open5GS 5G-core signalling-storm NOC eval: the agent reads a real
registration storm off Prometheus, recommends NGAP/NAS flow control, and
verifies it. Outcome-only grading; pass^k headline.

The task, tools, and product-based numeric scorers are implemented. Current
cleanup status, scoring formulas, anchors, and residual risks are recorded in
`../../docs/product-based-signal-storm-cleanup.md`.

<!-- Contributors: Automatically Generated -->
Contributed by [@emolero](https://github.com/emolero)
<!-- /Contributors: Automatically Generated -->

## Dataset

The dataset is five samples across the four investigation tasks:

- i1 measures the live storm (request count, peak rate, successes, deficit)
  from Prometheus metrics.
- i2 diagnoses the load state and runs in both a storm and a baseline world,
  so it contributes two samples.
- i3 selects the genuine NGAP/NAS overload controls from a candidate pool and
  names the protected and shed traffic.
- i4 sizes the NAS back-off so deferred retries disperse within live capacity.

Each prompt requests a concrete JSON artifact. Hidden live thresholds, final
answers, scorer weights, and reference artifacts are not shown to the agent.

## Scoring

Scoring is outcome-only. The submitted JSON product is checked against live
Open5GS/Prometheus state and the normative NGAP/NAS bounds in
`../../docs/grounding/normative-sources.md`. Every task returns a numeric
0.0..1.0 score with component metadata; unparseable artifacts score 0.0.

The Inspect aggregate metric is the numeric mean with stderr. `pass_hat_k.py`
treats product scores >= 0.8 as passes for the reliability headline.

## Changelog
