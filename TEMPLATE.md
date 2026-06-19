# Inspect AI eval template

Scaffolding, skills, and CI for this repository. The transport O&M eval itself
is documented in [README.md](README.md); this file holds the template
onboarding that previously lived there.

## Template documentation

This repository was scaffolded from a template for building
[Inspect AI](https://inspect.aisi.org.uk/) evaluations.

## Important Features

This template contains:

- [Skills](#skills) — Claude Code skills to help produce evaluations, improve
  their quality, and speed up velocity.
- [Documentation](#documentation) — guides on best practices and recommended
  standards.
- [Examples](#examples) — example evaluations that show how to produce
  evaluations in Inspect.

## Getting started

1. **Fork this repository** — click "Use this template" (or fork) on GitHub
   to create your own copy, then clone it:

   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **Install dependencies and run**:

   ```bash
   # Install dependencies
   uv sync

   # Run an evaluation
   uv run inspect eval <eval_name>/<task_name> --model openai/gpt-4o

   # Run tests
   uv run pytest

   # Run linters
   uv run ruff check && uv run ruff format --check && uv run mypy .
   ```

## Quickstart

1. Fork and clone (see above), then `uv sync`
2. Copy an example: `cp -r src/examples/simple_qa src/my_eval`
3. Register it in `pyproject.toml`:

   ```toml
   [project.entry-points.inspect_ai]
   my_eval = "my_eval"
   ```

4. Run it: `uv run inspect eval my_eval/my_task --model openai/gpt-5-nano`

See `src/examples/` for complete working examples, including a real
benchmark adaptation (GPQA).

## Structure

Each evaluation lives in its own directory under `src/` and is registered via
entry points in `pyproject.toml`. Tests go in `tests/<eval_name>/`.

```text
src/
  <eval_name>/          # Your evaluation
    __init__.py         # Exports task function(s) for Inspect discovery
    <eval_name>.py      # Task implementation
    eval.yaml           # Evaluation metadata
  examples/             # Example evaluations (not registered)
tests/
  <eval_name>/          # Tests for your evaluation
  examples/             # Tests for examples
```

## Adding evaluations

1. Create a new directory under `src/` (e.g., `src/my_eval/`) — copying one of
   `src/examples/` is the easiest start. It needs an `__init__.py` that exports
   your `@task` functions and an `eval.yaml` (see `src/examples/gpqa/eval.yaml`
   for a fully populated example).
2. Add an entry point in `pyproject.toml`:

   ```toml
   [project.entry-points.inspect_ai]
   my_eval = "my_eval"
   ```

3. Add the module name to `[tool.setuptools.packages.find]` include list
4. Add a mypy override for the new module

## Examples

The `src/examples/` directory contains three working evaluations demonstrating
common patterns. These are not registered as evaluations — they exist purely
as reference implementations you can copy from. They don't ship as part of
your eval's wheel.

### Simple Q&A (`src/examples/simple_qa/`)

A straightforward question-answering evaluation using `match()` scoring.
Demonstrates dataset conversion, prompt templates, and few-shot examples.
Similar to evaluations like GPQA.

### LLM-as-Judge (`src/examples/llm_judge/`)

An evaluation that uses a language model to grade open-ended responses via
`model_graded_qa()`. Demonstrates custom grading templates and judge model
configuration. Similar to evaluations like Healthbench.

### GPQA (`src/examples/gpqa/`)

A real-world benchmark adaptation demonstrating external dataset loading,
multiple-choice scoring, and domain filtering. Includes a fully-populated
`eval.yaml` showing all available metadata fields.

### Agentic (`src/examples/agentic/`)

An agent-based evaluation where the model uses `bash()` and `python()` tools
in a Docker sandbox via `basic_agent()`. Demonstrates sandbox configuration
and tool-use scoring. Similar to evaluations like GAIA.

## Skills

The `.claude/skills/` directory ships Claude Code skills that activate when
you ask Claude to perform the matching task — e.g. "create a new evaluation"
or "review this PR against the template standards". The reliable way to
invoke one is *"Please run the /SKILL_NAME skill on EVAL_NAME."*

### Authoring

- **create-eval** — implement a new evaluation from an issue, paper, or
  benchmark spec, with checkpoints between phases.
- **investigate-dataset** — explore HuggingFace, CSV, or JSON datasets to
  understand their structure and data quality.
- **ensure-test-coverage** — review existing tests or create missing ones for
  a single evaluation against repo conventions.

### Reviewing

- **eval-quality-workflow** — fix or review a single evaluation against the
  standards in [EVALUATION_CHECKLIST.md](EVALUATION_CHECKLIST.md).
- **eval-validity-review** — assess whether an evaluation accurately measures
  what it claims to measure and has good methodological standards.
- **review-pr-workflow** — review a PR against the agent-checkable standards
  in `EVALUATION_CHECKLIST.md` and `BEST_PRACTICES.md`; designed to run in CI.

### Running and analysing

- **eval-report-workflow** — produce a README results table by selecting
  models, estimating costs, and running evaluations.
- **read-eval-logs** — view and analyse Inspect `.eval` log files via the
  Python API and CLI.
- **check-trajectories-workflow** — use Inspect Scout to scan agent
  trajectories for failures, formatting issues, reward hacking, and refusals.

### Submission

- **prepare-submission-workflow** — finalize an evaluation for PR submission
  (dependencies, tests, lint, `eval.yaml`, README).

## Features

- **Multiple evaluation support** — add as many evaluations as needed, each
  with its own directory, tests, and metadata
- **Automated quality checks** — pre-commit hooks and CI for ruff, mypy,
  and pytest

## CI workflows

The template includes several GitHub Actions workflows that run
automatically.

### Standard checks (always active)

- **Checks** (`checks.yml`) — runs ruff, mypy, POSIX code check,
  unlisted-eval check, package build, autolint, generated-docs check,
  and large-file scan on every push and PR. Each check is individually
  enforceable — see [Checks and enforcement](#checks-and-enforcement).
- **Markdown Lint** (`markdown-lint.yml`) — lints markdown files on PRs
- **PR Template Check** (`pr-template-check.yml`) — verifies PR body
  contains the required checklist

### Claude-powered workflows

These workflows use Claude to automate code review and issue resolution.
To enable them, add one of these secrets to your repository settings
(Settings > Secrets and variables > Actions > Secrets):

- **`ANTHROPIC_API_KEY`** — an Anthropic API key (recommended for most
  users). Create one at <https://console.anthropic.com/settings/keys>.
- **`ANTHROPIC_ROLE_ARN`** — an AWS IAM role ARN for Bedrock access via
  OIDC (for organisations using AWS Bedrock).

Without either secret, the workflow is skipped.

At time of writing, each Claude review costs roughly **$0.50–$2** using
Claude Opus 4.6 ($5/$25 per million tokens input/output).

- **Claude Code Review** (`claude-review.yaml`) — reviews PRs against
  the evaluation standards in EVALUATION_CHECKLIST.md and
  BEST_PRACTICES.md.

  Three modes, controlled by repository variables (Settings > Variables
  > Actions):

  1. **Disabled** (default if no secret is set) — workflow skips
     entirely.
  2. **On-demand only** (`AUTO_REVIEW_ALL_COMMITS` unset or `false`) —
     review fires only when someone comments `/review` on a PR or
     dispatches the workflow manually. Recommended starting point.
  3. **Every commit** (`AUTO_REVIEW_ALL_COMMITS=true`) — review fires
     on every push to a non-draft PR. Highest cost; use when the team
     wants a review on each iteration.

  Optional `CLAUDE_MODEL` repository variable overrides the model
  (defaults to `claude-opus-4-6-20250725` for API key users).

## Checks and enforcement

This template is calibrated against the
the Inspect AI evaluation registry's
quality standards. Those standards are **recommended, not required** in the
template — meeting them is what we suggest if you want a smooth path to
registry submission, but the template doesn't block your work if you don't.

Each check has an `ENFORCE_<NAME>` setting in
[`tools/enforcement.config`](tools/enforcement.config). When
`ENFORCE_<NAME>=true`, the check blocks merge on failure. When `=false`, it
reports as advisory in the PR (visible in the run logs but doesn't prevent
merging). To change enforcement for your repo, edit that file and commit —
the change is git-tracked and reviewable.

The same file is honoured locally by `make check` (which runs
`tools/run_checks.sh`): advisory failures are reported with a `⚠` and a
"not enforced" note; only enforced failures cause `make check` to exit
non-zero. Environment variables override the file for one-off local runs:

```bash
ENFORCE_AUTOLINT=true bash tools/run_checks.sh
```

All toggles live in [`tools/enforcement.config`](tools/enforcement.config) — edit and commit to change behaviour for your fork. The defaults committed there are:

**Default-enforced** (blocking unless `ENFORCE_<NAME>=false`):

- `ENFORCE_RUFF` — Ruff format + lint
- `ENFORCE_MYPY` — Mypy static types
- `ENFORCE_POSIX_CHECK` — POSIX-only Python idioms (`tools/check_posix_code.py`)
- `ENFORCE_UV_LOCK` — `uv.lock` in sync with `pyproject.toml`
- `ENFORCE_UNLISTED_EVALS` — eval directories must be registered in
  `pyproject.toml` entry-points and have an `eval.yaml`
- `ENFORCE_PACKAGE` — package builds and inspects cleanly

**Default-advisory** (reported but non-blocking unless `ENFORCE_<NAME>=true`):

- `ENFORCE_AUTOLINT` — structural standards (eval.yaml schema,
  README sections, test patterns, etc.) via `tools/run_autolint.py`
- `ENFORCE_GENERATED_DOCS` — auto-generated README sections committed
- `ENFORCE_MARKDOWN_LINT` — markdown style (`.markdownlint.yaml`)
- `ENFORCE_LARGE_FILES` — no files >10MB
- `ENFORCE_PR_TEMPLATE` — PR body contains the template checklist

### Quick recipes

- **Strict mode (registry-ready)**: set every `ENFORCE_*` to `true`. Your
  PRs now fail on the same registry-grade standards.
- **Loose mode (default)**: leave everything unset. Correctness blocks
  (Ruff/Mypy/POSIX/lock/registration/build); style and structure are
  advisory.
- **Per-check**: set just the toggles you want — e.g.
  `ENFORCE_AUTOLINT=true` if you want eval-structure rules enforced but
  don't care about markdown style.

To opt out of a default-enforced check, set its variable to `false`. To opt
into a default-advisory check, set its variable to `true`.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) — development setup, testing, and
  submission guidelines.
- [BEST_PRACTICES.md](BEST_PRACTICES.md) — evaluation design best practices
  
- [EVALUATION_CHECKLIST.md](EVALUATION_CHECKLIST.md) — quality checklist used
  when reviewing evaluations
- [AUTOMATED_CHECKS.md](AUTOMATED_CHECKS.md) — what `tools/run_autolint.py`
  checks, and how to suppress individual rules.
- [TASK_VERSIONING.md](TASK_VERSIONING.md) — when to bump an eval's `task`
  version.
- [AGENTS.md](AGENTS.md) — repo-wide tips for coding agents and pointers to
  the skills above.
- [CLAUDE.md](CLAUDE.md) — project-level instructions Claude Code reads on
  every session in this repo.
