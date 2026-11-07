# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
from fractions import Fraction

from music21 import chord, expressions, instrument, key, meter, note, pitch, stream, tie
from tests.music21_builders import (
    bar_of,
    part_of,
    score_of,
    voices_bar,
    whole_note,
)

from aretz_texture.core.notation import TieType
from aretz_texture.ingest.music21_conversion import convert_score


def test_notes_in_bars_without_voices_belong_to_notated_voice_1() -> None:
    first_bar = bar_of([whole_note("C4")], 1)
    second_bar = voices_bar([[whole_note("E4")], [whole_note("G3")]], 2)
    source = score_of(part_of([first_bar, second_bar]))

    part = convert_score(source).score.parts[0]

    assert [(e.onset, e.pitches[0].pitch.step) for e in part.voices[0].events] == [
        (Fraction(0), "C"),
        (Fraction(4), "E"),
    ]
    assert [(e.onset, e.pitches[0].pitch.step) for e in part.voices[1].events] == [
        (Fraction(4), "G")
    ]


def test_notated_voice_that_holds_only_rests_is_not_created() -> None:
    silent = [note.Rest(quarterLength=4.0)]
    source = score_of(part_of([voices_bar([[whole_note("E4")], silent])]))

    part = convert_score(source).score.parts[0]

    assert len(part.voices) == 1


def test_notated_voice_two_may_sound_where_notated_voice_one_is_silent() -> None:
    silent = [note.Rest(quarterLength=4.0)]
    source = score_of(part_of([voices_bar([silent, [whole_note("G3")]])]))

    part = convert_score(source).score.parts[0]

    assert part.voices[0].events == ()
    assert len(part.voices[1].events) == 1


def test_chord_keeps_a_unison_written_twice_and_the_tie_of_each_pitch() -> None:
    upper = note.Note("E4")
    upper.tie = tie.Tie("start")
    unison_first = note.Note("C4")
    unison_second = note.Note("C4")
    unison_second.tie = tie.Tie("stop")
    divided = chord.Chord([unison_first, unison_second, upper], quarterLength=4.0)
    source = score_of(part_of([bar_of([divided])]))

    event = convert_score(source).score.parts[0].voices[0].events[0]

    assert [(p.pitch.step, p.pitch.octave) for p in event.pitches] == [
        ("E", 4),
        ("C", 4),
        ("C", 4),
    ]
    assert event.pitches[0].tie == TieType.START
    assert {event.pitches[1].tie, event.pitches[2].tie} == {None, TieType.STOP}


def test_fermata_on_a_chord_covers_the_whole_event() -> None:
    divided = chord.Chord(["C4", "E4"], quarterLength=4.0)
    divided.expressions.append(expressions.Fermata())
    source = score_of(part_of([bar_of([divided])]))

    event = convert_score(source).score.parts[0].voices[0].events[0]

    assert event.fermata is True


def test_event_without_a_fermata_has_it_false() -> None:
    source = score_of(part_of([bar_of([whole_note()])]))

    event = convert_score(source).score.parts[0].voices[0].events[0]

    assert event.fermata is False


def test_double_sharp_and_flat_accidentals_are_kept_as_alter() -> None:
    double_sharp = note.Note("F4", quarterLength=2.0)
    double_sharp.pitch.accidental = pitch.Accidental("double-sharp")
    flat = note.Note("B4", quarterLength=2.0)
    flat.pitch.accidental = pitch.Accidental("flat")
    source = score_of(part_of([bar_of([double_sharp, flat])]))

    events = convert_score(source).score.parts[0].voices[0].events

    assert [e.pitches[0].pitch.alter for e in events] == [2, -1]


def test_key_signature_change_in_the_middle_of_a_bar_keeps_its_onset() -> None:
    first_bar = bar_of([whole_note()], 1)
    second_bar = bar_of([note.Note("C4", quarterLength=2.0), note.Note("D4", quarterLength=2.0)], 2)
    second_bar.insert(2.0, key.KeySignature(2))
    source = score_of(part_of([first_bar, second_bar], sharps=1))

    changes = convert_score(source).score.parts[0].key_signatures

    assert [(c.onset, c.sharps) for c in changes] == [(Fraction(0), 1), (Fraction(6), 2)]


def test_repeated_key_signatures_are_collapsed() -> None:
    first_bar = bar_of([whole_note()], 1)
    second_bar = bar_of([whole_note()], 2)
    second_bar.insert(0, key.KeySignature(3))
    source = score_of(part_of([first_bar, second_bar], sharps=3))

    changes = convert_score(source).score.parts[0].key_signatures

    assert [(c.onset, c.sharps) for c in changes] == [(Fraction(0), 3)]


def test_part_without_a_key_signature_gets_no_sharps_at_onset_zero() -> None:
    bar = bar_of([whole_note()])
    bar.insert(0, meter.TimeSignature("4/4"))
    part = stream.Part()
    part.append(bar)

    changes = convert_score(score_of(part)).score.parts[0].key_signatures

    assert [(c.onset, c.sharps) for c in changes] == [(Fraction(0), 0)]


def test_part_and_instrument_names_are_trimmed_and_empty_names_become_none() -> None:
    named = part_of([bar_of([whole_note()])], name="  Alto  ")
    named.insert(0, _instrument_named(" Oboe "))
    unnamed = part_of([bar_of([whole_note()])], name="   ")

    parts = convert_score(score_of(named, unnamed)).score.parts

    assert [(p.name, p.instrument_name) for p in parts] == [("Alto", "Oboe"), (None, None)]


def _instrument_named(name: str) -> instrument.Instrument:
    named = instrument.Instrument()
    named.instrumentName = name
    return named


def test_has_lyrics_is_true_when_a_note_has_a_lyric() -> None:
    sung = whole_note()
    sung.addLyric("la")
    source = score_of(part_of([bar_of([sung])]), part_of([bar_of([whole_note()])]))

    assert convert_score(source).has_lyrics is True


def test_has_lyrics_is_true_when_a_chord_has_a_lyric() -> None:
    sung = chord.Chord(["C4", "E4"], quarterLength=4.0)
    sung.addLyric("la")
    source = score_of(part_of([bar_of([sung])]))

    assert convert_score(source).has_lyrics is True


def test_has_lyrics_is_false_when_no_note_has_a_lyric() -> None:
    source = score_of(part_of([bar_of([whole_note()])]))

    assert convert_score(source).has_lyrics is False
