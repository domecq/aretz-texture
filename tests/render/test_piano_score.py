"""Criteria 18, 20 and 21: the piano score writer."""

from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree

from music21 import clef, expressions, layout, stream
from tests.core_builders import event, part_of, score_of
from tests.music21_builders import corpus_score, parse_score

from aretz_texture.core.grand_staff import PIANO_LAYOUT
from aretz_texture.core.score import Score
from aretz_texture.ingest.sources import read_score
from aretz_texture.render.piano_score import write_piano_score

BWV66_6 = "bwv66.6"


def write_bwv66_6(path: Path) -> Score:
    score = read_score(BWV66_6).score
    write_piano_score(score, PIANO_LAYOUT, path)
    return score


def pitch_names(container: stream.Measure | stream.Voice | stream.Part) -> list[str]:
    return [
        pitch.nameWithOctave for element in container.recurse().notes for pitch in element.pitches
    ]


def test_bwv66_6_is_one_part_of_two_staves_joined_by_a_brace(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"

    write_bwv66_6(path)

    root = ElementTree.parse(path).getroot()
    assert len(root.findall("part")) == 1
    assert root.findtext("part/measure/attributes/staves") == "2"
    written = parse_score(path)
    groups = list(written.recurse().getElementsByClass(layout.StaffGroup))
    assert len(groups) == 1
    assert groups[0].symbol == "brace"
    assert list(groups[0]) == list(written.parts)


def test_bwv66_6_upper_staff_has_a_treble_clef_and_lower_staff_a_bass_clef(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"
    write_bwv66_6(path)

    upper, lower = parse_score(path).parts

    assert isinstance(upper.recurse().getElementsByClass(clef.Clef).first(), clef.TrebleClef)
    assert isinstance(lower.recurse().getElementsByClass(clef.Clef).first(), clef.BassClef)


def test_bwv66_6_places_parts_one_and_two_above_and_three_and_four_below(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"
    write_bwv66_6(path)
    source_parts = list(corpus_score(BWV66_6).parts)

    upper, lower = parse_score(path).parts

    def voice_pitches(staff: stream.Part, voice_index: int) -> list[str]:
        return [
            name
            for measure in staff.getElementsByClass(stream.Measure)
            for name in pitch_names(measure.voices[voice_index])
        ]

    assert voice_pitches(upper, 0) == pitch_names(source_parts[0])
    assert voice_pitches(upper, 1) == pitch_names(source_parts[1])
    assert voice_pitches(lower, 0) == pitch_names(source_parts[2])
    assert voice_pitches(lower, 1) == pitch_names(source_parts[3])


def test_bwv66_6_piano_file_carries_no_staff_or_instrument_names(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"
    write_bwv66_6(path)

    root = ElementTree.parse(path).getroot()

    assert not (root.findtext("part-list/score-part/part-name") or "").strip()
    assert root.find("part-list/score-part/score-instrument") is None
    assert root.find("part-list/score-part/part-abbreviation") is None


def test_stems_point_up_in_voice_one_and_down_in_voice_two(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"
    write_bwv66_6(path)

    for staff in parse_score(path).parts:
        for measure in staff.getElementsByClass(stream.Measure):
            for element in measure.voices[0].notes:
                assert element.stemDirection == "up"
            for element in measure.voices[1].notes:
                assert element.stemDirection == "down"


def test_a_fermata_is_upright_in_voice_one_and_inverted_in_voice_two(tmp_path: Path) -> None:
    score = score_of(
        part_of([event(0, 4, fermata=True)]),
        part_of([event(0, 4, fermata=True)]),
        part_of([event(0, 4, "C3", fermata=True)]),
        part_of([event(0, 4, "C2", fermata=True)]),
    )
    path = tmp_path / "piano.musicxml"

    write_piano_score(score, PIANO_LAYOUT, path)

    first_bars = [staff.getElementsByClass(stream.Measure)[0] for staff in parse_score(path).parts]
    types = [
        [
            expression.type
            for element in measure.voices[index].notes
            for expression in element.expressions
            if isinstance(expression, expressions.Fermata)
        ]
        for measure in first_bars
        for index in (0, 1)
    ]
    assert types == [["upright"], ["inverted"], ["upright"], ["inverted"]]


def test_every_staff_voice_fills_every_bar_with_rests_in_the_gaps(tmp_path: Path) -> None:
    path = tmp_path / "piano.musicxml"
    score = write_bwv66_6(path)

    for staff in parse_score(path).parts:
        for bar, measure in zip(score.bars, staff.getElementsByClass(stream.Measure), strict=True):
            assert len(measure.voices) == 2
            for voice in measure.voices:
                assert Fraction(voice.highestTime) == bar.duration
                covered = sum(Fraction(element.quarterLength) for element in voice.notesAndRests)
                assert covered == bar.duration


def test_a_silent_part_is_a_whole_bar_rest_in_its_staff_voice(tmp_path: Path) -> None:
    score = score_of(
        part_of([event(0, 4)]),
        part_of([event(4, 4)]),
        part_of([event(0, 4, "C3")]),
        part_of([event(0, 4, "C2"), event(4, 4, "D2")]),
    )
    path = tmp_path / "piano.musicxml"

    write_piano_score(score, PIANO_LAYOUT, path)

    upper_measures = list(parse_score(path).parts[0].getElementsByClass(stream.Measure))
    first_bar_voice_two = upper_measures[0].voices[1]
    assert [e.quarterLength for e in first_bar_voice_two.notesAndRests] == [4]
    assert not first_bar_voice_two.notes
