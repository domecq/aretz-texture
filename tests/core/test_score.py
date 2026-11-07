from fractions import Fraction

import pytest
from pydantic import ValidationError

from aretz_texture.core.notation import EventPitch, NotatedVoice, NoteEvent, SpelledPitch
from aretz_texture.core.score import (
    Bar,
    IngestedScore,
    KeySignatureChange,
    Part,
    Score,
    TimeSignatureChange,
)

FOUR_FOUR = TimeSignatureChange(onset=Fraction(0), numerator=4, denominator=4)
NO_SHARPS = KeySignatureChange(onset=Fraction(0), sharps=0)


def note_event(onset: int, duration: int = 1) -> NoteEvent:
    middle_c = SpelledPitch(step="C", alter=0, octave=4)
    return NoteEvent(
        onset=Fraction(onset),
        duration=Fraction(duration),
        pitches=(EventPitch(pitch=middle_c, tie=None),),
        fermata=False,
    )


def voice_of(*events: NoteEvent) -> NotatedVoice:
    return NotatedVoice(events=events)


def part_of(*voices: NotatedVoice) -> Part:
    return Part(name=None, instrument_name=None, key_signatures=(NO_SHARPS,), voices=voices)


def bars_of(*durations: int) -> tuple[Bar, ...]:
    bars: list[Bar] = []
    onset = 0
    for number, duration in enumerate(durations):
        bars.append(Bar(number=number, onset=Fraction(onset), duration=Fraction(duration)))
        onset += duration
    return tuple(bars)


def score_of(*parts: Part, bars: tuple[Bar, ...] | None = None) -> Score:
    return Score(
        bars=bars if bars is not None else bars_of(4, 4),
        time_signatures=(FOUR_FOUR,),
        parts=parts,
    )


def test_models_are_immutable() -> None:
    part = part_of(voice_of(note_event(0)))
    score = score_of(part)
    ingested = IngestedScore(score=score, has_lyrics=False)

    with pytest.raises(ValidationError):
        part.name = "Soprano"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        score.parts = ()  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ingested.has_lyrics = True  # type: ignore[misc]
    with pytest.raises(ValidationError):
        score.bars[0].number = 5  # type: ignore[misc]


def test_part_rejects_zero_notated_voices() -> None:
    with pytest.raises(ValidationError):
        part_of()


def test_part_rejects_a_last_notated_voice_without_content_when_there_are_several() -> None:
    with pytest.raises(ValidationError):
        part_of(voice_of(note_event(0)), voice_of())


def test_part_accepts_a_single_notated_voice_without_content() -> None:
    part = part_of(voice_of())

    assert len(part.voices) == 1


def test_part_rejects_a_first_key_signature_after_onset_zero() -> None:
    late = KeySignatureChange(onset=Fraction(1), sharps=2)

    with pytest.raises(ValidationError):
        Part(name=None, instrument_name=None, key_signatures=(late,), voices=(voice_of(),))


def test_score_rejects_zero_parts() -> None:
    with pytest.raises(ValidationError):
        score_of()


def test_score_rejects_bars_that_do_not_start_at_zero() -> None:
    bars = (Bar(number=1, onset=Fraction(1), duration=Fraction(4)),)

    with pytest.raises(ValidationError):
        score_of(part_of(voice_of()), bars=bars)


def test_score_rejects_bars_that_are_not_contiguous() -> None:
    bars = (
        Bar(number=1, onset=Fraction(0), duration=Fraction(4)),
        Bar(number=2, onset=Fraction(5), duration=Fraction(4)),
    )

    with pytest.raises(ValidationError):
        score_of(part_of(voice_of()), bars=bars)


def test_score_rejects_an_event_ending_after_the_last_bar() -> None:
    part = part_of(voice_of(note_event(7, duration=2)))

    with pytest.raises(ValidationError):
        score_of(part)


def test_score_accepts_an_event_ending_exactly_at_the_last_bar() -> None:
    part = part_of(voice_of(note_event(7, duration=1)))

    score = score_of(part)

    assert len(score.parts) == 1


def test_score_rejects_a_first_time_signature_after_onset_zero() -> None:
    late = TimeSignatureChange(onset=Fraction(4), numerator=3, denominator=4)

    with pytest.raises(ValidationError):
        Score(bars=bars_of(4, 4), time_signatures=(late,), parts=(part_of(voice_of()),))


def test_pickup_duration_is_the_length_of_a_short_first_bar() -> None:
    score = score_of(part_of(voice_of()), bars=bars_of(1, 4, 4))

    assert score.pickup_duration() == Fraction(1)


def test_pickup_duration_is_zero_when_the_first_bar_is_complete() -> None:
    score = score_of(part_of(voice_of()), bars=bars_of(4, 4))

    assert score.pickup_duration() == Fraction(0)
