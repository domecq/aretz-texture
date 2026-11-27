from fractions import Fraction

from tests.analysis.harmony_scores import (
    EIGHTH,
    line,
    pitch_text,
    suspension_score,
    tied_alto,
)
from tests.core_builders import event, part_of, score_of, spelled_pitch

from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.harmony import HarmonicWindow, NonChordToneKind
from aretz_texture.core.score import Score


def windows_of(score: Score) -> tuple[HarmonicWindow, ...]:
    texture = analyze_texture(score, TexturalAnalysisSettings())
    return segment_harmony(score, texture, NonChordToneSettings())


def bounds(window: HarmonicWindow) -> tuple[Fraction, Fraction]:
    return (window.span.onset, window.span.end)


def chord(window: HarmonicWindow) -> list[str]:
    return [pitch_text(pitch) for pitch in window.chord_tones]


def plane_note_texts(window: HarmonicWindow) -> list[tuple[int, str]]:
    return [(note.plane_number, pitch_text(note.pitch)) for note in window.plane_notes]


def chord_over_bass(bass: list[tuple[str, int]]) -> Score:
    """Return G4 and E4 held for a bar over a bass line of (pitch, duration)."""
    return score_of(
        part_of([event(0, 4, "G4")]), part_of([event(0, 4, "E4")]), part_of(line(*bass))
    )


def test_a_phrase_without_changes_is_one_window_from_its_first_attack_to_its_end() -> None:
    score = score_of(part_of([event(1, 3, "G4")]), part_of([event(1, 3, "C3")]))

    (window,) = windows_of(score)

    assert bounds(window) == (1, 4)
    assert chord(window) == ["G4", "C3"]


def test_a_new_pitch_class_opens_a_new_window() -> None:
    score = score_of(part_of(line(("G4", 2), ("A4", 2))), part_of([event(0, 4, "C3")]))

    windows = windows_of(score)

    assert [bounds(window) for window in windows] == [(0, 2), (2, 4)]
    assert [chord(window) for window in windows] == [["G4", "C3"], ["A4", "C3"]]


def test_a_change_of_the_bass_pitch_class_opens_a_window_with_no_new_pitch_class() -> None:
    windows = windows_of(chord_over_bass([("C3", 2), ("E3", 2)]))

    assert [bounds(window) for window in windows] == [(0, 2), (2, 4)]
    assert [chord(window) for window in windows] == [["G4", "E4", "C3"], ["G4", "E4", "E3"]]


def test_a_reattacked_identical_chord_continues_the_window() -> None:
    score = score_of(
        part_of(line(("G4", 1), ("G4", 3))),
        part_of(line(("E4", 1), ("E4", 3))),
        part_of(line(("C3", 1), ("C3", 3))),
    )

    assert [bounds(window) for window in windows_of(score)] == [(0, 4)]


def test_a_chord_that_loses_a_voice_continues_the_window() -> None:
    score = score_of(
        part_of([event(0, 1, "G4")]),
        part_of([event(0, 4, "E4")]),
        part_of(line(("C3", 2), ("C3", 2))),
    )

    (window,) = windows_of(score)

    assert bounds(window) == (0, 4)
    assert chord(window) == ["G4", "E4", "C3"]


def test_a_chord_that_changes_octave_without_a_new_pitch_class_continues_the_window() -> None:
    score = score_of(
        part_of(line(("G4", 2), ("G5", 2))),
        part_of([event(0, 4, "E4")]),
        part_of([event(0, 4, "C3")]),
    )

    assert [bounds(window) for window in windows_of(score)] == [(0, 4)]


def test_the_windows_of_a_phrase_are_contiguous_to_the_latest_end_of_a_note() -> None:
    score = score_of(
        part_of(line((None, 1), ("G4", 1), ("A4", 1))), part_of(line((None, 1), ("C3", 1)))
    )

    windows = windows_of(score)

    assert [bounds(window) for window in windows] == [(1, 2), (2, 3)]


def test_rests_after_a_final_fermata_stay_rests() -> None:
    score = score_of(
        part_of([event(0, 2, "G4", fermata=True)]),
        part_of([event(0, 2, "C3", fermata=True)]),
        bar_durations=(4,),
    )

    (window,) = windows_of(score)

    assert bounds(window) == (0, 2)


def fermata_score() -> Score:
    """Return a score whose first phrase is a whole bar of fermatas, then a second bar."""
    upper = [event(0, 4, "G4", fermata=True), event(4, 2, "A4"), event(6, 2, "G4")]
    lower = [event(0, 4, "C3", fermata=True), event(4, 4, "C3")]
    return score_of(part_of(upper), part_of(lower))


def test_no_window_crosses_a_phrase_boundary() -> None:
    windows = windows_of(fermata_score())

    assert [(window.phrase_number, *bounds(window)) for window in windows] == [
        (1, 0, 4),
        (2, 4, 6),
        (2, 6, 8),
    ]


def test_only_the_last_window_of_a_phrase_closing_at_a_fermata_has_the_fermata() -> None:
    windows = windows_of(fermata_score())

    assert [window.fermata for window in windows] == [True, False, False]


def test_every_window_of_a_phrase_but_the_last_has_no_fermata_even_in_a_fermata_phrase() -> None:
    upper = [event(0, 2, "G4"), event(2, 2, "A4", fermata=True)]
    lower = [event(0, 4, "C3", fermata=True)]

    windows = windows_of(score_of(part_of(upper), part_of(lower)))

    assert [window.fermata for window in windows] == [False, True]


def test_a_phrase_without_fermatas_has_no_window_with_a_fermata() -> None:
    windows = windows_of(chord_over_bass([("C3", 2), ("E3", 2)]))

    assert not any(window.fermata for window in windows)


def test_every_window_knows_its_phrase_and_the_plane_count() -> None:
    windows = windows_of(fermata_score())

    assert [(window.phrase_number, window.plane_count) for window in windows] == [
        (1, 2),
        (2, 2),
        (2, 2),
    ]


def test_plane_notes_are_one_per_sounding_plane_numbered_from_the_highest() -> None:
    (window,) = windows_of(chord_over_bass([("C3", 4)]))

    assert plane_note_texts(window) == [(1, "G4"), (2, "E4"), (3, "C3")]
    assert [note.stream.part_number for note in window.plane_notes] == [1, 2, 3]


def test_a_plane_note_is_the_first_chord_tone_the_plane_attacks_when_it_rests_at_the_onset() -> (
    None
):
    score = score_of(
        part_of([event(0, 4, "G4")]),
        part_of([event(1, 3, "E4")]),
        part_of([event(0, 4, "E3")]),
        part_of([event(0, 4, "C2")]),
    )

    (window,) = windows_of(score)

    assert bounds(window) == (0, 4)
    assert plane_note_texts(window) == [(1, "G4"), (2, "E4"), (3, "E3"), (4, "C2")]


def test_a_doubled_lowest_plane_gives_the_lower_pitch_of_its_voices() -> None:
    score = score_of(
        part_of([event(0, 4, "G4")]),
        part_of([event(0, 4, "E4")]),
        part_of([event(0, 4, "C3")]),
        part_of([event(0, 4, "C2")]),
    )

    (window,) = windows_of(score)

    assert plane_note_texts(window)[-1] == (3, "C2")
    assert window.plane_notes[-1].stream.part_number == 4
    assert chord(window) == ["G4", "E4", "C3", "C2"]


def test_a_doubled_upper_plane_gives_the_higher_pitch_of_its_voices() -> None:
    score = score_of(
        part_of([event(0, 4, "G5")]),
        part_of([event(0, 4, "G4")]),
        part_of([event(0, 4, "C3")]),
    )

    (window,) = windows_of(score)

    assert plane_note_texts(window) == [(1, "G5"), (2, "C3")]


def test_a_plane_without_a_chord_tone_in_the_window_has_no_plane_note() -> None:
    upper = [event(0, 2, "G4"), event(2, 2, "G4", fermata=True)]
    middle = [event(0, 4, "E4", fermata=True)]
    bass = [event(0, 2, "C3")]

    windows = windows_of(
        score_of(part_of(upper), part_of(middle), part_of(bass), bar_durations=(4,))
    )

    assert [plane_note_texts(window) for window in windows] == [
        [(1, "G4"), (2, "E4"), (3, "C3")],
        [(1, "G4"), (2, "E4")],
    ]


def test_passing_tones_are_removed_from_the_chord_tones_and_recorded_in_the_window() -> None:
    score = score_of(
        part_of(line(("C5", EIGHTH), ("D5", EIGHTH), ("E5", 1), ("E5", 2))),
        part_of([event(0, 4, "C3")]),
    )

    windows = windows_of(score)

    assert chord(windows[0]) == ["C5", "C3"]
    assert [(pitch_text(tone.note.pitch), tone.kind) for tone in windows[0].non_chord_tones] == [
        ("D5", NonChordToneKind.PASSING)
    ]
    assert bounds(windows[0]) == (0, 1)


def test_a_suspension_is_a_chord_tone_before_its_tactus_onset_and_its_resolution_after() -> None:
    windows = windows_of(suspension_score(tied_alto("B3", Fraction(9, 2))))

    assert [bounds(window) for window in windows] == [(0, 4), (4, 8)]
    assert chord(windows[-2]) == ["G4", "C3"]
    assert chord(windows[-1]) == ["G4", "D4", "B3", "G2"]
    assert windows[-2].non_chord_tones == ()
    assert [tone.kind for tone in windows[-1].non_chord_tones] == [NonChordToneKind.SUSPENSION]


def test_the_plane_note_of_a_suspended_voice_is_its_resolution_from_the_tactus_onset() -> None:
    windows = windows_of(suspension_score(tied_alto("B3", Fraction(9, 2))))

    assert plane_note_texts(windows[-2])[1] == (3, "C4")
    assert plane_note_texts(windows[-1])[2] == (3, "B3")


def test_an_anticipation_belongs_to_no_window_and_is_recorded_in_the_window_where_it_sounds() -> (
    None
):
    score = score_of(
        part_of(line(("D5", 2), ("B4", EIGHTH), ("C5", EIGHTH), ("C5", 1), ("C5", 4))),
        part_of(line(("G2", 3), ("C3", 5))),
    )

    windows = windows_of(score)

    assert [chord(window) for window in windows] == [["D5", "G2"], ["B4", "G2"], ["C5", "C3"]]
    assert [bounds(window) for window in windows] == [(0, 2), (2, 3), (3, 8)]
    assert [tone.kind for tone in windows[1].non_chord_tones] == [NonChordToneKind.ANTICIPATION]
    assert windows[2].non_chord_tones == ()


def test_the_end_of_the_bass_opens_a_window_with_the_next_lowest_pitch_as_bass() -> None:
    score = score_of(
        part_of([event(0, 2, "G4")]),
        part_of([event(0, 2, "D4")]),
        part_of([event(0, 2, "B3")]),
        part_of([event(0, 1, "G2")]),
    )

    windows = windows_of(score)

    assert [bounds(window) for window in windows] == [(0, 1), (1, 2)]
    assert [chord(window) for window in windows] == [["G4", "D4", "B3", "G2"], ["G4", "D4", "B3"]]
    assert windows[1].bass() == spelled_pitch("B3")


def test_the_tactus_onset_of_a_suspension_is_read_even_when_no_voice_attacks_there() -> None:
    alto = [event(0, Fraction(3, 2), "C4"), event(Fraction(3, 2), Fraction(5, 2), "B3")]
    score = score_of(
        part_of(alto),
        part_of([event(0, 4, "G4")]),
        part_of([event(Fraction(1, 2), Fraction(7, 2), "D4")]),
        part_of([event(0, 4, "C3")]),
    )

    windows = windows_of(score)

    assert [bounds(window) for window in windows] == [
        (0, Fraction(1, 2)),
        (Fraction(1, 2), 1),
        (1, 4),
    ]
    assert chord(windows[2]) == ["G4", "D4", "B3", "C3"]
    assert [tone.kind for tone in windows[2].non_chord_tones] == [NonChordToneKind.SUSPENSION]


def test_a_note_ending_at_the_end_of_the_phrase_opens_no_window() -> None:
    score = score_of(part_of([event(0, 2, "G4")]), part_of([event(0, 4, "C3")]))

    assert [bounds(window) for window in windows_of(score)] == [(0, 4)]


def test_a_note_carried_into_a_phrase_opens_no_window_before_its_first_attack() -> None:
    score = score_of(
        part_of([event(0, 3, "C5"), event(Fraction(7, 2), EIGHTH, "D5")]),
        part_of([event(0, 2, "G4", fermata=True), event(Fraction(7, 2), EIGHTH, "E4")]),
        part_of([event(0, Fraction(7, 2), "B3"), event(Fraction(7, 2), EIGHTH, "B3")]),
    )

    windows = [window for window in windows_of(score) if window.phrase_number == 2]

    assert bounds(windows[0])[0] == Fraction(7, 2)


def test_a_passing_tone_in_the_lowest_voice_opens_no_window_where_the_bass_note_ends() -> None:
    score = score_of(
        part_of([event(0, 4, "G4")]),
        part_of([event(0, 4, "E4")]),
        part_of(line(("C3", Fraction(3, 2)), ("D3", EIGHTH), ("E3", 2))),
    )

    windows = windows_of(score)

    assert [bounds(window) for window in windows] == [(0, 2), (2, 4)]
