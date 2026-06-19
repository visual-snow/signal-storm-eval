# signal_storm_bench: handover

Date: 2026-06-19. Branch: `eval-environment-and-harness`.

## Current state

The local Open5GS signalling-storm Inspect eval has a working environment,
agent tools, product prompts, and numeric product scorers for all t1..t10. The
old binary grader state described in earlier logs has been replaced: every
retained task now requests a concrete artifact and returns a numeric 0.0..1.0
score with component metadata.

The main cleanup record is `docs/product-based-signal-storm-cleanup.md`. It
lists retained task rationale, formulas, grounding, score anchors, and residual
risks. The historical roster logs `logs/p5` and `logs/p5b` predate product
scoring and should not be used as current capability evidence.

## What is solid

- `src/signal_storm_bench/topology/compose.yaml` boots a local Open5GS AIO,
  MongoDB/subscriber seed, Prometheus, and PacketRusher storm injector. The AMF
  is CPU-capped so a sustained request/success deficit forms under storm load.
- `task.py` attaches the compose world as an Inspect docker sandbox.
  `solvers.world_setup()` starts the storm/baseline, `tools.py` exposes the NOC
  primitives, and `scorers.py` gathers only the live fields needed for each
  task.
- Prompts are product-based and leak-closed: they request JSON artifacts but do
  not disclose hidden live thresholds, reference answers, scorer weights, or the
  t6 final action text.
- `decide()` is pure and deterministic. Infrastructure probe faults raise
  sample errors; model/parser gaps score numeric 0.0.
- Gradual-score tests cover each task with a reference artifact, a bad artifact,
  and at least three ordered partial artifacts.

## Current caveats

- Verbatim 3GPP excerpts in `docs/grounding/normative-sources.md` are still
  placeholders. The bounds and section citations are recorded, but an offline
  reviewer cannot yet compare exact source text.
- Fresh product-scored model calibration is still needed. The current strongest
  local calibration evidence is the scorer anchor test set; a roster run with
  epochs >= 3 is still needed for pass^k and differentiation.
- t7 and t8 are intentionally component-scored because they combine measurement
  and sizing. If fresh transcripts show mixed failure modes that are hard to
  interpret, split them into narrower samples.
- Fixed docker subnets still make parallel sandboxes risky. Use
  `MAX_SANDBOXES=1` unless the topology is refactored to allocate subnets
  dynamically.

## File map

- `src/signal_storm_bench/dataset.py` - t1..t10 product prompts and hidden
  metadata.
- `src/signal_storm_bench/scorers.py` - live probes, `LiveState`, and product
  scorers.
- `src/signal_storm_bench/logic.py` - parsing and numeric/component scoring
  helpers.
- `tests/test_scorer_logic.py` - reference, bad, and partial artifact anchors
  for every task.
- `scripts/check_differentiation.py` - suite-level numeric differentiation
  gate.
- `scripts/check_kind_differentiation.py` - per-kind numeric differentiation
  gate.
- `scripts/pass_hat_k.py` - reliability metric, treating numeric scores >= 0.8
  as passes.
- `scripts/export_gate_artifacts.py` - summary/transcript export for review.
- `scripts/run_product_smoke.sh` - guarded one-sample smoke wrapper with docker
  cleanup traps.
- `scripts/stop_signal_storm_sandboxes.sh` - removes interrupted
  `inspect-signal_storm-*` containers.
- `docs/product-based-signal-storm-cleanup.md` - current cleanup audit record.
- `docs/product-score-calibration.md` - offline scorer-anchor calibration table.
- `docs/grounding/normative-sources.md` - 3GPP/environment grounding.

## How to run

```bash
# unit tests + lint
uv run pytest -q
uv run ruff check .

# one live sample; guarded wrapper cleans up docker on exit/interruption
scripts/run_product_smoke.sh openrouter/anthropic/claude-haiku-4.5

# if a run is interrupted and the laptop is under load
scripts/stop_signal_storm_sandboxes.sh

# full roster + gates, when budget is approved
MAX_SANDBOXES=1 bash scripts/run_iteration.sh product-p1 3
uv run python scripts/check_differentiation.py logs/product-p1
uv run python scripts/check_kind_differentiation.py logs/product-p1
uv run python scripts/pass_hat_k.py logs/product-p1
uv run python scripts/export_gate_artifacts.py logs/product-p1 gate_exports/product-p1
```

## Historical note

Earlier commits and `docs/iteration-log.md` describe a binary-scored version
whose scores were not trustworthy capability evidence. Keep those logs for
debugging environment history, but evaluate the benchmark from the product-based
scorers and fresh product-scored logs only.
