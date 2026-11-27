"""Hypothesis properties of harmonic segmentation (spec 003, section 5)."""

from fractions import Fraction
from itertools import pairwise

from hypothesis import HealthCheck, assume, given, reject, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn
from tests.core_builders import event, part_of, score_of, spelled_pitch
from tests.strategies import scores

from aretz_texture.analysis.attacks import voice_attacks
from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.sounding_notes import sounding_notes
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.errors import SilentPhraseError
from aretz_texture.core.harmony import HarmonicWindow, NonChordToneKind
from aretz_texture.core.score import Score
from aretz_texture.core.texture import PhraseClosing, TexturalAnalysis, TimeSpan

TEXTURE_SETTINGS = TexturalAnalysisSettings()
NON_CHORD_TONE_SETTINGS = NonChordToneSettings()
HEAVY_EXAMPLES = 50  # the examples of these properties analyze two scores each
# These properties draw a whole score and then a second one inside the test, so hypothesis
# measures the time of input generation too and its too_slow health check fires at random
# on a loaded machine although the property is sound; the examples are capped instead.
HEAVY_SETTINGS = settings(max_examples=HEAVY_EXAMPLES, suppress_health_check=[HealthCheck.too_slow])


def texture_of(score: Score) -> TexturalAnalysis:
    """Analyze a score, discarding the generated ones with a phrase that has no attack."""
    try:
        return analyze_texture(score, TEXTURE_SETTINGS)
    except SilentPhraseError:
        reject()


def analyzed(score: Score) -> tuple[HarmonicWindow, ...]:
    """Segment the harmony of a score."""
    return segment_harmony(score, texture_of(score), NON_CHORD_TONE_SETTINGS)


@given(scores())
def test_windows_tile_each_phrase_from_its_first_attack_to_its_latest_note_end(
    score: Score,
) -> None:
    texture = texture_of(score)
    windows = segment_harmony(score, texture, NON_CHORD_TONE_SETTINGS)

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
            note.end for stream in streams for note in sounding_notes(score, stream, phrase.span)
        )
        assert own
        assert own[0].span.onset == first_attack
        assert own[-1].span.end == latest_end
        assert all(
            previous.span.end == following.span.onset for previous, following in pairwise(own)
        )
        assert phrase.span.contains(TimeSpan(onset=own[0].span.onset, end=own[-1].span.end))


@given(scores())
def test_only_the_last_window_of_a_phrase_closing_at_a_fermata_has_the_fermata(
    score: Score,
) -> None:
    texture = texture_of(score)
    windows = segment_harmony(score, texture, NON_CHORD_TONE_SETTINGS)

    for phrase_texture in texture.phrases:
        own = [window for window in windows if window.phrase_number == phrase_texture.phrase.number]
        closes = phrase_texture.phrase.closing is PhraseClosing.FERMATA
        assert [window.fermata for window in own] == [False] * (len(own) - 1) + [closes]


@given(scores())
def test_two_runs_give_equal_windows(score: Score) -> None:
    assert analyzed(score) == analyzed(score)


def summary_of(windows: tuple[HarmonicWindow, ...]) -> list[tuple[object, ...]]:
    """Describe the windows by what the order of the parts must not change."""
    return [
        (
            window.span,
            window.phrase_number,
            window.plane_count,
            window.chord_tones,
            sorted(
                (tone.note.pitch.highest_first_key(), tone.kind, tone.from_onset)
                for tone in window.non_chord_tones
            ),
            window.fermata,
        )
        for window in windows
    ]


@HEAVY_SETTINGS
@given(st.data())
def test_permuting_the_parts_does_not_change_windows_or_non_chord_tones(
    data: st.DataObject,
) -> None:
    score = data.draw(scores())
    order = data.draw(st.permutations(range(len(score.parts))))
    permuted = score.model_copy(update={"parts": tuple(score.parts[index] for index in order)})

    assert summary_of(analyzed(permuted)) == summary_of(analyzed(score))


CHORD_POOL = ["C4", "E4", "G4"]
# Pairs of notes a third apart, whose middle pitch is a step from both.
THIRDS_WITH_PASSING_TONE = [
    ("C4", "D4", "E4"),
    ("E4", "F4", "G4"),
    ("E4", "D4", "C4"),
    ("G4", "F4", "E4"),
]
CHORDAL_VOICES = 4
CHORDAL_BEATS = 8


@st.composite
def chordal_score_and_insertion(draw: DrawFn) -> tuple[list[list[str]], int, int, str]:
    """Return four voices of quarter notes on C, E, G, and where a passing tone may go.

    Quarters on the beat of 4/4 with no steps between them are all chord tones, so the score
    has no non chord tone. The result is the pitches of every voice, the voice and the beat
    where the inserted passing tone goes, and its pitch; the notes at that beat and the next
    are forced to be a third apart with the passing tone as the step between them.
    """
    voices = [
        [draw(st.sampled_from(CHORD_POOL)) for _ in range(CHORDAL_BEATS)]
        for _ in range(CHORDAL_VOICES)
    ]
    voice = draw(st.integers(0, CHORDAL_VOICES - 1))
    beat = draw(st.integers(0, CHORDAL_BEATS - 2))
    first, passing, last = draw(st.sampled_from(THIRDS_WITH_PASSING_TONE))
    voices[voice][beat], voices[voice][beat + 1] = first, last
    return voices, voice, beat, passing


def chordal_score(voices: list[list[str]], inserted: tuple[int, int, str] | None) -> Score:
    parts = []
    for number, pitches in enumerate(voices):
        events = []
        for beat, pitch in enumerate(pitches):
            if inserted is not None and inserted[:2] == (number, beat):
                events += [
                    event(beat, Fraction(1, 2), pitch),
                    event(beat + Fraction(1, 2), Fraction(1, 2), inserted[2]),
                ]
            else:
                events.append(event(beat, 1, pitch))
        parts.append(part_of(events))
    return score_of(*parts)


def windows_of_chordal(score: Score) -> tuple[HarmonicWindow, ...]:
    return segment_harmony(score, analyze_texture(score, TEXTURE_SETTINGS), NON_CHORD_TONE_SETTINGS)


@HEAVY_SETTINGS
@given(chordal_score_and_insertion())
def test_adding_an_unaccented_passing_tone_does_not_change_the_windows(
    drawn: tuple[list[list[str]], int, int, str],
) -> None:
    voices, voice, beat, passing = drawn
    # The chord tone that the passing tone replaces ends where the passing tone starts, and
    # that end is read (spec 003, section 3.4). When it is the only lowest note, the reading
    # has no bass and a window opens; so the property holds for the other voices (PR of 003a).
    others = [pitches[beat] for number, pitches in enumerate(voices) if number != voice]
    assume(
        any(CHORD_POOL.index(pitch) <= CHORD_POOL.index(voices[voice][beat]) for pitch in others)
    )
    base = windows_of_chordal(chordal_score(voices, None))
    inserted = windows_of_chordal(chordal_score(voices, (voice, beat, passing)))

    assert [(window.span, window.chord_tones) for window in inserted] == [
        (window.span, window.chord_tones) for window in base
    ]
    recorded = [tone for window in inserted for tone in window.non_chord_tones]
    assert [tone.kind for tone in recorded] == [NonChordToneKind.PASSING]
    assert recorded[0].note.pitch == spelled_pitch(passing)
