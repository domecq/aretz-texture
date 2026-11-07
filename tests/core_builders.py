"""Small core scores built for tests: one fixed meter, whole bars unless said otherwise."""

from collections.abc import Sequence
from fractions import Fraction

from aretz_texture.core.notation import (
    STEP_NAMES,
    EventPitch,
    NotatedVoice,
    NoteEvent,
    SpelledPitch,
    TieType,
)
from aretz_texture.core.score import (
    Bar,
    KeySignatureChange,
    Part,
    Score,
    TimeSignatureChange,
)

FOUR_FOUR = TimeSignatureChange(onset=Fraction(0), numerator=4, denominator=4)


def event(
    onset: Fraction | int,
    duration: Fraction | int,
    pitch: str = "C4",
    fermata: bool = False,
    tie: TieType | None = None,
) -> NoteEvent:
    """Return an event with one pitch written like "C4", "F#4" or "Bb3"."""
    step = STEP_NAMES["CDEFGAB".index(pitch[0])]
    alter = {"#": 1, "b": -1}.get(pitch[1], 0)
    spelled = SpelledPitch(step=step, alter=alter, octave=int(pitch[-1]))
    return NoteEvent(
        onset=Fraction(onset),
        duration=Fraction(duration),
        pitches=(EventPitch(pitch=spelled, tie=tie),),
        fermata=fermata,
    )


def part_of(
    *voices: Sequence[NoteEvent],
    name: str | None = None,
    instrument_name: str | None = None,
    key_signatures: Sequence[KeySignatureChange] | None = None,
) -> Part:
    """Return a part with one notated voice per sequence of events."""
    return Part(
        name=name,
        instrument_name=instrument_name,
        key_signatures=tuple(key_signatures or [KeySignatureChange(onset=Fraction(0), sharps=0)]),
        voices=tuple(NotatedVoice(events=tuple(events)) for events in voices),
    )


def score_of(
    *parts: Part,
    bar_durations: Sequence[Fraction | int] = (4, 4),
    time_signatures: Sequence[TimeSignatureChange] = (FOUR_FOUR,),
) -> Score:
    """Return a score whose bars are numbered from 1, or from 0 when the first one is short."""
    bars: list[Bar] = []
    onset = Fraction(0)
    first_number = 0 if Fraction(bar_durations[0]) < FOUR_FOUR.bar_duration() else 1
    for index, duration in enumerate(bar_durations):
        bars.append(Bar(number=first_number + index, onset=onset, duration=Fraction(duration)))
        onset += Fraction(duration)
    return Score(bars=tuple(bars), time_signatures=tuple(time_signatures), parts=parts)
