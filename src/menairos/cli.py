"""Command-line entry point for Menairos.

Every text the CLI shows is in Spanish, argparse's own included: the usage
prefix, the group titles, ``-h`` and the error messages the ``spec`` commands
can produce are translated with argparse's public API and a small table.
"""

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NoReturn, TextIO

from menairos import __version__, environment
from menairos.spec_publication import Item, Publication, publish_spec
from menairos.spec_validation import (
    CONFIG_CHECKS,
    DATA_CHECKS,
    Finding,
    Report,
    UsageError,
    validate_spec,
)

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
    (
        re.compile(r"argument (\S+): ignored explicit argument (.*)"),
        "{0} no admite un valor: {1}",
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
        help="comprueba la especificación (errores E01–E13 y avisos A01–A04)",
        description=(
            "Comprueba menairos.toml, docs/specs/hito-N.md y hito-N.tareas.yaml, "
            "docs/abiertas.md y docs/decisiones/. Sale con 0 sin errores (aunque "
            "haya avisos), 1 con errores y 2 si no se puede ejecutar."
        ),
    )
    _spec_options(validar, "salida en JSON: ok, errores y avisos")
    validar.set_defaults(run=_spec_validar)
    publicar: _Parser = spec_commands.add_parser(
        "publicar",
        help="publica el hito en GitHub: etiquetas, milestone, issues y dependencias",
        description=(
            "Comprueba la especificación con spec validar y publica en el repo de "
            "proyecto.repo de menairos.toml las etiquetas, el milestone, un issue por "
            "tarea y sus dependencias «blocked by». Repetirla no duplica nada, y nunca "
            "cierra ni borra un issue. Sale con 0 si todo se publicó (aunque haya "
            "avisos), 1 con errores y 2 si no se puede ejecutar."
        ),
    )
    publicar.options.add_argument(
        "--seco",
        action="store_true",
        help="muestra lo que haría sin escribir nada en GitHub",
    )
    _spec_options(
        publicar,
        "salida en JSON: creados, actualizados, quitados, sin cambios, avisos y "
        "errores",
    )
    publicar.set_defaults(run=_spec_publicar)
    entorno: _Parser = commands.add_parser(
        "entorno",
        help="prepara el entorno del proyecto: herramientas locales y repo",
        description=(
            "Comprueba la máquina (capa local) y prepara el repo (capa repo): escribe "
            "las plantillas sin sobrescribir nunca un fichero, ejecuta uv sync y "
            "pre-commit install, y hace el primer commit en main si el repo es nuevo, "
            "sin push. Sin capa, ejecuta las dos. Cada paso acaba en ok, hecho, manual "
            "(con la orden exacta) o error, y repetirla no cambia nada. Sale con 0 si "
            "todo queda en ok o hecho, 1 si hay algún manual o error, y 2 si no se "
            "puede ejecutar."
        ),
    )
    entorno.add_argument_group("argumentos").add_argument(
        "capa",
        nargs="?",
        choices=environment.LAYERS,
        metavar="CAPA",
        help=f"la capa: {' o '.join(environment.LAYERS)} (por defecto, las dos)",
    )
    entorno.options.add_argument(
        "--comprobar",
        action="store_true",
        help="solo comprueba, sin escribir nada; lo que haría sale como manual",
    )
    entorno.options.add_argument(
        "--json", action="store_true", help="salida en JSON: las capas y sus pasos"
    )
    entorno.options.add_argument(
        "--raiz",
        type=Path,
        default=Path("."),
        metavar="RUTA",
        help="raíz del proyecto (por defecto, la carpeta actual)",
    )
    entorno.set_defaults(run=_entorno)
    return parser


def _spec_options(parser: _Parser, json_help: str) -> None:
    """``--hito``, ``--json`` and ``--raiz``, common to the ``spec`` commands."""
    options = parser.options
    options.add_argument(
        "--hito",
        type=_milestone,
        metavar="N",
        help="número del hito (por defecto, el mayor con hito-N.tareas.yaml)",
    )
    options.add_argument("--json", action="store_true", help=json_help)
    options.add_argument(
        "--raiz",
        type=Path,
        default=Path("."),
        metavar="RUTA",
        help="raíz del proyecto (por defecto, la carpeta actual)",
    )


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
    if set(DATA_CHECKS) <= set(report.skipped):
        print(
            f"\nNo se comprobaron {DATA_CHECKS[0]}–{DATA_CHECKS[-1]}: necesitan "
            "que menairos.toml y el YAML de tareas cumplan su esquema.",
            file=out,
        )
    if set(CONFIG_CHECKS) <= set(report.skipped):
        print(
            f"\nNo se comprobó {', '.join(CONFIG_CHECKS)}: necesita que menairos.toml "
            "cumpla su esquema.",
            file=out,
        )
    errors = _count(len(report.errors), "error", "errores", "ningún error")
    warnings = _count(len(report.warnings), "aviso", "avisos", "ningún aviso")
    print(f"\nResultado: {errors} y {warnings}.", file=out)


def _count(n: int, one: str, many: str, none: str) -> str:
    if n == 0:
        return none
    return f"1 {one}" if n == 1 else f"{n} {many}"


# ── spec publicar ───────────────────────────────────────────────────────────


def _spec_publicar(args: argparse.Namespace) -> int:
    try:
        publication = publish_spec(args.raiz, args.hito, dry_run=args.seco)
    except UsageError as error:
        print(f"menairos spec publicar: error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_publication_json(publication), ensure_ascii=False, indent=2))
    else:
        _print_publication(publication, sys.stdout)
    return 0 if publication.ok else 1


def _publication_json(publication: Publication) -> dict[str, object]:
    return {
        "ok": publication.ok,
        "seco": publication.dry_run,
        "repo": publication.repo,
        "hito": publication.milestone,
        "creados": publication.created,
        "actualizados": publication.updated,
        "quitados": publication.removed,
        "sin_cambios": publication.unchanged,
        "avisos": publication.warnings,
        "errores": publication.errors,
    }


_SECTIONS = (
    ("created", "Creados", "Se crearían"),
    ("updated", "Actualizados", "Se actualizarían"),
    ("removed", "Quitados", "Se quitarían"),
)
_KINDS = (
    ("etiqueta", "etiqueta", "etiquetas"),
    ("milestone", "milestone", "milestones"),
    ("issue", "issue", "issues"),
    ("dependencia", "dependencia", "dependencias"),
)


def _print_publication(publication: Publication, out: TextIO) -> None:
    repo = publication.repo or "?"
    print(f"spec publicar · hito {publication.milestone} · {repo}", file=out)
    if publication.dry_run:
        print("En seco: no se escribe nada en GitHub; esto es lo que haría.", file=out)
    for name, title, dry_title in _SECTIONS:
        items: list[Item] = getattr(publication, name)
        if not items:
            continue
        shown = dry_title if publication.dry_run else title
        print(f"\n{shown} ({len(items)}):", file=out)
        for item in items:
            print(f"  {_describe(item, removed=name == 'removed')}", file=out)
    counts = [
        _count(
            sum(1 for i in publication.unchanged if i["tipo"] == kind), one, many, ""
        )
        for kind, one, many in _KINDS
    ]
    counts = [c for c in counts if c]
    if counts:
        listed = (
            counts[0]
            if len(counts) == 1
            else f"{', '.join(counts[:-1])} y {counts[-1]}"
        )
        print(f"\nSin cambios: {listed}.", file=out)
    for title, notices in (
        ("Avisos", publication.warnings),
        ("Errores", publication.errors),
    ):
        if not notices:
            continue
        print(f"\n{title} ({len(notices)}):", file=out)
        for item in notices:
            where = "  ".join(
                str(part)
                for part in (
                    item.get("tarea"),
                    f"#{item['numero']}" if item.get("numero") else None,
                    item.get("fichero"),
                    item.get("ruta"),
                )
                if part
            )
            print(f"  {item['codigo']}  {where}".rstrip(), file=out)
            print(f"       {item['mensaje']}", file=out)
    writes = _count(publication.writes, "escritura", "escrituras", "ninguna escritura")
    if not publication.ok:
        result = f"con errores, tras {writes}"
    elif publication.dry_run:
        result = f"haría {writes}"
    else:
        result = writes
    print(f"\nResultado: {result}.", file=out)


def _number(value: object) -> str:
    return f"#{value}" if value else "(nuevo)"


def _describe(item: Item, *, removed: bool = False) -> str:
    kind = item["tipo"]
    if kind == "etiqueta":
        return f"etiqueta     {item['nombre']}"
    if kind == "milestone":
        return f"milestone    {_number(item['numero'])} {item['titulo']}"
    if kind == "issue":
        line = f"issue        {_number(item['numero'])} {item['titulo']}"
        if item.get("cambios"):
            line += f"  ({', '.join(item['cambios'])})"
        return line
    verb = "ya no depende de" if removed else "depende de"
    return (
        f"dependencia  {_number(item['numero'])} {item['tarea']} {verb} "
        f"{_number(item['bloqueado_por'])} {item['depende_de']}"
    )


# ── entorno ─────────────────────────────────────────────────────────────────


def _entorno(args: argparse.Namespace) -> int:
    try:
        report = environment.run_environment(
            args.raiz,
            args.capa,
            check_only=args.comprobar,
            notify=lambda message: print(message, file=sys.stderr, flush=True),
        )
    except environment.UsageError as error:
        print(f"menairos entorno: error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_environment_json(report), ensure_ascii=False, indent=2))
    else:
        _print_environment(report, sys.stdout)
    return 0 if report.ok else 1


def _environment_json(report: environment.Report) -> dict[str, object]:
    def step(item: environment.Step) -> dict[str, object]:
        return {
            "paso": item.name,
            "estado": item.state,
            "detalle": item.detail,
            "orden": item.order,
            "avisos": item.warnings,
            **item.lists,
        }

    return {
        "ok": report.ok,
        "comprobar": report.check_only,
        "raiz": str(report.root),
        "capas": [
            {
                "capa": layer.name,
                "pasos": [step(s) for s in layer.steps],
                "sin_ejecutar": layer.not_run,
            }
            for layer in report.layers
        ],
        "despues": list(report.later),
    }


def _print_environment(report: environment.Report, out: TextIO) -> None:
    print(f"menairos entorno · {report.root.resolve()}", file=out)
    if report.check_only:
        print("Solo se comprueba: no se escribe nada.", file=out)
    for layer in report.layers:
        print(f"\nCapa {layer.name}", file=out)
        for item in layer.steps:
            print(f"  {item.state:<7}{item.name:<18}{item.detail}".rstrip(), file=out)
            for name, values in item.lists.items():
                print(f"{'':9}{name.replace('_', ' ')}:", file=out)
                for value in values:
                    print(f"{'':11}{value}", file=out)
            if item.order:
                print(f"{'':9}orden: {item.order}", file=out)
            for warning in item.warnings:
                print(f"{'':9}aviso: {warning}", file=out)
        if layer.not_run:
            print(f"  Sin ejecutar: {', '.join(layer.not_run)}.", file=out)
    if report.later:
        print(
            f"\nLas capas {' y '.join(report.later)} aún no están: llegan en una "
            "versión posterior.",
            file=out,
        )
    steps = list(report.steps())
    counts = [
        _count(sum(1 for s in steps if s.state == state), state, plural, "")
        for state, plural in (("manual", "manuales"), ("error", "errores"))
    ]
    counts = [c for c in counts if c]
    result = " y ".join(counts) if counts else "todo en verde"
    print(f"\nResultado: {result}.", file=out)
