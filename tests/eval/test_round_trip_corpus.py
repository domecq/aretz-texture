"""Criteria 27 to 29: the round trip over the 350 distinct corpus chorales (slow)."""

from pathlib import Path

import pytest

from aretz_texture.eval.round_trip import ChoraleOutcome, ChoraleRoundTrip, round_trip_chorale
from aretz_texture.ingest.sources import list_corpus_chorales

EVALUATION_DIRECTORY = Path(__file__).parent
FOUR_PARTS = 4


def read_expected_reasons(file_name: str) -> dict[str, str]:
    """Read "identifier: reason" lines, ignoring comment lines."""
    reasons: dict[str, str] = {}
    for line in (EVALUATION_DIRECTORY / file_name).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            identifier, reason = line.split(": ", maxsplit=1)
            reasons[identifier] = reason
    return reasons


@pytest.fixture(scope="module")
def corpus_round_trips(tmp_path_factory: pytest.TempPathFactory) -> list[ChoraleRoundTrip]:
    work_directory = tmp_path_factory.mktemp("round_trip")
    # The listing names 21 files twice; each distinct file is evaluated once.
    return [
        round_trip_chorale(identifier, work_directory)
        for identifier in dict.fromkeys(list_corpus_chorales())
    ]


@pytest.mark.slow
def test_no_corpus_chorale_changes_in_the_round_trip(
    corpus_round_trips: list[ChoraleRoundTrip],
) -> None:
    assert len(corpus_round_trips) == 350
    different = {
        result.identifier: [d.description for d in result.differences]
        for result in corpus_round_trips
        if result.outcome is ChoraleOutcome.DIFFERENT
    }

    assert different == {}


@pytest.mark.slow
def test_the_unsupported_chorales_are_the_committed_list(
    corpus_round_trips: list[ChoraleRoundTrip],
) -> None:
    unsupported = {
        result.identifier: result.unsupported_reason
        for result in corpus_round_trips
        if result.outcome is ChoraleOutcome.UNSUPPORTED
    }

    assert unsupported == read_expected_reasons("expected_unsupported_chorales.txt")


@pytest.mark.slow
def test_the_four_part_chorales_that_skip_the_grand_staff_are_the_committed_list(
    corpus_round_trips: list[ChoraleRoundTrip],
) -> None:
    skipped = {
        result.identifier: result.grand_staff_skip_reason
        for result in corpus_round_trips
        if result.part_count == FOUR_PARTS and result.grand_staff_skip_reason
    }

    assert skipped == read_expected_reasons("expected_grand_staff_skips.txt")


@pytest.mark.slow
def test_every_chorale_with_more_than_four_parts_records_its_part_count_as_the_reason(
    corpus_round_trips: list[ChoraleRoundTrip],
) -> None:
    larger = [result for result in corpus_round_trips if result.part_count > FOUR_PARTS]

    assert len(larger) == 19
    assert all(
        f"has {result.part_count} parts" in result.grand_staff_skip_reason for result in larger
    )
