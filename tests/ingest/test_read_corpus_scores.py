"""Ingestion of real corpus chorales, with the facts verified against music21 10.5.2."""

from fractions import Fraction

import pytest

from aretz_texture.core.notation import EventPitch, NoteEvent, SpelledPitch, StepName, TieType
from aretz_texture.core.score import Bar, Part, Score
from aretz_texture.ingest.sources import read_score

# Beat 3 of bars 1, 2, 3, 5, 7 and 9, which start at onsets 1, 5, 9, 17, 25 and 33.
SOPRANO_FERMATA_ONSETS_OF_BWV66_6 = (3, 7, 11, 19, 27, 35)


def part_named(score: Score, name: str) -> Part:
    return next(part for part in score.parts if part.name == name)


def event_at(part: Part, onset: Fraction, voice_number: int = 1) -> NoteEvent:
    return next(event for event in part.voices[voice_number - 1].events if event.onset == onset)


def test_bwv66_6_has_four_named_parts_with_three_sharps_in_score_order() -> None:
    score = read_score("bwv66.6").score

    assert [part.name for part in score.parts] == ["Soprano", "Alto", "Tenor", "Bass"]
    assert [part.instrument_name for part in score.parts] == [
        "Instrument 1",
        "Instrument 2",
        "Instrument 3",
        "Instrument 4",
    ]
    for part in score.parts:
        assert len(part.voices) == 1
        assert [change.sharps for change in part.key_signatures] == [3]
        assert part.key_signatures[0].onset == 0


def test_bwv66_6_has_the_meter_and_bars_of_the_source() -> None:
    score = read_score("bwv66.6").score

    assert [(s.onset, s.numerator, s.denominator) for s in score.time_signatures] == [
        (Fraction(0), 4, 4)
    ]
    expected_bars = [Bar(number=0, onset=Fraction(0), duration=Fraction(1))]
    expected_bars += [
        Bar(number=number, onset=Fraction(1 + 4 * (number - 1)), duration=Fraction(4))
        for number in range(1, 9)
    ]
    expected_bars.append(Bar(number=9, onset=Fraction(33), duration=Fraction(3)))
    assert list(score.bars) == expected_bars


def test_bwv66_6_pickup_bar_is_numbered_zero_and_lasts_one_quarter() -> None:
    score = read_score("bwv66.6").score

    assert score.bars[0].number == 0
    assert score.pickup_duration() == Fraction(1)


def test_corpus_identifier_works_with_and_without_the_bach_prefix() -> None:
    assert read_score("bwv66.6") == read_score("bach/bwv66.6")


def test_bwv66_6_marks_exactly_the_fermatas_of_the_source() -> None:
    soprano = part_named(read_score("bwv66.6").score, "Soprano")

    fermata_onsets = tuple(int(event.onset) for event in soprano.voices[0].events if event.fermata)

    assert fermata_onsets == SOPRANO_FERMATA_ONSETS_OF_BWV66_6


def test_note_tied_across_a_bar_line_becomes_two_events() -> None:
    # bach/bwv269, Alto: bar 8 ends with G4 (start) tied to G4 (stop) at the start of bar 9.
    alto = part_named(read_score("bach/bwv269").score, "Alto")

    before_bar_line = event_at(alto, Fraction(22 + 2))
    after_bar_line = event_at(alto, Fraction(25))

    assert before_bar_line.duration == Fraction(1)
    assert [(p.pitch.step, p.pitch.octave, p.tie) for p in before_bar_line.pitches] == [
        ("G", 4, TieType.START)
    ]
    assert after_bar_line.duration == Fraction(1, 2)
    assert [(p.pitch.step, p.pitch.octave, p.tie) for p in after_bar_line.pitches] == [
        ("G", 4, TieType.STOP)
    ]


def test_note_outside_the_key_signature_keeps_its_natural_spelling() -> None:
    # bach/bwv269, Alto, bar 13: F4 natural against a key signature of one sharp.
    alto = part_named(read_score("bach/bwv269").score, "Alto")
    bar_13 = next(bar for bar in read_score("bach/bwv269").score.bars if bar.number == 13)

    natural_f = event_at(alto, bar_13.onset + 2)

    assert [(p.pitch.step, p.pitch.alter, p.pitch.octave) for p in natural_f.pitches] == [
        ("F", 0, 4)
    ]
    assert [change.sharps for change in alto.key_signatures] == [1]


def test_chord_in_a_part_becomes_one_divided_event_with_every_pitch() -> None:
    # bach/bwv248.9-1, "Trumpet 1,2", bar 2 (onset 5): D5 and F#5 at beat 3.5 of the bar.
    trumpet = part_named(read_score("bach/bwv248.9-1").score, "Trumpet 1,2")

    divided = event_at(trumpet, Fraction(15, 2))

    assert divided.duration == Fraction(1, 4)
    assert [(p.pitch.step, p.pitch.alter, p.pitch.octave, p.tie) for p in divided.pitches] == [
        ("F", 1, 5, None),
        ("D", 0, 5, None),
    ]


def test_part_with_several_voices_keeps_each_as_its_own_notated_voice() -> None:
    # bach/bwv248.23-2, "Oboe d'amore": bars 0 and 1 have no voices, bar 2 (onset 7.5) has two.
    oboe = part_named(read_score("bach/bwv248.23-2").score, "Oboe d'amore")

    assert len(oboe.voices) == 2
    first_voice, second_voice = oboe.voices
    bar_2_onsets = Fraction(15, 2)
    in_bar_2 = [
        [
            (event.onset - bar_2_onsets, event.duration, event.pitches[0].pitch.step)
            for event in voice.events
            if bar_2_onsets <= event.onset < bar_2_onsets + 6
        ]
        for voice in (first_voice, second_voice)
    ]
    assert in_bar_2[0] == [
        (Fraction(3), Fraction(1), "B"),
        (Fraction(4), Fraction(1, 2), "A"),
        (Fraction(9, 2), Fraction(1), "A"),
        (Fraction(11, 2), Fraction(1, 2), "G"),
    ]
    assert in_bar_2[1] == [
        (Fraction(3), Fraction(1), "G"),
        (Fraction(4), Fraction(1, 2), "F"),
        (Fraction(9, 2), Fraction(1), "F"),
        (Fraction(11, 2), Fraction(1, 2), "D"),
    ]


def test_score_with_five_parts_keeps_every_part_with_its_names() -> None:
    score = read_score("bach/bwv27.6").score

    assert [part.name for part in score.parts] == [
        "Soprano 1",
        "Soprano 2",
        "Alto",
        "Tenor",
        "Bass",
    ]
    assert [part.instrument_name for part in score.parts] == [None] * 5


def test_combined_part_names_are_kept_verbatim_including_the_misspelling() -> None:
    score = read_score("bach/bwv41.6").score

    assert [part.name for part in score.parts][-4:] == [
        "Soprano Oboe 1 Violin1",
        "Alto Oboe 2 Viloin 2",
        "Tenor Viola",
        "Bass Continuo",
    ]
    assert len(score.parts) == 9


def test_score_with_fifteen_parts_keeps_every_part_with_name_and_instrument() -> None:
    score = read_score("bach/bwv190.7").score

    assert len(score.parts) == 15
    assert [(part.name, part.instrument_name) for part in score.parts][:5] == [
        ("Trumpet 1", "Instrument 6"),
        ("Trumpet 2", "Instrument 6"),
        ("Trumpet 3", "Instrument 6"),
        ("Timpani", "Instrument 5"),
        ("Oboe 1", "Instrument 7"),
    ]
    assert score.parts[-1].name == "Continuo"
    assert score.parts[-1].instrument_name == "Instrument 4"


# Verified against music21 10.5.2: the soprano of these chorales holds the only grace notes of
# the corpus, each an eighth with a slash, written before the note it ornaments.
GRACE_NOTES_OF_THE_CORPUS = [
    ("bach/bwv299", 37, "B", -1, 4),
    ("bach/bwv299", 44, "E", -1, 5),
    ("bach/bwv315", 41, "D", 0, 5),
]


@pytest.mark.parametrize(
    ("identifier", "onset", "step", "alter", "octave"), GRACE_NOTES_OF_THE_CORPUS
)
def test_a_corpus_grace_note_is_read_with_its_onset_pitch_value_and_slash(
    identifier: str, onset: int, step: StepName, alter: int, octave: int
) -> None:
    soprano = read_score(identifier).score.parts[0]

    grace_notes = [grace for grace in soprano.voices[0].grace_notes if grace.onset == onset]

    assert len(grace_notes) == 1
    assert grace_notes[0].pitches == (
        EventPitch(pitch=SpelledPitch(step=step, alter=alter, octave=octave), tie=None),
    )
    assert (grace_notes[0].notated_value, grace_notes[0].slash) == (Fraction(1, 2), True)


@pytest.mark.parametrize(("identifier", "expected_count"), [("bach/bwv299", 2), ("bach/bwv315", 1)])
def test_the_corpus_chorales_with_grace_notes_have_no_others(
    identifier: str, expected_count: int
) -> None:
    score = read_score(identifier).score

    counts = [len(voice.grace_notes) for part in score.parts for voice in part.voices]

    assert sum(counts) == expected_count
