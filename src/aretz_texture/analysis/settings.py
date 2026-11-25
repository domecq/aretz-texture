"""Typed settings of the textural analysis: every threshold with its unit and musical meaning.

Called settings, never configuration, so that "configuration" always means Fessel's textural
configuration. Defaults are provisional and change only through spec 002 or an ADR (ADR 0005).
"""

from fractions import Fraction
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Bounds checked when settings are built, the configuration boundary of AGENTS.md: an out of
# range threshold would otherwise change the analysis silently (a proportion above 1 fuses
# nothing, one of 0 fuses every voice, even voices without attacks).
type Proportion = Annotated[Fraction, Field(gt=0, le=1)]
type PositiveCount = Annotated[int, Field(ge=1)]
type IntervalClass = Annotated[int, Field(ge=0, le=11)]


class PhraseSegmentationSettings(BaseModel):
    """Settings of the segmentation of a score into phrases by fermatas."""

    model_config = ConfigDict(frozen=True)

    # Notated voices. How many notated voices must carry a fermata in a cluster for it
    # to end a phrase; 1 means any voice, so a missing fermata in other parts is harmless.
    minimum_fermata_voices: PositiveCount = 1


class DoublingSettings(BaseModel):
    """Settings of the fusion of doublings."""

    model_config = ConfigDict(frozen=True)

    # Ratio from 0 to 1. Share of the attacks of the voice with fewer attacks that must
    # fall at the same onset as an attack of the other voice, with a common pitch class,
    # for the two voices to be heard as one line with density (Fessel 2000, p. 87).
    minimum_coinciding_attack_proportion: Proportion = Fraction(9, 10)


class FeatureSettings(BaseModel):
    """Settings of the decisions of the textural features."""

    model_config = ConfigDict(frozen=True)

    # Interval classes in semitones modulo the octave at which simultaneous pitches of one
    # plane can still form one voice: unison and octave (0), fourth and fifth (5, 7), thirds
    # (3, 4) and sixths (8, 9), after Fessel's scale of closeness (1996, p. 81) and his
    # registral spacing of a line (2000, p. 86).
    linear_interval_classes: frozenset[IntervalClass] = frozenset({0, 3, 4, 5, 7, 8, 9})
    # Ratio from 0 to 1. Share of the steps between successive attack points of a plane,
    # where it has simultaneous pitches other than unison and octave, at which all its
    # pitches move in the same direction; Fessel 2000 (p. 86) asks that the parallelism
    # be relatively constant.
    minimum_parallel_motion_proportion: Proportion = Fraction(9, 10)
    # Ratio from 0 to 1. Share of the attack points of a plane at which the conditions of
    # linearity must hold for the plane to be +L; 1 is Fessel's necessary condition.
    minimum_linear_attack_proportion: Proportion = Fraction(1)
    # Tactus spans. How many tactus spans with diverging attacks make a configuration +D.
    minimum_divergent_tactus_spans: PositiveCount = 1


class TexturalAnalysisSettings(BaseModel):
    """All settings of the textural analysis."""

    model_config = ConfigDict(frozen=True)

    phrases: PhraseSegmentationSettings = Field(default_factory=PhraseSegmentationSettings)
    doublings: DoublingSettings = Field(default_factory=DoublingSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)
