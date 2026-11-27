"""Corpus chorales read once per test session, so that tests can share the parsing."""

from functools import cache

from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.score import Score
from aretz_texture.core.texture import TexturalAnalysis
from aretz_texture.ingest.sources import list_distinct_corpus_chorales, read_score


@cache
def corpus_score(identifier: str) -> Score:
    """Return the score of a corpus chorale such as "bach/bwv320"."""
    return read_score(identifier).score


def distinct_corpus_chorales() -> tuple[str, ...]:
    """Return the 350 distinct chorale identifiers; the listing names 21 files twice."""
    return list_distinct_corpus_chorales()


@cache
def corpus_texture(identifier: str) -> TexturalAnalysis:
    """Return the textural analysis of a corpus chorale with the default settings."""
    return analyze_texture(corpus_score(identifier), TexturalAnalysisSettings())
