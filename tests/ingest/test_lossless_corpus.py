# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
"""Lossless count over the corpus: every pitch music21 reads is a pitch of the model."""

import pytest
from music21 import chord, corpus, stream

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.score import Part
from aretz_texture.ingest.music21_conversion import convert_score
from aretz_texture.ingest.sources import list_corpus_chorales


def pitches_read_by_music21(part: stream.Part) -> int:
    return sum(
        len(element.notes) if isinstance(element, chord.Chord) else 1
        for element in part.recurse().notes
    )


def pitches_in_model(part: Part) -> int:
    return sum(len(event.pitches) for voice in part.voices for event in voice.events)


@pytest.mark.slow
def test_every_accepted_chorale_keeps_every_pitch_of_every_part() -> None:
    accepted = 0
    rejected: dict[str, str] = {}

    # The listing names 20 files twice; each distinct file is checked once.
    for identifier in dict.fromkeys(list_corpus_chorales()):
        source = corpus.parse(identifier)
        assert isinstance(source, stream.Score), identifier
        try:
            model = convert_score(source).score
        except UnsupportedScoreError as error:
            rejected[identifier] = str(error)
            continue
        accepted += 1
        counts = [
            (pitches_read_by_music21(part), pitches_in_model(model_part))
            for part, model_part in zip(source.parts, model.parts, strict=True)
        ]
        assert all(read == kept for read, kept in counts), identifier

    assert accepted > 0
    assert all("grace" in reason for reason in rejected.values()), rejected
