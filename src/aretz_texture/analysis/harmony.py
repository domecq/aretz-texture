"""Harmonic analysis: the surface events, one chord reading per harmonic window (spec 003)."""

from aretz_texture.analysis.chords import identify_chord
from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.core.harmony import GranularityLevel, HarmonicEvent, HarmonicWindow
from aretz_texture.core.score import Score
from aretz_texture.core.texture import TexturalAnalysis


def analyze_surface_harmony(
    score: Score, texture: TexturalAnalysis, settings: NonChordToneSettings
) -> tuple[HarmonicEvent, ...]:
    """Segment the harmony of a score and read each window as a chord: the level 1 events.

    Args:
        score: The score the texture analyzes.
        texture: Its textural analysis; the phrases and planes are read from it.
        settings: The thresholds of the non chord tone rules.

    Returns:
        One surface event per harmonic window, in order, each with its window as the only one
        it covers and no children. A window outside the vocabulary becomes an unidentified
        sonority, not an error.
    """
    return tuple(_surface_event(window) for window in segment_harmony(score, texture, settings))


def _surface_event(window: HarmonicWindow) -> HarmonicEvent:
    return HarmonicEvent(
        level=GranularityLevel.SURFACE,
        span=window.span,
        reading=identify_chord(window),
        windows=(window,),
        children=(),
    )
