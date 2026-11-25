"""Criterion 21 of spec 002: the reading of D, a tactus span at a time."""

from tests.analysis.texture_scores import (
    DEFAULT_SETTINGS,
    attacking_at,
    first_configuration,
    tied_continuation,
    voices_attacking_at,
)
from tests.core_builders import part_of, score_of

from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.texture import DecisionRule, TexturalConfiguration

QUARTERS = [0, 1, 2, 3, 4, 5, 6, 7]
EIGHTHS = [step / 2 for step in range(16)]


def divergence_of(configuration: TexturalConfiguration) -> bool | None:
    return configuration.features.attack_divergence.value


def test_a_homorhythmic_phrase_is_minus_d_at_the_root() -> None:
    score = voices_attacking_at([QUARTERS] * 4)

    root = first_configuration(score)

    assert root.features.planes.value is True
    assert divergence_of(root) is False


def test_voices_moving_together_in_eighths_do_not_diverge() -> None:
    score = voices_attacking_at([EIGHTHS] * 4)

    assert divergence_of(first_configuration(score)) is False


def test_one_passing_eighth_in_one_voice_makes_the_root_plus_d() -> None:
    alto = sorted([*QUARTERS, 3.5])
    score = voices_attacking_at([QUARTERS, alto, QUARTERS, QUARTERS])

    root = first_configuration(score)

    assert divergence_of(root) is True
    assert root.features.attack_divergence.rule is DecisionRule.ATTACKS_WITHIN_TACTUS


def test_a_voice_attacking_alone_while_the_others_hold_is_not_divergence() -> None:
    halves = [0, 2, 4, 6]
    score = voices_attacking_at([halves, QUARTERS, halves, halves])

    assert divergence_of(first_configuration(score)) is False


def test_voices_attacking_in_different_tactus_spans_are_not_divergence() -> None:
    # Spans [1, 2) and [2, 3) each hold the attack of one voice only.
    score = voices_attacking_at([[0, 1, 3, 4, 7], [0, 2, 3, 4, 7]])

    assert divergence_of(first_configuration(score)) is False


def test_a_tied_continuation_is_not_an_attack() -> None:
    eighths_in_the_first_beat = [0, 0.5, 1, 2, 3, 4, 5, 6, 7]
    with_a_tie = score_of(
        part_of(
            tied_continuation("E5", [0, 0.5], 1) + attacking_at("E5", [1, 2, 3, 4, 5, 6, 7], 8)
        ),
        part_of(attacking_at("C4", eighths_in_the_first_beat, 8)),
        bar_durations=(4, 4),
    )
    restruck = score_of(
        part_of(attacking_at("E5", eighths_in_the_first_beat, 8)),
        part_of(attacking_at("C4", eighths_in_the_first_beat, 8)),
        bar_durations=(4, 4),
    )

    assert divergence_of(first_configuration(with_a_tie)) is True
    assert divergence_of(first_configuration(restruck)) is False


def test_the_explanation_gives_the_count_and_the_first_divergent_span() -> None:
    alto = sorted([*QUARTERS, 5.5])
    score = voices_attacking_at([QUARTERS, alto, QUARTERS, QUARTERS])

    explanation = first_configuration(score).features.attack_divergence.explanation

    assert "1 of 8 tactus spans" in explanation
    assert "bar 2, tactus 2" in explanation
    assert "Alto" not in explanation  # the parts of the test have no names
    assert "part 2, voice 1" in explanation


def test_the_minimum_of_divergent_tactus_spans_is_a_setting() -> None:
    alto = sorted([*QUARTERS, 5.5])
    score = voices_attacking_at([QUARTERS, alto, QUARTERS, QUARTERS])
    features = DEFAULT_SETTINGS.features.model_copy(update={"minimum_divergent_tactus_spans": 2})
    settings = DEFAULT_SETTINGS.model_copy(update={"features": features})

    root = analyze_texture(score, settings).phrases[0].configuration

    assert divergence_of(root) is False
