"""Tests de las plantillas de documentos y de la sustitución {{clave}} (T-09).

Los datos son sintéticos: un menairos.toml de ejemplo y las claves que pasaría
quien llama. Las plantillas se rellenan y se escriben en tmp_path; nada se
escribe en el repo.
"""

import re
import subprocess
import tomllib
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from menairos import markdown
from menairos.schemas import (
    apply_defaults,
    check_decisions,
    load_document,
    load_schema,
    validate,
)
from menairos.spec_validation import DATA_CHECKS, validate_spec
from menairos.task_issues import render as render_issue
from menairos.templates import (
    CALLER_KEYS,
    DOC_TEMPLATES,
    TemplateError,
    fill,
    read,
    render,
    values,
)

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "src" / "menairos" / "plantillas" / "docs"

TOML = """\
[menairos]
version = "1.0.0"

[proyecto]
nombre = "proyecto-ejemplo"
repo = "ejemplo/proyecto-ejemplo"

[stack]
plantillas = ["base", "python-uv"]
"""
CONFIG: dict[str, Any] = tomllib.loads(TOML)


def _llamada(hito: int = 1) -> dict[str, object]:
    return {
        "hito.numero": hito,
        "hito.titulo": "Primer hito",
        "fecha": "2026-01-15",
        "tarea.id": "T-01",
        "tarea.titulo": "Primera tarea",
        "adr.numero": "0001",
        "adr.titulo": "Stack del proyecto",
        "adr.tipo": "stack",
    }


def _valores(**cambios: object) -> dict[str, object]:
    llamada = _llamada()
    llamada.update({k.replace("__", "."): v for k, v in cambios.items()})
    return values(CONFIG, llamada)


def _error(texto: str, valores: dict[str, object] | None = None, **opciones: Any):
    with pytest.raises(TemplateError) as error:
        fill(texto, _valores() if valores is None else valores, **opciones)
    return list(error.value.problems)


# ── Las plantillas que hay ──────────────────────────────────────────────────


def test_la_lista_de_plantillas_es_la_de_la_carpeta() -> None:
    en_disco = {
        p.relative_to(CARPETA).as_posix() for p in CARPETA.rglob("*") if p.is_file()
    }
    assert en_disco == set(DOC_TEMPLATES)
    assert len(DOC_TEMPLATES) == len(set(DOC_TEMPLATES))


@pytest.mark.parametrize("nombre", ["no-existe.md", "../esquemas/tareas.schema.json"])
def test_una_plantilla_fuera_de_la_lista_es_un_error(nombre: str) -> None:
    with pytest.raises(TemplateError, match="no existe la plantilla"):
        read(nombre)


@pytest.mark.parametrize("nombre", DOC_TEMPLATES)
def test_cada_plantilla_se_rellena_con_las_claves_de_quien_llama(nombre: str) -> None:
    texto = render(nombre, _valores())
    assert "{{" not in texto
    if nombre.endswith((".yaml", ".yml")):
        assert isinstance(yaml.safe_load(texto), dict)


@pytest.mark.parametrize(
    "nombre",
    [
        "pull_request_template.md",
        "ISSUE_TEMPLATE/tarea.md",
        "ISSUE_TEMPLATE/bug.md",
        "ISSUE_TEMPLATE/idea.md",
        "ISSUE_TEMPLATE/config.yml",
    ],
)
def test_las_plantillas_de_github_son_las_del_repo(nombre: str) -> None:
    assert (CARPETA / nombre).read_bytes() == (RAIZ / ".github" / nombre).read_bytes()


@pytest.mark.slow
def test_las_plantillas_viajan_en_el_wheel(tmp_path: Path) -> None:
    """uv tool install solo instala el paquete: las plantillas tienen que ir dentro."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=RAIZ,
        check=True,
        capture_output=True,
    )
    [rueda] = tmp_path.glob("menairos-*.whl")
    with zipfile.ZipFile(rueda) as contenido:
        nombres = set(contenido.namelist())
    for nombre in DOC_TEMPLATES:
        assert f"menairos/plantillas/docs/{nombre}" in nombres


# ── Secciones fijas de hito-0.md 3.2 ────────────────────────────────────────

SECCIONES: dict[str, list[str]] = {
    "producto.md": [
        "## Visión",
        "## Problema",
        "## Usuarios",
        "## Casos de uso",
        "## Alcance",
        "## Restricciones",
        "## Criterios de éxito",
    ],
    "diseno.md": [
        "## Arquitectura",
        "## Componentes",
        "## Datos",
        "## Stack",
        "## Entornos",
        "## Coste",
        "## Riesgos",
    ],
    "hitos.md": [
        "## Vista general",
        "## Hito 1 — Primer hito",
        "### Objetivo",
        "### Contenido",
        "### Criterios de salida",
        "### Demo funcional",
    ],
    "hito-N.md": [
        "# Hito 1 — Primer hito",
        "## Objetivo",
        "## Bloque de trabajo",
        "## Validación funcional",
        "## Anexo",
    ],
    "abiertas.md": ["# proyecto-ejemplo — preguntas abiertas y supuestos"],
    "adr.md": [
        "# ADR 0001 — Stack del proyecto",
        "- **Estado:** ",
        "- **Fecha:** ",
        "- **Tipo:** ",
        "- **Decidido por:** ",
        "- **Reversibilidad:** ",
        "## Contexto",
        "## Decisión",
        "## Alternativas consideradas",
        "## Consecuencias",
    ],
    "anexo-tarea.md": [
        "### T-01 — Primera tarea",
        "**Qué se hizo**",
        "**Decisiones del diff**",
        "**Medidas**",
        "**Versiones incorrectas**",
        "**Revisión**",
        "**Pendiente**",
    ],
    "revision-hito-N.md": [
        "# Revisión del hito 1 — Primer hito",
        "## Bloqueantes",
        "## Mejoras",
        "## Preguntas para Pedro",
        "## Predicción de paradas",
    ],
    "inventario-mvp.md": [
        "## Estructura",
        "## Stack detectado",
        "## Funcionalidades",
        "## Datos",
        "## Calidad",
        "## Riesgos",
    ],
    "pull_request_template.md": [
        "## Resumen",
        "## Closes #N",
        "## Decisiones",
        "## Comprobaciones",
        "## Revisión propia",
        "## Pendiente",
        "## Métricas",
    ],
    "ISSUE_TEMPLATE/tarea.md": [
        "## Especificación",
        "## Criterios de aceptación",
        "## Datos",
    ],
    "ISSUE_TEMPLATE/bug.md": [
        "## Qué pasa",
        "## Qué debería pasar",
        "## Pasos para reproducirlo",
        "## Entorno",
        "## Salida o registro",
    ],
    "ISSUE_TEMPLATE/idea.md": ["## Idea", "## Motivación", "## Alternativas"],
}


def _es_seccion(linea: str, seccion: str) -> bool:
    """Un encabezado o una negrita es toda la línea; un metadato, su inicio."""
    return linea.startswith(seccion) if seccion.startswith("- ") else linea == seccion


def _lineas(nombre: str) -> list[str]:
    documento = markdown.parse(render(nombre, _valores()))
    return [linea.text for linea in documento.lines if not linea.in_code]


@pytest.mark.parametrize(
    ("nombre", "seccion"),
    [(nombre, seccion) for nombre, lista in SECCIONES.items() for seccion in lista],
)
def test_cada_seccion_fija_esta_en_su_plantilla(nombre: str, seccion: str) -> None:
    assert any(_es_seccion(linea, seccion) for linea in _lineas(nombre))


@pytest.mark.parametrize("nombre", SECCIONES)
def test_las_secciones_van_en_orden_y_no_hay_otros_encabezados(nombre: str) -> None:
    esperadas = SECCIONES[nombre]
    halladas = [
        seccion
        for linea in _lineas(nombre)
        for seccion in esperadas
        if _es_seccion(linea, seccion)
    ]
    assert halladas == esperadas
    documento = markdown.parse(render(nombre, _valores()))
    encabezados = {f"{'#' * h.level} {h.text}" for h in documento.headings}
    declarados = {s for s in esperadas if s.startswith("#")}
    # El título (#) solo se comprueba en las plantillas que lo declaran.
    assert {e for e in encabezados if not e.startswith("# ")} == {
        d for d in declarados if not d.startswith("# ")
    }


def test_las_plantillas_yaml_tienen_las_claves_del_esquema() -> None:
    tareas = yaml.safe_load(render("hito-N.tareas.yaml", _valores()))
    assert tareas == {"hito": 1, "titulo": "Primer hito", "tareas": []}
    decisiones = yaml.safe_load(render("decisiones-tarea.yaml", _valores()))
    assert decisiones == {"tarea": "T-01", "decisiones": []}
    assert validate("decisiones", decisiones) == []
    assert check_decisions(decisiones) == []


def test_abiertas_no_trae_ningun_punto() -> None:
    documento = markdown.parse(render("abiertas.md", _valores()))
    assert [h for h in documento.headings if h.level == 3] == []


def test_el_anexo_recuerda_el_tope_de_80_lineas() -> None:
    assert "80 líneas" in read("anexo-tarea.md")


# ── La plantilla de issue «Tarea» y el cuerpo de spec publicar ──────────────

_ETIQUETA = re.compile(r"- \*\*([^*]+):\*\*")


def _cuerpo_de_ejemplo() -> str:
    tarea = apply_defaults(
        "tareas",
        {
            "hito": 0,
            "titulo": "Hito",
            "tareas": [
                {
                    "id": "T-01",
                    "titulo": "Tarea",
                    "rama": "feat/tarea",
                    "especificacion": ["hito-0.md#objetivo"],
                    "criterios_aceptacion": ["Un criterio"],
                }
            ],
        },
    )["tareas"][0]
    issue = render_issue(
        tarea, milestone=0, repo="ejemplo/proyecto", tasks_file="docs/specs/x.yaml"
    )
    return issue.content


def test_la_plantilla_tarea_tiene_las_secciones_del_cuerpo_generado() -> None:
    generado = markdown.parse(_cuerpo_de_ejemplo())
    plantilla = markdown.parse(read("ISSUE_TEMPLATE/tarea.md"))
    assert [h.text for h in plantilla.headings] == [h.text for h in generado.headings]

    def etiquetas(documento: markdown.Document) -> list[str]:
        return [m[1] for linea in documento.lines if (m := _ETIQUETA.match(linea.text))]

    assert etiquetas(plantilla) == etiquetas(generado)
    primera = next(
        linea.text for linea in plantilla.lines if linea.text.startswith("Tarea **")
    )
    assert primera.startswith(generado.lines[0].text.split("**")[0] + "**")
    assert "menairos:tarea=" not in read("ISSUE_TEMPLATE/tarea.md")


# ── Sustitución ─────────────────────────────────────────────────────────────


def test_rellena_desde_menairos_toml_con_sus_valores_por_defecto() -> None:
    valores = _valores()
    texto = "{{proyecto.nombre}} · {{proyecto.visibilidad}} · {{modo.defecto}}"
    assert fill(texto, valores) == "proyecto-ejemplo · publico · manual"
    assert fill("{{autonomia.paralelismo}}", valores) == "1"


def test_hito_cero_vale() -> None:
    assert fill("hito: {{hito.numero}}", _valores(hito__numero=0)) == "hito: 0"


def test_una_llave_literal() -> None:
    assert fill(r"\{{proyecto.nombre}} y \{{", _valores()) == "{{proyecto.nombre}} y {{"


def test_una_sola_pasada() -> None:
    valores = _valores(hito__titulo="{{proyecto.nombre}}")
    assert fill("{{hito.titulo}}", valores) == "{{proyecto.nombre}}"


def test_llaves_sueltas_de_cierre_no_significan_nada() -> None:
    assert fill("a }} b } {c}", _valores()) == "a }} b } {c}"


@pytest.mark.parametrize(
    "hueco", ["{{ proyecto.nombre }}", "{{}}", "{{proyecto.nombre", "{{{x}}}", "{{X}}"]
)
def test_un_hueco_mal_escrito_es_un_error(hueco: str) -> None:
    [problema] = _error(f"a\n{hueco}\n")
    assert problema.startswith("línea 2: hueco mal escrito")


def test_una_clave_que_no_existe_es_un_error() -> None:
    assert _error("{{proyecto.nombr}}") == [
        "línea 1: la clave «proyecto.nombr» no existe: no es de menairos.toml ni de "
        "las que pasa quien llama"
    ]


def test_un_hueco_sin_rellenar_es_un_error() -> None:
    valores = values(CONFIG, {"fecha": "2026-01-15"})
    assert _error("{{hito.numero}}", valores) == [
        "línea 1: hueco sin rellenar: «hito.numero» lo tiene que pasar quien llama"
    ]


@pytest.mark.parametrize(
    ("clave", "tipo"),
    [
        ("modo.resumen_aprendizaje", "un booleano"),
        ("stack.plantillas", "una lista"),
        ("proyecto", "una tabla"),
    ],
)
def test_un_valor_que_no_es_texto_ni_entero_es_un_error(clave: str, tipo: str) -> None:
    assert _error(f"{{{{{clave}}}}}") == [
        f"línea 1: «{clave}» no es un texto ni un entero: es {tipo}"
    ]


def test_un_booleano_de_quien_llama_no_es_un_numero() -> None:
    [problema] = _error("{{hito.numero}}", _valores(hito__numero=True))
    assert problema.endswith("es un booleano")


@pytest.mark.parametrize("valor", ["", "  ", "\ufeff"])
def test_un_texto_vacio_es_un_error(valor: str) -> None:
    [problema] = _error("{{hito.titulo}}", _valores(hito__titulo=valor))
    assert problema.endswith("está vacío o solo tiene espacios")


def test_el_texto_vacio_de_menairos_toml_tambien() -> None:
    [problema] = _error("{{guardarrailes.ventana_horaria}}")
    assert "vacío" in problema


@pytest.mark.parametrize("valor", ["a\nb", "a\r\nb", "a\u2028b", "a\n"])
def test_un_texto_con_saltos_de_linea_es_un_error(valor: str) -> None:
    [problema] = _error("{{hito.titulo}}", _valores(hito__titulo=valor))
    assert "saltos de línea" in problema


def test_salen_todos_los_problemas_con_su_linea_y_su_plantilla() -> None:
    texto = "{{proyecto.nombre}}\n{{nada}}\n\n{{ mal }}\n{{stack.plantillas}}\n"
    with pytest.raises(TemplateError) as error:
        fill(texto, _valores(), name="x.md")
    assert [p.split(":")[0] for p in error.value.problems] == [
        "«x.md», línea 2",
        "«x.md», línea 4",
        "«x.md», línea 5",
    ]


def test_una_clave_de_quien_llama_desconocida_es_un_error() -> None:
    with pytest.raises(TemplateError, match="«proyecto.nombre» no es una clave"):
        values(CONFIG, {"proyecto.nombre": "otro"})


def test_las_claves_de_quien_llama_no_chocan_con_menairos_toml() -> None:
    tablas = set(load_schema("menairos")["properties"])
    assert {clave.split(".")[0] for clave in CALLER_KEYS}.isdisjoint(tablas)


def test_un_menairos_toml_no_valido_es_un_error() -> None:
    with pytest.raises(TemplateError, match="menairos.toml no es válido: proyecto"):
        values({"menairos": {"version": "1.0.0"}, "stack": {"plantillas": ["base"]}})


TITULO_DIFICIL = "Hito 1: \"núcleo\" \\ #x 'a' 🚀"


def test_en_yaml_el_texto_se_escapa_y_conserva_su_valor() -> None:
    valores = _valores(hito__titulo=TITULO_DIFICIL, tarea__id='T-0"1')
    tareas = yaml.safe_load(render("hito-N.tareas.yaml", valores))
    assert tareas["titulo"] == TITULO_DIFICIL
    decisiones = yaml.safe_load(render("decisiones-tarea.yaml", valores))
    assert decisiones["tarea"] == 'T-0"1'


def test_en_markdown_el_texto_va_tal_cual() -> None:
    valores = _valores(hito__titulo=TITULO_DIFICIL)
    assert f"# Hito 1 — {TITULO_DIFICIL}\n" in render("hito-N.md", valores)


# ── Un hito generado desde las plantillas y spec validar ────────────────────

DOCUMENTOS = {
    "docs/producto.md": "producto.md",
    "docs/diseno.md": "diseno.md",
    "docs/hitos.md": "hitos.md",
    "docs/abiertas.md": "abiertas.md",
    "docs/specs/hito-{n}.md": "hito-N.md",
    "docs/specs/hito-{n}.tareas.yaml": "hito-N.tareas.yaml",
}


def _esqueleto(raiz: Path, hito: int) -> dict[str, object]:
    (raiz / "menairos.toml").write_text(TOML, encoding="utf-8")
    valores = values(load_document(raiz / "menairos.toml"), _llamada(hito))
    for destino, plantilla in DOCUMENTOS.items():
        ruta = raiz / destino.format(n=hito)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(render(plantilla, valores), encoding="utf-8")
    (raiz / "docs" / "decisiones").mkdir()
    return valores


def _descomentar_la_tarea_de_ejemplo(texto: str) -> str:
    lineas = [
        linea[1:] if linea.startswith("#  ") else linea
        for linea in texto.replace("tareas: []\n", "tareas:\n").splitlines()
    ]
    return "\n".join(lineas) + "\n"


@pytest.mark.parametrize("hito", [0, 3])
def test_el_esqueleto_da_solo_los_errores_por_falta_de_contenido(
    tmp_path: Path, hito: int
) -> None:
    _esqueleto(tmp_path, hito)
    informe = validate_spec(tmp_path, hito)
    assert [(e.code, e.file, e.path) for e in informe.errors] == [
        ("E02", f"docs/specs/hito-{hito}.tareas.yaml", "tareas"),
        ("E10", f"docs/specs/hito-{hito}.md", "#validación-funcional"),
        ("E12", "docs/decisiones/", ""),
    ]
    assert informe.errors[0].message == "debe tener al menos un elemento"
    assert "ninguna comprobación" in informe.errors[1].message
    assert informe.warnings == ()
    assert informe.skipped == DATA_CHECKS


def test_con_el_contenido_minimo_pasa_sin_errores(tmp_path: Path) -> None:
    valores = _esqueleto(tmp_path, 1)
    specs = tmp_path / "docs" / "specs"
    tareas = specs / "hito-1.tareas.yaml"
    tareas.write_text(
        _descomentar_la_tarea_de_ejemplo(tareas.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    hito = specs / "hito-1.md"
    comprobacion = "- ✅ La CLI responde — `uv run app --version`\n\n## Anexo"
    hito.write_text(
        hito.read_text(encoding="utf-8").replace("## Anexo", comprobacion),
        encoding="utf-8",
    )
    adr = tmp_path / "docs" / "decisiones" / "0001-stack-del-proyecto.md"
    adr.write_text(render("adr.md", valores), encoding="utf-8")

    informe = validate_spec(tmp_path, 1)
    assert informe.errors == ()
    assert informe.warnings == ()
    assert informe.skipped == ()
    assert len(load_document(tareas)["tareas"]) == 1
