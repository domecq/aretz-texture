"""Criterion 17: the grand staff layout of the piano command."""

from fractions import Fraction

import pytest

from aretz_texture.core.errors import AretzTextureError, GrandStaffMappingError
from aretz_texture.core.grand_staff import PIANO_LAYOUT, Staff, StaffVoice, piano_layout
from aretz_texture.core.notation import EventPitch, NotatedVoice, NoteEvent, SpelledPitch
from aretz_texture.core.score import (
    Bar,
    KeySignatureChange,
    Part,
    Score,
    TimeSignatureChange,
)


def whole_note_voice() -> NotatedVoice:
    middle_c = SpelledPitch(step="C", alter=0, octave=4)
    event = NoteEvent(
        onset=Fraction(0),
        duration=Fraction(4),
        pitches=(EventPitch(pitch=middle_c, tie=None),),
        fermata=False,
    )
    return NotatedVoice(events=(event,))


def part_with(voice_count: int = 1, sharps: int = 0) -> Part:
    key = KeySignatureChange(onset=Fraction(0), sharps=sharps)
    return Part(
        name=None,
        instrument_name=None,
        key_signatures=(key,),
        voices=(whole_note_voice(),) * voice_count,
    )


def score_with(*parts: Part) -> Score:
    return Score(
        bars=(Bar(number=1, onset=Fraction(0), duration=Fraction(4)),),
        time_signatures=(TimeSignatureChange(onset=Fraction(0), numerator=4, denominator=4),),
        parts=parts,
    )


def test_four_parts_with_one_notated_voice_and_one_key_get_the_piano_layout() -> None:
    score = score_with(*(part_with(sharps=2) for _ in range(4)))

    assert piano_layout(score) == PIANO_LAYOUT


def test_piano_layout_places_parts_one_and_two_on_the_upper_staff_in_score_order() -> None:
    assert PIANO_LAYOUT.placement(1) == StaffVoice(staff=Staff.UPPER, voice_number=1)
    assert PIANO_LAYOUT.placement(2) == StaffVoice(staff=Staff.UPPER, voice_number=2)


def test_piano_layout_places_parts_three_and_four_on_the_lower_staff_in_score_order() -> None:
    assert PIANO_LAYOUT.placement(3) == StaffVoice(staff=Staff.LOWER, voice_number=1)
    assert PIANO_LAYOUT.placement(4) == StaffVoice(staff=Staff.LOWER, voice_number=2)


@pytest.mark.parametrize("part_count", [1, 3, 5, 15])
def test_a_score_without_four_parts_is_refused_with_its_part_count(part_count: int) -> None:
    score = score_with(*(part_with() for _ in range(part_count)))

    with pytest.raises(GrandStaffMappingError) as raised:
        piano_layout(score)

    assert raised.value.part_count == part_count


def test_the_part_count_message_says_a_later_spec_is_needed() -> None:
    score = score_with(*(part_with() for _ in range(15)))

    with pytest.raises(GrandStaffMappingError) as raised:
        piano_layout(score)

    assert str(raised.value) == (
        "aretz-texture piano renders only scores with exactly four parts; this score has 15. "
        "Grand staff rendering of other textures needs the textural analysis of a later spec."
    )


def test_a_part_with_several_notated_voices_is_refused_naming_the_part() -> None:
    score = score_with(part_with(), part_with(voice_count=2), part_with(), part_with())

    with pytest.raises(GrandStaffMappingError, match="part 2") as raised:
        piano_layout(score)

    assert raised.value.part_count == 4


def test_differing_key_signatures_are_refused_naming_the_part() -> None:
    score = score_with(part_with(), part_with(), part_with(), part_with(sharps=3))

    with pytest.raises(GrandStaffMappingError, match="part 4") as raised:
        piano_layout(score)

    assert raised.value.part_count == 4


def test_a_mapping_error_is_a_domain_error() -> None:
    assert issubclass(GrandStaffMappingError, AretzTextureError)
