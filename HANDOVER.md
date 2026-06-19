# signal_storm_bench: handover

Date: 2026-06-19. Branch: `add-readme-env-diagram`. Nothing committed beyond the
two initial commits; all work is in the working tree.

## TL;DR (honest state)

There is a working agentic Inspect eval **harness** over a real, local Open5GS
5G-core signalling-storm **environment**. The plumbing is sound and reproducible
on one machine. The **task and scoring design is not valid** against
`../art-of-evals` and needs a rebuild, not another patch. Do not trust the
current scores as a capability signal.

The single most important thing that was never done: **no task has a reference
solution**, so no grader was ever proven to accept a known-good answer at 1.0.
Everything downstream of that is unverified.

## What is actually solid (keep it)

This is the part worth preserving; it took the most effort and it works.

- **Local environment.** `src/signal_storm_bench/topology/compose.yaml`: Open5GS
  AIO (`ghcr.io/niloysh/open5gs:v2.7.0`, amd64 under emulation), MongoDB +
  subscriber seed, Prometheus, and a PacketRusher injector (pinned ref). A real
  NGAP-over-SCTP registration storm runs locally; SCTP confirmed in unprivileged
  OrbStack containers. The AMF is CPU-capped (`cpus: 0.70`) so its throughput
  sits below the offered storm rate and a sustained `reginitreq > reginitsucc`
  deficit forms.
- **Inspect wiring.** `task.py` attaches the world as `sandbox=("docker",
  compose)`, `solvers.world_setup()` fires the storm before the agent runs,
  `tools.py` exposes four tools over `sandbox_ops.py`, `scorers.py` reads live
  state at grade time. `--message-limit 50`.
- **Harness-compat fixes already made** (these were real and are correct):
  removed `container_name:` (Inspect forbids it for epochs > 1), added
  `x-default: true` to `open5gs-aio`, dropped debug host ports, made all tool
  params required so OpenAI strict function-calling accepts the schemas.
- **Storm reliability** (`solvers.world_setup` + `sandbox_ops.wait_storm_manifest`):
  the gate now requires a severe overload (`live_peak_rate >= 50` reg/s) and
  replays the storm up to 3 times; the old gate let a degenerate ~4 reg/s dribble
  through and flipped a task's ground truth.
- **175 unit tests pass; ruff clean.** Roster of six OpenRouter models runs end
  to end (`scripts/run_iteration.sh`, slugs verified live).

## Why the eval is not valid yet (the core problem)

Measured against `../art-of-evals/content/docs/02-evaluation-model/05-task.md`
and `04-suite.md`:

1. **No reference solutions.** The doc: "A reference solution proves the task is
   solvable ... confirm every grader passes it at 1.0." Never done for any of
   t1..t10. This is the root cause; fix it first.
2. **The capability target is missing.** The doc: a competent agent should score
   above 0.9, an incompetent one below 0.1, and "a zero pass rate across many
   trials usually points at the task or grader, not the agent." The current suite
   has the best model at 0.50, `t6` at 0/6, and `t1/t2/t7/t8` at 1/6. That is the
   broken-grader signal, and it was rationalised as difficulty.
3. **Binary everywhere; no partial credit.** The doc: "Partial where useful." The
   house template (`zhejiang-transport-oam`) uses Jaccard and step-coverage
   partial credit. Every task here returns 1.0/0.0. Quantitative/multi-component
   tasks (count, deficit, TLR sizing, back-off range) throw away signal and add
   noise.
4. **Graders overfit to model phrasing.** The t9/t10 synonym substring matching
   and the exact-enum match for t6 fail the human-expert litmus test; a real
   engineer would phrase the answer differently and fail the matcher too.
5. **Optimised the wrong target.** The build chased "differentiation spread
   >= 0.25" (a house proxy) and declared success on spread, even though the
   spread came largely from broken graders and run-to-run noise (the ranking
   reshuffles between runs). Differentiation is a consequence of a good suite,
   not the objective.

## Evidence on disk

Two roster runs at epochs=1: `logs/p5` (buggy scorer) and `logs/p5b` (after the
t9/t10 synonym fix). Leaderboard from `logs/p5b`:

| model | score |
|---|---|
| qwen3.7-plus / gpt-5.5 / claude-haiku-4.5 | 0.50 |
| minimax-m3 | 0.40 |
| gemini-3-flash-preview | 0.30 |
| deepseek-v4-flash | 0.20 |

Per-task pass rate (`logs/p5b`, 6 models): t1 1/6, t2 1/6, t3 3/6, t4 5/6,
t5 6/6, t6 0/6, t7 1/6, t8 1/6, t9 3/6, t10 3/6. Run-to-run variance is high
(t1 was 5/6 in `logs/p5`). Note `logs/p5b` predates the storm-reliability fix and
the residual phrasing fix, so it is already stale.

## What a correct rebuild looks like

Per `../art-of-evals`, in order:

1. For each task, write a **reference solution** (a known-good submission) and a
   test that asserts the grader returns 1.0 for it and 0.0 for a known-bad one.
   Any task whose reference solution does not pass is a broken grader; fix the
   grader or the task before running a single model.
2. Add **partial credit** where a task has components (count tolerance bands,
   TLR/back-off as graded distance to the live target, mechanism naming as set
   overlap). Document what 0.0 / 0.3 / 0.5 / 0.8 / 1.0 mean per task.
3. **Calibrate difficulty** so a competent agent clears 0.9 and a weak one stays
   below 0.1. If t6's exact-enum recall cannot be passed by a capable model with
   the standard available, either grant the standard as a tool or redesign the
   task; do not keep a 0/6 task.
4. **One bottleneck per task**; split the multi-condition tasks (t7, t8) or make
   their components partial so a failure says which link broke.
5. Re-ground every threshold to a normative source (the placeholders in
   `docs/grounding/normative-sources.md` are still unfilled).
6. Only then run the roster; treat differentiation as a check on the result, not
   the goal. Use pass^k over epochs >= 3 for the headline.

## File map

- `src/signal_storm_bench/` — `task.py`, `dataset.py` (prompts + hidden metadata,
  `_STORM`/`_BASELINE`/`_T9_GIVEN_TLR`/`_T5_CANDIDATES`), `scorers.py`
  (`decide()` per task, the binary graders to rework), `logic.py`
  (`verdict_in`, `normalize_verdict`, `tlr_holds`, `backoff_ok` — pure, testable),
  `solvers.py` (`world_setup`), `tools.py`, `sandbox_ops.py`, `topology/`.
- `tests/` — `test_scorer_logic.py`, `test_logic.py`, `test_dataset.py`,
  `test_task_wiring.py` (175 pass; these lock the *current* behaviour, so update
  them as the graders are reworked).
- `docs/iteration-log.md` — full chronological build log, iterations 0..5,
  including every error and fix. Read this first.
- `docs/build-status.md` — phase plan P0..P7 and settled decisions.
- `docs/superpowers/specs/2026-06-18-task-suite-design.md` — the per-task contract
  spec the current (flawed) graders were built from.
- `docs/grounding/normative-sources.md` — 3GPP citations; verbatim excerpts still
  TODO.
- `../art-of-evals` — the methodology this must conform to. `05-task.md` and
  `04-suite.md` are the binding sections; `03-examples/zhejiang-transport-oam.md`
  is the reference implementation to mirror.
- `.env` — `OPENROUTER_API_KEY` (gitignored; copied from
  `../zhejiang-transport-eval/.env`).

## How to run

```bash
# unit tests + lint
uv run pytest -q && uv run ruff check .

# one live sample (boots the docker world; needs OPENROUTER_API_KEY)
set -a; . ./.env; set +a
uv run inspect eval signal_storm_bench/signal_storm \
  --model openrouter/anthropic/claude-haiku-4.5 --limit 1 --message-limit 50 \
  --max-sandboxes 1 --log-dir logs/smoke

# full roster + differentiation gate (serial; see note below)
MAX_SANDBOXES=1 bash scripts/run_iteration.sh <name> [epochs]
uv run python scripts/check_differentiation.py logs/<name>
uv run python scripts/pass_hat_k.py logs/<name>
```

## Open items / decisions pending

- **Parallelism.** Sandboxes run serially (`MAX_SANDBOXES=1`) because the compose
  pins fixed subnets (`10.10.2.0/24`; AMF NGAP IP `10.10.2.2` hardcoded in
  configs) and Docker rejects duplicate subnets. To parallelise: auto-assign
  subnets, bind AMF NGAP to `0.0.0.0`, and have the injector resolve the AMF IP at
  runtime. Not done; needed for any epochs >= 3 run in reasonable wall-clock.
- **Reference-solution rebuild** (above) is the blocking work before any score is
  trustworthy.
- `docs/grounding/normative-sources.md` verbatim excerpts.
- Deliverables not started: `EVALUATION_REPORT.md`, `METHODOLOGY.md`, register
  entry.
