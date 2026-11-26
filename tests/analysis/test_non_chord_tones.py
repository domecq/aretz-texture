from fractions import Fraction

from tests.analysis.harmony_scores import (
    EIGHTH,
    line,
    pitch_text,
    suspension_score,
    tied_alto,
)
from tests.core_builders import divided_event, event, part_of, score_of

from aretz_texture.analysis.attacks import stream_references
from aretz_texture.analysis.non_chord_tones import classify_non_chord_tones
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.analysis.sounding_notes import sounding_notes
from aretz_texture.core.harmony import NonChordToneKind
from aretz_texture.core.notation import SpelledPitch, TieType
from aretz_texture.core.score import Score, TimeSignatureChange
from aretz_texture.core.texture import TimeSpan

DEFAULTS = NonChordToneSettings()
THREE_TWO = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)


def classified(
    score: Score, settings: NonChordToneSettings = DEFAULTS
) -> list[tuple[str, str, Fraction]]:
    """Return (pitch, kind, from_onset) of every non chord tone of the whole score."""
    whole = TimeSpan(onset=Fraction(0), end=score.end())
    notes = tuple(
        note for stream in stream_references(score) for note in sounding_notes(score, stream, whole)
    )
    return [
        (pitch_text(tone.note.pitch), tone.kind, tone.from_onset)
        for tone in classify_non_chord_tones(score, notes, settings)
    ]


def soprano_score(*notes: tuple[str | None, Fraction | int]) -> Score:
    return score_of(part_of(line(*notes)))


def test_an_unaccented_eighth_between_steps_in_one_direction_is_a_passing_tone() -> None:
    score = soprano_score(("C5", EIGHTH), ("D5", EIGHTH), ("E5", 1), ("E5", 2))

    assert classified(score) == [("D5", NonChordToneKind.PASSING, EIGHTH)]


def test_an_unaccented_eighth_between_two_equal_pitches_is_a_neighbor_tone() -> None:
    score = soprano_score(("C5", EIGHTH), ("D5", EIGHTH), ("C5", 1), ("C5", 2))

    assert classified(score) == [("D5", NonChordToneKind.NEIGHBOR, EIGHTH)]


def test_a_lower_neighbor_tone_is_also_found() -> None:
    score = soprano_score(("C5", EIGHTH), ("B4", EIGHTH), ("C5", 1), ("C5", 2))

    assert classified(score) == [("B4", NonChordToneKind.NEIGHBOR, EIGHTH)]


def test_a_chromatic_step_counts_as_a_melodic_step() -> None:
    score = soprano_score(("C5", EIGHTH), ("C#5", EIGHTH), ("D5", 1), ("D5", 2))

    assert classified(score) == [("C#5", NonChordToneKind.PASSING, EIGHTH)]


def test_an_augmented_second_is_a_leap_so_no_passing_tone() -> None:
    score = soprano_score(("C5", EIGHTH), ("D#5", EIGHTH), ("E5", 1), ("E5", 2))

    assert classified(score) == []


def test_an_augmented_second_is_a_step_when_the_setting_allows_three_semitones() -> None:
    score = soprano_score(("C5", EIGHTH), ("D#5", EIGHTH), ("E5", 1), ("E5", 2))

    settings = NonChordToneSettings(maximum_melodic_step_semitones=3)

    assert classified(score, settings) == [("D#5", NonChordToneKind.PASSING, EIGHTH)]


def test_a_step_of_one_semitone_is_not_a_step_when_the_setting_allows_one() -> None:
    score = soprano_score(("C5", EIGHTH), ("D5", EIGHTH), ("E5", 1), ("E5", 2))

    settings = NonChordToneSettings(maximum_melodic_step_semitones=1)

    assert classified(score, settings) == []


def test_a_quarter_on_the_beat_between_steps_is_a_chord_tone() -> None:
    score = soprano_score(("C5", 1), ("D5", 1), ("E5", 1), ("E5", 1), ("E5", 4))

    assert classified(score) == []


def test_a_shorter_maximum_makes_the_eighth_a_chord_tone() -> None:
    score = soprano_score(("C5", EIGHTH), ("D5", EIGHTH), ("E5", 1), ("E5", 2))

    settings = NonChordToneSettings(maximum_unaccented_duration=Fraction(1, 4))

    assert classified(score, settings) == []


def test_in_three_two_a_quarter_on_the_second_quarter_of_the_tactus_is_a_passing_tone() -> None:
    score = score_of(
        part_of(line(("C5", 1), ("D5", 1), ("E5", 2), ("E5", 2))),
        bar_durations=(6, 6),
        time_signatures=(THREE_TWO,),
    )

    assert classified(score) == [("D5", NonChordToneKind.PASSING, Fraction(1))]


def test_a_note_without_an_adjacent_previous_note_is_a_chord_tone() -> None:
    score = soprano_score(("C5", EIGHTH), (None, EIGHTH), ("D5", EIGHTH), ("E5", 1), ("E5", 2))

    assert classified(score) == []


def test_a_note_followed_by_a_rest_is_a_chord_tone() -> None:
    score = soprano_score(("C5", EIGHTH), ("D5", EIGHTH), (None, 1), ("E5", 2))

    assert classified(score) == []


def test_a_voice_with_a_divided_event_beside_the_note_is_not_classified() -> None:
    soprano = [
        event(0, EIGHTH, "C5"),
        event(EIGHTH, EIGHTH, "D5"),
        divided_event(1, 1, ("E5", None), ("C5", None)),
        event(2, 2, "E5"),
    ]

    assert classified(score_of(part_of(soprano))) == []


def test_an_eighth_anticipating_the_next_beat_is_an_anticipation() -> None:
    score = soprano_score(("E5", 2), ("D5", EIGHTH), ("C5", EIGHTH), ("C5", 1), ("C5", 4))

    assert classified(score) == [("C5", NonChordToneKind.ANTICIPATION, Fraction(5, 2))]


def test_the_same_eighth_followed_by_a_step_down_is_a_passing_tone_instead() -> None:
    score = soprano_score(("E5", 2), ("D5", EIGHTH), ("C5", EIGHTH), ("B4", 1), ("B4", 4))

    assert classified(score) == [("C5", NonChordToneKind.PASSING, Fraction(5, 2))]


def test_an_anticipation_must_be_followed_by_the_same_pitch_on_the_next_beat() -> None:
    score = soprano_score(("E5", 2), ("D5", EIGHTH), ("C5", EIGHTH), (None, 1), ("C5", 4))

    assert classified(score) == []


def test_a_tied_over_dissonance_resolving_down_by_step_within_a_beat_is_a_suspension() -> None:
    score = suspension_score(tied_alto("B3", Fraction(9, 2)))

    assert classified(score) == [("C4", NonChordToneKind.SUSPENSION, Fraction(4))]


def test_a_suspension_records_its_resolution_and_the_tactus_onset_it_starts_at() -> None:
    score = suspension_score(tied_alto("B3", Fraction(9, 2)))
    whole = TimeSpan(onset=Fraction(0), end=score.end())
    notes = tuple(
        note for stream in stream_references(score) for note in sounding_notes(score, stream, whole)
    )

    (tone,) = classify_non_chord_tones(score, notes, DEFAULTS)

    assert (tone.note.onset, tone.note.end, tone.from_onset) == (3, Fraction(9, 2), 4)
    assert tone.resolution == SpelledPitch(step="B", alter=0, octave=3)


def test_a_repeated_dissonance_resolving_down_by_step_is_a_suspension() -> None:
    alto = [
        event(3, 1, "C4"),
        event(4, EIGHTH, "C4"),
        event(Fraction(9, 2), Fraction(7, 2), "B3"),
    ]

    assert classified(suspension_score(alto)) == [("C4", NonChordToneKind.SUSPENSION, Fraction(4))]


def test_a_dissonance_without_preparation_is_not_a_suspension() -> None:
    alto = [event(4, EIGHTH, "C4"), event(Fraction(9, 2), Fraction(7, 2), "B3")]

    assert classified(suspension_score(alto)) == []


def test_a_tied_dissonance_moving_up_is_not_a_suspension() -> None:
    assert classified(suspension_score(tied_alto("D4", Fraction(9, 2)))) == []


def test_a_resolution_exactly_one_tactus_after_the_onset_is_still_a_suspension() -> None:
    score = suspension_score(tied_alto("B3", Fraction(5)))

    assert classified(score) == [("C4", NonChordToneKind.SUSPENSION, Fraction(4))]


def test_a_resolution_after_more_than_the_maximum_duration_is_not_a_suspension() -> None:
    assert classified(suspension_score(tied_alto("B3", Fraction(11, 2)))) == []


def test_a_shorter_maximum_suspension_duration_rejects_a_slower_resolution() -> None:
    settings = NonChordToneSettings(maximum_suspension_duration=Fraction(1, 2))

    assert classified(suspension_score(tied_alto("B3", Fraction(5))), settings) == []
    assert classified(suspension_score(tied_alto("B3", Fraction(9, 2))), settings) != []


def test_a_resolution_by_a_leap_down_is_not_a_suspension() -> None:
    assert classified(suspension_score(tied_alto("A3", Fraction(9, 2)))) == []


def test_a_suspended_fourth_above_the_bass_counts_as_dissonant() -> None:
    alto = [
        event(3, 1, "F4", tie=TieType.START),
        event(4, EIGHTH, "F4", tie=TieType.STOP),
        event(Fraction(9, 2), Fraction(7, 2), "E4"),
    ]
    score = score_of(part_of(alto), part_of([event(0, 8, "C3")]))

    assert classified(score) == [("F4", NonChordToneKind.SUSPENSION, Fraction(4))]


def test_a_tied_note_consonant_with_every_sounding_pitch_is_not_a_suspension() -> None:
    alto = [
        event(3, 1, "C4", tie=TieType.START),
        event(4, EIGHTH, "C4", tie=TieType.STOP),
        event(Fraction(9, 2), Fraction(7, 2), "B3"),
    ]
    score = score_of(part_of(alto), part_of([event(0, 8, "E3")]), part_of([event(0, 8, "G4")]))

    assert classified(score) == []


def test_the_dissonance_is_looked_for_only_among_the_pitches_sounding_at_the_tactus() -> None:
    alto = [
        event(3, 1, "C4", tie=TieType.START),
        event(4, EIGHTH, "C4", tie=TieType.STOP),
        event(Fraction(9, 2), Fraction(7, 2), "B3"),
    ]
    tenor = [event(0, 4, "D4"), event(5, 3, "D4")]
    score = score_of(part_of(alto), part_of(tenor), part_of([event(0, 8, "E3")]))

    assert classified(score) == []
