"""Textural evaluation: one line per phrase of the corpus, committed and compared in review.

Spec 002, section 3.9. Any change of the analysis shows as a change of lines in
`tests/eval/expected_textural_configurations.txt`. To regenerate the file after an
intended change, run `uv run python -m aretz_texture.eval.textural_configurations`.
"""

import sys

from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.texture import TexturalAnalysis
from aretz_texture.ingest.sources import list_corpus_chorales, read_score
from aretz_texture.render.textural_schema import closing_label, compact_schema


def phrase_lines(identifier: str, analysis: TexturalAnalysis) -> tuple[str, ...]:
    """Write one line per phrase: its place, its closing and its compact configuration.

    Args:
        identifier: The name of the score, such as `"bach/bwv66.6"`.
        analysis: The textural analysis of that score.

    Returns:
        Lines such as `bach/bwv66.6: phrase 1, bars 0 to 1, closing: fermata: [+P, ...]`.
    """
    return tuple(
        f"{identifier}: phrase {texture.phrase.number}, "
        f"bars {texture.phrase.first_bar_number} to {texture.phrase.last_bar_number}, "
        f"closing: {closing_label(texture.phrase.closing)}: "
        f"{compact_schema(texture.configuration)}"
        for texture in analysis.phrases
    )


def corpus_phrase_lines(settings: TexturalAnalysisSettings) -> tuple[str, ...]:
    """Analyze the distinct chorales of the corpus and write the lines of all their phrases.

    Chorales are taken in the order of `list_corpus_chorales`, keeping the first
    occurrence of each, since the listing names 21 files twice.

    Args:
        settings: The settings of the textural analysis.

    Returns:
        The lines of every phrase of every chorale.
    """
    lines: list[str] = []
    for identifier in dict.fromkeys(list_corpus_chorales()):
        analysis = analyze_texture(read_score(identifier).score, settings)
        lines += phrase_lines(identifier, analysis)
    return tuple(lines)


if __name__ == "__main__":
    sys.stdout.write("\n".join(corpus_phrase_lines(TexturalAnalysisSettings())) + "\n")
