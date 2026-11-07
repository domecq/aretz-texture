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

### Protecting main

* The repository only allows squash merges and deletes the branch after merging. Each commit on `main` is one pull request.
* A ruleset on `main` forbids deleting it and force pushes, requires a pull request, requires the `checks` job to pass on a branch up to date with `main`, and requires every review thread to be resolved, so Codex comments cannot be ignored silently. Required approvals stay at zero, because GitHub does not let authors approve their own pull requests; merging is Nico's approval.
* The protection was applied after CI passed on the quality tooling pull request and before merging it, so the first protected merge was also the first proof that the rules work.
* Deleting merged branches loses nothing: the pull request keeps its commits, diff, reviews and CI results, and can restore the branch.

### Agents and hooks

* Claude Code runs on the Claude subscription, for a fixed cost. API credits are reserved for unattended automation.
* Codex review runs through the ChatGPT Plus plan.
* Five subagents in `.claude/agents/`: architect (Opus), implementer (Sonnet), explorer, QA runner and documenter (Haiku). The explorer is read only and the QA runner cannot edit files.
* Layer 1 hook: lint and format every edited Python file. Layer 2 hook: block `--no-verify`, commits without the pre-commit hook installed and pushes to `main`.
* The first Codex review, on the pull request that added the hooks, found three real bypasses in the layer 2 guard, each reproduced against git: multiline commands were checked only on their first line, `git commit -n` skipped the hooks, and `git push origin HEAD` from `main` was allowed. Fixing them surfaced two more of the same kind (the pre-commit `SKIP` variable and `core.hooksPath`) plus abbreviated long options such as `--no-veri`. All of them now have tests.
* Layer 2 was redesigned while building it. The plan was to rerun every check before each commit, but the pre-commit git hook already does that and its output already reaches the agent. The useful job left for layer 2 was making sure layer 3 cannot be skipped. Both hooks have their own tests.

## Notes for the article

* Small environment details (an SSH passphrase, an author name) surfaced only when the first real commits were made. In a public repository they matter from the first commit, because the history cannot be cleaned without rewriting it.
* Running every check through the lock file keeps one source of truth for tool versions across the developer machine, the agents and CI.
* The guards for agents are code like any other: they live in the repository, follow the same rules and have tests. The first lint run on the hook scripts flagged a function with too many returns, so the rules applied to the tooling from day one.
* Model diversity in review paid off on its first pull request: the code was written and tested by Claude, and the gaps were found by Codex, each with a reproduction. A guard parsing shell commands is a classic place for edge cases one author does not think of.
