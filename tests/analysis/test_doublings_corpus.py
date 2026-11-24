"""Fused streams of corpus chorales, facts verified against music21 10.5.2 on November 24, 2026."""

from fractions import Fraction

import pytest
from tests.corpus_scores import corpus_score, distinct_corpus_chorales

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.analysis.doublings import coinciding_attack_proportion, fuse_doublings
from aretz_texture.analysis.settings import DoublingSettings
from aretz_texture.core.score import Score
from aretz_texture.core.texture import TimeSpan

DEFAULTS = DoublingSettings()
FOUR_PARTS = 4

# Chorale: (parts, fused streams) for the 19 chorales with more than four parts.
PARTS_AND_FUSED_STREAMS = {
    "bach/bwv41.6": (9, 9),
    "bach/bwv8.6": (5, 4),
    "bach/bwv248.9-1": (8, 7),
    "bach/bwv91.6": (7, 7),
    "bach/bwv29.8": (8, 8),
    "bach/bwv27.6": (5, 5),
    "bach/bwv161.6": (5, 5),
    "bach/bwv19.7": (8, 8),
    "bach/bwv112.5": (7, 6),
    "bach/bwv172.6": (5, 5),
    "bach/bwv190.7": (15, 10),
    "bach/bwv251": (6, 5),
    "bach/bwv252": (6, 5),
    "bach/bwv136.6": (5, 5),
    "bach/bwv248.23-2": (8, 8),
    "bach/bwv250": (6, 6),
    "bach/bwv70.11": (7, 7),
    "bach/bwv248.59-6": (5, 4),
    "bach/bwv248.42-4": (12, 9),
}


def part_groups(score: Score) -> list[set[int]]:
    """Return the part numbers of each fused stream, in order."""
    return [
        {stream.part_number for stream in fused.streams}
        for fused in fuse_doublings(score, DEFAULTS)
    ]


def proportion_between(score: Score, first: tuple[int, int], second: tuple[int, int]) -> Fraction:
    whole = TimeSpan(onset=Fraction(0), end=score.end())
    attacks = {
        (stream.part_number, stream.voice_number): voice_attacks(score, stream, whole)
        for stream in stream_references(score)
    }
    return coinciding_attack_proportion(attacks[first], attacks[second])


@pytest.mark.parametrize("identifier", ["bach/bwv8.6", "bach/bwv248.59-6"])
def test_bass_and_continuo_fuse_and_the_other_voices_stay_alone(identifier: str) -> None:
    score = corpus_score(identifier)

    fused = fuse_doublings(score, DEFAULTS)

    assert [part.name for part in score.parts] == ["Soprano", "Alto", "Tenor", "Bass", "Continuo"]
    assert len(fused) == 4
    assert part_groups(score) == [{1}, {2}, {3}, {4, 5}]


def test_bwv190_7_has_10_fused_streams_from_15_parts() -> None:
    score = corpus_score("bach/bwv190.7")

    groups = part_groups(score)

    assert len(groups) == 10
    # Oboe 1, Violin 1 and Soprano; Violin 2 and Alto; Viola and Tenor; Bass and Continuo.
    assert [group for group in groups if len(group) > 1] == [
        {5, 8, 11},
        {9, 12},
        {10, 13},
        {14, 15},
    ]
    assert [group for group in groups if len(group) == 1] == [{n} for n in (1, 2, 3, 4, 6, 7)]


def test_bwv27_6_has_five_fused_streams_one_per_part() -> None:
    assert part_groups(corpus_score("bach/bwv27.6")) == [{1}, {2}, {3}, {4}, {5}]


@pytest.mark.parametrize(
    ("identifier", "first", "second", "proportion"),
    [
        ("bach/bwv91.6", (1, 1), (4, 1), Fraction(36, 43)),
        ("bach/bwv250", (1, 1), (3, 1), Fraction(13, 15)),
        ("bach/bwv112.5", (3, 1), (5, 1), Fraction(22, 27)),
        ("bach/bwv248.42-4", (7, 1), (10, 1), Fraction(61, 71)),
        ("bach/bwv248.42-4", (11, 1), (12, 1), Fraction(77, 86)),
        ("bach/bwv248.23-2", (7, 1), (8, 1), Fraction(38, 49)),
    ],
)
def test_near_misses_between_two_voices_stay_below_9_over_10(
    identifier: str,
    first: tuple[int, int],
    second: tuple[int, int],
    proportion: Fraction,
) -> None:
    # Pairwise only: in BWV 248.23 2 the Bass and the Organ still join one fused stream,
    # through the four attacks of the second notated voice of the Oboe da caccia, which
    # coincide with both (fusion is transitive, spec 002, section 3.5).
    score = corpus_score(identifier)

    assert proportion_between(score, first, second) == proportion
    assert proportion < DEFAULTS.minimum_coinciding_attack_proportion


@pytest.mark.slow
def test_no_four_part_chorale_fuses_two_voices() -> None:
    fusing = [
        identifier
        for identifier in distinct_corpus_chorales()
        if len(corpus_score(identifier).parts) == FOUR_PARTS
        and len(fuse_doublings(corpus_score(identifier), DEFAULTS))
        != len(stream_references(corpus_score(identifier)))
    ]

    assert fusing == []


@pytest.mark.slow
def test_the_chorales_with_more_than_four_parts_have_the_verified_numbers_of_fused_streams() -> (
    None
):
    found = {
        identifier: (
            len(corpus_score(identifier).parts),
            len(fuse_doublings(corpus_score(identifier), DEFAULTS)),
        )
        for identifier in distinct_corpus_chorales()
        if len(corpus_score(identifier).parts) > FOUR_PARTS
    }

    assert found == PARTS_AND_FUSED_STREAMS
