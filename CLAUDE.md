@AGENTS.md

## Claude Code

The conventions above apply to every agent. This section adds what is specific to Claude Code.

### Roles

Each role is a subagent in `.claude/agents/`, with its model and tools fixed there (docs/agent-pipeline.md, section 2):

* `architect` (Opus): issue to spec, algorithm design, ADRs. Writes documents only.
* `implementer` (Sonnet): approved spec to code with TDD, branch and pull request.
* `explorer` (Haiku): read only search of the code and of the music21 documentation.
* `qa-runner` (Haiku): runs every check and summarizes failures. Never edits.
* `documenter` (Haiku): docs, glossary, changelog and journal drafts.

### Delegation

* A new feature goes to `architect` first. Implementation starts only after Nico approves the spec.
* Use `explorer` to gather context instead of reading many files in the main conversation.
* Use `qa-runner` before opening or updating a pull request.
* At the end of a work session, ask `documenter` to draft the journal entry.
* Subagents without an explicit model run on Sonnet (`CLAUDE_CODE_SUBAGENT_MODEL`), never on Opus.

### Hooks

`.claude/settings.json` enables layers 1 and 2 of the quality checks (docs/agent-pipeline.md, section 10):

* After every edit, Python files are formatted and linted; problems ruff cannot fix come back to you.
* Before git commands, commits and pushes with `--no-verify`, commits without the pre-commit hook installed and pushes to `main` are blocked. If a commit is blocked because the hook is missing, run `uv run pre-commit install`.
