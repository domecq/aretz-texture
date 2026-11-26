"""The textural schema: a tree of textural configurations as text in Fessel's notation.

A secondary output of the analysis, an annex to the four voice reduction (spec 002,
section 3.8). It is rendered from the tree only and never recomputes the analysis.
"""

from aretz_texture.core.texture import (
    FeatureDecision,
    PhraseClosing,
    PhraseTexture,
    TexturalAnalysis,
    TexturalConfiguration,
    TexturalFeature,
)

INDENTATION_PER_LEVEL = 4  # spaces a child is indented deeper than its parent
EXPLANATION_INDENTATION = 2  # spaces a decision line is indented deeper than its node
STREAM_LABEL_SEPARATOR = "; "
LABEL_GAP = "  "  # between the closing bracket of a leaf and its stream labels
UNSPECIFIED = "unspecified"

# The order of the features in a feature list (Fessel 1996, pp. 84 to 89).
_FEATURE_ORDER = (
    TexturalFeature.PLANES,
    TexturalFeature.HOMOGENEITY,
    TexturalFeature.LINEARITY,
    TexturalFeature.ACCENT_COINCIDENCE,
    TexturalFeature.ATTACK_DIVERGENCE,
)

_CLOSING_WORDS = {
    PhraseClosing.FERMATA: "fermata",
    PhraseClosing.SCORE_END: "score end",
    PhraseClosing.NO_FERMATAS: "no fermatas",
}


def closing_label(closing: PhraseClosing) -> str:
    """Return how a phrase closing is written in headings and lists: `fermata` and the like."""
    return _CLOSING_WORDS[closing]


def _decisions_in_order(configuration: TexturalConfiguration) -> list[tuple[str, FeatureDecision]]:
    features = configuration.features
    by_feature = {
        TexturalFeature.PLANES: features.planes,
        TexturalFeature.HOMOGENEITY: features.homogeneity,
        TexturalFeature.LINEARITY: features.linearity,
        TexturalFeature.ACCENT_COINCIDENCE: features.accent_coincidence,
        TexturalFeature.ATTACK_DIVERGENCE: features.attack_divergence,
    }
    return [(feature.value, by_feature[feature]) for feature in _FEATURE_ORDER]


def _sign(value: bool | None) -> str:
    if value is None:
        return UNSPECIFIED
    return "+" if value else "-"


def _feature_list(configuration: TexturalConfiguration) -> str:
    """Return the opening of a node: `[` and its specified features, without a closing."""
    items = [
        f"{_sign(decision.value)}{letter}"
        for letter, decision in _decisions_in_order(configuration)
        if decision.value is not None
    ]
    return "[" + ", ".join(items)


def compact_schema(configuration: TexturalConfiguration) -> str:
    """Return a configuration on one line, collapsing identical sibling forms.

    Children whose compact forms are identical are printed once, in order of first
    appearance, as Fessel prints the four lines of his example 6 (1996, p. 86).

    Args:
        configuration: The root of the tree to write.

    Returns:
        The bracketed form, such as `[+P, +H, +C, +D [-P, +H, +L, +C, -D]]`.
    """
    opening = _feature_list(configuration)
    if not configuration.children:
        return opening + "]"
    distinct_children = dict.fromkeys(compact_schema(child) for child in configuration.children)
    return f"{opening} {' '.join(distinct_children)}]"


def _explanation_lines(configuration: TexturalConfiguration, indentation: int) -> list[str]:
    padding = " " * (indentation + EXPLANATION_INDENTATION)
    return [
        f"{padding}{letter} {_sign(decision.value)}: {decision.rule.value}: {decision.explanation}"
        for letter, decision in _decisions_in_order(configuration)
    ]


def _indented_lines(
    configuration: TexturalConfiguration, indentation: int, *, explain: bool
) -> list[str]:
    padding = " " * indentation
    explanation = _explanation_lines(configuration, indentation) if explain else []
    if not configuration.children:
        labels = STREAM_LABEL_SEPARATOR.join(stream.label() for stream in configuration.streams)
        leaf_line = f"{padding}{_feature_list(configuration)}]{LABEL_GAP}{labels}"
        return [leaf_line, *explanation]
    lines = [padding + _feature_list(configuration), *explanation]
    for child in configuration.children:
        lines += _indented_lines(child, indentation + INDENTATION_PER_LEVEL, explain=explain)
    return [*lines, padding + "]"]


def _phrase_block(phrase_texture: PhraseTexture, *, explain: bool) -> list[str]:
    phrase = phrase_texture.phrase
    heading = (
        f"Phrase {phrase.number}, bars {phrase.first_bar_number} to {phrase.last_bar_number}, "
        f"closing: {closing_label(phrase.closing)}"
    )
    configuration = phrase_texture.configuration
    return [
        heading,
        *_indented_lines(configuration, 0, explain=explain),
        f"Compact: {compact_schema(configuration)}",
    ]


def format_textural_schema(analysis: TexturalAnalysis, *, explain: bool = False) -> str:
    """Return the textural schema of an analysis, one block per phrase.

    Each block has a heading, the indented form with every leaf on its own line and its
    stream labels, and the compact form. Blocks are separated by one blank line. The text
    has no trailing newline.

    Args:
        analysis: The textural analysis to write.
        explain: Whether each node is followed by one line per feature with its value,
            rule and explanation.

    Returns:
        The text of the schema.
    """
    blocks = ["\n".join(_phrase_block(texture, explain=explain)) for texture in analysis.phrases]
    return "\n\n".join(blocks)
