# Agent development pipeline

Version 0.4, November 2026. Complements `architecture.md`.

Twofold goal: build Aretz Texture to production standards and, along the way, practice how engineering with agents is done in 2026.

## 1. Principles

* **Spec before code.** Every feature starts with a short specification with acceptance criteria. Agents implement against the spec, not against a conversation.
* **Evals as first class citizens.** Besides unit tests, the musical evaluation corpus runs in CI and blocks regressions.
* **Model diversity in review.** Whoever writes the code (Claude) is not who reviews it (OpenAI). Different model families have different blind spots.
* **The human decides at the gates.** Nico approves specs and merges. Agents never push to `main`.
* **Cost proportional to difficulty.** The expensive model only where the reasoning justifies it.
* **Small PRs.** One issue, one branch, one PR reviewable in minutes.
* **Shared context in the repo.** `AGENTS.md` is the single source of conventions; Claude Code, Codex and Cursor read it.
* **Verifiable clean code.** Quality rules (section 9) are enforced with tools whenever possible, and with review when not.
* **Everything in English.** Code, comments, docstrings, documentation, specs, ADRs and the development journal.
* **Process journal.** Each work session gets a dated entry in `docs/journal/`, recording decisions, friction and lessons. It is the raw material for an article about the process.

## 2. Roles

Each Claude role is a subagent defined in `.claude/agents/` (`architect`, `implementer`, `explorer`, `qa-runner`, `documenter`), with its model and tools fixed in the frontmatter.

### Nico: product owner and tech lead
Tool: **Cursor**.
* Approves specs (gate 1) and PRs (gate 2).
* Reads diffs, edits by hand when convenient, decides conflicts between reviewer and implementer.
* Musical judge: reviews the human evaluation sample in every version.

### Architect
Model: **Claude Opus 5.5**. Occasional use.
* Turns issues into specs with acceptance criteria and a test plan.
* Designs the delicate algorithms: harmonic segmentation, dynamic programming for voices, rhythm scoring.
* Writes ADRs.

### Implementer
Model: **Claude Sonnet 5.5**. The workhorse.
* Works on its own branch with TDD: tests first, then code.
* Responds to review comments and opens the PR.

### Explorer
Model: **Claude Haiku 5.5**. Read only.
* Searches the code and the music21 documentation, builds context for the implementer.

### QA runner
Model: **Claude Haiku 5.5**.
* Runs tests, linters and the corpus evaluation; summarizes failures for the implementer.
* Does not write production code.

### Documenter
Model: **Claude Haiku 5.5**.
* Updates docs, changelog and ADR formatting from the approved diff.

### External reviewer
Tool: **Codex code review on GitHub** (OpenAI), through Nico's ChatGPT Plus plan.
* Automatic review on every PR, guided by the `Review guidelines` section of `AGENTS.md`. A review can also be requested by commenting `@codex review`.
* The Plus plan has usage limits per time window; small PRs reviewed one at a time stay well within them.
* On GitHub it reports only P0 and P1 findings by default; repository rules can raise other categories.
* For local or CI reviews through Codex CLI the model can be pinned: **GPT-6.1 Sol** as the base, **GPT-6 Astra** reserved for changes to the algorithmic core.

### Musical writer (inside the product, not the pipeline)
Model: **Claude Sonnet 5.5** or **Haiku 5.5** depending on measured quality.
* Generates the textual description of the analysis. Evaluated like any other feature.

## 3. Feature flow

1. **Issue** on GitHub describing the need in musical language.
2. **Spec**: the architect writes `docs/specs/NNN_name.md` with acceptance criteria and a test plan.
3. **Gate 1**: Nico approves or corrects the spec.
4. **Implementation**: the implementer creates a branch, writes tests, implements. The explorer builds context when needed.
5. **Validation on every commit**: formatting, lint, types, architecture and fast tests. If it fails, the commit is not made and the agent receives the error to fix it (see section 10).
6. **PR**: CI runs the full tests, coverage and the corpus evaluation with regression thresholds.
7. **Codex review**, automatic. The implementer responds or fixes.
8. **Gate 2**: Nico reviews in Cursor and merges.
9. **Documentation**: the documenter updates docs and changelog.

## 4. Stack

* Python 3.12 or later, environment managed with **uv**
* **ruff** (formatting and lint), **pyright** (types)
* **pytest** and **hypothesis**: voice leading constraints (no parallels, spans, crossings) lend themselves very well to property based tests
* **pydantic** for the event tree data model
* **music21** as the musical base
* **GitHub Actions** for CI, with branch protection on `main`
* Later: **FastAPI** for an API and **Verovio** for web rendering

## 5. Repository structure

```
src/
    aretz_texture/
        core/        data model: harmonic event tree
        ingest/      MusicXML reading and normalization
        analysis/    segmentation, nonchord tones, roles, harmony, rhythm
        voicing/     four voice generation by dynamic programming
        render/      harmonic rhythm, representative rhythm, text
        eval/        metrics and evaluation corpus
tests/
docs/
    adr/
    specs/
    journal/         dated session entries, raw material for the process article
.claude/
    agents/          definition of each role with its model and tools
AGENTS.md            conventions and Review guidelines (single source)
CLAUDE.md            imports AGENTS.md and adds Claude Code specifics
LICENSE              MIT
```

## 6. Cost control

* **Claude subscription for interactive work.** Claude Code runs on Nico's Claude subscription, which gives a fixed and predictable cost. Its usage limit is shared with the Claude apps.
* **API credits only for unattended automation**, such as future jobs in CI, so they are measured separately. `ANTHROPIC_API_KEY` stays unset on the development machine; when it is set, Claude Code bills the API instead of the subscription.
* `CLAUDE_CODE_SUBAGENT_MODEL` set to Sonnet in `.claude/settings.json`: any subagent without an explicit model falls back there, never to Opus.
* Each role pins its model in the frontmatter of `.claude/agents/`.
* Opus is invoked only for specs and algorithm design, not for implementation.
* External review: Codex's base model for everything; the large model only for the core.
* Do not subscribe to Cursor's Bugbot at this stage: it would duplicate Codex review.
* During the first month, log how much of the subscription limit each PR consumes, to calibrate which model each role uses.

## 7. Roadmap

* **F0**: repo, CI, `AGENTS.md`, agent definitions, branch protection.
* **F1**: ingestion and level 2 segmentation on Bach chorales.
* **F2**: voice generation and harmonic rhythm rendering.
* **F3**: representative rhythm selection and its rendering.
* **F4**: textual description with an LLM and its evaluation.
* **F5**: levels 3 and 4.
* **F6**: web interface and OMR input.

## 8. What to practice in each phase

* **F0**: agent configuration, shared context, human gates.
* **F1 and F2**: spec driven development, TDD with agents, property based tests.
* **F3**: evals as regression in CI, parameter calibration.
* **F4**: an LLM inside the product, evaluation of nondeterministic outputs.
* **F6**: complete product, deployment, observability.

## 9. Code quality

Clean Code principles are followed, adapted to idiomatic Python. Where Clean Code and Python conventions differ, Python wins (PEP 8, docstrings rather than avoiding comments as a rule).

### Rules

* **Intention revealing names**, using the vocabulary of the musical domain. Everything in English. `docs/glossary.md` defines each musical term as the code uses it (for example, `HarmonicWindow` or `voicing`), so agents and reviewers do not invent synonyms.
* **Small functions with a single responsibility.** If describing one requires the word "and", it gets split.
* **Pure core.** Analysis has no side effects: it receives data and returns data. File reading and rendering live at the edges (`ingest/`, `render/`). This also guarantees the determinism the architecture requires.
* **Dependencies point inward.** `core/` imports nothing from the rest; `analysis/` and `voicing/` depend on `core/`; `render/` depends on the tree cut, never on internal analysis.
* **No magic numbers.** Weights, thresholds and spans go into typed configuration, with a name and an explanation.
* **Complete types.** Every public function annotated; immutable data models with pydantic.
* **Explicit errors.** Domain exceptions (`UnparseableScoreError`, `AmbiguousHarmonyError`), never `None` as a silent error signal.
* **Comments explain why**, not what. Musical decisions that are not obvious reference their ADR.
* **Tests readable as specification.** One concept per test, descriptive names, arrange, act, assert structure.
* **Boy scout rule.** Every PR leaves the touched code a little better than it found it, without drifting from scope.

### How it is enforced

* **ruff** with rules for cyclomatic complexity (C901), number of arguments and branches (PLR), naming (N), docstrings (D) and annotations (ANN), with strict thresholds.
* **pyright** in strict mode.
* **Architecture test** that verifies the direction of dependencies between packages.
* Rules that cannot be automated (intention revealing names, single responsibility, useful comments) go into the `Review guidelines` section of `AGENTS.md` as P1, so Codex flags them on every PR.
* Claude agents receive the same rules through `CLAUDE.md`, which imports `AGENTS.md`.

## 10. Quality checks at commit time

Defense in layers: each layer catches what the previous one may let through, and the last one has the final word.

### Layer 1: on edit (immediate feedback)
Claude Code `PostToolUse` hook on `Edit` and `Write` (`.claude/hooks/format_python.py`): runs `ruff check --fix` and `ruff format` on the touched Python file. Minor errors are fixed automatically; problems ruff cannot fix go back to the agent as a message.

### Layer 2: when the agent runs git
Claude Code `PreToolUse` hook on `Bash` (`.claude/hooks/guard_git.py`), for git commands. It exits with code 2, which blocks the command and sends the reason to the agent, when:
* a commit or push uses `--no-verify`,
* a commit is attempted without the pre-commit git hook installed (for example, in a fresh cloud session), so layer 3 could not run,
* a push would update `main`.

It does not run the checks itself: layer 3 runs them on every commit, and their output already reaches the agent when a commit fails. Running them twice would only slow commits down. Both hooks have tests in `tests/tooling/`.

### Layer 3: git hook (applies to agents and humans)
The `pre-commit` framework installed in the repo, so it applies equally to Claude Code, Codex and Nico from Cursor:
* `ruff format --check` and `ruff check`
* strict `pyright`
* architecture test (dependency direction)
* fast tests (`pytest -m "not slow"`)

Budget: under 20 seconds. A slow hook invites skipping it; heavy work goes to CI.

### Layer 4: CI (the final authority)
GitHub Actions repeats the layer 3 checks and adds the full tests, coverage and the corpus evaluation. They are required checks in branch protection: even if a local hook failed or was skipped, nothing reaches `main` without passing here.

Layers 1 and 2 help the agent; layers 3 and 4 are the guarantee. Quality is never entrusted to a single local mechanism.
