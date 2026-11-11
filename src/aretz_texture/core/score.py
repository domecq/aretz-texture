"""A score: bars, signatures and parts."""

from fractions import Fraction
from itertools import pairwise
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from aretz_texture.core.notation import NotatedVoice

QUARTER_LENGTHS_PER_WHOLE_NOTE = 4


class Bar(BaseModel):
    """A measure of the score."""

    model_config = ConfigDict(frozen=True)

    number: int  # the bar number shown in the score; a pickup bar is usually 0
    onset: Fraction
    duration: Fraction  # actual length; shorter than the meter in a pickup bar

    @model_validator(mode="after")
    def _check_duration_is_positive(self) -> Self:
        if self.duration <= 0:
            message = f"bar duration must be greater than 0, got {self.duration}"
            raise ValueError(message)
        return self


class KeySignatureChange(BaseModel):
    """A key signature taking effect at an onset."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction
    sharps: int  # negative for flats


class TimeSignatureChange(BaseModel):
    """A time signature taking effect at an onset."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction
    numerator: int
    denominator: int

    def bar_duration(self) -> Fraction:
        """Return the length of a complete bar in this meter, in quarter lengths."""
        return Fraction(QUARTER_LENGTHS_PER_WHOLE_NOTE * self.numerator, self.denominator)


class Part(BaseModel):
    """One part of the source score, identified by its position in the score."""

    model_config = ConfigDict(frozen=True)

    name: str | None  # part name as written in the source
    instrument_name: str | None  # source of the timbre factor (ADR 0004)
    key_signatures: tuple[KeySignatureChange, ...]  # first one at onset 0
    voices: tuple[NotatedVoice, ...]  # at least one; notated voice 1 first

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        if not self.voices:
            message = "a part needs at least one notated voice"
            raise ValueError(message)
        if len(self.voices) > 1 and not self.voices[-1].has_content():
            message = "the last notated voice of a part with several must have content"
            raise ValueError(message)
        if not self.key_signatures or self.key_signatures[0].onset != 0:
            message = "the first key signature must be at onset 0"
            raise ValueError(message)
        return self


class Score(BaseModel):
    """A complete piece: its bars, its time signatures and its parts in score order."""

    model_config = ConfigDict(frozen=True)

    bars: tuple[Bar, ...]  # contiguous, starting at onset 0
    time_signatures: tuple[TimeSignatureChange, ...]  # first one at onset 0
    parts: tuple[Part, ...]  # score order, top to bottom; at least one

    @model_validator(mode="after")
    def _check_structure(self) -> Self:
        if not self.parts:
            message = "a score needs at least one part"
            raise ValueError(message)
        self._check_bars_are_contiguous()
        if not self.time_signatures or self.time_signatures[0].onset != 0:
            message = "the first time signature must be at onset 0"
            raise ValueError(message)
        self._check_events_end_within_the_bars()
        return self

    def _check_bars_are_contiguous(self) -> None:
        if not self.bars or self.bars[0].onset != 0:
            message = "bars must start at onset 0"
            raise ValueError(message)
        for previous, following in pairwise(self.bars):
            if following.onset != previous.onset + previous.duration:
                message = f"bar {following.number} does not follow bar {previous.number}"
                raise ValueError(message)

    def _check_events_end_within_the_bars(self) -> None:
        end = self.end()
        for part in self.parts:
            for voice in part.voices:
                if any(event.end() > end for event in [*voice.events, *voice.rest_fermatas]):
                    message = f"an event ends after the last bar, at {end}"
                    raise ValueError(message)
                if any(grace_note.onset >= end for grace_note in voice.grace_notes):
                    message = f"a grace note ornaments nothing, at or after the last bar, at {end}"
                    raise ValueError(message)

    def end(self) -> Fraction:
        """Return the onset at which the last bar stops."""
        last_bar = self.bars[-1]
        return last_bar.onset + last_bar.duration

    def pickup_duration(self) -> Fraction:
        """Return the length of the pickup bar, or 0 when the first bar is complete."""
        first_bar_length = self.time_signatures[0].bar_duration()
        first_bar = self.bars[0]
        return first_bar.duration if first_bar.duration < first_bar_length else Fraction(0)


class IngestedScore(BaseModel):
    """A score read from a source, with what ingestion ignored."""

    model_config = ConfigDict(frozen=True)

    score: Score
    has_lyrics: bool  # the source had lyrics, which this spec ignores
