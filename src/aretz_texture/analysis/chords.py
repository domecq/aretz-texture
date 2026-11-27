"""Chord identification by stacked thirds (spec 003, section 3.5; ADR 0007, reading 8)."""

from itertools import pairwise

from aretz_texture.core.harmony import (
    ChordIdentity,
    ChordQuality,
    HarmonicWindow,
    PitchName,
    UnidentifiedSonority,
)
from aretz_texture.core.notation import (
    SEMITONES_OF_STEP,
    SEMITONES_PER_OCTAVE,
    STEP_NAMES,
    SpelledPitch,
)

# Letters (steps) a member of a tertian chord lies above its root, music theory not a setting.
THIRD_LETTERS, FIFTH_LETTERS, SEVENTH_LETTERS = 2, 4, 6
LETTERS_PER_INVERSION_STEP = 2  # each inversion moves the bass up one chord member, two letters
PERFECT_FIFTH_SEMITONES = 7  # an absent fifth is read as perfect (ADR 0007, reading 8)

# The vocabulary: (semitones of the third, of the fifth, of the seventh or None) to the quality.
CHORD_VOCABULARY: dict[tuple[int, int, int | None], ChordQuality] = {
    (4, 7, None): ChordQuality.MAJOR,
    (3, 7, None): ChordQuality.MINOR,
    (3, 6, None): ChordQuality.DIMINISHED,
    (4, 8, None): ChordQuality.AUGMENTED,
    (4, 7, 10): ChordQuality.DOMINANT_SEVENTH,
    (4, 7, 11): ChordQuality.MAJOR_SEVENTH,
    (3, 7, 10): ChordQuality.MINOR_SEVENTH,
    (3, 6, 10): ChordQuality.HALF_DIMINISHED_SEVENTH,
    (3, 6, 9): ChordQuality.DIMINISHED_SEVENTH,
}


def identify_chord(window: HarmonicWindow) -> ChordIdentity | UnidentifiedSonority:
    """Read the chord tones of a window as a chord of the vocabulary, or say why not.

    The root is the pitch name from which every other name lies a third, a fifth or a seventh
    above by letter, with at least one third; the sizes of those intervals give the quality.
    An unidentified sonority is a reading, not an error (ADR 0007, reading 8).

    Args:
        window: The harmonic window; its chord tones are read, its bass gives the inversion.

    Returns:
        The chord identity, or an unidentified sonority with its pitch names and the reason.
    """
    names = _distinct_names(window.chord_tones)
    same_letter = _first_pair_on_one_letter(names)
    if same_letter is not None:
        first, second = same_letter
        return UnidentifiedSonority(
            pitch_names=names, reason=f"{first.text()} and {second.text()} in one window"
        )
    roots = candidate_roots(names)
    if not roots:
        return UnidentifiedSonority(pitch_names=names, reason=_reason_without_root(names))
    return _chord_over(roots[0], names, _name_of(window.bass()))


def candidate_roots(names: tuple[PitchName, ...]) -> tuple[PitchName, ...]:
    """Return the names that qualify as the root of a stack of thirds; at most one does.

    Args:
        names: Distinct pitch names, in any order.

    Returns:
        The names from which every other name lies 2, 4 or 6 letters above, with at least
        one 2 letters above: none or one name, in a tuple.
    """
    return tuple(name for name in sorted(names, key=_letter_order) if _stacks_over(name, names))


def _name_of(pitch: SpelledPitch) -> PitchName:
    return PitchName(step=pitch.step, alter=pitch.alter)


def _letter_order(name: PitchName) -> tuple[int, int]:
    return (STEP_NAMES.index(name.step), name.alter)


def _distinct_names(pitches: tuple[SpelledPitch, ...]) -> tuple[PitchName, ...]:
    keys = {(STEP_NAMES.index(pitch.step), pitch.alter) for pitch in pitches}
    return tuple(PitchName(step=STEP_NAMES[letter], alter=alter) for letter, alter in sorted(keys))


def _letters_above(root: PitchName, name: PitchName) -> int:
    return (STEP_NAMES.index(name.step) - STEP_NAMES.index(root.step)) % len(STEP_NAMES)


def _semitones_above(root: PitchName, name: PitchName) -> int:
    root_class = SEMITONES_OF_STEP[root.step] + root.alter
    name_class = SEMITONES_OF_STEP[name.step] + name.alter
    return (name_class - root_class) % SEMITONES_PER_OCTAVE


def _stacks_over(root: PitchName, names: tuple[PitchName, ...]) -> bool:
    distances = {_letters_above(root, name) for name in names if name != root}
    return THIRD_LETTERS in distances and distances <= {
        THIRD_LETTERS,
        FIFTH_LETTERS,
        SEVENTH_LETTERS,
    }


def _first_pair_on_one_letter(names: tuple[PitchName, ...]) -> tuple[PitchName, PitchName] | None:
    for first, second in pairwise(names):
        if first.step == second.step:
            return first, second
    return None


def _reason_without_root(names: tuple[PitchName, ...]) -> str:
    if any(_letters_above(low, high) == THIRD_LETTERS for low in names for high in names):
        return "the pitches do not stack in thirds from one root"
    return "no third above any pitch"


def _chord_over(
    root: PitchName, names: tuple[PitchName, ...], bass: PitchName
) -> ChordIdentity | UnidentifiedSonority:
    above = {_letters_above(root, name): _semitones_above(root, name) for name in names}
    third, fifth, seventh = (
        above[THIRD_LETTERS],
        above.get(FIFTH_LETTERS),
        above.get(SEVENTH_LETTERS),
    )
    quality = CHORD_VOCABULARY.get((third, fifth or PERFECT_FIFTH_SEMITONES, seventh))
    if quality is None:
        reason = (
            f"{root.text()} with third {third}, fifth {_semitones_text(fifth)} and seventh "
            f"{_semitones_text(seventh)} semitones is outside the vocabulary"
        )
        return UnidentifiedSonority(pitch_names=names, reason=reason)
    inversion = _letters_above(root, bass) // LETTERS_PER_INVERSION_STEP
    return ChordIdentity(root=root, quality=quality, bass=bass, inversion=inversion)


def _semitones_text(semitones: int | None) -> str:
    return "none" if semitones is None else str(semitones)
