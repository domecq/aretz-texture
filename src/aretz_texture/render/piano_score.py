# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Writing a score of four parts as a MusicXML piano score on a grand staff."""

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from music21 import chord, clef, duration, expressions, key, meter, note, pitch, stream, tie
from music21.layout import StaffGroup

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.grand_staff import GrandStaffLayout, Staff
from aretz_texture.core.notation import EventPitch, GraceNote, NotatedVoice, NoteEvent, RestFermata
from aretz_texture.core.score import Bar, KeySignatureChange, Score, TimeSignatureChange
from aretz_texture.render.rests import (
    BarRests,
    insert_rests,
    require_fermata_rests_read_back_exactly,
)

LOWER_VOICE_NUMBER = 2
STAFF_VOICE_NUMBERS = (1, LOWER_VOICE_NUMBER)
STEM_DIRECTIONS = {1: "up", LOWER_VOICE_NUMBER: "down"}
CLEFS = {Staff.UPPER: clef.TrebleClef, Staff.LOWER: clef.BassClef}


def write_piano_score(score: Score, layout: GrandStaffLayout, output_path: Path) -> None:
    """Write a score of four parts as MusicXML for piano, on one grand staff.

    The grand staff carries no staff or instrument names (spec 001, decision 6).

    Args:
        score: The score to write; `piano_layout` must have accepted it.
        layout: Where each part of the score is written.
        output_path: The MusicXML file to write; an existing file is overwritten.

    Raises:
        UnsupportedScoreError: A key signature change falls inside a note of both voices
            of a staff, where MusicXML cannot place it at its onset.
        OSError: The file cannot be written.
    """
    music21_score = stream.Score()
    music21_staves = [_build_staff(score, layout, staff) for staff in Staff]
    for music21_staff in music21_staves:
        music21_score.insert(0, music21_staff)
    music21_score.insert(0, StaffGroup(music21_staves, symbol="brace"))
    music21_score.write("musicxml", fp=output_path)


def _build_staff(score: Score, layout: GrandStaffLayout, staff: Staff) -> stream.PartStaff:
    music21_staff = stream.PartStaff()
    measures = [_build_measure(score, layout, staff, bar) for bar in score.bars]
    for bar, measure in zip(score.bars, measures, strict=True):
        music21_staff.insert(bar.onset, measure)
    measures[0].insert(0, CLEFS[staff]())
    return music21_staff


def _build_measure(
    score: Score, layout: GrandStaffLayout, staff: Staff, bar: Bar
) -> stream.Measure:
    measure = stream.Measure(number=bar.number)
    for change in score.time_signatures:
        if change.onset == bar.onset:
            measure.insert(0, meter.TimeSignature(f"{change.numerator}/{change.denominator}"))
    _set_padding(measure, score, bar)
    # piano_layout guarantees that every part has the key signatures of part 1.
    key_changes = [
        change
        for change in score.parts[0].key_signatures
        if bar.onset <= change.onset < _bar_end(bar)
    ]
    rests = BarRests(
        meter_duration=_time_signature_in_force(score, bar).bar_duration(),
        split_offsets=frozenset(change.onset - bar.onset for change in key_changes) - {Fraction(0)},
    )
    voices: list[stream.Voice] = []
    voices_in_bar: list[NotatedVoice] = []
    for voice_number in STAFF_VOICE_NUMBERS:
        content = _content_of_staff_voice(score, layout, staff, voice_number, bar)
        voice = stream.Voice()
        voice.id = str(voice_number)
        _fill(voice, content, bar, rests, voice_number)
        measure.insert(0, voice)
        voices.append(voice)
        voices_in_bar.append(content)
    require_fermata_rests_read_back_exactly(measure, rests.meter_duration)
    for change in key_changes:
        _insert_key_signature(measure, voices, voices_in_bar, bar, change)
    return measure


def _content_of_staff_voice(
    score: Score, layout: GrandStaffLayout, staff: Staff, voice_number: int, bar: Bar
) -> NotatedVoice:
    for part_number, part in enumerate(score.parts, start=1):
        placement = layout.placement(part_number)
        if placement.staff is staff and placement.voice_number == voice_number:
            return part.voices[0].within(bar.onset, _bar_end(bar))
    return NotatedVoice(events=())


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


def _fill(
    voice: stream.Voice,
    content: NotatedVoice,
    bar: Bar,
    rests: BarRests,
    voice_number: int,
) -> None:
    # A rest is cut where a grace note falls, so that the grace note comes right before a rest.
    grace_offsets = frozenset(grace_note.onset - bar.onset for grace_note in content.grace_notes)
    gap_rests = replace(rests, split_offsets=rests.split_offsets | grace_offsets)
    cursor = Fraction(0)
    for item in sorted([*content.events, *content.rest_fermatas], key=lambda item: item.onset):
        insert_rests(voice, cursor, item.onset - bar.onset, gap_rests)
        cursor = item.end() - bar.onset
    insert_rests(voice, cursor, bar.duration, gap_rests)
    for event in content.events:
        voice.insert(event.onset - bar.onset, _build_note(event, voice_number))
    for rest_fermata in content.rest_fermatas:
        voice.insert(
            rest_fermata.onset - bar.onset, _build_rest_fermata(rest_fermata, voice_number)
        )
    for grace_note in content.grace_notes:
        voice.insert(grace_note.onset - bar.onset, _build_grace_note(grace_note, voice_number))


def _insert_key_signature(
    measure: stream.Measure,
    voices: list[stream.Voice],
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
    for voice, content in zip(voices, voices_in_bar, strict=True):
        held = [*content.events, *content.rest_fermatas]
        if not any(item.onset - bar.onset < offset < item.end() - bar.onset for item in held):
            voice.insert(offset, signature)
            return
    message = f"the key signature change at onset {change.onset} falls inside a note of both voices"
    raise UnsupportedScoreError(message)


def _build_note(event: NoteEvent, voice_number: int) -> note.GeneralNote:
    notes = [_build_pitch(event_pitch, event.duration) for event_pitch in event.pitches]
    element = notes[0] if len(notes) == 1 else chord.Chord(notes)
    if len(notes) > 1:
        element.quarterLength = event.duration
        _keep_duration_as_written(element)
    element.stemDirection = STEM_DIRECTIONS[voice_number]
    if event.fermata:
        element.expressions.append(_build_fermata(voice_number))
    return element


def _build_fermata(voice_number: int) -> expressions.Fermata:
    fermata = expressions.Fermata()
    # music21 makes a fermata inverted unless told otherwise.
    fermata.type = "inverted" if voice_number == LOWER_VOICE_NUMBER else "upright"
    return fermata


def _build_rest_fermata(rest_fermata: RestFermata, voice_number: int) -> note.Rest:
    rest = note.Rest(quarterLength=rest_fermata.duration)
    _keep_duration_as_written(rest)
    rest.expressions.append(_build_fermata(voice_number))
    return rest


def _build_grace_note(grace_note: GraceNote, voice_number: int) -> note.GeneralNote:
    notes = [
        _build_pitch(event_pitch, grace_note.notated_value) for event_pitch in grace_note.pitches
    ]
    element = notes[0] if len(notes) == 1 else chord.Chord(notes)
    symbol = duration.Duration(quarterLength=grace_note.notated_value)
    grace_duration = duration.GraceDuration(type=symbol.type, dots=symbol.dots)
    grace_duration.slash = grace_note.slash
    element.duration = grace_duration
    element.stemDirection = STEM_DIRECTIONS[voice_number]
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
