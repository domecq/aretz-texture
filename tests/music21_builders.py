# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
"""Small music21 scores built for tests, in 4/4 with whole bars unless said otherwise."""

from collections.abc import Sequence
from pathlib import Path

from music21 import converter, key, meter, note, stream

BAR_LENGTH = 4.0


def whole_note(name: str = "C4") -> note.Note:
    return note.Note(name, quarterLength=BAR_LENGTH)


def bar_of(elements: Sequence[note.GeneralNote], number: int = 1) -> stream.Measure:
    """Return a measure with the elements placed one after another from offset 0."""
    measure = stream.Measure(number=number)
    for element in elements:
        measure.append(element)
    return measure


def voices_bar(voices: Sequence[Sequence[note.GeneralNote]], number: int = 1) -> stream.Measure:
    """Return a measure holding one music21 voice per sequence, with ids "1", "2" and so on."""
    measure = stream.Measure(number=number)
    for voice_number, elements in enumerate(voices, start=1):
        voice = stream.Voice()
        voice.id = str(voice_number)
        for element in elements:
            voice.append(element)
        measure.insert(0, voice)
    return measure


def part_of(
    measures: Sequence[stream.Measure],
    name: str | None = "Part",
    time_signature: str = "4/4",
    sharps: int = 0,
) -> stream.Part:
    """Return a part whose measures follow each other, with the signatures in the first one."""
    part = stream.Part()
    part.partName = name
    for index, measure in enumerate(measures):
        if index == 0:
            measure.insert(0, meter.TimeSignature(time_signature))
            measure.insert(0, key.KeySignature(sharps))
        part.append(measure)
    return part


def score_of(*parts: stream.Part) -> stream.Score:
    score = stream.Score()
    for part in parts:
        score.insert(0, part)
    return score


def parse_score(path: Path) -> stream.Score:
    """Parse a MusicXML file written by the tool and check that music21 gives a score."""
    parsed = converter.parse(path)
    assert isinstance(parsed, stream.Score)
    return parsed
