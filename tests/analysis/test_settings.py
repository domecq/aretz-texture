from fractions import Fraction

import pytest
from pydantic import ValidationError

from aretz_texture.analysis.settings import (
    DoublingSettings,
    FeatureSettings,
    PhraseSegmentationSettings,
    TexturalAnalysisSettings,
)


def test_defaults_are_those_of_spec_002() -> None:
    settings = TexturalAnalysisSettings()

    assert settings.phrases.minimum_fermata_voices == 1
    assert settings.doublings.minimum_coinciding_attack_proportion == Fraction(9, 10)
    assert settings.features.linear_interval_classes == frozenset({0, 3, 4, 5, 7, 8, 9})
    assert settings.features.minimum_parallel_motion_proportion == Fraction(9, 10)
    assert settings.features.minimum_linear_attack_proportion == Fraction(1)
    assert settings.features.minimum_divergent_tactus_spans == 1


def test_phrase_settings_are_immutable() -> None:
    settings = PhraseSegmentationSettings()

    with pytest.raises(ValidationError):
        settings.minimum_fermata_voices = 2  # pyright: ignore[reportAttributeAccessIssue]


def test_doubling_settings_are_immutable() -> None:
    settings = DoublingSettings()

    with pytest.raises(ValidationError):
        settings.minimum_coinciding_attack_proportion = Fraction(1)  # pyright: ignore[reportAttributeAccessIssue]


def test_feature_settings_are_immutable() -> None:
    settings = FeatureSettings()

    with pytest.raises(ValidationError):
        settings.minimum_divergent_tactus_spans = 2  # pyright: ignore[reportAttributeAccessIssue]


def test_the_bundle_of_settings_is_immutable() -> None:
    settings = TexturalAnalysisSettings()

    with pytest.raises(ValidationError):
        settings.phrases = PhraseSegmentationSettings(minimum_fermata_voices=2)  # pyright: ignore[reportAttributeAccessIssue]


def test_settings_can_be_overridden_by_name() -> None:
    settings = DoublingSettings(minimum_coinciding_attack_proportion=Fraction(1))

    assert settings.minimum_coinciding_attack_proportion == 1
