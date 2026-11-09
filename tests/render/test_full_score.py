"""Criteria 15 and 16: the full score writer, one staff per part."""

from fractions import Fraction
from pathlib import Path

import pytest
from music21 import expressions, note, stream
from tests.core_builders import FOUR_FOUR, divided_event, event, part_of, score_of
from tests.music21_builders import parse_score

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.notation import TieType
from aretz_texture.core.score import KeySignatureChange, Score, TimeSignatureChange
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


def score_with_voices_in_second_bar() -> Score:
    """Return a one part score whose notated voice 1 is silent in bar 2, where voice 2 sounds."""
    return score_of(part_of([event(0, 4)], [event(4, 4)]))


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


def test_notated_voices_survive_the_full_score_round_trip(tmp_path: Path) -> None:
    original, returned = round_trip("bach/bwv248.23-2", tmp_path / "chorale.musicxml")

    assert returned == original
    assert any(len(part.voices) == 2 for part in original.parts)


def test_a_bar_with_several_notated_voices_holds_numbered_music21_voices(tmp_path: Path) -> None:
    score = score_with_voices_in_second_bar()
    path = tmp_path / "voices.musicxml"

    write_full_score(score, path)

    measures = list(parse_score(path).parts[0].getElementsByClass(stream.Measure))
    assert not measures[0].hasVoices()
    assert [voice.id for voice in measures[1].voices] == ["1", "2"]


def test_a_notated_voice_that_is_silent_in_a_bar_is_a_whole_bar_rest(tmp_path: Path) -> None:
    score = score_with_voices_in_second_bar()
    path = tmp_path / "voices.musicxml"

    write_full_score(score, path)

    measures = list(parse_score(path).parts[0].getElementsByClass(stream.Measure))
    silent_voice = measures[1].voices[0]
    assert [(rest.offset, rest.quarterLength) for rest in silent_voice.notesAndRests] == [(0, 4)]
    assert all(isinstance(element, note.Rest) for element in silent_voice.notesAndRests)


def key_change(onset: int, sharps: int) -> KeySignatureChange:
    return KeySignatureChange(onset=Fraction(onset), sharps=sharps)


def round_trip_built(score: Score, path: Path) -> Score:
    write_full_score(score, path)
    return read_score(str(path)).score


def test_a_key_signature_change_in_the_middle_of_a_bar_keeps_its_onset(tmp_path: Path) -> None:
    keys = [key_change(0, 0), key_change(6, 2)]
    score = score_of(
        part_of([event(0, 2), event(2, 2), event(4, 2), event(6, 2)], key_signatures=keys)
    )

    assert round_trip_built(score, tmp_path / "key.musicxml") == score


def test_a_key_signature_change_inside_a_rest_keeps_its_onset(tmp_path: Path) -> None:
    keys = [key_change(0, 0), key_change(6, -1)]
    score = score_of(part_of([event(0, 4)], key_signatures=keys))

    assert round_trip_built(score, tmp_path / "key.musicxml") == score


def test_a_key_signature_change_in_the_middle_of_a_bar_with_voices_keeps_its_onset(
    tmp_path: Path,
) -> None:
    keys = [key_change(0, 0), key_change(6, 3)]
    upper = [event(0, 4), event(4, 2), event(6, 2)]
    lower = [event(0, 4), event(4, 4, "E4")]
    score = score_of(part_of(upper, lower, key_signatures=keys))

    assert round_trip_built(score, tmp_path / "key.musicxml") == score


def test_a_key_signature_change_inside_a_note_of_every_voice_is_refused(tmp_path: Path) -> None:
    keys = [key_change(0, 0), key_change(5, 2)]
    score = score_of(part_of([event(4, 4)], key_signatures=keys))

    with pytest.raises(UnsupportedScoreError, match="inside a note"):
        write_full_score(score, tmp_path / "key.musicxml")


def test_a_time_signature_change_on_a_bar_line_survives(tmp_path: Path) -> None:
    three_four = TimeSignatureChange(onset=Fraction(8), numerator=3, denominator=4)
    score = score_of(
        part_of([event(0, 4), event(4, 4), event(8, 3)]),
        bar_durations=(4, 4, 3),
        time_signatures=(FOUR_FOUR, three_four),
    )

    assert round_trip_built(score, tmp_path / "meter.musicxml") == score


def test_fermatas_are_written_upright(tmp_path: Path) -> None:
    score = score_of(part_of([event(0, 4, fermata=True), event(4, 4)]))
    path = tmp_path / "fermata.musicxml"

    write_full_score(score, path)

    fermatas = [
        expression
        for element in parse_score(path).parts[0].recurse().notes
        for expression in element.expressions
        if isinstance(expression, expressions.Fermata)
    ]
    assert [fermata.type for fermata in fermatas] == ["upright"]


def test_a_triplet_of_tied_notes_is_not_merged_into_one_note(tmp_path: Path) -> None:
    third = Fraction(1, 3)
    triplet = [
        event(0, third, tie=TieType.START),
        event(third, third, tie=TieType.CONTINUE),
        event(2 * third, third, tie=TieType.STOP),
    ]
    score = score_of(part_of([*triplet, event(1, 3)]), bar_durations=(4,))

    assert round_trip_built(score, tmp_path / "triplet.musicxml") == score


def test_a_silent_pickup_of_four_quarters_in_three_two_time_keeps_its_length(
    tmp_path: Path,
) -> None:
    three_two = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)
    score = score_of(part_of([event(4, 6)]), bar_durations=(4, 6), time_signatures=(three_two,))

    assert round_trip_built(score, tmp_path / "pickup.musicxml") == score


@pytest.mark.parametrize(
    ("numerator", "denominator", "bar_duration", "chord_duration"),
    [(3, 2, 6, 2), (6, 4, 6, 2), (12, 4, 12, 4)],
)
def test_a_divided_event_followed_by_a_whole_or_breve_rest_keeps_the_bar_length(
    tmp_path: Path, numerator: int, denominator: int, bar_duration: int, chord_duration: int
) -> None:
    # music21 counts chords as neither notes nor rests when it reads a measure, so a bar
    # holding only chords and one undotted whole or breve rest is taken for a whole bar
    # rest and stretched to the meter.
    meter = TimeSignatureChange(onset=Fraction(0), numerator=numerator, denominator=denominator)
    chord_event = divided_event(0, chord_duration, ("E4", None), ("C4", None))
    score = score_of(
        part_of([chord_event]), bar_durations=(bar_duration,), time_signatures=(meter,)
    )

    assert round_trip_built(score, tmp_path / "chord_and_rest.musicxml") == score


def test_a_silent_voice_does_not_stretch_a_rest_of_another_voice(tmp_path: Path) -> None:
    # music21 writes a rest that fills a bar inside a voice as a whole bar rest, and on
    # reading it stretches the first rest of the measure to the meter, whichever voice it
    # belongs to. Here that would be the whole rest music21 writes in voice 1 of bar 2.
    three_two = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)
    voice_one = [event(6, Fraction(1, 2))]
    voice_two = [event(0, 6, pitch="G3")]  # silent in bar 2, where voices 1 and 3 sound
    voice_three = [event(10, 1, pitch="E3")]
    score = score_of(
        part_of(voice_one, voice_two, voice_three),
        bar_durations=(6, 6),
        time_signatures=(three_two,),
    )

    assert round_trip_built(score, tmp_path / "silent_voice.musicxml") == score
