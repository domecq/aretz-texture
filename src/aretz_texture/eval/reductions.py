"""Evaluation of the reduction: one line per phrase of the corpus, committed and compared in review.

Spec 003, section 3.10. Any change of the segmentation or of the chord naming shows as a change
of lines in `tests/eval/expected_reductions.txt`. To regenerate the file after an intended
change, run `uv run python -m aretz_texture.eval.reductions`.
"""

import sys

from aretz_texture.analysis.harmony import analyze_surface_harmony
from aretz_texture.analysis.metric_grid import tactus_position
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.harmony import ChordIdentity, HarmonicEvent
from aretz_texture.core.score import Score
from aretz_texture.core.texture import PhraseTexture, TexturalAnalysis
from aretz_texture.ingest.sources import list_distinct_corpus_chorales, read_score

# Planes a phrase needs for the reduction to voice it, one per voice (spec 003, section 3.7).
VOICED_PLANE_COUNT = 4


def reduction_lines(
    identifier: str,
    score: Score,
    texture: TexturalAnalysis,
    events: tuple[HarmonicEvent, ...],
) -> tuple[str, ...]:
    """Write one line per phrase with its chords, and one line if the score cannot be voiced.

    A phrase line is `identifier: phrase N, bars A to B: POSITION SYMBOL | ...`. `POSITION` is
    `B.T`, the bar and tactus number of `tactus_label`, followed by `+F` when the chord starts
    F quarter lengths after the tactus onset. An unidentified sonority prints `?(` and its
    pitch names separated by commas, `)` where the symbol would be. A score with a phrase
    that does not have exactly four planes ends with `identifier: not voiced: phrase N has P
    planes`, naming the first such phrase.

    Args:
        identifier: The name of the score, such as `"bach/bwv66.6"`.
        score: The score, which gives the metric grid.
        texture: Its textural analysis, which gives the phrases and their planes.
        events: Its surface events, in order.

    Returns:
        The phrase lines in order, then the not voiced line if there is one.
    """
    lines = [
        _phrase_line(identifier, score, phrase_texture, events)
        for phrase_texture in texture.phrases
    ]
    return (*lines, *_not_voiced_lines(identifier, texture))


def corpus_reduction_lines(settings: NonChordToneSettings) -> tuple[str, ...]:
    """Analyze the distinct chorales of the corpus and write the lines of all their phrases.

    Chorales are taken in the order of `list_distinct_corpus_chorales`. Every chorale is
    segmented and named, whether or not the reduction can voice it.

    Args:
        settings: The settings of the non chord tone rules.

    Returns:
        The lines of every chorale, as `reduction_lines` writes them.
    """
    lines: list[str] = []
    for identifier in list_distinct_corpus_chorales():
        score = read_score(identifier).score
        texture = analyze_texture(score, TexturalAnalysisSettings())
        events = analyze_surface_harmony(score, texture, settings)
        lines += reduction_lines(identifier, score, texture, events)
    return tuple(lines)


def _phrase_line(
    identifier: str, score: Score, phrase_texture: PhraseTexture, events: tuple[HarmonicEvent, ...]
) -> str:
    phrase = phrase_texture.phrase
    chords = " | ".join(
        _chord_text(score, event)
        for event in events
        if event.windows[0].phrase_number == phrase.number
    )
    return (
        f"{identifier}: phrase {phrase.number}, "
        f"bars {phrase.first_bar_number} to {phrase.last_bar_number}: {chords}"
    )


def _chord_text(score: Score, event: HarmonicEvent) -> str:
    bar, tactus, offset = tactus_position(score, event.span.onset)
    position = f"{bar}.{tactus}" + (f"+{offset}" if offset else "")
    if isinstance(event.reading, ChordIdentity):
        return f"{position} {event.reading.symbol()}"
    names = ",".join(name.text() for name in event.reading.pitch_names)
    return f"{position} ?({names})"


def _not_voiced_lines(identifier: str, texture: TexturalAnalysis) -> tuple[str, ...]:
    for phrase_texture in texture.phrases:
        plane_count = len(phrase_texture.configuration.leaves())
        if plane_count != VOICED_PLANE_COUNT:
            number = phrase_texture.phrase.number
            return (f"{identifier}: not voiced: phrase {number} has {plane_count} planes",)
    return ()


if __name__ == "__main__":
    sys.stdout.write("\n".join(corpus_reduction_lines(NonChordToneSettings())) + "\n")
