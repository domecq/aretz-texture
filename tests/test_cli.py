"""Criteria 22 to 24: the `aretz-texture piano` command."""

import tomllib
from pathlib import Path

import pytest
from tests.core_builders import event, part_of, score_of
from tests.music21_builders import parse_score

from aretz_texture.cli import main
from aretz_texture.ingest.sources import read_score
from aretz_texture.render.full_score import write_full_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def four_part_file_without_lyrics(directory: Path) -> Path:
    score = score_of(
        part_of([event(0, 4, "E5")]),
        part_of([event(0, 4, "C5")]),
        part_of([event(0, 4, "G3")]),
        part_of([event(0, 4, "C2")]),
    )
    path = directory / "source.musicxml"
    write_full_score(score, path)
    return path


def test_piano_command_writes_the_grand_staff_of_a_corpus_chorale(tmp_path: Path) -> None:
    output = tmp_path / "piano.musicxml"

    exit_code = main(["piano", "bwv66.6", "--output", str(output)])

    assert exit_code == 0
    assert len(parse_score(output).parts) == 2


def test_piano_command_accepts_a_musicxml_file_path_as_source(tmp_path: Path) -> None:
    source = tmp_path / "bwv66_6_full.musicxml"
    write_full_score(read_score("bwv66.6").score, source)
    output = tmp_path / "piano.musicxml"

    exit_code = main(["piano", str(source), "-o", str(output)])

    assert exit_code == 0
    assert len(parse_score(output).parts) == 2


def test_piano_command_overwrites_an_existing_output_file(tmp_path: Path) -> None:
    output = tmp_path / "piano.musicxml"
    output.write_text("old content")

    exit_code = main(["piano", "bwv66.6", "--output", str(output)])

    assert exit_code == 0
    assert "old content" not in output.read_text()


def test_piano_command_says_that_lyrics_were_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # BWV 269 has four parts and lyrics; BWV 66.6 has no lyrics in the corpus.
    main(["piano", "bach/bwv269", "--output", str(tmp_path / "piano.musicxml")])

    printed = capsys.readouterr()
    assert printed.out == "The lyrics of the source were ignored.\n"
    assert printed.err == ""


def test_piano_command_prints_nothing_when_there_are_no_lyrics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = four_part_file_without_lyrics(tmp_path)

    exit_code = main(["piano", str(source), "--output", str(tmp_path / "piano.musicxml")])

    printed = capsys.readouterr()
    assert exit_code == 0
    assert printed.out == ""
    assert printed.err == ""


def test_piano_command_refuses_a_five_part_chorale_without_writing_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "piano.musicxml"

    exit_code = main(["piano", "bwv27.6", "--output", str(output)])

    printed = capsys.readouterr()
    assert exit_code == 1
    assert "this score has 5 parts: Soprano 1, Soprano 2, Alto, Tenor, Bass." in printed.err
    assert "needs the textural analysis of a later spec" in printed.err
    assert printed.out == ""
    assert not output.exists()


def test_piano_command_reports_an_unknown_source_on_standard_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "piano.musicxml"

    exit_code = main(["piano", "bwv0.0", "--output", str(output)])

    printed = capsys.readouterr()
    assert exit_code == 1
    assert "bwv0.0" in printed.err
    assert not output.exists()


def test_piano_command_without_output_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["piano", "bwv66.6"])

    assert raised.value.code == 2
    assert "--output" in capsys.readouterr().err


def test_reduce_is_not_a_subcommand_yet(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["reduce", "bwv66.6", "--output", "out.musicxml"])

    assert raised.value.code == 2
    assert "reduce" in capsys.readouterr().err


def test_the_script_entry_point_is_declared() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"] == {"aretz-texture": "aretz_texture.cli:main"}
