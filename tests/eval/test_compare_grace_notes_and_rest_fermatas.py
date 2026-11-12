"""Spec 001d, criteria 30 and 31: `compare_scores` reports grace notes and rest fermatas."""

from fractions import Fraction

import pytest
from tests.core_builders import event, grace_note, part_of, rest_fermata, score_of

from aretz_texture.core.notation import EventPitch, GraceNote, NotatedVoice, TieType
from aretz_texture.core.score import Score
from aretz_texture.eval.round_trip import DifferenceKind, RoundTripRoute, compare_scores

ROUTE = RoundTripRoute.GRAND_STAFF


def base_voice() -> NotatedVoice:
    return NotatedVoice(
        events=(event(0, 2, "C4"), event(4, 4, "E4")),
        grace_notes=(grace_note(0, "B3"), grace_note(4, "G4", "E4")),
        rest_fermatas=(rest_fermata(2, 2),),
    )


def score_with(voice: NotatedVoice) -> Score:
    return score_of(part_of(voice, name="Soprano"), part_of([event(0, 8, "C3")], name="Bass"))


def kinds_and_places(original: NotatedVoice, returned: NotatedVoice) -> list[tuple[object, ...]]:
    differences = compare_scores(score_with(original), score_with(returned), ROUTE)
    return [(d.kind, d.part_number, d.voice_number, d.onset) for d in differences]


def test_a_score_with_grace_notes_and_rest_fermatas_compared_with_itself_has_no_differences() -> (
    None
):
    score = score_with(base_voice())

    assert compare_scores(score, score, ROUTE) == ()


def test_a_removed_grace_note_is_one_grace_note_difference() -> None:
    returned = base_voice().model_copy(update={"grace_notes": (base_voice().grace_notes[1],)})

    assert kinds_and_places(base_voice(), returned) == [
        (DifferenceKind.GRACE_NOTE, 1, 1, Fraction(0))
    ]


def test_an_added_grace_note_is_one_grace_note_difference() -> None:
    original = base_voice().model_copy(update={"grace_notes": (base_voice().grace_notes[1],)})

    assert kinds_and_places(original, base_voice()) == [
        (DifferenceKind.GRACE_NOTE, 1, 1, Fraction(0))
    ]


def altered(grace: GraceNote, change: str) -> GraceNote:
    changes: dict[str, dict[str, object]] = {
        "pitch": {"pitches": grace_note(0, "C4").pitches},
        "value": {"notated_value": Fraction(1, 4)},
        "slash": {"slash": not grace.slash},
        "tie": {"pitches": (EventPitch(pitch=grace.pitches[0].pitch, tie=TieType.START),)},
    }
    return grace.model_copy(update=changes[change])


@pytest.mark.parametrize("change", ["pitch", "value", "slash", "tie"])
def test_an_altered_grace_note_is_one_grace_note_difference(change: str) -> None:
    original = base_voice()
    first, second = original.grace_notes
    returned = original.model_copy(update={"grace_notes": (altered(first, change), second)})

    assert kinds_and_places(original, returned) == [(DifferenceKind.GRACE_NOTE, 1, 1, Fraction(0))]


def test_grace_notes_at_one_onset_in_another_order_are_one_grace_note_difference() -> None:
    original = base_voice().model_copy(
        update={"grace_notes": (grace_note(4, "G4"), grace_note(4, "E4"))}
    )
    returned = original.model_copy(update={"grace_notes": tuple(reversed(original.grace_notes))})

    assert kinds_and_places(original, returned) == [(DifferenceKind.GRACE_NOTE, 1, 1, Fraction(4))]


def test_a_removed_rest_fermata_is_one_rest_fermata_difference() -> None:
    returned = base_voice().model_copy(update={"rest_fermatas": ()})

    assert kinds_and_places(base_voice(), returned) == [
        (DifferenceKind.REST_FERMATA, 1, 1, Fraction(2))
    ]


def test_an_added_rest_fermata_is_one_rest_fermata_difference() -> None:
    original = base_voice().model_copy(update={"rest_fermatas": ()})

    assert kinds_and_places(original, base_voice()) == [
        (DifferenceKind.REST_FERMATA, 1, 1, Fraction(2))
    ]


def test_a_rest_fermata_with_another_duration_is_one_rest_fermata_difference() -> None:
    returned = base_voice().model_copy(update={"rest_fermatas": (rest_fermata(2, 1),)})

    assert kinds_and_places(base_voice(), returned) == [
        (DifferenceKind.REST_FERMATA, 1, 1, Fraction(2))
    ]


def test_the_description_of_a_grace_note_difference_names_the_bar() -> None:
    returned = base_voice().model_copy(update={"grace_notes": (base_voice().grace_notes[0],)})

    differences = compare_scores(score_with(base_voice()), score_with(returned), ROUTE)

    assert "bar 2" in differences[0].description
