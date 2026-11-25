"""Hypothesis properties of the textural analysis (spec 002, section 5, slice 002c)."""

from collections.abc import Callable
from fractions import Fraction

from hypothesis import assume, given, reject, settings
from hypothesis import strategies as st
from tests.strategies import scores

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.analysis.doublings import fuse_doublings
from aretz_texture.analysis.metric_grid import tactus_spans
from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.errors import SilentPhraseError
from aretz_texture.core.notation import EventPitch, NotatedVoice, NoteEvent, TieType
from aretz_texture.core.score import Score
from aretz_texture.core.texture import (
    DecisionRule,
    TexturalAnalysis,
    TexturalConfiguration,
    TimeSpan,
)
from aretz_texture.render.textural_schema import compact_schema

SETTINGS = TexturalAnalysisSettings()
HEAVY_EXAMPLES = 50  # the examples of these properties analyze two scores each

# Ties of the two halves of an event split in two, so that the first half attacks exactly
# when the event did and the second half always attacks.
FIRST_HALF_TIE = {
    None: None,
    TieType.START: None,
    TieType.STOP: TieType.STOP,
    TieType.CONTINUE: TieType.STOP,
}
SECOND_HALF_TIE = {
    None: None,
    TieType.STOP: None,
    TieType.START: TieType.START,
    TieType.CONTINUE: TieType.START,
}


def analysis_of(score: Score) -> TexturalAnalysis:
    """Analyze a score, discarding the generated ones with a phrase that has no attack."""
    try:
        return analyze_texture(score, SETTINGS)
    except SilentPhraseError:
        reject()


def summary_of(
    analysis: TexturalAnalysis, original_part_number: Callable[[int], int]
) -> list[tuple[object, ...]]:
    """Describe each phrase by what part order must not change, with original part numbers."""
    described: list[tuple[object, ...]] = []
    for texture in analysis.phrases:
        root = texture.configuration
        values = tuple(
            (decision.value, decision.rule)
            for decision in (
                root.features.planes,
                root.features.homogeneity,
                root.features.linearity,
                root.features.accent_coincidence,
                root.features.attack_divergence,
            )
        )
        leaves = sorted(
            (
                sorted(
                    (original_part_number(stream.part_number), stream.voice_number)
                    for stream in leaf.streams
                ),
                compact_schema(leaf),
            )
            for leaf in root.leaves()
        )
        described.append((texture.phrase.span, values, leaves))
    return described


def has_register_tie(score: Score, configuration: TexturalConfiguration, span: TimeSpan) -> bool:
    """Return whether two planes of the configuration have the same mean register."""
    means = []
    for leaf in configuration.leaves():
        semitones = [
            pitch.sounding_semitones()
            for stream in leaf.streams
            for attack in voice_attacks(score, stream, span)
            for pitch in attack.pitches
        ]
        means.append(Fraction(sum(semitones), len(semitones)))
    return len(set(means)) != len(means)


@given(scores())
def test_two_runs_give_equal_analyses_that_pass_the_validators(score: Score) -> None:
    first = analysis_of(score)
    second = analyze_texture(score, SETTINGS)

    assert first == second
    assert TexturalAnalysis.model_validate(first.model_dump()) == first


@given(scores())
def test_every_linear_leaf_is_minus_d_by_restriction_5(score: Score) -> None:
    for texture in analysis_of(score).phrases:
        for leaf in texture.configuration.leaves():
            if leaf.features.linearity.value:
                assert leaf.features.attack_divergence.value is False
                assert leaf.features.attack_divergence.rule is DecisionRule.RESTRICTION_5
            else:
                assert leaf.features.attack_divergence.rule is DecisionRule.ATTACKS_WITHIN_TACTUS


@settings(max_examples=HEAVY_EXAMPLES)
@given(st.data())
def test_permuting_the_parts_keeps_phrases_features_and_leaves(data: st.DataObject) -> None:
    score = data.draw(scores())
    order = data.draw(st.permutations(range(len(score.parts))))
    permuted = score.model_copy(update={"parts": tuple(score.parts[index] for index in order)})

    original, shuffled = analysis_of(score), analysis_of(permuted)

    assert summary_of(shuffled, lambda number: order[number - 1] + 1) == summary_of(
        original, lambda number: number
    )


@settings(max_examples=HEAVY_EXAMPLES)
@given(st.data())
def test_permuting_the_parts_keeps_the_compact_form_when_no_two_planes_share_a_register(
    data: st.DataObject,
) -> None:
    score = data.draw(scores())
    order = data.draw(st.permutations(range(len(score.parts))))
    permuted = score.model_copy(update={"parts": tuple(score.parts[index] for index in order)})

    original, shuffled = analysis_of(score), analysis_of(permuted)

    for before, after in zip(original.phrases, shuffled.phrases, strict=True):
        assume(not has_register_tie(score, before.configuration, before.phrase.span))
        assert compact_schema(after.configuration) == compact_schema(before.configuration)


def split_in_two(note_event: NoteEvent) -> tuple[NoteEvent, NoteEvent]:
    """Return an event as two halves, the second one attacking again at its midpoint."""
    middle = note_event.onset + note_event.duration / 2
    halves = []
    for onset, duration, ties in (
        (note_event.onset, note_event.duration / 2, FIRST_HALF_TIE),
        (middle, note_event.duration / 2, SECOND_HALF_TIE),
    ):
        halves.append(
            note_event.model_copy(
                update={
                    "onset": onset,
                    "duration": duration,
                    "pitches": tuple(
                        EventPitch(pitch=item.pitch, tie=ties[item.tie])
                        for item in note_event.pitches
                    ),
                }
            )
        )
    return halves[0], halves[1]


@settings(max_examples=HEAVY_EXAMPLES)
@given(st.data())
def test_an_added_attack_beside_the_attack_of_another_plane_makes_the_root_plus_d(
    data: st.DataObject,
) -> None:
    score = data.draw(scores())
    stream = data.draw(st.sampled_from(stream_references(score)))
    voice = score.parts[stream.part_number - 1].voices[stream.voice_number - 1]
    candidates = [index for index, item in enumerate(voice.events) if not item.fermata]
    assume(candidates)
    index = data.draw(st.sampled_from(candidates))
    first_half, second_half = split_in_two(voice.events[index])
    events = (*voice.events[:index], first_half, second_half, *voice.events[index + 1 :])
    new_voice = NotatedVoice(
        events=events, grace_notes=voice.grace_notes, rest_fermatas=voice.rest_fermatas
    )
    parts = list(score.parts)
    voices = list(parts[stream.part_number - 1].voices)
    voices[stream.voice_number - 1] = new_voice
    parts[stream.part_number - 1] = parts[stream.part_number - 1].model_copy(
        update={"voices": tuple(voices)}
    )
    modified = score.model_copy(update={"parts": tuple(parts)})
    new_attack = second_half.onset
    whole = TimeSpan(onset=Fraction(0), end=score.end())
    assume(
        all(
            attack.onset != new_attack
            for other in stream_references(score)
            for attack in voice_attacks(score, other, whole)
        )
    )

    fused = fuse_doublings(modified, SETTINGS.doublings)
    assume(fused == fuse_doublings(score, SETTINGS.doublings))
    analysis = analysis_of(modified)

    group = next(f for f in fused if stream in f.streams)
    texture = next(
        t for t in analysis.phrases if t.phrase.span.onset <= new_attack < t.phrase.span.end
    )
    tactus = next(
        t for t in tactus_spans(modified, texture.phrase.span) if t.onset <= new_attack < t.end
    )
    other_plane_attacks = any(
        tactus.onset <= attack.onset < tactus.end
        for other in stream_references(modified)
        if other not in group.streams
        for attack in voice_attacks(modified, other, texture.phrase.span)
    )
    assume(other_plane_attacks)
    assert texture.configuration.features.attack_divergence.value is True
