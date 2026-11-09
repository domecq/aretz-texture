"""Criterion 15, property: any score survives the full score round trip."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from tests.strategies import scores

from aretz_texture.core.score import Score
from aretz_texture.ingest.sources import read_score
from aretz_texture.render.full_score import write_full_score


@pytest.mark.slow
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(score=scores())
def test_any_score_survives_the_full_score_round_trip(score: Score) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "score.musicxml"

        write_full_score(score, path)

        assert read_score(str(path)).score == score
