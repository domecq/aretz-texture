"""Hypothesis properties of chord identification (spec 003, section 5)."""

from hypothesis import given
from hypothesis import strategies as st
from tests.chord_strategies import SpelledChord, pitch_names, spelled_chords
from tests.core_builders import harmonic_window

from aretz_texture.analysis.chords import candidate_roots, identify_chord
from aretz_texture.core.harmony import PitchName
from aretz_texture.core.notation import STEP_NAMES


@given(spelled_chords())
def test_identification_recovers_root_quality_bass_and_inversion_of_any_built_chord(
    chord: SpelledChord,
) -> None:
    assert identify_chord(harmonic_window(chord.pitches)) == chord.identity


@given(
    st.lists(pitch_names(), min_size=1, max_size=7, unique_by=lambda name: (name.step, name.alter))
)
def test_at_most_one_root_qualifies_for_any_set_of_pitch_names(names: list[PitchName]) -> None:
    assert len(candidate_roots(tuple(names))) <= 1


@st.composite
def stacks_of_thirds(draw: st.DrawFn) -> tuple[PitchName, list[PitchName]]:
    """Return a root and names on the letters 0, 2 and some of 4 and 6 above it, any alters."""
    root_letter = draw(st.integers(min_value=0, max_value=len(STEP_NAMES) - 1))
    offsets = [0, 2, *draw(st.lists(st.sampled_from([4, 6]), unique=True))]
    names = [
        PitchName(
            step=STEP_NAMES[(root_letter + offset) % len(STEP_NAMES)],
            alter=draw(st.integers(min_value=-2, max_value=2)),
        )
        for offset in offsets
    ]
    return names[0], names


@given(stacks_of_thirds())
def test_the_root_of_names_stacked_in_thirds_is_the_only_candidate(
    stack: tuple[PitchName, list[PitchName]],
) -> None:
    root, names = stack

    assert candidate_roots(tuple(names)) == (root,)
