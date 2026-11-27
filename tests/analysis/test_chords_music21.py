"""Consistency check of chord symbols against music21 (ADR 0006, decision 3).

music21 is the reference only for this comparison; the analysis never calls it. Over the
17071 identified windows of the 350 chorales (November 26, 2026, music21 10.5.2) 16086 give
the same symbol once its notation is normalized, 985 cannot be named by music21 and none
is named differently. These tests keep the check on a few chorales and on the chords of
criterion 14.
"""

import pytest
from music21 import chord, harmony, pitch
from tests.core_builders import harmonic_window, spelled_pitch
from tests.corpus_scores import corpus_score, corpus_texture

from aretz_texture.analysis.chords import identify_chord
from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.core.harmony import ChordIdentity, HarmonicWindow
from aretz_texture.core.notation import SpelledPitch

# music21 writes the half diminished seventh as `ø7`, the diminished seventh as `o7` and the
# augmented triad as `+`, and flats as `-`; the project writes `m7b5`, `dim7`, `aug` and `b`.
MUSIC21_NOTATION = (("-", "b"), ("ø7", "m7b5"), ("o7", "dim7"), ("+", "aug"))
MAXIMUM_NAMES_WITHOUT_FIFTH = 3
CHORALES = ("bach/bwv66.6", "bach/bwv269", "bach/bwv347", "bach/bwv320")


def music21_symbol(pitches: tuple[SpelledPitch, ...]) -> str | None:
    """Name the pitches with music21, in the project's notation; None if it cannot."""
    names = [pitch.Pitch(f"{p.step}{'#' * p.alter}{'-' * -p.alter}{p.octave}") for p in pitches]
    figure = harmony.chordSymbolFromChord(chord.Chord(names)).figure
    if figure.startswith("Chord Symbol Cannot"):
        return None
    for theirs, ours in MUSIC21_NOTATION:
        figure = figure.replace(theirs, ours)
    return figure


@pytest.mark.parametrize(
    ("chord_tones", "symbol"),
    [
        (("G4", "F4", "D4", "B3"), "G7/B"),
        (("F4", "D4", "B3"), "Bdim"),
        (("E4", "C4", "A3", "F#3"), "F#m7b5"),
        (("A4", "F4", "D4", "Bb3"), "Bbmaj7"),
        (("B3", "G3", "Eb3"), "Ebaug"),
        (("C#4", "Bb3", "G3", "E3"), "C#dim7/E"),
    ],
)
def test_the_chords_of_criterion_14_have_the_same_symbol_in_music21(
    chord_tones: tuple[str, ...], symbol: str
) -> None:
    pitches = tuple(spelled_pitch(name) for name in chord_tones)

    ours = identify_chord(harmonic_window(pitches))

    assert isinstance(ours, ChordIdentity)
    assert (ours.symbol(), music21_symbol(pitches)) == (symbol, symbol)


@pytest.mark.parametrize("identifier", CHORALES)
def test_music21_never_names_a_chorale_window_differently_from_the_project(
    identifier: str,
) -> None:
    score, texture = corpus_score(identifier), corpus_texture(identifier)
    windows = segment_harmony(score, texture, NonChordToneSettings())
    named_differently: list[str] = []
    unnamed_by_music21: list[HarmonicWindow] = []

    for window in windows:
        ours = identify_chord(window)
        theirs = music21_symbol(window.chord_tones)
        if not isinstance(ours, ChordIdentity):
            continue
        if theirs is None:
            unnamed_by_music21.append(window)
        elif theirs != ours.symbol():
            named_differently.append(f"{window.span}: {ours.symbol()} against {theirs}")

    assert not named_differently
    # music21 declines what has no fifth: a third alone, or a seventh chord with three names.
    assert all(
        len(distinct_names(window)) <= MAXIMUM_NAMES_WITHOUT_FIFTH for window in unnamed_by_music21
    )


def distinct_names(window: HarmonicWindow) -> set[tuple[str, int]]:
    return {(pitch.step, pitch.alter) for pitch in window.chord_tones}
