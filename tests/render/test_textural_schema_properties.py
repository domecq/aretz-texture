from collections.abc import Callable
from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st
from tests.strategies import textural_configurations
from tests.texture_builders import (
    PHRASE_SPAN,
    accompaniment_features,
    chord_features,
    leaf_of,
    line_features,
    node_of,
    root_features,
    stream,
)

from aretz_texture.core.texture import (
    Phrase,
    PhraseClosing,
    PhraseTexture,
    TexturalAnalysis,
    TexturalConfiguration,
    TexturalFeatures,
    TimeSpan,
)
from aretz_texture.render.textural_schema import compact_schema, format_textural_schema


def is_balanced(text: str) -> bool:
    depth = 0
    for character in text:
        depth += {"[": 1, "]": -1}.get(character, 0)
        if depth < 0:
            return False
    return depth == 0


def phrase_texture_of(
    number: int, closing: PhraseClosing, tree: TexturalConfiguration
) -> PhraseTexture:
    phrase = Phrase(
        number=number, span=tree.span, first_bar_number=1, last_bar_number=1, closing=closing
    )
    return PhraseTexture(phrase=phrase, configuration=tree)


def analysis_of(tree: TexturalConfiguration) -> TexturalAnalysis:
    """Return an analysis ending in the tree, with a filler phrase when it starts after 0."""
    if tree.span.onset == 0:
        return TexturalAnalysis(phrases=(phrase_texture_of(1, PhraseClosing.FERMATA, tree),))
    filler_span = TimeSpan(onset=Fraction(0), end=tree.span.onset)
    filler = leaf_of(line_features(), stream(1), span=filler_span)
    return TexturalAnalysis(
        phrases=(
            phrase_texture_of(1, PhraseClosing.FERMATA, filler),
            phrase_texture_of(2, PhraseClosing.SCORE_END, tree),
        )
    )


@given(textural_configurations())
def test_compact_form_has_balanced_brackets(tree: TexturalConfiguration) -> None:
    assert is_balanced(compact_schema(tree))


@given(textural_configurations())
def test_indented_form_has_balanced_brackets_with_every_leaf_on_its_own_line(
    tree: TexturalConfiguration,
) -> None:
    lines = format_textural_schema(analysis_of(tree)).splitlines()
    assert is_balanced("\n".join(lines))
    filler_leaves = 0 if tree.span.onset == 0 else 1
    leaf_lines = [line for line in lines if "(part " in line]
    assert len(leaf_lines) == len(tree.leaves()) + filler_leaves


LEAF_FEATURES = [line_features, chord_features, accompaniment_features]


@given(st.sampled_from(LEAF_FEATURES), st.integers(min_value=2, max_value=8))
def test_identical_children_collapse_to_one_whatever_their_number(
    make_features: Callable[[], TexturalFeatures], child_count: int
) -> None:
    leaves = [leaf_of(make_features(), stream(number)) for number in range(1, child_count + 1)]
    tree = node_of(root_features(), *leaves, span=PHRASE_SPAN)
    only_child = compact_schema(leaves[0])
    assert compact_schema(tree) == f"[+P, +H, +C, +D {only_child}]"
