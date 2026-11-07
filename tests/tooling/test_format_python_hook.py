"""Tests for the Claude Code hook that formats and lints edited Python files."""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parents[2] / ".claude" / "hooks" / "format_python.py"
OK = 0
REPORTED = 2


def run_hook(file_path: Path) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(file_path)}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_ignores_files_that_are_not_python(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("x   =   1\n")

    assert run_hook(notes).returncode == OK
    assert notes.read_text() == "x   =   1\n"


def test_formats_python_file(tmp_path: Path) -> None:
    module = tmp_path / "module.py"
    module.write_text('"""Example."""\n\nx   =   1\n')

    assert run_hook(module).returncode == OK
    assert module.read_text() == '"""Example."""\n\nx = 1\n'


def test_removes_unused_import_and_formats_the_result(tmp_path: Path) -> None:
    module = tmp_path / "module.py"
    module.write_text('"""Example."""\n\nimport os\nx   =   1\n')

    assert run_hook(module).returncode == OK
    assert module.read_text() == '"""Example."""\n\nx = 1\n'


def test_reports_problems_ruff_cannot_fix(tmp_path: Path) -> None:
    module = tmp_path / "module.py"
    module.write_text('"""Example."""\n\nvalue = undefined_name\n')

    result = run_hook(module)

    assert result.returncode == REPORTED
    assert "undefined_name" in result.stderr
