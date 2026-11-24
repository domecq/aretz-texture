from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st
from tests.strategies import scores

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.analysis.doublings import fuse_doublings
from aretz_texture.analysis.settings import DoublingSettings
from aretz_texture.core.score import Score
from aretz_texture.core.texture import TimeSpan

DEFAULTS = DoublingSettings()


def groups_of(score: Score) -> list[set[tuple[int, int]]]:
    return [
        {(s.part_number, s.voice_number) for s in fused.streams}
        for fused in fuse_doublings(score, DEFAULTS)
    ]


@given(scores())
def test_every_notated_voice_is_in_exactly_one_fused_stream(score: Score) -> None:
    members = [key for group in groups_of(score) for key in sorted(group)]

    expected = [(s.part_number, s.voice_number) for s in stream_references(score)]
    assert sorted(members) == expected


@given(st.data())
def test_an_exact_copy_of_a_part_fuses_with_it_and_changes_nothing_else(
    data: st.DataObject,
) -> None:
    score = data.draw(scores())
    copied_number = data.draw(st.integers(min_value=1, max_value=len(score.parts)))
    with_copy = score.model_copy(update={"parts": (*score.parts, score.parts[copied_number - 1])})
    copy_number = len(with_copy.parts)
    whole = TimeSpan(onset=Fraction(0), end=score.end())

    original_groups = groups_of(score)
    groups = groups_of(with_copy)

    copy_keys = {
        (copy_number, voice) for voice in range(1, len(score.parts[copied_number - 1].voices) + 1)
    }
    without_copy = [group - copy_keys for group in groups]
    assert [group for group in without_copy if group] == original_groups
    for stream in stream_references(with_copy):
        if stream.part_number == copy_number and voice_attacks(with_copy, stream, whole):
            original = (copied_number, stream.voice_number)
            assert any(
                original in group and (copy_number, stream.voice_number) in group
                for group in groups
            )
