"""`round_trip_chorale` on single corpus chorales."""

from pathlib import Path

from aretz_texture.eval.round_trip import ChoraleOutcome, round_trip_chorale


def test_a_four_part_chorale_is_identical_through_both_routes(tmp_path: Path) -> None:
    result = round_trip_chorale("bwv66.6", tmp_path)

    assert result.outcome is ChoraleOutcome.IDENTICAL
    assert result.part_count == 4
    assert result.differences == ()
    assert result.grand_staff_skip_reason == ""
    assert result.unsupported_reason == ""


def test_a_chorale_with_more_than_four_parts_skips_the_grand_staff(tmp_path: Path) -> None:
    result = round_trip_chorale("bach/bwv27.6", tmp_path)

    assert result.outcome is ChoraleOutcome.IDENTICAL
    assert result.part_count == 5
    assert "5 parts" in result.grand_staff_skip_reason


def test_a_chorale_ingestion_rejects_is_unsupported_with_its_reason(tmp_path: Path) -> None:
    result = round_trip_chorale("bach/bwv299", tmp_path)

    assert result.outcome is ChoraleOutcome.UNSUPPORTED
    assert result.part_count == 0
    assert result.unsupported_reason == "grace notes are not supported yet"
    assert result.differences == ()
