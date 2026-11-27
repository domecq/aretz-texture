"""Harmonic segmentation: verticalities merged into harmonic windows (spec 003, section 3.4)."""

from dataclasses import dataclass
from fractions import Fraction

from aretz_texture.analysis.attacks import voice_attacks
from aretz_texture.analysis.non_chord_tones import classify_non_chord_tones
from aretz_texture.analysis.settings import NonChordToneSettings
from aretz_texture.analysis.sounding_notes import sounding_notes
from aretz_texture.core.harmony import (
    HarmonicWindow,
    NonChordTone,
    NonChordToneKind,
    PlaneNote,
    SoundingNote,
)
from aretz_texture.core.notation import STEP_NAMES, SpelledPitch
from aretz_texture.core.score import Score
from aretz_texture.core.texture import (
    PhraseClosing,
    PhraseTexture,
    StreamReference,
    TexturalAnalysis,
    TimeSpan,
)

type StreamKey = tuple[int, int]


@dataclass(frozen=True)
class _ChordToneSpan:
    """A stretch of a sounding note during which it counts as a chord tone."""

    stream: StreamReference
    plane_number: int
    pitch: SpelledPitch  # the note's pitch, or the resolution of a suspension that has resolved
    onset: Fraction
    end: Fraction
    attack: Fraction | None  # where the voice attacks it; None for a resolution, not attacked


@dataclass(frozen=True)
class _WindowStart:
    """The reduced verticality that opens a window."""

    onset: Fraction
    chord_tones: tuple[SpelledPitch, ...]  # highest first, doublings kept


def segment_harmony(
    score: Score, texture: TexturalAnalysis, settings: NonChordToneSettings
) -> tuple[HarmonicWindow, ...]:
    """Segment the harmony of every phrase into windows, with plane notes and removed tones.

    Per phrase: sounding notes, non chord tones, reduced verticalities at every attack, and
    windows where a pitch class appears that the current window does not hold or where the
    bass changes pitch class (ADR 0007, reading 7). Pure and deterministic.

    Args:
        score: The score the texture analyzes.
        texture: Its textural analysis; the phrases and planes are read from it.
        settings: The thresholds of the non chord tone rules.

    Returns:
        The windows of all phrases in order. Those of a phrase are contiguous, from its first
        attack to the latest end of a note in it, and never cross its boundary.
    """
    return tuple(
        window
        for phrase_texture in texture.phrases
        for window in _phrase_windows(score, phrase_texture, settings)
    )


def _phrase_windows(
    score: Score, phrase_texture: PhraseTexture, settings: NonChordToneSettings
) -> tuple[HarmonicWindow, ...]:
    planes = phrase_texture.configuration.leaves()
    plane_of = {
        (stream.part_number, stream.voice_number): number
        for number, plane in enumerate(planes, start=1)
        for stream in plane.streams
    }
    notes = tuple(
        note
        for plane in planes
        for stream in plane.streams
        for note in sounding_notes(score, stream, phrase_texture.phrase.span)
    )
    tones = classify_non_chord_tones(score, notes, settings)
    spans = _chord_tone_spans(notes, tones, plane_of)
    attack_points = _reading_instants(score, phrase_texture, notes, tones)
    starts = _window_starts(attack_points, spans)
    if not starts:
        return ()
    phrase_end = max(note.end for note in notes)
    ends = [start.onset for start in starts[1:]] + [phrase_end]
    closes_at_fermata = phrase_texture.phrase.closing is PhraseClosing.FERMATA
    return tuple(
        HarmonicWindow(
            span=TimeSpan(onset=start.onset, end=end),
            phrase_number=phrase_texture.phrase.number,
            plane_count=len(planes),
            chord_tones=start.chord_tones,
            plane_notes=_plane_notes(spans, start.onset, end, len(planes)),
            non_chord_tones=tuple(tone for tone in tones if start.onset <= tone.from_onset < end),
            fermata=closes_at_fermata and index == len(starts) - 1,
        )
        for index, (start, end) in enumerate(zip(starts, ends, strict=True))
    )


def _key_of(note: SoundingNote) -> tuple[int, int, Fraction, Fraction, SpelledPitch]:
    return (note.stream.part_number, note.stream.voice_number, note.onset, note.end, note.pitch)


def _chord_tone_spans(
    notes: tuple[SoundingNote, ...],
    tones: tuple[NonChordTone, ...],
    plane_of: dict[StreamKey, int],
) -> list[_ChordToneSpan]:
    """Return when each note counts as a chord tone, with the pitch it counts as.

    A passing tone, neighbor tone or anticipation never counts; a suspension counts as itself
    before its tactus onset and as its resolution from then on (ADR 0007, reading 6).
    """
    tone_of = {_key_of(tone.note): tone for tone in tones}
    spans: list[_ChordToneSpan] = []
    for note in notes:
        number = plane_of[(note.stream.part_number, note.stream.voice_number)]
        tone = tone_of.get(_key_of(note))
        if tone is None:
            spans.append(
                _ChordToneSpan(note.stream, number, note.pitch, note.onset, note.end, note.onset)
            )
        elif tone.kind is NonChordToneKind.SUSPENSION and tone.resolution is not None:
            if note.onset < tone.from_onset:
                spans.append(
                    _ChordToneSpan(
                        note.stream, number, note.pitch, note.onset, tone.from_onset, note.onset
                    )
                )
            spans.append(
                _ChordToneSpan(
                    note.stream, number, tone.resolution, tone.from_onset, note.end, None
                )
            )
    return spans


def _verticality(spans: list[_ChordToneSpan], moment: Fraction) -> tuple[SpelledPitch, ...]:
    """Return the chord tones sounding at a moment, highest first."""
    pitches = [span.pitch for span in spans if span.onset <= moment < span.end]
    return tuple(sorted(pitches, key=lambda pitch: pitch.highest_first_key()))


def _reading_instants(
    score: Score,
    phrase_texture: PhraseTexture,
    notes: tuple[SoundingNote, ...],
    tones: tuple[NonChordTone, ...],
) -> list[Fraction]:
    """Return the instants at which a reduced verticality is read.

    Attacks of notes that are not passing tones, neighbor tones or anticipations (attacks of
    suspensions count), ends before the end of the phrase of notes that are chord tones, and
    the tactus onset of every suspension. A removed note is read nowhere: its attack would
    leave the verticality without its voice, and a window would open (ADR 0007, reading 7).
    The start of a tie chain clipped at the phrase boundary is no attack of this phrase.
    """
    removed = {_key_of(tone.note) for tone in tones if tone.kind is not NonChordToneKind.SUSPENSION}
    removed_attacks = {key[:3] for key in removed}
    streams = [
        stream for plane in phrase_texture.configuration.leaves() for stream in plane.streams
    ]
    attacks = {
        attack.onset
        for stream in streams
        for attack in voice_attacks(score, stream, phrase_texture.phrase.span)
        if (stream.part_number, stream.voice_number, attack.onset) not in removed_attacks
    }
    phrase_end = max(note.end for note in notes)
    ends = {note.end for note in notes if _key_of(note) not in removed and note.end < phrase_end}
    suspensions = {tone.from_onset for tone in tones if tone.kind is NonChordToneKind.SUSPENSION}
    # Silence before the first attack belongs to no window, so notes carried into the phrase
    # that end before it are not read.
    return sorted(instant for instant in attacks | ends | suspensions if instant >= min(attacks))


def _window_starts(
    attack_points: list[Fraction], spans: list[_ChordToneSpan]
) -> list[_WindowStart]:
    starts: list[_WindowStart] = []
    for moment in attack_points:
        verticality = _verticality(spans, moment)
        if verticality and (not starts or _opens_new_window(starts[-1], verticality)):
            starts.append(_WindowStart(onset=moment, chord_tones=verticality))
    return starts


def _opens_new_window(current: _WindowStart, verticality: tuple[SpelledPitch, ...]) -> bool:
    held = {pitch.pitch_class() for pitch in current.chord_tones}
    has_new_pitch_class = any(pitch.pitch_class() not in held for pitch in verticality)
    return (
        has_new_pitch_class
        or verticality[-1].pitch_class() != current.chord_tones[-1].pitch_class()
    )


def _plane_notes(
    spans: list[_ChordToneSpan], onset: Fraction, end: Fraction, plane_count: int
) -> tuple[PlaneNote, ...]:
    plane_notes: list[PlaneNote] = []
    for number in range(1, plane_count + 1):
        candidates = [span for span in spans if span.plane_number == number]
        chosen = _structural_span(candidates, onset, end, lowest=number == plane_count)
        if chosen is not None:
            plane_notes.append(
                PlaneNote(plane_number=number, pitch=chosen.pitch, stream=chosen.stream)
            )
    return tuple(plane_notes)


def _structural_span(
    candidates: list[_ChordToneSpan], onset: Fraction, end: Fraction, *, lowest: bool
) -> _ChordToneSpan | None:
    """Return the chord tone a plane sounds at the window onset, else the first it attacks."""
    sounding = [span for span in candidates if span.onset <= onset < span.end]
    if not sounding:
        attacked = [
            span for span in candidates if span.attack is not None and onset < span.attack < end
        ]
        if not attacked:
            return None
        first_attack = min(span.attack for span in attacked if span.attack is not None)
        sounding = [span for span in attacked if span.attack == first_attack]
    return min(sounding, key=lambda span: _plane_preference(span, lowest=lowest))


def _plane_preference(span: _ChordToneSpan, *, lowest: bool) -> tuple[int, int, int, int]:
    """Order the voices of a plane: the lowest pitch for the lowest plane, else the highest."""
    semitones = span.pitch.sounding_semitones()
    return (
        semitones if lowest else -semitones,
        STEP_NAMES.index(span.pitch.step),
        span.stream.part_number,
        span.stream.voice_number,
    )
