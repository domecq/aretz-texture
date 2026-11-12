"""Small core scores built for tests: one fixed meter, whole bars unless said otherwise."""

from collections.abc import Sequence
from fractions import Fraction

from aretz_texture.core.notation import (
    STEP_NAMES,
    EventPitch,
    GraceNote,
    NotatedVoice,
    NoteEvent,
    RestFermata,
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


def spelled_pitch(pitch: str) -> SpelledPitch:
    """Return a pitch written like "C4", "F#4" or "Bb3"."""
    alter = {"#": 1, "b": -1}.get(pitch[1], 0)
    return SpelledPitch(
        step=STEP_NAMES["CDEFGAB".index(pitch[0])], alter=alter, octave=int(pitch[-1])
    )


def event(
    onset: Fraction | int,
    duration: Fraction | int,
    pitch: str = "C4",
    fermata: bool = False,
    tie: TieType | None = None,
) -> NoteEvent:
    """Return an event with one pitch."""
    return divided_event(onset, duration, (pitch, tie), fermata=fermata)


def divided_event(
    onset: Fraction | int,
    duration: Fraction | int,
    *pitches: tuple[str, TieType | None],
    fermata: bool = False,
) -> NoteEvent:
    """Return an event with the given pitches, each with its tie, highest first."""
    return NoteEvent(
        onset=Fraction(onset),
        duration=Fraction(duration),
        pitches=tuple(EventPitch(pitch=spelled_pitch(name), tie=tie) for name, tie in pitches),
        fermata=fermata,
    )


def grace_note(
    onset: Fraction | int,
    *pitches: str,
    notated_value: Fraction | int = Fraction(1, 2),
    slash: bool = True,
) -> GraceNote:
    """Return a grace note with the given untied pitches, highest first."""
    return GraceNote(
        onset=Fraction(onset),
        pitches=tuple(EventPitch(pitch=spelled_pitch(name), tie=None) for name in pitches),
        notated_value=Fraction(notated_value),
        slash=slash,
    )


def rest_fermata(onset: Fraction | int, duration: Fraction | int) -> RestFermata:
    """Return a fermata on a rest."""
    return RestFermata(onset=Fraction(onset), duration=Fraction(duration))


def part_of(
    *voices: Sequence[NoteEvent] | NotatedVoice,
    name: str | None = None,
    instrument_name: str | None = None,
    key_signatures: Sequence[KeySignatureChange] | None = None,
) -> Part:
    """Return a part with one notated voice per sequence of events, or per given voice."""
    return Part(
        name=name,
        instrument_name=instrument_name,
        key_signatures=tuple(key_signatures or [KeySignatureChange(onset=Fraction(0), sharps=0)]),
        voices=tuple(
            voice if isinstance(voice, NotatedVoice) else NotatedVoice(events=tuple(voice))
            for voice in voices
        ),
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
