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


def test_allows_no_verify_inside_commit_message(feature_repo: Path) -> None:
    result = run_hook('git commit -m "Explain why --no-verify is banned"', feature_repo)

    assert result.returncode == ALLOWED


def test_blocks_commit_without_pre_commit_hook(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", "feat/example", with_pre_commit_hook=False)

    result = run_hook('git commit -m "Add test"', repo)

    assert result.returncode == BLOCKED
    assert "pre-commit install" in result.stderr


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


def test_blocks_push_without_refspec_while_on_main(main_repo: Path) -> None:
    assert run_hook("git push", main_repo).returncode == BLOCKED


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
