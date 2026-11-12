"""Criterion 26, properties: comparison is reflexive and detects any single removal."""

from hypothesis import assume, given
from hypothesis import strategies as st
from tests.strategies import scores

from aretz_texture.core.score import Score
from aretz_texture.eval.round_trip import DifferenceKind, RoundTripRoute, compare_scores


@given(score=scores(), route=st.sampled_from(RoundTripRoute))
def test_a_generated_score_compared_with_itself_has_no_differences(
    score: Score, route: RoundTripRoute
) -> None:
    assert compare_scores(score, score, route) == ()


@given(score=scores(), data=st.data())
def test_removing_any_one_event_gives_one_missing_event_at_its_place(
    score: Score, data: st.DataObject
) -> None:
    places = [
        (part_index, voice_index, event_index)
        for part_index, part in enumerate(score.parts)
        for voice_index, voice in enumerate(part.voices)
        for event_index in range(len(voice.events))
    ]
    assume(places)  # a score without any event has nothing to remove
    part_index, voice_index, event_index = data.draw(st.sampled_from(places))
    part = score.parts[part_index]
    removed = part.voices[voice_index].events[event_index]
    kept = tuple(e for i, e in enumerate(part.voices[voice_index].events) if i != event_index)
    voices = list(part.voices)
    voices[voice_index] = part.voices[voice_index].model_copy(update={"events": kept})
    parts = list(score.parts)
    # model_copy skips validation, so a voice left empty does not stop the example.
    parts[part_index] = part.model_copy(update={"voices": tuple(voices)})
    changed = score.model_copy(update={"parts": tuple(parts)})

    differences = compare_scores(score, changed, RoundTripRoute.FULL_SCORE)

    assert [(d.kind, d.part_number, d.voice_number, d.onset) for d in differences] == [
        (DifferenceKind.MISSING_EVENT, part_index + 1, voice_index + 1, removed.onset)
    ]
