from fractions import Fraction

from tests.core_builders import divided_event, event, part_of, score_of

from aretz_texture.analysis.attacks import Attack, voice_attacks
from aretz_texture.analysis.doublings import (
    coinciding_attack_proportion,
    fuse_doublings,
)
from aretz_texture.analysis.settings import DoublingSettings
from aretz_texture.core.notation import NoteEvent, TieType
from aretz_texture.core.score import Score
from aretz_texture.core.texture import StreamReference, TimeSpan

DEFAULTS = DoublingSettings()
MELODY = ["C4", "E4", "G4", "C5", "E4", "D4", "F4", "A4", "G4", "E4"]
OCTAVE_UP = ["C5", "E5", "G5", "C6", "E5", "D5", "F5", "A5", "G5", "E5"]
FIFTH_UP = ["G4", "B4", "D5", "G5", "B4", "A4", "C5", "E5", "D5", "B4"]


def line(pitches: list[str], tie: TieType | None = None) -> list[NoteEvent]:
    """Return one quarter note per pitch, from onset 0."""
    return [event(onset, 1, pitch, tie=tie) for onset, pitch in enumerate(pitches)]


def stream(part_number: int, voice_number: int = 1) -> StreamReference:
    return StreamReference(part_number=part_number, voice_number=voice_number, part_name=None)


def attacks_of(events: list[NoteEvent]) -> tuple[Attack, ...]:
    score = score_of(part_of(events), bar_durations=(4, 4, 4))
    return voice_attacks(score, stream(1), TimeSpan(onset=Fraction(0), end=score.end()))


def groups_of(score: Score, settings: DoublingSettings = DEFAULTS) -> list[list[tuple[int, int]]]:
    return [
        [(s.part_number, s.voice_number) for s in fused.streams]
        for fused in fuse_doublings(score, settings)
    ]


def test_the_proportion_of_a_voice_with_itself_is_1() -> None:
    attacks = attacks_of(line(MELODY))

    assert coinciding_attack_proportion(attacks, attacks) == 1


def test_a_copy_at_the_octave_has_proportion_1_and_one_at_the_fifth_has_0() -> None:
    melody = attacks_of(line(MELODY))

    assert coinciding_attack_proportion(melody, attacks_of(line(OCTAVE_UP))) == 1
    assert coinciding_attack_proportion(melody, attacks_of(line(FIFTH_UP))) == 0


def test_the_proportion_is_over_the_attacks_of_the_sparser_voice() -> None:
    dense = attacks_of(line(MELODY))
    sparse = attacks_of([event(0, 2, "C4"), event(2, 2, "G4")])

    assert coinciding_attack_proportion(dense, sparse) == 1
    assert coinciding_attack_proportion(sparse, dense) == 1


def test_the_proportion_is_0_when_either_voice_has_no_attack() -> None:
    attacks = attacks_of(line(MELODY))

    assert coinciding_attack_proportion(attacks, ()) == 0
    assert coinciding_attack_proportion((), attacks) == 0


def test_attacks_at_different_onsets_do_not_coincide() -> None:
    first = attacks_of([event(0, 1, "C4"), event(1, 1, "D4")])
    second = attacks_of([event(0, Fraction(1, 2), "C4"), event(Fraction(1, 2), 1, "D4")])

    assert coinciding_attack_proportion(first, second) == Fraction(1, 2)


def test_a_copy_at_the_octave_fuses_and_one_at_the_fifth_does_not() -> None:
    score = score_of(
        part_of(line(MELODY)),
        part_of(line(OCTAVE_UP)),
        part_of(line(FIFTH_UP)),
        bar_durations=(4, 4, 4),
    )

    assert groups_of(score) == [[(1, 1), (2, 1)], [(3, 1)]]


def test_a_proportion_of_exactly_9_over_10_fuses() -> None:
    nine_of_ten = [*OCTAVE_UP[:9], "F#5"]
    score = score_of(part_of(line(MELODY)), part_of(line(nine_of_ten)), bar_durations=(4, 4, 4))

    assert groups_of(score) == [[(1, 1), (2, 1)]]


def test_a_proportion_just_below_9_over_10_does_not_fuse() -> None:
    # 17 of 19 coincide, 0.8947 of the sparser voice.
    long_melody = [*MELODY, *MELODY[:9]]
    nearly = [*OCTAVE_UP, *OCTAVE_UP[:7], "F#5", "F#5"]
    score = score_of(
        part_of(line(long_melody)), part_of(line(nearly)), bar_durations=(4, 4, 4, 4, 4)
    )

    assert groups_of(score) == [[(1, 1)], [(2, 1)]]


def test_the_threshold_is_a_setting() -> None:
    nine_of_ten = [*OCTAVE_UP[:9], "F#5"]
    score = score_of(part_of(line(MELODY)), part_of(line(nine_of_ten)), bar_durations=(4, 4, 4))

    strict = DoublingSettings(minimum_coinciding_attack_proportion=Fraction(1))

    assert groups_of(score, strict) == [[(1, 1)], [(2, 1)]]


def test_fusion_is_transitive_through_a_voice_that_doubles_two_others() -> None:
    both = [divided_event(onset, 1, ("E4", None), ("C4", None)) for onset in range(10)]
    score = score_of(
        part_of(line(["C4"] * 10)),
        part_of(both),
        part_of(line(["E4"] * 10)),
        bar_durations=(4, 4, 4),
    )

    assert groups_of(score) == [[(1, 1), (2, 1), (3, 1)]]


def test_a_voice_without_attacks_stays_alone() -> None:
    score = score_of(part_of(line(MELODY)), part_of([]), bar_durations=(4, 4, 4))

    assert groups_of(score) == [[(1, 1)], [(2, 1)]]


def test_a_voice_of_a_part_with_several_voices_can_fuse_with_another_part() -> None:
    score = score_of(
        part_of(line(MELODY), line(FIFTH_UP)),
        part_of(line(OCTAVE_UP)),
        bar_durations=(4, 4, 4),
    )

    assert groups_of(score) == [[(1, 1), (2, 1)], [(1, 2)]]
