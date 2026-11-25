from fractions import Fraction

from tests.core_builders import (
    divided_event,
    event,
    grace_note,
    part_of,
    rest_fermata,
    score_of,
    spelled_pitch,
)

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.core.notation import NotatedVoice, TieType
from aretz_texture.core.texture import StreamReference, TimeSpan

WHOLE = TimeSpan(onset=Fraction(0), end=Fraction(8))
FIRST_STREAM = StreamReference(part_number=1, voice_number=1, part_name="Soprano")


def test_every_untied_event_is_an_attack_with_its_onset() -> None:
    score = score_of(part_of([event(0, 2, "C4"), event(2, 2, "D4")], name="Soprano"))

    attacks = voice_attacks(score, FIRST_STREAM, WHOLE)

    assert [(a.onset, a.pitches) for a in attacks] == [
        (Fraction(0), (spelled_pitch("C4"),)),
        (Fraction(2), (spelled_pitch("D4"),)),
    ]
    assert all(attack.stream == FIRST_STREAM for attack in attacks)


def test_an_event_whose_pitches_all_continue_a_tie_is_not_an_attack() -> None:
    score = score_of(
        part_of(
            [
                event(0, 2, "C4", tie=TieType.START),
                event(2, 1, "C4", tie=TieType.CONTINUE),
                event(3, 1, "C4", tie=TieType.STOP),
                event(4, 4, "D4"),
            ],
            name="Soprano",
        )
    )

    attacks = voice_attacks(score, FIRST_STREAM, WHOLE)

    assert [a.onset for a in attacks] == [0, 4]


def test_a_divided_event_keeps_only_its_newly_attacked_pitches() -> None:
    score = score_of(
        part_of(
            [
                divided_event(0, 2, ("E4", TieType.START), ("C4", None)),
                divided_event(2, 2, ("E4", TieType.STOP), ("D4", None)),
            ],
            name="Soprano",
        )
    )

    attacks = voice_attacks(score, FIRST_STREAM, WHOLE)

    assert [a.pitches for a in attacks] == [
        (spelled_pitch("E4"), spelled_pitch("C4")),
        (spelled_pitch("D4"),),
    ]


def test_grace_notes_and_rest_fermatas_are_not_attacks() -> None:
    voice = NotatedVoice(
        events=(event(2, 2, "C4"),),
        grace_notes=(grace_note(2, "D4"),),
        rest_fermatas=(rest_fermata(0, 2),),
    )
    score = score_of(part_of(voice, name="Soprano"))

    attacks = voice_attacks(score, FIRST_STREAM, WHOLE)

    assert [(a.onset, a.pitches) for a in attacks] == [(Fraction(2), (spelled_pitch("C4"),))]


def test_only_events_with_an_onset_inside_the_span_are_attacks() -> None:
    score = score_of(part_of([event(n, 1, "C4") for n in range(8)], name="Soprano"))

    attacks = voice_attacks(score, FIRST_STREAM, TimeSpan(onset=Fraction(2), end=Fraction(5)))

    assert [a.onset for a in attacks] == [2, 3, 4]


def test_attacks_are_read_from_the_voice_of_the_stream() -> None:
    score = score_of(part_of([event(0, 8, "C4")], [event(0, 4, "G3"), event(4, 4, "A3")]))

    attacks = voice_attacks(
        score, StreamReference(part_number=1, voice_number=2, part_name=None), WHOLE
    )

    assert [a.pitches[0] for a in attacks] == [spelled_pitch("G3"), spelled_pitch("A3")]


def test_stream_references_list_every_voice_of_every_part_in_score_order() -> None:
    score = score_of(
        part_of([event(0, 8)], [event(0, 8)], name="Violin"),
        part_of([event(0, 8)]),
    )

    assert stream_references(score) == (
        StreamReference(part_number=1, voice_number=1, part_name="Violin"),
        StreamReference(part_number=1, voice_number=2, part_name="Violin"),
        StreamReference(part_number=2, voice_number=1, part_name=None),
    )
