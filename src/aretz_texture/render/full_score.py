# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Writing the core model as a MusicXML full score, one staff per part."""

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from music21 import (
    chord,
    clef,
    duration,
    expressions,
    instrument,
    key,
    meter,
    note,
    pitch,
    stream,
    tie,
)

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.notation import EventPitch, GraceNote, NotatedVoice, NoteEvent, RestFermata
from aretz_texture.core.score import Bar, KeySignatureChange, Part, Score, TimeSignatureChange
from aretz_texture.render.rests import (
    BarRests,
    insert_rests,
    require_fermata_rests_read_back_exactly,
)


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
    voices_in_bar = [voice.within(bar.onset, _bar_end(bar)) for voice in part.voices]
    voice_count = _voice_count(voices_in_bar)
    key_changes = [
        change for change in part.key_signatures if bar.onset <= change.onset < _bar_end(bar)
    ]
    rests = BarRests(
        meter_duration=_time_signature_in_force(score, bar).bar_duration(),
        split_offsets=frozenset(change.onset - bar.onset for change in key_changes) - {Fraction(0)},
    )
    containers = _containers(measure, voice_count)
    for container, voice in zip(containers, voices_in_bar, strict=False):
        _fill(container, voice, bar, rests)
    require_fermata_rests_read_back_exactly(measure, rests.meter_duration)
    for change in key_changes:
        _insert_key_signature(measure, containers, voices_in_bar, bar, change)
    return measure


def _voice_count(voices_in_bar: list[NotatedVoice]) -> int:
    numbers_with_content = (
        number for number, voice in enumerate(voices_in_bar, 1) if voice.has_content()
    )
    return max(numbers_with_content, default=1)


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
    voice: NotatedVoice,
    bar: Bar,
    rests: BarRests,
) -> None:
    # A rest is cut where a grace note falls, so that the grace note comes right before a rest.
    grace_offsets = frozenset(grace_note.onset - bar.onset for grace_note in voice.grace_notes)
    gap_rests = replace(rests, split_offsets=rests.split_offsets | grace_offsets)
    cursor = Fraction(0)
    for item in sorted([*voice.events, *voice.rest_fermatas], key=lambda item: item.onset):
        insert_rests(container, cursor, item.onset - bar.onset, gap_rests)
        cursor = item.end() - bar.onset
    insert_rests(container, cursor, bar.duration, gap_rests)
    for event in voice.events:
        container.insert(event.onset - bar.onset, _build_note(event))
    for rest_fermata in voice.rest_fermatas:
        container.insert(rest_fermata.onset - bar.onset, _build_rest_fermata(rest_fermata))
    for grace_note in voice.grace_notes:
        container.insert(grace_note.onset - bar.onset, _build_grace_note(grace_note))


def _insert_key_signature(
    measure: stream.Measure,
    containers: list[stream.Measure | stream.Voice],
    voices_in_bar: list[NotatedVoice],
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
    for container, voice in zip(containers, voices_in_bar, strict=False):
        held = [*voice.events, *voice.rest_fermatas]
        if not any(item.onset - bar.onset < offset < item.end() - bar.onset for item in held):
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
        _keep_duration_as_written(element)
    if event.fermata:
        fermata = expressions.Fermata()
        # music21 makes a fermata inverted, printed below the staff, unless told otherwise.
        fermata.type = "upright"
        element.expressions.append(fermata)
    return element


def _build_rest_fermata(rest_fermata: RestFermata) -> note.Rest:
    rest = note.Rest(quarterLength=rest_fermata.duration)
    fermata = expressions.Fermata()
    # music21 makes a fermata inverted, printed below the staff, unless told otherwise.
    fermata.type = "upright"
    rest.expressions.append(fermata)
    return rest


def _build_grace_note(grace_note: GraceNote) -> note.GeneralNote:
    notes = [
        _build_pitch(event_pitch, grace_note.notated_value) for event_pitch in grace_note.pitches
    ]
    element = notes[0] if len(notes) == 1 else chord.Chord(notes)
    symbol = duration.Duration(quarterLength=grace_note.notated_value)
    grace_duration = duration.GraceDuration(type=symbol.type, dots=symbol.dots)
    grace_duration.slash = grace_note.slash
    element.duration = grace_duration
    return element


def _build_pitch(event_pitch: EventPitch, duration: Fraction) -> note.Note:
    spelled = event_pitch.pitch
    music21_pitch = pitch.Pitch()
    music21_pitch.step = spelled.step
    music21_pitch.octave = spelled.octave
    if spelled.alter != 0:
        music21_pitch.accidental = pitch.Accidental(spelled.alter)
    music21_note = note.Note(music21_pitch, quarterLength=duration)
    _keep_duration_as_written(music21_note)
    if event_pitch.tie is not None:
        music21_note.tie = tie.Tie(event_pitch.tie.value)
    return music21_note


def _bar_end(bar: Bar) -> Fraction:
    return bar.onset + bar.duration


def _keep_duration_as_written(element: note.GeneralNote) -> None:
    # On writing, music21 merges tied notes that complete a tuplet into one longer note,
    # unless the duration is marked as set by hand rather than inferred from its length.
    # Reading `tuplets` first makes music21 work out the components that the mark freezes.
    if element.duration.tuplets:
        element.duration.expressionIsInferred = False
