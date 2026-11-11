"""Criterion 26: `compare_scores` reports exactly one difference per single change."""

from fractions import Fraction

import pytest
from tests.core_builders import divided_event, event, part_of, score_of

from aretz_texture.core.notation import NotatedVoice, NoteEvent, TieType
from aretz_texture.core.score import (
    KeySignatureChange,
    Part,
    Score,
    TimeSignatureChange,
)
from aretz_texture.eval.round_trip import (
    DifferenceKind,
    RoundTripRoute,
    compare_scores,
    without_part_metadata,
)

ROUTE = RoundTripRoute.FULL_SCORE


def melody() -> list[NoteEvent]:
    return [event(0, 2, "C4"), event(2, 2, "D4"), divided_event(4, 4, ("E4", None), ("C4", None))]


def bass() -> list[NoteEvent]:
    return [event(0, 4, "C3"), event(4, 4, "G2")]


def base_score() -> Score:
    return score_of(
        part_of(melody(), name="Upper", instrument_name="Voice"),
        part_of(bass(), name="Lower", instrument_name="Voice"),
    )


def with_part(score: Score, index: int, part: Part) -> Score:
    parts = list(score.parts)
    parts[index] = part
    return score.model_copy(update={"parts": tuple(parts)})


def with_first_part_events(score: Score, events: list[NoteEvent]) -> Score:
    part = score.parts[0].model_copy(update={"voices": (NotatedVoice(events=tuple(events)),)})
    return with_part(score, 0, part)


def test_a_score_compared_with_itself_has_no_differences() -> None:
    score = base_score()

    assert compare_scores(score, score, ROUTE) == ()


def test_a_removed_event_is_one_missing_event() -> None:
    changed = with_first_part_events(base_score(), [melody()[0], melody()[2]])

    differences = compare_scores(base_score(), changed, ROUTE)

    assert [(d.kind, d.part_number, d.voice_number, d.onset) for d in differences] == [
        (DifferenceKind.MISSING_EVENT, 1, 1, Fraction(2))
    ]


def test_an_added_event_is_one_extra_event() -> None:
    original = with_first_part_events(base_score(), [melody()[0], melody()[2]])

    differences = compare_scores(original, base_score(), ROUTE)

    assert [(d.kind, d.part_number, d.voice_number, d.onset) for d in differences] == [
        (DifferenceKind.EXTRA_EVENT, 1, 1, Fraction(2))
    ]


def altered(events: list[NoteEvent]) -> Score:
    return with_first_part_events(base_score(), events)


@pytest.mark.parametrize(
    "replacement",
    [
        pytest.param(event(2, 2, "D#4"), id="pitch spelling"),
        pytest.param(event(2, 1, "D4"), id="duration"),
        pytest.param(event(2, 2, "D4", tie=TieType.START), id="tie"),
        pytest.param(event(2, 2, "D4", fermata=True), id="fermata"),
    ],
)
def test_a_changed_event_is_one_altered_event_at_its_onset(replacement: NoteEvent) -> None:
    changed = altered([melody()[0], replacement, melody()[2]])

    differences = compare_scores(base_score(), changed, ROUTE)

    assert [(d.kind, d.onset) for d in differences] == [(DifferenceKind.ALTERED_EVENT, Fraction(2))]


def test_a_pitch_added_to_a_divided_event_is_one_altered_event() -> None:
    wider = divided_event(4, 4, ("E4", None), ("C4", None), ("A3", None))

    differences = compare_scores(base_score(), altered([melody()[0], melody()[1], wider]), ROUTE)

    assert [(d.kind, d.onset) for d in differences] == [(DifferenceKind.ALTERED_EVENT, Fraction(4))]


def test_a_pitch_removed_from_a_divided_event_is_one_altered_event() -> None:
    narrower = event(4, 4, "E4")

    differences = compare_scores(base_score(), altered([melody()[0], melody()[1], narrower]), ROUTE)

    assert [(d.kind, d.onset) for d in differences] == [(DifferenceKind.ALTERED_EVENT, Fraction(4))]


def test_a_changed_part_name_is_one_part_name_difference() -> None:
    changed = with_part(base_score(), 1, base_score().parts[1].model_copy(update={"name": "Bass"}))

    differences = compare_scores(base_score(), changed, ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [(DifferenceKind.PART_NAME, 2)]


def test_a_changed_instrument_name_is_one_instrument_name_difference() -> None:
    changed = with_part(
        base_score(), 0, base_score().parts[0].model_copy(update={"instrument_name": "Oboe"})
    )

    differences = compare_scores(base_score(), changed, ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [(DifferenceKind.INSTRUMENT_NAME, 1)]


def test_an_added_part_is_one_part_count_difference() -> None:
    larger = score_of(*base_score().parts, part_of([event(0, 8, "C2")], name="Extra"))

    differences = compare_scores(base_score(), larger, ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [(DifferenceKind.PART_COUNT, None)]


def test_an_added_notated_voice_is_one_voice_count_difference() -> None:
    two_voices = part_of(melody(), [event(0, 2, "G3")], name="Upper", instrument_name="Voice")

    differences = compare_scores(base_score(), with_part(base_score(), 0, two_voices), ROUTE)

    assert [(d.kind, d.part_number, d.voice_number) for d in differences] == [
        (DifferenceKind.VOICE_COUNT, 1, None)
    ]


def test_a_changed_bar_is_one_bars_difference() -> None:
    original = base_score()
    renumbered = original.bars[1].model_copy(update={"number": 7})
    changed = original.model_copy(update={"bars": (original.bars[0], renumbered)})

    differences = compare_scores(original, changed, ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [(DifferenceKind.BARS, None)]


def test_a_changed_key_signature_is_one_key_signatures_difference() -> None:
    sharps = [KeySignatureChange(onset=Fraction(0), sharps=2)]
    keyed = part_of(melody(), name="Upper", instrument_name="Voice", key_signatures=sharps)

    differences = compare_scores(base_score(), with_part(base_score(), 0, keyed), ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [(DifferenceKind.KEY_SIGNATURES, 1)]


def test_a_changed_time_signature_is_one_time_signatures_difference() -> None:
    three_four = (TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=4),)
    changed = base_score().model_copy(update={"time_signatures": three_four})

    differences = compare_scores(base_score(), changed, ROUTE)

    assert [(d.kind, d.part_number) for d in differences] == [
        (DifferenceKind.TIME_SIGNATURES, None)
    ]


def test_a_part_name_equal_to_the_instrument_name_equals_no_name() -> None:
    unnamed = part_of(bass(), name=None, instrument_name="Piano")
    named_after_instrument = part_of(bass(), name="Piano", instrument_name="Piano")

    differences = compare_scores(score_of(unnamed), score_of(named_after_instrument), ROUTE)

    assert differences == ()


def test_a_difference_names_the_bar_of_the_event() -> None:
    changed = altered([melody()[0], event(2, 2, "D#4"), melody()[2]])
    changed_in_second_bar = altered([melody()[0], melody()[1], event(4, 4, "E4")])

    first = compare_scores(base_score(), changed, ROUTE)
    second = compare_scores(base_score(), changed_in_second_bar, ROUTE)

    assert "bar 1" in first[0].description
    assert "bar 2" in second[0].description


def test_a_difference_records_the_route() -> None:
    changed = altered([melody()[0], melody()[2]])

    differences = compare_scores(base_score(), changed, RoundTripRoute.GRAND_STAFF)

    assert differences[0].route is RoundTripRoute.GRAND_STAFF


def test_without_part_metadata_clears_every_part_and_instrument_name() -> None:
    stripped = without_part_metadata(base_score())

    assert [(part.name, part.instrument_name) for part in stripped.parts] == [
        (None, None),
        (None, None),
    ]
    assert stripped.parts[0].voices == base_score().parts[0].voices
