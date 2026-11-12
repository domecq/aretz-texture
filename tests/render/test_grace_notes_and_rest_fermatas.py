# See ADR 0003: music21 is untyped; tests that build music21 objects follow the boundary rule.
"""Spec 001d, criteria 30 and 31: both renderers keep grace notes and fermatas on rests."""

from collections.abc import Callable
from fractions import Fraction
from pathlib import Path

import pytest
from music21 import expressions, stream
from tests.core_builders import (
    FOUR_FOUR,
    divided_event,
    event,
    grace_note,
    part_of,
    rest_fermata,
    score_of,
)
from tests.music21_builders import parse_score

from aretz_texture.core.errors import UnsupportedScoreError
from aretz_texture.core.grand_staff import PIANO_LAYOUT
from aretz_texture.core.notation import EventPitch, NotatedVoice, TieType
from aretz_texture.core.score import KeySignatureChange, Score, TimeSignatureChange
from aretz_texture.ingest.sources import read_grand_staff_file, read_score
from aretz_texture.render.full_score import write_full_score
from aretz_texture.render.piano_score import write_piano_score

THREE_TWO = TimeSignatureChange(onset=Fraction(0), numerator=3, denominator=2)

Route = Callable[[Score, Path], Score]


def full_score_route(score: Score, path: Path) -> Score:
    write_full_score(score, path)
    return read_score(str(path)).score


def grand_staff_route(score: Score, path: Path) -> Score:
    write_piano_score(score, PIANO_LAYOUT, path)
    return read_grand_staff_file(path, PIANO_LAYOUT)


ROUTES = pytest.mark.parametrize(
    "route", [full_score_route, grand_staff_route], ids=["full_score", "grand_staff"]
)


def four_part_score(
    first_voice: NotatedVoice,
    bar_durations: tuple[int, ...] = (4, 4),
    time_signatures: tuple[TimeSignatureChange, ...] = (FOUR_FOUR,),
) -> Score:
    """Return a four part score whose part 1 has the given voice and the others whole notes."""
    bar_onsets = [sum(bar_durations[:index]) for index in range(len(bar_durations))]
    filler = [
        event(onset, duration, "C3")
        for onset, duration in zip(bar_onsets, bar_durations, strict=True)
    ]
    return score_of(
        part_of(first_voice),
        part_of(filler),
        part_of(filler),
        part_of(filler),
        bar_durations=bar_durations,
        time_signatures=time_signatures,
    )


def tied(grace: NotatedVoice, tie: TieType) -> NotatedVoice:
    pitches = (EventPitch(pitch=grace.grace_notes[0].pitches[0].pitch, tie=tie),)
    return grace.model_copy(
        update={"grace_notes": (grace.grace_notes[0].model_copy(update={"pitches": pitches}),)}
    )


VOICES_WITH_GRACE_NOTES = {
    "before a note": NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")),
        grace_notes=(grace_note(4, "B4", notated_value=Fraction(1, 2)),),
    ),
    "before the first note of the score": NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")), grace_notes=(grace_note(0, "A4"),)
    ),
    "with a sixteenth and no slash": NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")),
        grace_notes=(grace_note(0, "A4", notated_value=Fraction(1, 4), slash=False),),
    ),
    "as a chord": NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")), grace_notes=(grace_note(0, "C5", "E4"),)
    ),
    "several at one onset": NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")),
        grace_notes=(
            grace_note(4, "E5", notated_value=Fraction(1, 4)),
            grace_note(4, "D5", notated_value=Fraction(1, 4)),
            grace_note(4, "C5", notated_value=Fraction(1, 4)),
        ),
    ),
    "inside a gap, before a rest": NotatedVoice(
        events=(event(0, 1, "G4"), event(4, 4, "A4")), grace_notes=(grace_note(2, "B4"),)
    ),
    "at the start of a gap": NotatedVoice(
        events=(event(0, 1, "G4"), event(4, 4, "A4")), grace_notes=(grace_note(1, "B4"),)
    ),
    "before a note after a triplet": NotatedVoice(
        events=(event(0, Fraction(1, 3)), event(Fraction(1, 3), Fraction(1, 3)), event(4, 4)),
        grace_notes=(grace_note(4, "B4"),),
    ),
    "tied to the note it ornaments": tied(
        NotatedVoice(
            events=(event(0, 4, "D5"), event(4, 4, "D5")), grace_notes=(grace_note(0, "D5"),)
        ),
        TieType.START,
    ),
}

VOICES_WITH_REST_FERMATAS = {
    "in a gap between notes": NotatedVoice(
        events=(event(0, 2, "G4"), event(4, 4, "A4")), rest_fermatas=(rest_fermata(2, 2),)
    ),
    "filling a whole bar": NotatedVoice(
        events=(event(4, 4, "A4"),), rest_fermatas=(rest_fermata(0, 4),)
    ),
    "filling a whole last bar": NotatedVoice(
        events=(event(0, 4, "A4"),), rest_fermatas=(rest_fermata(4, 4),)
    ),
    "filling a whole score": NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),)),
    "with plain rests around it": NotatedVoice(
        events=(event(0, 1, "G4"), event(7, 1, "A4")), rest_fermatas=(rest_fermata(2, 1),)
    ),
    "next to another rest fermata": NotatedVoice(
        events=(event(0, 2, "G4"), event(6, 2, "A4")),
        rest_fermatas=(rest_fermata(2, 2), rest_fermata(4, 2)),
    ),
    "before a note": NotatedVoice(events=(event(1, 3, "G4"),), rest_fermatas=(rest_fermata(0, 1),)),
    "on a triplet eighth": NotatedVoice(
        events=(event(0, Fraction(1, 3)), event(Fraction(2, 3), Fraction(1, 3)), event(1, 3)),
        rest_fermatas=(rest_fermata(Fraction(1, 3), Fraction(1, 3)),),
    ),
    "on a whole triplet group": NotatedVoice(
        events=(event(1, 3),),
        rest_fermatas=tuple(rest_fermata(Fraction(index, 3), Fraction(1, 3)) for index in range(3)),
    ),
}


@ROUTES
@pytest.mark.parametrize(
    "voice", VOICES_WITH_GRACE_NOTES.values(), ids=VOICES_WITH_GRACE_NOTES.keys()
)
def test_a_grace_note_survives_the_round_trip(
    route: Route, voice: NotatedVoice, tmp_path: Path
) -> None:
    score = four_part_score(voice)

    returned = route(score, tmp_path / "score.musicxml")

    assert returned.parts[0].voices[0] == voice


@ROUTES
@pytest.mark.parametrize(
    "voice", VOICES_WITH_REST_FERMATAS.values(), ids=VOICES_WITH_REST_FERMATAS.keys()
)
def test_a_rest_fermata_survives_the_round_trip(
    route: Route, voice: NotatedVoice, tmp_path: Path
) -> None:
    score = four_part_score(voice)

    returned = route(score, tmp_path / "score.musicxml")

    assert returned.parts[0].voices[0] == voice


@ROUTES
def test_a_score_with_a_grace_note_and_a_rest_fermata_in_other_parts_is_unchanged(
    route: Route, tmp_path: Path
) -> None:
    score = four_part_score(NotatedVoice(events=(event(0, 4, "G4"), event(4, 4, "G4"))))
    voices = [
        NotatedVoice(events=(event(0, 4, "C3"),), rest_fermatas=(rest_fermata(4, 4),)),
        NotatedVoice(
            events=(event(0, 4, "C3"), event(4, 4, "C3")), grace_notes=(grace_note(0, "D3"),)
        ),
    ]
    parts = (score.parts[0], part_of(voices[0]), part_of(voices[1]), score.parts[3])
    changed = score.model_copy(update={"parts": parts})

    assert route(changed, tmp_path / "score.musicxml") == changed


def test_a_grace_note_is_written_before_the_note_it_ornaments(tmp_path: Path) -> None:
    voice = NotatedVoice(
        events=(event(0, 4, "G4"), event(4, 4, "A4")), grace_notes=(grace_note(4, "B4"),)
    )
    path = tmp_path / "full.musicxml"

    write_full_score(score_of(part_of(voice)), path)

    notes = list(parse_score(path).parts[0].recurse().notes)
    assert [(n.pitches[0].nameWithOctave, n.duration.isGrace) for n in notes] == [
        ("G4", False),
        ("B4", True),
        ("A4", False),
    ]


def test_a_grace_note_in_the_second_notated_voice_belongs_to_it(tmp_path: Path) -> None:
    second = NotatedVoice(events=(event(0, 4, "C4"),), grace_notes=(grace_note(0, "D4"),))
    score = score_of(part_of([event(0, 4, "G4")], second), bar_durations=(4,))

    returned = full_score_route(score, tmp_path / "full.musicxml")

    assert returned.parts[0].voices == score.parts[0].voices


def test_a_voice_that_only_holds_a_rest_fermata_is_written_as_the_second_voice(
    tmp_path: Path,
) -> None:
    second = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),))
    score = score_of(part_of([event(0, 4, "G4")], second), bar_durations=(4,))

    returned = full_score_route(score, tmp_path / "full.musicxml")

    assert returned.parts[0].voices == score.parts[0].voices


def test_a_rest_fermata_is_one_rest_with_the_stored_length_in_the_written_file(
    tmp_path: Path,
) -> None:
    voice = NotatedVoice(
        events=(event(0, 1, "G4"), event(3, 1, "A4")), rest_fermatas=(rest_fermata(1, 2),)
    )
    path = tmp_path / "full.musicxml"

    write_full_score(score_of(part_of(voice), bar_durations=(4,)), path)

    rests = list(parse_score(path).parts[0].recurse().getElementsByClass("Rest"))
    assert [(Fraction(r.offset), Fraction(r.quarterLength)) for r in rests] == [(1, 2)]
    assert [type(e) for e in rests[0].expressions] == [expressions.Fermata]


def test_a_rest_fermata_in_the_lower_staff_voice_is_inverted(tmp_path: Path) -> None:
    quiet = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),))
    score = score_of(
        part_of([event(0, 4, "G4")]),
        part_of(quiet),
        part_of([event(0, 4, "C3")]),
        part_of([event(0, 4, "C2")]),
        bar_durations=(4,),
    )
    path = tmp_path / "piano.musicxml"

    write_piano_score(score, PIANO_LAYOUT, path)

    measure = parse_score(path).parts[0].getElementsByClass(stream.Measure)[0]
    fermatas = [e for e in measure.voices[1].notesAndRests[0].expressions]
    assert [f.type for f in fermatas] == ["inverted"]


def test_a_grace_note_in_the_lower_staff_voice_has_its_stem_down(tmp_path: Path) -> None:
    voice = NotatedVoice(events=(event(0, 4, "C3"),), grace_notes=(grace_note(0, "D3"),))
    score = score_of(
        part_of([event(0, 4, "G4")]),
        part_of([event(0, 4, "E4")]),
        part_of([event(0, 4, "C3")]),
        part_of(voice),
        bar_durations=(4,),
    )
    path = tmp_path / "piano.musicxml"

    write_piano_score(score, PIANO_LAYOUT, path)

    measure = parse_score(path).parts[1].getElementsByClass(stream.Measure)[0]
    stems = [n.stemDirection for n in measure.voices[1].notes if n.duration.isGrace]
    assert stems == ["down"]


@ROUTES
def test_a_rest_fermata_of_four_quarter_lengths_next_to_a_plain_rest_in_a_longer_bar_survives(
    route: Route, tmp_path: Path
) -> None:
    voice = NotatedVoice(events=(event(4, 1, "G4"),), rest_fermatas=(rest_fermata(0, 4),))
    score = four_part_score(voice, bar_durations=(6,), time_signatures=(THREE_TWO,))

    returned = route(score, tmp_path / "score.musicxml")

    assert returned.parts[0].voices[0] == voice


def test_a_lone_rest_fermata_that_music21_would_stretch_is_unsupported_in_the_full_score(
    tmp_path: Path,
) -> None:
    voice = NotatedVoice(
        events=(divided_event(4, 2, ("G4", None), ("E4", None)),),
        rest_fermatas=(rest_fermata(0, 4),),
    )
    score = four_part_score(voice, bar_durations=(6,), time_signatures=(THREE_TWO,))

    with pytest.raises(UnsupportedScoreError, match="stretch"):
        write_full_score(score, tmp_path / "full.musicxml")


def test_a_lone_rest_fermata_that_music21_would_stretch_is_unsupported_in_the_piano_score(
    tmp_path: Path,
) -> None:
    upper = NotatedVoice(
        events=(divided_event(4, 2, ("G4", None), ("E4", None)),),
        rest_fermatas=(rest_fermata(0, 4),),
    )
    whole_bar = NotatedVoice(events=(divided_event(0, 6, ("C4", None), ("A3", None)),))
    filler = [event(0, 6, "C3")]
    score = score_of(
        part_of(upper),
        part_of(whole_bar),
        part_of(filler),
        part_of(filler),
        bar_durations=(6,),
        time_signatures=(THREE_TWO,),
    )

    with pytest.raises(UnsupportedScoreError, match="stretch"):
        write_piano_score(score, PIANO_LAYOUT, tmp_path / "piano.musicxml")


def test_a_grace_note_keeps_music21_from_stretching_a_lone_rest_fermata(tmp_path: Path) -> None:
    voice = NotatedVoice(
        events=(divided_event(4, 2, ("G4", None), ("E4", None)),),
        grace_notes=(grace_note(4, "B4"),),
        rest_fermatas=(rest_fermata(0, 4),),
    )
    score = four_part_score(voice, bar_durations=(6,), time_signatures=(THREE_TWO,))

    returned = full_score_route(score, tmp_path / "full.musicxml")

    assert returned.parts[0].voices[0] == voice


def test_a_key_signature_change_inside_a_rest_fermata_that_every_voice_holds_is_unsupported(
    tmp_path: Path,
) -> None:
    holding = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 4),))
    change = (
        KeySignatureChange(onset=Fraction(0), sharps=0),
        KeySignatureChange(onset=Fraction(2), sharps=1),
    )
    score = score_of(part_of(holding, key_signatures=change), bar_durations=(4,))

    with pytest.raises(UnsupportedScoreError, match="key signature"):
        write_full_score(score, tmp_path / "full.musicxml")


def test_a_rest_fermata_filling_a_bar_in_one_voice_keeps_the_rest_of_another_voice(
    tmp_path: Path,
) -> None:
    # A rest that fills a bar inside a voice is read as a whole bar rest, and music21 then
    # stretches the first rest of the measure, here the plain rest of voice 1.
    first = [event(0, Fraction(1, 2), "G4")]
    second = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 6),))
    score = score_of(part_of(first, second), bar_durations=(6,), time_signatures=(THREE_TWO,))

    assert full_score_route(score, tmp_path / "full.musicxml") == score


def test_a_rest_fermata_filling_a_bar_on_a_staff_keeps_the_rest_of_the_other_staff_voice(
    tmp_path: Path,
) -> None:
    # Same music21 behavior as above, on the upper staff of the grand staff.
    filler = [event(0, 6, "C3")]
    second = NotatedVoice(events=(), rest_fermatas=(rest_fermata(0, 6),))
    score = score_of(
        part_of([event(0, Fraction(1, 2), "G4")]),
        part_of(second),
        part_of(filler),
        part_of(filler),
        bar_durations=(6,),
        time_signatures=(THREE_TWO,),
    )

    assert grand_staff_route(score, tmp_path / "piano.musicxml") == score
