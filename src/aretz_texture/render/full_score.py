# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Writing the core model as a MusicXML full score, one staff per part."""

from fractions import Fraction
from pathlib import Path

from music21 import clef, instrument, meter, note, pitch, stream

from aretz_texture.core.notation import NoteEvent
from aretz_texture.core.score import Bar, Part, Score


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
    events = [
        event
        for event in part.voices[0].events
        if bar.onset <= event.onset < bar.onset + bar.duration
    ]
    cursor = bar.onset
    for event in events:
        _insert_rest(measure, cursor - bar.onset, event.onset - cursor)
        measure.insert(event.onset - bar.onset, _build_note(event))
        cursor = event.end()
    _insert_rest(measure, cursor - bar.onset, bar.onset + bar.duration - cursor)
    return measure


def _insert_rest(
    container: stream.Measure | stream.Voice, offset: Fraction, length: Fraction
) -> None:
    if length > 0:
        container.insert(offset, note.Rest(quarterLength=length))


def _build_note(event: NoteEvent) -> note.Note:
    spelled = event.pitches[0].pitch
    music21_pitch = pitch.Pitch()
    music21_pitch.step = spelled.step
    music21_pitch.octave = spelled.octave
    if spelled.alter != 0:
        music21_pitch.accidental = pitch.Accidental(spelled.alter)
    return note.Note(music21_pitch, quarterLength=event.duration)
