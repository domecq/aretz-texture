"""Criteria 23 and 25 of spec 002: H and C by rule, and the shape of the tree of a phrase."""

from collections.abc import Sequence
from fractions import Fraction

import pytest
from tests.analysis.texture_scores import analyze, attacking_at, first_configuration
from tests.core_builders import FOUR_FOUR, event, part_of, score_of

from aretz_texture.core.errors import SilentPhraseError
from aretz_texture.core.score import KeySignatureChange, Score, TimeSignatureChange
from aretz_texture.core.texture import DecisionRule

THREE_FOUR_AT_4 = TimeSignatureChange(onset=Fraction(4), numerator=3, denominator=4)
THREE_FOUR_AT_8 = TimeSignatureChange(onset=Fraction(8), numerator=3, denominator=4)


def two_parts(
    bar_durations: Sequence[int],
    time_signatures: Sequence[TimeSignatureChange] = (FOUR_FOUR,),
    second_part_keys: Sequence[KeySignatureChange] | None = None,
    fermata_at: int | None = None,
) -> Score:
    end = sum(bar_durations)
    onsets = list(range(end))
    upper = attacking_at("E5", onsets, end)
    if fermata_at is not None:
        upper[fermata_at] = event(fermata_at, 1, "E5", fermata=True)
    return score_of(
        part_of(upper),
        part_of(attacking_at("C4", onsets, end), key_signatures=second_part_keys),
        bar_durations=bar_durations,
        time_signatures=time_signatures,
    )


def test_h_is_plus_by_the_single_meter_and_key_rule_without_changes_inside_the_phrase() -> None:
    root = first_configuration(two_parts((4, 4)))

    assert root.features.homogeneity.value is True
    assert root.features.homogeneity.rule is DecisionRule.SINGLE_METER_AND_KEY


def test_h_is_assumed_when_a_time_signature_changes_inside_the_phrase() -> None:
    score = two_parts((4, 3), time_signatures=(FOUR_FOUR, THREE_FOUR_AT_4))

    homogeneity = first_configuration(score).features.homogeneity

    assert homogeneity.value is True
    assert homogeneity.rule is DecisionRule.ASSUMED_OUTSIDE_CONDITIONS
    assert "time signature" in homogeneity.explanation
    assert "bar 2" in homogeneity.explanation


def test_h_is_assumed_when_a_part_changes_its_key_signature_inside_the_phrase() -> None:
    keys = (
        KeySignatureChange(onset=Fraction(0), sharps=0),
        KeySignatureChange(onset=Fraction(4), sharps=2),
    )
    score = two_parts((4, 4), second_part_keys=keys)

    homogeneity = first_configuration(score).features.homogeneity

    assert homogeneity.rule is DecisionRule.ASSUMED_OUTSIDE_CONDITIONS
    assert "key signature" in homogeneity.explanation
    assert "part 2" in homogeneity.explanation


def test_a_change_exactly_at_the_start_of_a_phrase_is_not_inside_it() -> None:
    score = two_parts((4, 4, 3), time_signatures=(FOUR_FOUR, THREE_FOUR_AT_8), fermata_at=7)

    analysis = analyze(score)

    first, second = (texture.configuration for texture in analysis.phrases)
    assert first.features.homogeneity.rule is DecisionRule.SINGLE_METER_AND_KEY
    assert second.features.homogeneity.rule is DecisionRule.SINGLE_METER_AND_KEY


def test_key_signatures_of_different_parts_are_not_compared() -> None:
    keys = (KeySignatureChange(onset=Fraction(0), sharps=3),)
    score = two_parts((4, 4), second_part_keys=keys)

    root = first_configuration(score)

    assert root.features.homogeneity.rule is DecisionRule.SINGLE_METER_AND_KEY


def test_the_root_has_c_by_the_shared_meter_and_l_unspecified_by_restriction_4() -> None:
    features = first_configuration(two_parts((4, 4))).features

    assert features.accent_coincidence.value is True
    assert features.accent_coincidence.rule is DecisionRule.SHARED_METER
    assert features.linearity.value is None
    assert features.linearity.rule is DecisionRule.RESTRICTION_4
    assert features.planes.value is True
    assert features.planes.rule is DecisionRule.PLANE_COUNT
    assert "2 planes" in features.planes.explanation


def test_the_leaves_get_h_and_c_by_restrictions_2_and_3() -> None:
    root = first_configuration(two_parts((4, 4)))

    for leaf in root.children:
        assert leaf.features.planes.value is False
        assert leaf.features.homogeneity.rule is DecisionRule.RESTRICTION_2
        assert leaf.features.accent_coincidence.rule is DecisionRule.RESTRICTION_3


def test_a_phrase_with_one_plane_is_a_single_leaf() -> None:
    score = score_of(part_of(attacking_at("C4", [0, 1, 2, 3], 4)), bar_durations=(4,))

    configuration = first_configuration(score)

    assert configuration.features.planes.value is False
    assert configuration.children == ()
    assert [stream.part_number for stream in configuration.streams] == [1]


def test_a_voice_that_does_not_attack_in_a_phrase_has_no_plane_there() -> None:
    upper = attacking_at("E5", range(8), 8)
    upper[3] = event(3, 1, "E5", fermata=True)
    lower_voice_resting_in_the_first_phrase = [event(onset, 1, "C4") for onset in range(4, 8)]
    score = score_of(
        part_of(upper),
        part_of(lower_voice_resting_in_the_first_phrase),
        bar_durations=(4, 4),
    )

    first, second = (texture.configuration for texture in analyze(score).phrases)

    assert first.children == ()
    assert [stream.part_number for stream in first.streams] == [1]
    assert len(second.children) == 2


def test_planes_are_ordered_by_register_whatever_the_order_of_the_parts() -> None:
    score = score_of(
        part_of(attacking_at("C3", range(4), 4), name="Low"),
        part_of(attacking_at("E5", range(4), 4), name="High"),
        part_of(attacking_at("G4", range(4), 4), name="Middle"),
        bar_durations=(4,),
    )

    root = first_configuration(score)

    assert [leaf.streams[0].part_name for leaf in root.children] == ["High", "Middle", "Low"]


def test_planes_of_equal_register_are_ordered_by_their_first_stream() -> None:
    # Both parts have the mean pitch D4: C4 with E4, and D4 alone, never attacking together.
    first = [event(0, 2, "C4"), event(2, 2, "E4")]
    second = [event(1, 1, "D4"), event(3, 1, "D4")]
    score = score_of(part_of(first), part_of(second), bar_durations=(4,))

    root = first_configuration(score)

    assert [leaf.streams[0].part_number for leaf in root.children] == [1, 2]


def test_a_phrase_without_attacks_is_refused_with_a_domain_error() -> None:
    score = score_of(part_of([]), bar_durations=(4,))

    with pytest.raises(SilentPhraseError, match="Phrase 1, bars 1 to 1"):
        analyze(score)
