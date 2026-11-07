"""Criterion 17, property: the grand staff only accepts four parts."""

import pytest
from hypothesis import assume, given
from tests.strategies import scores

from aretz_texture.core.errors import GrandStaffMappingError
from aretz_texture.core.grand_staff import PIANO_PART_COUNT, piano_layout
from aretz_texture.core.score import Score


@given(score=scores())
def test_piano_layout_refuses_any_score_without_four_parts_with_its_part_count(
    score: Score,
) -> None:
    assume(len(score.parts) != PIANO_PART_COUNT)

    with pytest.raises(GrandStaffMappingError) as raised:
        piano_layout(score)

    assert raised.value.part_count == len(score.parts)
