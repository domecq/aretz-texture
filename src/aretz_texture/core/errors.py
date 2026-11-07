"""Domain exceptions of Aretz Texture."""


class AretzTextureError(Exception):
    """Base of every domain error."""


class UnparseableScoreError(AretzTextureError):
    """The source is missing or is not a MusicXML score."""


class UnsupportedScoreError(AretzTextureError):
    """The source parses but the core model cannot represent it."""
