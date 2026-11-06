# AGENTS.md

Single source of conventions for all agents (Claude Code, Codex, Cursor) and for humans. If a rule changes, it changes here.

## Project

Aretz Texture (`aretz_texture`): an analysis tool that reduces a MusicXML score to its harmonic structure in four voices, with two rhythmic modes and several granularity levels. Free and open source under the MIT License (ADR 0001). Named in honor of Isabel Aretz, composer and ethnomusicologist.

* Architecture: `docs/architecture.md`
* Decisions: `docs/adr/`
* Specifications: `docs/specs/`
* Domain glossary: `docs/glossary.md`
* Process journal: `docs/journal/`

## Language

Everything in English: code, identifiers, comments, docstrings, commit messages, PR descriptions, documentation, specs, ADRs and the journal.

## Commands

* Install environment: `uv sync`
* Fast tests: `uv run pytest -m "not slow"`
* Full tests: `uv run pytest`
* Formatting: `uv run ruff format .`
* Lint: `uv run ruff check .`
* Types: `uv run pyright`
* Dependency direction: `uv run lint-imports`
* All commit checks: `uv run pre-commit run --all-files`

## Workflow

* Every feature starts from an approved spec in `docs/specs/`. No spec, no implementation.
* If the task is complex or the spec does not define structure, propose design and files before writing code.
* TDD: tests are written before the code that makes them pass.
* One issue, one branch, one small PR. No changes outside the scope of the spec, except minor improvements to code you are already touching.
* Never push to `main`. Never use `--no-verify` or any other way of skipping checks.
* Do not add dependencies unless they are approved in the spec or in an ADR.
* If a check fails, fix the cause. Do not disable rules or add lint exceptions without written justification in the PR.

## Architecture

The package lives in `src/aretz_texture/` (ADR 0002). Packages and dependency direction (verified by `lint-imports`):

* `core/`: data model. Imports nothing from the project.
* `analysis/` and `voicing/`: depend only on `core/`.
* `ingest/`: reads files and produces `core/` objects.
* `render/`: consumes cuts of the event tree. Never imports `analysis/` or `voicing/`.
* `eval/`: may import everything; nothing imports `eval/`.

**Pure core.** `core/`, `analysis/` and `voicing/` do not read or write files, use the network or global state, or generate randomness. They receive data and return data. All I/O lives in `ingest/` and `render/`. This guarantees that the analysis is deterministic.

## Code rules

### Names
* Musical terms follow `docs/glossary.md`, which defines each term as the code uses it. If a term is missing, add it in the same PR.
* Intention revealing names, no abbreviations: `harmonic_window`, not `hw`. The only valid abbreviations are musical domain ones listed in the glossary.
* PEP 8: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.

### Functions and classes
* One responsibility per function. If describing it requires "and", split it.
* Size is controlled by complexity, not by line count: ruff limits cyclomatic complexity, arguments and branches.
* Duplication: abstract at the third occurrence, not before. Two similar repetitions are better than the wrong abstraction.

### Types and data
* Every function fully annotated, arguments and return, with modern builtin types (`list[int]`, `X | None`).
* Data models with pydantic, immutable (`frozen=True`).
* `Any` is forbidden except at the boundary with music21, encapsulated in `ingest/`.

### Validation and errors
* Validate at the edges: ingestion, configuration and, later, the API. Inside the core, trust the types and do not revalidate.
* Errors use domain exceptions defined in `core/errors.py` (`UnparseableScoreError`, `AmbiguousHarmonyError`). Never return `None` to signal an error.
* Never catch generic exceptions (`except Exception`) without reraising them.

### Configuration
* No magic numbers. Weights, thresholds, spans and tolerances go into typed configuration with a name, a unit and one line explaining their musical meaning.

### Concurrency
* Code is synchronous. Do not use `async` in the core or in ingestion. It will be considered only for the API, when it exists.

### Comments and docstrings
* Google style docstrings on every public function, class and module.
* Comments explain why, never what. A musical decision that is not obvious references its ADR (`# See ADR 0007: suspensions resolve to the following chord`).
* No commented out code and no `TODO` without an associated issue.

## Tests and definition of done

* One concept per test, a name that describes the behavior, arrange, act, assert structure.
* Voice leading rules (parallels, crossings, spans) are tested with hypothesis in addition to specific cases.
* Slow tests are marked `@pytest.mark.slow`.
* Scores protected by copyright never enter the repository (ADR 0001).
* A feature is done when:
  1. it meets all acceptance criteria of its spec,
  2. its edge cases have tests,
  3. it passes the commit checks and CI, including the corpus evaluation with no regressions,
  4. it does not break existing public interfaces, or the change is justified in an ADR,
  5. documentation and glossary are updated.

## Review guidelines

Review the diff against the corresponding spec and against these rules.

### P0
* Core code (`core/`, `analysis/`, `voicing/`) with I/O, global state, randomness or any source of nondeterminism.
* Imports that violate the dependency direction.
* Changes that alter musical results without a test covering them or an explanation in the PR.
* Disabled checks, silenced lint rules or skipped tests without justification.
* New dependencies without approval in a spec or ADR.
* Scores protected by copyright, secrets or credentials added to the repository.

### P1
* Names that do not reveal intention or that contradict the glossary.
* Functions with more than one responsibility.
* Magic numbers outside typed configuration.
* Errors signaled with `None` or generic exceptions.
* Abstractions created before the third repetition, or duplication from the third repetition on.
* Public functions without type annotations or docstring.
* Comments that describe what the code does instead of why; musical decisions without a reference to their ADR.
* New logic without tests, or tests that verify several concepts at once.
* Use of `async` outside the API.
* Changes outside the scope of the spec.
* Code, comments or documentation not written in English.
* Writing errors in documentation.
