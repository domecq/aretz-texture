from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st
from tests.strategies import scores

from aretz_texture.analysis.phrases import fermata_clusters, segment_phrases
from aretz_texture.analysis.settings import PhraseSegmentationSettings
from aretz_texture.core.score import Score

DEFAULTS = PhraseSegmentationSettings()


@given(scores())
def test_phrases_tile_the_score_from_0_to_its_end_numbered_from_1(score: Score) -> None:
    phrases = segment_phrases(score, DEFAULTS)

    assert [phrase.number for phrase in phrases] == list(range(1, len(phrases) + 1))
    assert phrases[0].span.onset == 0
    assert phrases[-1].span.end == score.end()
    for previous, following in pairwise(phrases):
        assert following.span.onset == previous.span.end


@given(st.data())
def test_permuting_the_parts_does_not_change_the_phrases(data: st.DataObject) -> None:
    score = data.draw(scores())
    permuted = score.model_copy(update={"parts": tuple(data.draw(st.permutations(score.parts)))})

    assert segment_phrases(permuted, DEFAULTS) == segment_phrases(score, DEFAULTS)


@given(st.data())
def test_permuting_the_parts_does_not_change_where_the_clusters_are(data: st.DataObject) -> None:
    score = data.draw(scores())
    permuted = score.model_copy(update={"parts": tuple(data.draw(st.permutations(score.parts)))})

    def places(candidate: Score) -> list[tuple[object, object, tuple[object, ...]]]:
        return [
            (cluster.span, cluster.boundary, cluster.ends)
            for cluster in fermata_clusters(candidate, DEFAULTS)
        ]

    assert places(permuted) == places(score)
