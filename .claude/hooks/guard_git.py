"""Claude Code PreToolUse hook that guards git commands run by agents.

Layer 2 of the quality checks (docs/agent-pipeline.md, section 10). It blocks:

* commits or pushes that skip git hooks with ``--no-verify``,
* commits when the pre-commit git hook is not installed, so the checks of
  layer 3 always run, including in fresh cloud sessions,
* any push that would update ``main``.

Exit code 2 blocks the tool call and sends the message on stderr to the agent.
"""

import json
import shlex
import subprocess
import sys
from pathlib import Path

ALLOW = 0
BLOCK = 2
PROTECTED_BRANCH = "main"
COMMAND_SEPARATORS = frozenset({"&&", "||", ";", "|", "&"})
GIT_OPTIONS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree"})
PUSH_EVERYTHING_FLAGS = frozenset({"--all", "--mirror"})


def split_segments(command: str) -> list[list[str]]:
    """Split a shell command into simple commands, separated by shell operators."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    segments: list[list[str]] = [[]]
    for token in lexer:
        if token in COMMAND_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def parse_git(segment: list[str], cwd: Path) -> tuple[str, list[str], Path] | None:
    """Return the git subcommand, its arguments and the working directory, if any."""
    if not segment or Path(segment[0]).name != "git":
        return None
    index = 1
    workdir = cwd
    while index < len(segment) and segment[index].startswith("-"):
        option = segment[index]
        if option in GIT_OPTIONS_WITH_VALUE and index + 1 < len(segment):
            if option == "-C":
                workdir = cwd / segment[index + 1]
            index += 2
        else:
            index += 1
    if index >= len(segment):
        return None
    return segment[index], segment[index + 1 :], workdir


def current_branch(workdir: Path) -> str | None:
    """Return the checked out branch, or None when HEAD is detached or unknown."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def pre_commit_hook_installed(workdir: Path) -> bool:
    """Tell whether the pre-commit git hook exists in the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks/pre-commit"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return (workdir / result.stdout.strip()).is_file()


def push_targets_protected_branch(arguments: list[str], workdir: Path) -> bool:
    """Tell whether a push with these arguments would update the protected branch."""
    if PUSH_EVERYTHING_FLAGS.intersection(arguments):
        return True
    positional = [argument for argument in arguments if not argument.startswith("-")]
    refspecs = positional[1:]
    if not refspecs:
        return current_branch(workdir) == PROTECTED_BRANCH
    for refspec in refspecs:
        destination = refspec.lstrip("+").rsplit(":", 1)[-1]
        if destination.removeprefix("refs/heads/") == PROTECTED_BRANCH:
            return True
    return False


def check_commit(arguments: list[str], workdir: Path) -> str | None:
    """Return the reason to block a commit, or None to allow it."""
    if "--no-verify" in arguments:
        return "Skipping git hooks with --no-verify is not allowed (AGENTS.md, Workflow)."
    if not pre_commit_hook_installed(workdir):
        return (
            "The pre-commit git hook is not installed, so the commit checks would not run. "
            "Run `uv run pre-commit install` and commit again."
        )
    return None


def check_push(arguments: list[str], workdir: Path) -> str | None:
    """Return the reason to block a push, or None to allow it."""
    if "--no-verify" in arguments:
        return "Skipping git hooks with --no-verify is not allowed (AGENTS.md, Workflow)."
    if push_targets_protected_branch(arguments, workdir):
        return (
            f"Pushing to {PROTECTED_BRANCH} is not allowed. "
            "Push a feature branch and open a pull request (AGENTS.md, Workflow)."
        )
    return None


def check_segment(segment: list[str], cwd: Path) -> str | None:
    """Return the reason to block one simple command, or None to allow it."""
    parsed = parse_git(segment, cwd)
    if parsed is None:
        return None
    subcommand, arguments, workdir = parsed
    checks = {"commit": check_commit, "push": check_push}
    check = checks.get(subcommand)
    return check(arguments, workdir) if check is not None else None


def main() -> int:
    """Read the hook input from stdin and decide whether the command may run."""
    payload = json.loads(sys.stdin.read())
    command = str(payload.get("tool_input", {}).get("command", ""))
    cwd = Path(str(payload.get("cwd", ".")))
    try:
        segments = split_segments(command)
    except ValueError:
        # An unbalanced quote means the shell will reject the command anyway.
        return ALLOW
    for segment in segments:
        reason = check_segment(segment, cwd)
        if reason is not None:
            sys.stderr.write(reason + "\n")
            return BLOCK
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
