"""Command-line entry point for Menairos."""

import argparse

from menairos import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="menairos",
        description=(
            "Menairos: método de desarrollo con agentes de IA, "
            "distribuido como plugin de Claude Code."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="muestra la versión y termina",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"menairos {__version__}")
        return 0
    parser.print_help()
    return 0
