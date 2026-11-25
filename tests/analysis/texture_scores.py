"""Small scores for the tests of the textural analysis: voices defined by their attack points."""

from collections.abc import Sequence
from fractions import Fraction
from itertools import pairwise

from tests.core_builders import event, part_of, score_of

from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.notation import NoteEvent, TieType
from aretz_texture.core.score import Part, Score
from aretz_texture.core.texture import TexturalAnalysis, TexturalConfiguration

DEFAULT_SETTINGS = TexturalAnalysisSettings()
# Four pitch classes that no two voices share, so that no voice is fused with another.
DISTINCT_PITCHES = ("E5", "C5", "G4", "D3")


def attacking_at(
    pitch: str, onsets: Sequence[Fraction | float], end: Fraction | int
) -> list[NoteEvent]:
    """Return events of one pitch that start at the onsets and each last until the next one."""
    boundaries = [Fraction(onset) for onset in onsets] + [Fraction(end)]
    return [event(start, following - start, pitch) for start, following in pairwise(boundaries)]


def tied_continuation(
    pitch: str, onsets: Sequence[Fraction | float], end: Fraction | int
) -> list[NoteEvent]:
    """Return events like `attacking_at`, but each one after the first continues a tie."""
    events = attacking_at(pitch, onsets, end)
    return [
        event(
            item.onset,
            item.duration,
            pitch,
            tie=TieType.START if index == 0 else TieType.STOP,
        )
        for index, item in enumerate(events)
    ]


def voices_attacking_at(
    onsets_of_voices: Sequence[Sequence[Fraction | float]], end: Fraction | int = 8
) -> Score:
    """Return a score in 4/4 with one part per voice, each attacking at its own onsets."""
    parts: list[Part] = [
        part_of(attacking_at(pitch, onsets, end))
        for pitch, onsets in zip(DISTINCT_PITCHES, onsets_of_voices, strict=False)
    ]
    return score_of(*parts, bar_durations=(4,) * int(Fraction(end) / 4))


def analyze(score: Score) -> TexturalAnalysis:
    return analyze_texture(score, DEFAULT_SETTINGS)


def first_configuration(score: Score) -> TexturalConfiguration:
    return analyze(score).phrases[0].configuration
