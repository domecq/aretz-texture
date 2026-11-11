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


def _check_pitches_are_ordered(pitches: tuple[EventPitch, ...]) -> None:
    if not pitches:
        message = "at least one pitch is needed"
        raise ValueError(message)
    keys = [event_pitch.pitch.highest_first_key() for event_pitch in pitches]
    if any(following < previous for previous, following in pairwise(keys)):
        message = "pitches must be ordered from highest to lowest"
        raise ValueError(message)


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
        _check_pitches_are_ordered(self.pitches)
        return self

    def end(self) -> Fraction:
        """Return the onset at which this event stops."""
        return self.onset + self.duration


class GraceNote(BaseModel):
    """An ornamental note or chord written small, which takes no time in the bar."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction  # onset of the note or rest it ornaments
    pitches: tuple[EventPitch, ...]  # highest first
    notated_value: Fraction  # quarter lengths of the symbol, 1/2 for an eighth
    slash: bool  # written with a slash through the stem

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        if self.notated_value <= 0:
            message = f"notated value must be greater than 0, got {self.notated_value}"
            raise ValueError(message)
        _check_pitches_are_ordered(self.pitches)
        return self


class RestFermata(BaseModel):
    """A fermata on a rest, kept because the rest is notated, unlike a plain gap."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction
    duration: Fraction  # the notated rest that carries the fermata

    @model_validator(mode="after")
    def _check_duration_is_positive(self) -> Self:
        if self.duration <= 0:
            message = f"duration must be greater than 0, got {self.duration}"
            raise ValueError(message)
        return self

    def end(self) -> Fraction:
        """Return the onset at which this rest stops."""
        return self.onset + self.duration


class NotatedVoice(BaseModel):
    """One voice written on the staff of a part, with its own rhythm."""

    model_config = ConfigDict(frozen=True)

    events: tuple[NoteEvent, ...]  # sorted by onset, never overlapping
    grace_notes: tuple[GraceNote, ...] = ()  # sorted by onset, source order kept
    rest_fermatas: tuple[RestFermata, ...] = ()  # each inside a gap between events

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        solid = sorted([*self.events, *self.rest_fermatas], key=lambda item: item.onset)
        for previous, following in pairwise(solid):
            if following.onset < previous.end():
                message = f"items at {previous.onset} and {following.onset} are unsorted or overlap"
                raise ValueError(message)
        if [e.onset for e in self.events] != sorted(e.onset for e in self.events):
            message = "events must be sorted by onset"
            raise ValueError(message)
        if [r.onset for r in self.rest_fermatas] != sorted(r.onset for r in self.rest_fermatas):
            message = "rest fermatas must be sorted by onset"
            raise ValueError(message)
        self._check_grace_notes(solid)
        return self

    def _check_grace_notes(self, solid: list[NoteEvent | RestFermata]) -> None:
        onsets = [grace_note.onset for grace_note in self.grace_notes]
        if onsets != sorted(onsets):
            message = "grace notes must be sorted by onset"
            raise ValueError(message)
        for grace_note in self.grace_notes:
            if any(item.onset < grace_note.onset < item.end() for item in solid):
                message = f"the grace note at {grace_note.onset} falls inside a note or rest"
                raise ValueError(message)

    def has_content(self) -> bool:
        """Return whether anything is written in this voice besides plain rests."""
        return bool(self.events or self.grace_notes or self.rest_fermatas)

    def within(self, start: Fraction, end: Fraction) -> "NotatedVoice":
        """Return the part of this voice that starts from `start` up to, not including, `end`."""
        return NotatedVoice(
            events=tuple(e for e in self.events if start <= e.onset < end),
            grace_notes=tuple(g for g in self.grace_notes if start <= g.onset < end),
            rest_fermatas=tuple(r for r in self.rest_fermatas if start <= r.onset < end),
        )
