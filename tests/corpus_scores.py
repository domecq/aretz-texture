"""Corpus chorales read once per test session, so that tests can share the parsing."""

from functools import cache

from aretz_texture.core.score import Score
from aretz_texture.ingest.sources import list_corpus_chorales, read_score


@cache
def corpus_score(identifier: str) -> Score:
    """Return the score of a corpus chorale such as "bach/bwv320"."""
    return read_score(identifier).score


def distinct_corpus_chorales() -> tuple[str, ...]:
    """Return the 350 distinct chorale identifiers; the listing names 21 files twice."""
    return tuple(dict.fromkeys(list_corpus_chorales()))
