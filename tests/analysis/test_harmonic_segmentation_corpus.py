"""Harmonic segmentation of corpus chorales (music21 10.5.2, November 26, 2026)."""

from collections import Counter
from fractions import Fraction
from itertools import pairwise

import pytest
from tests.analysis.harmony_scores import pitch_text
from tests.corpus_scores import corpus_score, corpus_texture, distinct_corpus_chorales

from aretz_texture.analysis.attacks import voice_attacks
from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.metric_grid import tactus_at, tactus_label, tactus_spans
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.analysis.sounding_notes import sounding_notes
from aretz_texture.core.harmony import HarmonicWindow, NonChordToneKind
from aretz_texture.core.score import Score
from aretz_texture.core.texture import PhraseClosing, TimeSpan

FOUR_PLANES = 4


def windows_of(identifier: str) -> tuple[HarmonicWindow, ...]:
    return segment_harmony(
        corpus_score(identifier), corpus_texture(identifier), NonChordToneSettings()
    )


def tactus_label_of(score: Score, moment: Fraction) -> str:
    whole = TimeSpan(onset=Fraction(0), end=score.end())
    holding = next(span for span in tactus_spans(score, whole) if span.onset <= moment < span.end)
    return tactus_label(score, holding)


def tones_of_bwv66_6() -> list[tuple[str, str, str, NonChordToneKind]]:
    """Describe each non chord tone as (part, pitch, bar and tactus, kind)."""
    score = corpus_score("bach/bwv66.6")
    tones = [tone for window in windows_of("bach/bwv66.6") for tone in window.non_chord_tones]
    return [
        (
            score.parts[tone.note.stream.part_number - 1].name or "",
            pitch_text(tone.note.pitch),
            tactus_label_of(score, tone.note.onset),
            tone.kind,
        )
        for tone in tones
    ]


def test_bwv66_6_pickup_soprano_b4_is_a_passing_tone_between_c_sharp_5_and_a4() -> None:
    assert ("Soprano", "B4", "bar 0, tactus 4", NonChordToneKind.PASSING) in tones_of_bwv66_6()


def test_bwv66_6_alto_d4_in_bar_8_is_a_passing_tone_between_c_sharp_4_and_e4() -> None:
    assert ("Alto", "D4", "bar 8, tactus 1", NonChordToneKind.PASSING) in tones_of_bwv66_6()


def test_bwv66_6_bass_f_sharp_3_in_bar_4_is_a_lower_neighbor_tone_of_g_sharp_3() -> None:
    assert ("Bass", "F#3", "bar 4, tactus 1", NonChordToneKind.NEIGHBOR) in tones_of_bwv66_6()


def test_bwv66_6_alto_f_sharp_4_in_bar_4_is_a_suspension_resolving_to_e4() -> None:
    score = corpus_score("bach/bwv66.6")
    tones = [tone for window in windows_of("bach/bwv66.6") for tone in window.non_chord_tones]

    (suspension,) = [
        tone
        for tone in tones
        if tone.kind is NonChordToneKind.SUSPENSION
        and tone.note.stream.part_number == 2
        and tactus_label_of(score, tone.note.onset) == "bar 4, tactus 1"
    ]

    assert pitch_text(suspension.note.pitch) == "F#4"
    assert suspension.resolution is not None
    assert pitch_text(suspension.resolution) == "E4"
    assert suspension.from_onset == suspension.note.onset == 13


def test_bwv66_6_has_no_anticipation() -> None:
    assert NonChordToneKind.ANTICIPATION not in {kind for *_, kind in tones_of_bwv66_6()}


def test_bwv347_alto_e4_in_bar_7_anticipates_the_e4_of_the_next_beat() -> None:
    score = corpus_score("bach/bwv347")
    tones = [tone for window in windows_of("bach/bwv347") for tone in window.non_chord_tones]

    anticipations = [
        (score.parts[tone.note.stream.part_number - 1].name, pitch_text(tone.note.pitch))
        for tone in tones
        if tone.kind is NonChordToneKind.ANTICIPATION
        and tactus_label_of(score, tone.note.onset) == "bar 7, tactus 3"
    ]

    assert anticipations == [("Alto", "E4")]


def test_bwv66_6_has_the_non_chord_tones_of_the_probe_by_kind() -> None:
    counts = Counter(kind for *_, kind in tones_of_bwv66_6())

    assert counts == {
        NonChordToneKind.PASSING: 12,
        NonChordToneKind.NEIGHBOR: 5,
        NonChordToneKind.SUSPENSION: 4,
    }


def test_bwv66_6_pickup_with_three_passing_tones_leaves_only_the_alto_in_its_second_window() -> (
    None
):
    first, second, third = windows_of("bach/bwv66.6")[:3]

    assert [(window.span.onset, window.span.end) for window in (first, second, third)] == [
        (0, Fraction(1, 2)),
        (Fraction(1, 2), 1),
        (1, 2),
    ]
    assert [pitch_text(pitch) for pitch in first.chord_tones] == ["C#5", "E4", "A3", "A3"]
    assert [pitch_text(pitch) for pitch in second.chord_tones] == ["E4"]
    assert len(second.non_chord_tones) == 3


def test_bwv8_6_the_plane_of_bass_and_continuo_gives_the_lower_of_the_two() -> None:
    score = corpus_score("bach/bwv8.6")
    moment = next(
        window
        for window in windows_of("bach/bwv8.6")
        if tactus_label_of(score, window.span.onset) == "bar 16, tactus 3"
    )

    lowest = moment.plane_notes[-1]

    assert (lowest.plane_number, pitch_text(lowest.pitch)) == (4, "E2")
    assert score.parts[lowest.stream.part_number - 1].name == "Continuo"
    assert "E3" in [pitch_text(pitch) for pitch in moment.chord_tones]


def test_bwv8_6_a_plane_that_rests_has_no_plane_note_in_the_windows_of_the_rest() -> None:
    windows = windows_of("bach/bwv8.6")

    assert [(note.plane_number, pitch_text(note.pitch)) for note in windows[1].plane_notes] == [
        (1, "B4")
    ]


def test_bwv320_bar_2_the_bass_that_walks_on_after_its_fermata_keeps_its_plane_note() -> None:
    # Spec 003 criterion 9 expects no plane note for plane 4 here; the bass does not rest.
    score = corpus_score("bach/bwv320")
    bar_2 = [
        window
        for window in windows_of("bach/bwv320")
        if window.phrase_number == 1 and 3 <= window.span.onset < 6
    ]

    assert [(window.span.onset, window.span.end) for window in bar_2] == [(3, 5), (5, 6)]
    assert [pitch_text(window.plane_notes[-1].pitch) for window in bar_2] == ["C3", "Bb3"]
    assert [event.onset for event in score.parts[3].voices[0].events if 3 <= event.onset < 6] == [
        3,
        4,
        5,
    ]


@pytest.mark.slow
def test_windows_of_every_chorale_tile_each_phrase_from_the_first_attack_to_the_last_end() -> None:
    for identifier in distinct_corpus_chorales():
        score, texture = corpus_score(identifier), corpus_texture(identifier)
        windows = windows_of(identifier)
        for phrase_texture in texture.phrases:
            phrase = phrase_texture.phrase
            own = [window for window in windows if window.phrase_number == phrase.number]
            streams = [
                stream for leaf in phrase_texture.configuration.leaves() for stream in leaf.streams
            ]
            first_attack = min(
                attack.onset
                for stream in streams
                for attack in voice_attacks(score, stream, phrase.span)
            )
            latest_end = max(
                note.end
                for stream in streams
                for note in sounding_notes(score, stream, phrase.span)
            )
            assert own[0].span.onset == first_attack, (identifier, phrase.number)
            assert own[-1].span.end == latest_end, (identifier, phrase.number)
            assert all(
                previous.span.end == following.span.onset for previous, following in pairwise(own)
            ), (identifier, phrase.number)
            closes_at_fermata = phrase.closing is PhraseClosing.FERMATA
            assert [window.fermata for window in own][-1] is closes_at_fermata
            assert not any(window.fermata for window in own[:-1])


def corpus_measures(identifiers: tuple[str, ...]) -> tuple[int, int, int]:
    """Count windows, windows shorter than one tactus and windows with a voice crossing."""
    windows_count = short = crossing = 0
    for identifier in identifiers:
        score = corpus_score(identifier)
        for window in windows_of(identifier):
            windows_count += 1
            short += window.span.end - window.span.onset < tactus_at(score, window.span.onset)
            lowest = window.plane_notes[-1] if window.plane_notes else None
            if lowest is not None and lowest.plane_number == window.plane_count:
                crossing += any(
                    note.pitch.sounding_semitones() < lowest.pitch.sounding_semitones()
                    for note in window.plane_notes[:-1]
                )
    return windows_count, short, crossing


@pytest.mark.slow
def test_the_corpus_has_the_windows_counted_in_section_7_item_6_of_spec_003() -> None:
    identifiers = distinct_corpus_chorales()
    four_planes = tuple(
        identifier
        for identifier in identifiers
        if all(
            len(phrase_texture.configuration.leaves()) == FOUR_PLANES
            for phrase_texture in corpus_texture(identifier).phrases
        )
    )

    assert len(identifiers) == 350
    assert len(four_planes) == 333
    assert corpus_measures(four_planes) == (19994, 8818, 95)
    assert corpus_measures(identifiers) == (21471, 9666, 137)
