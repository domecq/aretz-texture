"""Domain exceptions of Aretz Texture."""


class AretzTextureError(Exception):
    """Base of every domain error."""


class UnparseableScoreError(AretzTextureError):
    """The source is missing or is not a MusicXML score."""


class UnsupportedScoreError(AretzTextureError):
    """The source parses but the core model cannot represent it."""


class GrandStaffMappingError(AretzTextureError):
    """The score is valid but cannot be placed on the grand staff of this slice."""

    def __init__(self, message: str, part_count: int) -> None:
        """Create the error.

        Args:
            message: What stops the grand staff from placing the score.
            part_count: The number of parts of the score that could not be placed.
        """
        super().__init__(message)
        self.part_count = part_count
