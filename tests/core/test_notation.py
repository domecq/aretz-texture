from fractions import Fraction

import pytest
from pydantic import ValidationError

from aretz_texture.core.notation import (
    EventPitch,
    NotatedVoice,
    NoteEvent,
    SpelledPitch,
    TieType,
)


def pitch(step: str, alter: int, octave: int) -> SpelledPitch:
    return SpelledPitch.model_validate({"step": step, "alter": alter, "octave": octave})


def event_pitch(step: str, alter: int, octave: int, tie: TieType | None = None) -> EventPitch:
    return EventPitch(pitch=pitch(step, alter, octave), tie=tie)


def note_event(
    onset: Fraction,
    duration: Fraction,
    pitches: tuple[EventPitch, ...] | None = None,
) -> NoteEvent:
    return NoteEvent(
        onset=onset,
        duration=duration,
        pitches=pitches if pitches is not None else (event_pitch("C", 0, 4),),
        fermata=False,
    )


def test_enharmonic_pitches_are_different_with_the_same_pitch_class() -> None:
    f_sharp = pitch("F", 1, 4)
    g_flat = pitch("G", -1, 4)

    assert f_sharp != g_flat
    assert f_sharp.pitch_class() == g_flat.pitch_class() == 6


@pytest.mark.parametrize(
    ("spelled", "expected"),
    [
        (("C", 0, 4), 0),
        (("B", 1, 3), 0),
        (("C", -1, 4), 11),
        (("A", 0, 4), 9),
    ],
)
def test_pitch_class_wraps_around_the_octave(spelled: tuple[str, int, int], expected: int) -> None:
    assert pitch(*spelled).pitch_class() == expected


def test_models_are_immutable() -> None:
    spelled = pitch("C", 0, 4)
    event = note_event(Fraction(0), Fraction(1))
    voice = NotatedVoice(events=(event,))

    with pytest.raises(ValidationError):
        spelled.alter = 1  # type: ignore[misc]
    with pytest.raises(ValidationError):
        event.duration = Fraction(2)  # type: ignore[misc]
    with pytest.raises(ValidationError):
        voice.events = ()  # type: ignore[misc]


def test_note_event_rejects_empty_pitches() -> None:
    with pytest.raises(ValidationError):
        note_event(Fraction(0), Fraction(1), pitches=())


def test_note_event_rejects_pitches_not_ordered_highest_first() -> None:
    ascending = (event_pitch("C", 0, 4), event_pitch("E", 0, 4))

    with pytest.raises(ValidationError):
        note_event(Fraction(0), Fraction(1), pitches=ascending)


def test_note_event_accepts_the_same_spelled_pitch_twice() -> None:
    unison = (event_pitch("C", 0, 4), event_pitch("C", 0, 4), event_pitch("A", 0, 3))

    event = note_event(Fraction(0), Fraction(1), pitches=unison)

    assert len(event.pitches) == 3


def test_note_event_orders_enharmonic_spellings_by_step() -> None:
    f_sharp = event_pitch("F", 1, 4)
    g_flat = event_pitch("G", -1, 4)

    note_event(Fraction(0), Fraction(1), pitches=(f_sharp, g_flat))
    with pytest.raises(ValidationError):
        note_event(Fraction(0), Fraction(1), pitches=(g_flat, f_sharp))


@pytest.mark.parametrize("duration", [Fraction(0), Fraction(-1)])
def test_note_event_rejects_a_duration_that_is_not_positive(duration: Fraction) -> None:
    with pytest.raises(ValidationError):
        note_event(Fraction(0), duration)


def test_notated_voice_rejects_unsorted_events() -> None:
    first = note_event(Fraction(1), Fraction(1))
    second = note_event(Fraction(0), Fraction(1))

    with pytest.raises(ValidationError):
        NotatedVoice(events=(first, second))


def test_notated_voice_rejects_overlapping_events() -> None:
    first = note_event(Fraction(0), Fraction(2))
    second = note_event(Fraction(1), Fraction(1))

    with pytest.raises(ValidationError):
        NotatedVoice(events=(first, second))


def test_notated_voice_accepts_events_that_touch() -> None:
    first = note_event(Fraction(0), Fraction(1))
    second = note_event(Fraction(1), Fraction(1))

    voice = NotatedVoice(events=(first, second))

    assert voice.events == (first, second)
