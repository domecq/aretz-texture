from fractions import Fraction

from tests.texture_builders import (
    accompaniment_features,
    chord_features,
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
from aretz_texture.render.textural_schema import compact_schema, format_textural_schema

EXAMPLE_SIX = "[+P, +H, +C, +D [-P, +H, +L, +C, -D]]"


def two_level_tree() -> TexturalConfiguration:
    """A root over a line, a fused bass of two streams and an unnamed part."""
    return node_of(
        root_features(),
        leaf_of(line_features(), stream(1, 1, "Soprano")),
        leaf_of(chord_features(), stream(4, 1, "Bass"), stream(5, 1, "Continuo")),
        leaf_of(accompaniment_features(), stream(6, 1)),
    )


def three_level_tree() -> TexturalConfiguration:
    inner = node_of(
        root_features(),
        leaf_of(line_features(), stream(2, 1, "Violin 1")),
        leaf_of(line_features(), stream(3, 1, "Violin 2")),
    )
    return node_of(root_features(), leaf_of(chord_features(), stream(1, 1, "Bass")), inner)


def phrase_texture(
    number: int, closing: PhraseClosing, tree: TexturalConfiguration
) -> PhraseTexture:
    span = tree.span
    phrase = Phrase(
        number=number,
        span=span,
        first_bar_number=number,
        last_bar_number=number + 1,
        closing=closing,
    )
    return PhraseTexture(phrase=phrase, configuration=tree)


class TestCompactSchema:
    def test_four_identical_lines_are_example_six(self) -> None:
        assert compact_schema(four_lines()) == EXAMPLE_SIX

    def test_melody_with_accompaniment_prints_both_distinct_planes(self) -> None:
        assert compact_schema(melody_with_accompaniment()) == (
            "[+P, +H, +C, +D [-P, +H, +L, +C, -D] [-P, +H, -L, +C, +D]]"
        )

    def test_a_single_leaf_block_of_chords_is_its_feature_list(self) -> None:
        leaf = leaf_of(chord_features(), stream(1))
        assert compact_schema(leaf) == "[-P, +H, -L, +C, -D]"

    def test_identical_siblings_print_once_in_order_of_first_appearance(self) -> None:
        tree = node_of(
            root_features(),
            leaf_of(chord_features(), stream(1)),
            leaf_of(line_features(), stream(2)),
            leaf_of(chord_features(), stream(3)),
            leaf_of(line_features(), stream(4)),
        )
        assert compact_schema(tree) == (
            "[+P, +H, +C, +D [-P, +H, -L, +C, -D] [-P, +H, +L, +C, -D]]"
        )

    def test_a_deeper_tree_nests_its_compact_forms(self) -> None:
        assert compact_schema(three_level_tree()) == (
            "[+P, +H, +C, +D [-P, +H, -L, +C, -D] [+P, +H, +C, +D [-P, +H, +L, +C, -D]]]"
        )

    def test_a_negative_planes_feature_list_omits_nothing_else(self) -> None:
        features = TexturalFeatures(
            planes=_decision(True),
            homogeneity=_decision(False),
            linearity=_decision(None),
            accent_coincidence=_decision(False),
            attack_divergence=_decision(False),
        )
        tree = node_of(
            features, leaf_of(line_features(), stream(1)), leaf_of(chord_features(), stream(2))
        )
        assert compact_schema(tree).startswith("[+P, -H, -C, -D ")


def _decision(value: bool | None) -> FeatureDecision:
    return FeatureDecision(value=value, rule=DecisionRule.PLANE_COUNT, explanation="x")


class TestIndentedForm:
    def test_two_level_tree_with_a_fused_leaf_and_an_unnamed_part(self) -> None:
        text = format_textural_schema(
            TexturalAnalysis(phrases=(phrase_texture(1, PhraseClosing.FERMATA, two_level_tree()),))
        )
        assert text == (
            "Phrase 1, bars 1 to 2, closing: fermata\n"
            "[+P, +H, +C, +D\n"
            "    [-P, +H, +L, +C, -D]  Soprano (part 1, voice 1)\n"
            "    [-P, +H, -L, +C, -D]  Bass (part 4, voice 1); Continuo (part 5, voice 1)\n"
            "    [-P, +H, -L, +C, +D]  unnamed (part 6, voice 1)\n"
            "]\n"
            "Compact: [+P, +H, +C, +D [-P, +H, +L, +C, -D] [-P, +H, -L, +C, -D]"
            " [-P, +H, -L, +C, +D]]"
        )

    def test_a_deeper_tree_indents_each_level_four_spaces_deeper(self) -> None:
        text = format_textural_schema(
            TexturalAnalysis(
                phrases=(phrase_texture(1, PhraseClosing.FERMATA, three_level_tree()),)
            )
        )
        assert text.splitlines()[1:-1] == [
            "[+P, +H, +C, +D",
            "    [-P, +H, -L, +C, -D]  Bass (part 1, voice 1)",
            "    [+P, +H, +C, +D",
            "        [-P, +H, +L, +C, -D]  Violin 1 (part 2, voice 1)",
            "        [-P, +H, +L, +C, -D]  Violin 2 (part 3, voice 1)",
            "    ]",
            "]",
        ]

    def test_a_phrase_of_a_single_leaf_is_one_line(self) -> None:
        tree = leaf_of(chord_features(), stream(1, 1, "Piano"))
        text = format_textural_schema(
            TexturalAnalysis(phrases=(phrase_texture(1, PhraseClosing.NO_FERMATAS, tree),))
        )
        assert text.splitlines() == [
            "Phrase 1, bars 1 to 2, closing: no fermatas",
            "[-P, +H, -L, +C, -D]  Piano (part 1, voice 1)",
            "Compact: [-P, +H, -L, +C, -D]",
        ]

    def test_phrases_are_separated_by_one_blank_line_and_name_their_closing(self) -> None:
        first = TimeSpan(onset=Fraction(0), end=Fraction(4))
        second = TimeSpan(onset=Fraction(4), end=Fraction(8))
        analysis = TexturalAnalysis(
            phrases=(
                phrase_texture(1, PhraseClosing.FERMATA, four_lines(first)),
                phrase_texture(2, PhraseClosing.SCORE_END, four_lines(second)),
            )
        )
        lines = format_textural_schema(analysis).splitlines()
        assert lines.count("") == 1
        assert [line for line in lines if line.startswith("Phrase")] == [
            "Phrase 1, bars 1 to 2, closing: fermata",
            "Phrase 2, bars 2 to 3, closing: score end",
        ]
        assert lines[lines.index("") - 1] == f"Compact: {EXAMPLE_SIX}"


class TestExplain:
    def explained(self) -> list[str]:
        root = TexturalFeatures(
            planes=FeatureDecision(
                value=True, rule=DecisionRule.PLANE_COUNT, explanation="2 planes below."
            ),
            homogeneity=FeatureDecision(
                value=True, rule=DecisionRule.SINGLE_METER_AND_KEY, explanation="One meter."
            ),
            linearity=FeatureDecision(
                value=None, rule=DecisionRule.RESTRICTION_4, explanation="Not at planes."
            ),
            accent_coincidence=FeatureDecision(
                value=True, rule=DecisionRule.SHARED_METER, explanation="Same meter."
            ),
            attack_divergence=FeatureDecision(
                value=False, rule=DecisionRule.ATTACKS_WITHIN_TACTUS, explanation="None diverge."
            ),
        )
        tree = node_of(
            root, leaf_of(line_features(), stream(1, 1, "A")), leaf_of(line_features(), stream(2))
        )
        analysis = TexturalAnalysis(phrases=(phrase_texture(1, PhraseClosing.FERMATA, tree),))
        return format_textural_schema(analysis, explain=True).splitlines()

    def test_a_plus_p_node_is_followed_by_its_five_decisions_two_spaces_deeper(self) -> None:
        assert self.explained()[1:7] == [
            "[+P, +H, +C, -D",
            "  P +: plane_count: 2 planes below.",
            "  H +: single_meter_and_key: One meter.",
            "  L unspecified: restriction_4: Not at planes.",
            "  C +: shared_meter: Same meter.",
            "  D -: attacks_within_tactus: None diverge.",
        ]

    def test_a_leaf_is_followed_by_its_decisions_two_spaces_deeper_than_the_leaf(self) -> None:
        lines = self.explained()
        assert lines[7] == "    [-P, +H, +L, +C, -D]  A (part 1, voice 1)"
        assert lines[8] == "      P -: plane_count: test decision"
        assert lines[12] == "      D -: plane_count: test decision"

    def test_the_closing_bracket_and_compact_line_follow_the_decisions(self) -> None:
        lines = self.explained()
        assert lines[-2] == "]"
        assert lines[-1].startswith("Compact: ")

    def test_without_explain_no_decision_lines_appear(self) -> None:
        analysis = TexturalAnalysis(
            phrases=(phrase_texture(1, PhraseClosing.FERMATA, four_lines()),)
        )
        assert "plane_count" not in format_textural_schema(analysis)
