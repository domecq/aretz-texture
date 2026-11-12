# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
"""Spec 001d, criteria 30 and 31: grace notes and fermatas on rests become model objects."""

from fractions import Fraction

import pytest
from music21 import chord, duration, expressions, note, tie
from tests.core_builders import grace_note, rest_fermata
from tests.music21_builders import bar_of, part_of, score_of, voices_bar, whole_note

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.notation import TieType
from aretz_texture.ingest.music21_conversion import convert_score

QUARTER = 1.0


def music21_grace(name: str = "B-4", kind: str = "eighth", slash: bool = True) -> note.Note:
    grace = note.Note(name, type=kind).getGrace()
    assert grace is not None
    assert isinstance(grace.duration, duration.GraceDuration)
    grace.duration.slash = slash
    return grace


def fermata_rest(length: float) -> note.Rest:
    rest = note.Rest(quarterLength=length)
    rest.expressions.append(expressions.Fermata())
    return rest


def test_a_grace_note_becomes_a_grace_note_of_its_voice_with_its_symbol() -> None:
    measure = bar_of([note.Note("G4", quarterLength=QUARTER), music21_grace("B-4")])
    measure.append(note.Note("A4", quarterLength=3 * QUARTER))
    # The grace note sits before the A4, at offset 1.
    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].grace_notes == (grace_note(1, "Bb4", notated_value=Fraction(1, 2)),)


def test_a_grace_note_takes_the_slash_and_the_value_of_its_symbol() -> None:
    measure = bar_of(
        [
            music21_grace("D5", kind="16th", slash=False),
            note.Note("C5", quarterLength=4 * QUARTER),
        ]
    )

    ornament = convert_score(score_of(part_of([measure]))).score.parts[0].voices[0].grace_notes[0]

    assert (ornament.notated_value, ornament.slash) == (Fraction(1, 4), False)


def test_a_dotted_grace_note_keeps_the_value_of_its_dotted_symbol() -> None:
    dotted = note.Note("D5", type="eighth", dots=1).getGrace()
    assert dotted is not None
    measure = bar_of([dotted, note.Note("C5", quarterLength=4 * QUARTER)])

    ornament = convert_score(score_of(part_of([measure]))).score.parts[0].voices[0].grace_notes[0]

    assert ornament.notated_value == Fraction(3, 4)


def test_a_grace_note_is_not_a_note_event() -> None:
    measure = bar_of([music21_grace(), whole_note("C5")])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert [event.pitches[0].pitch.step for event in part.voices[0].events] == ["C"]


def test_grace_notes_at_one_onset_keep_the_source_order() -> None:
    measure = bar_of([music21_grace("E5", "16th"), music21_grace("D5", "16th"), whole_note("C5")])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert [g.pitches[0].pitch.step for g in part.voices[0].grace_notes] == ["E", "D"]


def test_a_grace_chord_keeps_every_pitch_highest_first() -> None:
    grace_chord = chord.Chord(["C5", "E5"], type="eighth").getGrace()
    assert grace_chord is not None
    measure = bar_of([grace_chord, whole_note("C5")])

    ornament = convert_score(score_of(part_of([measure]))).score.parts[0].voices[0].grace_notes[0]

    assert [event_pitch.pitch.step for event_pitch in ornament.pitches] == ["E", "C"]


def test_a_tied_grace_note_keeps_the_tie_of_its_pitch() -> None:
    tied = music21_grace("D5")
    tied.tie = tie.Tie("start")
    measure = bar_of([tied, whole_note("C5")])

    ornament = convert_score(score_of(part_of([measure]))).score.parts[0].voices[0].grace_notes[0]

    assert [event_pitch.tie for event_pitch in ornament.pitches] == [TieType.START]


def test_a_grace_note_in_a_music21_voice_belongs_to_that_notated_voice() -> None:
    measure = voices_bar([[whole_note("E5")], [music21_grace("D3"), whole_note("C3")]])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].grace_notes == ()
    assert [g.pitches[0].pitch.step for g in part.voices[1].grace_notes] == ["D"]


def test_a_grace_note_in_a_later_bar_has_the_onset_of_the_note_it_ornaments() -> None:
    first = bar_of([whole_note("C5")], 1)
    second = bar_of([music21_grace("E5"), whole_note("D5")], 2)

    part = convert_score(score_of(part_of([first, second]))).score.parts[0]

    assert part.voices[0].grace_notes[0].onset == Fraction(4)


def test_a_grace_note_before_a_rest_ornaments_the_rest() -> None:
    measure = bar_of([note.Note("C5", quarterLength=2.0), music21_grace("E5")])
    measure.append(note.Rest(quarterLength=2.0))

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].grace_notes[0].onset == Fraction(2)


def test_a_grace_note_with_nothing_after_it_in_its_bar_is_unsupported() -> None:
    measure = bar_of([whole_note("C5"), music21_grace("E5")])

    with pytest.raises(UnsupportedScoreError, match="grace note at onset 4 has nothing"):
        convert_score(score_of(part_of([measure])))


def test_a_grace_note_with_a_tuplet_is_unsupported() -> None:
    grace = music21_grace("E5")
    grace.duration.appendTuplet(duration.Tuplet(3, 2))
    measure = bar_of([grace, whole_note("C5")])

    with pytest.raises(UnsupportedScoreError, match="tuplet"):
        convert_score(score_of(part_of([measure])))


def test_a_fermata_on_a_rest_becomes_a_rest_fermata_with_the_onset_and_length_of_the_rest() -> None:
    measure = bar_of([note.Note("C5", quarterLength=2.0), fermata_rest(2.0)])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].rest_fermatas == (rest_fermata(2, 2),)


def test_a_rest_without_fermata_is_not_stored() -> None:
    measure = bar_of([note.Note("C5", quarterLength=2.0), note.Rest(quarterLength=2.0)])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].rest_fermatas == ()


def test_a_rest_fermata_in_a_later_bar_has_an_onset_from_the_start_of_the_score() -> None:
    first = bar_of([whole_note("C5")], 1)
    second = bar_of([fermata_rest(4.0)], 2)

    part = convert_score(score_of(part_of([first, second]))).score.parts[0]

    assert part.voices[0].rest_fermatas == (rest_fermata(4, 4),)


def test_a_rest_fermata_in_a_music21_voice_belongs_to_that_notated_voice() -> None:
    measure = voices_bar([[whole_note("E5")], [fermata_rest(4.0)]])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert part.voices[0].rest_fermatas == ()
    assert part.voices[1].rest_fermatas == (rest_fermata(0, 4),)


def test_a_voice_that_holds_only_a_rest_fermata_is_created() -> None:
    measure = voices_bar([[whole_note("E5")], [fermata_rest(4.0)]])

    part = convert_score(score_of(part_of([measure]))).score.parts[0]

    assert len(part.voices) == 2


def test_a_note_with_a_fermata_is_still_a_note_event_not_a_rest_fermata() -> None:
    fermata_note = whole_note("C5")
    fermata_note.expressions.append(expressions.Fermata())

    part = convert_score(score_of(part_of([bar_of([fermata_note])]))).score.parts[0]

    assert part.voices[0].rest_fermatas == ()
    assert part.voices[0].events[0].fermata
