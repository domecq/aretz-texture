"""Harmony: sounding notes, non chord tones and harmonic windows (spec 003, ADR 0007)."""

from enum import StrEnum
from fractions import Fraction
from itertools import pairwise
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aretz_texture.core.notation import SpelledPitch, StepName
from aretz_texture.core.texture import StreamReference, TimeSpan


class PitchName(BaseModel):
    """The step and alter of a pitch without its octave, such as F sharp."""

    model_config = ConfigDict(frozen=True)

    step: StepName
    alter: Annotated[int, Field(ge=-2, le=2)]  # as in SpelledPitch

    def text(self) -> str:
        """Return the name with ASCII accidentals: "F#", "Bb", "C", "F##"."""
        accidentals = "#" * self.alter if self.alter > 0 else "b" * -self.alter
        return f"{self.step}{accidentals}"


class SoundingNote(BaseModel):
    """One pitch of a notated voice from its attack to the end of its tie chain."""

    model_config = ConfigDict(frozen=True)

    stream: StreamReference  # the notated voice it sounds in
    pitch: SpelledPitch
    onset: Fraction  # attack of the first event of its tie chain, clipped to the phrase
    end: Fraction  # end of the last event of the chain, clipped to the phrase

    @model_validator(mode="after")
    def _check_end_is_after_onset(self) -> Self:
        if self.onset >= self.end:
            message = f"a sounding note must end after its onset, got {self.onset} to {self.end}"
            raise ValueError(message)
        return self


class NonChordToneKind(StrEnum):
    """The kinds of non chord tone this version recognizes (ADR 0007, readings 5 and 6)."""

    PASSING = "passing"
    NEIGHBOR = "neighbor"
    SUSPENSION = "suspension"
    ANTICIPATION = "anticipation"


class NonChordTone(BaseModel):
    """A sounding note, or the part of it from a tactus onset, removed from the harmony."""

    model_config = ConfigDict(frozen=True)

    note: SoundingNote
    kind: NonChordToneKind
    # Where it stops being a chord tone: the tactus onset for a suspension, the onset of the
    # note for the other kinds.
    from_onset: Fraction
    resolution: SpelledPitch | None  # only for a suspension: the pitch it resolves to

    @model_validator(mode="after")
    def _check_resolution_belongs_to_suspensions(self) -> Self:
        is_suspension = self.kind is NonChordToneKind.SUSPENSION
        if is_suspension != (self.resolution is not None):
            message = "a resolution is given exactly for a suspension"
            raise ValueError(message)
        return self


class PlaneNote(BaseModel):
    """The structural note of one plane in a harmonic window."""

    model_config = ConfigDict(frozen=True)

    plane_number: int  # 1 is the highest plane of the phrase (spec 002, section 3.7)
    pitch: SpelledPitch
    stream: StreamReference  # the notated voice it comes from


class HarmonicWindow(BaseModel):
    """A span over which a single harmony is considered to hold, within one phrase."""

    model_config = ConfigDict(frozen=True)

    span: TimeSpan
    phrase_number: int
    plane_count: int  # planes of the phrase in the textural tree
    chord_tones: tuple[SpelledPitch, ...]  # highest first, doublings kept
    plane_notes: tuple[PlaneNote, ...]  # one per plane sounding in the window, by plane number
    non_chord_tones: tuple[NonChordTone, ...]  # those whose from_onset lies in the window
    fermata: bool  # last window of a phrase that closes at a fermata

    @model_validator(mode="after")
    def _check_chord_tones_are_ordered(self) -> Self:
        if not self.chord_tones:
            message = "a window needs at least one chord tone"
            raise ValueError(message)
        keys = [pitch.highest_first_key() for pitch in self.chord_tones]
        if any(following < previous for previous, following in pairwise(keys)):
            message = "chord tones must be ordered from highest to lowest"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _check_plane_notes(self) -> Self:
        numbers = [plane_note.plane_number for plane_note in self.plane_notes]
        if any(following <= previous for previous, following in pairwise(numbers)):
            message = "plane notes must be ordered by plane number, without repeats"
            raise ValueError(message)
        if numbers and (numbers[0] < 1 or numbers[-1] > self.plane_count):
            message = f"plane numbers must lie from 1 to the plane count, {self.plane_count}"
            raise ValueError(message)
        return self

    def bass(self) -> SpelledPitch:
        """Return the lowest chord tone."""
        return self.chord_tones[-1]
