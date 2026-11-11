# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Writing a score of four parts as a MusicXML piano score on a grand staff."""

from fractions import Fraction
from pathlib import Path

from music21 import chord, clef, expressions, key, meter, note, pitch, stream, tie
from music21.layout import StaffGroup

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.grand_staff import GrandStaffLayout, Staff
from aretz_texture.core.notation import EventPitch, NoteEvent
from aretz_texture.core.score import Bar, KeySignatureChange, Score, TimeSignatureChange
from aretz_texture.render.rests import BarRests, insert_rests

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
    events_by_voice: list[list[NoteEvent]] = []
    for voice_number in STAFF_VOICE_NUMBERS:
        events = _events_of_staff_voice(score, layout, staff, voice_number, bar)
        voice = stream.Voice()
        voice.id = str(voice_number)
        _fill(voice, events, bar, rests, voice_number)
        measure.insert(0, voice)
        voices.append(voice)
        events_by_voice.append(events)
    for change in key_changes:
        _insert_key_signature(measure, voices, events_by_voice, bar, change)
    return measure


def _events_of_staff_voice(
    score: Score, layout: GrandStaffLayout, staff: Staff, voice_number: int, bar: Bar
) -> list[NoteEvent]:
    for part_number, part in enumerate(score.parts, start=1):
        placement = layout.placement(part_number)
        if placement.staff is staff and placement.voice_number == voice_number:
            return [
                event for event in part.voices[0].events if bar.onset <= event.onset < _bar_end(bar)
            ]
    return []


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
    events: list[NoteEvent],
    bar: Bar,
    rests: BarRests,
    voice_number: int,
) -> None:
    cursor = Fraction(0)
    for event in events:
        insert_rests(voice, cursor, event.onset - bar.onset, rests)
        voice.insert(event.onset - bar.onset, _build_note(event, voice_number))
        cursor = event.end() - bar.onset
    insert_rests(voice, cursor, bar.duration, rests)


def _insert_key_signature(
    measure: stream.Measure,
    voices: list[stream.Voice],
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
    for voice, events in zip(voices, events_by_voice, strict=True):
        if not any(event.onset - bar.onset < offset < event.end() - bar.onset for event in events):
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
        fermata = expressions.Fermata()
        # music21 makes a fermata inverted unless told otherwise.
        fermata.type = "inverted" if voice_number == LOWER_VOICE_NUMBER else "upright"
        element.expressions.append(fermata)
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
