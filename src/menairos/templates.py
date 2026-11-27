"""Document templates (hito-0.md 3.2) and their ``{{clave}}`` substitution.

The templates live in ``plantillas/docs/`` inside the package, so they travel
with ``uv tool install``, and are read with :mod:`importlib.resources`.

Substitution has no logic and no dependencies:

* a hole is ``{{clave}}``: lower-case ASCII words (letters, digits and ``_``,
  starting with a letter) joined by dots, with no spaces inside the braces;
* the values come from ``menairos.toml`` (validated, with its defaults applied
  and flattened to dotted keys such as ``proyecto.nombre``) and from the few
  keys the caller passes (:data:`CALLER_KEYS`);
* a value is a non-blank text without line breaks or control characters, or
  an integer (not a boolean); a table or a list is an error;
* a hole that is badly written, whose key does not exist or that the caller
  did not fill is an error; every problem of a template is reported at once;
* ``\\{{`` writes a literal ``{{`` (as in Handlebars). The backslash has no
  escape of its own: a backslash right before a hole cannot be written;
* the text is scanned once, so a value that contains ``{{…}}`` stays as is;
* in a YAML template a text only goes in a hole the template writes between
  double quotes (``"{{clave}}"``), and is escaped as inside them (its JSON
  without the quotes); anywhere else, only an integer.

Messages are in Spanish, because they are shown to the user.
"""

import json
import re
import unicodedata
from collections.abc import Mapping
from importlib.resources import files
from typing import Any

from menairos.schemas import apply_defaults, validate

DOC_TEMPLATES: tuple[str, ...] = (
    "producto.md",
    "diseno.md",
    "hitos.md",
    "hito-N.md",
    "hito-N.tareas.yaml",
    "abiertas.md",
    "adr.md",
    "decisiones-tarea.yaml",
    "anexo-tarea.md",
    "revision-hito-N.md",
    "inventario-mvp.md",
    "pull_request_template.md",
    "ISSUE_TEMPLATE/tarea.md",
    "ISSUE_TEMPLATE/bug.md",
    "ISSUE_TEMPLATE/idea.md",
    "ISSUE_TEMPLATE/config.yml",
)
"""Every document template, by its path inside ``plantillas/docs/``."""

CALLER_KEYS: frozenset[str] = frozenset(
    {
        "hito.numero",
        "hito.titulo",
        "fecha",
        "tarea.id",
        "tarea.titulo",
        "adr.numero",
        "adr.titulo",
        "adr.tipo",
    }
)
"""The keys that do not come from ``menairos.toml``: the caller passes them."""

_DOCS_DIR = files("menairos") / "plantillas" / "docs"
_KEY = r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*"
_HOLE = re.compile(rf"\{{\{{({_KEY})\}}\}}")
_NOT_BLANK = re.compile(r"[^\s\uFEFF]")  # the rule of schemas._NOT_BLANK
_NONCHARACTERS = (chr(0xFFFE), chr(0xFFFF))
_KINDS = {dict: "una tabla", list: "una lista", bool: "un booleano"}


class TemplateError(ValueError):
    """A template cannot be read or filled; ``problems`` has one line each."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("\n".join(problems))


def read(name: str) -> str:
    """The text of the template ``name``, one of :data:`DOC_TEMPLATES`."""
    if name not in DOC_TEMPLATES:
        listed = ", ".join(DOC_TEMPLATES)
        raise TemplateError(
            [f"no existe la plantilla «{name}»; las plantillas son: {listed}"]
        )
    return _DOCS_DIR.joinpath(*name.split("/")).read_text(encoding="utf-8")


def values(
    config: Mapping[str, Any], extra: Mapping[str, object] | None = None
) -> dict[str, object]:
    """The values for the templates: ``menairos.toml`` and the caller's keys.

    ``config`` is the document as read (it is validated and gets its
    defaults here). Its tables are flattened to dotted keys; the tables and
    lists themselves are kept too, so using one gives a clear error. Every key
    of ``extra`` must be one of :data:`CALLER_KEYS`; its value is checked
    when a template uses it.
    """
    issues = validate("menairos", config)
    if issues:
        raise TemplateError(
            [
                f"menairos.toml no es válido: {i.path or 'la raíz'}: {i.message}"
                for i in issues
            ]
        )
    flat: dict[str, object] = {}
    _flatten(apply_defaults("menairos", config), "", flat)
    problems: list[str] = []
    for key, value in (extra or {}).items():
        if key in CALLER_KEYS:
            flat[key] = value
        else:
            problems.append(
                f"«{key}» no es una clave que pueda pasar quien llama; se admiten: "
                + ", ".join(sorted(CALLER_KEYS))
            )
    if problems:
        raise TemplateError(problems)
    return flat


def fill(
    text: str, values: Mapping[str, object], *, yaml: bool = False, name: str = ""
) -> str:
    """``text`` with every ``{{clave}}`` replaced by its value, in one pass.

    With ``yaml``, a text only goes in a hole written between double quotes
    (``"{{clave}}"``) and is escaped as inside them; anywhere else, only an
    integer. ``name`` is the template's, for the messages. Raises
    :class:`TemplateError` with every problem found.
    """
    where = f"«{name}», " if name else ""
    out: list[str] = []
    problems: list[str] = []
    start = 0
    line = 1
    while (at := text.find("{{", start)) != -1:
        line += text.count("\n", start, at)
        if at > 0 and text[at - 1] == "\\":
            out += [text[start : at - 1], "{{"]
            start = at + 2
            continue
        out.append(text[start:at])
        hole = _HOLE.match(text, at)
        if hole is None:
            shown = text[at:].split("\n", 1)[0][:40]
            problems.append(
                f"{where}línea {line}: hueco mal escrito «{shown}»: se escribe "
                "{{clave}}, sin espacios, con minúsculas, cifras, _ y puntos "
                "(un {{ literal se escribe \\{{)"
            )
            out.append("{{")
            start = at + 2
            continue
        start = hole.end()
        quoted = text[at - 1 : at] == '"' and text[start : start + 1] == '"'
        try:
            out.append(_shown(hole[1], values, yaml=yaml, quoted=quoted))
        except _BadValue as error:
            problems.append(f"{where}línea {line}: {error}")
    out.append(text[start:])
    if problems:
        raise TemplateError(problems)
    return "".join(out)


def render(name: str, values: Mapping[str, object]) -> str:
    """The template ``name`` filled with ``values`` (see :func:`values`)."""
    return fill(read(name), values, yaml=name.endswith((".yaml", ".yml")), name=name)


class _BadValue(Exception):
    """Why a hole cannot be filled; the message is in Spanish."""


def _shown(key: str, values: Mapping[str, object], *, yaml: bool, quoted: bool) -> str:
    """The value of ``key`` as written in the template."""
    if key not in values:
        if key in CALLER_KEYS:
            raise _BadValue(
                f"hueco sin rellenar: «{key}» lo tiene que pasar quien llama"
            )
        raise _BadValue(
            f"la clave «{key}» no existe: no es de menairos.toml ni de las que pasa "
            "quien llama"
        )
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, str | int):
        kind = _KINDS.get(type(value), f"de tipo {type(value).__name__}")
        raise _BadValue(f"«{key}» no es un texto ni un entero: es {kind}")
    if isinstance(value, int):
        return str(value)
    shown = json.dumps(value, ensure_ascii=False)
    if not _NOT_BLANK.search(value):
        raise _BadValue(f"«{key}» está vacío o solo tiene espacios")
    if value.splitlines() != [value]:
        raise _BadValue(f"«{key}» tiene saltos de línea: {shown}")
    if any(_is_control(char) for char in value):
        raise _BadValue(f"«{key}» tiene caracteres de control: {ascii(value)}")
    if yaml and not quoted:
        raise _BadValue(
            f"«{key}» es un texto y en una plantilla YAML un texto solo va en un "
            'hueco entre comillas dobles ("{{clave}}")'
        )
    return shown[1:-1] if yaml else value


def _is_control(char: str) -> bool:
    """Control characters, lone surrogates and the two last noncharacters.

    YAML rejects them even escaped as JSON leaves them; they have no place in
    a document either. The tab is a control character too.
    """
    return unicodedata.category(char) in ("Cc", "Cs") or char in _NONCHARACTERS


def _flatten(value: object, prefix: str, out: dict[str, object]) -> None:
    """Dotted keys of a table: ``{"a": {"b": 1}}`` gives ``a`` and ``a.b``."""
    if prefix:
        out[prefix] = value
    if isinstance(value, dict):
        for key, child in value.items():
            _flatten(child, f"{prefix}.{key}" if prefix else str(key), out)
