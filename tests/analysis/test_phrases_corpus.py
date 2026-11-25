"""Phrases of corpus chorales, facts verified against music21 10.5.2 on November 24, 2026."""

from fractions import Fraction

import pytest
from tests.corpus_scores import corpus_score, distinct_corpus_chorales

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.analysis.metric_grid import tactus_spans
from aretz_texture.analysis.phrases import fermata_clusters, segment_phrases
from aretz_texture.analysis.settings import PhraseSegmentationSettings
from aretz_texture.core.texture import PhraseClosing

DEFAULTS = PhraseSegmentationSettings()
EXPECTED_PHRASE_COUNT = 2143


@pytest.mark.parametrize("identifier", ["bach/bwv248.9-1", "bach/bwv190.7"])
def test_chorales_whose_part_1_has_no_fermata_still_have_several_phrases(identifier: str) -> None:
    score = corpus_score(identifier)

    assert not any(note.fermata for voice in score.parts[0].voices for note in voice.events), (
        "part 1 is expected to carry no fermata"
    )
    assert len(segment_phrases(score, DEFAULTS)) > 1


def test_bwv320_bar_2_is_one_cluster_ending_at_the_dotted_half_of_three_voices() -> None:
    score = corpus_score("bach/bwv320")

    clusters = fermata_clusters(score, DEFAULTS)

    first = clusters[0]
    assert (first.span.onset, first.span.end, first.boundary) == (3, 6, 6)
    assert first.ends == (Fraction(4), Fraction(6))
    assert len(first.streams) == 4
    second = clusters[1]
    assert (second.span.onset, second.boundary, second.ends) == (
        15,
        18,
        (Fraction(17), Fraction(18)),
    )


def test_bwv320_has_no_phrase_of_one_or_two_beats() -> None:
    score = corpus_score("bach/bwv320")

    phrases = segment_phrases(score, DEFAULTS)

    assert [phrase.span.end for phrase in phrases][:3] == [6, 18, 42]
    assert all(len(tactus_spans(score, phrase.span)) > 2 for phrase in phrases)


def test_bwv153_5_pickup_chorale_has_one_cluster_with_boundary_48() -> None:
    score = corpus_score("bach/bwv153.5")

    clusters = [c for c in fermata_clusters(score, DEFAULTS) if c.span.onset <= 45 < c.boundary]

    assert len(clusters) == 1
    assert (clusters[0].span.onset, clusters[0].boundary) == (45, 48)
    assert clusters[0].ends == (Fraction(46), Fraction(48))
    assert len(clusters[0].streams) == 4


@pytest.mark.parametrize(
    ("identifier", "onset", "ends"),
    [
        ("bach/bwv41.6", 111, (Fraction(223, 2), Fraction(112))),
        ("bach/bwv357", 39, (Fraction(79, 2), Fraction(40))),
    ],
)
def test_fermata_ends_half_a_beat_apart_are_one_cluster(
    identifier: str, onset: int, ends: tuple[Fraction, ...]
) -> None:
    clusters = fermata_clusters(corpus_score(identifier), DEFAULTS)

    (cluster,) = [c for c in clusters if c.span.onset == onset]
    assert cluster.ends == ends
    assert cluster.boundary == ends[-1]


@pytest.mark.parametrize(
    ("identifier", "last_fermata_end", "score_end"),
    [
        ("bach/bwv330", 35, 36),
        ("bach/bwv424", 38, 40),
        ("bach/bwv374", 76, 80),
        ("bach/bwv261", 77, 78),
        ("bach/bwv248.42-4", 157, 159),
    ],
)
def test_rests_alone_after_the_last_fermata_join_the_last_phrase(
    identifier: str, last_fermata_end: int, score_end: int
) -> None:
    score = corpus_score(identifier)

    phrases = segment_phrases(score, DEFAULTS)

    assert fermata_clusters(score, DEFAULTS)[-1].boundary == last_fermata_end
    assert score.end() == score_end
    assert phrases[-1].span.end == score_end
    assert phrases[-1].closing is PhraseClosing.FERMATA


def test_bwv248_9_1_ends_with_one_score_end_phrase_of_bars_13_to_15_and_75_attacks() -> None:
    score = corpus_score("bach/bwv248.9-1")

    last = segment_phrases(score, DEFAULTS)[-1]

    assert (last.span.onset, last.span.end) == (50, 61)
    assert (last.first_bar_number, last.last_bar_number) == (13, 15)
    assert last.closing is PhraseClosing.SCORE_END
    assert sum(len(voice_attacks(score, s, last.span)) for s in stream_references(score)) == 75


def test_bwv248_23_2_has_no_fermata_and_is_one_phrase_closing_with_no_fermatas() -> None:
    score = corpus_score("bach/bwv248.23-2")

    phrases = segment_phrases(score, DEFAULTS)

    assert fermata_clusters(score, DEFAULTS) == ()
    assert len(phrases) == 1
    assert phrases[0].closing is PhraseClosing.NO_FERMATAS
    assert (phrases[0].span.onset, phrases[0].span.end) == (0, score.end())


def test_bwv66_6_phrase_bars_follow_the_pickup_numbering() -> None:
    score = corpus_score("bach/bwv66.6")

    first = segment_phrases(score, DEFAULTS)[0]

    assert (first.first_bar_number, first.span.onset) == (0, 0)


@pytest.mark.slow
def test_the_350_chorales_have_2143_phrases_none_of_two_tactus_spans_or_less() -> None:
    phrase_count = 0
    short: list[tuple[str, int]] = []
    closings: dict[PhraseClosing, list[str]] = {}
    for identifier in distinct_corpus_chorales():
        score = corpus_score(identifier)
        for phrase in segment_phrases(score, DEFAULTS):
            phrase_count += 1
            closings.setdefault(phrase.closing, []).append(identifier)
            if len(tactus_spans(score, phrase.span)) <= 2:
                short.append((identifier, phrase.number))

    assert phrase_count == EXPECTED_PHRASE_COUNT
    assert short == []
    assert closings[PhraseClosing.NO_FERMATAS] == ["bach/bwv248.23-2"]
    assert closings[PhraseClosing.SCORE_END] == ["bach/bwv248.9-1"]


@pytest.mark.slow
def test_every_corpus_phrase_has_an_attack() -> None:
    attackless: list[tuple[str, int]] = []
    for identifier in distinct_corpus_chorales():
        score = corpus_score(identifier)
        for phrase in segment_phrases(score, DEFAULTS):
            if not any(voice_attacks(score, s, phrase.span) for s in stream_references(score)):
                attackless.append((identifier, phrase.number))

    assert attackless == []
