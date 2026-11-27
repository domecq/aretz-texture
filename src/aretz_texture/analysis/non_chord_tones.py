"""Non chord tones: passing, neighbor, anticipation and suspension (spec 003, section 3.4)."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from fractions import Fraction

from aretz_texture.analysis.metric_grid import tactus_at, tactus_spans
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.core.harmony import NonChordTone, NonChordToneKind, SoundingNote
from aretz_texture.core.notation import SEMITONES_PER_OCTAVE, SpelledPitch
from aretz_texture.core.score import Score
from aretz_texture.core.texture import TimeSpan

# Interval classes (semitones modulo the octave) that two voice counterpoint hears as
# dissonant between two voices: seconds and sevenths. Music theory, not settings.
DISSONANT_INTERVAL_CLASSES = frozenset({1, 2, 10, 11})
# The fourth is dissonant only above the lowest sounding pitch (the bass), as in two voice
# counterpoint.
DISSONANT_ABOVE_BASS_INTERVAL_CLASSES = frozenset({5})


@dataclass(frozen=True)
class _Neighbors:
    """The notes of a voice that touch a note: the one ending where it begins and the next."""

    previous: SoundingNote | None
    following: SoundingNote | None


@dataclass(frozen=True)
class _Grid:
    """What the rules read besides the notes: the metric grid and the thresholds."""

    score: Score
    settings: NonChordToneSettings
    tactus_onsets: tuple[Fraction, ...]  # ascending
    notes: tuple[SoundingNote, ...]  # every note, of every voice

    def is_accented(self, note: SoundingNote) -> bool:
        index = bisect_left(self.tactus_onsets, note.onset)
        return index < len(self.tactus_onsets) and self.tactus_onsets[index] == note.onset

    def first_tactus_onset_after(self, moment: Fraction) -> Fraction | None:
        index = bisect_right(self.tactus_onsets, moment)
        return self.tactus_onsets[index] if index < len(self.tactus_onsets) else None


def classify_non_chord_tones(
    score: Score, notes: tuple[SoundingNote, ...], settings: NonChordToneSettings
) -> tuple[NonChordTone, ...]:
    """Classify the passing tones, neighbor tones, anticipations and suspensions of a phrase.

    Each rule reads only the note, its adjacent notes in its voice and the pitches sounding
    at a tactus onset, never the classification of another note, so the result does not
    depend on the order of evaluation. Only notes of voices without a divided event at the
    note or at its two neighbors are classified (ADR 0007, readings 5 and 6).

    Args:
        score: The score whose bars give the metric grid.
        notes: The sounding notes of a phrase, of all its notated voices.
        settings: The thresholds of the rules.

    Returns:
        The non chord tones by the onset from which they stop being chord tones.
    """
    grid = _Grid(
        score=score,
        settings=settings,
        tactus_onsets=_tactus_onsets(score),
        notes=notes,
    )
    tones: list[NonChordTone] = []
    for voice in _voices_of(notes):
        for index in range(len(voice)):
            neighbors = _neighbors_of(index, voice)
            tone = None if neighbors is None else _classify(voice[index], neighbors, grid)
            if tone is not None:
                tones.append(tone)
    return tuple(
        sorted(
            tones,
            key=lambda tone: (
                tone.from_onset,
                tone.note.onset,
                tone.note.pitch.highest_first_key(),
            ),
        )
    )


def _tactus_onsets(score: Score) -> tuple[Fraction, ...]:
    whole_score = TimeSpan(onset=Fraction(0), end=score.end())
    return tuple(span.onset for span in tactus_spans(score, whole_score))


def _voices_of(notes: tuple[SoundingNote, ...]) -> list[list[SoundingNote]]:
    voices: dict[tuple[int, int], list[SoundingNote]] = {}
    for note in notes:
        key = (note.stream.part_number, note.stream.voice_number)
        voices.setdefault(key, []).append(note)
    return [
        sorted(voice, key=lambda note: (note.onset, note.end, note.pitch.highest_first_key()))
        for _, voice in sorted(voices.items())
    ]


def _is_alone(note: SoundingNote, voice: list[SoundingNote]) -> bool:
    """Return whether no other note of the voice sounds at the same time."""
    return all(
        other is note or other.end <= note.onset or other.onset >= note.end for other in voice
    )


def _neighbors_of(index: int, voice: list[SoundingNote]) -> _Neighbors | None:
    """Return the adjacent notes, or None when the note or a neighbor is in a divided event."""
    note = voice[index]
    before = [other for other in voice if other.end == note.onset]
    after = [other for other in voice if other.onset == note.end]
    undivided = all(_is_alone(other, voice) for other in [note, *before, *after])
    if not undivided:
        return None
    return _Neighbors(previous=before[0] if before else None, following=after[0] if after else None)


def _classify(note: SoundingNote, neighbors: _Neighbors, grid: _Grid) -> NonChordTone | None:
    # A descending passing tone can also meet the suspension rule when it straddles a tactus
    # onset; the suspension is the more specific reading, so it is tried first.
    return _suspension(note, neighbors, grid) or _unaccented_tone(note, neighbors, grid)


def _semitones_between(first: SpelledPitch, second: SpelledPitch) -> int:
    """Return the signed distance from the first pitch up to the second, in semitones."""
    return second.sounding_semitones() - first.sounding_semitones()


def _is_step(semitones: int, grid: _Grid) -> bool:
    return 1 <= abs(semitones) <= grid.settings.maximum_melodic_step_semitones


def _unaccented_tone(note: SoundingNote, neighbors: _Neighbors, grid: _Grid) -> NonChordTone | None:
    previous, following = neighbors.previous, neighbors.following
    if previous is None or following is None or grid.is_accented(note):
        return None
    longest = grid.settings.maximum_unaccented_duration * tactus_at(grid.score, note.onset)
    if note.end - note.onset > longest:
        return None
    step_in = _semitones_between(previous.pitch, note.pitch)
    step_out = _semitones_between(note.pitch, following.pitch)
    kind = _unaccented_kind(step_in, step_out, note, grid)
    if kind is None:
        return None
    return NonChordTone(note=note, kind=kind, from_onset=note.onset, resolution=None)


def _unaccented_kind(
    step_in: int, step_out: int, note: SoundingNote, grid: _Grid
) -> NonChordToneKind | None:
    if not _is_step(step_in, grid):
        return None
    if step_out == 0:
        return _anticipation_kind(note, grid)
    if not _is_step(step_out, grid):
        return None
    return _kind_of_two_steps(step_in, step_out)


def _kind_of_two_steps(step_in: int, step_out: int) -> NonChordToneKind | None:
    if step_in * step_out > 0:
        return NonChordToneKind.PASSING
    # Opposite directions: a neighbor only when the note comes back to where it left.
    return NonChordToneKind.NEIGHBOR if step_in + step_out == 0 else None


def _anticipation_kind(note: SoundingNote, grid: _Grid) -> NonChordToneKind | None:
    """Return the anticipation kind when the repeated pitch starts at the next tactus onset."""
    is_next_tactus = grid.first_tactus_onset_after(note.onset) == note.end
    return NonChordToneKind.ANTICIPATION if is_next_tactus else None


def _suspension(note: SoundingNote, neighbors: _Neighbors, grid: _Grid) -> NonChordTone | None:
    following = neighbors.following
    if following is None:
        return None
    step_down = _semitones_between(note.pitch, following.pitch)
    if not _is_step(step_down, grid) or step_down > 0:
        return None
    longest = grid.settings.maximum_suspension_duration * tactus_at(grid.score, note.onset)
    for onset, prepared in _suspension_candidates(note, neighbors.previous, grid):
        if (
            note.end <= onset + longest
            and _is_dissonant_at(note, onset, grid)
            and not _is_dissonant_at(prepared, prepared.onset, grid)
        ):
            return NonChordTone(
                note=note,
                kind=NonChordToneKind.SUSPENSION,
                from_onset=onset,
                resolution=following.pitch,
            )
    return None


def _suspension_candidates(
    note: SoundingNote, previous: SoundingNote | None, grid: _Grid
) -> list[tuple[Fraction, SoundingNote]]:
    """Return the tactus onsets at which the note could be a suspension, with its preparation.

    Tied over: the first tactus onset after the attack, if the note still sounds; the note
    itself is prepared at its onset. Repeated: the attack itself, when it falls on a tactus
    onset after a note of the same pitch, which is the preparation.
    """
    candidates: list[tuple[Fraction, SoundingNote]] = []
    first_after = grid.first_tactus_onset_after(note.onset)
    if first_after is not None and first_after < note.end:
        candidates.append((first_after, note))
    repeats_previous = previous is not None and _semitones_between(previous.pitch, note.pitch) == 0
    if previous is not None and repeats_previous and grid.is_accented(note):
        candidates.append((note.onset, previous))
    return candidates


def _is_dissonant_at(note: SoundingNote, moment: Fraction, grid: _Grid) -> bool:
    """Return whether the note forms a dissonance with a pitch sounding at the moment."""
    others = [
        other for other in grid.notes if other is not note and other.onset <= moment < other.end
    ]
    if not others:
        return False
    lowest = min(other.pitch.sounding_semitones() for other in [note, *others])
    above_bass = (note.pitch.sounding_semitones() - lowest) % SEMITONES_PER_OCTAVE
    if above_bass in DISSONANT_ABOVE_BASS_INTERVAL_CLASSES:
        return True
    return any(
        abs(_semitones_between(other.pitch, note.pitch)) % SEMITONES_PER_OCTAVE
        in DISSONANT_INTERVAL_CLASSES
        for other in others
    )
