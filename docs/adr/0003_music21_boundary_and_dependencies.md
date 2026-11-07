# ADR 0003: music21 boundary and runtime dependencies

Date: November 7, 2026
Status: Proposed

## Context

Until now the package has had no runtime dependencies. Spec 001 (chorale round trip) is the first end to end slice: it reads a four voice chorale, holds it in the core data model and writes it back as a piano score in MusicXML. That needs two libraries:

* **music21**, the musical base chosen in the architecture (section 2). It parses MusicXML, ships the Bach chorale corpus used for evaluation (architecture, section 9) and writes MusicXML.
* **pydantic**, chosen in the pipeline document (section 4) for the immutable data model of the event tree.

`AGENTS.md` allowed `Any` only "at the boundary with music21, encapsulated in `ingest/`". Writing MusicXML also requires building music21 objects, so the boundary has to include `render/` as well.

music21 ships partial type annotations (it includes a `py.typed` marker, confirmed in version 10.5.2), but many of its members are untyped or typed loosely, so pyright in strict mode reports unknown types wherever music21 objects are used.

Facts checked on November 7, 2026:

* music21 10.5.2 is the latest stable release on PyPI (October 28, 2026), requires Python 3.11 or later and is released under the BSD 3 clause license (SPDX `BSD-3-Clause`; the LICENSE file in the repository reads "Copyright (c) 2006-2026 Michael Scott Asato Cuthbert").
* pydantic 2.14 is the current release line on PyPI (2.14.3 as of November 7, 2026). Since version 2.10, `fractions.Fraction` is a first class type in pydantic, which the core uses for onsets and durations. pydantic is released under the MIT License (confirmed in its package metadata).

## Decision

1. music21 and pydantic become runtime dependencies, declared in `[project.dependencies]` with a lower bound on the version verified here and an upper bound below the next major version: `music21>=10.5,<11` and `pydantic>=2.10,<3`.
2. music21 may be imported only in `ingest/` and `render/`. `core/`, `analysis/`, `voicing/`, `eval/` and the command line module never import it. An import-linter contract enforces this.
3. Every module that imports music21 is a boundary module. It converts music21 objects to core objects (in `ingest/`) or core objects to music21 objects (in `render/`), and exposes only core types and standard library types in its public functions.
4. pyright stays in strict mode for the whole project. In boundary modules only, a file level pyright comment disables the rules that report unknown types coming from music21 (the `reportUnknown*` family and, if it fires, `reportMissingTypeStubs`). The comment references this ADR. No other rule is relaxed and no other module carries the comment.
5. `Any` is allowed only inside boundary modules, and never in their public signatures.

## Rationale

* Reading and writing are both conversions between music21 and the core model. Keeping both at the edges preserves the pure core: `core/`, `analysis/` and `voicing/` still receive data and return data.
* A file level comment is the narrowest pyright mechanism that matches the boundary exactly: it applies to the modules that touch music21 and nothing else. Relaxing the rules in the global configuration would hide real typing errors in the rest of the code.
* Containing music21 in a few modules makes a future change of library, or a second input adapter such as OMR (architecture, section 2), a local change.
* BSD 3 clause and MIT are permissive licenses compatible with the MIT License of the project (ADR 0001).
* Upper bounds below the next major version protect the musical results from breaking changes in parsing; `uv.lock` pins the exact versions used locally and in CI.

## Consequences

* `AGENTS.md`, section "Types and data", now names `ingest/` and `render/` as the music21 boundary.
* `pyproject.toml` gains the two runtime dependencies and an import-linter contract that forbids music21 outside `ingest/` and `render/`. Forbidding an external package requires `include_external_packages = true` in the import-linter root options.
* `eval/` cannot iterate the music21 corpus directly; it asks `ingest/` for the list of chorale identifiers.
* `ingest/` and `render/` cannot import each other, so a small amount of conversion logic (for example, pitch spelling) exists on both sides. The grand staff layout shared by both lives in `core/`.
* Installing the package now downloads music21 and its own dependencies, which makes the environment noticeably larger.
* Moving to music21 11, currently in beta, will require a new ADR or an update of this one after checking the round trip evaluation.
