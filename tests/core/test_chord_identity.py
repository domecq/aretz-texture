"""Criteria 14 and 15 (core part): chord identity, chord symbols and harmonic events."""

from fractions import Fraction

import pytest
from pydantic import ValidationError
from tests.core_builders import harmonic_window

from aretz_texture.core.harmony import (
    ChordIdentity,
    ChordQuality,
    GranularityLevel,
    HarmonicEvent,
    PitchName,
    UnidentifiedSonority,
)
from aretz_texture.core.texture import TimeSpan


def name(text: str) -> PitchName:
    alter = {"#": 1, "b": -1}.get(text[1:2], 0)
    return PitchName(step=text[0], alter=alter)  # pyright: ignore[reportArgumentType]


def chord(
    root: str, quality: ChordQuality, bass: str | None = None, inversion: int = 0
) -> ChordIdentity:
    return ChordIdentity(
        root=name(root), quality=quality, bass=name(bass or root), inversion=inversion
    )


@pytest.mark.parametrize(
    ("identity", "symbol"),
    [
        (chord("G", ChordQuality.DOMINANT_SEVENTH, "B", 1), "G7/B"),
        (chord("B", ChordQuality.DIMINISHED), "Bdim"),
        (chord("F#", ChordQuality.HALF_DIMINISHED_SEVENTH), "F#m7b5"),
        (chord("Bb", ChordQuality.MAJOR_SEVENTH), "Bbmaj7"),
        (chord("Eb", ChordQuality.AUGMENTED), "Ebaug"),
        (chord("C#", ChordQuality.DIMINISHED_SEVENTH, "E", 1), "C#dim7/E"),
        (chord("C", ChordQuality.MAJOR), "C"),
        (chord("A", ChordQuality.MINOR, "E", 2), "Am/E"),
        (chord("D", ChordQuality.MINOR_SEVENTH, "C", 3), "Dm7/C"),
    ],
)
def test_a_chord_symbol_is_the_root_the_quality_suffix_and_the_bass_when_inverted(
    identity: ChordIdentity, symbol: str
) -> None:
    assert identity.symbol() == symbol


def test_the_quality_values_are_the_musicxml_kind_names() -> None:
    assert [quality.value for quality in ChordQuality] == [
        "major",
        "minor",
        "diminished",
        "augmented",
        "dominant",
        "major-seventh",
        "minor-seventh",
        "half-diminished",
        "diminished-seventh",
    ]


def test_an_inversion_beyond_the_third_is_rejected() -> None:
    with pytest.raises(ValidationError, match="inversion"):
        chord("C", ChordQuality.DOMINANT_SEVENTH, "Bb", 4)


def test_a_triad_has_no_third_inversion() -> None:
    with pytest.raises(ValidationError, match="seventh"):
        chord("C", ChordQuality.MAJOR, "Bb", 3)


def test_the_pitch_names_of_an_unidentified_sonority_are_in_letter_order_from_c() -> None:
    with pytest.raises(ValidationError, match="letter order"):
        UnidentifiedSonority(pitch_names=(name("D"), name("C")), reason="x")


def test_the_pitch_names_of_an_unidentified_sonority_are_distinct() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        UnidentifiedSonority(pitch_names=(name("C"), name("C")), reason="x")


def surface_event(
    children: tuple[HarmonicEvent, ...] = (), span_end: int = 1, windows: int = 1
) -> HarmonicEvent:
    window = harmonic_window(("E4", "C4"))
    return HarmonicEvent(
        level=GranularityLevel.SURFACE,
        span=TimeSpan(onset=Fraction(0), end=Fraction(span_end)),
        reading=chord("C", ChordQuality.MAJOR),
        windows=(window,) * windows,
        children=children,
    )


def test_every_model_of_chord_identity_is_immutable() -> None:
    models = [chord("C", ChordQuality.MAJOR), UnidentifiedSonority(pitch_names=(), reason="x")]
    models.append(surface_event())  # pyright: ignore[reportArgumentType]

    for model in models:
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValidationError):
            setattr(model, field, getattr(model, field))


def test_a_surface_event_has_no_children() -> None:
    with pytest.raises(ValidationError, match="children"):
        surface_event(children=(surface_event(),))


def test_an_event_covers_at_least_one_window() -> None:
    with pytest.raises(ValidationError, match="window"):
        surface_event(windows=0)


def test_an_event_spans_exactly_its_windows() -> None:
    with pytest.raises(ValidationError, match="span"):
        surface_event(span_end=2)


def test_granularity_levels_are_numbered_from_one_to_four() -> None:
    assert [level.value for level in GranularityLevel] == [1, 2, 3, 4]
