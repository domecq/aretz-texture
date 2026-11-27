"""Criterion 31 for readings: determinism and independence of the order of the parts."""

from hypothesis import HealthCheck, given, reject, settings
from hypothesis import strategies as st
from tests.strategies import scores

from aretz_texture.analysis.harmonic_segmentation import segment_harmony
from aretz_texture.analysis.harmony import analyze_surface_harmony
from aretz_texture.analysis.settings import NonChordToneSettings, TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.errors import SilentPhraseError
from aretz_texture.core.harmony import HarmonicEvent
from aretz_texture.core.score import Score

HEAVY_EXAMPLES = 50  # the examples of these properties analyze two scores each
# As in the segmentation properties: the score is drawn and then analyzed twice inside the
# test, so the too_slow health check fires at random on a loaded machine; examples are capped.
HEAVY_SETTINGS = settings(max_examples=HEAVY_EXAMPLES, suppress_health_check=[HealthCheck.too_slow])


def surface_events(score: Score) -> tuple[HarmonicEvent, ...]:
    """Read the surface harmony of a score, discarding the generated ones without an attack."""
    try:
        texture = analyze_texture(score, TexturalAnalysisSettings())
    except SilentPhraseError:
        reject()
    return analyze_surface_harmony(score, texture, NonChordToneSettings())


@given(scores())
def test_every_window_of_any_score_has_exactly_one_surface_event(score: Score) -> None:
    try:
        texture = analyze_texture(score, TexturalAnalysisSettings())
    except SilentPhraseError:
        reject()
    windows = segment_harmony(score, texture, NonChordToneSettings())

    events = analyze_surface_harmony(score, texture, NonChordToneSettings())

    assert [event.windows for event in events] == [(window,) for window in windows]


@given(scores())
def test_two_runs_give_equal_events(score: Score) -> None:
    assert surface_events(score) == surface_events(score)


@HEAVY_SETTINGS
@given(st.data())
def test_permuting_the_parts_does_not_change_the_readings_or_the_spans(
    data: st.DataObject,
) -> None:
    score = data.draw(scores())
    order = data.draw(st.permutations(range(len(score.parts))))
    permuted = score.model_copy(update={"parts": tuple(score.parts[index] for index in order)})

    assert [(event.span, event.reading) for event in surface_events(permuted)] == [
        (event.span, event.reading) for event in surface_events(score)
    ]
