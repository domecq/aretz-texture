"""`round_trip_chorale` on single corpus chorales."""

# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
from pathlib import Path

import pytest
from music21 import note, pitch
from tests.music21_builders import bar_of, part_of, score_of

from aretz_texture.eval.round_trip import ChoraleOutcome, round_trip_chorale


def test_a_four_part_chorale_is_identical_through_both_routes(tmp_path: Path) -> None:
    result = round_trip_chorale("bwv66.6", tmp_path)

    assert result.outcome is ChoraleOutcome.IDENTICAL
    assert result.part_count == 4
    assert result.differences == ()
    assert result.grand_staff_skip_reason == ""
    assert result.unsupported_reason == ""


def test_a_chorale_with_more_than_four_parts_skips_the_grand_staff(tmp_path: Path) -> None:
    result = round_trip_chorale("bach/bwv27.6", tmp_path)

    assert result.outcome is ChoraleOutcome.IDENTICAL
    assert result.part_count == 5
    assert "5 parts" in result.grand_staff_skip_reason


def test_a_score_ingestion_rejects_is_unsupported_with_its_reason(tmp_path: Path) -> None:
    quarter_tone = note.Note("C4", quarterLength=4.0)
    quarter_tone.pitch.accidental = pitch.Accidental("half-sharp")
    path = tmp_path / "quarter_tone.musicxml"
    score_of(part_of([bar_of([quarter_tone])])).write("musicxml", fp=path)

    result = round_trip_chorale(str(path), tmp_path)

    assert result.outcome is ChoraleOutcome.UNSUPPORTED
    assert result.part_count == 0
    assert "microtonal" in result.unsupported_reason
    assert result.differences == ()


@pytest.mark.parametrize("identifier", ["bach/bwv299", "bach/bwv315"])
def test_a_chorale_with_grace_notes_is_identical_through_both_routes(
    identifier: str, tmp_path: Path
) -> None:
    result = round_trip_chorale(identifier, tmp_path)

    assert result.outcome is ChoraleOutcome.IDENTICAL
    assert result.part_count == 4
    assert result.grand_staff_skip_reason == ""
