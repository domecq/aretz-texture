from fractions import Fraction

from tests.core_builders import divided_event, event, grace_note, part_of, rest_fermata, score_of

from aretz_texture.analysis.sounding_notes import sounding_notes
from aretz_texture.core.notation import NotatedVoice, TieType
from aretz_texture.core.score import Score
from aretz_texture.core.texture import StreamReference, TimeSpan

VOICE = StreamReference(part_number=1, voice_number=1, part_name=None)


def span(onset: int, end: int) -> TimeSpan:
    return TimeSpan(onset=Fraction(onset), end=Fraction(end))


def described(
    score: Score, window: TimeSpan, stream: StreamReference = VOICE
) -> list[tuple[str, Fraction, Fraction]]:
    """Describe the notes as (pitch, onset, end) with the pitch written as step, alter, octave."""
    return [
        (f"{note.pitch.step}{note.pitch.alter:+d}/{note.pitch.octave}", note.onset, note.end)
        for note in sounding_notes(score, stream, window)
    ]


def test_each_event_without_ties_is_one_note_from_its_onset_to_its_end() -> None:
    score = score_of(part_of([event(0, 1, "C4"), event(1, 2, "D4")]))

    assert described(score, span(0, 8)) == [("C+0/4", 0, 1), ("D+0/4", 1, 3)]


def test_a_tie_chain_of_start_continue_and_stop_is_one_note() -> None:
    score = score_of(
        part_of(
            [
                event(0, 2, "C4", tie=TieType.START),
                event(2, 2, "C4", tie=TieType.CONTINUE),
                event(4, 1, "C4", tie=TieType.STOP),
            ]
        )
    )

    assert described(score, span(0, 8)) == [("C+0/4", 0, 5)]


def test_a_tie_joins_only_the_pitch_that_is_tied_in_a_divided_event() -> None:
    score = score_of(
        part_of(
            [
                divided_event(0, 2, ("E4", TieType.START), ("C4", None)),
                divided_event(2, 2, ("E4", TieType.STOP), ("D4", None)),
            ]
        )
    )

    assert sorted(described(score, span(0, 8))) == [
        ("C+0/4", 0, 2),
        ("D+0/4", 2, 4),
        ("E+0/4", 0, 4),
    ]


def test_each_pitch_of_a_divided_event_is_kept_apart_with_doublings() -> None:
    score = score_of(part_of([divided_event(0, 1, ("C4", None), ("C4", None), ("A3", None))]))

    assert len(sounding_notes(score, VOICE, span(0, 8))) == 3


def test_the_same_pitch_attacked_again_after_a_tie_stop_is_a_new_note() -> None:
    score = score_of(
        part_of(
            [
                event(0, 1, "C4", tie=TieType.START),
                event(1, 1, "C4", tie=TieType.STOP),
                event(2, 1, "C4"),
            ]
        )
    )

    assert described(score, span(0, 8)) == [("C+0/4", 0, 2), ("C+0/4", 2, 3)]


def test_a_chain_that_crosses_the_end_of_the_phrase_is_clipped_to_it() -> None:
    score = score_of(
        part_of(
            [
                event(0, 2, "C4"),
                event(2, 2, "D4", tie=TieType.START),
                event(4, 2, "D4", tie=TieType.STOP),
            ]
        ),
        bar_durations=(4, 4),
    )

    assert described(score, span(0, 5)) == [("C+0/4", 0, 2), ("D+0/4", 2, 5)]


def test_a_chain_that_started_before_the_phrase_is_clipped_to_its_onset() -> None:
    score = score_of(
        part_of(
            [
                event(2, 2, "D4", tie=TieType.START),
                event(4, 2, "D4", tie=TieType.STOP),
                event(6, 2, "E4"),
            ]
        )
    )

    assert described(score, span(3, 8)) == [("D+0/4", 3, 6), ("E+0/4", 6, 8)]


def test_events_outside_the_phrase_give_no_notes() -> None:
    score = score_of(part_of([event(0, 2, "C4"), event(6, 2, "D4")]))

    assert described(score, span(2, 6)) == []


def test_grace_notes_and_rest_fermatas_are_ignored() -> None:
    voice = NotatedVoice(
        events=(event(0, 1, "C4"), event(2, 1, "D4")),
        grace_notes=(grace_note(2, "B3"),),
        rest_fermatas=(rest_fermata(1, 1),),
    )
    score = score_of(part_of(voice))

    assert described(score, span(0, 8)) == [("C+0/4", 0, 1), ("D+0/4", 2, 3)]


def test_notes_of_other_voices_and_parts_are_not_included() -> None:
    score = score_of(
        part_of([event(0, 4, "C4")], [event(0, 4, "E4")]), part_of([event(0, 4, "G4")])
    )
    second_voice = StreamReference(part_number=1, voice_number=2, part_name=None)

    assert described(score, span(0, 8), second_voice) == [("E+0/4", 0, 4)]


def test_notes_carry_their_stream() -> None:
    score = score_of(part_of([event(0, 4, "C4")]))

    assert [note.stream for note in sounding_notes(score, VOICE, span(0, 8))] == [VOICE]
