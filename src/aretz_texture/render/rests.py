# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Rests written by the MusicXML writers, shaped so music21 reads every bar back intact.

The model stores no rests: writers fill the gaps between note events with rests, and
music21 reads them back to recover the bars. Two behaviors of music21 10.5.2 change the
length of a bar on reading, and the rests written here avoid both:

* It does not count chords when it decides whether a measure is a whole bar rest, so a
  measure holding only chords and one undotted whole or breve rest of another length than
  the meter has that rest stretched to the meter. Such rests are written as two halves.
* It marks a rest that fills a bar as a whole bar rest; when it reads one inside a voice it
  stretches the first rest of the measure, which may belong to another voice. Rests inside
  voices are written as ordinary rests.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import pairwise

from music21 import note, stream

# Durations of the undotted whole and breve rests, in quarter lengths.
STRETCHABLE_REST_DURATIONS = frozenset({Fraction(4), Fraction(8)})


@dataclass(frozen=True)
class BarRests:
    """What the rests of one bar must respect.

    Attributes:
        meter_duration: Length of a full bar of the time signature in force, in quarter
            lengths.
        split_offsets: Offsets in the bar where a rest must be cut, such as the onset of a
            key signature change, which music21 writes after the element that spans it.
    """

    meter_duration: Fraction
    split_offsets: frozenset[Fraction] = field(default_factory=frozenset[Fraction])


def insert_rests(
    container: stream.Measure | stream.Voice, start: Fraction, end: Fraction, rules: BarRests
) -> None:
    """Fill the gap from start to end of a measure or voice with rests.

    Args:
        container: The measure, or the voice inside a measure, that receives the rests.
        start: Start of the gap, in quarter lengths from the start of the bar.
        end: End of the gap, in quarter lengths from the start of the bar.
        rules: What the rests of this bar must respect.
    """
    inner_cuts = sorted(offset for offset in rules.split_offsets if start < offset < end)
    for rest_start, rest_end in pairwise([start, *inner_cuts, end]):
        pieces = _unstretchable_pieces(rest_start, rest_end, rules.meter_duration)
        for piece_start, piece_end in pieces:
            rest = note.Rest(quarterLength=piece_end - piece_start)
            if isinstance(container, stream.Voice):
                rest.fullMeasure = False
            container.insert(piece_start, rest)


def _unstretchable_pieces(
    start: Fraction, end: Fraction, meter_duration: Fraction
) -> list[tuple[Fraction, Fraction]]:
    """Split a rest that music21 would stretch to the whole bar when reading it back."""
    if end <= start:
        return []
    length = end - start
    if length in STRETCHABLE_REST_DURATIONS and length != meter_duration:
        middle = start + length / 2
        return [(start, middle), (middle, end)]
    return [(start, end)]
