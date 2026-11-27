"""Tests del lector de Markdown: encabezados, anclas como GitHub y secciones (T-06)."""

from pathlib import Path

import pytest

from menairos.markdown import github_slug, parse, read, visible_text

RAIZ = Path(__file__).resolve().parents[1]
CASOS = RAIZ / "tests" / "data" / "spec_validar" / "anclas.md"

# Lo que GitHub dio para tests/data/spec_validar/anclas.md (API de contenidos con
# `Accept: application/vnd.github.html+json`, rama feat/h0-spec-validar, una sola
# lectura el 2026-11-27; anexo de T-06). Cada par es (texto visible, ancla); None
# es un encabezado sin ancla.
GITHUB: list[tuple[str, str | None]] = [
    ("Casos difíciles de anclas", "casos-difíciles-de-anclas"),
    ("Modelo de datos", "modelo-de-datos"),
    ("Validación funcional", "validación-funcional"),
    ("ÁRBOL Ñandú Über", "árbol-ñandú-über"),
    ("¿Qué?", "qué"),
    ("¿Qué pasa si falta menairos.toml?", "qué-pasa-si-falta-menairostoml"),
    ("idioma_docs y stack.plantillas", "idioma_docs-y-stackplantillas"),
    ("2.2 Esquemas", "22-esquemas"),
    ("10.1 Diez", "101-diez"),
    ("6.3 menairos cierre N --aprobar", "63-menairos-cierre-n---aprobar"),
    (
        "1.6 Verificación temprana del plugin (V-plugin)",
        "16-verificación-temprana-del-plugin-v-plugin",
    ),
    ("4.2 /crear-spec", "42-crear-spec"),
    ("snake_case y a_b_c", "snake_case-y-a_b_c"),
    ("init y doble y doble", "init-y-doble-y-doble"),
    ("énfasis y otro y ab", "énfasis-y-otro-y-ab"),
    ("tachado", "tachado"),
    ("Hecho ✅ y 👁 revisado 🚀", "hecho--y--revisado-"),
    ("✅", None),
    ("Pulgar 👍🏽", "pulgar-"),
    ("Hito 0 — Núcleo en modo manual", "hito-0--núcleo-en-modo-manual"),
    (
        "«Comillas» “curvas” 'simples' \"rectas\" l'eau",
        "comillas-curvas-simples-rectas-leau",
    ),
    ("a – b … c · d → e ≥ f", "a--b--c--d--e--f"),
    ("C++ & C# = 1.0 + 2/3", "c--c--10--23"),
    ("Entidades & # ©", "entidades---"),
    ("Enlace texto y negrita", "enlace-texto-y-negrita"),
    ("Imagen  fin", "imagen--fin"),
    ("Título con almohadillas", "título-con-almohadillas"),
    ("Espacios   dobles", "espacios---dobles"),
    ("Repetido", "repetido"),
    ("Repetido", "repetido-1"),
    ("Repetido-1", "repetido-1-1"),
    ("Repetido", "repetido-2"),
    ("REPETIDO", "repetido-3"),
    ("e\u0301 combinado", "e\u0301-combinado"),
    ("Ελληνικά 漢字 ① ²", "ελληνικά-漢字--"),
    ("İstanbul ẞ", "i\u0307stanbul-ß"),
    ("Barra#escapada *", "barraescapada-"),
    ("html dentro", "html-dentro"),
    ("Tab\tseparado", "tabseparado"),
    ("No\u00a0rompible", "norompible"),
    ("Dos--guiones -final-", "dos--guiones--final-"),
    ("(paréntesis) [corchetes] {llaves}", "paréntesis-corchetes-llaves"),
    ("¿?", "-1"),
    ("100%", "100"),
    ("Formato de abiertas.md (E11).", "formato-de-abiertasmd-e11"),
    # GitHub los cuenta; Menairos no (hito-0.md 2.3): en lista, en cita y setext.
    ("En lista", "en-lista"),
    ("En cita", "en-cita"),
    ("Setext uno", "setext-uno"),
    ("Setext dos", "setext-dos"),
    ("Sangrado tres", "sangrado-tres"),
    ("Final", "final"),
]
NO_CUENTAN = {"En lista", "En cita", "Setext uno", "Setext dos"}

# El texto visible de Menairos conserva «~~» (GitHub lo muestra tachado); el ancla
# es la misma, porque «~» se quita.
TEXTO_DE_MENAIROS = {"tachado": "~~tachado~~"}


def test_las_anclas_del_fichero_de_casos_son_las_de_github() -> None:
    documento = read(CASOS)
    esperadas = [
        (TEXTO_DE_MENAIROS.get(texto, texto), ancla or "")
        for texto, ancla in GITHUB
        if texto not in NO_CUENTAN
    ]
    obtenidas = [(h.text, h.anchor) for h in documento.headings]
    assert obtenidas == esperadas


def test_los_encabezados_que_no_cuentan_no_tienen_ancla() -> None:
    anclas = read(CASOS).anchors
    for texto, ancla in GITHUB:
        if texto in NO_CUENTAN:
            assert ancla not in anclas
    for ancla in ("dentro-de-código", "sigue-dentro", "dentro-de-virgulillas"):
        assert ancla not in anclas
    for ancla in ("sigue-en-virgulillas", "dentro-de-cuatro", "sangrado-cuatro"):
        assert ancla not in anclas
    assert "sin-espacio" not in anclas


@pytest.mark.parametrize(
    ("encabezado", "ancla"),
    [
        # Encabezados reales de hito-0.md, con el id que dio GitHub en main (9b1f887).
        ("Hito 0 — Núcleo en modo manual", "hito-0--núcleo-en-modo-manual"),
        (
            "`menairos.schema.json` (para `menairos.toml`)",
            "menairosschemajson-para-menairostoml",
        ),
        (
            "`tareas.schema.json` (para `hito-N.tareas.yaml`)",
            "tareasschemajson-para-hito-ntareasyaml",
        ),
        ("6.3 `menairos cierre N --aprobar`", "63-menairos-cierre-n---aprobar"),
        ("4.2 `/crear-spec`", "42-crear-spec"),
        ("1. H0.0 — Arranque", "1-h00--arranque"),
        ("Validación funcional", "validación-funcional"),
        ("T-05 — Esquemas JSON", "t-05--esquemas-json"),
        (
            "T-04 — Verificación temprana del plugin (V-plugin) y repo de prueba",
            "t-04--verificación-temprana-del-plugin-v-plugin-y-repo-de-prueba",
        ),
    ],
)
def test_anclas_de_encabezados_reales(encabezado: str, ancla: str) -> None:
    assert github_slug(visible_text(encabezado)) == ancla


@pytest.mark.parametrize(
    ("contenido", "texto"),
    [
        ("`a_b` y _c_", "a_b y c"),
        ("``con ` dentro``", "con ` dentro"),
        ("` espacios `", "espacios"),
        ("`sin cerrar", "`sin cerrar"),
        ("[enlace [anidado]](x) fin", "enlace [anidado] fin"),
        ("[no es enlace] fin", "[no es enlace] fin"),
        ("<https://example.com> fin", "https://example.com fin"),
        ("a <!-- comentario --> b", "a  b"),
        ("_abierto sin cerrar", "_abierto sin cerrar"),
        ("__a_", "_a"),
        ("\\_literal\\_", "_literal_"),
    ],
)
def test_texto_visible(contenido: str, texto: str) -> None:
    assert visible_text(contenido) == texto


def test_bom_y_crlf() -> None:
    documento = parse("\ufeff# Título\r\n\r\n## Otro\rtexto\r\n")
    assert [h.anchor for h in documento.headings] == ["título", "otro"]
    assert [line.text for line in documento.lines] == [
        "# Título",
        "",
        "## Otro",
        "texto",
    ]


def test_bom_al_leer_un_fichero(tmp_path: Path) -> None:
    ruta = tmp_path / "x.md"
    ruta.write_bytes("\ufeff# Título\r\n".encode())
    assert [h.anchor for h in read(ruta).headings] == ["título"]


def test_un_cercado_solo_se_cierra_con_el_mismo_caracter_y_al_menos_tan_largo() -> None:
    texto = "````\n```\n~~~~\n# a\n````\n# b\n~~~\n```\n# c\n"
    documento = parse(texto)
    assert [h.text for h in documento.headings] == ["b"]
    assert [line.in_code for line in documento.lines][:6] == [
        True,
        True,
        True,
        True,
        True,
        False,
    ]


def test_un_cercado_sin_cerrar_llega_hasta_el_final() -> None:
    assert parse("# a\n```\n# b\n").headings[0].text == "a"
    assert len(parse("# a\n```\n# b\n").headings) == 1


def test_comillas_invertidas_en_la_informacion_no_abren_cercado() -> None:
    assert [h.text for h in parse("``` a`b\n# x\n").headings] == ["x"]


def test_almohadillas_de_cierre_y_almohadilla_pegada() -> None:
    documento = parse("## C# ##\n## #\n##\tTab\n####### siete\n")
    assert [(h.level, h.text) for h in documento.headings] == [(2, "C#"), (2, "Tab")]


def test_la_seccion_llega_hasta_el_siguiente_encabezado_de_su_nivel() -> None:
    documento = parse("## A\nuno\n### A1\ndos\n## B\ntres\n# C\n")
    a, a1, b, _ = documento.headings
    assert [line.text for line in documento.section(a)] == ["uno", "### A1", "dos"]
    assert [line.text for line in documento.section(a1)] == ["dos"]
    assert [line.text for line in documento.section(b)] == ["tres"]


def test_la_ultima_seccion_llega_hasta_el_final() -> None:
    documento = parse("# A\nuno\ndos")
    assert [line.number for line in documento.section(documento.headings[0])] == [
        2,
        3,
    ]


def test_un_sufijo_que_choca_con_un_encabezado_anterior_sigue_contando() -> None:
    """Como github-slugger: si «a-1» ya existe, el segundo «a» es «a-2».

    GitHub confirmó el caso contrario («Repetido-1» después de un «repetido-1»
    generado da «repetido-1-1»); este orden sale del mismo algoritmo.
    """
    documento = parse("# a\n# a-1\n# a\n# a\n")
    assert [h.anchor for h in documento.headings] == ["a", "a-1", "a-2", "a-3"]
