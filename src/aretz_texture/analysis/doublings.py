"""Fusion of doublings: notated voices heard as one line with density (spec 002, section 3.5)."""

from fractions import Fraction

from pydantic import BaseModel, ConfigDict

from aretz_texture.analysis.attacks import Attack, stream_references, voice_attacks
from aretz_texture.analysis.settings import DoublingSettings
from aretz_texture.core.score import Score
from aretz_texture.core.texture import StreamReference, TimeSpan


class FusedStream(BaseModel):
    """The notated voices joined by doubling into one stream; most hold a single voice."""

    model_config = ConfigDict(frozen=True)

    streams: tuple[StreamReference, ...]  # sorted by part number, then voice number


def coinciding_attack_proportion(
    first: tuple[Attack, ...],
    second: tuple[Attack, ...],
) -> Fraction:
    """Return the share of the sparser voice's attacks that coincide with the other voice's.

    Two attacks coincide when they have the same onset and share at least one pitch class: a
    doubling at the unison or at any number of octaves (Fessel 2000, pp. 85 to 88).

    Args:
        first: The attacks of one notated voice over the whole score.
        second: The attacks of the other notated voice.

    Returns:
        The number of coinciding attack pairs over the attack count of the voice with fewer
        attacks; 0 when either voice has no attack.
    """
    if not first or not second:
        return Fraction(0)
    pitch_classes_by_onset = {
        attack.onset: {pitch.pitch_class() for pitch in attack.pitches} for attack in second
    }
    coinciding = sum(
        1
        for attack in first
        if attack.onset in pitch_classes_by_onset
        and pitch_classes_by_onset[attack.onset] & {pitch.pitch_class() for pitch in attack.pitches}
    )
    return Fraction(coinciding, min(len(first), len(second)))


def fuse_doublings(score: Score, settings: DoublingSettings) -> tuple[FusedStream, ...]:
    """Fuse the notated voices that double each other over the whole score.

    Two voices are doublings when their coinciding attack proportion reaches
    `minimum_coinciding_attack_proportion`; fused streams are the connected groups of that
    relation. Every notated voice belongs to exactly one fused stream, most of them alone.
    Fusion is computed once over the whole score, because the doublings of a chorale come
    from its instrumentation (ADR 0005).

    Args:
        score: The score.
        settings: The threshold of the coinciding proportion.

    Returns:
        The fused streams ordered by their first notated voice.
    """
    streams = stream_references(score)
    whole_score = TimeSpan(onset=Fraction(0), end=score.end())
    attacks = [voice_attacks(score, stream, whole_score) for stream in streams]
    group_of = list(range(len(streams)))  # the smallest index of the group, found by union
    for later in range(len(streams)):
        for earlier in range(later):
            proportion = coinciding_attack_proportion(attacks[earlier], attacks[later])
            if proportion >= settings.minimum_coinciding_attack_proportion:
                _join(group_of, earlier, later)
    members: dict[int, list[StreamReference]] = {}
    for index, stream in enumerate(streams):
        members.setdefault(_root(group_of, index), []).append(stream)
    return tuple(FusedStream(streams=tuple(members[root])) for root in sorted(members))


def _root(group_of: list[int], index: int) -> int:
    while group_of[index] != index:
        index = group_of[index]
    return index


def _join(group_of: list[int], first: int, second: int) -> None:
    first_root, second_root = _root(group_of, first), _root(group_of, second)
    group_of[max(first_root, second_root)] = min(first_root, second_root)
