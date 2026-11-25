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


@pytest.mark.parametrize(
    "proportion", [Fraction(0), Fraction(-1, 10), Fraction(11, 10), Fraction(9)]
)
def test_doubling_proportion_outside_zero_to_one_is_rejected(proportion: Fraction) -> None:
    with pytest.raises(ValidationError):
        DoublingSettings(minimum_coinciding_attack_proportion=proportion)


@pytest.mark.parametrize(
    "field", ["minimum_parallel_motion_proportion", "minimum_linear_attack_proportion"]
)
@pytest.mark.parametrize("proportion", [Fraction(0), Fraction(-1, 10), Fraction(11, 10)])
def test_feature_proportion_outside_zero_to_one_is_rejected(
    field: str, proportion: Fraction
) -> None:
    with pytest.raises(ValidationError):
        FeatureSettings.model_validate({field: proportion})


@pytest.mark.parametrize("count", [0, -1])
def test_minimum_fermata_voices_below_one_is_rejected(count: int) -> None:
    with pytest.raises(ValidationError):
        PhraseSegmentationSettings(minimum_fermata_voices=count)


@pytest.mark.parametrize("count", [0, -1])
def test_minimum_divergent_tactus_spans_below_one_is_rejected(count: int) -> None:
    with pytest.raises(ValidationError):
        FeatureSettings(minimum_divergent_tactus_spans=count)


@pytest.mark.parametrize("interval_class", [-1, 12])
def test_interval_class_outside_the_octave_is_rejected(interval_class: int) -> None:
    with pytest.raises(ValidationError):
        FeatureSettings(linear_interval_classes=frozenset({0, interval_class}))


def test_proportion_of_exactly_one_is_accepted() -> None:
    settings = FeatureSettings(minimum_parallel_motion_proportion=Fraction(1))

    assert settings.minimum_parallel_motion_proportion == 1
