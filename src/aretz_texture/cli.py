"""Command line entry point of Aretz Texture."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aretz_texture.analysis.settings import TexturalAnalysisSettings
from aretz_texture.analysis.texture import analyze_texture
from aretz_texture.core.errors import AretzTextureError
from aretz_texture.core.grand_staff import piano_layout
from aretz_texture.ingest.sources import read_score
from aretz_texture.render.piano_score import write_piano_score
from aretz_texture.render.textural_schema import format_textural_schema

SUCCESS_EXIT_CODE = 0
DOMAIN_ERROR_EXIT_CODE = 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: The arguments after the program name; `sys.argv` when `None`.

    Returns:
        The exit code: 0 on success and 1 when a domain error stops the command. Usage
        errors exit with code 2 through argparse.
    """
    arguments = _build_parser().parse_args(argv)
    if arguments.command == "schema":
        return _run_schema(arguments.source, explain=arguments.explain)
    return _run_piano(arguments.source, Path(arguments.output))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aretz-texture",
        description="Analyze how the texture of a MusicXML score is organized.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    piano = commands.add_parser(
        "piano",
        help="write a score of four parts as a MusicXML piano grand staff",
        description=(
            "Write a score of exactly four parts as a MusicXML piano grand staff: "
            "parts 1 and 2 on the right hand staff, parts 3 and 4 on the left hand staff."
        ),
    )
    piano.add_argument("source", help="a MusicXML file path or a music21 corpus identifier")
    piano.add_argument(
        "--output", "-o", required=True, help="the MusicXML file to write; overwritten if present"
    )
    schema = commands.add_parser(
        "schema",
        help="print the textural schema of a score, one block per phrase",
        description=(
            "Print the textural configuration of each phrase of a score in Fessel's bracket "
            "notation, a secondary output of the textural analysis."
        ),
    )
    schema.add_argument("source", help="a MusicXML file path or a music21 corpus identifier")
    schema.add_argument(
        "--explain",
        action="store_true",
        help="follow each node with the value, rule and explanation of its five features",
    )
    return parser


def _run_piano(source: str, output_path: Path) -> int:
    try:
        ingested = read_score(source)
        # The layout is checked before writing, so a refused score leaves no file behind.
        layout = piano_layout(ingested.score)
        write_piano_score(ingested.score, layout, output_path)
    except AretzTextureError as error:
        sys.stderr.write(f"{error}\n")
        return DOMAIN_ERROR_EXIT_CODE
    if ingested.has_lyrics:
        sys.stdout.write("The lyrics of the source were ignored.\n")
    return SUCCESS_EXIT_CODE


def _run_schema(source: str, *, explain: bool) -> int:
    try:
        ingested = read_score(source)
        analysis = analyze_texture(ingested.score, TexturalAnalysisSettings())
    except AretzTextureError as error:
        sys.stderr.write(f"{error}\n")
        return DOMAIN_ERROR_EXIT_CODE
    sys.stdout.write(format_textural_schema(analysis, explain=explain) + "\n")
    return SUCCESS_EXIT_CODE
