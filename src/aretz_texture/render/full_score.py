# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Writing the core model as a MusicXML full score, one staff per part."""

from fractions import Fraction
from itertools import pairwise
from pathlib import Path

from music21 import chord, clef, expressions, instrument, key, meter, note, pitch, stream, tie

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.notation import EventPitch, NotatedVoice, NoteEvent
from aretz_texture.core.score import Bar, KeySignatureChange, Part, Score, TimeSignatureChange


def write_full_score(score: Score, output_path: Path) -> None:
    """Write a score as MusicXML with one staff per part, in score order.

    Args:
        score: The score to write.
        output_path: The MusicXML file to write; an existing file is overwritten.

    Raises:
        OSError: The file cannot be written.
    """
    music21_score = stream.Score()
    for part in score.parts:
        music21_score.insert(0, _build_part(score, part))
    music21_score.write("musicxml", fp=output_path)


def _build_part(score: Score, part: Part) -> stream.Part:
    music21_part = stream.Part()
    if part.name is not None:
        music21_part.partName = part.name
    if part.instrument_name is not None:
        music21_instrument = instrument.Instrument()
        music21_instrument.instrumentName = part.instrument_name
        music21_part.insert(0, music21_instrument)
    measures = [_build_measure(score, part, bar) for bar in score.bars]
    for bar, measure in zip(score.bars, measures, strict=True):
        music21_part.insert(bar.onset, measure)
    measures[0].insert(0, clef.bestClef(music21_part.flatten()))
    return music21_part


def _build_measure(score: Score, part: Part, bar: Bar) -> stream.Measure:
    measure = stream.Measure(number=bar.number)
    for change in score.time_signatures:
        if change.onset == bar.onset:
            measure.insert(0, meter.TimeSignature(f"{change.numerator}/{change.denominator}"))
    _set_padding(measure, score, bar)
    events_by_voice = [_events_in_bar(voice, bar) for voice in part.voices]
    voice_count = _voice_count(events_by_voice)
    key_changes = [
        change for change in part.key_signatures if bar.onset <= change.onset < _bar_end(bar)
    ]
    key_offsets = {change.onset - bar.onset for change in key_changes} - {Fraction(0)}
    containers = _containers(measure, voice_count)
    for container, events in zip(containers, events_by_voice, strict=False):
        _fill(container, events, bar, key_offsets)
    for change in key_changes:
        _insert_key_signature(measure, containers, events_by_voice, bar, change)
    return measure


def _voice_count(events_by_voice: list[list[NoteEvent]]) -> int:
    numbers_with_content = (number for number, events in enumerate(events_by_voice, 1) if events)
    return max(numbers_with_content, default=1)


def _events_in_bar(voice: NotatedVoice, bar: Bar) -> list[NoteEvent]:
    return [event for event in voice.events if bar.onset <= event.onset < _bar_end(bar)]


def _containers(measure: stream.Measure, voice_count: int) -> list[stream.Measure | stream.Voice]:
    if voice_count == 1:
        return [measure]
    containers: list[stream.Measure | stream.Voice] = []
    for voice_number in range(1, voice_count + 1):
        voice = stream.Voice()
        voice.id = str(voice_number)
        measure.insert(0, voice)
        containers.append(voice)
    return containers


def _fill(
    container: stream.Measure | stream.Voice,
    events: list[NoteEvent],
    bar: Bar,
    split_offsets: set[Fraction],
) -> None:
    cursor = Fraction(0)
    for event in events:
        _insert_rests(container, cursor, event.onset - bar.onset, split_offsets)
        container.insert(event.onset - bar.onset, _build_note(event))
        cursor = event.end() - bar.onset
    _insert_rests(container, cursor, bar.duration, split_offsets)


def _insert_rests(
    container: stream.Measure | stream.Voice,
    start: Fraction,
    end: Fraction,
    split_offsets: set[Fraction],
) -> None:
    # A gap is cut where a key signature change falls inside it, so that the change can
    # be written at its exact onset: music21 writes it after the element that spans it.
    cuts = [start, *sorted(offset for offset in split_offsets if start < offset < end), end]
    for rest_start, rest_end in pairwise(cuts):
        if rest_end > rest_start:
            container.insert(rest_start, note.Rest(quarterLength=rest_end - rest_start))


def _insert_key_signature(
    measure: stream.Measure,
    containers: list[stream.Measure | stream.Voice],
    events_by_voice: list[list[NoteEvent]],
    bar: Bar,
    change: KeySignatureChange,
) -> None:
    offset = change.onset - bar.onset
    signature = key.KeySignature(change.sharps)
    if offset == 0:
        # music21 drops a key signature at a later offset of a measure that has voices;
        # at offset 0 it is written whatever the measure holds.
        measure.insert(0, signature)
        return
    for container, events in zip(containers, events_by_voice, strict=False):
        if not any(event.onset - bar.onset < offset < event.end() - bar.onset for event in events):
            container.insert(offset, signature)
            return
    message = f"the key signature change at onset {change.onset} falls inside a note of every voice"
    raise UnsupportedScoreError(message)


def _set_padding(measure: stream.Measure, score: Score, bar: Bar) -> None:
    meter_in_force = _time_signature_in_force(score, bar)
    missing = meter_in_force.bar_duration() - bar.duration
    if missing <= 0:
        return
    # Without padding music21 writes an invisible rest to fill the short bar.
    if bar.onset == 0:
        measure.paddingLeft = missing
    else:
        measure.paddingRight = missing


def _time_signature_in_force(score: Score, bar: Bar) -> TimeSignatureChange:
    return [change for change in score.time_signatures if change.onset <= bar.onset][-1]


def _build_note(event: NoteEvent) -> note.GeneralNote:
    notes = [_build_pitch(event_pitch, event.duration) for event_pitch in event.pitches]
    element = notes[0] if len(notes) == 1 else chord.Chord(notes)
    if len(notes) > 1:
        element.quarterLength = event.duration
    if event.fermata:
        element.expressions.append(expressions.Fermata())
    return element


def _build_pitch(event_pitch: EventPitch, duration: Fraction) -> note.Note:
    spelled = event_pitch.pitch
    music21_pitch = pitch.Pitch()
    music21_pitch.step = spelled.step
    music21_pitch.octave = spelled.octave
    if spelled.alter != 0:
        music21_pitch.accidental = pitch.Accidental(spelled.alter)
    music21_note = note.Note(music21_pitch, quarterLength=duration)
    if event_pitch.tie is not None:
        music21_note.tie = tie.Tie(event_pitch.tie.value)
    return music21_note


def _bar_end(bar: Bar) -> Fraction:
    return bar.onset + bar.duration
