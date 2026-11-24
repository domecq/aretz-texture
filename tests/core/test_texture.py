from fractions import Fraction
from itertools import product

import pytest
from pydantic import ValidationError
from tests.texture_builders import (
    PHRASE_SPAN,
    decision,
    four_lines,
    leaf_of,
    line_features,
    melody_with_accompaniment,
    node_of,
    root_features,
    stream,
)

from aretz_texture.core.texture import (
    DecisionRule,
    FeatureDecision,
    Phrase,
    PhraseClosing,
    PhraseTexture,
    TexturalAnalysis,
    TexturalConfiguration,
    TexturalFeatures,
    TimeSpan,
)


def satisfies_restrictions(
    planes: bool | None,
    homogeneity: bool | None,
    linearity: bool | None,
    accent_coincidence: bool | None,
    attack_divergence: bool | None,
) -> bool:
    """Restate the five restrictions of Fessel (1996, pp. 84 and 85) as plain logic."""
    if None in (planes, homogeneity, accent_coincidence, attack_divergence):
        return False
    restriction_1 = homogeneity or planes
    restriction_2 = planes or homogeneity
    restriction_3 = accent_coincidence or planes
    restriction_4 = (linearity is None) == bool(planes)
    restriction_5 = not linearity or not attack_divergence
    return bool(
        restriction_1 and restriction_2 and restriction_3 and restriction_4 and restriction_5
    )


def build_features(values: tuple[bool | None, ...]) -> TexturalFeatures:
    return TexturalFeatures(
        planes=decision(values[0]),
        homogeneity=decision(values[1]),
        linearity=decision(values[2]),
        accent_coincidence=decision(values[3]),
        attack_divergence=decision(values[4]),
    )


def one_span(onset: int, end: int) -> TimeSpan:
    return TimeSpan(onset=Fraction(onset), end=Fraction(end))


def phrase_texture(number: int, onset: int, end: int, span_end: int | None = None) -> PhraseTexture:
    span = one_span(onset, end)
    phrase = Phrase(
        number=number,
        span=span,
        first_bar_number=number,
        last_bar_number=number,
        closing=PhraseClosing.FERMATA,
    )
    leaf_span = one_span(onset, end if span_end is None else span_end)
    return PhraseTexture(
        phrase=phrase, configuration=leaf_of(line_features(), stream(1), span=leaf_span)
    )


class TestImmutability:
    @pytest.mark.parametrize(
        ("model", "field", "value"),
        [
            (one_span(0, 1), "end", Fraction(2)),
            (stream(1), "part_number", 2),
            (decision(True), "value", False),
            (line_features(), "planes", decision(True)),
            (four_lines(), "streams", ()),
            (phrase_texture(1, 0, 4).phrase, "number", 2),
            (phrase_texture(1, 0, 4), "phrase", phrase_texture(2, 4, 8).phrase),
            (TexturalAnalysis(phrases=(phrase_texture(1, 0, 4),)), "phrases", ()),
        ],
    )
    def test_assigning_to_a_field_raises_validation_error(
        self, model: object, field: str, value: object
    ) -> None:
        with pytest.raises(ValidationError):
            setattr(model, field, value)


class TestTimeSpan:
    def test_rejects_an_empty_span(self) -> None:
        with pytest.raises(ValidationError):
            one_span(2, 2)

    def test_rejects_an_end_before_the_onset(self) -> None:
        with pytest.raises(ValidationError):
            one_span(3, 2)

    def test_contains_a_span_inside_it(self) -> None:
        assert one_span(0, 8).contains(one_span(2, 4))

    def test_contains_itself(self) -> None:
        assert one_span(0, 8).contains(one_span(0, 8))

    def test_does_not_contain_a_span_ending_later(self) -> None:
        assert not one_span(0, 8).contains(one_span(4, 9))

    def test_does_not_contain_a_span_starting_earlier(self) -> None:
        assert not one_span(2, 8).contains(one_span(1, 4))


class TestStreamReferenceLabel:
    def test_names_the_part_when_it_has_a_name(self) -> None:
        assert stream(1, 1, "Soprano").label() == "Soprano (part 1, voice 1)"

    def test_says_unnamed_when_the_part_has_no_name(self) -> None:
        assert stream(5, 2).label() == "unnamed (part 5, voice 2)"


COMBINATIONS = list(
    product(
        (True, False),
        (True, False),
        (True, False, None),
        (True, False),
        (True, False),
    )
)


class TestFeatureRestrictions:
    def test_there_are_48_combinations(self) -> None:
        assert len(COMBINATIONS) == 48

    @pytest.mark.parametrize("values", COMBINATIONS)
    def test_accepts_exactly_the_combinations_that_satisfy_the_restrictions(
        self, values: tuple[bool | None, ...]
    ) -> None:
        if satisfies_restrictions(*values):
            build_features(values)
        else:
            with pytest.raises(ValidationError):
                build_features(values)

    def test_eleven_combinations_are_valid(self) -> None:
        valid = [values for values in COMBINATIONS if satisfies_restrictions(*values)]
        assert len(valid) == 11

    @pytest.mark.parametrize("position", [0, 1, 3, 4])
    def test_rejects_an_unspecified_value_on_any_feature_but_linearity(self, position: int) -> None:
        values: list[bool | None] = [False, True, True, True, False]
        values[position] = None
        with pytest.raises(ValidationError):
            build_features(tuple(values))

    def test_accepts_unspecified_linearity_at_planes(self) -> None:
        assert root_features().linearity.value is None


class TestConfigurationStructure:
    def test_accepts_example_six(self) -> None:
        assert len(four_lines().children) == 4

    def test_rejects_a_plus_p_node_without_children(self) -> None:
        with pytest.raises(ValidationError):
            TexturalConfiguration(
                span=PHRASE_SPAN, features=root_features(), children=(), streams=()
            )

    def test_rejects_a_plus_p_node_with_one_child(self) -> None:
        with pytest.raises(ValidationError):
            node_of(root_features(), leaf_of(line_features(), stream(1)))

    def test_rejects_a_minus_p_node_with_children(self) -> None:
        child = leaf_of(line_features(), stream(2))
        with pytest.raises(ValidationError):
            TexturalConfiguration(
                span=PHRASE_SPAN, features=line_features(), children=(child,), streams=(stream(1),)
            )

    def test_rejects_a_minus_p_node_without_streams(self) -> None:
        with pytest.raises(ValidationError):
            leaf_of(line_features())

    def test_rejects_a_plus_p_node_with_streams_of_its_own(self) -> None:
        children = (leaf_of(line_features(), stream(1)), leaf_of(line_features(), stream(2)))
        with pytest.raises(ValidationError):
            TexturalConfiguration(
                span=PHRASE_SPAN,
                features=root_features(),
                children=children,
                streams=(stream(3),),
            )

    def test_rejects_a_child_span_ending_after_the_parent(self) -> None:
        late = leaf_of(line_features(), stream(2), span=one_span(4, 9))
        with pytest.raises(ValidationError):
            node_of(root_features(), leaf_of(line_features(), stream(1)), late)

    def test_rejects_a_child_span_starting_before_the_parent(self) -> None:
        parent_span = one_span(2, 8)
        early = leaf_of(line_features(), stream(2), span=one_span(1, 8))
        with pytest.raises(ValidationError):
            node_of(
                root_features(),
                leaf_of(line_features(), stream(1), span=parent_span),
                early,
                span=parent_span,
            )

    def test_accepts_children_spanning_less_than_the_parent(self) -> None:
        inner = one_span(2, 4)
        node = node_of(
            root_features(),
            leaf_of(line_features(), stream(1), span=inner),
            leaf_of(line_features(), stream(2), span=inner),
        )
        assert node.children[0].span == inner

    def test_rejects_the_same_part_and_voice_in_two_leaves(self) -> None:
        with pytest.raises(ValidationError):
            node_of(
                root_features(),
                leaf_of(line_features(), stream(1, 1, "Soprano")),
                leaf_of(line_features(), stream(1, 1, "Soprano")),
            )

    def test_rejects_the_same_part_and_voice_in_two_leaves_of_a_deeper_tree(self) -> None:
        inner = node_of(
            root_features(),
            leaf_of(line_features(), stream(1)),
            leaf_of(line_features(), stream(2)),
        )
        with pytest.raises(ValidationError):
            node_of(root_features(), inner, leaf_of(line_features(), stream(2, 1, "Other name")))

    def test_accepts_two_voices_of_one_part_in_two_leaves(self) -> None:
        node = node_of(
            root_features(),
            leaf_of(line_features(), stream(1, 1)),
            leaf_of(line_features(), stream(1, 2)),
        )
        assert len(node.leaves()) == 2


class TestLeavesAndDensity:
    def test_leaves_are_the_minus_p_nodes_in_order(self) -> None:
        labels = [leaf.streams[0].label() for leaf in four_lines().leaves()]
        assert labels == [
            "Soprano (part 1, voice 1)",
            "Alto (part 2, voice 1)",
            "Tenor (part 3, voice 1)",
            "Bass (part 4, voice 1)",
        ]

    def test_leaves_of_a_leaf_is_the_leaf_itself(self) -> None:
        leaf = leaf_of(line_features(), stream(1))
        assert leaf.leaves() == (leaf,)

    def test_leaves_cross_every_level_of_a_deeper_tree(self) -> None:
        inner = melody_with_accompaniment()
        tree = node_of(
            root_features(),
            inner,
            leaf_of(line_features(), stream(3)),
            span=PHRASE_SPAN,
        )
        assert [leaf.streams[0].part_number for leaf in tree.leaves()] == [1, 2, 3]

    def test_density_is_the_number_of_streams_of_a_leaf(self) -> None:
        leaf = leaf_of(line_features(), stream(4, 1, "Bass"), stream(5, 1, "Continuo"))
        assert leaf.density() == 2

    def test_density_of_a_plus_p_node_is_zero_because_it_has_no_streams_of_its_own(self) -> None:
        assert four_lines().density() == 0


class TestTexturalAnalysis:
    def test_accepts_contiguous_phrases_covering_from_zero(self) -> None:
        analysis = TexturalAnalysis(phrases=(phrase_texture(1, 0, 4), phrase_texture(2, 4, 9)))
        assert analysis.phrases[1].phrase.number == 2

    def test_rejects_phrases_not_numbered_from_one(self) -> None:
        with pytest.raises(ValidationError):
            TexturalAnalysis(phrases=(phrase_texture(2, 0, 4),))

    def test_rejects_phrases_numbered_out_of_order(self) -> None:
        with pytest.raises(ValidationError):
            TexturalAnalysis(phrases=(phrase_texture(1, 0, 4), phrase_texture(3, 4, 8)))

    def test_rejects_phrases_that_are_not_contiguous(self) -> None:
        with pytest.raises(ValidationError):
            TexturalAnalysis(phrases=(phrase_texture(1, 0, 4), phrase_texture(2, 5, 8)))

    def test_rejects_a_first_phrase_not_starting_at_zero(self) -> None:
        with pytest.raises(ValidationError):
            TexturalAnalysis(phrases=(phrase_texture(1, 1, 4),))

    def test_rejects_a_configuration_whose_span_differs_from_its_phrase(self) -> None:
        with pytest.raises(ValidationError):
            TexturalAnalysis(phrases=(phrase_texture(1, 0, 4, span_end=3),))


def test_every_decision_rule_has_a_distinct_value() -> None:
    values = [rule.value for rule in DecisionRule]
    assert len(values) == len(set(values)) == 10


def test_a_decision_carries_value_rule_and_explanation() -> None:
    made = FeatureDecision(value=None, rule=DecisionRule.RESTRICTION_4, explanation="Because.")
    assert (made.value, made.rule, made.explanation) == (
        None,
        DecisionRule.RESTRICTION_4,
        "Because.",
    )
