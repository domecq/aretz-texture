"""Criteria 28 to 31: one line per phrase, and the committed file of the whole corpus."""

from pathlib import Path

import pytest
from tests.corpus_scores import corpus_texture

from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.eval.textural_configurations import corpus_phrase_lines, phrase_lines
from aretz_texture.render.textural_schema import compact_schema

EXPECTED_FILE = Path(__file__).parent / "expected_textural_configurations.txt"
EXAMPLE_6 = "[+P, +H, +C, +D [-P, +H, +L, +C, -D]]"
PHRASE_COUNT = 2143
ROOT_WITHOUT_DIVERGENCE_COUNT = 78
FIRST_DIFFERENCES_REPORTED = 5


def test_phrase_lines_of_bwv66_6_give_six_lines_the_first_with_the_example_6_form() -> None:
    analysis = corpus_texture("bach/bwv66.6")

    lines = phrase_lines("bach/bwv66.6", analysis)

    assert len(lines) == 6
    assert lines[0] == f"bach/bwv66.6: phrase 1, bars 0 to 1, closing: fermata: {EXAMPLE_6}"


def test_every_phrase_line_ends_with_the_compact_form_of_its_configuration() -> None:
    analysis = corpus_texture("bach/bwv66.6")

    lines = phrase_lines("bach/bwv66.6", analysis)

    for line, texture in zip(lines, analysis.phrases, strict=True):
        assert line.endswith(f": {compact_schema(texture.configuration)}")


def test_phrase_lines_of_a_score_without_fermatas_say_so() -> None:
    analysis = corpus_texture("bach/bwv248.23-2")

    lines = phrase_lines("bach/bwv248.23-2", analysis)

    assert len(lines) == 1
    assert "closing: no fermatas: " in lines[0]


def committed_lines() -> list[str]:
    return EXPECTED_FILE.read_text(encoding="utf-8").splitlines()


@pytest.mark.slow
def test_the_phrase_lines_of_the_corpus_are_the_committed_file() -> None:
    current = corpus_phrase_lines(TexturalAnalysisSettings())
    expected = committed_lines()

    differing = [
        f"committed: {before}\ncurrent:   {after}"
        for before, after in zip(expected, current, strict=False)
        if before != after
    ]
    assert not differing, "\n".join(differing[:FIRST_DIFFERENCES_REPORTED])
    assert len(current) == len(expected)


def test_the_committed_file_has_one_line_per_phrase() -> None:
    assert len(committed_lines()) == PHRASE_COUNT


def test_the_committed_file_has_78_phrases_with_a_root_without_attack_divergence() -> None:
    roots = [line.rsplit(": ", maxsplit=1)[1] for line in committed_lines()]

    assert sum(", -D" in root.split(" [")[0] for root in roots) == ROOT_WITHOUT_DIVERGENCE_COUNT


def test_the_committed_line_of_bwv244_54_phrase_1_is_example_6() -> None:
    line = next(line for line in committed_lines() if line.startswith("bach/bwv244.54: phrase 1, "))

    assert line.endswith(f": {EXAMPLE_6}")
