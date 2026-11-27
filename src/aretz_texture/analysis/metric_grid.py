"""The metric grid: the tactus of each bar and its tactus spans (spec 002, section 3.4)."""

from fractions import Fraction
from itertools import pairwise
from math import floor

from aretz_texture.core.score import QUARTER_LENGTHS_PER_WHOLE_NOTE, Bar, Score, TimeSignatureChange
from aretz_texture.core.texture import TimeSpan

# Numerators whose beat is a dotted note, as in 6/8, 9/8 and 12/8 (music theory, not a setting).
COMPOUND_METER_NUMERATORS = frozenset({6, 9, 12})
SUBDIVISIONS_PER_COMPOUND_BEAT = 3


def tactus_duration(time_signature: TimeSignatureChange) -> Fraction:
    """Return the tactus of a meter in quarter lengths: its beat, dotted in compound meters.

    Args:
        time_signature: The meter.

    Returns:
        The beat: 1 for 4/4 and 3/4, 2 for 3/2 and 2/2, 3/2 for 6/8 and 12/8.
    """
    beat = Fraction(QUARTER_LENGTHS_PER_WHOLE_NOTE, time_signature.denominator)
    if time_signature.numerator in COMPOUND_METER_NUMERATORS:
        return beat * SUBDIVISIONS_PER_COMPOUND_BEAT
    return beat


def tactus_spans(score: Score, span: TimeSpan) -> tuple[TimeSpan, ...]:
    """Return the tactus spans that overlap a span, clipped to it.

    Spans tile each bar from its onset with the time signature in effect at the bar. A first
    bar shorter than its meter, a pickup, is tiled from its end backwards, so that its spans
    fall on the last beats of a virtual complete bar and the first one may be shorter.

    Args:
        score: The score whose bars give the grid.
        span: The stretch of the score.

    Returns:
        The spans in order, each inside `span`.
    """
    clipped: list[TimeSpan] = []
    for index, bar in enumerate(score.bars):
        if bar.onset + bar.duration <= span.onset:
            continue
        if bar.onset >= span.end:
            break
        for tactus in _bar_tactus_spans(score, index):
            onset, end = max(tactus.onset, span.onset), min(tactus.end, span.end)
            if onset < end:
                clipped.append(TimeSpan(onset=onset, end=end))
    return tuple(clipped)


def tactus_at(score: Score, moment: Fraction) -> Fraction:
    """Return the tactus, in quarter lengths, of the bar that holds a moment.

    Args:
        score: The score whose bars and time signatures give the grid.
        moment: A moment inside the score, from 0 up to, not including, its end.

    Returns:
        The tactus of the time signature in effect at the onset of that bar.
    """
    bar = score.bars[_bar_index_at(score, moment)]
    return tactus_duration(_time_signature_at(score, bar.onset))


def tactus_label(score: Score, tactus_span: TimeSpan) -> str:
    """Return the label of a tactus span for explanations, such as "bar 0, tactus 4".

    Tactus spans are numbered from 1 within the virtual complete bar: a pickup takes the last
    numbers, and the second piece of a bar split in two pieces continues the numbering of the
    first.

    Args:
        score: The score whose bars give the grid.
        tactus_span: A span from `tactus_spans`; its onset places the label.

    Returns:
        The bar number as shown in the score and the tactus number in that bar.
    """
    index = _bar_index_at(score, tactus_span.onset)
    bar = score.bars[index]
    tactus = tactus_duration(_time_signature_at(score, bar.onset))
    position_in_virtual_bar = _virtual_bar_start(score, index) + tactus_span.onset - bar.onset
    return f"bar {bar.number}, tactus {floor(position_in_virtual_bar / tactus) + 1}"


def _time_signature_at(score: Score, onset: Fraction) -> TimeSignatureChange:
    in_effect = [change for change in score.time_signatures if change.onset <= onset]
    return in_effect[-1]


def _bar_index_at(score: Score, moment: Fraction) -> int:
    for index, bar in enumerate(score.bars):
        if bar.onset <= moment < bar.onset + bar.duration:
            return index
    message = f"no bar holds the moment {moment}"
    raise ValueError(message)


def _is_pickup(score: Score, index: int) -> bool:
    bar = score.bars[index]
    return index == 0 and bar.duration < _time_signature_at(score, bar.onset).bar_duration()


def _virtual_bar_start(score: Score, index: int) -> Fraction:
    """Return where a bar piece starts inside its virtual complete bar."""
    bar = score.bars[index]
    if _is_pickup(score, index):
        return _time_signature_at(score, bar.onset).bar_duration() - bar.duration
    start = Fraction(0)
    for previous in reversed(score.bars[:index]):
        if previous.number != bar.number:
            break
        start += previous.duration
    return start


def _bar_tactus_spans(score: Score, index: int) -> list[TimeSpan]:
    bar = score.bars[index]
    tactus = tactus_duration(_time_signature_at(score, bar.onset))
    bar_end = bar.onset + bar.duration
    if _is_pickup(score, index):
        return _spans_from_the_end(bar, tactus)
    boundaries = [bar.onset + tactus * step for step in range(floor(bar.duration / tactus) + 1)]
    if boundaries[-1] < bar_end:
        boundaries.append(bar_end)
    return [TimeSpan(onset=a, end=b) for a, b in pairwise(boundaries)]


def _spans_from_the_end(bar: Bar, tactus: Fraction) -> list[TimeSpan]:
    bar_end = bar.onset + bar.duration
    spans: list[TimeSpan] = []
    end = bar_end
    while end > bar.onset:
        onset = max(end - tactus, bar.onset)
        spans.append(TimeSpan(onset=onset, end=end))
        end = onset
    return spans[::-1]
