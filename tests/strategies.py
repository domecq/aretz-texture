"""Hypothesis strategies that generate core scores for the round trip properties."""

import string
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise

from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

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

# (numerator, denominator) pairs of the meters the properties use.
METERS = [(2, 4), (3, 4), (4, 4), (3, 2)]
PLAIN_DURATIONS = [
    Fraction(1, 2),
    Fraction(1),
    Fraction(3, 2),
    Fraction(2),
    Fraction(3),
    Fraction(4),
]
# Notated values of grace notes: a sixteenth and an eighth.
GRACE_NOTE_VALUES = [Fraction(1, 4), Fraction(1, 2)]
# Rests of these lengths are stretched by music21 to the bar when they stand alone in a
# measure of another length, so the generated fermata rests avoid that case.
STRETCHABLE_REST_DURATIONS = {Fraction(4), Fraction(8)}
TRIPLET_EIGHTH = Fraction(1, 3)
TRIPLET_GROUP_SIZE = 3
MAX_FULL_BARS = 4
MAX_SHARPS = 4

SPELLED_PITCHES = st.builds(
    SpelledPitch,
    step=st.sampled_from(STEP_NAMES),
    alter=st.sampled_from([-1, 0, 1]),
    octave=st.integers(min_value=2, max_value=5),
)
NAMES = st.none() | st.text(alphabet=string.ascii_letters + string.digits + " ", min_size=1).map(
    str.strip
).filter(bool)


@dataclass
class _Draft:
    """An event under construction, so that ties can be applied before it is frozen."""

    onset: Fraction
    duration: Fraction
    pitches: list[SpelledPitch]
    ties: list[TieType | None]
    fermata: bool

    def freeze(self) -> NoteEvent:
        pairs = sorted(
            zip(self.pitches, self.ties, strict=True), key=lambda pair: pair[0].highest_first_key()
        )
        return NoteEvent(
            onset=self.onset,
            duration=self.duration,
            pitches=tuple(EventPitch(pitch=pitch, tie=tie) for pitch, tie in pairs),
            fermata=self.fermata,
        )


@st.composite
def _tiling(draw: DrawFn, length: Fraction) -> list[Fraction]:
    """Return durations that tile a bar: plain values, and triplet eighths in whole beats."""
    durations: list[Fraction] = []
    cursor = Fraction(0)
    while cursor < length:
        remaining = length - cursor
        options = [duration for duration in PLAIN_DURATIONS if duration <= remaining]
        if cursor.denominator == 1 and remaining >= 1:
            options.append(TRIPLET_EIGHTH)
        choice = draw(st.sampled_from(options))
        if choice == TRIPLET_EIGHTH:
            durations += [TRIPLET_EIGHTH] * TRIPLET_GROUP_SIZE
            cursor += 1
        else:
            durations.append(choice)
            cursor += choice
    return durations


@st.composite
def _draft_of(draw: DrawFn, onset: Fraction, duration: Fraction) -> _Draft:
    pitches = draw(st.lists(SPELLED_PITCHES, min_size=1, max_size=1))
    if draw(st.integers(min_value=0, max_value=9)) == 0:
        pitches += draw(st.lists(SPELLED_PITCHES, min_size=1, max_size=2))
        if draw(st.booleans()):
            pitches.append(pitches[0])
    fermata = draw(st.integers(min_value=0, max_value=9)) == 0
    return _Draft(onset, duration, pitches, [None] * len(pitches), fermata)


@dataclass
class _VoiceDrafts:
    """What a notated voice holds before ties are applied."""

    events: list[_Draft]
    rest_fermatas: list[RestFermata]
    grace_notes: list[GraceNote]


@st.composite
def _grace_notes_at(draw: DrawFn, onset: Fraction) -> list[GraceNote]:
    count = {0: 1, 1: 2}.get(draw(st.integers(min_value=0, max_value=9)), 0)
    graces: list[GraceNote] = []
    for _ in range(count):
        pitches = draw(st.lists(SPELLED_PITCHES, min_size=1, max_size=2))
        ordered = sorted(pitches, key=lambda pitch: pitch.highest_first_key())
        graces.append(
            GraceNote(
                onset=onset,
                pitches=tuple(EventPitch(pitch=pitch, tie=None) for pitch in ordered),
                notated_value=draw(st.sampled_from(GRACE_NOTE_VALUES)),
                slash=draw(st.booleans()),
            )
        )
    return graces


@st.composite
def _voice_drafts(
    draw: DrawFn, bar_durations: list[Fraction], meter_duration: Fraction
) -> _VoiceDrafts:
    drafts = _VoiceDrafts([], [], [])
    onset = Fraction(0)
    for bar_duration in bar_durations:
        bar_is_silent = draw(st.integers(min_value=0, max_value=4)) == 0
        cursor = onset
        for duration in draw(_tiling(bar_duration)):
            drafts.grace_notes += draw(_grace_notes_at(cursor))
            if not bar_is_silent and draw(st.integers(min_value=0, max_value=3)) > 0:
                drafts.events.append(draw(_draft_of(cursor, duration)))
            elif _may_carry_fermata(duration, meter_duration) and draw(st.integers(0, 9)) == 0:
                drafts.rest_fermatas.append(RestFermata(onset=cursor, duration=duration))
            cursor += duration
        onset += bar_duration
    return drafts


def _may_carry_fermata(duration: Fraction, meter_duration: Fraction) -> bool:
    return duration not in STRETCHABLE_REST_DURATIONS or duration == meter_duration


def _apply_tie(draw: DrawFn, source: _Draft, target: _Draft) -> None:
    source_index = draw(st.integers(min_value=0, max_value=len(source.pitches) - 1))
    target_index = draw(st.integers(min_value=0, max_value=len(target.pitches) - 1))
    target.pitches[target_index] = source.pitches[source_index]
    target.ties[target_index] = TieType.STOP
    already_stopped = source.ties[source_index] is TieType.STOP
    source.ties[source_index] = TieType.CONTINUE if already_stopped else TieType.START


@st.composite
def _notated_voice(
    draw: DrawFn, bar_durations: list[Fraction], meter_duration: Fraction
) -> NotatedVoice:
    drafts = draw(_voice_drafts(bar_durations, meter_duration))
    for source, target in pairwise(drafts.events):
        touching = source.onset + source.duration == target.onset
        if touching and draw(st.integers(min_value=0, max_value=3)) == 0:
            _apply_tie(draw, source, target)
    return NotatedVoice(
        events=tuple(draft.freeze() for draft in drafts.events),
        grace_notes=tuple(drafts.grace_notes),
        rest_fermatas=tuple(drafts.rest_fermatas),
    )


@st.composite
def _part(
    draw: DrawFn,
    bar_durations: list[Fraction],
    meter_duration: Fraction,
    voice_count: int,
    key_signature: KeySignatureChange,
) -> Part:
    voices = [draw(_notated_voice(bar_durations, meter_duration)) for _ in range(voice_count)]
    if voice_count > 1 and not voices[-1].has_content():
        voices[-1] = draw(
            _notated_voice(bar_durations, meter_duration).filter(NotatedVoice.has_content)
        )
    name = draw(NAMES)
    # music21 gives a part without a name the name of its instrument when it reads the file
    # back, so the generated instrument name is only kept with a part name.
    instrument_name = draw(NAMES) if name is not None else None
    return Part(
        name=name,
        instrument_name=instrument_name,
        key_signatures=(key_signature,),
        voices=tuple(voices),
    )


def _bars_of(bar_durations: list[Fraction], has_pickup: bool) -> tuple[Bar, ...]:
    bars: list[Bar] = []
    onset = Fraction(0)
    first_number = 0 if has_pickup else 1
    for index, duration in enumerate(bar_durations):
        bars.append(Bar(number=first_number + index, onset=onset, duration=duration))
        onset += duration
    return tuple(bars)


@st.composite
def _scores(
    draw: DrawFn,
    part_counts: st.SearchStrategy[int],
    voice_counts: st.SearchStrategy[int],
    same_key_in_every_part: bool,
) -> Score:
    numerator, denominator = draw(st.sampled_from(METERS))
    meter = TimeSignatureChange(onset=Fraction(0), numerator=numerator, denominator=denominator)
    full_bar = meter.bar_duration()
    bar_durations = [full_bar] * draw(st.integers(min_value=1, max_value=MAX_FULL_BARS))
    has_pickup = draw(st.booleans())
    if has_pickup:
        pickup = Fraction(draw(st.integers(min_value=1, max_value=int(full_bar * 2) - 1)), 2)
        bar_durations.insert(0, pickup)
    sharps = st.integers(min_value=-MAX_SHARPS, max_value=MAX_SHARPS)
    shared_key = KeySignatureChange(onset=Fraction(0), sharps=draw(sharps))
    parts = []
    for _ in range(draw(part_counts)):
        key = (
            shared_key
            if same_key_in_every_part
            else KeySignatureChange(onset=Fraction(0), sharps=draw(sharps))
        )
        parts.append(draw(_part(bar_durations, full_bar, draw(voice_counts), key)))
    return Score(
        bars=_bars_of(bar_durations, has_pickup),
        time_signatures=(meter,),
        parts=tuple(parts),
    )


def scores() -> st.SearchStrategy[Score]:
    """Generate scores of one to six parts, each with one to three notated voices."""
    return _scores(st.integers(1, 6), st.integers(1, 3), same_key_in_every_part=False)


def four_part_scores() -> st.SearchStrategy[Score]:
    """Generate scores that the grand staff accepts: four parts, one voice, one shared key."""
    return _scores(st.just(4), st.just(1), same_key_in_every_part=True)
