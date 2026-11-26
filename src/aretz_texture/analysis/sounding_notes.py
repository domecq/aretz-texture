"""Sounding notes: the notes of a notated voice joined across ties (spec 003, section 3.4)."""

from dataclasses import dataclass
from fractions import Fraction

from aretz_texture.analysis.attacks import CONTINUING_TIES
from aretz_texture.core.harmony import SoundingNote
from aretz_texture.core.notation import NoteEvent, SpelledPitch
from aretz_texture.core.score import Score
from aretz_texture.core.texture import StreamReference, TimeSpan


@dataclass
class _Chain:
    """A tie chain still open while the events of a voice are walked in order."""

    pitch: SpelledPitch
    onset: Fraction
    end: Fraction


def sounding_notes(
    score: Score, stream: StreamReference, span: TimeSpan
) -> tuple[SoundingNote, ...]:
    """Return the sounding notes of a notated voice inside a phrase.

    Each pitch of each event is a note, joined with the following events of its tie chain
    from the first onset to the last end. Chains are clipped to the span, so each phrase is
    analyzed alone. Grace notes and rest fermatas take no part in the harmony (ADR 0007,
    reading 2).

    Args:
        score: The score holding the voice.
        stream: Which notated voice of which part.
        span: The phrase whose notes are wanted.

    Returns:
        The notes by onset, then from the highest pitch down.
    """
    voice = score.parts[stream.part_number - 1].voices[stream.voice_number - 1]
    chains: list[_Chain] = []
    still_open: list[_Chain] = []
    for note_event in voice.events:
        if note_event.end() <= span.onset or note_event.onset >= span.end:
            continue
        still_open = _extend_chains(note_event, still_open, chains)
    notes = [_clipped_note(chain, stream, span) for chain in chains]
    return tuple(sorted(notes, key=lambda note: (note.onset, note.pitch.highest_first_key())))


def _extend_chains(
    note_event: NoteEvent, still_open: list[_Chain], chains: list[_Chain]
) -> list[_Chain]:
    """Join each pitch of an event to the open chain it continues, or open a new chain."""
    continuable = [chain for chain in still_open if chain.end == note_event.onset]
    open_after: list[_Chain] = []
    for event_pitch in note_event.pitches:
        chain = None
        if event_pitch.tie in CONTINUING_TIES:
            chain = next((c for c in continuable if c.pitch == event_pitch.pitch), None)
        if chain is None:
            chain = _Chain(event_pitch.pitch, note_event.onset, note_event.end())
            chains.append(chain)
        else:
            continuable.remove(chain)
            chain.end = note_event.end()
        open_after.append(chain)
    return open_after


def _clipped_note(chain: _Chain, stream: StreamReference, span: TimeSpan) -> SoundingNote:
    return SoundingNote(
        stream=stream,
        pitch=chain.pitch,
        onset=max(chain.onset, span.onset),
        end=min(chain.end, span.end),
    )
