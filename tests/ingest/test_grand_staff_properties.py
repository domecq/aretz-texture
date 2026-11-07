"""Criterion 19, property: any four part score survives the piano round trip."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from tests.strategies import four_part_scores

from aretz_texture.core.grand_staff import PIANO_LAYOUT, piano_layout
from aretz_texture.core.score import Score
from aretz_texture.ingest.sources import read_grand_staff_file
from aretz_texture.render.piano_score import write_piano_score


@pytest.mark.slow
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(score=four_part_scores())
def test_any_four_part_score_survives_the_piano_round_trip_without_part_names(
    score: Score,
) -> None:
    layout = piano_layout(score)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "piano.musicxml"

        write_piano_score(score, layout, path)
        returned = read_grand_staff_file(path, PIANO_LAYOUT)

    expected_parts = tuple(
        part.model_copy(update={"name": None, "instrument_name": None}) for part in score.parts
    )
    assert returned == score.model_copy(update={"parts": expected_parts})
