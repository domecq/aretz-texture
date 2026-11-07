# pyright: reportUnknownMemberType=false
# See ADR 0003: music21 is untyped; this module is the boundary.
"""Sources of scores: MusicXML files and the music21 corpus."""

from pathlib import Path

from music21 import converter, corpus, stream

from aretz_texture.core.errors import UnparseableScoreError
from aretz_texture.core.score import IngestedScore
from aretz_texture.ingest.music21_conversion import convert_score


def read_score(source: str) -> IngestedScore:
    """Read a score from a MusicXML file path or a music21 corpus identifier.

    Args:
        source: The path of an existing MusicXML file, or a corpus identifier such as
            `"bwv66.6"` or `"bach/bwv66.6"`.

    Returns:
        The score with every part of the source.

    Raises:
        UnparseableScoreError: The source is missing, is not MusicXML or is not a score.
        UnsupportedScoreError: The score parses but the core model cannot represent it.
    """
    parsed = _parse(source)
    if not isinstance(parsed, stream.Score):
        message = f"{source!r} is not a score"
        raise UnparseableScoreError(message)
    return convert_score(parsed)


def _parse(source: str) -> object:
    path = Path(source)
    try:
        if path.is_file():
            return converter.parse(path)
        return corpus.parse(source)
    except Exception as error:
        message = f"cannot read {source!r}: {error}"
        raise UnparseableScoreError(message) from error


def list_corpus_chorales() -> tuple[str, ...]:
    """List the identifiers of the Bach chorales of the music21 corpus, in a stable order.

    The Riemenschneider numbering lists 20 files twice, so the 371 identifiers hold 351
    distinct ones; each one is returned as the corpus lists it.
    """
    return tuple(str(name) for name in corpus.chorales.Iterator(returnType="filename"))
