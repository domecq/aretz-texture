"""Decisions of the five textural features of a configuration (spec 002, section 3.6, ADR 0005).

Every decision returns a `FeatureDecision` with its rule and an explanation that names bars
and tactus spans, because Fessel (2000, p. 88) values the factors behind a reading more than
the binary value.
"""

from collections import defaultdict
from collections.abc import Sequence
from fractions import Fraction
from itertools import combinations, pairwise

from pydantic import BaseModel, ConfigDict

from aretz_texture.analysis.attacks import Attack, voice_attacks
from aretz_texture.analysis.metric_grid import tactus_label, tactus_spans
from aretz_texture.analysis.settings import FeatureSettings
from aretz_texture.core.notation import SEMITONES_PER_OCTAVE, SpelledPitch
from aretz_texture.core.score import Score
from aretz_texture.core.texture import (
    DecisionRule,
    FeatureDecision,
    StreamReference,
    TexturalConfiguration,
    TexturalFeatures,
    TimeSpan,
)

UNISON_INTERVAL_CLASS = 0  # unison and octave: a registral duplication of one note
MINIMUM_COMPONENTS_TO_DIVERGE = 2  # a component attacking alone is not divergence


class Component(BaseModel):
    """Something that can attack in a configuration: a plane at the root, a voice in a leaf."""

    model_config = ConfigDict(frozen=True)

    label: str
    attack_onsets: frozenset[Fraction]  # quarter lengths from the start of the first bar


class DivergentSpan(BaseModel):
    """A tactus span in which components attack at different time points."""

    model_config = ConfigDict(frozen=True)

    span: TimeSpan
    first_label: str  # a component attacking in the span
    second_label: str  # another one whose attack points differ from the first's


class Divergence(BaseModel):
    """The tactus spans of a phrase in which attacks diverge."""

    model_config = ConfigDict(frozen=True)

    divergent_spans: tuple[DivergentSpan, ...]
    span_count: int  # all tactus spans of the phrase


class _AttackPoint(BaseModel):
    """The attacks of the notated voices of a plane at one onset."""

    model_config = ConfigDict(frozen=True)

    onset: Fraction
    attacks: tuple[Attack, ...]
    pitches: tuple[SpelledPitch, ...]  # every pitch attacked here, highest first


def measure_divergence(score: Score, span: TimeSpan, components: Sequence[Component]) -> Divergence:
    """Find the tactus spans of a phrase in which attacks diverge.

    A span diverges when at least two components attack in it and their sets of attack
    points inside it are not all equal. A component attacking alone, tied continuations
    (which are not attacks) and attacks in different tactus spans never diverge.

    Args:
        score: The score whose bars give the tactus spans.
        span: The phrase.
        components: What can attack, in the order that explanations name them.

    Returns:
        The divergent spans in order, and the number of tactus spans of the phrase.
    """
    spans = tactus_spans(score, span)
    divergent: list[DivergentSpan] = []
    for tactus in spans:
        labels = _diverging_labels(tactus, components)
        if labels is not None:
            divergent.append(
                DivergentSpan(span=tactus, first_label=labels[0], second_label=labels[1])
            )
    return Divergence(divergent_spans=tuple(divergent), span_count=len(spans))


def _diverging_labels(tactus: TimeSpan, components: Sequence[Component]) -> tuple[str, str] | None:
    attacking = [
        (component.label, points)
        for component in components
        if (
            points := frozenset(
                onset for onset in component.attack_onsets if tactus.onset <= onset < tactus.end
            )
        )
    ]
    if len(attacking) < MINIMUM_COMPONENTS_TO_DIVERGE:
        return None
    first_label, first_points = attacking[0]
    for label, points in attacking[1:]:
        if points != first_points:
            return first_label, label
    return None


def decide_planes(plane_count: int) -> FeatureDecision:
    """Decide P from the number of planes below a node; a leaf has none."""
    if plane_count == 0:
        explanation = "no planes below this configuration: it is one plane."
        return FeatureDecision(value=False, rule=DecisionRule.PLANE_COUNT, explanation=explanation)
    explanation = f"{plane_count} planes below this configuration."
    return FeatureDecision(value=True, rule=DecisionRule.PLANE_COUNT, explanation=explanation)


def decide_root_homogeneity(score: Score, span: TimeSpan) -> FeatureDecision:
    """Decide H of a `+P` configuration by the provisional rule of one meter and key.

    The value is `+` in both cases; outside the conditions it is an assumption, recorded as
    such. Key signatures are not compared across parts.

    Args:
        score: The score whose signatures are read.
        span: The phrase.

    Returns:
        The decision, with the changes inside the phrase when there are any.
    """
    changes = _signature_changes_inside(score, span)
    if not changes:
        return FeatureDecision(
            value=True,
            rule=DecisionRule.SINGLE_METER_AND_KEY,
            explanation=(
                "one time signature and no key signature change inside the phrase, which "
                "stand in for simple pulse proportions and one harmonic field (provisional rule)."
            ),
        )
    return FeatureDecision(
        value=True,
        rule=DecisionRule.ASSUMED_OUTSIDE_CONDITIONS,
        explanation=(
            f"assumed, not decided: {'; '.join(changes)}, so the provisional rule of one "
            "meter and key does not apply."
        ),
    )


def decide_root_accent_coincidence() -> FeatureDecision:
    """Decide C of a `+P` configuration: `+`, because every plane follows the score's meter."""
    return FeatureDecision(
        value=True,
        rule=DecisionRule.SHARED_METER,
        explanation=(
            "every plane follows the single meter of the score; phenomenal accents, "
            "syncopation and hemiola are not modeled (provisional rule)."
        ),
    )


def decide_linearity(
    score: Score, settings: FeatureSettings, streams: Sequence[StreamReference], span: TimeSpan
) -> FeatureDecision:
    """Decide L of a leaf from the necessary conditions of Fessel (1996, pp. 79 to 83).

    At each attack point of the plane, every notated voice of the plane that sounds must also
    attack, and every pair of attacked pitches must be at an interval class of
    `linear_interval_classes`. Where the plane has simultaneous pitches other than unison and
    octave, they must also move in the same direction at nearly every step.

    Args:
        score: The score.
        settings: The thresholds of the shares of attack points and of parallel steps.
        streams: The notated voices of the plane.
        span: The phrase.

    Returns:
        The decision; its explanation names the first failing attack and the condition.
    """
    points = _attack_points(score, streams, span)
    failures = [
        (point, reason)
        for point in points
        if (reason := _failure_at(score, settings, streams, point)) is not None
    ]
    if (
        Fraction(len(points) - len(failures), len(points))
        < settings.minimum_linear_attack_proportion
    ):
        point, reason = failures[0]
        return _simultaneity_decision(
            value=False,
            explanation=(
                f"{len(failures)} of {len(points)} attack points fail the conditions; "
                f"the first is at {_label_at(score, point.onset)}: {reason}."
            ),
        )
    failed = {point.onset for point, _ in failures}
    meeting = [point for point in points if point.onset not in failed]
    not_parallel = _parallel_motion_failure(points, meeting, settings)
    if not_parallel is not None:
        return _simultaneity_decision(value=False, explanation=not_parallel)
    if failures:
        point, reason = failures[0]
        return _simultaneity_decision(
            value=True,
            explanation=(
                f"{len(meeting)} of {len(points)} attack points meet the conditions, at least "
                f"{settings.minimum_linear_attack_proportion} as the settings require; the first "
                f"that does not is at {_label_at(score, point.onset)}: {reason}."
            ),
        )
    return _simultaneity_decision(
        value=True,
        explanation=(
            f"at all {len(points)} attack points every voice that sounds attacks, and the "
            "pitches are at intervals that a single voice can take."
        ),
    )


def decide_leaf_attack_divergence(
    score: Score,
    streams: Sequence[StreamReference],
    span: TimeSpan,
    linearity: FeatureDecision,
    settings: FeatureSettings,
) -> FeatureDecision:
    """Decide D of a leaf: `-` by restriction 5 when `+L`, else measured between its voices."""
    if linearity.value:
        return FeatureDecision(
            value=False,
            rule=DecisionRule.RESTRICTION_5,
            explanation="a linear plane has no diverging attacks: +L implies -D.",
        )
    components = [
        Component(label=stream.label(), attack_onsets=_attack_onsets(score, [stream], span))
        for stream in streams
    ]
    return _measured_divergence(score, settings, span, components, "between its voices")


def decide_root_attack_divergence(
    score: Score,
    leaves: Sequence[TexturalConfiguration],
    span: TimeSpan,
    settings: FeatureSettings,
) -> FeatureDecision:
    """Decide D of a `+P` configuration: measured between its planes, or inherited.

    The root is also `+D` when one of its planes is, because Fessel's divergence covers the
    attacks within and between planes (1996, p. 83).
    """
    components = [
        Component(
            label=_plane_label(leaf.streams),
            attack_onsets=_attack_onsets(score, leaf.streams, span),
        )
        for leaf in leaves
    ]
    measured = _measured_divergence(score, settings, span, components, "between its planes")
    inner = [leaf for leaf in leaves if leaf.features.attack_divergence.value]
    if measured.value or not inner:
        return measured
    return FeatureDecision(
        value=True,
        rule=DecisionRule.ATTACKS_WITHIN_TACTUS,
        explanation=(
            f"{measured.explanation[:-1]}, but the plane {_plane_label(inner[0].streams)} "
            f"diverges within itself: {inner[0].features.attack_divergence.explanation}"
        ),
    )


def leaf_features(
    score: Score, settings: FeatureSettings, streams: Sequence[StreamReference], span: TimeSpan
) -> TexturalFeatures:
    """Return the features of a `-P` configuration: L, then D, then H and C by restriction."""
    linearity = decide_linearity(score, settings, streams, span)
    return TexturalFeatures(
        planes=decide_planes(0),
        homogeneity=FeatureDecision(
            value=True,
            rule=DecisionRule.RESTRICTION_2,
            explanation="a plane with no planes below has none to differ from: -P implies +H.",
        ),
        linearity=linearity,
        accent_coincidence=FeatureDecision(
            value=True,
            rule=DecisionRule.RESTRICTION_3,
            explanation="a plane with no planes below has none to disagree with: -C implies +P.",
        ),
        attack_divergence=decide_leaf_attack_divergence(score, streams, span, linearity, settings),
    )


def root_features(
    score: Score,
    settings: FeatureSettings,
    leaves: Sequence[TexturalConfiguration],
    span: TimeSpan,
) -> TexturalFeatures:
    """Return the features of a `+P` configuration over its planes, which are leaves."""
    return TexturalFeatures(
        planes=decide_planes(len(leaves)),
        homogeneity=decide_root_homogeneity(score, span),
        linearity=FeatureDecision(
            value=None,
            rule=DecisionRule.RESTRICTION_4,
            explanation="linearity is specified only for configurations without planes.",
        ),
        accent_coincidence=decide_root_accent_coincidence(),
        attack_divergence=decide_root_attack_divergence(score, leaves, span, settings),
    )


def _simultaneity_decision(*, value: bool, explanation: str) -> FeatureDecision:
    return FeatureDecision(
        value=value, rule=DecisionRule.SIMULTANEITY_CONDITIONS, explanation=explanation
    )


def _measured_divergence(
    score: Score,
    settings: FeatureSettings,
    span: TimeSpan,
    components: Sequence[Component],
    where: str,
) -> FeatureDecision:
    divergence = measure_divergence(score, span, components)
    count = len(divergence.divergent_spans)
    if count == 0:
        explanation = (
            f"no tactus span has attacks at different points {where} "
            f"(0 of {divergence.span_count} tactus spans)."
        )
    else:
        first = divergence.divergent_spans[0]
        explanation = (
            f"{count} of {divergence.span_count} tactus spans have attacks at different "
            f"points {where}; the first is {tactus_label(score, first.span)}, where "
            f"{first.first_label} and {first.second_label} attack at different points."
        )
    return FeatureDecision(
        value=count >= settings.minimum_divergent_tactus_spans,
        rule=DecisionRule.ATTACKS_WITHIN_TACTUS,
        explanation=explanation,
    )


def _plane_label(streams: Sequence[StreamReference]) -> str:
    return " and ".join(stream.label() for stream in streams)


def _label_at(score: Score, onset: Fraction) -> str:
    return tactus_label(score, TimeSpan(onset=onset, end=onset + 1))


def _attack_onsets(
    score: Score, streams: Sequence[StreamReference], span: TimeSpan
) -> frozenset[Fraction]:
    return frozenset(
        attack.onset for stream in streams for attack in voice_attacks(score, stream, span)
    )


def _signature_changes_inside(score: Score, span: TimeSpan) -> list[str]:
    """Describe the signature changes that start strictly inside a span."""
    changes = [
        f"the time signature changes at {_label_at(score, change.onset)}"
        for change in score.time_signatures
        if span.onset < change.onset < span.end
    ]
    for part_number, part in enumerate(score.parts, start=1):
        changes += [
            f"part {part_number} changes its key signature at {_label_at(score, change.onset)}"
            for change in part.key_signatures
            if span.onset < change.onset < span.end
        ]
    return changes


def _attack_points(
    score: Score, streams: Sequence[StreamReference], span: TimeSpan
) -> list[_AttackPoint]:
    by_onset: dict[Fraction, list[Attack]] = defaultdict(list)
    for stream in streams:
        for attack in voice_attacks(score, stream, span):
            by_onset[attack.onset].append(attack)
    return [
        _AttackPoint(
            onset=onset,
            attacks=tuple(attacks),
            pitches=tuple(
                sorted(
                    (pitch for attack in attacks for pitch in attack.pitches),
                    key=SpelledPitch.highest_first_key,
                )
            ),
        )
        for onset, attacks in sorted(by_onset.items())
    ]


def _failure_at(
    score: Score,
    settings: FeatureSettings,
    streams: Sequence[StreamReference],
    point: _AttackPoint,
) -> str | None:
    """Return why the conditions of linearity fail at an attack point, or `None` if they hold."""
    attacking = {(a.stream.part_number, a.stream.voice_number) for a in point.attacks}
    for stream in streams:
        key = (stream.part_number, stream.voice_number)
        if key not in attacking and _sounds_at(score, stream, point.onset):
            return f"{stream.label()} sounds without attacking"
    for upper, lower in combinations(point.pitches, 2):
        interval_class = _interval_class(upper, lower)
        if interval_class not in settings.linear_interval_classes:
            return (
                f"the pitches {_pitch_name(upper)} and {_pitch_name(lower)} are "
                f"{interval_class} semitones apart modulo the octave, an interval that a "
                "single voice does not take"
            )
    return None


def _sounds_at(score: Score, stream: StreamReference, onset: Fraction) -> bool:
    voice = score.parts[stream.part_number - 1].voices[stream.voice_number - 1]
    return any(item.onset <= onset < item.end() for item in voice.events)


def _interval_class(upper: SpelledPitch, lower: SpelledPitch) -> int:
    return (upper.sounding_semitones() - lower.sounding_semitones()) % SEMITONES_PER_OCTAVE


def _pitch_name(pitch: SpelledPitch) -> str:
    accidental = "#" * pitch.alter if pitch.alter > 0 else "b" * -pitch.alter
    return f"{pitch.step}{accidental}{pitch.octave}"


def _parallel_motion_failure(
    points: Sequence[_AttackPoint], meeting: Sequence[_AttackPoint], settings: FeatureSettings
) -> str | None:
    """Return why simultaneous pitches do not move in parallel, or `None` if they do or none."""
    has_simultaneous_pitches = any(
        _interval_class(upper, lower) != UNISON_INTERVAL_CLASS
        for point in meeting
        for upper, lower in combinations(point.pitches, 2)
    )
    steps = list(pairwise(points))
    if not has_simultaneous_pitches or not steps:
        return None
    parallel = sum(_move_together(before, after) for before, after in steps)
    if Fraction(parallel, len(steps)) >= settings.minimum_parallel_motion_proportion:
        return None
    return (
        f"the simultaneous pitches move in the same direction at only {parallel} of "
        f"{len(steps)} steps between attack points, so they are not parallel."
    )


def _move_together(before: _AttackPoint, after: _AttackPoint) -> bool:
    """Return whether all pitches go up, all go down or all repeat between two points."""
    if len(before.pitches) != len(after.pitches):
        return False
    directions = {
        _sign(new.sounding_semitones() - old.sounding_semitones())
        for old, new in zip(before.pitches, after.pitches, strict=True)
    }
    return len(directions) == 1


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)
