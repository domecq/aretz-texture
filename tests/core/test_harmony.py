from fractions import Fraction

import pytest
from pydantic import ValidationError
from tests.core_builders import spelled_pitch

from aretz_texture.core.harmony import (
    HarmonicWindow,
    NonChordTone,
    NonChordToneKind,
    PitchName,
    PlaneNote,
    SoundingNote,
)
from aretz_texture.core.texture import StreamReference, TimeSpan


def stream(part_number: int = 1) -> StreamReference:
    return StreamReference(part_number=part_number, voice_number=1, part_name=None)


def sounding_note(pitch: str = "C4", onset: int = 0, end: int = 1) -> SoundingNote:
    return SoundingNote(
        stream=stream(), pitch=spelled_pitch(pitch), onset=Fraction(onset), end=Fraction(end)
    )


def non_chord_tone(
    kind: NonChordToneKind, resolution: str | None, from_onset: int = 0
) -> NonChordTone:
    return NonChordTone(
        note=sounding_note(),
        kind=kind,
        from_onset=Fraction(from_onset),
        resolution=None if resolution is None else spelled_pitch(resolution),
    )


def plane_note(plane_number: int, pitch: str = "C4") -> PlaneNote:
    return PlaneNote(plane_number=plane_number, pitch=spelled_pitch(pitch), stream=stream())


def window(
    chord_tones: tuple[str, ...] = ("E4", "C4"),
    plane_notes: tuple[PlaneNote, ...] = (),
    plane_count: int = 2,
) -> HarmonicWindow:
    return HarmonicWindow(
        span=TimeSpan(onset=Fraction(0), end=Fraction(1)),
        phrase_number=1,
        plane_count=plane_count,
        chord_tones=tuple(spelled_pitch(name) for name in chord_tones),
        plane_notes=plane_notes,
        non_chord_tones=(),
        fermata=False,
    )


@pytest.mark.parametrize(
    ("step", "alter", "text"),
    [
        ("C", 0, "C"),
        ("F", 1, "F#"),
        ("B", -1, "Bb"),
        ("F", 2, "F##"),
        ("E", -2, "Ebb"),
    ],
)
def test_a_pitch_name_is_written_with_ascii_sharps_and_flats(
    step: str, alter: int, text: str
) -> None:
    assert PitchName(step=step, alter=alter).text() == text  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize("alter", [-3, 3])
def test_a_pitch_name_rejects_an_alter_beyond_two_accidentals(alter: int) -> None:
    with pytest.raises(ValidationError):
        PitchName(step="C", alter=alter)


def test_every_model_is_immutable() -> None:
    models = [
        PitchName(step="C", alter=0),
        sounding_note(),
        non_chord_tone(NonChordToneKind.PASSING, None),
        plane_note(1),
        window(),
    ]

    for model in models:
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValidationError):
            setattr(model, field, getattr(model, field))


def test_chord_tones_must_be_ordered_from_the_highest() -> None:
    with pytest.raises(ValidationError, match="highest to lowest"):
        window(chord_tones=("C4", "E4"))


def test_chord_tones_may_not_be_empty() -> None:
    with pytest.raises(ValidationError, match="chord tone"):
        window(chord_tones=())


def test_chord_tones_keep_doublings() -> None:
    assert len(window(chord_tones=("C5", "C5", "E4")).chord_tones) == 3


def test_the_bass_is_the_lowest_chord_tone() -> None:
    assert window(chord_tones=("G4", "E4", "C3")).bass() == spelled_pitch("C3")


def test_plane_notes_must_be_ordered_by_plane_number() -> None:
    with pytest.raises(ValidationError, match="ordered"):
        window(plane_notes=(plane_note(2), plane_note(1)))


def test_plane_notes_may_not_repeat_a_plane() -> None:
    with pytest.raises(ValidationError, match="ordered"):
        window(plane_notes=(plane_note(1), plane_note(1)))


def test_a_plane_note_may_not_exceed_the_plane_count() -> None:
    with pytest.raises(ValidationError, match="plane count"):
        window(plane_notes=(plane_note(3),), plane_count=2)


def test_a_plane_number_starts_at_one() -> None:
    with pytest.raises(ValidationError, match="plane count"):
        window(plane_notes=(plane_note(0),))


def test_a_suspension_needs_a_resolution() -> None:
    with pytest.raises(ValidationError, match="resolution"):
        non_chord_tone(NonChordToneKind.SUSPENSION, None)


@pytest.mark.parametrize(
    "kind", [NonChordToneKind.PASSING, NonChordToneKind.NEIGHBOR, NonChordToneKind.ANTICIPATION]
)
def test_a_resolution_on_another_kind_is_rejected(kind: NonChordToneKind) -> None:
    with pytest.raises(ValidationError, match="resolution"):
        non_chord_tone(kind, "B3")


def test_a_suspension_with_a_resolution_is_accepted() -> None:
    assert non_chord_tone(NonChordToneKind.SUSPENSION, "B3").resolution == spelled_pitch("B3")


def test_a_sounding_note_must_end_after_its_onset() -> None:
    with pytest.raises(ValidationError, match="end"):
        sounding_note(onset=1, end=1)
