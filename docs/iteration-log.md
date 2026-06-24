# Iteration log

One entry per build step. Record the source or error, the rule applied, and the
change. Agents consult this before improvising.

## Iteration 0: context and scaffolding (2026-06-18)

Mapped the three knowledge sources and chose the template.

| Source / decision | What it gave | Outcome |
|---|---|---|
| `env_recipes_telco/.../open5gs_signaling_storm_sandbox` | k8s-only env, tool surfaces, metric names, the LOCAL_BOOT path | env is real and contract-tested; runs only on Linux k8s |
| `zhejiang-transport-eval` (transport_oam_bench) | house-style package, scorers, loop scripts, the reviewer | adopted as the template; son_energy_bench rejected |
| judge report plus README | t1..t10 contracts, three required fixes, live-peak re-grounding | scorer spec recorded in `docs/build-status.md` |
| `EVALUATION_CHECKLIST.md`, `BEST_PRACTICES.md`, `AUTOMATED_CHECKS.md` | the bible | copied verbatim into the repo |

Open blockers: where the cluster runs; the sandbox attachment architecture; the
roster.

Next: resolve the environment decision, then Phase P0 scaffold.

## Iteration 0.1: local-first pivot (2026-06-18)

Owner directive: the benchmark must run on a single machine with no cluster, so
anyone can reproduce it. This supersedes the cluster and k8s-sandbox options.

| Probe / source | Finding | Outcome |
|---|---|---|
| SCTP socket probe in the Docker backend (OrbStack, kernel 6.17.8) | unprivileged container created an AF_INET SCTP socket; SCTP built-in | a real NGAP-over-SCTP storm runs locally; no cluster needed |
| `base/open5gs-aio/docker-compose.yaml` (vendored upstream) | all-in-one Open5GS `ghcr.io/niloysh/open5gs:v2.7.0`, metrics 9090, NGAP 38412/sctp, plus mongo and webui | the base for a local docker-compose topology |

Decision: substrate becomes a local docker-compose topology shipped in the eval,
attached as `sandbox=("docker", compose_file)`, matching the transport_oam_bench
house style. Component set is unchanged (Open5GS, PacketRusher, Prometheus,
MongoDB); recorded as a deliberate deviation in FIDELITY.md.

Next: pull the upstream AIO config and the recipe's Prometheus / subscriber-seed
/ injector manifests, assemble `topology/`, and prove a local storm drives the
AMF counter (P0 plus P2).

## Iteration 0.2: parallel scaffold and env (2026-06-18)

Read the full env interface from the AIO and recipe manifests. Key facts: the
AMF NGAP server binds 10.10.2.2 (n2network); the AMF metrics bind 127.0.0.5:9090
and must move to 0.0.0.0:9090 for a separate Prometheus container to scrape it;
config at `/open5gs/config/amf.yaml`, log at
`/open5gs/install/var/log/open5gs/amf.log`.

Launched two background agents (each loads karpathy-guidelines, non-overlapping
files):

- P2 environment: assemble and boot `src/signal_storm_bench/topology/` locally,
  prove the storm drives `reginitreq`, write `docs/topology-notes.md`.
- P0 scaffold: port the package, `pyproject`, loop scripts, the `eval-reviewer`
  agent, and repo chrome from the transport_oam_bench template; leave task logic
  as stubs.

Wrote `docs/superpowers/specs/2026-06-18-task-suite-design.md`: the resolved
per-task contracts (t1..t10), the live-peak re-grounding (capacity_rate and
live_peak_rate replace the deleted ceiling), and the three judge fixes baked in.
This is the source of truth for P1 and P3.

Next: when P0 and P2 report, implement P1 (dataset and prompts) and P3 (tools
and scorers) against the spec, then P4 local validation.

## Iteration 0.3: P0 scaffold complete (2026-06-18)

P0 reported PASS. ruff clean, package imports, the ported script tests pass
(9 passed). Stubs in place for task/dataset/scorers/solvers/tools/sandbox_ops/
logic. Decisions: per-file-ignore extended to scripts/ for PLR2004; AGENTS.md
de-symlinked; .env not copied (no key in repo).

Owner directive: agent message budget is 50 (`--message-limit 50`,
DEFAULT_MESSAGE_LIMIT = 50); overrides the README's ~40. Roster = the standard
five over OpenRouter; P5 runs full loop within a budget (default $5/model).

## Iteration 0.4: P2 environment PASS (2026-06-18)

The local docker-compose world boots and a real NGAP-over-SCTP storm drives the
live AMF counters. Evidence: a 150-UE storm climbed reginitreq ahead of
reginitsucc (transient lag), then both reached +150; the default 200-UE storm
gave +200/+200; baseline held flat; SCTP confirmed (NGAP on 10.10.2.2:38412);
fresh boot to AMF-healthy plus 500 seeded subscribers in ~18s.

Findings folded into the design:
- The core image is amd64-only; runs under OrbStack x86 emulation.
- NGAP rides n2 (10.10.2.2), not n3; the injector gNB/amfif moved to n2. The one
  substantive address change.
- AMF metrics bind moved 127.0.0.5 -> 0.0.0.0 (one config edit) for the
  Prometheus container to scrape; all other NF configs byte-faithful.
- PacketRusher `-tr` is a bare integer ms, not a Go duration.
- Prometheus: inside-sandbox http://prometheus:9090; host http://localhost:9091.

KEY OPEN ITEM for P4 (scorer validity): at 100 reg/s the AMF keeps up, so the
deficit is transient, not sustained. For t7/t8/t9 to be non-degenerate,
`live_peak_rate` must robustly exceed `capacity_rate`. P4 must tune the storm
hotter (raise STORM_RATE/UE_COUNT) or cap the AMF container CPU so capacity is
bounded below the offered load. Decide and validate this before the P5 loop.

Launched the `signal-storm-implement` Workflow (run wf_dbfba8ed-4a4): a real
generator/critique loop (Implement -> Test -> Review), free, visible in
/workflows.

## Iteration 1: implementation signed off (2026-06-18)

The `signal-storm-implement` Workflow completed: eval-reviewer SIGN-OFF, score
9/10, 2 review rounds, 96 unit tests pass. All ten grader contracts match the
spec; the three judge fixes and the live-peak re-grounding are in; outcome-only
scoring; unparseable scores 0; infra errors raise; message_limit 50; the four
tools present.

Non-blocking reviewer notes to clear (P4/P6):
1. sandbox_ops peak uses a 30s outer window, not the full storm window; take the
   max sustained rate over the storm window per the spec.
2. t10 scorer hardcodes 30s; thread peak_window from metadata.
3. docs/grounding/normative-sources.md still has verbatim-excerpt placeholders
   (row 7 WIP); bounds and citations are present and match the scorer constants.

Next: P4. Tune the storm to a sustained overload (capacity_rate < live_peak_rate
robustly) so t7/t8/t9 are non-degenerate, clear notes 1 and 2, then one live
`--limit 1` run (needs OPENROUTER_API_KEY). Then the P5 differentiation loop.

## Iteration 2: P4 sustained overload + harness fixes + smoke PASS (2026-06-18)

Storm retuned to a deep, sustained overload and baked into the topology:
`cpus: 0.70` on the core, injector defaults `STORM_RATE=120 UE_COUNT=6000
DURATION_S=90` over a `5m` window; `dataset._STORM` updated to match;
`scrape_interval_s=5` threaded into the rate probes; the two non-blocking scorer
notes (peak window, t10 hardcoded 30s) cleared. Validation (fresh world):
`live_peak=122.4 reg/s` vs `capacity=15.2 reg/s` (ratio 0.12), `rejected=5770`,
baseline `0.0`. 162 unit tests pass. The injector now boots idle and storms only
on explicit exec, matching `world_setup()`.

Three live-only harness incompatibilities the unit tests could not catch (they
never boot Docker), found and fixed against the real Inspect docker sandbox:

| Error (live bring-up) | Rule | Fix |
|---|---|---|
| `container_name ... not permitted ... will not work with epochs > 1` | Inspect provisions per-sample names | removed all 5 `container_name:` |
| `No 'default' service found in Docker compose file` | Inspect needs `default` or `x-default: true` | `x-default: true` on `open5gs-aio` |
| (latent) `Pool overlaps with other one on this address space` | Docker rejects duplicate subnets | dropped debug host ports; pinned `MAX_SANDBOXES=1` until subnets are reworked |

Smoke (`inspect eval --limit 1`, openrouter/anthropic/claude-haiku-4.5,
`--message-limit 50`): `status: success`, 1/1 sample, `accuracy 1.0`, no infra
errors, 3:02, ~125k tokens. Full path proven: Inspect boots compose -> world_setup
fires the 90s storm -> agent reads live Prometheus -> scorer grades live state.

Roster slugs all verified present in the live OpenRouter catalog.

Launched P5 epochs=1 differentiation pass (5 models, serial, `MAX_SANDBOXES=1`),
logs in `logs/p5`. The differentiation gate (the exit condition) needs only
epochs=1; pass^k (epochs >= 3) is deferred to the P7 report, and the topology
subnet rework for parallelism is deferred until then too.

## Iteration 3: P5 differentiation PASS + OpenAI strict-tool fix (2026-06-19)

epochs=1 roster (all status success, 10/10 samples, zero infra errors):

| model | accuracy |
|---|---|
| minimax-m3 | 0.50 |
| claude-haiku-4.5 | 0.40 |
| gemini-3-flash-preview | 0.40 |
| qwen3.7-plus | 0.30 |
| deepseek-v4-flash | 0.10 |

`check_differentiation.py`: **PASS**. Spread 0.40 (>= 0.25), 4 distinct bands
(>= 3), roster 5 (>= 5). This is the build-loop exit criterion 2; the suite
discriminates capability without floor/ceiling clustering.

Owner added `openai/gpt-5.5` to the roster. First run errored before any sample:
OpenAI strict function-calling (`tools[2].parameters ... invalid_function_parameters`,
missing `nf_name` in `required`). Cause: tool params with defaults
(`read_nf_log_file(nf_name="amf")`, `run_ue_storm_simulator(rate=120,...)`) are
emitted as optional, and OpenAI strict mode requires every property in `required`.
The other five providers are lenient. Fix (portable, model-agnostic): dropped the
defaults so all params are required; verified `required == properties` for all
four tools; 162 tests still pass; canonical storm values moved into the
`run_ue_storm_simulator` docstring. Re-running gpt-5.5 into `logs/p5`.

## Iteration 4: scorer validity fix (t9/t10 false negatives) (2026-06-19)

The per-task matrix over the 6-model run exposed three 0/6 tasks. Two were scorer
false negatives, not difficulty:

- t10 (idle baseline): all six models answered "no flow control needed", every
  one rejected. The set required the exact "no control needed"; the word "flow"
  broke the substring match.
- t9 (undersized TLR): four models said "insufficient"/"not sufficient" (correct);
  the set only held {ineffective, not capped, ceiling exceeded, overloaded}.

Both tasks have a constant live half (storm always overloaded, baseline always
idle), so the verdict match is the sole discriminator; the narrow sets gave it
near-zero recall. Broadened both to the judgment-bearing phrasings models actually
use, deliberately excluding bare state words ("overloaded", "no flow control")
that appear in both polarities, to keep precision. Added 12 regression tests
(real phrasings must pass; opposite-polarity must fail); 174 tests pass.

Offline re-score against the recorded answers (valid because the live half is
constant): t9 0/6 -> 5/6, t10 0/6 -> 6/6. Predicted corrected means: minimax 0.70,
gpt-5.5 0.70, haiku 0.60, gemini 0.60, qwen 0.60, deepseek 0.20. Spread widens
0.40 -> 0.50; differentiation still PASS. t6 stays 0/6 and is left as is: all six
picked a wrong TS 38.413 overload-action enum, a correct rejection, not a bug.

The scorer reads live state at grade time, so `inspect score` cannot re-grade the
old logs (no live sandbox). Launching a clean re-run with the fixed scorer into
`logs/p5b` for authoritative on-disk artifacts, then export + eval-reviewer.

Next: re-run -> export gate artifacts -> eval-reviewer sign-off (exit criterion 3),
then P7 (report + METHODOLOGY.md) and the deferred parallel rework for epochs>=3.

## Iteration 5: storm-reliability gate + residual phrasing (2026-06-19)

The corrected re-run (logs/p5b) still PASSED differentiation (spread 0.30 this
time; haiku/qwen/gpt 0.50, minimax 0.40, gemini 0.30, deepseek 0.20) but the
per-sample explanations exposed two harness issues bigger than the synonym gaps:

1. Intermittent storm under-fire. One t9 sample (qwen) read
   `live_peak_rate=4.0, capacity_rate=4.0, live_fails=False`: the injector
   delivered a few registrations instead of thousands, so a 10% TLR "held" and
   the ground truth flipped, grading qwen's correct "insufficient" as wrong.
   1/11 storm-reading samples under-fired (~9%). Root cause: `wait_storm_manifest`
   gated on `count>0 and deficit>0`, which any dribble clears. Fix: gate on
   `live_peak_rate >= MIN_STORM_PEAK_RATE` (50 reg/s; healthy ~106-115, under-fire
   ~4) with a real deficit, return bool, and have `world_setup` replay the storm
   up to STORM_ATTEMPTS=3 times before raising. MANIFEST_TIMEOUT_S 180 -> 60
   (data is present right after the storm).
2. Residual t10 recall: gpt-5.5's "no flow control required" was rejected ("not
   required" present, "no ... required" not). Added the "required"-structure
   phrasings. epochs=1 also shows high run-to-run variance (t1 5/6 -> 1/6 across
   runs), which is why pass^k over epochs>=3 is the right headline for the report.

175 tests pass, lint clean. The scorer reads live state, so these fixes need a
fresh authoritative run to land on disk; pending the owner's call on epochs and
whether to do the parallel-sandbox rework first.
