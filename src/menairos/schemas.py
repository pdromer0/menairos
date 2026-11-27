"""JSON Schemas of the Menairos contract: load, validate and fill in defaults.

The three schemas (``menairos``, ``tareas`` and ``decisiones``) live in the
``esquemas/`` folder inside the package, so they travel with
``uv tool install``, and are read with :mod:`importlib.resources`.

Validation has three layers:

* the schema itself, checked with :class:`jsonschema.Draft202012Validator`;
* strict checks the schema cannot express portably (``1.0`` is not an integer,
  and an anchored pattern does not accept a trailing line break);
* for decision files, :func:`check_decisions` (coherence across fields).

Every problem is an :class:`Issue` whose ``message`` is in Spanish, because it
is shown to the user. Checks that look at keys the user wrote (such as the A01
warning of ``spec validar``) must run on the document *before*
:func:`apply_defaults`.
"""

import copy
import json
import re
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

type SchemaName = Literal["menairos", "tareas", "decisiones"]
type _Part = str | int
type _Found = tuple[tuple[_Part, ...], str, str]

SCHEMA_NAMES: tuple[SchemaName, ...] = ("menairos", "tareas", "decisiones")

_SCHEMA_DIR = files("menairos") / "esquemas"
_LOCAL_REF = "#/$defs/"
_NOT_BLANK = r"\S"
_TYPE_NAMES = {
    "string": "un texto",
    "integer": "un entero",
    "number": "un número",
    "boolean": "un booleano (true o false)",
    "array": "una lista",
    "object": "una tabla",
    "null": "null",
}


@dataclass(frozen=True)
class Issue:
    """A validation problem: where it is, which rule failed and why.

    ``path`` follows the format of ``spec validar`` (``tareas[3].depende_de[0]``);
    the root of the document is ``""``. ``keyword`` is the JSON Schema keyword
    or the name of the code check. ``message`` is in Spanish.
    """

    path: str
    keyword: str
    message: str


class DuplicateKeyError(yaml.YAMLError):
    """A YAML mapping repeats a key (PyYAML would silently keep the last one)."""


class _StrictSafeLoader(yaml.SafeLoader):
    """``yaml.SafeLoader`` that rejects repeated keys in a mapping.

    It keeps the safe constructors untouched. A key that overrides one brought
    in with ``<<`` (merge) is not a repetition.
    """

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[Any, Any]:
        seen: set[object] = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=deep)
            try:
                repeated = key in seen
            except TypeError:  # unhashable key: SafeLoader reports it below
                continue
            if repeated:
                line = key_node.start_mark.line + 1
                raise DuplicateKeyError(f"clave repetida «{key}» en la línea {line}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_schema(name: SchemaName) -> dict[str, Any]:
    """Return a fresh copy of the named schema."""
    text = (_SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8")
    return json.loads(text)


def load_document(path: Path) -> Any:
    """Read a ``.toml`` or ``.yaml``/``.yml`` document (UTF-8, BOM allowed).

    YAML is loaded safely and a repeated key raises :class:`DuplicateKeyError`;
    ``tomllib`` already rejects repeated keys in TOML.
    """
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".toml":
        return tomllib.loads(text)
    if path.suffix in (".yaml", ".yml"):
        return yaml.load(text, Loader=_StrictSafeLoader)
    raise ValueError(
        f"formato no admitido: «{path.suffix}» (se espera .toml, .yaml o .yml)"
    )


def validate(name: SchemaName, document: Any) -> list[Issue]:
    """Validate ``document`` against the schema and the strict checks.

    Returns the issues sorted by path (indexes compared as numbers); an empty
    list means the document is valid. Defaults are not applied.
    """
    schema = load_schema(name)
    found: list[_Found] = []
    for error in Draft202012Validator(schema).iter_errors(document):
        found.extend(_from_error(error))
    found.extend(_strict(document, schema, schema, ()))
    return _issues(found)


def apply_defaults(name: SchemaName, document: Any) -> Any:
    """Return a copy of ``document`` with the schema defaults filled in.

    Missing optional keys take their ``default``, nested tables included; keys
    already present are kept. The input is not modified. Meant for a valid
    document; with wrong types it skips the parts it cannot follow.
    """
    schema = load_schema(name)
    return _fill(copy.deepcopy(document), schema, schema)


def is_marked(decision: Mapping[str, Any]) -> bool:
    """A decision is marked if it is hard to revert or of high impact (point 9)."""
    return decision["reversibilidad"] == "dificil" or decision["impacto"] == "alto"


def check_decisions(document: Mapping[str, Any]) -> list[Issue]:
    """Check what the decisions schema cannot express.

    ``document`` must already be valid against the ``decisiones`` schema.
    Each id must belong to the file's task and appear only once, and a decision
    that is hard to revert and of high impact cannot have been taken by the
    agent: according to the point 9 matrix, the agent had to stop.
    """
    task: str = document["tarea"]
    first_seen: dict[str, int] = {}
    found: list[_Found] = []
    for index, decision in enumerate(document["decisiones"]):
        did: str = decision["id"]
        at_id = ("decisiones", index, "id")
        if did.rpartition("-D")[0] != task:
            message = (
                f"el id «{did}» no es de la tarea «{task}» del fichero: "
                f"debe empezar por «{task}-D»"
            )
            found.append((at_id, "task_mismatch", message))
        if did in first_seen:
            message = (
                f"el id «{did}» está repetido: ya se usó en "
                f"decisiones[{first_seen[did]}]"
            )
            found.append((at_id, "duplicate_id", message))
        else:
            first_seen[did] = index
        if (
            decision["reversibilidad"] == "dificil"
            and decision["impacto"] == "alto"
            and decision["decidido_por"] == "agente"
        ):
            message = (
                f"la decisión «{did}» es difícil de revertir y de impacto alto, "
                "y la tomó el agente: según la matriz del punto 9, el agente "
                "tenía que haber parado y pedírsela a Pedro"
            )
            found.append(
                (
                    ("decisiones", index, "decidido_por"),
                    "agent_should_have_stopped",
                    message,
                )
            )
    return _issues(found)


def format_path(parts: Sequence[_Part]) -> str:
    """Format a path as ``tareas[3].depende_de[0]`` (``""`` for the root)."""
    text = ""
    for part in parts:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else part
    return text


def _issues(found: list[_Found]) -> list[Issue]:
    """Deduplicate, sort by path and build the issues."""

    def key(item: _Found) -> tuple[list[tuple[int, int, str]], str, str]:
        parts, keyword, message = item
        sortable = [(0, p, "") if isinstance(p, int) else (1, 0, p) for p in parts]
        return sortable, keyword, message

    unique = sorted(set(found), key=key)
    return [
        Issue(format_path(parts), keyword, message)
        for parts, keyword, message in unique
    ]


def _from_error(error: ValidationError) -> Iterator[_Found]:
    """Translate a jsonschema error; ``required`` and extra keys point to the key."""
    parts = tuple(error.absolute_path)
    keyword = str(error.validator)
    instance: Any = error.instance
    expected: Any = error.validator_value
    if keyword == "required" and isinstance(instance, dict):
        for key in expected:
            if key not in instance:
                yield parts + (key,), keyword, f"falta la clave obligatoria «{key}»"
    elif keyword == "additionalProperties" and isinstance(instance, dict):
        schema = error.schema if isinstance(error.schema, Mapping) else {}
        allowed = schema.get("properties", {})
        for key in instance:
            if key not in allowed:
                yield parts + (str(key),), keyword, f"clave desconocida «{key}»"
    else:
        yield parts, keyword, _message(keyword, error)


def _message(keyword: str, error: ValidationError) -> str:
    """Spanish message for each keyword the schemas use."""
    value: Any = error.validator_value
    shown = _show(error.instance)
    match keyword:
        case "type":
            names = [value] if isinstance(value, str) else list(value)
            expected = " o ".join(_TYPE_NAMES.get(n, n) for n in names)
            return f"debe ser {expected} (valor: {shown})"
        case "enum":
            options = ", ".join(_show(option) for option in value)
            return f"valor {shown} no admitido; se admite: {options}"
        case "pattern" if value == _NOT_BLANK:
            return "está vacío o solo tiene espacios"
        case "pattern":
            return f"{shown} no tiene el formato esperado ({value})"
        case "minItems" if value == 1:
            return "debe tener al menos un elemento"
        case "minItems":
            return f"debe tener al menos {value} elementos"
        case "uniqueItems":
            return "tiene elementos repetidos"
        case "contains":
            return f"debe incluir {_show(value.get('const'))}"
        case "minimum":
            return f"debe ser como mínimo {value} (valor: {shown})"
        case "maximum":
            return f"debe ser como máximo {value} (valor: {shown})"
        case _:
            return error.message


def _show(value: object) -> str:
    """Show a value as it would be written in JSON."""
    return json.dumps(value, ensure_ascii=False, default=str)


def _resolve(schema: Mapping[str, Any], root: Mapping[str, Any]) -> dict[str, Any]:
    """Follow a local ``$ref`` (``#/$defs/…``), keeping its sibling keywords."""
    ref = schema.get("$ref")
    if ref is None:
        return dict(schema)
    if not isinstance(ref, str) or not ref.startswith(_LOCAL_REF):
        raise ValueError(
            f"solo se admiten referencias locales «{_LOCAL_REF}…»: {ref!r}"
        )
    target = _resolve(root["$defs"][ref.removeprefix(_LOCAL_REF)], root)
    siblings = {k: v for k, v in schema.items() if k != "$ref"}
    return target | siblings


def _children(
    value: object, schema: Mapping[str, Any]
) -> Iterator[tuple[_Part, object, Mapping[str, Any]]]:
    """Yield (key, value, subschema) for the parts of ``value`` the schema describes.

    The subschema is returned as written: the caller follows its ``$ref``.
    """
    if isinstance(value, dict):
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                yield key, value[key], sub
    elif isinstance(value, list) and isinstance(schema.get("items"), Mapping):
        for index, item in enumerate(value):
            yield index, item, schema["items"]


def _strict(
    value: object,
    schema: Mapping[str, Any],
    root: Mapping[str, Any],
    parts: tuple[_Part, ...],
) -> Iterator[_Found]:
    """Strict checks after the schema: no ``1.0`` integers, no trailing line break."""
    schema = _resolve(schema, root)
    if (
        schema.get("type") == "integer"
        and isinstance(value, float)
        and value.is_integer()
    ):
        yield (
            parts,
            "type",
            f"debe ser un entero, no un decimal (valor: {_show(value)})",
        )
    pattern = schema.get("pattern")
    if (
        isinstance(value, str)
        and isinstance(pattern, str)
        and pattern.startswith("^")
        and pattern.endswith("$")
        and "\n" in value
        and re.search(pattern, value)
    ):
        # Python's `$` also matches before a final "\n", which the schema
        # (ECMA-262) would reject: report it as the same pattern error.
        yield (
            parts,
            "pattern",
            f"{_show(value)} no tiene el formato esperado: acaba en salto de línea",
        )
    for key, child, child_schema in _children(value, schema):
        yield from _strict(child, child_schema, root, (*parts, key))


def _fill(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any]) -> Any:
    """Fill in defaults in place (``value`` is already a private copy)."""
    schema = _resolve(schema, root)
    if isinstance(value, dict):
        for key, sub in schema.get("properties", {}).items():
            sub = _resolve(sub, root)
            if key not in value and "default" in sub:
                value[key] = copy.deepcopy(sub["default"])
    for key, child, child_schema in _children(value, schema):
        value[key] = _fill(child, child_schema, root)
    return value
