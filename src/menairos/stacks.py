"""Stack templates and the common contract (hito-0.md 3.3).

A stack template is a folder in ``plantillas/stacks/`` inside the package (so
it travels with ``uv tool install``) with a ``plantilla.toml`` manifest and a
``ficheros/`` folder that mirrors the project. Every file there ends in
``.plantilla``, which composition removes: git, ruff and pyright do not read
the nested ``.gitignore`` or ``pyproject.toml`` of the templates, nor trip on
their holes. Paths and texts are filled with :func:`menairos.templates.fill`;
templates have no logic.

* :func:`compose` returns, in memory, the files of a project for its
  ``stack.plantillas``: the templates in order (each after the ones it
  requires, otherwise in the order of ``stack.plantillas``), the mergeable
  files merged, and the two files the code generates
  (``.claude/settings.json`` and ``scripts/stack/plantillas.txt``). Writing
  them into a repo is ``menairos entorno`` (T-11).
* :func:`contract` returns the :class:`Contract`: who owns a file (by
  extension and, failing that, by folder), its format order and the test
  orders. The ``PostToolUse`` hook (T-20) and ``/implementar`` (T-22) use it.

Every problem is reported at once in a :class:`StackError`; messages are in
Spanish, because they are shown to the user.
"""

import json
import keyword
import os
import re
import shlex
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

from menairos import templates
from menairos.schemas import apply_defaults, load_text, validate

MANIFEST = "plantilla.toml"
FILES_DIR = "ficheros"
SUFFIX = ".plantilla"
CI_FILE = ".github/workflows/ci.yml"
CI_MARKER = "      # menairos: pasos de las plantillas de lenguaje"
SETTINGS_FILE = ".claude/settings.json"
OWNERSHIP_FILE = "scripts/stack/plantillas.txt"
GENERATED = (SETTINGS_FILE, OWNERSHIP_FILE)
MARKETPLACE_REPO = "pdromer0/menairos"
PLUGIN = "menairos@menairos"
SETTINGS_SCHEMA = "https://json.schemastore.org/claude-code-settings.json"
PACKAGE_ROOT: Traversable = files("menairos") / "plantillas" / "stacks"

BASE_ORDERS = ("n1", "n2", "n3")
LANGUAGE_ORDERS = ("formato", "formato_fichero", "lint", "tipos", "tests_area")
BASE_PARTS = ("scripts/n1.sh", "scripts/n2.sh", "scripts/n3.sh")
_PLACEHOLDERS = {"formato_fichero": "{fichero}", "tests_area": "{rutas}"}
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*")
_PACKAGE_HOLE = "{{paquete}}"


class StackError(ValueError):
    """The templates cannot be loaded or composed; ``problems`` has one line each."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("\n".join(self.problems))


@dataclass(frozen=True)
class Check:
    """A deliberate check (hito-0.md 3.6): what is provoked and what must catch it."""

    name: str
    provokes: str
    caught_by: str
    message: str


@dataclass(frozen=True)
class Template:
    """A stack template, read from its manifest; ``files`` are its raw texts.

    ``files`` maps the project path (without ``.plantilla``, holes unfilled)
    to the text of the template file.
    """

    name: str
    version: str
    kind: str
    requires: tuple[str, ...]
    tools: Mapping[str, str]
    extensions: tuple[str, ...]
    folders: tuple[str, ...]
    orders: Mapping[str, str]
    deny: tuple[str, ...]
    ask: tuple[str, ...]
    allow: tuple[str, ...]
    mergeable: frozenset[str]
    checks: tuple[Check, ...]
    files: Mapping[str, str]


@dataclass(frozen=True)
class StackFile:
    """A composed file: its text and whether it is executable (the ``.sh``)."""

    text: str
    executable: bool


# ── Loading ─────────────────────────────────────────────────────────────────


def available(roots: Sequence[Traversable] = (PACKAGE_ROOT,)) -> tuple[str, ...]:
    """The names of the templates in ``roots`` (folders with a manifest), sorted."""
    return tuple(sorted(_folders(roots)))


def load(name: str, roots: Sequence[Traversable] = (PACKAGE_ROOT,)) -> Template:
    """Read and check the template ``name``."""
    folders = _folders(roots)
    if name not in folders:
        listed = ", ".join(sorted(folders)) or "ninguna"
        raise StackError([f"la plantilla «{name}» no existe; las que hay: {listed}"])
    return _read_template(name, folders[name])


def _folders(roots: Sequence[Traversable]) -> dict[str, Traversable]:
    """Template folders by name; the same name in two roots is an error."""
    found: dict[str, Traversable] = {}
    problems: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for folder in root.iterdir():
            if not folder.is_dir() or not folder.joinpath(MANIFEST).is_file():
                continue
            if folder.name in found:
                problems.append(
                    f"la plantilla «{folder.name}» está repetida en dos carpetas de "
                    "plantillas"
                )
            found[folder.name] = folder
    if problems:
        raise StackError(problems)
    return found


def _read_template(name: str, folder: Traversable) -> Template:
    where = f"{name}/{MANIFEST}"
    try:
        document = tomllib.loads(folder.joinpath(MANIFEST).read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise StackError([f"«{where}» no se puede leer: {error}"]) from None
    issues = validate("plantilla", document)
    if issues:
        raise StackError(
            [f"«{where}»: {i.path or 'la raíz'}: {i.message}" for i in issues]
        )
    data: dict[str, Any] = apply_defaults("plantilla", document)
    head, orders = data["plantilla"], data["ordenes"]
    owns: dict[str, list[str]] = data.get("propiedad", {})
    template = Template(
        name=head["nombre"],
        version=head["version"],
        kind=head["tipo"],
        requires=tuple(head["requiere"]),
        tools=dict(data["herramientas"]),
        extensions=tuple(owns.get("extensiones", ())),
        folders=tuple(owns.get("carpetas", ())),
        orders=dict(orders),
        deny=tuple(data["permisos"]["denegar"]),
        ask=tuple(data["permisos"]["preguntar"]),
        allow=tuple(data["permisos"]["permitir"]),
        mergeable=frozenset(data["ficheros"]["fusionables"]),
        checks=tuple(
            Check(c["nombre"], c["provoca"], c["salta"], c["mensaje"])
            for c in data["comprobaciones"]
        ),
        files=_read_files(name, folder.joinpath(FILES_DIR)),
    )
    problems = _template_problems(template, name)
    if problems:
        raise StackError([f"«{where}»: {p}" for p in problems])
    return template


def _read_files(name: str, folder: Traversable) -> dict[str, str]:
    """The template files by project path; each one must end in ``.plantilla``."""
    found: dict[str, str] = {}
    problems: list[str] = []

    def walk(node: Traversable, prefix: str) -> None:
        for child in node.iterdir():
            path = f"{prefix}{child.name}"
            if child.is_dir():
                walk(child, f"{path}/")
            elif path.endswith(SUFFIX):
                found[path.removesuffix(SUFFIX)] = child.read_text(encoding="utf-8")
            else:
                problems.append(
                    f"«{name}/{FILES_DIR}/{path}» no acaba en «{SUFFIX}»: cada fichero "
                    "de una plantilla de stack lleva ese sufijo"
                )

    if folder.is_dir():
        walk(folder, "")
    if problems:
        raise StackError(problems)
    return dict(sorted(found.items()))


def _template_problems(template: Template, folder: str) -> list[str]:
    """What the schema cannot check about one template."""
    problems: list[str] = []
    if template.name != folder:
        problems.append(
            f"el nombre «{template.name}» no es el de su carpeta, «{folder}»"
        )
    if template.name in template.requires:
        problems.append("la plantilla se requiere a sí misma")
    if template.kind == "base":
        if template.name != "base":
            problems.append("solo la plantilla «base» puede ser de tipo base")
        allowed, parts = BASE_ORDERS, BASE_PARTS
    else:
        allowed = LANGUAGE_ORDERS
        parts = tuple(f"scripts/stack/{template.name}/{n}.sh" for n in ("n1", "n3"))
    problems += [
        f"la orden «{order}» no es de una plantilla de tipo {template.kind}"
        for order in template.orders
        if order not in allowed
    ]
    problems += [
        f"la orden «{order}» tiene que llevar el hueco {hole}"
        for order, hole in _PLACEHOLDERS.items()
        if order in template.orders and hole not in template.orders[order]
    ]
    problems += [
        f"falta el fichero «{p}{SUFFIX}»" for p in parts if p not in template.files
    ]
    for path in sorted(template.mergeable):
        if path not in _MERGERS:
            problems.append(
                f"«{path}» no se puede fusionar: los fusionables son "
                + ", ".join(_MERGERS)
            )
        elif path not in template.files:
            problems.append(f"el fusionable «{path}» no está en {FILES_DIR}/")
    problems += [
        f"trae «{path}», que genera menairos"
        for path in GENERATED
        if path in template.files
    ]
    ci = template.files.get(CI_FILE)
    if ci is not None:
        markers = ci.count(CI_MARKER)
        if template.kind == "base" and (
            markers != 1 or ci.count(f"{CI_MARKER}\n\n") != 1
        ):
            problems.append(
                f"«{CI_FILE}» tiene que llevar una vez la línea marcador «"
                f"{CI_MARKER.strip()}», seguida de una línea en blanco"
            )
        if template.kind != "base" and markers:
            problems.append(f"«{CI_FILE}» lleva la línea marcador, que es de base")
    return problems


# ── Order ───────────────────────────────────────────────────────────────────


def resolve(
    config: Mapping[str, Any], roots: Sequence[Traversable] = (PACKAGE_ROOT,)
) -> tuple[Template, ...]:
    """The templates of ``stack.plantillas`` in the order they are applied.

    ``config`` is a valid ``menairos.toml`` with its defaults. Each template
    goes after the ones it requires; the rest keep the order of
    ``stack.plantillas``. Also checks the stack as a whole: one base, at least
    one language template, and no extension or folder owned twice.
    """
    names: list[str] = list(config["stack"]["plantillas"])
    folders = _folders(roots)
    problems: list[str] = []
    loaded: dict[str, Template] = {}
    listed = ", ".join(sorted(folders)) or "ninguna"
    for name in names:
        if name not in folders:
            problems.append(f"la plantilla «{name}» no existe; las que hay: {listed}")
            continue
        try:
            loaded[name] = _read_template(name, folders[name])
        except StackError as error:
            problems += error.problems
    if problems:
        raise StackError(problems)
    for template in loaded.values():
        problems += [
            f"«{template.name}» requiere «{needed}», que no está en stack.plantillas"
            for needed in template.requires
            if needed not in loaded
        ]
    if problems:
        raise StackError(problems)

    ordered: list[Template] = []
    pending = [loaded[name] for name in names]
    while pending:
        done = {t.name for t in ordered}
        ready = next((t for t in pending if set(t.requires) <= done), None)
        if ready is None:
            cycle = " → ".join(t.name for t in pending)
            raise StackError([f"las plantillas se requieren en ciclo: {cycle}"])
        ordered.append(ready)
        pending.remove(ready)

    languages = [t for t in ordered if t.kind == "lenguaje"]
    if not languages:
        problems.append(
            "stack.plantillas no tiene ninguna plantilla de lenguaje: el contrato "
            "común pide formato, lint, tipos y tests, y base no los tiene"
        )
    problems += _ownership_problems(languages)
    if problems:
        raise StackError(problems)
    return tuple(ordered)


def _ownership_problems(languages: Sequence[Template]) -> list[str]:
    problems: list[str] = []
    for i, first in enumerate(languages):
        for second in languages[i + 1 :]:
            for ext in sorted(set(first.extensions) & set(second.extensions)):
                problems.append(
                    f"la extensión «{ext}» es de «{first.name}» y de «{second.name}»"
                )
            for a in first.folders:
                for b in second.folders:
                    if a.startswith(b) or b.startswith(a):
                        problems.append(
                            f"las carpetas «{a}» de «{first.name}» y «{b}» de "
                            f"«{second.name}» se solapan"
                        )
    return problems


# ── Composition ─────────────────────────────────────────────────────────────


def compose(
    config: Mapping[str, Any], roots: Sequence[Traversable] = (PACKAGE_ROOT,)
) -> dict[str, StackFile]:
    """The files of a project for ``config`` (``menairos.toml`` as read).

    Returns them in memory, by path and sorted. Raises :class:`StackError`
    with every problem found.
    """
    try:
        values = templates.values(config)
    except templates.TemplateError as error:
        raise StackError(error.problems) from None
    effective: dict[str, Any] = apply_defaults("menairos", config)
    stack = resolve(effective, roots)

    if any(_uses_package(t) for t in stack):
        package, problem = package_name(effective["proyecto"]["nombre"])
        if problem:
            raise StackError([problem])
        values["paquete"] = package

    problems: list[str] = []
    brought: dict[str, list[tuple[Template, str]]] = {}
    for template in stack:
        for raw_path, raw_text in template.files.items():
            try:
                path = templates.fill(raw_path, values, name=f"{template.name}: ruta")
                text = templates.fill(
                    raw_text,
                    values,
                    yaml=path.endswith((".yaml", ".yml")),
                    name=f"{template.name}/{raw_path}",
                )
            except templates.TemplateError as error:
                problems += error.problems
                continue
            brought.setdefault(path, []).append((template, text))
    if problems:
        raise StackError(problems)

    composed: dict[str, str] = {}
    for path, sources in brought.items():
        if path in GENERATED:
            problems.append(
                f"«{path}» lo genera menairos y no lo puede traer una plantilla"
            )
            continue
        if len(sources) > 1 and not all(path in t.mergeable for t, _ in sources):
            names = " y ".join(f"«{t.name}»" for t, _ in sources)
            problems.append(f"«{path}» lo traen {names}, y no es fusionable")
            continue
        try:
            composed[path] = _merge(path, sources)
        except StackError as error:
            problems += error.problems
    if problems:
        raise StackError(problems)

    languages = [t for t in stack if t.kind == "lenguaje"]
    composed[OWNERSHIP_FILE] = ownership_text(languages)
    composed[SETTINGS_FILE] = claude_settings(effective, stack)
    problems += _parse_problems(composed)
    if problems:
        raise StackError(problems)
    return {
        path: StackFile(text, path.endswith(".sh"))
        for path, text in sorted(composed.items())
    }


def package_name(project: str) -> tuple[str, str | None]:
    """The Python package of a project name: lower case and ``-`` → ``_``.

    Returns the package and, if the name is not valid, why (in Spanish).
    """
    package = project.lower().replace("-", "_")
    rule = (
        "el nombre del proyecto tiene que ser ASCII: letras y cifras, empezar por una "
        "letra y separar las palabras con un solo «-» o «_»"
    )
    if not _NAME.fullmatch(project):
        return package, f"«{project}» no sirve de nombre de paquete de Python: {rule}"
    if keyword.iskeyword(package):
        return package, f"«{package}» es una palabra reservada de Python"
    if package in sys.stdlib_module_names:
        return package, f"«{package}» es un módulo de la biblioteca estándar de Python"
    return package, None


def _uses_package(template: Template) -> bool:
    return any(
        _PACKAGE_HOLE in path or _PACKAGE_HOLE in text
        for path, text in template.files.items()
    )


def _merge(path: str, sources: Sequence[tuple[Template, str]]) -> str:
    """One file from what each template brings; the CI is merged always."""
    if path == CI_FILE:
        return _merge_ci(sources)
    if len(sources) == 1:
        return sources[0][1]
    return _MERGERS[path]([text for _, text in sources])


def _merge_gitignore(texts: Sequence[str]) -> str:
    """The first text as is; after a blank line, the new non-empty lines."""
    result = texts[0]
    seen = set(result.splitlines())
    for text in texts[1:]:
        new: list[str] = []
        for line in text.splitlines():
            if line.strip() and line not in seen:
                new.append(line)
                seen.add(line)
        if new:
            result = result.rstrip("\n") + "\n\n" + "\n".join(new) + "\n"
    return result


def _merge_pre_commit(texts: Sequence[str]) -> str:
    """Every fragment starts with ``repos:``; the bodies are joined by a blank line."""
    bodies: list[str] = []
    for text in texts:
        head, _, body = text.partition("\n")
        if head != "repos:":
            raise StackError(
                [
                    "un fragmento de «.pre-commit-config.yaml» tiene que empezar por "
                    "la línea «repos:»"
                ]
            )
        bodies.append(body.strip("\n"))
    return "repos:\n" + "\n\n".join(b for b in bodies if b) + "\n"


def _merge_ci(sources: Sequence[tuple[Template, str]]) -> str:
    """The language fragments, joined by a blank line, replace the marker of base."""
    hosts = [text for template, text in sources if template.kind == "base"]
    if len(hosts) != 1:
        raise StackError(
            [f"«{CI_FILE}» tiene que venir de base, con su línea marcador"]
        )
    fragments = [text.strip("\n") for t, text in sources if t.kind != "base"]
    fragments = [f for f in fragments if f]
    if fragments:
        return hosts[0].replace(CI_MARKER, "\n\n".join(fragments), 1)
    return hosts[0].replace(f"{CI_MARKER}\n\n", "", 1)


def _merge_sections(texts: Sequence[str]) -> str:
    """Base's text and then each template's section, separated by a blank line."""
    return "\n\n".join(t.strip("\n") for t in texts if t.strip("\n")) + "\n"


_MERGERS: dict[str, Callable[[Sequence[str]], str]] = {
    ".gitignore": _merge_gitignore,
    ".pre-commit-config.yaml": _merge_pre_commit,
    CI_FILE: _merge_sections,  # not used: the CI goes through _merge_ci
    "AGENTS.md": _merge_sections,
}


def _parse_problems(composed: Mapping[str, str]) -> list[str]:
    """The composed TOML, YAML and JSON must parse (YAML without repeated keys)."""
    problems: list[str] = []
    for path, text in composed.items():
        suffix = os.path.splitext(path)[1]
        try:
            if suffix in (".toml", ".yaml", ".yml"):
                load_text(text, suffix)
            elif suffix == ".json":
                json.loads(text)
        except (tomllib.TOMLDecodeError, yaml.YAMLError, ValueError) as error:
            problems.append(f"«{path}» compuesto no es válido: {error}")
    return problems


def ownership_text(languages: Iterable[Template]) -> str:
    """``scripts/stack/plantillas.txt``: each language template and what it owns."""
    lines = [
        "# Generado por menairos a partir de los manifiestos: no se edita a mano.",
        "# Cada línea: una plantilla de lenguaje y lo que es suyo, primero las",
        "# extensiones (.x) y después las carpetas (x/). Lo lee scripts/n1.sh.",
    ]
    lines += [" ".join((t.name, *t.extensions, *t.folders)) for t in languages]
    return "\n".join(lines) + "\n"


def claude_settings(config: Mapping[str, Any], stack: Sequence[Template]) -> str:
    """``.claude/settings.json``: the rules of every template and the plugin.

    ``config`` is ``menairos.toml`` with its defaults. In H0 the three modes
    give the same file: the file is one per repo while the mode is per task,
    and an ``ask`` already fails closed in Actions (hito-0.md 3.3). The
    marketplace is pinned to ``v<version>``; a prerelease (``3.0.0-dev``) has
    no tag yet and follows the default branch.
    """
    version: str = config["menairos"]["version"]
    source: dict[str, str] = {"source": "github", "repo": MARKETPLACE_REPO}
    if "-" not in version:
        source["ref"] = f"v{version}"
    settings = {
        "$schema": SETTINGS_SCHEMA,
        "permissions": {
            "deny": _union(t.deny for t in stack),
            "ask": _union(t.ask for t in stack),
            "allow": _union(t.allow for t in stack),
        },
        "extraKnownMarketplaces": {"menairos": {"source": source}},
        "enabledPlugins": {PLUGIN: True},
    }
    return json.dumps(settings, ensure_ascii=False, indent=2) + "\n"


def _union(groups: Iterable[Sequence[str]]) -> list[str]:
    result: list[str] = []
    for group in groups:
        result += [rule for rule in group if rule not in result]
    return result


# ── The contract ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Owner:
    """A language template as the contract sees it: what it owns and its orders."""

    name: str
    extensions: tuple[str, ...]
    folders: tuple[str, ...]
    orders: Mapping[str, str]


def extension(path: str) -> str:
    """The extension of a path, as ``scripts/n1.sh`` computes it.

    What follows the last dot of the file name, once its leading dots are
    removed (``.py`` and ``x.`` have none; ``a.b.py`` has ``.py``).
    """
    name = path.rsplit("/", 1)[-1].lstrip(".")
    if "." not in name or name.endswith("."):
        return ""
    return "." + name.rsplit(".", 1)[1]


class Contract:
    """The common contract of a project's stack (hito-0.md 3.3).

    Paths are relative to ``root`` (the repo root; the current folder if
    ``None``); an absolute path inside it is made relative, and a path that
    goes out of it is an error.
    """

    def __init__(self, owners: Sequence[Owner], root: Path | None = None) -> None:
        self.owners = tuple(owners)
        self.root = root

    def relative(self, path: str | os.PathLike[str]) -> str:
        """``path`` relative to the root, normalised and with ``/``."""
        root = os.path.abspath(self.root if self.root is not None else os.curdir)
        full = os.path.normpath(os.path.join(root, os.fspath(path)))
        relative = os.path.relpath(full, root).replace(os.sep, "/")
        if relative == ".." or relative.startswith("../"):
            raise StackError([f"la ruta «{os.fspath(path)}» está fuera del repo"])
        return relative

    def owner(self, path: str | os.PathLike[str]) -> Owner | None:
        """The template that owns ``path``: by extension, then by folder."""
        relative = self.relative(path)
        ext = extension(relative)
        if ext:
            for owner in self.owners:
                if ext in owner.extensions:
                    return owner
        for owner in self.owners:
            if any(f"{relative}/".startswith(folder) for folder in owner.folders):
                return owner
        return None

    def format_command(self, path: str | os.PathLike[str]) -> str | None:
        """The ``formato_fichero`` order for ``path``, chosen by its extension.

        ``None`` if no template owns its extension (by folder does not count:
        a template formats only its own kind of file).
        """
        relative = self.relative(path)
        ext = extension(relative)
        for owner in self.owners:
            if ext and ext in owner.extensions:
                command = owner.orders["formato_fichero"]
                return command.replace("{fichero}", shlex.quote(relative))
        return None

    def templates_for(
        self, touched: Iterable[str | os.PathLike[str]]
    ) -> tuple[str, ...]:
        """The templates that own some of the touched files, in stack order.

        A touched file nobody owns (``docs/…``, ``pyproject.toml``) is ignored.
        """
        names = {o.name for p in touched if (o := self.owner(p)) is not None}
        return tuple(o.name for o in self.owners if o.name in names)

    def split(self, paths: Iterable[str | os.PathLike[str]]) -> dict[str, list[str]]:
        """Test paths by owner, as ``scripts/n1.sh`` splits them.

        A path nobody owns is an error.
        """
        found: dict[str, list[str]] = {}
        problems: list[str] = []
        for path in paths:
            owner = self.owner(path)
            if owner is None:
                problems.append(
                    f"la ruta «{os.fspath(path)}» no es de ninguna plantilla"
                )
            else:
                found.setdefault(owner.name, []).append(self.relative(path))
        if problems:
            raise StackError(problems)
        return {o.name: found[o.name] for o in self.owners if o.name in found}

    def tests_commands(
        self, paths: Iterable[str | os.PathLike[str]]
    ) -> list[tuple[str, str]]:
        """``(template, order)`` with the ``tests_area`` of each owner of ``paths``."""
        return [
            (
                name,
                self._orders(name)["tests_area"].replace(
                    "{rutas}", " ".join(shlex.quote(p) for p in group)
                ),
            )
            for name, group in self.split(paths).items()
        ]

    def _orders(self, name: str) -> Mapping[str, str]:
        return next(o.orders for o in self.owners if o.name == name)


def contract(
    config: Mapping[str, Any],
    root: Path | None = None,
    roots: Sequence[Traversable] = (PACKAGE_ROOT,),
) -> Contract:
    """The contract of the project ``config`` (``menairos.toml`` as read).

    The orders come from the manifests. With ``root``, what each template owns
    comes from the project's ``scripts/stack/plantillas.txt``, the same file
    ``scripts/n1.sh`` reads; without it, from the manifests.
    """
    issues = validate("menairos", config)
    if issues:
        raise StackError(
            [
                f"menairos.toml no es válido: {i.path or 'la raíz'}: {i.message}"
                for i in issues
            ]
        )
    stack = resolve(apply_defaults("menairos", config), roots)
    languages = {t.name: t for t in stack if t.kind == "lenguaje"}
    if root is None:
        owners = [
            Owner(t.name, t.extensions, t.folders, t.orders) for t in languages.values()
        ]
        return Contract(owners, None)
    owners = []
    problems: list[str] = []
    for name, owned in _read_ownership(root / OWNERSHIP_FILE):
        if name not in languages:
            problems.append(
                f"«{OWNERSHIP_FILE}» nombra «{name}», que no es una plantilla de "
                "lenguaje de stack.plantillas"
            )
            continue
        exts = tuple(p for p in owned if not p.endswith("/"))
        folders = tuple(p for p in owned if p.endswith("/"))
        owners.append(Owner(name, exts, folders, languages[name].orders))
    if problems:
        raise StackError(problems)
    return Contract(owners, root)


def _read_ownership(path: Path) -> list[tuple[str, list[str]]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise StackError([f"no se puede leer «{path}»: {error.strerror}"]) from None
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        words = line.split()
        if words and not words[0].startswith("#"):
            rows.append((words[0], words[1:]))
    return rows
