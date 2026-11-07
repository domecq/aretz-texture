# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
from pathlib import Path

import pytest
from music21 import expressions, instrument, meter, note, pitch, stream, tie
from tests.music21_builders import (
    bar_of,
    part_of,
    score_of,
    voices_bar,
    whole_note,
)

from aretz_texture.core.errors import UnparseableScoreError, UnsupportedScoreError
from aretz_texture.ingest.music21_conversion import convert_score
from aretz_texture.ingest.sources import read_score


def test_microtonal_accidental_is_unsupported() -> None:
    quarter_tone = whole_note("C4")
    quarter_tone.pitch.accidental = pitch.Accidental("half-sharp")
    source = score_of(part_of([bar_of([quarter_tone])]))

    with pytest.raises(UnsupportedScoreError, match="microtonal"):
        convert_score(source)


def test_unpitched_note_is_unsupported() -> None:
    unpitched = note.Unpitched(quarterLength=4.0)
    source = score_of(part_of([bar_of([unpitched])]))

    with pytest.raises(UnsupportedScoreError, match="unpitched"):
        convert_score(source)


@pytest.mark.parametrize("tie_type", ["let-ring", "continue-let-ring"])
def test_let_ring_tie_is_unsupported(tie_type: str) -> None:
    tied = whole_note()
    tied.tie = tie.Tie(tie_type)
    source = score_of(part_of([bar_of([tied])]))

    with pytest.raises(UnsupportedScoreError, match="tie"):
        convert_score(source)


def test_parts_with_bars_that_do_not_line_up_are_unsupported() -> None:
    first = part_of([bar_of([whole_note()], 1), bar_of([whole_note()], 2)])
    second = part_of([bar_of([whole_note()], 1)])

    with pytest.raises(UnsupportedScoreError, match="part 2"):
        convert_score(score_of(first, second))


def test_parts_with_different_time_signatures_are_unsupported() -> None:
    first = part_of([bar_of([whole_note()])])
    second = part_of([bar_of([whole_note()])], time_signature="2/4")

    with pytest.raises(UnsupportedScoreError, match="time signatures of part 2"):
        convert_score(score_of(first, second))


def test_time_signature_change_inside_a_bar_is_unsupported() -> None:
    second_bar = bar_of([whole_note()], 2)
    second_bar.insert(2.0, meter.TimeSignature("3/4"))
    part = part_of([bar_of([whole_note()], 1), second_bar])

    with pytest.raises(UnsupportedScoreError, match="bar line"):
        convert_score(score_of(part))


def test_score_without_a_time_signature_is_unsupported() -> None:
    part = stream.Part()
    part.append(bar_of([whole_note()]))

    with pytest.raises(UnsupportedScoreError, match="time signature"):
        convert_score(score_of(part))


def test_note_outside_the_voices_of_a_bar_with_voices_is_unsupported() -> None:
    measure = voices_bar([[whole_note("E4")]])
    measure.insert(0, whole_note("C4"))

    with pytest.raises(UnsupportedScoreError, match="outside its voices"):
        convert_score(score_of(part_of([measure])))


def test_transposing_part_is_unsupported() -> None:
    part = part_of([bar_of([whole_note()])])
    part.insert(0, instrument.Clarinet())

    with pytest.raises(UnsupportedScoreError, match="transposing"):
        convert_score(score_of(part))


def test_grace_note_is_unsupported_until_spec_001d() -> None:
    grace = note.Note("D4").getGrace()
    assert grace is not None
    measure = bar_of([grace, whole_note()])

    with pytest.raises(UnsupportedScoreError, match="grace"):
        convert_score(score_of(part_of([measure])))


def test_fermata_on_a_rest_is_unsupported_until_spec_001d() -> None:
    rest = note.Rest(quarterLength=4.0)
    rest.expressions.append(expressions.Fermata())

    with pytest.raises(UnsupportedScoreError, match="fermata"):
        convert_score(score_of(part_of([bar_of([rest])])))


def test_overlapping_notes_in_a_bar_without_voices_are_unsupported() -> None:
    measure = stream.Measure(number=1)
    measure.insert(0, note.Note("C4", quarterLength=4.0))
    measure.insert(1.0, note.Note("E4", quarterLength=1.0))

    with pytest.raises(UnsupportedScoreError, match="structural rule"):
        convert_score(score_of(part_of([measure])))


def test_score_without_parts_is_unsupported() -> None:
    with pytest.raises(UnsupportedScoreError, match="no parts"):
        convert_score(stream.Score())


def test_missing_file_is_unparseable(tmp_path: Path) -> None:
    with pytest.raises(UnparseableScoreError):
        read_score(str(tmp_path / "missing.musicxml"))


def test_unknown_corpus_identifier_is_unparseable() -> None:
    with pytest.raises(UnparseableScoreError) as raised:
        read_score("bwv0.0")

    assert raised.value.__cause__ is not None


def test_file_that_is_not_musicxml_is_unparseable(tmp_path: Path) -> None:
    path = tmp_path / "notes.musicxml"
    path.write_text("this is not a score")

    with pytest.raises(UnparseableScoreError):
        read_score(str(path))
