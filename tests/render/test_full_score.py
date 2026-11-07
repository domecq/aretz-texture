"""Criteria 15 and 16: the full score writer, one staff per part."""

from pathlib import Path

from music21 import stream
from tests.music21_builders import parse_score

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
