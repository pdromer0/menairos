"""Tests de los esquemas JSON del contrato y de su módulo (T-05)."""

import re
import subprocess
import tomllib
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, validators

from menairos.schemas import (
    SCHEMA_NAMES,
    DuplicateKeyError,
    Issue,
    SchemaName,
    apply_defaults,
    check_decisions,
    is_marked,
    load_document,
    load_schema,
    validate,
)

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "tests" / "data" / "esquemas"

# Las reglas de las tablas de hito-0.md 2.2 (más «claves-desconocidas» y los casos
# límite que se recorren aquí). Cada una tiene al menos un caso válido y uno inválido.
REGLAS: dict[SchemaName, set[str]] = {
    "menairos": {
        "claves-desconocidas",
        "tablas-obligatorias",
        "menairos.version",
        "proyecto.nombre",
        "proyecto.repo",
        "proyecto.visibilidad",
        "proyecto.idiomas",
        "stack.plantillas",
        "modo.defecto",
        "modo.resumen_aprendizaje",
        "entornos.*",
        "modelos.*",
        "revisores.*",
        "enteros",
        "booleanos",
        "autonomia.rutas_protegidas",
        "guardarrailes.aviso_presupuesto_pct",
        "guardarrailes.ventana_horaria",
        "modulos.*",
    },
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
    "decisiones": {
        "claves-desconocidas",
        "tarea",
        "decisiones",
        "decisiones[].id",
        "decisiones[].decision",
        "decisiones[].motivo",
        "decisiones[].alternativas",
        "decisiones[].reversibilidad",
        "decisiones[].impacto",
        "decisiones[].decidido_por",
        "decisiones[].por_que_no_escalo",
        "decisiones[].agente",
        "decisiones[].revisor",
        "decisiones[].revision",
        "coherencia.id-de-la-tarea",
        "coherencia.id-repetido",
        "coherencia.matriz",
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


# Las palabras clave que siguen el recorrido estricto y apply_defaults (properties,
# items y $ref) y las que solo comprueba jsonschema. Una nueva (anyOf, oneOf,
# prefixItems, patternProperties…) obliga a revisar antes esos dos recorridos.
PALABRAS_CLAVE = {
    "$schema",
    "$id",
    "$defs",
    "$ref",
    "title",
    "description",
    "default",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "if",
    "then",
    "enum",
    "const",
    "pattern",
    "minimum",
    "maximum",
    "minItems",
    "uniqueItems",
    "contains",
}


# ── Los esquemas ───────────────────────────────────────────────────────────


def test_hay_reglas_para_cada_esquema() -> None:
    assert set(REGLAS) == set(SCHEMA_NAMES) == {"menairos", "tareas", "decisiones"}


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
def test_los_esquemas_solo_usan_palabras_clave_que_se_recorren(
    esquema: SchemaName,
) -> None:
    """Si falla, hay que enseñar la palabra clave nueva a _strict y a _fill."""
    usadas: set[str] = set()
    for subesquema in _subesquemas(load_schema(esquema)):
        usadas |= set(subesquema)
        if isinstance(subesquema.get("contains"), dict):
            usadas |= set(subesquema["contains"])
    assert usadas <= PALABRAS_CLAVE, usadas - PALABRAS_CLAVE


def test_el_id_de_tarea_es_el_mismo_en_tareas_y_en_decisiones() -> None:
    """El id de decisión es el de la tarea seguido de -Dn."""
    tareas = load_schema("tareas")["$defs"]["id_tarea"]
    decisiones = load_schema("decisiones")
    assert decisiones["$defs"]["id_tarea"] == tareas
    patron_decision = decisiones["$defs"]["decision"]["properties"]["id"]["pattern"]
    assert patron_decision == tareas["pattern"].removesuffix("$") + "-D[1-9][0-9]*$"


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
def test_cada_esquema_es_json_schema_2020_12_valido(esquema: SchemaName) -> None:
    """El esquema pasa su metaesquema, declara 2020-12 y tiene un $id con su nombre."""
    contenido = load_schema(esquema)
    assert contenido["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert contenido["$id"].endswith(f"/src/menairos/esquemas/{esquema}.schema.json")
    assert validators.validator_for(contenido) is Draft202012Validator
    Draft202012Validator.check_schema(contenido)


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
def test_todos_los_objetos_rechazan_claves_desconocidas(esquema: SchemaName) -> None:
    """Cada subesquema de tipo objeto lleva additionalProperties: false."""
    objetos = [
        s for s in _subesquemas(load_schema(esquema)) if s.get("type") == "object"
    ]
    assert objetos
    for objeto in objetos:
        assert objeto.get("additionalProperties") is False, objeto.get("description")


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
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


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
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


@pytest.mark.parametrize("esquema", SCHEMA_NAMES)
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


def _ejemplo_de_diseno() -> dict[str, Any]:
    """El bloque TOML de diseno.md 3.1, leído del propio documento."""
    diseno = (RAIZ / "docs" / "diseno.md").read_text(encoding="utf-8")
    seccion = diseno.split("### 3.1", 1)[1]
    bloque = re.search(r"```toml\n(.*?)```", seccion, re.DOTALL)
    assert bloque is not None, "diseno.md 3.1 no tiene un bloque toml"
    return tomllib.loads(bloque.group(1))


def test_valores_por_defecto_de_menairos_toml_son_los_de_diseno() -> None:
    """Las claves obligatorias del ejemplo, con sus defaults, dan el ejemplo entero."""
    ejemplo = _ejemplo_de_diseno()
    minimo = {
        "menairos": {"version": ejemplo["menairos"]["version"]},
        "proyecto": {
            "nombre": ejemplo["proyecto"]["nombre"],
            "repo": ejemplo["proyecto"]["repo"],
        },
        "stack": {"plantillas": ejemplo["stack"]["plantillas"]},
    }
    assert validate("menairos", minimo) == []
    assert apply_defaults("menairos", minimo) == ejemplo


def test_las_subtablas_que_faltan_se_crean_con_sus_valores() -> None:
    """Una tabla de modelo con solo una clave recibe la otra."""
    documento = load_document(DATOS / "menairos" / "validos" / "modelos-haiku.toml")
    modelos = apply_defaults("menairos", documento)["modelos"]
    assert modelos["plan"] == {"normal": "haiku", "critica": "opus"}
    assert modelos["implementacion"] == {"normal": "sonnet", "critica": "opus"}
    assert modelos["informe"] == "haiku"


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


def test_valores_por_defecto_de_una_decision() -> None:
    """revision es pendiente; por_que_no_escalo, agente y revisor no tienen."""
    documento = load_document(
        DATOS / "decisiones" / "validos" / "pedro-sin-por-que.yaml"
    )
    decision = apply_defaults("decisiones", documento)["decisiones"][0]
    assert decision == documento["decisiones"][0] | {"revision": "pendiente"}


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


def test_el_menairos_toml_del_repo_es_valido() -> None:
    assert validate("menairos", load_document(RAIZ / "menairos.toml")) == []


@pytest.mark.parametrize(
    "ruta",
    sorted((RAIZ / "docs" / "specs").glob("hito-*.tareas.yaml")),
    ids=lambda r: r.name,
)
def test_las_tareas_de_los_hitos_del_repo_son_validas(ruta: Path) -> None:
    assert validate("tareas", load_document(ruta)) == []


@pytest.mark.parametrize(
    "ruta",
    sorted((RAIZ / "docs" / "specs").glob("hito-*/decisiones/*.yaml")),
    ids=lambda r: f"{r.parent.parent.name}/{r.name}",
)
def test_los_ficheros_de_decisiones_del_repo_son_validos(ruta: Path) -> None:
    """Cumplen el esquema y las coherencias, y se llaman como su tarea."""
    documento = load_document(ruta)
    assert _problemas("decisiones", documento) == []
    assert ruta.stem == documento["tarea"]


# ── Marca y coherencias de las decisiones ───────────────────────────────────


@pytest.mark.parametrize(
    ("reversibilidad", "impacto", "marcada"),
    [
        ("reversible", "bajo", False),
        ("dificil", "bajo", True),
        ("reversible", "alto", True),
        ("dificil", "alto", True),
    ],
)
def test_la_marca_se_calcula_con_dificil_o_impacto_alto(
    reversibilidad: str, impacto: str, marcada: bool
) -> None:
    """La marca no se escribe: está marcada si es difícil o de impacto alto (2.2)."""
    assert is_marked({"reversibilidad": reversibilidad, "impacto": impacto}) is marcada


def test_dificil_alto_y_agente_es_un_error_porque_tenia_que_parar() -> None:
    """La matriz del punto 9: el agente tenía que haber parado."""
    ruta = DATOS / "decisiones" / "invalidos" / "dificil-alto-agente.yaml"
    documento = load_document(ruta)
    assert validate("decisiones", documento) == []
    [problema] = check_decisions(documento)
    assert problema.path == "decisiones[0].decidido_por"
    assert problema.keyword == "agent_should_have_stopped"
    assert "tenía que haber parado" in problema.message
    assert "punto 9" in problema.message


def test_un_id_repetido_es_un_error_en_su_segunda_aparicion() -> None:
    documento = load_document(DATOS / "decisiones" / "invalidos" / "id-repetido.yaml")
    assert check_decisions(documento) == [
        Issue(
            "decisiones[2].id",
            "duplicate_id",
            "el id «T-07-D1» está repetido: ya se usó en decisiones[0]",
        )
    ]


def test_un_id_de_otra_tarea_es_un_error() -> None:
    documento = load_document(
        DATOS / "decisiones" / "invalidos" / "id-de-otra-tarea.yaml"
    )
    assert check_decisions(documento) == [
        Issue(
            "decisiones[1].id",
            "task_mismatch",
            "el id «T-08-D2» no es de la tarea «T-07» del fichero: "
            "debe empezar por «T-07-D»",
        )
    ]


# ── Errores y mensajes ──────────────────────────────────────────────────────


def test_un_alias_que_se_contiene_a_si_mismo_es_un_error_y_no_un_fallo(
    tmp_path: Path,
) -> None:
    """2.3: un alias que crea un bucle es un error de esquema."""
    minimo = (DATOS / "tareas" / "validos" / "minimo.yaml").read_text(encoding="utf-8")
    ruta = tmp_path / "bucle.yaml"
    ruta.write_text(
        minimo.replace("titulo: Hito 1 — Ejemplo", "titulo: &t [*t]"), encoding="utf-8"
    )
    assert validate("tareas", load_document(ruta)) == [
        Issue(
            "titulo",
            "type",
            "debe ser un texto (valor: un valor que se contiene a sí mismo)",
        )
    ]


def test_un_alias_en_bucle_dentro_de_una_lista_es_un_error(tmp_path: Path) -> None:
    minimo = (DATOS / "tareas" / "validos" / "minimo.yaml").read_text(encoding="utf-8")
    ruta = tmp_path / "bucle.yaml"
    ruta.write_text(
        minimo.replace(
            "    rama: feat/h1-primera",
            "    rama: feat/h1-primera\n    depende_de: &d [*d, *d]",
        ),
        encoding="utf-8",
    )
    problemas = validate("tareas", load_document(ruta))
    assert {(p.path, p.keyword) for p in problemas} >= {
        ("tareas[0].depende_de[0]", "type"),
        ("tareas[0].depende_de[1]", "type"),
    }


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
        (
            "id-un-digito",
            '"T-1" no tiene el formato esperado (^T-(?:[0-9]{2}|[1-9][0-9]{2})$)',
        ),
        (
            "id-con-salto",
            '"T-01\\n" no tiene el formato esperado: acaba en salto de línea',
        ),
        ("tareas-vacia", "debe tener al menos un elemento"),
        ("depende-de-repetido", "tiene elementos repetidos"),
        ("hito-negativo", "debe ser como mínimo 0 (valor: -1)"),
        (
            "hito-fecha",
            "debe ser un entero (valor: 2026-01-01, una fecha u hora sin comillas)",
        ),
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
    ruta.write_bytes("\ufeffhito: 1\n".encode())
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


@pytest.mark.parametrize(
    ("caso", "mensaje"),
    [
        ("sin-base", 'debe incluir "base"'),
        ("pct-101", "debe ser como máximo 100 (valor: 101)"),
        ("plan-texto", 'debe ser una tabla (valor: "opus")'),
    ],
)
def test_los_mensajes_de_menairos_toml_estan_en_espanol(
    caso: str, mensaje: str
) -> None:
    ruta = DATOS / "menairos" / "invalidos" / f"{caso}.toml"
    assert [p.message for p in validate("menairos", load_document(ruta))] == [mensaje]


# ── Empaquetado ─────────────────────────────────────────────────────────────


@pytest.mark.slow
def test_los_esquemas_viajan_en_el_wheel(tmp_path: Path) -> None:
    """uv tool install solo instala el paquete: los esquemas tienen que ir dentro."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=RAIZ,
        check=True,
        capture_output=True,
    )
    [rueda] = tmp_path.glob("menairos-*.whl")
    with zipfile.ZipFile(rueda) as contenido:
        nombres = set(contenido.namelist())
    for esquema in REGLAS:
        assert f"menairos/esquemas/{esquema}.schema.json" in nombres
