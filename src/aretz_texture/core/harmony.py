"""Harmony: sounding notes, non chord tones and harmonic windows (spec 003, ADR 0007)."""

from enum import IntEnum, StrEnum
from fractions import Fraction
from itertools import pairwise
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aretz_texture.core.notation import STEP_NAMES, SpelledPitch, StepName
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


class ChordQuality(StrEnum):
    """The kinds of chord of the vocabulary; values are the MusicXML `<kind>` names."""

    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    DOMINANT_SEVENTH = "dominant"
    MAJOR_SEVENTH = "major-seventh"
    MINOR_SEVENTH = "minor-seventh"
    HALF_DIMINISHED_SEVENTH = "half-diminished"
    DIMINISHED_SEVENTH = "diminished-seventh"


# Chord symbol suffix of each quality, as music21 writes its figures (spec 003, section 3.5).
CHORD_SYMBOL_SUFFIXES: dict[ChordQuality, str] = {
    ChordQuality.MAJOR: "",
    ChordQuality.MINOR: "m",
    ChordQuality.DIMINISHED: "dim",
    ChordQuality.AUGMENTED: "aug",
    ChordQuality.DOMINANT_SEVENTH: "7",
    ChordQuality.MAJOR_SEVENTH: "maj7",
    ChordQuality.MINOR_SEVENTH: "m7",
    ChordQuality.HALF_DIMINISHED_SEVENTH: "m7b5",
    ChordQuality.DIMINISHED_SEVENTH: "dim7",
}
SEVENTH_CHORD_QUALITIES = frozenset(
    {
        ChordQuality.DOMINANT_SEVENTH,
        ChordQuality.MAJOR_SEVENTH,
        ChordQuality.MINOR_SEVENTH,
        ChordQuality.HALF_DIMINISHED_SEVENTH,
        ChordQuality.DIMINISHED_SEVENTH,
    }
)
LAST_TRIAD_INVERSION = 2
LAST_SEVENTH_CHORD_INVERSION = 3


class ChordIdentity(BaseModel):
    """A harmonic window read as a chord: root, quality, bass and inversion."""

    model_config = ConfigDict(frozen=True)

    root: PitchName
    quality: ChordQuality
    bass: PitchName
    inversion: int  # 0 root position, 1 first, 2 second, 3 third (sevenths only)

    @model_validator(mode="after")
    def _check_inversion_exists_for_the_quality(self) -> Self:
        is_seventh = self.quality in SEVENTH_CHORD_QUALITIES
        last = LAST_SEVENTH_CHORD_INVERSION if is_seventh else LAST_TRIAD_INVERSION
        if not 0 <= self.inversion <= last:
            kind = "seventh chord" if is_seventh else "triad (no seventh, so no third inversion)"
            message = f"inversion must be from 0 to {last} for a {kind}, got {self.inversion}"
            raise ValueError(message)
        return self

    def symbol(self) -> str:
        """Return the chord symbol: root, quality suffix and, when inverted, a slash and the bass.

        Returns:
            Text such as `G7/B`, `Bdim` or `F#m7b5`, with ASCII accidentals.
        """
        suffix = CHORD_SYMBOL_SUFFIXES[self.quality]
        bass = f"/{self.bass.text()}" if self.inversion else ""
        return f"{self.root.text()}{suffix}{bass}"


class UnidentifiedSonority(BaseModel):
    """A window whose chord tones are outside the vocabulary: a reading, not an error."""

    model_config = ConfigDict(frozen=True)

    pitch_names: tuple[PitchName, ...]  # distinct, in letter order from C
    reason: str  # "no third above any pitch", "C and C# in one window", ...

    @model_validator(mode="after")
    def _check_pitch_names_are_distinct_and_in_letter_order(self) -> Self:
        keys = [(STEP_NAMES.index(name.step), name.alter) for name in self.pitch_names]
        if any(following == previous for previous, following in pairwise(keys)):
            message = "the pitch names of an unidentified sonority must be distinct"
            raise ValueError(message)
        if keys != sorted(keys):
            message = "the pitch names of an unidentified sonority must be in letter order from C"
            raise ValueError(message)
        return self


class GranularityLevel(IntEnum):
    """How coarse a cut of the tree of harmonic events is (architecture, section 8)."""

    SURFACE = 1
    HARMONIC_RHYTHM = 2
    PROLONGATION = 3  # reserved, not computed
    PHRASE = 4  # reserved, not computed


class HarmonicEvent(BaseModel):
    """A node of the tree of harmonic events: a reading over the windows it covers."""

    model_config = ConfigDict(frozen=True)

    level: GranularityLevel
    span: TimeSpan
    reading: ChordIdentity | UnidentifiedSonority
    windows: tuple[HarmonicWindow, ...]  # traceability: the windows it covers, in order
    children: tuple["HarmonicEvent", ...]  # events of the level below; empty at level 1

    @model_validator(mode="after")
    def _check_span_and_children_follow_from_the_windows(self) -> Self:
        if not self.windows:
            message = "an event covers at least one window"
            raise ValueError(message)
        first, last = self.windows[0].span, self.windows[-1].span
        if (self.span.onset, self.span.end) != (first.onset, last.end):
            message = "the span of an event runs from its first window to its last"
            raise ValueError(message)
        if self.level is GranularityLevel.SURFACE and self.children:
            message = "a surface event has no children"
            raise ValueError(message)
        return self
