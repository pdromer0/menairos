"""Tests del issue de una tarea (T-08): título, cuerpo, etiquetas, huella y marca.

Los cuerpos esperados están escritos a mano a partir del formato de hito-0.md 2.4, y
la huella se recalcula aquí con hashlib, sin pasar por el módulo. Los datos son los
del ejemplo congelado de tests/data/spec_publicar/ejemplo.
"""

import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest

from menairos.schemas import apply_defaults, load_document
from menairos.task_issues import (
    Fingerprint,
    content_without,
    find_markers,
    issue_title,
    labels_digest,
    normalize_body,
    one_line,
    previous_labels,
    render,
    with_marker,
)

EJEMPLO = Path(__file__).resolve().parent / "data" / "spec_publicar" / "ejemplo"
YAML = "docs/specs/hito-0.tareas.yaml"
REPO = "pdromer0/menairos-prueba"
URL = f"https://github.com/{REPO}/blob/main/docs/specs/hito-0.md"
PIE = (
    "*Generado por `menairos spec publicar` desde `docs/specs/hito-0.tareas.yaml`: "
    "los cambios se hacen allí.*"
)

CUERPO_T02 = f"""\
Tarea **T-02** del hito 0, área `datos`.

**Crítica:** Fija el formato que leen las demás tareas

## Especificación

- [hito-0.md#12-lectura]({URL}#12-lectura)
- [hito-0.md]({URL})

## Criterios de aceptación

- [ ] Lee los datos de T-01

## Datos

- **Rama:** `feat/h0-lectura`
- **Depende de:** T-01 · Datos de ejemplo
- **Necesita el portátil:** no
- **La hace:** Claude
- **Modo:** el del hito

{PIE}"""

CUERPO_T03 = f"""\
Tarea **T-03** del hito 0, área `entorno`.

## Especificación

- [hito-0.md#21-entorno]({URL}#21-entorno)

## Criterios de aceptación

- [ ] El entorno se prepara en local

## Datos

- **Rama:** `chore/h0-entorno`
- **Depende de:** T-01 · Datos de ejemplo
- **Necesita el portátil:** sí (donde: local)
- **La hace:** Claude
- **Modo:** didáctico (etiqueta `modo:didactico`)

{PIE}"""


def _h(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def _tareas() -> dict[str, dict[str, Any]]:
    documento = apply_defaults("tareas", load_document(EJEMPLO / YAML))
    return {tarea["id"]: tarea for tarea in documento["tareas"]}


def _render(tid: str, tareas: dict[str, dict[str, Any]] | None = None) -> Any:
    tareas = tareas or _tareas()
    return render(tareas[tid], tareas, milestone=0, repo=REPO, tasks_file=YAML)


# ── Cuerpo, título y etiquetas ──────────────────────────────────────────────


def test_cuerpo_exacto_de_una_tarea_critica_con_un_enlace_sin_ancla() -> None:
    issue = _render("T-02")
    assert issue.title == "T-02 · Lectura de los datos"
    assert issue.content == CUERPO_T02
    assert issue.labels == ("area:datos", "critica", "tipo:tarea")


def test_cuerpo_exacto_de_una_tarea_local_con_modo() -> None:
    issue = _render("T-03")
    assert issue.content == CUERPO_T03
    assert issue.labels == ("area:entorno", "modo:didactico", "tipo:tarea")


def test_codex_y_varias_dependencias() -> None:
    contenido = _render("T-04").content
    assert "- **La hace:** Codex" in contenido
    assert "- **Depende de:** T-02 · Lectura de los datos; T-03 · Entorno local" in (
        contenido
    )
    assert "- **Depende de:** ninguna" in _render("T-01").content


def test_huella_de_valor_fijo_y_recalculada_a_mano() -> None:
    issue = _render("T-02")
    a_mano = Fingerprint(
        _h("T-02 · Lectura de los datos"),
        _h(CUERPO_T02),
        _h("area:datos\ncritica\ntipo:tarea"),
    )
    assert issue.fingerprint == a_mano
    assert (
        str(issue.fingerprint) == "a26eef9c69ca6a2a.76d905ea2fab0109.445cc2ee50b21811"
    )
    assert issue.marker == (
        "<!-- menairos:tarea=T-02 hito=0 "
        "huella=a26eef9c69ca6a2a.76d905ea2fab0109.445cc2ee50b21811 -->"
    )
    assert issue.body == f"{CUERPO_T02}\n\n{issue.marker}"


def test_las_huellas_del_ejemplo_no_cambian_sin_querer() -> None:
    huellas = {tid: str(_render(tid).fingerprint) for tid in _tareas()}
    assert huellas == {
        "T-01": "0735601b7fc1792a.4abaaa0a736e2b35.108ff8eedf4a38e9",
        "T-02": "a26eef9c69ca6a2a.76d905ea2fab0109.445cc2ee50b21811",
        "T-03": "89c4e21358f17749.f327d4d3d9988cdb.1e5cc19043220ead",
        "T-04": "7cbb55ac53cd2ebf.865cbbf9cb23f4d4.9204a1791163504b",
    }


def test_rutas_normalizadas_y_codificadas() -> None:
    tareas = _tareas()
    tarea = copy.deepcopy(tareas["T-01"])
    tarea["especificacion"] = ["../specs/./hito-0.md#x", "sub/a b.md", "c[1].md"]
    contenido = render(tarea, tareas, milestone=0, repo=REPO, tasks_file=YAML).content
    assert f"- [../specs/./hito-0.md#x]({URL}#x)" in contenido
    base = f"https://github.com/{REPO}/blob/main/docs/specs"
    assert f"- [sub/a b.md]({base}/sub/a%20b.md)" in contenido
    assert f"- [c\\[1\\].md]({base}/c%5B1%5D.md)" in contenido


def test_textos_de_varias_lineas() -> None:
    tareas = _tareas()
    tarea = copy.deepcopy(tareas["T-02"])
    tarea["titulo"] = "Dos\nlíneas"
    tarea["motivo_critica"] = "Motivo\n<!-- menairos:tarea=T-09 hito=0 -->"
    tarea["criterios_aceptacion"] = ["Primera\nsegunda\n\n# no es un encabezado"]
    tareas["T-01"] = {**tareas["T-01"], "titulo": "Datos\nde ejemplo"}
    issue = render(tarea, tareas, milestone=0, repo=REPO, tasks_file=YAML)
    assert issue.title == "T-02 · Dos líneas"
    assert "**Crítica:** Motivo <!-- menairos:tarea=T-09 hito=0 -->" in issue.content
    assert "- [ ] Primera\n  segunda\n\n  # no es un encabezado" in issue.content
    assert "- **Depende de:** T-01 · Datos de ejemplo" in issue.content
    assert [m.task for m in find_markers(issue.body)] == ["T-02"]


def test_one_line_y_titulo() -> None:
    assert one_line("  a \n  b\r\nc  ") == "a b c"
    assert issue_title({"id": "T-07", "titulo": "Uno\ndos"}) == "T-07 · Uno dos"


# ── Marca ───────────────────────────────────────────────────────────────────


def test_la_marca_de_un_cuerpo_generado() -> None:
    issue = _render("T-02")
    [marca] = find_markers(issue.body)
    assert (marca.task, marca.milestone, marca.fingerprint) == (
        "T-02",
        0,
        issue.fingerprint,
    )
    assert content_without(issue.body, marca) == issue.content


@pytest.mark.parametrize(
    "linea",
    [
        "<!-- menairos:tarea=T-02 hito=0 huella=roto -->",
        "<!-- menairos:tarea=T-02 hito=0 -->",
        "<!-- menairos:tarea=T-02 hito=0 huella=a26eef9c69ca6a2a.76d905ea2fab0109 -->",
        "<!-- menairos:tarea=T-02 hito=0 huella=A26EEF9C69CA6A2A."
        "76d905ea2fab0109.445cc2ee50b21811 -->",
    ],
    ids=["texto", "sin-huella", "dos-partes", "mayusculas"],
)
def test_una_marca_con_la_huella_rota_se_reconoce_pero_es_ilegible(linea: str) -> None:
    [marca] = find_markers(f"Cuerpo\n\n{linea}")
    assert (marca.task, marca.milestone, marca.fingerprint) == ("T-02", 0, None)


@pytest.mark.parametrize(
    "texto",
    [
        "- [ ] <!-- menairos:tarea=T-02 hito=0 -->",
        "  <!-- menairos:tarea=T-02 hito=0 -->",
        "<!-- menairos:tarea=T-02 hito=01 -->",
        "<!-- menairos:tarea=T-02 hito=0 --> y más",
        "`<!-- menairos:tarea=T-02 hito=0 -->`",
        "<!-- menairos:tarea=T-02 hito=x -->",
    ],
    ids=[
        "en-un-criterio",
        "sangrada",
        "hito-con-cero",
        "texto-detras",
        "codigo",
        "hito",
    ],
)
def test_lo_que_no_es_una_marca(texto: str) -> None:
    assert find_markers(f"Cuerpo\n{texto}\nfin") == []


def test_la_marca_de_otro_hito_se_lee_con_su_hito() -> None:
    [marca] = find_markers("<!-- menairos:tarea=T-01 hito=12 -->")
    assert (marca.task, marca.milestone) == ("T-01", 12)


def test_cuerpo_con_crlf_y_cuerpo_vacio() -> None:
    issue = _render("T-02")
    cuerpo = normalize_body(issue.body.replace("\n", "\r\n") + "\r\n")
    [marca] = find_markers(cuerpo)
    assert marca.fingerprint == issue.fingerprint
    assert content_without(cuerpo, marca) == issue.content
    assert normalize_body(None) == ""
    assert find_markers(normalize_body(None)) == []


def test_cambiar_solo_la_marca_conserva_el_resto_del_cuerpo() -> None:
    cuerpo = "Editado a mano\n\n<!-- menairos:tarea=T-02 hito=0 huella=x -->\nnota"
    [marca] = find_markers(cuerpo)
    nuevo = with_marker(cuerpo, marca, "<!-- nueva -->")
    assert nuevo == "Editado a mano\n\n<!-- nueva -->\nnota"
    assert content_without(cuerpo, marca) == "Editado a mano\n\n\nnota"


# ── Etiquetas de la vez anterior ────────────────────────────────────────────


@pytest.mark.parametrize(
    "etiquetas",
    [
        {"tipo:tarea", "area:datos"},
        {"tipo:tarea", "area:datos", "critica"},
        {"tipo:tarea", "area:entorno", "modo:didactico"},
        {"tipo:tarea", "area:entorno", "critica", "modo:automatico"},
    ],
)
def test_las_etiquetas_de_antes_se_deducen_de_la_huella(etiquetas: set[str]) -> None:
    huella = Fingerprint("0" * 16, "0" * 16, labels_digest(etiquetas))
    assert previous_labels(huella, ["datos", "entorno"]) == etiquetas


def test_sin_coincidencia_no_se_deduce_nada() -> None:
    huella = Fingerprint("0" * 16, "0" * 16, labels_digest({"tipo:tarea", "area:otra"}))
    assert previous_labels(huella, ["datos", "entorno"]) is None
    assert previous_labels(huella, ["otra"]) == {"tipo:tarea", "area:otra"}


def test_labels_digest_sin_mayusculas_ni_orden_ni_repetidas() -> None:
    assert labels_digest(["B", "a", "b"]) == _h("a\nb")
