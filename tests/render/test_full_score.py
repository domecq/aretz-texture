"""Criteria 15 and 16: the full score writer, one staff per part."""

from pathlib import Path

from music21 import stream
from tests.music21_builders import parse_score

from aretz_texture.core.notation import TieType
from aretz_texture.core.score import Score
from aretz_texture.ingest.sources import read_score
from aretz_texture.render.full_score import write_full_score


def test_bwv27_6_full_score_has_five_parts_with_the_source_names(tmp_path: Path) -> None:
    path = tmp_path / "bwv27_6.musicxml"
    original = read_score("bach/bwv27.6").score

    write_full_score(original, path)

    written = parse_score(path)
    assert [part.partName for part in written.parts] == [
        "Soprano 1",
        "Soprano 2",
        "Alto",
        "Tenor",
        "Bass",
    ]


def test_a_bar_with_only_notated_voice_one_is_written_without_music21_voices(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bwv27_6.musicxml"
    write_full_score(read_score("bach/bwv27.6").score, path)

    written = parse_score(path)

    for part in written.parts:
        for measure in part.getElementsByClass(stream.Measure):
            assert not measure.hasVoices()


def round_trip(identifier: str, path: Path) -> tuple[Score, Score]:
    original = read_score(identifier).score
    write_full_score(original, path)
    return original, read_score(str(path)).score


def test_bwv27_6_survives_the_full_score_round_trip(tmp_path: Path) -> None:
    original, returned = round_trip("bach/bwv27.6", tmp_path / "chorale.musicxml")

    assert returned == original


def test_a_pickup_bar_survives_the_full_score_round_trip(tmp_path: Path) -> None:
    original, returned = round_trip("bwv66.6", tmp_path / "chorale.musicxml")

    assert returned.bars == original.bars
    assert returned.bars[0].number == 0
    assert returned.pickup_duration() == original.pickup_duration() == 1


def test_divided_events_with_ties_per_pitch_survive_the_full_score_round_trip(
    tmp_path: Path,
) -> None:
    original, returned = round_trip("bach/bwv248.9-1", tmp_path / "chorale.musicxml")

    assert returned == original
    assert any(len(event.pitches) > 1 for part in original.parts for event in part.voices[0].events)


def test_fermatas_survive_the_full_score_round_trip(tmp_path: Path) -> None:
    original, returned = round_trip("bwv66.6", tmp_path / "chorale.musicxml")

    assert returned == original
    assert any(event.fermata for event in original.parts[0].voices[0].events)


def test_a_tie_across_a_bar_line_survives_the_full_score_round_trip(tmp_path: Path) -> None:
    original, returned = round_trip("bach/bwv269", tmp_path / "chorale.musicxml")

    assert returned == original
    assert any(
        pitch.tie is TieType.START
        for part in original.parts
        for event in part.voices[0].events
        for pitch in event.pitches
    )
