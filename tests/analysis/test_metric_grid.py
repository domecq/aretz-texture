from fractions import Fraction

import pytest
from tests.core_builders import event, part_of, score_of

from aretz_texture.analysis.metric_grid import (
    tactus_at,
    tactus_duration,
    tactus_label,
    tactus_spans,
)
from aretz_texture.core.score import Bar, Score, TimeSignatureChange
from aretz_texture.core.texture import TimeSpan


def meter(numerator: int, denominator: int, onset: int = 0) -> TimeSignatureChange:
    return TimeSignatureChange(onset=Fraction(onset), numerator=numerator, denominator=denominator)


def span(onset: int | Fraction, end: int | Fraction) -> TimeSpan:
    return TimeSpan(onset=Fraction(onset), end=Fraction(end))


def whole_score_spans(score: Score) -> list[tuple[Fraction, Fraction]]:
    whole = span(0, score.end())
    return [(tactus.onset, tactus.end) for tactus in tactus_spans(score, whole)]


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [
        (4, 4, Fraction(1)),
        (3, 4, Fraction(1)),
        (3, 2, Fraction(2)),
        (2, 2, Fraction(2)),
        (12, 8, Fraction(3, 2)),
        (6, 8, Fraction(3, 2)),
        (9, 8, Fraction(3, 2)),
    ],
)
def test_tactus_duration_is_the_beat_dotted_in_compound_meters(
    numerator: int, denominator: int, expected: Fraction
) -> None:
    assert tactus_duration(meter(numerator, denominator)) == expected


def test_a_pickup_of_one_quarter_is_one_span_labeled_tactus_4_of_bar_0() -> None:
    score = score_of(part_of([event(0, 1)]), bar_durations=(1, 4, 4))

    spans = tactus_spans(score, span(0, 9))

    assert spans[0] == span(0, 1)
    assert tactus_label(score, spans[0]) == "bar 0, tactus 4"
    assert [(s.onset, s.end) for s in spans[1:3]] == [(1, 2), (2, 3)]
    assert tactus_label(score, spans[1]) == "bar 1, tactus 1"
    assert len(spans) == 9


def test_a_pickup_of_three_eighths_has_a_short_first_span_on_the_last_beats() -> None:
    score = score_of(part_of([event(0, 1)]), bar_durations=(Fraction(3, 2), 4))

    spans = tactus_spans(score, span(0, Fraction(3, 2)))

    assert spans == (span(0, Fraction(1, 2)), span(Fraction(1, 2), Fraction(3, 2)))
    assert [tactus_label(score, s) for s in spans] == ["bar 0, tactus 3", "bar 0, tactus 4"]


def test_a_final_short_bar_is_tiled_from_its_onset() -> None:
    score = score_of(part_of([event(0, 1)]), bar_durations=(4, Fraction(5, 2)))

    spans = tactus_spans(score, span(4, Fraction(13, 2)))

    assert [(s.onset, s.end) for s in spans] == [
        (4, 5),
        (5, 6),
        (6, Fraction(13, 2)),
    ]


def test_spans_are_clipped_to_the_requested_span() -> None:
    score = score_of(part_of([event(0, 1)]))

    spans = tactus_spans(score, span(Fraction(3, 2), Fraction(5, 2)))

    assert spans == (span(Fraction(3, 2), 2), span(2, Fraction(5, 2)))


def test_a_span_ending_on_a_beat_does_not_include_the_next_tactus() -> None:
    score = score_of(part_of([event(0, 1)]))

    assert tactus_spans(score, span(1, 2)) == (span(1, 2),)


def test_each_bar_is_tiled_with_the_time_signature_in_effect() -> None:
    score = score_of(
        part_of([event(0, 1)]),
        bar_durations=(4, 3, 6),
        time_signatures=(meter(4, 4), meter(3, 4, 4), meter(3, 2, 7)),
    )

    assert whole_score_spans(score) == [
        *[(Fraction(n), Fraction(n + 1)) for n in range(7)],
        (Fraction(7), Fraction(9)),
        (Fraction(9), Fraction(11)),
        (Fraction(11), Fraction(13)),
    ]


def test_compound_meter_bars_have_four_dotted_beats_labeled_one_to_four() -> None:
    score = score_of(part_of([event(0, 1)]), bar_durations=(6,), time_signatures=(meter(12, 8),))

    spans = tactus_spans(score, span(0, 6))

    assert [s.end - s.onset for s in spans] == [Fraction(3, 2)] * 4
    assert [tactus_label(score, s) for s in spans] == [f"bar 1, tactus {n}" for n in range(1, 5)]


def test_the_second_piece_of_a_split_bar_continues_the_numbering_of_its_virtual_bar() -> None:
    split_score = Score(
        bars=(
            Bar(number=1, onset=Fraction(0), duration=Fraction(4)),
            Bar(number=2, onset=Fraction(4), duration=Fraction(2)),
            Bar(number=2, onset=Fraction(6), duration=Fraction(2)),
            Bar(number=3, onset=Fraction(8), duration=Fraction(4)),
        ),
        time_signatures=(meter(4, 4),),
        parts=(part_of([event(0, 1)]),),
    )

    spans = tactus_spans(split_score, span(4, 12))

    assert [tactus_label(split_score, s) for s in spans] == [
        *[f"bar 2, tactus {n}" for n in (1, 2, 3, 4)],
        *[f"bar 3, tactus {n}" for n in (1, 2, 3, 4)],
    ]


def test_the_tactus_at_a_moment_is_that_of_the_meter_of_its_bar() -> None:
    score = score_of(
        part_of([event(0, 4, "C4")]),
        bar_durations=(4, 6),
        time_signatures=(meter(4, 4), meter(3, 2, onset=4)),
    )

    assert tactus_at(score, Fraction(3)) == 1
    assert tactus_at(score, Fraction(4)) == 2
    assert tactus_at(score, Fraction(19, 2)) == 2
