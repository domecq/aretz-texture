"""Criteria 19 and 20: reading back the piano files that the renderer writes."""

from fractions import Fraction
from pathlib import Path

import pytest
from tests.core_builders import divided_event, event, part_of, score_of

from aretz_texture.core.errors import UnparseableScoreError, UnsupportedScoreError
from aretz_texture.core.grand_staff import PIANO_LAYOUT
from aretz_texture.core.notation import TieType
from aretz_texture.core.score import KeySignatureChange, Score, TimeSignatureChange
from aretz_texture.ingest.sources import read_grand_staff_file, read_score
from aretz_texture.render.full_score import write_full_score
from aretz_texture.render.piano_score import write_piano_score


def without_part_metadata(score: Score) -> Score:
    parts = tuple(
        part.model_copy(update={"name": None, "instrument_name": None}) for part in score.parts
    )
    return score.model_copy(update={"parts": parts})


def piano_round_trip(score: Score, path: Path) -> Score:
    write_piano_score(score, PIANO_LAYOUT, path)
    return read_grand_staff_file(path, PIANO_LAYOUT)


def test_bwv66_6_survives_the_piano_round_trip_without_part_names(tmp_path: Path) -> None:
    original = read_score("bwv66.6").score

    returned = piano_round_trip(original, tmp_path / "piano.musicxml")

    assert returned == without_part_metadata(original)
    assert all(part.name is None and part.instrument_name is None for part in returned.parts)


def test_a_pickup_bar_survives_the_piano_round_trip(tmp_path: Path) -> None:
    original = read_score("bwv66.6").score

    returned = piano_round_trip(original, tmp_path / "piano.musicxml")

    assert returned.bars == original.bars
    assert returned.bars[0].number == 0
    assert returned.pickup_duration() == original.pickup_duration() == 1


def test_divided_events_ties_per_pitch_and_fermatas_survive_the_piano_round_trip(
    tmp_path: Path,
) -> None:
    divided_bass = divided_event(0, 2, ("D3", TieType.START), ("D2", None), fermata=True)
    tied_to = divided_event(2, 2, ("D3", TieType.STOP), ("D2", None))
    score = score_of(
        part_of([event(0, 4, "E5", fermata=True)]),
        part_of([event(0, 4, "C5")]),
        part_of([event(0, 4, "G3", tie=TieType.START), event(4, 4, "G3", tie=TieType.STOP)]),
        part_of([divided_bass, tied_to]),
    )

    returned = piano_round_trip(score, tmp_path / "piano.musicxml")

    assert returned == score


def test_a_key_signature_change_in_the_middle_of_a_bar_survives_the_piano_round_trip(
    tmp_path: Path,
) -> None:
    keys = [
        KeySignatureChange(onset=Fraction(0), sharps=0),
        KeySignatureChange(onset=Fraction(6), sharps=2),
    ]
    score = score_of(
        part_of([event(0, 4), event(4, 2), event(6, 2)], key_signatures=keys),
        part_of([event(0, 4, "E4"), event(4, 4, "E4")], key_signatures=keys),
        part_of([event(0, 4, "C3"), event(4, 4, "C3")], key_signatures=keys),
        part_of([event(0, 4, "C2")], key_signatures=keys),
    )

    returned = piano_round_trip(score, tmp_path / "piano.musicxml")

    assert returned == score


def test_a_divided_event_and_a_whole_rest_keep_the_bar_length_on_the_grand_staff(
    tmp_path: Path,
) -> None:
    # Same music21 behavior as in the full score: chords are not counted when it decides
    # whether a measure is a whole bar rest. Each staff holds two divided events here.
    three_two = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)
    parts = [
        part_of([divided_event(0, 2, (pitch, None), (lower, None))])
        for pitch, lower in (("G5", "E5"), ("C5", "A4"), ("E4", "C4"), ("C3", "A2"))
    ]
    score = score_of(*parts, bar_durations=(6,), time_signatures=(three_two,))

    assert piano_round_trip(score, tmp_path / "chords.musicxml") == without_part_metadata(score)


def test_a_silent_part_does_not_stretch_a_rest_of_the_other_part_on_its_staff(
    tmp_path: Path,
) -> None:
    # Part 2 is silent in bar 2, so its staff voice is a whole bar rest there; music21 would
    # stretch the whole rest of part 1 on the same staff when it reads the file back.
    three_two = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)
    score = score_of(
        part_of([event(0, 6, pitch="G4"), event(6, Fraction(1, 2), pitch="E5")]),
        part_of([event(0, 6, pitch="C4")]),
        part_of([event(0, 6, pitch="E3"), event(6, 6, pitch="E3")]),
        part_of([event(0, 6, pitch="C3"), event(6, 6, pitch="C3")]),
        bar_durations=(6, 6),
        time_signatures=(three_two,),
    )

    assert piano_round_trip(score, tmp_path / "silent.musicxml") == without_part_metadata(score)


def test_a_file_that_is_not_a_grand_staff_is_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "full.musicxml"
    write_full_score(score_of(part_of([event(0, 4)])), path)

    with pytest.raises(UnsupportedScoreError, match="two staves"):
        read_grand_staff_file(path, PIANO_LAYOUT)


def test_a_missing_file_is_unparseable(tmp_path: Path) -> None:
    with pytest.raises(UnparseableScoreError):
        read_grand_staff_file(tmp_path / "missing.musicxml", PIANO_LAYOUT)
