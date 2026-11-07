"""Tests for the Claude Code hook that guards git commands."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parents[2] / ".claude" / "hooks" / "guard_git.py"
ALLOWED = 0
BLOCKED = 2


def run_hook(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def make_repo(path: Path, branch: str, *, with_pre_commit_hook: bool) -> Path:
    subprocess.run(["git", "init", "--quiet", "-b", branch, str(path)], check=True)
    if with_pre_commit_hook:
        hook_file = path / ".git" / "hooks" / "pre-commit"
        hook_file.parent.mkdir(parents=True, exist_ok=True)
        hook_file.write_text("#!/bin/sh\n")
        hook_file.chmod(0o755)
    return path


@pytest.fixture
def feature_repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo", "feat/example", with_pre_commit_hook=True)


@pytest.fixture
def main_repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo", "main", with_pre_commit_hook=True)


def test_allows_commands_that_are_not_git(feature_repo: Path) -> None:
    assert run_hook("uv run pytest", feature_repo).returncode == ALLOWED


def test_allows_commit_with_pre_commit_hook_installed(feature_repo: Path) -> None:
    assert run_hook('git commit -m "Add test"', feature_repo).returncode == ALLOWED


def test_blocks_commit_with_no_verify(feature_repo: Path) -> None:
    result = run_hook('git commit --no-verify -m "Skip"', feature_repo)

    assert result.returncode == BLOCKED
    assert "--no-verify" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        'git commit -n -m "Skip"',
        'git commit -an -m "Skip"',
        'git commit -nm "Skip"',
        'git commit --no-veri -m "Skip"',
    ],
)
def test_blocks_short_and_abbreviated_no_verify(feature_repo: Path, command: str) -> None:
    assert run_hook(command, feature_repo).returncode == BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        'SKIP=pyright git commit -m "Skip"',
        'PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "Skip"',
        'git -c core.hooksPath=/dev/null commit -m "Skip"',
        'HOOKS=/dev/null git --config-env=core.hooksPath=HOOKS commit -m "Skip"',
        'HOOKS=/dev/null git --config-env core.hooksPath=HOOKS commit -m "Skip"',
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit",
    ],
)
def test_blocks_commit_that_disables_hooks(feature_repo: Path, command: str) -> None:
    assert run_hook(command, feature_repo).returncode == BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "Explain why --no-verify is banned"',
        'git commit -m "-n is banned"',
        "git commit -mnote -a",
        'git commit -u -m "Add files"',
    ],
)
def test_allows_option_values_that_look_like_no_verify(feature_repo: Path, command: str) -> None:
    assert run_hook(command, feature_repo).returncode == ALLOWED


def test_checks_every_line_of_a_multiline_command(feature_repo: Path) -> None:
    assert run_hook("git status\ngit push origin main", feature_repo).returncode == BLOCKED


def test_keeps_newlines_inside_quoted_messages(feature_repo: Path) -> None:
    command = 'git commit -m "Title\n\ngit push origin main"'

    assert run_hook(command, feature_repo).returncode == ALLOWED


def test_blocks_commit_without_pre_commit_hook(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", "feat/example", with_pre_commit_hook=False)

    result = run_hook('git commit -m "Add test"', repo)

    assert result.returncode == BLOCKED
    assert "pre-commit install" in result.stderr


def test_blocks_commit_when_pre_commit_hook_is_not_executable(feature_repo: Path) -> None:
    (feature_repo / ".git" / "hooks" / "pre-commit").chmod(0o644)

    assert run_hook('git commit -m "Add test"', feature_repo).returncode == BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin +feat/example:refs/heads/main",
        "git push --all origin",
        "cd . && git push origin main",
    ],
)
def test_blocks_push_to_main_from_feature_branch(feature_repo: Path, command: str) -> None:
    assert run_hook(command, feature_repo).returncode == BLOCKED


@pytest.mark.parametrize("command", ["git push", "git push origin HEAD", "git push origin @"])
def test_blocks_implicit_push_while_on_main(main_repo: Path, command: str) -> None:
    assert run_hook(command, main_repo).returncode == BLOCKED


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push -u origin feat/example",
        "git push origin HEAD",
    ],
)
def test_allows_push_of_feature_branch(feature_repo: Path, command: str) -> None:
    assert run_hook(command, feature_repo).returncode == ALLOWED
