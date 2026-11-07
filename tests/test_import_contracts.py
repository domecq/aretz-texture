"""The import contract of ADR 0003 keeps music21 at the boundary."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def run_lint_imports(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LINT_IMPORTS), "--config", str(project / "pyproject.toml")],
        cwd=project,
        env={"PYTHONPATH": str(project / "src"), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    shutil.copy(PROJECT_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copytree(
        PROJECT_ROOT / "src", tmp_path / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    return tmp_path


def test_contracts_pass_on_the_project(project_copy: Path) -> None:
    result = run_lint_imports(project_copy)

    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("subpackage", ["core", "analysis", "voicing", "eval"])
def test_music21_import_outside_the_boundary_breaks_the_contract(
    project_copy: Path, subpackage: str
) -> None:
    offender = project_copy / "src" / "aretz_texture" / subpackage / "offender.py"
    offender.write_text('"""Imports music21 where it must not."""\n\nimport music21\n')

    result = run_lint_imports(project_copy)

    assert result.returncode != 0
    assert "music21 only at the boundary BROKEN" in result.stdout


@pytest.mark.parametrize("subpackage", ["ingest", "render"])
def test_music21_import_at_the_boundary_is_allowed(project_copy: Path, subpackage: str) -> None:
    module = project_copy / "src" / "aretz_texture" / subpackage / "boundary_module.py"
    module.write_text('"""Imports music21 at the boundary."""\n\nimport music21\n')

    result = run_lint_imports(project_copy)

    assert result.returncode == 0, result.stdout
