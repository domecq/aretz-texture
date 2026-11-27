"""Criterion 15: one level 1 event per window, with its reading."""

from tests.analysis.harmony_scores import line
from tests.core_builders import event, part_of, score_of

from aretz_texture.analysis.chords import identify_chord
from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.harmony import analyze_surface_harmony
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.harmony import (
    ChordIdentity,
    GranularityLevel,
    HarmonicEvent,
    UnidentifiedSonority,
)
from aretz_texture.core.score import Score


def events_of(score: Score) -> tuple[HarmonicEvent, ...]:
    texture = analyze_texture(score, TexturalAnalysisSettings())
    return analyze_surface_harmony(score, texture, NonChordToneSettings())


def dominant_seventh_then_tonic() -> Score:
    """Return G7 over B3 for a bar, then C major over C3 for a bar, in four parts."""
    return score_of(
        part_of(line(("G4", 4), ("E5", 4))),
        part_of(line(("F4", 4), ("G4", 4))),
        part_of(line(("D4", 4), ("C4", 4))),
        part_of(line(("B3", 4), ("C3", 4))),
    )


def test_every_window_gives_one_surface_event_with_that_window_as_its_only_one() -> None:
    score = dominant_seventh_then_tonic()
    texture = analyze_texture(score, TexturalAnalysisSettings())
    windows = segment_harmony(score, texture, NonChordToneSettings())

    events = analyze_surface_harmony(score, texture, NonChordToneSettings())

    assert [event.windows for event in events] == [(window,) for window in windows]
    assert [event.span for event in events] == [window.span for window in windows]
    assert all(event.level is GranularityLevel.SURFACE and not event.children for event in events)


def test_the_reading_of_an_event_is_the_identification_of_its_window() -> None:
    events = events_of(dominant_seventh_then_tonic())

    assert [identify_chord(event.windows[0]) for event in events] == [
        event.reading for event in events
    ]


def test_the_first_event_of_the_dominant_seventh_in_first_inversion_is_g7_over_b() -> None:
    first = events_of(dominant_seventh_then_tonic())[0]

    assert isinstance(first.reading, ChordIdentity)
    assert first.reading.symbol() == "G7/B"


def test_a_window_outside_the_vocabulary_is_a_reading_and_does_not_stop_the_analysis() -> None:
    score = score_of(
        part_of([event(0, 4, "C4")]),
        part_of([event(0, 4, "C#4")]),
        part_of(line(("C3", 2), ("C3", 2))),
    )

    (only,) = events_of(score)

    assert isinstance(only.reading, UnidentifiedSonority)
