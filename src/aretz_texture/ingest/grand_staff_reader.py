# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Reading back the piano files that `render/piano_score.py` writes."""

from music21 import stream
from pydantic import ValidationError

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.grand_staff import GrandStaffLayout, Staff
from aretz_texture.core.score import Part, Score
from aretz_texture.ingest.music21_conversion import (
    join_voice_bars,
    read_bars,
    read_key_signatures,
    read_time_signatures,
    read_voice_bar,
    require_same_bars,
    require_same_time_signatures,
    to_fraction,
)

STAVES_OF_A_GRAND_STAFF = 2


def convert_grand_staff(source: stream.Score, layout: GrandStaffLayout) -> Score:
    """Convert a music21 grand staff score into the core model, one part per staff voice.

    Args:
        source: A music21 score read from a file written by `write_piano_score`.
        layout: Where each part of the original score was written.

    Returns:
        The score with one part per placement of the layout, in order, each with one
        notated voice and no part name or instrument name, since the grand staff has none.

    Raises:
        UnsupportedScoreError: The score does not have exactly two staves, a staff lacks a
            voice of the layout, or the model cannot represent the score.
    """
    staves = list(source.parts)
    if len(staves) != STAVES_OF_A_GRAND_STAFF:
        message = f"a grand staff has exactly two staves; this score has {len(staves)}"
        raise UnsupportedScoreError(message)
    upper, lower = staves
    try:
        return _convert_staves({Staff.UPPER: upper, Staff.LOWER: lower}, layout)
    except ValidationError as error:
        message = f"the grand staff breaks a structural rule of the core model: {error}"
        raise UnsupportedScoreError(message) from error


def _convert_staves(staves: dict[Staff, stream.Part], layout: GrandStaffLayout) -> Score:
    bars = read_bars(staves[Staff.UPPER])
    time_signatures = read_time_signatures(staves[Staff.UPPER], bars)
    require_same_bars(bars, read_bars(staves[Staff.LOWER]), 2)
    require_same_time_signatures(time_signatures, staves[Staff.LOWER], bars, 2)
    parts = tuple(
        _convert_staff_voice(staves[placement.staff], placement.voice_number)
        for placement in layout.placements
    )
    return Score(bars=bars, time_signatures=time_signatures, parts=parts)


def _convert_staff_voice(staff: stream.Part, voice_number: int) -> Part:
    voice_bars = []
    for measure in staff.getElementsByClass(stream.Measure):
        # Voices are identified by position, which music21 keeps from the file (spec 001, 3.5).
        voices = list(measure.voices)
        if len(voices) < voice_number:
            message = f"bar {measure.number} has no voice {voice_number} on its staff"
            raise UnsupportedScoreError(message)
        voice_bars.append(read_voice_bar(voices[voice_number - 1], to_fraction(measure.offset)))
    return Part(
        name=None,
        instrument_name=None,
        key_signatures=read_key_signatures(staff),
        voices=(join_voice_bars(voice_bars),),
    )
