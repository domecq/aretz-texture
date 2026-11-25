"""Phrase segmentation of the chorales by their fermatas (spec 002, section 3.4, ADR 0005)."""

from fractions import Fraction

from pydantic import BaseModel, ConfigDict

from aretz_texture.analysis.attacks import stream_references, voice_attacks
from aretz_texture.analysis.settings import PhraseSegmentationSettings
from aretz_texture.core.score import Score
from aretz_texture.core.texture import Phrase, PhraseClosing, StreamReference, TimeSpan


class FermataCluster(BaseModel):
    """Fermatas of different notated voices that sound together, heard as one stop."""

    model_config = ConfigDict(frozen=True)

    span: TimeSpan  # from the earliest fermata onset to the latest fermata end
    boundary: Fraction  # the latest fermata end of the cluster: where the phrase ends
    ends: tuple[Fraction, ...]  # every distinct fermata end in the cluster, ascending
    streams: tuple[StreamReference, ...]  # the notated voices that carry them


def fermata_clusters(
    score: Score, settings: PhraseSegmentationSettings
) -> tuple[FermataCluster, ...]:
    """Return the clusters of fermatas that end a phrase, in order.

    Fermatas of every notated voice of every part are collected, so the result does not
    depend on part order. Fermatas whose time spans overlap, transitively, are one cluster;
    fermatas that only touch are separate. A cluster is kept when at least
    `minimum_fermata_voices` distinct notated voices contribute to it.

    Args:
        score: The score to read the fermatas of.
        settings: How many notated voices a cluster needs.

    Returns:
        The clusters in order of onset.
    """
    clusters = [_cluster_of(group) for group in _overlapping_groups(_fermatas_of(score))]
    return tuple(
        cluster for cluster in clusters if len(cluster.streams) >= settings.minimum_fermata_voices
    )


def segment_phrases(score: Score, settings: PhraseSegmentationSettings) -> tuple[Phrase, ...]:
    """Split a score into phrases, each ending at a cluster of fermatas.

    Music with attacks after the last fermata is a last phrase closing with `SCORE_END`.
    When only rests follow the last fermata, they join the last phrase, which then ends at
    the end of the score, since a phrase without attacks would have no plane. A score
    without fermatas is one phrase closing with `NO_FERMATAS`.

    Args:
        score: The score to segment.
        settings: How many notated voices a fermata cluster needs to end a phrase.

    Returns:
        Phrases numbered from 1 that tile the score from 0 to its end.
    """
    # See ADR 0005: the chorales end their phrases at fermatas, whatever the part order.
    boundaries = [cluster.boundary for cluster in fermata_clusters(score, settings)]
    if not boundaries:
        return (_phrase_of(score, 1, Fraction(0), score.end(), PhraseClosing.NO_FERMATAS),)
    ends = [*boundaries]
    closings = [PhraseClosing.FERMATA] * len(ends)
    if boundaries[-1] < score.end():
        if _has_attacks(score, TimeSpan(onset=boundaries[-1], end=score.end())):
            ends.append(score.end())
            closings.append(PhraseClosing.SCORE_END)
        else:
            ends[-1] = score.end()
    onsets = [Fraction(0), *ends[:-1]]
    return tuple(
        _phrase_of(score, number, onset, end, closing)
        for number, (onset, end, closing) in enumerate(
            zip(onsets, ends, closings, strict=True), start=1
        )
    )


def _fermatas_of(score: Score) -> list[tuple[TimeSpan, StreamReference]]:
    fermatas: list[tuple[TimeSpan, StreamReference]] = []
    for stream in stream_references(score):
        voice = score.parts[stream.part_number - 1].voices[stream.voice_number - 1]
        stopped = [item for item in voice.events if item.fermata] + list(voice.rest_fermatas)
        fermatas += [(TimeSpan(onset=item.onset, end=item.end()), stream) for item in stopped]
    return sorted(fermatas, key=lambda fermata: (fermata[0].onset, fermata[0].end))


def _overlapping_groups(
    fermatas: list[tuple[TimeSpan, StreamReference]],
) -> list[list[tuple[TimeSpan, StreamReference]]]:
    groups: list[list[tuple[TimeSpan, StreamReference]]] = []
    latest_end = Fraction(0)
    for fermata in fermatas:
        if groups and fermata[0].onset < latest_end:
            groups[-1].append(fermata)
            latest_end = max(latest_end, fermata[0].end)
        else:
            groups.append([fermata])
            latest_end = fermata[0].end
    return groups


def _cluster_of(group: list[tuple[TimeSpan, StreamReference]]) -> FermataCluster:
    ends = sorted({span.end for span, _ in group})
    streams = {(stream.part_number, stream.voice_number): stream for _, stream in group}
    return FermataCluster(
        span=TimeSpan(onset=min(span.onset for span, _ in group), end=ends[-1]),
        boundary=ends[-1],
        ends=tuple(ends),
        streams=tuple(streams[key] for key in sorted(streams)),
    )


def _has_attacks(score: Score, span: TimeSpan) -> bool:
    return any(voice_attacks(score, stream, span) for stream in stream_references(score))


def _phrase_of(
    score: Score, number: int, onset: Fraction, end: Fraction, closing: PhraseClosing
) -> Phrase:
    return Phrase(
        number=number,
        span=TimeSpan(onset=onset, end=end),
        first_bar_number=_bar_number_holding(score, onset),
        last_bar_number=_bar_number_holding_the_moment_before(score, end),
        closing=closing,
    )


def _bar_number_holding(score: Score, moment: Fraction) -> int:
    return next(bar.number for bar in score.bars if bar.onset <= moment < bar.onset + bar.duration)


def _bar_number_holding_the_moment_before(score: Score, end: Fraction) -> int:
    return next(bar.number for bar in score.bars if bar.onset < end <= bar.onset + bar.duration)
