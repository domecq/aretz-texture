"""Hypothesis strategies for chords: a spelled chord with its voicing, and sets of pitch names."""

from dataclasses import dataclass

from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from aretz_texture.core.harmony import ChordIdentity, ChordQuality, PitchName
from aretz_texture.core.notation import (
    SEMITONES_OF_STEP,
    SEMITONES_PER_OCTAVE,
    STEP_NAMES,
    SpelledPitch,
)

# Semitones above the root of the third, fifth and (for sevenths) seventh of each quality.
CHORD_SEMITONES: dict[ChordQuality, tuple[int, ...]] = {
    ChordQuality.MAJOR: (4, 7),
    ChordQuality.MINOR: (3, 7),
    ChordQuality.DIMINISHED: (3, 6),
    ChordQuality.AUGMENTED: (4, 8),
    ChordQuality.DOMINANT_SEVENTH: (4, 7, 10),
    ChordQuality.MAJOR_SEVENTH: (4, 7, 11),
    ChordQuality.MINOR_SEVENTH: (3, 7, 10),
    ChordQuality.HALF_DIMINISHED_SEVENTH: (3, 6, 10),
    ChordQuality.DIMINISHED_SEVENTH: (3, 6, 9),
}
LETTERS_ABOVE_ROOT = (2, 4, 6)  # third, fifth, seventh
MIN_BASS_OCTAVE, MAX_BASS_OCTAVE = 2, 4
OCTAVES_ABOVE_BASS = 3
MAX_DOUBLINGS = 3


@dataclass(frozen=True)
class SpelledChord:
    """A chord as a generator built it: what it should be read as and the pitches that sound."""

    identity: ChordIdentity
    pitches: tuple[SpelledPitch, ...]  # highest first, doublings kept, the bass last


def _spelled_member(root: PitchName, letters_above: int, semitones: int) -> PitchName:
    """Return the member `letters_above` letters over the root, spelled `semitones` above it."""
    letter = STEP_NAMES[(STEP_NAMES.index(root.step) + letters_above) % len(STEP_NAMES)]
    root_class = SEMITONES_OF_STEP[root.step] + root.alter
    natural_class = SEMITONES_OF_STEP[letter]
    alter = (root_class + semitones - natural_class + 6) % SEMITONES_PER_OCTAVE - 6
    return PitchName.model_construct(step=letter, alter=alter)


def _chord_members(root: PitchName, quality: ChordQuality) -> tuple[PitchName, ...]:
    """Return the root, third, fifth and, for a seventh chord, seventh, spelled by letters.

    Members are built without validation, so that one needing three accidentals can be told.
    """
    above = tuple(
        _spelled_member(root, letters, semitones)
        for letters, semitones in zip(LETTERS_ABOVE_ROOT, CHORD_SEMITONES[quality], strict=False)
    )
    return (root, *above)


def _pitch_above(draw: DrawFn, name: PitchName, bass: SpelledPitch) -> SpelledPitch:
    """Return a pitch of this name strictly above the bass, within a few octaves of it."""
    candidates = [
        SpelledPitch(step=name.step, alter=name.alter, octave=octave)
        for octave in range(bass.octave, bass.octave + OCTAVES_ABOVE_BASS + 1)
    ]
    return draw(
        st.sampled_from(
            [
                pitch
                for pitch in candidates
                if pitch.sounding_semitones() > bass.sounding_semitones()
            ]
        )
    )


def _is_spellable(members: tuple[PitchName, ...]) -> bool:
    return all(-2 <= member.alter <= 2 for member in members)


def _spellable_roots_and_qualities() -> list[tuple[PitchName, ChordQuality]]:
    """Return the roots (alter -1 to 1) and qualities whose members need at most two accidentals.

    F flat with a diminished seventh would need E triple flat, which no pitch name has.
    """
    roots = [PitchName(step=step, alter=alter) for step in STEP_NAMES for alter in (-1, 0, 1)]
    return [
        (root, quality)
        for root in roots
        for quality in ChordQuality
        if _is_spellable(_chord_members(root, quality))
    ]


@st.composite
def spelled_chords(draw: DrawFn) -> SpelledChord:
    """Generate a chord of any quality with a root of alter -1 to 1, any inversion and doublings."""
    root, quality = draw(st.sampled_from(_spellable_roots_and_qualities()))
    members = _chord_members(root, quality)
    inversion = draw(st.integers(min_value=0, max_value=len(members) - 1))
    bass_name = members[inversion]
    bass = SpelledPitch(
        step=bass_name.step,
        alter=bass_name.alter,
        octave=draw(st.integers(min_value=MIN_BASS_OCTAVE, max_value=MAX_BASS_OCTAVE)),
    )
    upper_names = [name for index, name in enumerate(members) if index != inversion]
    upper_names += draw(st.lists(st.sampled_from(members), max_size=MAX_DOUBLINGS))
    upper = [_pitch_above(draw, name, bass) for name in upper_names]
    pitches = sorted([*upper, bass], key=SpelledPitch.highest_first_key)
    return SpelledChord(
        identity=ChordIdentity(root=root, quality=quality, bass=bass_name, inversion=inversion),
        pitches=tuple(pitches),
    )


def pitch_names() -> st.SearchStrategy[PitchName]:
    """Generate a pitch name with up to two accidentals."""
    return st.builds(
        PitchName, step=st.sampled_from(STEP_NAMES), alter=st.integers(min_value=-2, max_value=2)
    )
