"""Claude Code PreToolUse hook that guards git commands run by agents.

Layer 2 of the quality checks (docs/agent-pipeline.md, section 10). It blocks:

* commits that skip git hooks, through ``--no-verify``, its short form ``-n``,
  the pre-commit ``SKIP`` variable or a redirected ``core.hooksPath``,
* commits when the pre-commit git hook is not installed, so the checks of
  layer 3 always run, including in fresh cloud sessions,
* any push that would update ``main``.

This is a guard rail for agents, not a security boundary: CI and the ruleset
on ``main`` remain the final authority.

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

# Shell operators that separate simple commands. Unquoted newlines separate them too.
SHELL_PUNCTUATION = "();<>|&\n"
COMMAND_SEPARATORS = frozenset({"&&", "||", ";", "|", "&", "\n", "(", ")"})

GIT_OPTIONS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree"})
HOOK_BYPASS_SETTING = "core.hookspath"
HOOK_BYPASS_VARIABLES = frozenset({"SKIP", "PRE_COMMIT_ALLOW_NO_CONFIG"})

NO_VERIFY = "--no-verify"
# git accepts unambiguous prefixes of long options; "--no-ve" is still ambiguous
# with "--no-verbose", so any longer prefix of "--no-verify" means the same.
SHORTEST_NO_VERIFY_PREFIX = len("--no-ver")
COMMIT_NO_VERIFY_SHORT = "n"
# Short options of git commit that take a value, attached or as the next argument.
COMMIT_SHORT_OPTIONS_WITH_VALUE = frozenset("mFCct")
# Short options of git commit whose optional value can only be attached.
COMMIT_SHORT_OPTIONS_WITH_OPTIONAL_VALUE = frozenset("Su")

PUSH_EVERYTHING_FLAGS = frozenset({"--all", "--mirror"})
CURRENT_BRANCH_ALIASES = frozenset({"HEAD", "@"})


def split_segments(command: str) -> list[list[str]]:
    """Split a shell command into simple commands, separated by shell operators."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=SHELL_PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    segments: list[list[str]] = [[]]
    for token in lexer:
        if token in COMMAND_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def split_assignments(segment: list[str]) -> tuple[dict[str, str], list[str]]:
    """Separate leading environment assignments (``NAME=value``) from the command."""
    assignments: dict[str, str] = {}
    index = 0
    while index < len(segment) and "=" in segment[index]:
        name, value = segment[index].split("=", 1)
        if not name.isidentifier():
            break
        assignments[name] = value
        index += 1
    return assignments, segment[index:]


def parse_git(segment: list[str], cwd: Path) -> tuple[str, list[str], Path, list[str]] | None:
    """Return subcommand, arguments, working directory and ``-c`` settings of a git call."""
    if not segment or Path(segment[0]).name != "git":
        return None
    index = 1
    workdir = cwd
    settings: list[str] = []
    while index < len(segment) and segment[index].startswith("-"):
        option = segment[index]
        if option in GIT_OPTIONS_WITH_VALUE and index + 1 < len(segment):
            if option == "-C":
                workdir = cwd / segment[index + 1]
            elif option == "-c":
                settings.append(segment[index + 1])
            index += 2
        else:
            index += 1
    if index >= len(segment):
        return None
    return segment[index], segment[index + 1 :], workdir, settings


def is_no_verify_long_option(argument: str) -> bool:
    """Tell whether an argument is ``--no-verify`` or an unambiguous prefix of it."""
    return len(argument) >= SHORTEST_NO_VERIFY_PREFIX and NO_VERIFY.startswith(argument)


def commit_short_flags(arguments: list[str]) -> set[str]:
    """Collect the short option letters of a git commit, skipping option values."""
    flags: set[str] = set()
    expects_value = False
    for argument in arguments:
        if expects_value:
            expects_value = False
            continue
        if argument == "--":
            break
        if not argument.startswith("-") or argument.startswith("--"):
            continue
        for position, letter in enumerate(argument[1:], start=1):
            flags.add(letter)
            if letter in COMMIT_SHORT_OPTIONS_WITH_VALUE:
                expects_value = position == len(argument) - 1
                break
            if letter in COMMIT_SHORT_OPTIONS_WITH_OPTIONAL_VALUE:
                break
    return flags


def bypasses_hooks(environment: dict[str, str], settings: list[str]) -> bool:
    """Tell whether the environment or git settings disable the pre-commit checks."""
    if HOOK_BYPASS_VARIABLES.intersection(environment):
        return True
    return any(setting.lower().startswith(HOOK_BYPASS_SETTING) for setting in settings)


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


def refspec_destination(refspec: str, workdir: Path) -> str | None:
    """Return the branch a refspec updates, resolving ``HEAD`` to the current branch."""
    source, _, explicit_destination = refspec.lstrip("+").partition(":")
    destination = explicit_destination or source
    if destination in CURRENT_BRANCH_ALIASES:
        return current_branch(workdir)
    return destination.removeprefix("refs/heads/")


def push_targets_protected_branch(arguments: list[str], workdir: Path) -> bool:
    """Tell whether a push with these arguments would update the protected branch."""
    if PUSH_EVERYTHING_FLAGS.intersection(arguments):
        return True
    positional = [argument for argument in arguments if not argument.startswith("-")]
    refspecs = positional[1:]
    if not refspecs:
        return current_branch(workdir) == PROTECTED_BRANCH
    return any(refspec_destination(refspec, workdir) == PROTECTED_BRANCH for refspec in refspecs)


def check_commit(arguments: list[str], workdir: Path) -> str | None:
    """Return the reason to block a commit, or None to allow it."""
    skips_hooks = any(is_no_verify_long_option(argument) for argument in arguments)
    if skips_hooks or COMMIT_NO_VERIFY_SHORT in commit_short_flags(arguments):
        return "Skipping git hooks with --no-verify or -n is not allowed (AGENTS.md, Workflow)."
    if not pre_commit_hook_installed(workdir):
        return (
            "The pre-commit git hook is not installed, so the commit checks would not run. "
            "Run `uv run pre-commit install` and commit again."
        )
    return None


def check_push(arguments: list[str], workdir: Path) -> str | None:
    """Return the reason to block a push, or None to allow it."""
    if any(is_no_verify_long_option(argument) for argument in arguments):
        return "Skipping git hooks with --no-verify is not allowed (AGENTS.md, Workflow)."
    if push_targets_protected_branch(arguments, workdir):
        return (
            f"Pushing to {PROTECTED_BRANCH} is not allowed. "
            "Push a feature branch and open a pull request (AGENTS.md, Workflow)."
        )
    return None


def check_segment(segment: list[str], cwd: Path) -> str | None:
    """Return the reason to block one simple command, or None to allow it."""
    environment, command = split_assignments(segment)
    parsed = parse_git(command, cwd)
    if parsed is None:
        return None
    subcommand, arguments, workdir, settings = parsed
    if subcommand == "commit" and bypasses_hooks(environment, settings):
        return (
            "Disabling git hooks through SKIP, PRE_COMMIT_ALLOW_NO_CONFIG or core.hooksPath "
            "is not allowed (AGENTS.md, Workflow)."
        )
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
