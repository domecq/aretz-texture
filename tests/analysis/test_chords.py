"""Criterion 13: chord identification by stacked thirds, with its fallbacks."""

import pytest
from tests.core_builders import harmonic_window

from aretz_texture.analysis.chords import identify_chord
from aretz_texture.core.harmony import ChordIdentity, ChordQuality, UnidentifiedSonority

STACKING_REASON = "the pitches do not stack in thirds from one root"


def identified(*chord_tones: str) -> ChordIdentity:
    reading = identify_chord(harmonic_window(chord_tones))
    assert isinstance(reading, ChordIdentity), reading
    return reading


def unidentified(*chord_tones: str) -> UnidentifiedSonority:
    reading = identify_chord(harmonic_window(chord_tones))
    assert isinstance(reading, UnidentifiedSonority), reading
    return reading


def test_a_major_triad_is_read_with_its_root_in_the_bass() -> None:
    reading = identified("G4", "E4", "C4")

    assert (reading.symbol(), reading.inversion) == ("C", 0)


def test_the_dominant_seventh_over_its_third_is_g7_over_b() -> None:
    reading = identified("G4", "F4", "D4", "B3")

    assert (reading.symbol(), reading.inversion) == ("G7/B", 1)


def test_a_chord_without_its_fifth_reads_the_fifth_as_perfect() -> None:
    assert identified("E4", "C4").symbol() == "C"


def test_a_dominant_seventh_without_its_fifth_is_still_a_dominant_seventh() -> None:
    assert identified("Bb4", "E4", "C4").symbol() == "C7"


def test_a_minor_third_alone_is_a_minor_triad() -> None:
    assert identified("Eb4", "C4").symbol() == "Cm"


def test_the_diminished_seventh_has_the_root_its_spelling_says() -> None:
    reading = identified("Ab4", "F4", "D4", "B3")

    assert (reading.root.text(), reading.quality) == ("B", ChordQuality.DIMINISHED_SEVENTH)


def test_the_augmented_triad_has_the_root_its_spelling_says() -> None:
    reading = identified("G#4", "E4", "C4")

    assert (reading.root.text(), reading.quality) == ("C", ChordQuality.AUGMENTED)


@pytest.mark.parametrize(
    ("chord_tones", "inversion"),
    [
        (("G4", "E4", "C4"), 0),
        (("C5", "G4", "E4"), 1),
        (("E5", "C5", "G4"), 2),
        (("C5", "G4", "E4", "Bb3"), 3),
    ],
)
def test_the_inversion_is_the_position_of_the_lowest_pitch_in_the_chord(
    chord_tones: tuple[str, ...], inversion: int
) -> None:
    assert identified(*chord_tones).inversion == inversion


def test_a_doubled_bass_and_doubled_upper_voices_are_one_chord() -> None:
    assert identified("E5", "C5", "G4", "E4", "C3").symbol() == "C"


def test_a_fifth_alone_has_no_third() -> None:
    reading = unidentified("G4", "C4")

    assert reading.reason == "no third above any pitch"
    assert [name.text() for name in reading.pitch_names] == ["C", "G"]


def test_a_single_pitch_has_no_third() -> None:
    assert unidentified("C4").reason == "no third above any pitch"


def test_a_pitch_and_its_chromatic_alteration_are_two_spellings_of_one_letter() -> None:
    reading = unidentified("C#4", "C4")

    assert reading.reason == "C and C# in one window"
    assert [name.text() for name in reading.pitch_names] == ["C", "C#"]


def test_an_augmented_sixth_chord_is_unidentified_with_its_pitch_names_in_letter_order() -> None:
    reading = unidentified("F#5", "Eb5", "C5", "Ab4")

    assert [name.text() for name in reading.pitch_names] == ["C", "Eb", "F#", "Ab"]
    assert reading.reason.startswith("F# with third 2, fifth 6")


def test_pitches_that_do_not_stack_from_one_root_say_so() -> None:
    assert unidentified("F#4", "E4", "C4").reason == STACKING_REASON


def test_a_seventh_outside_the_vocabulary_names_the_root_and_the_intervals() -> None:
    reading = unidentified("Bbb4", "G4", "E4", "C4")

    assert "outside the vocabulary" in reading.reason
    assert reading.reason.startswith("C ")


def test_a_diminished_third_is_outside_the_vocabulary() -> None:
    assert "outside the vocabulary" in unidentified("Ebb4", "C4").reason


def test_a_third_with_a_diminished_fifth_that_is_major_is_outside_the_vocabulary() -> None:
    assert "outside the vocabulary" in unidentified("Gb4", "E4", "C4").reason


def test_a_seventh_of_nine_semitones_over_a_major_third_is_outside_the_vocabulary() -> None:
    assert "outside the vocabulary" in unidentified("Bbb4", "E4", "C4").reason


def test_a_fifth_and_a_seventh_without_a_third_do_not_stack_from_one_root() -> None:
    assert unidentified("Bb4", "G4", "C4").reason == STACKING_REASON
