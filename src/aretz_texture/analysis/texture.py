"""The tree of textural configurations of each phrase of a score (spec 002, section 3.7)."""

from fractions import Fraction

from aretz_texture.analysis.attacks import voice_attacks
from aretz_texture.analysis.doublings import FusedStream, fuse_doublings
from aretz_texture.analysis.features import leaf_features, root_features
from aretz_texture.analysis.phrases import segment_phrases
from aretz_texture.analysis.settings import FeatureSettings, TexturalAnalysisSettings
from aretz_texture.core.errors import SilentPhraseError
from aretz_texture.core.score import Score
from aretz_texture.core.texture import (
    Phrase,
    PhraseTexture,
    StreamReference,
    TexturalAnalysis,
    TexturalConfiguration,
    TimeSpan,
)


def analyze_texture(score: Score, settings: TexturalAnalysisSettings) -> TexturalAnalysis:
    """Compute the tree of textural configurations of every phrase of a score.

    Pure and deterministic: the result depends on the score and the settings only, and not on
    the order of the parts, except for the order of planes of equal register, which is
    presentation only.

    Args:
        score: The score to analyze.
        settings: The thresholds of every step.

    Returns:
        One configuration per phrase, whose span is the span of the phrase.

    Raises:
        SilentPhraseError: A phrase has no attack, so it has no plane.
    """
    fused_streams = fuse_doublings(score, settings.doublings)
    return TexturalAnalysis(
        phrases=tuple(
            PhraseTexture(
                phrase=phrase,
                configuration=_configuration_of(score, settings.features, fused_streams, phrase),
            )
            for phrase in segment_phrases(score, settings.phrases)
        )
    )


def _configuration_of(
    score: Score,
    settings: FeatureSettings,
    fused_streams: tuple[FusedStream, ...],
    phrase: Phrase,
) -> TexturalConfiguration:
    planes = _planes_in(score, fused_streams, phrase)
    # See ADR 0005: each fused stream present in the phrase is one plane under the root.
    leaves = [
        TexturalConfiguration(
            span=phrase.span,
            features=leaf_features(score, settings, plane, phrase.span),
            children=(),
            streams=plane,
        )
        for plane in planes
    ]
    if len(leaves) == 1:
        return leaves[0]
    return TexturalConfiguration(
        span=phrase.span,
        features=root_features(score, settings, leaves, phrase.span),
        children=tuple(leaves),
        streams=(),
    )


def _planes_in(
    score: Score, fused_streams: tuple[FusedStream, ...], phrase: Phrase
) -> list[tuple[StreamReference, ...]]:
    """Return the planes of a phrase, highest register first.

    A fused stream is present when one of its notated voices attacks in the phrase, and its
    plane lists only those voices.
    """
    present = [
        plane for fused in fused_streams if (plane := _voices_attacking(score, fused, phrase.span))
    ]
    if not present:
        message = (
            f"Phrase {phrase.number}, bars {phrase.first_bar_number} to "
            f"{phrase.last_bar_number}, has no attack, so it has no plane to configure."
        )
        raise SilentPhraseError(message)
    # Project, presentation only: Fessel's configurations are unordered (1996, p. 79).
    return sorted(
        present,
        key=lambda plane: (
            -_mean_register(score, plane, phrase.span),
            plane[0].part_number,
            plane[0].voice_number,
        ),
    )


def _voices_attacking(
    score: Score, fused: FusedStream, span: TimeSpan
) -> tuple[StreamReference, ...]:
    return tuple(stream for stream in fused.streams if voice_attacks(score, stream, span))


def _mean_register(score: Score, plane: tuple[StreamReference, ...], span: TimeSpan) -> Fraction:
    """Return the mean sounding pitch of the pitches a plane attacks, exact, in semitones."""
    semitones = [
        pitch.sounding_semitones()
        for stream in plane
        for attack in voice_attacks(score, stream, span)
        for pitch in attack.pitches
    ]
    return Fraction(sum(semitones), len(semitones))
