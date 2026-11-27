"""``menairos spec validar``: check the specification of a milestone (hito-0.md 2.3).

:func:`validate_spec` reads ``menairos.toml``, ``docs/specs/hito-N.md`` and
``docs/specs/hito-N.tareas.yaml``, ``docs/abiertas.md`` and ``docs/decisiones/``
under a root folder and returns a :class:`Report` with the errors (E01–E12) and
warnings (A01–A04). E13 arrives with the stack templates (T-10).

A missing input is a :class:`UsageError` (exit code 2 in the CLI); a file that
exists but cannot be read is an error of the check that needed it. If E01 or
E02 fail, E03–E09 are skipped, because they need valid data; E10–E12 do not
use the data and always run. A01 and A02 look at the documents as written,
before :func:`menairos.schemas.apply_defaults`.
"""

import difflib
import os
import re
import tomllib
from collections import deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from menairos import markdown
from menairos.schemas import (
    DuplicateKeyError,
    SchemaName,
    apply_defaults,
    format_path,
    load_document,
    validate,
)

CONFIG_FILE = "menairos.toml"
SPECS_DIR = "docs/specs"
OPEN_QUESTIONS_FILE = "docs/abiertas.md"
ADR_DIR = "docs/decisiones"

FUNCTIONAL_SECTION = "Validación funcional"
DATA_CHECKS = ("E03", "E04", "E05", "E06", "E07", "E08", "E09")

_TASKS_FILE = re.compile(r"hito-(0|[1-9][0-9]*)\.tareas\.yaml")
_ADR_FILE = re.compile(r"[0-9]{4}-.*\.md")
_ADR_STACK_LINE = "- **Tipo:** stack"
_JUSTIFICATION = "**Justificación:**"
_LIST_ITEM = re.compile(r" {0,3}[-*+](?:[ \t]+(.*))?")
_CHECK_MARKS = ("✅", "👁")
_COMMAND_AT_END = re.compile(r"\s—\s+(`+)(.+?)\1[ \t]*$")


class UsageError(Exception):
    """The command cannot run: a missing input or a wrong argument (exit 2)."""


@dataclass(frozen=True)
class Finding:
    """An error or warning of ``spec validar``.

    ``file`` is relative to the root, with ``/``. ``path`` is a data path
    (``tareas[3].depende_de[0]``) or, in Markdown, the anchor of the section
    (``#validación-funcional``); ``""`` is the whole file.
    """

    code: str
    message: str
    file: str
    path: str


@dataclass(frozen=True)
class Report:
    """The result of validating a milestone's specification."""

    milestone: int
    tasks_file: str
    errors: tuple[Finding, ...]
    warnings: tuple[Finding, ...]
    skipped: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """True if there are no errors (warnings do not count)."""
        return not self.errors


def latest_milestone(root: Path) -> int:
    """The highest N with a ``docs/specs/hito-N.tareas.yaml``."""
    specs = root / SPECS_DIR
    found = (
        [int(m[1]) for p in specs.iterdir() if (m := _TASKS_FILE.fullmatch(p.name))]
        if specs.is_dir()
        else []
    )
    if not found:
        raise UsageError(
            f"no hay ningún {SPECS_DIR}/hito-N.tareas.yaml en «{root}»: "
            "indica la raíz del proyecto con --raiz"
        )
    return max(found)


def validate_spec(root: Path, milestone: int | None = None) -> Report:
    """Validate the specification of ``milestone`` (by default, the latest)."""
    if not root.is_dir():
        raise UsageError(f"la raíz «{root}» no existe o no es una carpeta")
    if milestone is None:
        milestone = latest_milestone(root)
    tasks_file = f"{SPECS_DIR}/hito-{milestone}.tareas.yaml"
    spec_file = f"{SPECS_DIR}/hito-{milestone}.md"
    _require(root, [CONFIG_FILE, tasks_file, spec_file, OPEN_QUESTIONS_FILE], ADR_DIR)

    errors: list[Finding] = []
    warnings: list[Finding] = []
    config, config_ok = _load(root, CONFIG_FILE, "menairos", "E01", errors)
    tasks, tasks_ok = _load(root, tasks_file, "tareas", "E02", errors)
    if tasks_ok and tasks["hito"] != milestone:
        message = (
            f"el fichero es del hito {milestone} y «hito» dice {tasks['hito']}: "
            "el número del nombre y el del contenido deben coincidir"
        )
        errors.append(Finding("E02", message, tasks_file, "hito"))

    config_eff = apply_defaults("menairos", config) if config_ok else None
    tasks_eff = apply_defaults("tareas", tasks) if tasks_ok else None
    skipped: tuple[str, ...] = ()
    if tasks_eff is not None and config_ok:
        errors += _graph_checks(tasks_eff["tareas"], tasks_file)
        errors += _link_checks(root, tasks_eff["tareas"], tasks_file)
    else:
        skipped = DATA_CHECKS
    errors += _functional_section(root, spec_file)
    errors += _open_questions(root)
    errors += _stack_adr(root)

    if tasks_ok:
        warnings += _motivo_without_critica(tasks["tareas"], tasks_file)
    if config_eff is not None:
        warnings += _config_coherence(config_eff)
    if config_eff is not None and tasks_eff is not None:
        warnings += _area_with_parallelism(tasks["tareas"], config_eff, tasks_file)
        warnings += _codex_outside_manual(tasks_eff["tareas"], config_eff, tasks_file)

    return Report(
        milestone,
        tasks_file,
        tuple(_sorted(errors)),
        tuple(_sorted(warnings)),
        skipped,
    )


# ── Reading ─────────────────────────────────────────────────────────────────


def _require(root: Path, files: Sequence[str], folder: str) -> None:
    """Raise a UsageError naming every input that is missing."""
    missing = [f for f in files if not (root / f).is_file()]
    if not (root / folder).is_dir():
        missing.append(f"{folder}/")
    if missing:
        listed = ", ".join(f"«{m}»" for m in missing)
        raise UsageError(f"faltan ficheros del proyecto en «{root}»: {listed}")


def _load(
    root: Path, name: str, schema: SchemaName, code: str, errors: list[Finding]
) -> tuple[Any, bool]:
    """Load and validate a data file; return (document, valid)."""
    try:
        document = load_document(root / name)
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as error:
        errors.append(Finding(code, _unreadable(error), name, ""))
        return None, False
    try:
        issues = validate(schema, document)
    except RecursionError:
        message = "no se puede validar: está anidado demasiado hondo"
        errors.append(Finding(code, message, name, ""))
        return None, False
    errors += (Finding(code, i.message, name, i.path) for i in issues)
    return document, not issues


def _unreadable(error: BaseException) -> str:
    """Spanish message for a file that cannot be read; the detail is the parser's."""
    match error:
        case UnicodeDecodeError():
            return "no se puede leer: no está en UTF-8"
        case DuplicateKeyError():
            return f"no se puede leer el YAML: {error}"
        case yaml.MarkedYAMLError(problem_mark=mark) if mark is not None:
            where = f"línea {mark.line + 1}, columna {mark.column + 1}"
            return f"no se puede leer el YAML ({where}): {error.problem}"
        case yaml.YAMLError():
            return f"no se puede leer el YAML: {error}"
        case tomllib.TOMLDecodeError():
            return f"no se puede leer el TOML: {error}"
        case RecursionError():
            return "no se puede leer: está anidado demasiado hondo"
        case _:
            return f"no se puede leer: {error}"


def _read_markdown(path: Path) -> markdown.Document | str:
    """The parsed document, or the reason it cannot be read."""
    try:
        return markdown.read(path)
    except UnicodeDecodeError:
        return "no se puede leer: no está en UTF-8"
    except OSError as error:
        return f"no se puede leer: {error.strerror}"


def _sorted(findings: Iterable[Finding]) -> list[Finding]:
    """By code and file; within them, in the order found (document order)."""
    return sorted(findings, key=lambda f: (f.code, f.file))


# ── E03–E07: ids, branches and dependencies ─────────────────────────────────


def _graph_checks(tasks: Sequence[Mapping[str, Any]], file: str) -> list[Finding]:
    found: list[Finding] = []
    found += _repeated(tasks, "id", "E03", "el id «{}» está repetido", file)
    found += _repeated(tasks, "rama", "E04", "la rama «{}» está repetida", file)
    first_index = _first_index(tasks)
    for i, task in enumerate(tasks):
        for j, dep in enumerate(task["depende_de"]):
            at = format_path(("tareas", i, "depende_de", j))
            if dep == task["id"]:
                message = f"«{dep}» depende de sí misma"
                found.append(Finding("E06", message, file, at))
            elif dep not in first_index:
                message = f"la dependencia «{dep}» no es ninguna tarea del hito"
                found.append(Finding("E05", message, file, at))
    found += _cycles(tasks, first_index, file)
    return found


def _repeated(
    tasks: Sequence[Mapping[str, Any]], key: str, code: str, what: str, file: str
) -> Iterator[Finding]:
    seen: dict[str, int] = {}
    for i, task in enumerate(tasks):
        value = task[key]
        if value in seen:
            message = f"{what.format(value)}: ya se usó en tareas[{seen[value]}]"
            yield Finding(code, message, file, format_path(("tareas", i, key)))
        else:
            seen[value] = i


def _first_index(tasks: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    first: dict[str, int] = {}
    for i, task in enumerate(tasks):
        first.setdefault(task["id"], i)
    return first


def _cycles(
    tasks: Sequence[Mapping[str, Any]], first_index: Mapping[str, int], file: str
) -> Iterator[Finding]:
    """One E07 per strongly connected component with more than one task."""
    edges: dict[str, list[str]] = {tid: [] for tid in first_index}
    for task in tasks:
        out = edges[task["id"]]
        for dep in task["depende_de"]:
            if dep != task["id"] and dep in first_index and dep not in out:
                out.append(dep)
    components = [
        c for c in _strongly_connected(list(first_index), edges) if len(c) > 1
    ]
    components.sort(key=lambda c: min(first_index[t] for t in c))
    for component in components:
        members = sorted(component, key=first_index.__getitem__)
        cycle = _shortest_cycle(members[0], set(component), edges)
        message = "ciclo de dependencias: " + " → ".join(cycle)
        if len(members) > len(cycle) - 1:
            message += f"; dependen unas de otras {_join(members)}"
        start, step = cycle[0], cycle[1]
        i, j = next(
            (i, t["depende_de"].index(step))
            for i, t in enumerate(tasks)
            if t["id"] == start and step in t["depende_de"]
        )
        yield Finding("E07", message, file, format_path(("tareas", i, "depende_de", j)))


def _strongly_connected(
    nodes: Sequence[str], edges: Mapping[str, Sequence[str]]
) -> list[list[str]]:
    """Tarjan's algorithm, iterative, so 1000 tasks do not hit the recursion limit."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)

    for root in nodes:
        if root in index:
            continue
        visit(root)
        work: list[tuple[str, Iterator[str]]] = [(root, iter(edges[root]))]
        while work:
            node, pending = work[-1]
            for nxt in pending:
                if nxt not in index:
                    visit(nxt)
                    work.append((nxt, iter(edges[nxt])))
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    component: list[str] = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    components.append(component)
    return components


def _shortest_cycle(
    start: str, component: set[str], edges: Mapping[str, Sequence[str]]
) -> list[str]:
    """The shortest path from ``start`` back to itself inside its component (BFS)."""
    parent: dict[str, str] = {}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in edges[node]:
            if nxt == start:
                path = [node]
                while path[-1] != start:
                    path.append(parent[path[-1]])
                return [*reversed(path), start]
            if nxt in component and nxt not in parent and nxt != start:
                parent[nxt] = node
                queue.append(nxt)
    raise AssertionError("a strongly connected component always has a cycle")


def _join(items: Sequence[str]) -> str:
    """«a, b y c»."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} y {items[-1]}"


# ── E08–E09: links of `especificacion` ──────────────────────────────────────


def _link_checks(
    root: Path, tasks: Sequence[Mapping[str, Any]], file: str
) -> list[Finding]:
    base = (root / file).parent
    real_root = root.resolve()
    cache: dict[Path, markdown.Document | str] = {}
    found: list[Finding] = []
    for i, task in enumerate(tasks):
        for j, link in enumerate(task["especificacion"]):
            at = format_path(("tareas", i, "especificacion", j))
            name, _, anchor = link.partition("#")
            problem = _target_problem(root, real_root, base, name)
            if problem:
                found.append(Finding("E08", problem, file, at))
                continue
            if not anchor:
                continue
            target = (base / name).resolve()
            if target not in cache:
                cache[target] = _read_markdown(target)
            document = cache[target]
            if isinstance(document, str):
                found.append(Finding("E09", f"«{name}»: {document}", file, at))
            elif anchor not in document.anchors:
                message = f"el ancla «#{anchor}» no existe en «{name}»"
                close = difflib.get_close_matches(anchor, sorted(document.anchors), 1)
                if close:
                    message += f"; la más parecida es «#{close[0]}»"
                found.append(Finding("E09", message, file, at))
    return found


def _target_problem(root: Path, real_root: Path, base: Path, name: str) -> str | None:
    """Why ``name`` (relative to the YAML's folder) is not a valid link, if so."""
    lexical = Path(os.path.normpath(base / name))
    if not lexical.is_relative_to(root) or not lexical.resolve().is_relative_to(
        real_root
    ):
        return f"«{name}» apunta fuera del repo"
    if not lexical.is_file():
        shown = lexical.relative_to(root).as_posix()
        return f"el fichero «{name}» no existe (se busca en «{shown}»)"
    folder = root
    for part in lexical.relative_to(root).parts:
        if part not in os.listdir(folder):
            return (
                f"«{name}» no coincide en mayúsculas con el fichero del repo: "
                "GitHub distingue mayúsculas"
            )
        folder = folder / part
    return None


# ── E10–E12: Markdown documents ─────────────────────────────────────────────


def _functional_section(root: Path, file: str) -> list[Finding]:
    """E10: one «Validación funcional» with ✅/👁 checks; each ✅ ends in its command."""
    document = _read_markdown(root / file)
    if isinstance(document, str):
        return [Finding("E10", document, file, "")]
    sections = [h for h in document.headings if h.text == FUNCTIONAL_SECTION]
    if not sections:
        message = (
            f"falta la sección «{FUNCTIONAL_SECTION}» (un encabezado con ese texto)"
        )
        return [Finding("E10", message, file, "")]
    heading = sections[0]
    at = f"#{heading.anchor}"
    found: list[Finding] = []
    for repeated in sections[1:]:
        message = (
            f"la sección «{FUNCTIONAL_SECTION}» está repetida: líneas "
            f"{heading.line} y {repeated.line}"
        )
        found.append(Finding("E10", message, file, f"#{repeated.anchor}"))
    checks = [
        (line, text)
        for line, text in _list_items(document.section(heading))
        if text.startswith(_CHECK_MARKS)
    ]
    if not checks:
        message = (
            f"la sección «{FUNCTIONAL_SECTION}» (línea {heading.line}) no tiene "
            "ninguna comprobación: un elemento de lista que empiece por ✅ o 👁"
        )
        found.append(Finding("E10", message, file, at))
    for line, text in checks:
        if text.startswith("✅") and not _ends_with_command(text):
            message = (
                f"la comprobación ✅ de la línea {line} no termina con su orden: "
                "« — `orden`» (6.2)"
            )
            found.append(Finding("E10", message, file, at))
    return found


def _list_items(lines: Sequence[markdown.Line]) -> Iterator[tuple[int, str]]:
    """(line, text) of each list item, its continuation lines joined with spaces."""
    current: list[str] = []
    start = 0
    for line in lines:
        item = None if line.in_code else _LIST_ITEM.fullmatch(line.text)
        ends = (
            line.in_code or not line.text.strip() or line.text.lstrip().startswith("#")
        )
        if current and (item or ends):
            yield start, " ".join(current)
            current = []
        if item:
            start, current = line.number, [(item[1] or "").strip()]
        elif current:
            current.append(line.text.strip())
    if current:
        yield start, " ".join(current)


def _ends_with_command(text: str) -> bool:
    match = _COMMAND_AT_END.search(text)
    if not match:
        return False
    ticks, code = match[1], match[2]
    inner = re.search(rf"(?<!`)`{{{len(ticks)}}}(?!`)", code)
    return bool(code.strip()) and inner is None


def _open_questions(root: Path) -> list[Finding]:
    """E11: each ``###`` point of abiertas.md has a **Justificación:** with text."""
    file = OPEN_QUESTIONS_FILE
    document = _read_markdown(root / file)
    if isinstance(document, str):
        return [Finding("E11", document, file, "")]
    found: list[Finding] = []
    for heading in document.headings:
        if heading.level != 3:
            continue
        if not any(_is_justification(line) for line in document.section(heading)):
            message = (
                f"el punto «{heading.text}» (línea {heading.line}) no tiene una línea "
                f"«{_JUSTIFICATION}» con texto"
            )
            path = f"#{heading.anchor}" if heading.anchor else ""
            found.append(Finding("E11", message, file, path))
    return found


def _is_justification(line: markdown.Line) -> bool:
    text = line.text.lstrip(" ")
    return (
        not line.in_code
        and text.startswith(_JUSTIFICATION)
        and bool(text.removeprefix(_JUSTIFICATION).strip())
    )


def _stack_adr(root: Path) -> list[Finding]:
    """E12: at least one ADR (``NNNN-*.md``) with the line ``- **Tipo:** stack``."""
    folder = root / ADR_DIR
    found: list[Finding] = []
    has_stack = False
    for path in sorted(folder.iterdir()):
        if not (_ADR_FILE.fullmatch(path.name) and path.is_file()):
            continue
        document = _read_markdown(path)
        if isinstance(document, str):
            found.append(Finding("E12", document, f"{ADR_DIR}/{path.name}", ""))
        elif any(
            not line.in_code and line.text == _ADR_STACK_LINE for line in document.lines
        ):
            has_stack = True
    if not has_stack:
        message = (
            "no hay ningún ADR de tipo «stack»: hace falta una línea "
            f"«{_ADR_STACK_LINE}» en algún {ADR_DIR}/NNNN-*.md"
        )
        found.append(Finding("E12", message, f"{ADR_DIR}/", ""))
    return found


# ── Warnings ────────────────────────────────────────────────────────────────


def _motivo_without_critica(
    tasks: Sequence[Mapping[str, Any]], file: str
) -> Iterator[Finding]:
    """A01, on the tasks as written."""
    for i, task in enumerate(tasks):
        if "motivo_critica" in task and task.get("critica") is not True:
            message = (
                f"«{task['id']}» tiene motivo_critica pero no es crítica: "
                "falta «critica: true» o sobra el motivo"
            )
            yield Finding(
                "A01", message, file, format_path(("tareas", i, "motivo_critica"))
            )


def _area_with_parallelism(
    tasks: Sequence[Mapping[str, Any]], config: Mapping[str, Any], file: str
) -> Iterator[Finding]:
    """A02: a task without an explicit area (as written) when tasks run in parallel."""
    parallelism: int = config["autonomia"]["paralelismo"]
    if parallelism <= 1:
        return
    for i, task in enumerate(tasks):
        if "area" not in task:
            message = (
                f"«{task['id']}» no tiene area explícita y autonomia.paralelismo es "
                f"{parallelism}: tomará «general»"
            )
            yield Finding("A02", message, file, format_path(("tareas", i)))


def _config_coherence(config: Mapping[str, Any]) -> Iterator[Finding]:
    """A03: the two coherences of menairos.toml (hito-0.md 2.2)."""
    if config["modo"]["defecto"] == "automatico" and (
        config["proyecto"]["visibilidad"] == "privado"
    ):
        message = (
            "el modo automático en un repo privado requiere GitHub Pro: "
            "GitHub Free no aplica los rulesets en los repos privados"
        )
        yield Finding("A03", message, CONFIG_FILE, "modo.defecto")
    if config["revisores"]["pr"] == "codex":
        message = (
            "Codex como revisor bloqueante de los PR está sin verificar: hasta que el "
            "hito 0 confirme que puede ser un check bloqueante, el revisor es Claude"
        )
        yield Finding("A03", message, CONFIG_FILE, "revisores.pr")


def _codex_outside_manual(
    tasks: Sequence[Mapping[str, Any]], config: Mapping[str, Any], file: str
) -> Iterator[Finding]:
    """A04: ``quien: codex`` in a task whose effective mode is not manual."""
    default: str = config["modo"]["defecto"]
    for i, task in enumerate(tasks):
        mode: str = task["modo"] or default
        if task["quien"] == "codex" and mode != "manual":
            message = (
                f"«{task['id']}» la hace Codex en modo {mode}: Codex como "
                "implementador solo está previsto en modo manual (5.8)"
            )
            yield Finding("A04", message, file, format_path(("tareas", i, "quien")))
