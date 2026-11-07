# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Conversion of a music21 score into the core model.

The conversion is lossless for notes: every part, every notated voice and every
pitch of a divided event is kept. What the core model cannot represent raises
`UnsupportedScoreError` instead of being dropped.
"""

from collections.abc import Iterable
from fractions import Fraction

from music21 import chord, expressions, key, meter, note, stream
from pydantic import ValidationError

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.notation import (
    EventPitch,
    NotatedVoice,
    NoteEvent,
    SpelledPitch,
    TieType,
)
from aretz_texture.core.score import (
    Bar,
    IngestedScore,
    KeySignatureChange,
    Part,
    Score,
    TimeSignatureChange,
)

# Ties that music21 reads and the core model cannot represent.
_UNSUPPORTED_TIE_TYPES = frozenset({"let-ring", "continue-let-ring"})


def convert_score(source: stream.Score) -> IngestedScore:
    """Convert a music21 score into the core model.

    Args:
        source: A music21 score, as read from MusicXML.

    Returns:
        The core score with every part of the source, and whether the source had lyrics.

    Raises:
        UnsupportedScoreError: The source parses but the core model cannot represent it.
    """
    try:
        score = _convert_parts(list(source.parts))
    except ValidationError as error:
        message = f"the score breaks a structural rule of the core model: {error}"
        raise UnsupportedScoreError(message) from error
    return IngestedScore(score=score, has_lyrics=_has_lyrics(source))


def _convert_parts(parts: list[stream.Part]) -> Score:
    if not parts:
        message = "the score has no parts"
        raise UnsupportedScoreError(message)
    bars = _read_bars(parts[0])
    time_signatures = _read_time_signatures(parts[0], bars)
    for part_number, part in enumerate(parts[1:], start=2):
        _require_same_bars(bars, _read_bars(part), part_number)
        _require_same_time_signatures(time_signatures, part, bars, part_number)
    return Score(
        bars=bars,
        time_signatures=time_signatures,
        parts=tuple(_convert_part(part) for part in parts),
    )


def _fraction(value: float | Fraction) -> Fraction:
    # music21 gives floats only when they are binary exact (music21.common.opFrac).
    return Fraction(value)


def _clean_name(name: str | None) -> str | None:
    if name is None:
        return None
    trimmed = name.strip()
    return trimmed or None


def _read_bars(part: stream.Part) -> tuple[Bar, ...]:
    measures = list(part.getElementsByClass(stream.Measure))
    if not measures:
        message = "a part has no measures"
        raise UnsupportedScoreError(message)
    onsets = [_fraction(measure.offset) for measure in measures]
    ends = [*onsets[1:], onsets[-1] + _fraction(measures[-1].highestTime)]
    return tuple(
        Bar(number=measure.number, onset=onset, duration=end - onset)
        for measure, onset, end in zip(measures, onsets, ends, strict=True)
    )


def _require_same_bars(expected: tuple[Bar, ...], found: tuple[Bar, ...], part_number: int) -> None:
    if expected != found:
        message = f"the bars of part {part_number} do not line up with the bars of part 1"
        raise UnsupportedScoreError(message)


def _read_time_signatures(
    part: stream.Part, bars: tuple[Bar, ...]
) -> tuple[TimeSignatureChange, ...]:
    changes = tuple(
        TimeSignatureChange(
            onset=_fraction(signature.getOffsetInHierarchy(part)),
            numerator=signature.numerator,
            denominator=signature.denominator,
        )
        for signature in part.recurse().getElementsByClass(meter.TimeSignature)
    )
    if not changes or changes[0].onset != 0:
        message = "the score has no time signature at onset 0"
        raise UnsupportedScoreError(message)
    bar_onsets = {bar.onset for bar in bars}
    for change in changes:
        if change.onset not in bar_onsets:
            message = f"a time signature change at onset {change.onset} does not fall on a bar line"
            raise UnsupportedScoreError(message)
    return changes


def _require_same_time_signatures(
    expected: tuple[TimeSignatureChange, ...],
    part: stream.Part,
    bars: tuple[Bar, ...],
    part_number: int,
) -> None:
    if _read_time_signatures(part, bars) != expected:
        message = f"the time signatures of part {part_number} differ from those of part 1"
        raise UnsupportedScoreError(message)


def _convert_part(part: stream.Part) -> Part:
    instrument = part.getInstrument(returnDefault=False)
    if instrument is not None and instrument.transposition is not None:
        message = f"part {part.partName!r} has a transposing instrument, which is not supported"
        raise UnsupportedScoreError(message)
    return Part(
        name=_clean_name(part.partName),
        instrument_name=_clean_name(instrument.instrumentName) if instrument else None,
        key_signatures=_read_key_signatures(part),
        voices=_read_notated_voices(part),
    )


def _read_key_signatures(part: stream.Part) -> tuple[KeySignatureChange, ...]:
    changes = [
        KeySignatureChange(
            onset=_fraction(signature.getOffsetInHierarchy(part)), sharps=signature.sharps
        )
        for signature in part.recurse().getElementsByClass(key.KeySignature)
    ]
    if not changes or changes[0].onset != 0:
        changes.insert(0, KeySignatureChange(onset=Fraction(0), sharps=0))
    return tuple(
        change
        for index, change in enumerate(changes)
        if index == 0 or change.sharps != changes[index - 1].sharps
    )


def _read_notated_voices(part: stream.Part) -> tuple[NotatedVoice, ...]:
    events_by_voice: dict[int, list[NoteEvent]] = {}
    for measure in part.getElementsByClass(stream.Measure):
        for voice_number, container in _voice_containers(measure):
            events = _read_events(container, _fraction(measure.offset))
            if events:
                events_by_voice.setdefault(voice_number, []).extend(events)
    voice_count = max(events_by_voice, default=1)
    return tuple(
        NotatedVoice(events=tuple(events_by_voice.get(voice_number, ())))
        for voice_number in range(1, voice_count + 1)
    )


def _voice_containers(
    measure: stream.Measure,
) -> list[tuple[int, stream.Measure | stream.Voice]]:
    if not measure.hasVoices():
        return [(1, measure)]
    for element in measure.notesAndRests:
        if not isinstance(element, note.Rest):
            message = f"bar {measure.number} has a note outside its voices"
            raise UnsupportedScoreError(message)
    return list(enumerate(measure.voices, start=1))


def _read_events(
    container: stream.Measure | stream.Voice, measure_onset: Fraction
) -> list[NoteEvent]:
    # A voice sits at offset 0 of its measure in practice; adding it keeps the onset exact anyway.
    is_voice = isinstance(container, stream.Voice)
    container_onset = measure_onset + (_fraction(container.offset) if is_voice else 0)
    events: list[NoteEvent] = []
    for element in container.notesAndRests:
        if isinstance(element, note.Rest):
            _reject_fermata_on_rest(element)
            continue
        events.append(_convert_element(element, container_onset))
    return events


def _reject_fermata_on_rest(rest: note.Rest) -> None:
    if _has_fermata(rest.expressions):
        message = "a fermata on a rest is not supported yet"
        raise UnsupportedScoreError(message)


def _convert_element(element: note.GeneralNote, container_onset: Fraction) -> NoteEvent:
    if isinstance(element, note.Unpitched):
        message = "unpitched notes are not supported"
        raise UnsupportedScoreError(message)
    if not isinstance(element, (note.Note, chord.Chord)):
        message = f"unsupported element {type(element).__name__}"
        raise UnsupportedScoreError(message)
    if element.duration.isGrace:
        message = "grace notes are not supported yet"
        raise UnsupportedScoreError(message)
    sounding_notes = element.notes if isinstance(element, chord.Chord) else [element]
    pitches = sorted(
        (_convert_pitch(sounding) for sounding in sounding_notes),
        key=lambda event_pitch: event_pitch.pitch.highest_first_key(),
    )
    expressions_of_element = list(element.expressions)
    if isinstance(element, chord.Chord):
        expressions_of_element += [e for sounding in sounding_notes for e in sounding.expressions]
    return NoteEvent(
        onset=container_onset + _fraction(element.offset),
        duration=_fraction(element.duration.quarterLength),
        pitches=tuple(pitches),
        fermata=_has_fermata(expressions_of_element),
    )


def _has_fermata(expression_list: Iterable[expressions.Expression]) -> bool:
    return any(isinstance(expression, expressions.Fermata) for expression in expression_list)


def _convert_pitch(sounding: note.Note) -> EventPitch:
    pitch = sounding.pitch
    alter = pitch.accidental.alter if pitch.accidental is not None else 0
    if alter != int(alter):
        message = f"microtonal accidental with alter {alter} is not supported"
        raise UnsupportedScoreError(message)
    spelled = SpelledPitch(step=pitch.step, alter=int(alter), octave=pitch.implicitOctave)
    return EventPitch(pitch=spelled, tie=_convert_tie(sounding))


def _convert_tie(sounding: note.Note) -> TieType | None:
    if sounding.tie is None:
        return None
    tie_type = sounding.tie.type
    if tie_type in _UNSUPPORTED_TIE_TYPES:
        message = f"tie of type {tie_type!r} is not supported"
        raise UnsupportedScoreError(message)
    try:
        return TieType(tie_type)
    except ValueError as error:
        message = f"tie of unknown type {tie_type!r}"
        raise UnsupportedScoreError(message) from error


def _has_lyrics(source: stream.Score) -> bool:
    for element in source.recurse().notes:
        sounding_notes = element.notes if isinstance(element, chord.Chord) else []
        if element.lyrics or any(sounding.lyrics for sounding in sounding_notes):
            return True
    return False


__all__ = ["convert_score"]
