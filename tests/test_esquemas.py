"""Tests de los esquemas JSON del contrato y de su módulo (T-05)."""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, validators

from menairos.schemas import (
    DuplicateKeyError,
    Issue,
    SchemaName,
    apply_defaults,
    check_decisions,
    load_document,
    load_schema,
    validate,
)

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "tests" / "data" / "esquemas"

# Las reglas de las tablas de hito-0.md 2.2 (más «claves-desconocidas» y los casos
# límite que se recorren aquí). Cada una tiene al menos un caso válido y uno inválido.
REGLAS: dict[SchemaName, set[str]] = {
    "tareas": {
        "claves-desconocidas",
        "hito",
        "titulo",
        "tareas",
        "tareas[].id",
        "tareas[].titulo",
        "tareas[].rama",
        "tareas[].depende_de",
        "tareas[].area",
        "tareas[].critica",
        "tareas[].motivo_critica",
        "tareas[].donde",
        "tareas[].quien",
        "tareas[].modo",
        "tareas[].especificacion",
        "tareas[].criterios_aceptacion",
        "ultimo-elemento",
    },
}

# Claves opcionales sin valor por defecto (decisión de Pedro, P2).
SIN_DEFAULT: set[tuple[SchemaName, str]] = {
    ("tareas", "motivo_critica"),
    ("decisiones", "por_que_no_escalo"),
    ("decisiones", "agente"),
    ("decisiones", "revisor"),
}

EXTENSION: dict[SchemaName, str] = {
    "menairos": "toml",
    "tareas": "yaml",
    "decisiones": "yaml",
}


def _cabecera(ruta: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Lee las líneas «# regla: …» y «# error: <ruta> <palabra_clave>» de un caso."""
    reglas: list[str] = []
    errores: list[tuple[str, str]] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.startswith("#"):
            break
        if encontrada := re.fullmatch(r"# regla: (\S+)", linea):
            reglas.append(encontrada.group(1))
        elif encontrada := re.fullmatch(r"# error: (\S+) (\S+)", linea):
            errores.append((encontrada.group(1), encontrada.group(2)))
    return reglas, errores


def _problemas(esquema: SchemaName, documento: Any) -> list[Issue]:
    """Esquema y comprobaciones estrictas; en decisiones, también las coherencias."""
    problemas = validate(esquema, documento)
    if esquema == "decisiones" and not problemas:
        problemas = check_decisions(documento)
    return problemas


def _casos() -> Iterator[Any]:
    for esquema in REGLAS:
        for tipo in ("validos", "invalidos"):
            for ruta in sorted((DATOS / esquema / tipo).iterdir()):
                yield pytest.param(esquema, ruta, id=f"{esquema}/{tipo}/{ruta.stem}")


def _minimo(esquema: SchemaName) -> Any:
    return load_document(DATOS / esquema / "validos" / f"minimo.{EXTENSION[esquema]}")


def _subesquemas(esquema: Any) -> Iterator[dict[str, Any]]:
    """Los subesquemas que describen datos: properties, items, $defs, if y then."""
    if not isinstance(esquema, dict):
        return
    yield esquema
    for hijo in esquema.get("properties", {}).values():
        yield from _subesquemas(hijo)
    for hijo in esquema.get("$defs", {}).values():
        yield from _subesquemas(hijo)
    for clave in ("items", "if", "then"):
        yield from _subesquemas(esquema.get(clave))


# ── Los esquemas ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("esquema", list(REGLAS))
def test_cada_esquema_es_json_schema_2020_12_valido(esquema: SchemaName) -> None:
    """El esquema pasa su metaesquema, declara 2020-12 y tiene un $id con su nombre."""
    contenido = load_schema(esquema)
    assert contenido["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert contenido["$id"].endswith(f"/src/menairos/esquemas/{esquema}.schema.json")
    assert validators.validator_for(contenido) is Draft202012Validator
    Draft202012Validator.check_schema(contenido)


@pytest.mark.parametrize("esquema", list(REGLAS))
def test_todos_los_objetos_rechazan_claves_desconocidas(esquema: SchemaName) -> None:
    """Cada subesquema de tipo objeto lleva additionalProperties: false."""
    objetos = [
        s for s in _subesquemas(load_schema(esquema)) if s.get("type") == "object"
    ]
    assert objetos
    for objeto in objetos:
        assert objeto.get("additionalProperties") is False, objeto.get("description")


@pytest.mark.parametrize("esquema", list(REGLAS))
def test_cada_clave_opcional_tiene_valor_por_defecto(esquema: SchemaName) -> None:
    """Las claves no obligatorias llevan default, salvo las de SIN_DEFAULT."""
    for objeto in _subesquemas(load_schema(esquema)):
        if objeto.get("type") != "object":
            continue
        obligatorias = set(objeto.get("required", []))
        for clave, propiedad in objeto["properties"].items():
            if clave in obligatorias:
                assert "default" not in propiedad, clave
            elif (esquema, clave) in SIN_DEFAULT:
                assert "default" not in propiedad, clave
            else:
                assert "default" in propiedad, clave


@pytest.mark.parametrize("esquema", list(REGLAS))
def test_el_minimo_con_valores_por_defecto_sigue_siendo_valido(
    esquema: SchemaName,
) -> None:
    """Los defaults cumplen su propio esquema."""
    assert validate(esquema, apply_defaults(esquema, _minimo(esquema))) == []


# ── Casos por regla ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(("esquema", "ruta"), list(_casos()))
def test_cada_caso_da_exactamente_los_errores_declarados(
    esquema: SchemaName, ruta: Path
) -> None:
    """Un válido no da errores; un inválido da justo los de su cabecera."""
    reglas, esperados = _cabecera(ruta)
    assert reglas, "al caso le falta la línea «# regla: …»"
    assert bool(esperados) == (ruta.parent.name == "invalidos")
    problemas = _problemas(esquema, load_document(ruta))
    assert sorted((p.path, p.keyword) for p in problemas) == sorted(esperados), (
        problemas
    )
    assert all(p.message for p in problemas)


@pytest.mark.parametrize("esquema", list(REGLAS))
def test_cada_regla_tiene_un_caso_valido_y_uno_invalido(esquema: SchemaName) -> None:
    """Los válidos y los inválidos cubren exactamente las reglas de REGLAS."""
    for tipo in ("validos", "invalidos"):
        cubiertas = {
            regla
            for ruta in (DATOS / esquema / tipo).iterdir()
            for regla in _cabecera(ruta)[0]
        }
        assert cubiertas == REGLAS[esquema], tipo


# ── Valores por defecto ─────────────────────────────────────────────────────


def test_valores_por_defecto_de_una_tarea() -> None:
    """Los de la tabla de hito-0.md 2.2; motivo_critica no tiene."""
    escrita = _minimo("tareas")["tareas"][0]
    tarea = apply_defaults("tareas", _minimo("tareas"))["tareas"][0]
    assert {clave: valor for clave, valor in tarea.items() if clave not in escrita} == {
        "depende_de": [],
        "area": "general",
        "critica": False,
        "donde": "cualquiera",
        "quien": "claude",
        "modo": None,
    }


def test_aplicar_valores_por_defecto_no_cambia_la_entrada() -> None:
    documento = _minimo("tareas")
    copia = load_document(DATOS / "tareas" / "validos" / "minimo.yaml")
    apply_defaults("tareas", documento)
    assert documento == copia


def test_los_valores_por_defecto_mutables_no_se_comparten() -> None:
    """Dos tareas sin depende_de reciben listas distintas."""
    tareas = apply_defaults(
        "tareas", load_document(DATOS / "tareas" / "validos" / "varias-tareas.yaml")
    )
    primera, segunda = (
        tareas["tareas"][0]["depende_de"],
        tareas["tareas"][1]["depende_de"],
    )
    assert primera == segunda == []
    assert primera is not segunda


def test_un_valor_explicito_no_se_sustituye() -> None:
    documento = load_document(DATOS / "tareas" / "validos" / "modo-didactico.yaml")
    assert apply_defaults("tareas", documento)["tareas"][0]["modo"] == "didactico"


# ── Ficheros del repo ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ruta",
    sorted((RAIZ / "docs" / "specs").glob("hito-*.tareas.yaml")),
    ids=lambda r: r.name,
)
def test_las_tareas_de_los_hitos_del_repo_son_validas(ruta: Path) -> None:
    assert validate("tareas", load_document(ruta)) == []


# ── Errores y mensajes ──────────────────────────────────────────────────────


def test_un_documento_vacio_da_un_error_en_la_raiz() -> None:
    assert validate("tareas", None) == [
        Issue("", "type", "debe ser una tabla (valor: null)")
    ]


@pytest.mark.parametrize(
    ("caso", "mensaje"),
    [
        ("sin-hito", "falta la clave obligatoria «hito»"),
        ("clave-tarea", "clave desconocida «dependencias»"),
        ("hito-texto", 'debe ser un entero (valor: "1")'),
        ("hito-decimal", "debe ser un entero, no un decimal (valor: 1.0)"),
        ("donde-nube", 'valor "nube" no admitido; se admite: "cualquiera", "local"'),
        ("titulo-solo-espacios", "está vacío o solo tiene espacios"),
        ("id-un-digito", '"T-1" no tiene el formato esperado (^T-[0-9]{2,3}$)'),
        (
            "id-con-salto",
            '"T-01\\n" no tiene el formato esperado: acaba en salto de línea',
        ),
        ("tareas-vacia", "debe tener al menos un elemento"),
        ("depende-de-repetido", "tiene elementos repetidos"),
        ("hito-negativo", "debe ser como mínimo 0 (valor: -1)"),
    ],
)
def test_los_mensajes_estan_en_espanol(caso: str, mensaje: str) -> None:
    problemas = validate(
        "tareas", load_document(DATOS / "tareas" / "invalidos" / f"{caso}.yaml")
    )
    assert [p.message for p in problemas] == [mensaje]


# ── Lectura de documentos ───────────────────────────────────────────────────


def test_una_clave_repetida_en_yaml_es_un_error_con_su_linea(tmp_path: Path) -> None:
    """safe_load se quedaría en silencio con el último valor."""
    ruta = tmp_path / "repetida.yaml"
    ruta.write_text(
        "hito: 1\ntareas:\n  - id: T-01\n    area: a\n    area: b\n", encoding="utf-8"
    )
    with pytest.raises(DuplicateKeyError, match="clave repetida «area» en la línea 5"):
        load_document(ruta)


def test_una_clave_que_pisa_una_fusion_no_es_repetida(tmp_path: Path) -> None:
    """Los alias se aceptan (2.3): pisar una clave de << no es repetirla."""
    ruta = tmp_path / "fusion.yaml"
    ruta.write_text(
        "base: &b {x: 1, y: 2}\nhija:\n  <<: *b\n  y: 3\n", encoding="utf-8"
    )
    assert load_document(ruta)["hija"] == {"x": 1, "y": 3}


def test_yaml_no_construye_objetos_de_python(tmp_path: Path) -> None:
    """La carga es segura: una etiqueta de Python es un error."""
    ruta = tmp_path / "python.yaml"
    ruta.write_text("a: !!python/tuple [1, 2]\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError, match="python/tuple"):
        load_document(ruta)


def test_un_fichero_con_bom_se_lee(tmp_path: Path) -> None:
    ruta = tmp_path / "bom.yaml"
    ruta.write_bytes("﻿hito: 1\n".encode())
    assert load_document(ruta) == {"hito": 1}


def test_una_clave_repetida_en_toml_es_un_error(tmp_path: Path) -> None:
    """tomllib ya la rechaza."""
    ruta = tmp_path / "repetida.toml"
    ruta.write_text("a = 1\na = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Cannot overwrite a value"):
        load_document(ruta)


def test_un_formato_desconocido_es_un_error(tmp_path: Path) -> None:
    ruta = tmp_path / "datos.json"
    ruta.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="formato no admitido"):
        load_document(ruta)
