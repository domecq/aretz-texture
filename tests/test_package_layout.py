"""Smoke tests for the package layout."""

import importlib

import pytest

SUBPACKAGES = ("core", "ingest", "analysis", "voicing", "render", "eval")


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_is_importable_and_documented(name: str) -> None:
    module = importlib.import_module(f"aretz_texture.{name}")

    assert module.__doc__
