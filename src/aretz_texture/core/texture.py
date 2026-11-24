"""Textural configurations: Fessel's tree of planes with five binary features (ADR 0004)."""

from enum import StrEnum
from fractions import Fraction
from itertools import pairwise
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

MINIMUM_PLANES_OF_A_PLUS_P_CONFIGURATION = 2  # a plane is only distinguished from another


class TimeSpan(BaseModel):
    """A stretch of the score, in quarter lengths from the start of the first bar."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction
    end: Fraction  # greater than onset

    @model_validator(mode="after")
    def _check_onset_is_before_end(self) -> Self:
        if self.onset >= self.end:
            message = f"a span must end after its onset, got {self.onset} to {self.end}"
            raise ValueError(message)
        return self

    def contains(self, other: "TimeSpan") -> bool:
        """Return whether the other span lies inside this one, borders included."""
        return self.onset <= other.onset and other.end <= self.end


class StreamReference(BaseModel):
    """One notated voice of one part, the unit the textural analysis groups into planes."""

    model_config = ConfigDict(frozen=True)

    part_number: int  # 1 based, score order
    voice_number: int  # 1 based notated voice of that part
    part_name: str | None  # as in the source; shown in the labels of the schema

    def label(self) -> str:
        """Return the label of the schema, such as "Soprano (part 1, voice 1)"."""
        name = "unnamed" if self.part_name is None else self.part_name
        return f"{name} (part {self.part_number}, voice {self.voice_number})"


class TexturalFeature(StrEnum):
    """The five binary textural features of Fessel (1996, p. 79), by their letter."""

    PLANES = "P"
    HOMOGENEITY = "H"
    LINEARITY = "L"
    ACCENT_COINCIDENCE = "C"
    ATTACK_DIVERGENCE = "D"


class DecisionRule(StrEnum):
    """The rule or factor that decided the value of a feature (spec 002, section 3.6)."""

    PLANE_COUNT = "plane_count"  # P from the number of planes below the node
    SINGLE_METER_AND_KEY = "single_meter_and_key"  # H, provisional rule
    ASSUMED_OUTSIDE_CONDITIONS = "assumed_outside_conditions"  # H outside its conditions
    SHARED_METER = "shared_meter"  # C at +P nodes, provisional rule
    SIMULTANEITY_CONDITIONS = "simultaneity_conditions"  # L at -P nodes
    ATTACKS_WITHIN_TACTUS = "attacks_within_tactus"  # D measured
    RESTRICTION_2 = "restriction_2"  # -P implies +H (Fessel 1996, p. 84)
    RESTRICTION_3 = "restriction_3"  # -C implies +P, so -P is +C
    RESTRICTION_4 = "restriction_4"  # L unspecified at +P
    RESTRICTION_5 = "restriction_5"  # +L implies -D


class FeatureDecision(BaseModel):
    """The value of one feature at one node, with the rule that decided it."""

    model_config = ConfigDict(frozen=True)

    value: bool | None  # True is +, False is -, None is unspecified (only L, at +P)
    rule: DecisionRule
    explanation: str  # one sentence for a musician, with bars and tactus spans


class TexturalFeatures(BaseModel):
    """The five decisions of a configuration, bound by the cooccurrence restrictions."""

    model_config = ConfigDict(frozen=True)

    planes: FeatureDecision
    homogeneity: FeatureDecision
    linearity: FeatureDecision
    accent_coincidence: FeatureDecision
    attack_divergence: FeatureDecision

    @model_validator(mode="after")
    def _check_only_linearity_is_unspecified(self) -> Self:
        specified = {
            TexturalFeature.PLANES: self.planes,
            TexturalFeature.HOMOGENEITY: self.homogeneity,
            TexturalFeature.ACCENT_COINCIDENCE: self.accent_coincidence,
            TexturalFeature.ATTACK_DIVERGENCE: self.attack_divergence,
        }
        for feature, feature_decision in specified.items():
            if feature_decision.value is None:
                message = f"only linearity may be unspecified, {feature} is"
                raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _check_cooccurrence_restrictions(self) -> Self:
        # Fessel 1996, pp. 84 and 85. Restrictions 1 (-H implies +P) and 2 (-P implies +H)
        # are contrapositives, so one check covers both (spec 002, section 6).
        planes = self.planes.value
        if self.homogeneity.value is False and not planes:
            message = "restrictions 1 and 2: -H needs +P, and -P needs +H"
            raise ValueError(message)
        if self.accent_coincidence.value is False and not planes:
            message = "restriction 3: -C needs +P"
            raise ValueError(message)
        if (self.linearity.value is None) != bool(planes):
            message = "restriction 4: L is specified if and only if the configuration is -P"
            raise ValueError(message)
        if self.linearity.value and self.attack_divergence.value:
            message = "restriction 5: +L needs -D"
            raise ValueError(message)
        return self


class TexturalConfiguration(BaseModel):
    """A node of the tree: a `+P` configuration over its planes, or a `-P` leaf of streams."""

    model_config = ConfigDict(frozen=True)

    span: TimeSpan
    features: TexturalFeatures
    children: tuple["TexturalConfiguration", ...]  # the planes below; empty exactly at -P
    streams: tuple[StreamReference, ...]  # only at -P: the notated voices it groups

    @model_validator(mode="after")
    def _check_children_agree_with_planes(self) -> Self:
        # Project, following the tree of Fessel 1996, pp. 83 and 84.
        child_count = len(self.children)
        if self.features.planes.value:
            if child_count < MINIMUM_PLANES_OF_A_PLUS_P_CONFIGURATION:
                message = f"a +P configuration needs at least two children, got {child_count}"
                raise ValueError(message)
            if self.streams:
                message = "a +P configuration has no streams of its own"
                raise ValueError(message)
        else:
            if self.children:
                message = "a -P configuration has no children"
                raise ValueError(message)
            if not self.streams:
                message = "a -P configuration needs at least one stream"
                raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _check_children_spans_are_inside(self) -> Self:
        for child in self.children:
            if not self.span.contains(child.span):
                message = f"a child span {child.span} is outside the parent span {self.span}"
                raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _check_no_stream_is_in_two_leaves(self) -> Self:
        # Stream segregation is out of scope, so a notated voice is in one leaf only.
        seen: set[tuple[int, int]] = set()
        for leaf in self.leaves():
            for stream in leaf.streams:
                key = (stream.part_number, stream.voice_number)
                if key in seen:
                    message = f"part {key[0]}, voice {key[1]} is in two leaves"
                    raise ValueError(message)
                seen.add(key)
        return self

    def leaves(self) -> tuple["TexturalConfiguration", ...]:
        """Return the `-P` nodes below this one, in order; a leaf returns itself."""
        if not self.children:
            return (self,)
        return tuple(leaf for child in self.children for leaf in child.leaves())

    def density(self) -> int:
        """Return the number of streams of a `-P` node; a `+P` node has none of its own."""
        return len(self.streams)


class PhraseClosing(StrEnum):
    """What ends a phrase."""

    FERMATA = "fermata"  # ends at a fermata end cluster
    SCORE_END = "score_end"  # the music after the last fermata
    NO_FERMATAS = "no_fermatas"  # the whole score, which has no fermata


class Phrase(BaseModel):
    """The local domain over which one textural configuration is computed (ADR 0005)."""

    model_config = ConfigDict(frozen=True)

    number: int  # 1 based
    span: TimeSpan
    first_bar_number: int  # the bar containing the onset, as shown in the score
    last_bar_number: int  # the bar containing the last moment before the end
    closing: PhraseClosing


class PhraseTexture(BaseModel):
    """A phrase with its textural configuration."""

    model_config = ConfigDict(frozen=True)

    phrase: Phrase
    configuration: TexturalConfiguration  # its span equals the span of the phrase


class TexturalAnalysis(BaseModel):
    """The textural configurations of every phrase of a score."""

    model_config = ConfigDict(frozen=True)

    phrases: tuple[PhraseTexture, ...]  # numbered from 1, contiguous, covering the score

    @model_validator(mode="after")
    def _check_phrases_tile_the_score(self) -> Self:
        for expected_number, phrase_texture in enumerate(self.phrases, start=1):
            if phrase_texture.phrase.number != expected_number:
                message = f"phrase {expected_number} is numbered {phrase_texture.phrase.number}"
                raise ValueError(message)
            if phrase_texture.configuration.span != phrase_texture.phrase.span:
                message = f"the configuration of phrase {expected_number} spans another stretch"
                raise ValueError(message)
        if self.phrases and self.phrases[0].phrase.span.onset != 0:
            message = "the first phrase must start at 0"
            raise ValueError(message)
        for previous, following in pairwise(self.phrases):
            if following.phrase.span.onset != previous.phrase.span.end:
                message = f"phrase {following.phrase.number} does not start where the previous ends"
                raise ValueError(message)
        return self
