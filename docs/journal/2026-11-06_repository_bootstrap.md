# Journal: repository bootstrap and quality tooling

Date: November 6, 2026
Phase: F0

## Goal

Create the public repository, bring in the design documents and set up the quality checks that every later change must pass.

## What happened

### Repository

* Created `aretz-texture` on GitHub as a public repository with the MIT License, and initialized the package with `uv init --package` (src layout, ADR 0002).
* The first commit went straight to `main`, the only exception to the rule: branch protection can only be applied to a branch that already exists.
* The documentation (AGENTS.md, CLAUDE.md, architecture, pipeline, ADRs and journal) entered through a pull request, so the rule "everything through a PR" shows in the history from the second commit on.

### Identity and signing

* Git was already configured to sign commits with an SSH key, which asked for the key passphrase on every commit. The passphrase now lives in the macOS keychain, and the key is registered on GitHub as a signing key, so commits show as verified.
* The commit author was the local account name. It now uses the real name, since the repository is public.
* Squash merges are signed by GitHub with its own GPG key; verifying them locally requires gpg, which is not installed. They show as verified on GitHub.

### Quality tooling

* Single Python version (3.12) everywhere: locally, in pre-commit and in CI. No version matrix for now.
* ruff, pyright in strict mode, pytest, hypothesis, pytest-cov and import-linter as development dependencies.
* import-linter contracts encode the dependency direction from AGENTS.md. The subpackages exist from the start, empty, because the contracts fail if they name modules that do not exist.
* pre-commit runs the project tools through `uv run --frozen`, so their versions come from `uv.lock`, the same ones CI uses. It also refuses commits made directly on `main`.
* CI runs a single job named `checks`, which becomes the required status check for `main`.

## Notes for the article

* Small environment details (an SSH passphrase, an author name) surfaced only when the first real commits were made. In a public repository they matter from the first commit, because the history cannot be cleaned without rewriting it.
* Running every check through the lock file keeps one source of truth for tool versions across the developer machine, the agents and CI.
