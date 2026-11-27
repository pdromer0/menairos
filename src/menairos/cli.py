"""Command-line entry point for Menairos.

Every text the CLI shows is in Spanish, argparse's own included: the usage
prefix, the group titles, ``-h`` and the error messages ``spec validar`` can
produce are translated with argparse's public API and a small table.
"""

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NoReturn, TextIO

from menairos import __version__
from menairos.spec_validation import Finding, Report, UsageError, validate_spec

_ARGPARSE_ERRORS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"unrecognized arguments: (.*)"), "argumentos no reconocidos: {0}"),
    (re.compile(r"argument (\S+): expected one argument"), "a {0} le falta su valor"),
    (
        re.compile(r"argument (\S+): invalid choice: (.*?) \(choose from (.*)\)"),
        "orden no válida: {1} (se admite: {2})",
    ),
    (
        re.compile(r"the following arguments are required: (.*)"),
        "falta un argumento obligatorio: {0}",
    ),
    (re.compile(r"argument (\S+): (.*)"), "{0}: {1}"),
)


def _translate(message: str) -> str:
    """Spanish version of an argparse error message (unchanged if unknown)."""
    for pattern, spanish in _ARGPARSE_ERRORS:
        match = pattern.fullmatch(message)
        if match:
            return spanish.format(*match.groups())
    return message


class _Formatter(argparse.HelpFormatter):
    """Help formatter with the Spanish usage prefix."""

    def add_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[Any],
        prefix: str | None = None,
    ) -> None:
        super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


class _Parser(argparse.ArgumentParser):
    """ArgumentParser in Spanish: own ``-h``, «opciones» group and errors."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            formatter_class=_Formatter, add_help=False, allow_abbrev=False, **kwargs
        )
        self.options = self.add_argument_group("opciones")
        self.options.add_argument(
            "-h", "--help", action="help", help="muestra esta ayuda y termina"
        )

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {_translate(message)}\n")


def _milestone(text: str) -> int:
    """``--hito``: a non-negative integer written without leading zeros."""
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        raise argparse.ArgumentTypeError(f"«{text}» no es un número de hito (0, 1, 2…)")
    try:
        return int(text)
    except ValueError:  # more digits than Python converts
        raise argparse.ArgumentTypeError(f"«{text[:20]}…» es demasiado largo") from None


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = _Parser(
        prog="menairos",
        description=(
            "Menairos: método de desarrollo con agentes de IA, "
            "distribuido como plugin de Claude Code."
        ),
    )
    parser.options.add_argument(
        "--version",
        action="store_true",
        help="muestra la versión y termina",
    )
    commands = parser.add_subparsers(
        title="órdenes", dest="orden", metavar="ORDEN", parser_class=_Parser
    )
    spec = commands.add_parser(
        "spec",
        help="la especificación de un hito",
        description="Órdenes sobre la especificación de un hito.",
    )
    spec_commands = spec.add_subparsers(
        title="órdenes", dest="suborden", metavar="ORDEN", required=True
    )
    validar: _Parser = spec_commands.add_parser(
        "validar",
        help="comprueba la especificación (errores E01–E12 y avisos A01–A04)",
        description=(
            "Comprueba menairos.toml, docs/specs/hito-N.md y hito-N.tareas.yaml, "
            "docs/abiertas.md y docs/decisiones/. Sale con 0 sin errores (aunque "
            "haya avisos), 1 con errores y 2 si no se puede ejecutar."
        ),
    )
    options = validar.options
    options.add_argument(
        "--hito",
        type=_milestone,
        metavar="N",
        help="número del hito (por defecto, el mayor con hito-N.tareas.yaml)",
    )
    options.add_argument(
        "--json", action="store_true", help="salida en JSON: ok, errores y avisos"
    )
    options.add_argument(
        "--raiz",
        type=Path,
        default=Path("."),
        metavar="RUTA",
        help="raíz del proyecto (por defecto, la carpeta actual)",
    )
    validar.set_defaults(run=_spec_validar)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"menairos {__version__}")
        return 0
    if hasattr(args, "run"):
        return args.run(args)
    parser.print_help()
    return 0


def _spec_validar(args: argparse.Namespace) -> int:
    try:
        report = validate_spec(args.raiz, args.hito)
    except UsageError as error:
        print(f"menairos spec validar: error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_as_json(report), ensure_ascii=False, indent=2))
    else:
        _print_report(report, sys.stdout)
    return 0 if report.ok else 1


def _as_json(report: Report) -> dict[str, object]:
    def item(finding: Finding) -> dict[str, str]:
        return {
            "codigo": finding.code,
            "mensaje": finding.message,
            "fichero": finding.file,
            "ruta": finding.path,
        }

    return {
        "ok": report.ok,
        "errores": [item(f) for f in report.errors],
        "avisos": [item(f) for f in report.warnings],
    }


def _print_report(report: Report, out: TextIO) -> None:
    print(f"Hito {report.milestone} · {report.tasks_file}", file=out)
    for title, findings in (("Errores", report.errors), ("Avisos", report.warnings)):
        if not findings:
            continue
        print(f"\n{title} ({len(findings)}):", file=out)
        for finding in findings:
            print(
                f"  {finding.code}  {finding.file}  {finding.path}".rstrip(), file=out
            )
            print(f"       {finding.message}", file=out)
    if report.skipped:
        print(
            f"\nNo se comprobaron {report.skipped[0]}–{report.skipped[-1]}: necesitan "
            "que menairos.toml y el YAML de tareas cumplan su esquema.",
            file=out,
        )
    errors = _count(len(report.errors), "error", "errores", "ningún error")
    warnings = _count(len(report.warnings), "aviso", "avisos", "ningún aviso")
    print(f"\nResultado: {errors} y {warnings}.", file=out)


def _count(n: int, one: str, many: str, none: str) -> str:
    if n == 0:
        return none
    return f"1 {one}" if n == 1 else f"{n} {many}"
