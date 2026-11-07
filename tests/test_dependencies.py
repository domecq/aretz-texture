"""Runtime dependencies declared by ADR 0003."""

import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_runtime_dependencies_have_the_bounds_of_adr_0003() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    dependencies = pyproject["project"]["dependencies"]

    assert "music21>=10.5,<11" in dependencies
    assert "pydantic>=2.10,<3" in dependencies


def test_lock_file_pins_both_runtime_dependencies() -> None:
    lock = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text())

    locked_names = {package["name"] for package in lock["package"]}

    assert {"music21", "pydantic"} <= locked_names
