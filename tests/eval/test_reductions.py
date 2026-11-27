"""Criterion 16: one line per phrase, and the committed file of the whole corpus."""

from fractions import Fraction
from pathlib import Path

import pytest
from tests.analysis.harmony_scores import line
from tests.core_builders import event, part_of, score_of
from tests.corpus_scores import corpus_score, corpus_texture

from aretz_texture.analysis.harmony import analyze_surface_harmony
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.score import Score
from aretz_texture.eval.reductions import corpus_reduction_lines, reduction_lines
from aretz_texture.ingest.sources import list_distinct_corpus_chorales

EXPECTED_FILE = Path(__file__).parent / "expected_reductions.txt"
PHRASE_COUNT = 2143
NOT_VOICED_COUNT = 17
FIRST_DIFFERENCES_REPORTED = 5
SETTINGS = NonChordToneSettings()


def synthetic_lines(score: Score) -> tuple[str, ...]:
    texture = analyze_texture(score, TexturalAnalysisSettings())
    events = analyze_surface_harmony(score, texture, SETTINGS)
    return reduction_lines("synthetic", score, texture, events)


def phrase_line(score: Score) -> str:
    """Return the line of the only phrase of a synthetic score."""
    return synthetic_lines(score)[0]


def corpus_lines(identifier: str) -> tuple[str, ...]:
    score, texture = corpus_score(identifier), corpus_texture(identifier)
    return reduction_lines(
        identifier, score, texture, analyze_surface_harmony(score, texture, SETTINGS)
    )


def test_a_chord_on_the_beat_is_written_as_bar_dot_tactus_and_its_symbol() -> None:
    score = score_of(
        part_of(line(("G4", 2), ("A4", 2))),
        part_of([event(0, 4, "E4")]),
        part_of([event(0, 4, "C3")]),
        bar_durations=(4,),
    )

    assert phrase_line(score) == "synthetic: phrase 1, bars 1 to 1: 1.1 C | 1.3 Am/C"


def test_a_chord_off_the_beat_adds_the_quarter_lengths_after_the_tactus_onset() -> None:
    score = score_of(
        part_of(line(("G4", Fraction(3, 2)), ("A4", Fraction(5, 2)))),
        part_of([event(0, 4, "E4")]),
        part_of([event(0, 4, "C3")]),
        bar_durations=(4,),
    )

    assert phrase_line(score) == "synthetic: phrase 1, bars 1 to 1: 1.1 C | 1.2+1/2 Am/C"


def test_an_unidentified_sonority_is_written_with_its_pitch_names() -> None:
    score = score_of(
        part_of([event(0, 4, "C4")]), part_of([event(0, 4, "C#4")]), bar_durations=(4,)
    )

    assert phrase_line(score) == "synthetic: phrase 1, bars 1 to 1: 1.1 ?(C,C#)"


def test_bwv66_6_has_one_line_per_phrase_the_first_with_the_pickup_chord_on_tactus_4() -> None:
    lines = corpus_lines("bach/bwv66.6")

    assert len(lines) == 6
    assert lines[0].startswith("bach/bwv66.6: phrase 1, bars 0 to 1: 0.4 A | ")


def test_a_chorale_with_four_planes_in_every_phrase_has_no_not_voiced_line() -> None:
    assert not any("not voiced" in line for line in corpus_lines("bach/bwv66.6"))


def test_a_chorale_with_five_planes_ends_with_a_line_that_names_the_first_such_phrase() -> None:
    lines = corpus_lines("bach/bwv27.6")
    texture = corpus_texture("bach/bwv27.6")
    first = next(
        phrase_texture
        for phrase_texture in texture.phrases
        if len(phrase_texture.configuration.leaves()) != 4
    )
    planes = len(first.configuration.leaves())

    assert (
        lines[-1] == f"bach/bwv27.6: not voiced: phrase {first.phrase.number} has {planes} planes"
    )
    assert len(lines) == len(texture.phrases) + 1


def committed_lines() -> list[str]:
    return EXPECTED_FILE.read_text(encoding="utf-8").splitlines()


@pytest.mark.slow
def test_the_reduction_lines_of_the_corpus_are_the_committed_file() -> None:
    current = corpus_reduction_lines(SETTINGS)
    expected = committed_lines()

    differing = [
        f"committed: {before}\ncurrent:   {after}"
        for before, after in zip(expected, current, strict=False)
        if before != after
    ]
    assert not differing, "\n".join(differing[:FIRST_DIFFERENCES_REPORTED])
    assert len(current) == len(expected)


def test_the_committed_file_has_a_line_per_phrase_and_one_per_chorale_not_voiced() -> None:
    lines = committed_lines()

    assert sum("not voiced" in line for line in lines) == NOT_VOICED_COUNT
    assert len(lines) == PHRASE_COUNT + NOT_VOICED_COUNT


def test_the_committed_file_names_the_350_distinct_chorales_in_the_order_of_the_listing() -> None:
    identifiers = [line.split(": ", maxsplit=1)[0] for line in committed_lines()]

    assert tuple(dict.fromkeys(identifiers)) == list_distinct_corpus_chorales()
