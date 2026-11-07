"""Notated music: spelled pitches, note events and notated voices."""

from enum import StrEnum
from fractions import Fraction
from itertools import pairwise
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

StepName = Literal["C", "D", "E", "F", "G", "A", "B"]

STEP_NAMES: tuple[StepName, ...] = ("C", "D", "E", "F", "G", "A", "B")

SEMITONES_OF_STEP: dict[StepName, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

SEMITONES_PER_OCTAVE = 12

# Scientific pitch notation: C4 is middle C, so octave 0 starts 12 semitones above semitone 0.
OCTAVE_NUMBERING_OFFSET = 1


class SpelledPitch(BaseModel):
    """A pitch written as step, alter and octave, so enharmonic spellings stay different."""

    model_config = ConfigDict(frozen=True)

    step: StepName
    alter: int  # semitones: -2 double flat to 2 double sharp
    octave: int  # scientific pitch notation, middle C is C4

    def pitch_class(self) -> int:
        """Return the pitch class, from 0 (C) to 11 (B)."""
        return (SEMITONES_OF_STEP[self.step] + self.alter) % SEMITONES_PER_OCTAVE

    def sounding_semitones(self) -> int:
        """Return the semitones above C minus one octave, which orders pitches by height."""
        octave_start = (self.octave + OCTAVE_NUMBERING_OFFSET) * SEMITONES_PER_OCTAVE
        return octave_start + SEMITONES_OF_STEP[self.step] + self.alter

    def highest_first_key(self) -> tuple[int, int]:
        """Return a key that sorts pitches from the highest to the lowest.

        Ties between enharmonic spellings are broken by step order, so F sharp
        comes before G flat.
        """
        return (-self.sounding_semitones(), STEP_NAMES.index(self.step))


class TieType(StrEnum):
    """The place of a pitch in a tie."""

    START = "start"
    CONTINUE = "continue"
    STOP = "stop"


class EventPitch(BaseModel):
    """One pitch of a note event together with its tie."""

    model_config = ConfigDict(frozen=True)

    pitch: SpelledPitch
    tie: TieType | None  # None when this pitch is not tied


class NoteEvent(BaseModel):
    """One notated note or divided chord of a notated voice."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction  # quarter lengths from the start of the first bar
    duration: Fraction  # quarter lengths, greater than 0
    pitches: tuple[EventPitch, ...]  # several in a divided event; highest first
    fermata: bool

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        if self.duration <= 0:
            message = f"duration must be greater than 0, got {self.duration}"
            raise ValueError(message)
        if not self.pitches:
            message = "a note event needs at least one pitch"
            raise ValueError(message)
        keys = [event_pitch.pitch.highest_first_key() for event_pitch in self.pitches]
        if any(following < previous for previous, following in pairwise(keys)):
            message = "pitches must be ordered from highest to lowest"
            raise ValueError(message)
        return self

    def end(self) -> Fraction:
        """Return the onset at which this event stops."""
        return self.onset + self.duration


class NotatedVoice(BaseModel):
    """One voice written on the staff of a part, with its own rhythm."""

    model_config = ConfigDict(frozen=True)

    events: tuple[NoteEvent, ...]  # sorted by onset, never overlapping

    @model_validator(mode="after")
    def _check_events_are_sorted_and_apart(self) -> Self:
        for previous, following in pairwise(self.events):
            if following.onset < previous.end():
                message = (
                    f"events at {previous.onset} and {following.onset} are unsorted or overlap"
                )
                raise ValueError(message)
        return self
