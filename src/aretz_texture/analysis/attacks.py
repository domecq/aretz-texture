"""Attacks of a notated voice: where a sound starts, as the textural features read them."""

from fractions import Fraction

from pydantic import BaseModel, ConfigDict

from aretz_texture.core.notation import SpelledPitch, TieType
from aretz_texture.core.score import Score
from aretz_texture.core.texture import StreamReference, TimeSpan

# A pitch with one of these ties continues a sound that started earlier.
CONTINUING_TIES = frozenset({TieType.STOP, TieType.CONTINUE})


class Attack(BaseModel):
    """The start of one or more sounds in a notated voice."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction  # quarter lengths from the start of the first bar
    pitches: tuple[SpelledPitch, ...]  # the pitches that start here, highest first
    stream: StreamReference


def stream_references(score: Score) -> tuple[StreamReference, ...]:
    """Return a reference to every notated voice of every part, in score order."""
    return tuple(
        StreamReference(part_number=part_number, voice_number=voice_number, part_name=part.name)
        for part_number, part in enumerate(score.parts, start=1)
        for voice_number in range(1, len(part.voices) + 1)
    )


def voice_attacks(score: Score, stream: StreamReference, span: TimeSpan) -> tuple[Attack, ...]:
    """Return the attacks of a notated voice whose onset lies in a span.

    An attack is a note event keeping only the pitches whose tie is not a stop or a
    continuation, so an event all of whose pitches continue a tie is not an attack. Grace
    notes and rest fermatas are not attacks: a grace note takes no time in the bar.

    Args:
        score: The score holding the voice.
        stream: Which notated voice of which part.
        span: Events with an onset from its onset up to, not including, its end.

    Returns:
        The attacks in order of onset.
    """
    voice = score.parts[stream.part_number - 1].voices[stream.voice_number - 1]
    attacks: list[Attack] = []
    for note_event in voice.events:
        if not span.onset <= note_event.onset < span.end:
            continue
        new_pitches = tuple(
            event_pitch.pitch
            for event_pitch in note_event.pitches
            if event_pitch.tie not in CONTINUING_TIES
        )
        if new_pitches:
            attacks.append(Attack(onset=note_event.onset, pitches=new_pitches, stream=stream))
    return tuple(attacks)
