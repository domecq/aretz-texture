"""Criterion 22 of spec 002: L of a leaf, and D by restriction 5 or measured."""

from fractions import Fraction

from tests.analysis.texture_scores import (
    DEFAULT_SETTINGS,
    analyze,
    attacking_at,
    first_configuration,
)
from tests.core_builders import divided_event, event, part_of, score_of

from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.notation import NoteEvent
from aretz_texture.core.texture import DecisionRule, TexturalConfiguration

LINE = ["C4", "D4", "E4", "F4", "G4", "A4", "G4", "F4", "E4", "D4"]
CHORD_TONES = ("E4", "C4")


def one_quarter_per_pitch(pitches: list[str]) -> list[NoteEvent]:
    return [event(onset, 1, pitch) for onset, pitch in enumerate(pitches)]


def thirds(*pairs: tuple[str, str]) -> list[NoteEvent]:
    return [
        divided_event(onset, 1, (upper, None), (lower, None))
        for onset, (upper, lower) in enumerate(pairs)
    ]


def leaf_of_score(*events_of_parts: list[NoteEvent], bars: int = 3) -> TexturalConfiguration:
    parts = [part_of(events) for events in events_of_parts]
    return first_configuration(score_of(*parts, bar_durations=(4,) * bars))


def test_a_leaf_of_one_voice_without_divided_events_is_plus_l_and_minus_d_by_restriction_5() -> (
    None
):
    root = leaf_of_score(one_quarter_per_pitch(LINE[:8]), attacking_at("E3", [0, 1, 2, 3], 4))
    soprano_leaf = root.children[0]

    assert soprano_leaf.features.linearity.value is True
    assert soprano_leaf.features.linearity.rule is DecisionRule.SIMULTANEITY_CONDITIONS
    assert soprano_leaf.features.attack_divergence.value is False
    assert soprano_leaf.features.attack_divergence.rule is DecisionRule.RESTRICTION_5


def test_two_voices_fused_at_the_octave_with_all_attacks_coinciding_are_plus_l() -> None:
    upper = one_quarter_per_pitch(LINE)
    lower = one_quarter_per_pitch([pitch[:-1] + "3" for pitch in LINE])

    leaf = leaf_of_score(upper, lower, bars=3)

    assert leaf.features.planes.value is False
    assert len(leaf.streams) == 2
    assert leaf.features.linearity.value is True


def fused_pair_where_one_voice_attacks_while_the_other_holds() -> TexturalConfiguration:
    held = [event(2 * step, 2, "C4") for step in range(10)]
    restruck = attacking_at(
        "C3", [2 * step + offset for step in range(10) for offset in (0, 0.5)], 20
    )
    return leaf_of_score(held, restruck, bars=5)


def test_a_fused_leaf_where_one_voice_attacks_while_the_other_holds_is_minus_l() -> None:
    leaf = fused_pair_where_one_voice_attacks_while_the_other_holds()

    assert len(leaf.streams) == 2
    assert leaf.features.linearity.value is False
    assert "sounds without attacking" in leaf.features.linearity.explanation
    assert "bar 1, tactus 1" in leaf.features.linearity.explanation


def test_the_divergence_of_a_minus_l_fused_leaf_is_measured() -> None:
    leaf = fused_pair_where_one_voice_attacks_while_the_other_holds()

    divergence = leaf.features.attack_divergence
    assert divergence.value is True
    assert divergence.rule is DecisionRule.ATTACKS_WITHIN_TACTUS


def test_a_divided_event_at_a_second_makes_its_leaf_minus_l() -> None:
    dyads = [divided_event(onset, 1, ("D4", None), ("C4", None)) for onset in range(4)]

    leaf = leaf_of_score(dyads, bars=1)

    assert leaf.features.linearity.value is False
    assert "2 semitones" in leaf.features.linearity.explanation


def test_a_succession_of_divided_events_in_parallel_thirds_is_plus_l() -> None:
    parallel = thirds(("E4", "C4"), ("F4", "D4"), ("G4", "E4"), ("A4", "F4"))

    leaf = leaf_of_score(parallel, bars=1)

    assert leaf.features.linearity.value is True


def test_the_same_thirds_in_contrary_motion_are_minus_l() -> None:
    contrary = thirds(("E4", "C4"), ("G4", "B3"), ("E4", "C4"), ("G4", "B3"))

    leaf = leaf_of_score(contrary, bars=1)

    assert leaf.features.linearity.value is False
    assert "parallel" in leaf.features.linearity.explanation


def test_octave_doublings_inside_one_voice_need_no_parallel_motion() -> None:
    # Dyads at the octave beside single notes: the steps between them have different counts
    # of pitches, so they would not count as parallel if the octave needed parallel motion.
    mixed = [
        divided_event(0, 1, ("C5", None), ("C4", None)),
        event(1, 1, "E4"),
        divided_event(2, 1, ("D5", None), ("D4", None)),
        event(3, 1, "C4"),
    ]

    leaf = leaf_of_score(mixed, bars=1)

    assert leaf.features.linearity.value is True


def test_the_linear_attack_proportion_is_a_setting() -> None:
    features = DEFAULT_SETTINGS.features.model_copy(
        update={"minimum_linear_attack_proportion": Fraction(1, 2)}
    )
    settings = DEFAULT_SETTINGS.model_copy(update={"features": features})
    held = [event(2 * step, 2, "C4") for step in range(10)]
    restruck = attacking_at(
        "C3", [2 * step + offset for step in range(10) for offset in (0, 0.5)], 20
    )
    score = score_of(part_of(held), part_of(restruck), bar_durations=(4,) * 5)

    leaf = analyze_texture(score, settings).phrases[0].configuration

    assert leaf.features.linearity.value is True


def test_a_tolerated_failure_is_reported_with_the_share_and_the_threshold() -> None:
    features = DEFAULT_SETTINGS.features.model_copy(
        update={"minimum_linear_attack_proportion": Fraction(1, 2)}
    )
    settings = DEFAULT_SETTINGS.model_copy(update={"features": features})
    held = [event(2 * step, 2, "C4") for step in range(10)]
    restruck = attacking_at(
        "C3", [2 * step + offset for step in range(10) for offset in (0, 0.5)], 20
    )
    score = score_of(part_of(held), part_of(restruck), bar_durations=(4,) * 5)

    explanation = (
        analyze_texture(score, settings).phrases[0].configuration.features.linearity.explanation
    )

    assert explanation.startswith("10 of 20 attack points meet the conditions, at least 1/2")


def test_every_decision_of_a_leaf_has_an_explanation() -> None:
    analysis = analyze(score_of(part_of(one_quarter_per_pitch(LINE[:4])), bar_durations=(4,)))

    leaf = analysis.phrases[0].configuration

    assert leaf.features.linearity.explanation
    assert leaf.features.attack_divergence.explanation
