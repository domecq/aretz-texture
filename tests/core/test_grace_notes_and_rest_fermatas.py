"""Spec 001d, section 3.2: the grace note and rest fermata models and their invariants."""

from fractions import Fraction

import pytest
from pydantic import ValidationError
from tests.core_builders import event, grace_note, part_of, rest_fermata, score_of

from aretz_texture.core.notation import GraceNote, NotatedVoice, RestFermata


def test_a_voice_built_as_in_spec_001a_has_no_grace_notes_or_rest_fermatas() -> None:
    voice = NotatedVoice(events=(event(0, 1),))

    assert voice.grace_notes == ()
    assert voice.rest_fermatas == ()


def test_grace_note_rejects_a_notated_value_that_is_not_positive() -> None:
    with pytest.raises(ValidationError):
        grace_note(0, "C4", notated_value=0)


def test_grace_note_rejects_empty_pitches() -> None:
    with pytest.raises(ValidationError):
        GraceNote(onset=Fraction(0), pitches=(), notated_value=Fraction(1, 2), slash=True)


def test_grace_note_rejects_pitches_that_are_not_ordered_from_highest_to_lowest() -> None:
    with pytest.raises(ValidationError):
        grace_note(0, "C4", "E4")


def test_rest_fermata_rejects_a_duration_that_is_not_positive() -> None:
    with pytest.raises(ValidationError):
        RestFermata(onset=Fraction(0), duration=Fraction(0))


def test_models_of_001d_are_immutable() -> None:
    with pytest.raises(ValidationError):
        grace_note(0, "C4").slash = False  # type: ignore[misc]
    with pytest.raises(ValidationError):
        rest_fermata(0, 1).duration = Fraction(2)  # type: ignore[misc]


def test_notated_voice_rejects_grace_notes_that_are_not_sorted_by_onset() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(events=(), grace_notes=(grace_note(2, "C4"), grace_note(1, "C4")))


def test_notated_voice_keeps_grace_notes_at_the_same_onset_in_source_order() -> None:
    first, second = grace_note(1, "E5"), grace_note(1, "D5")

    voice = NotatedVoice(events=(event(1, 1),), grace_notes=(first, second))

    assert voice.grace_notes == (first, second)


def test_notated_voice_rejects_a_grace_note_inside_an_event() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(events=(event(0, 4),), grace_notes=(grace_note(1, "C4"),))


def test_notated_voice_accepts_a_grace_note_at_the_end_of_an_event() -> None:
    voice = NotatedVoice(events=(event(0, 1), event(2, 1)), grace_notes=(grace_note(1, "C4"),))

    assert len(voice.grace_notes) == 1


def test_notated_voice_rejects_a_grace_note_inside_a_rest_fermata() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(
            events=(), rest_fermatas=(rest_fermata(0, 4),), grace_notes=(grace_note(1, "C4"),)
        )


def test_notated_voice_rejects_rest_fermatas_that_are_not_sorted() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(events=(), rest_fermatas=(rest_fermata(2, 1), rest_fermata(0, 1)))


def test_notated_voice_rejects_rest_fermatas_that_overlap() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 2), rest_fermata(1, 1)))


def test_notated_voice_rejects_a_rest_fermata_that_overlaps_an_event() -> None:
    with pytest.raises(ValidationError):
        NotatedVoice(events=(event(1, 2),), rest_fermatas=(rest_fermata(0, 2),))


def test_notated_voice_accepts_a_rest_fermata_in_the_gap_between_events() -> None:
    voice = NotatedVoice(events=(event(0, 1), event(3, 1)), rest_fermatas=(rest_fermata(1, 2),))

    assert voice.rest_fermatas == (rest_fermata(1, 2),)


def test_a_voice_with_only_a_rest_fermata_has_content() -> None:
    assert NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),)).has_content()


def test_a_voice_with_only_a_grace_note_has_content() -> None:
    assert NotatedVoice(events=(), grace_notes=(grace_note(0, "C4"),)).has_content()


def test_an_empty_voice_has_no_content() -> None:
    assert not NotatedVoice(events=()).has_content()


def test_part_accepts_a_last_notated_voice_that_only_has_a_rest_fermata() -> None:
    only_rest_fermata = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),))

    part = part_of([event(0, 1)], only_rest_fermata)

    assert len(part.voices) == 2


def test_within_keeps_only_what_starts_in_the_span() -> None:
    voice = NotatedVoice(
        events=(event(0, 1), event(4, 1)),
        grace_notes=(grace_note(0, "C4"), grace_note(4, "D4")),
        rest_fermatas=(rest_fermata(2, 2),),
    )

    second_bar = voice.within(Fraction(4), Fraction(8))

    assert second_bar == NotatedVoice(events=(event(4, 1),), grace_notes=(grace_note(4, "D4"),))


def test_score_rejects_a_grace_note_at_the_end_of_the_last_bar() -> None:
    voice = NotatedVoice(events=(event(0, 4),), grace_notes=(grace_note(8, "C4"),))

    with pytest.raises(ValidationError):
        score_of(part_of(voice))


def test_score_rejects_a_rest_fermata_ending_after_the_last_bar() -> None:
    voice = NotatedVoice(events=(event(0, 4),), rest_fermatas=(rest_fermata(4, 8),))

    with pytest.raises(ValidationError):
        score_of(part_of(voice))
