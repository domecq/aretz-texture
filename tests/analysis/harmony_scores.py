"""Small scores for the tests of harmonic segmentation: lines, suspensions and phrases."""

from fractions import Fraction

from tests.core_builders import event, part_of, score_of

from aretz_texture.core.notation import NoteEvent, SpelledPitch, TieType
from aretz_texture.core.score import Score

EIGHTH = Fraction(1, 2)


def line(*notes: tuple[str | None, Fraction | int], onset: Fraction | int = 0) -> list[NoteEvent]:
    """Return consecutive events from an onset, one per (pitch, duration); None is a rest."""
    cursor = Fraction(onset)
    events: list[NoteEvent] = []
    for pitch, duration in notes:
        if pitch is not None:
            events.append(event(cursor, duration, pitch))
        cursor += Fraction(duration)
    return events


def pitch_text(pitch: SpelledPitch) -> str:
    """Return a pitch as "C4", "F#4" or "Bb3"."""
    return f"{pitch.step}{'#' * pitch.alter}{'b' * -pitch.alter}{pitch.octave}"


def suspension_score(alto: list[NoteEvent]) -> Score:
    """Return a score with an alto over G4, a bass C3 then G2, and D4 from the second bar.

    The first bar is a C chord (C3, G4), so a C4 of the alto is consonant there; in the second
    bar the D4 and the G2 make it a second and a fourth above the bass.
    """
    soprano = part_of([event(0, 4, "G4"), event(4, 4, "G4")])
    tenor = part_of([event(4, 4, "D4")])
    bass = part_of([event(0, 4, "C3"), event(4, 4, "G2")])
    return score_of(part_of(alto), soprano, tenor, bass)


def tied_alto(resolution: str, resolves_at: Fraction) -> list[NoteEvent]:
    """Return an alto C4 from beat 4 tied over the bar line, then the resolution."""
    return [
        event(3, 1, "C4", tie=TieType.START),
        event(4, resolves_at - 4, "C4", tie=TieType.STOP),
        event(resolves_at, 8 - resolves_at, resolution),
    ]
