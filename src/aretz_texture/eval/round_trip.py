"""Round trip evaluation: write a score, read it back and compare it with the original."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aretz_texture.core.errors import GrandStaffMappingError, UnsupportedScoreError
from aretz_texture.core.grand_staff import piano_layout
from aretz_texture.core.notation import GraceNote, NotatedVoice, NoteEvent, RestFermata
from aretz_texture.core.score import Bar, Part, Score
from aretz_texture.ingest.sources import read_grand_staff_file, read_score
from aretz_texture.render.full_score import write_full_score
from aretz_texture.render.piano_score import write_piano_score


class RoundTripRoute(StrEnum):
    """The way a score is written and read back."""

    FULL_SCORE = "full_score"  # one staff per part, any number of parts
    GRAND_STAFF = "grand_staff"  # piano, four parts only


class DifferenceKind(StrEnum):
    """What differs between an original score and the one read back."""

    PART_COUNT = "part_count"
    PART_NAME = "part_name"
    INSTRUMENT_NAME = "instrument_name"
    VOICE_COUNT = "voice_count"  # notated voices in a part
    MISSING_EVENT = "missing_event"  # in the original, not in the output
    EXTRA_EVENT = "extra_event"  # in the output, not in the original
    ALTERED_EVENT = "altered_event"  # same onset, other duration, pitches or fermata
    BARS = "bars"
    KEY_SIGNATURES = "key_signatures"
    TIME_SIGNATURES = "time_signatures"
    GRACE_NOTE = "grace_note"  # the grace notes at one onset differ, in any way
    REST_FERMATA = "rest_fermata"  # the fermatas on rests at one onset differ, in any way


class RoundTripDifference(BaseModel):
    """One difference found by `compare_scores`."""

    model_config = ConfigDict(frozen=True)

    route: RoundTripRoute
    kind: DifferenceKind
    part_number: int | None  # 1 based; None for score level differences
    voice_number: int | None  # 1 based; None above the notated voice
    onset: Fraction | None  # None for differences that are not about one event
    description: str  # human readable, includes the bar number when known


class ChoraleOutcome(StrEnum):
    """The result of the round trip of one chorale."""

    IDENTICAL = "identical"
    DIFFERENT = "different"
    UNSUPPORTED = "unsupported"  # ingestion raised UnsupportedScoreError


class ChoraleRoundTrip(BaseModel):
    """The round trip of one corpus chorale through both routes."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    outcome: ChoraleOutcome
    part_count: int  # 0 when unsupported
    differences: tuple[RoundTripDifference, ...]
    grand_staff_skip_reason: str  # empty when the grand staff route ran
    unsupported_reason: str  # message of the UnsupportedScoreError, or empty


@dataclass(frozen=True)
class _Scope:
    """Where a comparison is happening, so that each difference is built the same way."""

    route: RoundTripRoute
    part_number: int | None = None
    voice_number: int | None = None

    def difference(
        self, kind: DifferenceKind, description: str, onset: Fraction | None = None
    ) -> RoundTripDifference:
        return RoundTripDifference(
            route=self.route,
            kind=kind,
            part_number=self.part_number,
            voice_number=self.voice_number,
            onset=onset,
            description=description,
        )

    def in_part(self, part_number: int) -> "_Scope":
        return _Scope(self.route, part_number)

    def in_voice(self, voice_number: int) -> "_Scope":
        return _Scope(self.route, self.part_number, voice_number)


def compare_scores(
    original: Score,
    returned: Score,
    route: RoundTripRoute,
) -> tuple[RoundTripDifference, ...]:
    """Compare a score with the one read back from a file written from it.

    Parts are aligned by position, notated voices by number and events by onset.
    What the core model does not carry (rests without fermata, accidental display,
    clefs, beaming, lyrics and the like) is ignored (spec 001, section 3.8).

    Args:
        original: The score before writing.
        returned: The score read back.
        route: The route the file took, recorded in every difference.

    Returns:
        Every difference found, empty when the scores are equal.
    """
    scope = _Scope(route)
    differences = _compare_score_level(original, returned, scope)
    for part_number, (original_part, returned_part) in enumerate(
        zip(original.parts, returned.parts, strict=False), start=1
    ):
        differences += _compare_part(
            original_part, returned_part, original.bars, scope.in_part(part_number)
        )
    return tuple(differences)


def without_part_metadata(score: Score) -> Score:
    """Return the score with every part name and instrument name set to `None`.

    The grand staff carries neither (spec 001, decision 6).

    Args:
        score: The score to strip.

    Returns:
        A copy of the score without part metadata.
    """
    parts = tuple(
        part.model_copy(update={"name": None, "instrument_name": None}) for part in score.parts
    )
    return score.model_copy(update={"parts": parts})


def _compare_score_level(
    original: Score, returned: Score, scope: _Scope
) -> list[RoundTripDifference]:
    differences: list[RoundTripDifference] = []
    if len(original.parts) != len(returned.parts):
        differences.append(
            scope.difference(
                DifferenceKind.PART_COUNT,
                f"the original has {len(original.parts)} parts, the output {len(returned.parts)}",
            )
        )
    if original.bars != returned.bars:
        differences.append(
            scope.difference(DifferenceKind.BARS, _bars_description(original, returned))
        )
    if original.time_signatures != returned.time_signatures:
        differences.append(
            scope.difference(DifferenceKind.TIME_SIGNATURES, "the time signatures differ")
        )
    return differences


def _bars_description(original: Score, returned: Score) -> str:
    for original_bar, returned_bar in zip(original.bars, returned.bars, strict=False):
        if original_bar != returned_bar:
            return f"bar {original_bar.number} differs: {original_bar} became {returned_bar}"
    return f"the original has {len(original.bars)} bars, the output {len(returned.bars)}"


def _compare_part(
    original: Part, returned: Part, bars: tuple[Bar, ...], scope: _Scope
) -> list[RoundTripDifference]:
    differences = _compare_part_metadata(original, returned, scope)
    if len(original.voices) != len(returned.voices):
        differences.append(
            scope.difference(
                DifferenceKind.VOICE_COUNT,
                f"the original has {len(original.voices)} notated voices, "
                f"the output {len(returned.voices)}",
            )
        )
    for voice_number, (original_voice, returned_voice) in enumerate(
        zip(original.voices, returned.voices, strict=False), start=1
    ):
        differences += _compare_voice(
            original_voice, returned_voice, bars, scope.in_voice(voice_number)
        )
    return differences


def _compare_part_metadata(
    original: Part, returned: Part, scope: _Scope
) -> list[RoundTripDifference]:
    differences: list[RoundTripDifference] = []
    if _effective_name(original) != _effective_name(returned):
        differences.append(
            scope.difference(
                DifferenceKind.PART_NAME,
                f"part name {original.name!r} became {returned.name!r}",
            )
        )
    if original.instrument_name != returned.instrument_name:
        differences.append(
            scope.difference(
                DifferenceKind.INSTRUMENT_NAME,
                f"instrument name {original.instrument_name!r} became {returned.instrument_name!r}",
            )
        )
    if original.key_signatures != returned.key_signatures:
        differences.append(
            scope.difference(DifferenceKind.KEY_SIGNATURES, "the key signatures differ")
        )
    return differences


def _effective_name(part: Part) -> str | None:
    """Return the part name, or `None` when it only repeats the instrument name.

    music21 names an unnamed part after its instrument when it reads the file back,
    so the two cases are equivalent (spec 001, decision 13).
    """
    return None if part.name == part.instrument_name else part.name


def _compare_voice(
    original: NotatedVoice,
    returned: NotatedVoice,
    bars: tuple[Bar, ...],
    scope: _Scope,
) -> list[RoundTripDifference]:
    original_events = {event.onset: event for event in original.events}
    returned_events = {event.onset: event for event in returned.events}
    differences: list[RoundTripDifference] = []
    for onset in sorted(original_events.keys() | returned_events.keys()):
        difference = _compare_event(
            original_events.get(onset), returned_events.get(onset), onset, bars, scope
        )
        if difference is not None:
            differences.append(difference)
    differences += _compare_by_onset(
        original.grace_notes, returned.grace_notes, DifferenceKind.GRACE_NOTE, bars, scope
    )
    differences += _compare_by_onset(
        original.rest_fermatas, returned.rest_fermatas, DifferenceKind.REST_FERMATA, bars, scope
    )
    return differences


def _compare_by_onset(
    original: Sequence[GraceNote] | Sequence[RestFermata],
    returned: Sequence[GraceNote] | Sequence[RestFermata],
    kind: DifferenceKind,
    bars: tuple[Bar, ...],
    scope: _Scope,
) -> list[RoundTripDifference]:
    """Compare what a voice holds at each onset, keeping the order of items at one onset."""
    original_by_onset = _group_by_onset(original)
    returned_by_onset = _group_by_onset(returned)
    differences: list[RoundTripDifference] = []
    for onset in sorted(original_by_onset.keys() | returned_by_onset.keys()):
        before = original_by_onset.get(onset, ())
        after = returned_by_onset.get(onset, ())
        if before != after:
            what = _change_label(before, after)
            where = f"at onset {onset} ({_bar_label(bars, onset)})"
            description = f"{kind.value} {what} {where}: {before} became {after}"
            differences.append(scope.difference(kind, description, onset))
    return differences


def _change_label(before: tuple[object, ...], after: tuple[object, ...]) -> str:
    if not after:
        return "missing in the output"
    return "not in the original" if not before else "altered"


def _group_by_onset(
    items: Sequence[GraceNote] | Sequence[RestFermata],
) -> dict[Fraction, tuple[GraceNote | RestFermata, ...]]:
    grouped: dict[Fraction, list[GraceNote | RestFermata]] = {}
    for item in items:
        grouped.setdefault(item.onset, []).append(item)
    return {onset: tuple(group) for onset, group in grouped.items()}


def _compare_event(
    original: NoteEvent | None,
    returned: NoteEvent | None,
    onset: Fraction,
    bars: tuple[Bar, ...],
    scope: _Scope,
) -> RoundTripDifference | None:
    where = f"at onset {onset} ({_bar_label(bars, onset)})"
    if returned is None:
        return scope.difference(
            DifferenceKind.MISSING_EVENT, f"event missing in the output {where}", onset
        )
    if original is None:
        return scope.difference(
            DifferenceKind.EXTRA_EVENT, f"event not in the original, in the output {where}", onset
        )
    if original != returned:
        return scope.difference(
            DifferenceKind.ALTERED_EVENT,
            f"event altered {where}: {original} became {returned}",
            onset,
        )
    return None


def _bar_label(bars: tuple[Bar, ...], onset: Fraction) -> str:
    for bar in bars:
        if bar.onset <= onset < bar.onset + bar.duration:
            return f"bar {bar.number}"
    return "outside the bars"


def round_trip_chorale(identifier: str, work_directory: Path) -> ChoraleRoundTrip:
    """Write a corpus chorale through each route, read it back and compare.

    The full score route runs for every chorale. The grand staff route runs when
    `piano_layout` accepts the score. A domain error while reading back a file written
    by this tool is a bug and propagates.

    Args:
        identifier: A music21 corpus identifier such as `"bach/bwv66.6"`.
        work_directory: An existing directory where the files are written.

    Returns:
        The outcome, the part count and every difference found.
    """
    try:
        original = read_score(identifier).score
    except UnsupportedScoreError as error:
        return ChoraleRoundTrip(
            identifier=identifier,
            outcome=ChoraleOutcome.UNSUPPORTED,
            part_count=0,
            differences=(),
            grand_staff_skip_reason="",
            unsupported_reason=str(error),
        )
    differences = _full_score_differences(original, work_directory)
    skip_reason = ""
    try:
        layout = piano_layout(original)
    except GrandStaffMappingError as error:
        skip_reason = str(error)
    else:
        piano_path = work_directory / "piano.musicxml"
        write_piano_score(original, layout, piano_path)
        returned = read_grand_staff_file(piano_path, layout)
        differences += compare_scores(
            without_part_metadata(original), returned, RoundTripRoute.GRAND_STAFF
        )
    return ChoraleRoundTrip(
        identifier=identifier,
        outcome=ChoraleOutcome.DIFFERENT if differences else ChoraleOutcome.IDENTICAL,
        part_count=len(original.parts),
        differences=differences,
        grand_staff_skip_reason=skip_reason,
        unsupported_reason="",
    )


def _full_score_differences(
    original: Score, work_directory: Path
) -> tuple[RoundTripDifference, ...]:
    full_score_path = work_directory / "full_score.musicxml"
    write_full_score(original, full_score_path)
    returned = read_score(str(full_score_path)).score
    return compare_scores(original, returned, RoundTripRoute.FULL_SCORE)
