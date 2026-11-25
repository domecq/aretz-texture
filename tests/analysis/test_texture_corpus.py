"""Textural configurations of corpus chorales (music21 10.5.2, November 24, 2026)."""

import re

import pytest
from tests.corpus_scores import corpus_score, corpus_texture, distinct_corpus_chorales

from aretz_texture.core.texture import DecisionRule, PhraseTexture
from aretz_texture.render.textural_schema import compact_schema

EXAMPLE_6 = "[+P, +H, +C, +D [-P, +H, +L, +C, -D]]"
FOUR_PARTS = 4


def phrase_of(identifier: str, number: int) -> PhraseTexture:
    return corpus_texture(identifier).phrases[number - 1]


def divergent_span_count(texture: PhraseTexture) -> int:
    explanation = texture.configuration.features.attack_divergence.explanation
    match = re.match(r"(\d+) of \d+ tactus spans", explanation)
    assert match is not None, explanation
    return int(match.group(1))


def first_divergent_span(texture: PhraseTexture) -> str:
    explanation = texture.configuration.features.attack_divergence.explanation
    match = re.search(r"the first is (bar \d+, tactus \d+)", explanation)
    assert match is not None, explanation
    return match.group(1)


def test_every_phrase_of_bwv66_6_has_four_lines_ordered_from_soprano_to_bass() -> None:
    analysis = corpus_texture("bach/bwv66.6")

    assert len(analysis.phrases) == 6
    for texture in analysis.phrases:
        root = texture.configuration
        assert root.features.planes.value is True
        assert [leaf.streams[0].part_name for leaf in root.children] == [
            "Soprano",
            "Alto",
            "Tenor",
            "Bass",
        ]
        for leaf in root.children:
            assert compact_schema(leaf) == "[-P, +H, +L, +C, -D]"


def test_bwv66_6_phrases_are_plus_d_with_the_divergent_spans_of_the_probe() -> None:
    analysis = corpus_texture("bach/bwv66.6")

    assert [divergent_span_count(texture) for texture in analysis.phrases] == [1, 2, 1, 5, 2, 4]
    assert [first_divergent_span(texture) for texture in analysis.phrases] == [
        "bar 0, tactus 4",
        "bar 2, tactus 1",
        "bar 3, tactus 2",
        "bar 4, tactus 1",
        "bar 7, tactus 1",
        "bar 8, tactus 1",
    ]
    assert {
        texture.configuration.features.attack_divergence.value for texture in analysis.phrases
    } == {True}


def test_the_first_phrase_of_bwv244_54_is_fessels_example_6() -> None:
    texture = phrase_of("bach/bwv244.54", 1)

    assert compact_schema(texture.configuration) == EXAMPLE_6
    assert first_divergent_span(texture) == "bar 0, tactus 4"


@pytest.mark.parametrize(
    ("identifier", "first_span"),
    [
        ("bach/bwv244.15", "bar 1, tactus 3"),
        ("bach/bwv244.44", "bar 1, tactus 3"),
        ("bach/bwv244.62", "bar 0, tactus 4"),
    ],
)
def test_the_other_settings_of_the_passion_melody_are_plus_d_in_their_first_phrase(
    identifier: str, first_span: str
) -> None:
    texture = phrase_of(identifier, 1)

    assert texture.configuration.features.attack_divergence.value is True
    assert first_divergent_span(texture) == first_span


@pytest.mark.parametrize(
    ("identifier", "numbers"),
    [
        ("bach/bwv17.7", [1, 3, 5, 7, 8]),
        ("bach/bwv65.2", [1, 2, 3, 4]),
        ("bach/bwv184.5", [3]),
        ("bach/bwv43.11", [1, 2, 3, 4, 5, 6]),
        ("bach/bwv41.6", [8, 9, 11]),
        ("bach/bwv26.6", [1, 2]),
    ],
)
def test_the_homorhythmic_phrases_of_the_probe_are_minus_d_at_the_root(
    identifier: str, numbers: list[int]
) -> None:
    for number in numbers:
        root = phrase_of(identifier, number).configuration
        assert root.features.attack_divergence.value is False, (identifier, number)


def test_bwv184_5_phrase_3_is_homorhythmic_in_bars_5_to_6() -> None:
    phrase = phrase_of("bach/bwv184.5", 3).phrase

    assert (phrase.first_bar_number, phrase.last_bar_number) == (5, 6)


@pytest.mark.parametrize("identifier", ["bach/bwv8.6", "bach/bwv248.59-6"])
def test_bass_with_continuo_is_one_leaf_of_density_2_and_four_planes(identifier: str) -> None:
    root = phrase_of(identifier, 1).configuration

    assert len(root.children) == 4
    bass = root.children[-1]
    assert [stream.part_number for stream in bass.streams] == [4, 5]
    assert bass.density() == 2


def test_bwv8_6_bass_with_continuo_is_minus_l_because_the_continuo_holds_and_is_plus_d() -> None:
    bass = phrase_of("bach/bwv8.6", 1).configuration.children[-1]

    assert bass.features.linearity.value is False
    assert "bar 6, tactus 1" in bass.features.linearity.explanation
    assert bass.features.attack_divergence.value is True
    assert bass.features.attack_divergence.rule is DecisionRule.ATTACKS_WITHIN_TACTUS


def test_the_trumpet_leaf_of_bwv248_9_1_is_minus_l_only_where_a_seventh_is_divided() -> None:
    linearity = []
    for texture in corpus_texture("bach/bwv248.9-1").phrases:
        leaf = next(
            leaf for leaf in texture.configuration.leaves() if leaf.streams[0].part_number == 1
        )
        linearity.append(leaf.features.linearity.value)

    assert linearity == [True, True, True, True, False]


def test_bwv362_phrase_8_assumes_homogeneity_for_a_time_signature_change() -> None:
    homogeneity = phrase_of("bach/bwv362", 8).configuration.features.homogeneity

    assert homogeneity.value is True
    assert homogeneity.rule is DecisionRule.ASSUMED_OUTSIDE_CONDITIONS
    assert "time signature changes at bar 16" in homogeneity.explanation


@pytest.mark.slow
def test_the_corpus_has_2143_phrases_of_which_78_are_homorhythmic_in_40_chorales() -> None:
    homorhythmic: list[tuple[str, int]] = []
    count = 0
    for identifier in distinct_corpus_chorales():
        for texture in corpus_texture(identifier).phrases:
            count += 1
            root = texture.configuration
            if root.children and root.features.attack_divergence.value is False:
                homorhythmic.append((identifier, texture.phrase.number))

    assert count == 2143
    assert len(homorhythmic) == 78
    assert len({identifier for identifier, _ in homorhythmic}) == 40


@pytest.mark.slow
def test_every_phrase_of_a_four_part_chorale_has_four_planes_of_one_voice() -> None:
    for identifier in distinct_corpus_chorales():
        if len(corpus_score(identifier).parts) != FOUR_PARTS:
            continue
        for texture in corpus_texture(identifier).phrases:
            leaves = texture.configuration.leaves()
            assert len(leaves) == FOUR_PARTS, (identifier, texture.phrase.number)
            assert all(leaf.density() == 1 for leaf in leaves)


@pytest.mark.slow
def test_homogeneity_is_assumed_only_in_bwv362_phrase_8_and_no_key_changes_inside_phrases() -> None:
    assumed = [
        (identifier, texture.phrase.number)
        for identifier in distinct_corpus_chorales()
        for texture in corpus_texture(identifier).phrases
        if texture.configuration.features.homogeneity.rule
        is DecisionRule.ASSUMED_OUTSIDE_CONDITIONS
    ]

    assert assumed == [("bach/bwv362", 8)]


@pytest.mark.slow
def test_15_fused_leaves_are_minus_l_and_every_one_of_them_is_plus_d() -> None:
    minus_l = [
        leaf
        for identifier in distinct_corpus_chorales()
        for texture in corpus_texture(identifier).phrases
        for leaf in texture.configuration.leaves()
        if leaf.density() > 1 and leaf.features.linearity.value is False
    ]

    assert len(minus_l) == 15
    assert all(leaf.features.attack_divergence.value is True for leaf in minus_l)
