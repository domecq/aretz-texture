"""The grand staff of the piano command: where each part of a score is written."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from aretz_texture.core.errors import GrandStaffMappingError
from aretz_texture.core.score import Score

PIANO_PART_COUNT = 4


class Staff(StrEnum):
    """One of the two staves of the grand staff."""

    UPPER = "upper"  # right hand, treble clef
    LOWER = "lower"  # left hand, bass clef


class StaffVoice(BaseModel):
    """A voice on one staff of the grand staff."""

    model_config = ConfigDict(frozen=True)

    staff: Staff
    voice_number: int  # 1 is the upper voice of the staff, stems up; 2 the lower


class GrandStaffLayout(BaseModel):
    """The placement of the parts of a score on a grand staff."""

    model_config = ConfigDict(frozen=True)

    placements: tuple[StaffVoice, ...]  # placement of parts 1 to 4 in score order

    def placement(self, part_number: int) -> StaffVoice:
        """Return where a part is written.

        Args:
            part_number: The position of the part in the score, starting at 1.

        Returns:
            The staff and voice of the part.
        """
        return self.placements[part_number - 1]


PIANO_LAYOUT = GrandStaffLayout(
    placements=(
        StaffVoice(staff=Staff.UPPER, voice_number=1),
        StaffVoice(staff=Staff.UPPER, voice_number=2),
        StaffVoice(staff=Staff.LOWER, voice_number=1),
        StaffVoice(staff=Staff.LOWER, voice_number=2),
    )
)


def piano_layout(score: Score) -> GrandStaffLayout:
    """Return the layout that writes a score of four parts as piano music.

    Parts 1 and 2 go to the right hand and parts 3 and 4 to the left hand, in score
    order, because this slice places parts without analysing them (spec 001, decision 6).

    Args:
        score: The score to place.

    Returns:
        `PIANO_LAYOUT`.

    Raises:
        GrandStaffMappingError: The score does not have exactly four parts, or a part has
            several notated voices, or the key signatures of the parts differ.
    """
    part_count = len(score.parts)
    if part_count != PIANO_PART_COUNT:
        message = (
            f"aretz-texture piano renders only scores with exactly four parts; this score "
            f"has {part_count}. Grand staff rendering of other textures needs the textural "
            f"analysis of a later spec."
        )
        raise GrandStaffMappingError(message, part_count)
    for part_number, part in enumerate(score.parts, start=1):
        if len(part.voices) > 1:
            message = (
                f"part {part_number} has {len(part.voices)} notated voices; the grand staff "
                f"places one notated voice per part"
            )
            raise GrandStaffMappingError(message, part_count)
        if part.key_signatures != score.parts[0].key_signatures:
            message = f"part {part_number} has key signatures that differ from those of part 1"
            raise GrandStaffMappingError(message, part_count)
    return PIANO_LAYOUT
