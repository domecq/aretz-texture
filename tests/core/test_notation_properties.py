from fractions import Fraction

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import ValidationError

from aretz_texture.core.notation import (
    STEP_NAMES,
    EventPitch,
    NotatedVoice,
    NoteEvent,
    SpelledPitch,
)

spelled_pitches = st.builds(
    SpelledPitch,
    step=st.sampled_from(STEP_NAMES),
    alter=st.integers(min_value=-1, max_value=1),
    octave=st.integers(min_value=1, max_value=6),
)
event_pitches = st.builds(EventPitch, pitch=spelled_pitches, tie=st.none())


def event_of(pitches: list[EventPitch], onset: Fraction, duration: Fraction) -> NoteEvent:
    return NoteEvent(onset=onset, duration=duration, pitches=tuple(pitches), fermata=False)


def highest_first(pitches: list[EventPitch]) -> list[EventPitch]:
    return sorted(pitches, key=lambda event_pitch: event_pitch.pitch.highest_first_key())


@given(st.lists(event_pitches, min_size=1, max_size=4))
def test_divided_event_accepts_pitches_ordered_from_highest_to_lowest(
    pitches: list[EventPitch],
) -> None:
    ordered = highest_first(pitches)

    event = event_of(ordered, Fraction(0), Fraction(1))

    heights = [p.pitch.sounding_semitones() for p in event.pitches]
    assert heights == sorted(heights, reverse=True)


@given(st.lists(event_pitches, min_size=2, max_size=4))
def test_divided_event_rejects_pitches_ordered_from_lowest_to_highest(
    pitches: list[EventPitch],
) -> None:
    ascending = list(reversed(highest_first(pitches)))
    assume(ascending != highest_first(pitches))

    with pytest.raises(ValidationError):
        event_of(ascending, Fraction(0), Fraction(1))


durations = st.sampled_from([Fraction(1, 2), Fraction(1), Fraction(3, 2), Fraction(2)])


@given(st.lists(durations, min_size=2, max_size=8), event_pitches)
def test_notated_voice_events_that_follow_each_other_are_sorted_and_apart(
    event_durations: list[Fraction], event_pitch: EventPitch
) -> None:
    events: list[NoteEvent] = []
    onset = Fraction(0)
    for duration in event_durations:
        events.append(event_of([event_pitch], onset, duration))
        onset += duration

    voice = NotatedVoice(events=tuple(events))

    assert all(a.end() <= b.onset for a, b in zip(voice.events, voice.events[1:], strict=False))


@given(st.lists(durations, min_size=2, max_size=8), event_pitches, st.data())
def test_notated_voice_rejects_any_two_events_swapped(
    event_durations: list[Fraction], event_pitch: EventPitch, data: st.DataObject
) -> None:
    events: list[NoteEvent] = []
    onset = Fraction(0)
    for duration in event_durations:
        events.append(event_of([event_pitch], onset, duration))
        onset += duration
    first = data.draw(st.integers(min_value=0, max_value=len(events) - 2))
    second = data.draw(st.integers(min_value=first + 1, max_value=len(events) - 1))
    events[first], events[second] = events[second], events[first]

    with pytest.raises(ValidationError):
        NotatedVoice(events=tuple(events))
