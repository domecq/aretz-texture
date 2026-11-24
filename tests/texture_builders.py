"""Hand built textural configurations for tests: features, leaves and trees."""

from fractions import Fraction

from aretz_texture.core.texture import (
    DecisionRule,
    FeatureDecision,
    StreamReference,
    TexturalConfiguration,
    TexturalFeatures,
    TimeSpan,
)

PHRASE_SPAN = TimeSpan(onset=Fraction(0), end=Fraction(8))


def decision(value: bool | None, rule: DecisionRule = DecisionRule.PLANE_COUNT) -> FeatureDecision:
    """Return a decision with a fixed explanation."""
    return FeatureDecision(value=value, rule=rule, explanation="test decision")


def features_of(
    planes: bool,
    homogeneity: bool,
    linearity: bool | None,
    accent_coincidence: bool,
    attack_divergence: bool,
) -> TexturalFeatures:
    """Return features with the given values, each decided by an arbitrary rule."""
    return TexturalFeatures(
        planes=decision(planes),
        homogeneity=decision(homogeneity),
        linearity=decision(linearity),
        accent_coincidence=decision(accent_coincidence),
        attack_divergence=decision(attack_divergence),
    )


def line_features() -> TexturalFeatures:
    """Return `-P, +H, +L, +C, -D`: a line."""
    return features_of(False, True, True, True, False)


def chord_features() -> TexturalFeatures:
    """Return `-P, +H, -L, +C, -D`: a block of chords."""
    return features_of(False, True, False, True, False)


def accompaniment_features() -> TexturalFeatures:
    """Return `-P, +H, -L, +C, +D`: an accompaniment whose attacks diverge."""
    return features_of(False, True, False, True, True)


def root_features() -> TexturalFeatures:
    """Return `+P, +H, +C, +D`, with L unspecified."""
    return features_of(True, True, None, True, True)


def stream(
    part_number: int, voice_number: int = 1, part_name: str | None = None
) -> StreamReference:
    """Return a stream reference."""
    return StreamReference(part_number=part_number, voice_number=voice_number, part_name=part_name)


def leaf_of(
    features: TexturalFeatures,
    *streams: StreamReference,
    span: TimeSpan = PHRASE_SPAN,
) -> TexturalConfiguration:
    """Return a `-P` configuration grouping the streams."""
    return TexturalConfiguration(span=span, features=features, children=(), streams=streams)


def node_of(
    features: TexturalFeatures,
    *children: TexturalConfiguration,
    span: TimeSpan = PHRASE_SPAN,
) -> TexturalConfiguration:
    """Return a `+P` configuration over the children."""
    return TexturalConfiguration(span=span, features=features, children=children, streams=())


def four_lines(span: TimeSpan = PHRASE_SPAN) -> TexturalConfiguration:
    """Return Fessel's example 6: four lines of one chorale phrase, Soprano to Bass."""
    names = ("Soprano", "Alto", "Tenor", "Bass")
    return node_of(
        root_features(),
        *(
            leaf_of(line_features(), stream(number, 1, name), span=span)
            for number, name in enumerate(names, 1)
        ),
        span=span,
    )


def melody_with_accompaniment() -> TexturalConfiguration:
    """Return a line over an accompaniment of chords with diverging attacks."""
    return node_of(
        root_features(),
        leaf_of(line_features(), stream(1, 1, "Melody")),
        leaf_of(accompaniment_features(), stream(2, 1, "Accompaniment")),
    )
