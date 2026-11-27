"""Tests del catálogo de etiquetas (T-08): el de diseno.md 3.4, válido para GitHub."""

import re
from pathlib import Path

from menairos import labels
from menairos.labels import BASE_LABELS, Label, area_label, is_valid, mode_label

RAIZ = Path(__file__).resolve().parents[1]


def _etiquetas_de_diseno() -> set[str]:
    """Los nombres de la tabla de diseno.md 3.4, salvo `area:*`."""
    texto = (RAIZ / "docs" / "diseno.md").read_text(encoding="utf-8")
    seccion = texto.split("### 3.4 Etiquetas de GitHub", 1)[1].split("\n## ", 1)[0]
    filas = [linea for linea in seccion.splitlines() if linea.startswith("| `")]
    nombres = {
        n for fila in filas for n in re.findall(r"`([^`]+)`", fila.split("|")[1])
    }
    return nombres - {"area:*"}


def test_el_catalogo_es_el_de_diseno_3_4() -> None:
    assert {label.name for label in BASE_LABELS} == _etiquetas_de_diseno()
    assert len(BASE_LABELS) == 10


def test_nombres_unicos_en_minusculas_y_validos_para_github() -> None:
    nombres = [label.name for label in BASE_LABELS]
    assert len(set(nombres)) == len(nombres)
    assert all(nombre == nombre.lower() for nombre in nombres)
    assert all(is_valid(label) for label in BASE_LABELS)


def test_los_modos_tienen_su_etiqueta_en_el_catalogo() -> None:
    nombres = {label.name for label in BASE_LABELS}
    assert {mode_label(modo) for modo in labels.MODES} <= nombres
    assert {labels.TASK, labels.CRITICAL} <= nombres


def test_etiqueta_de_area() -> None:
    assert area_label("contratos") == Label(
        "area:contratos", "c5def5", "Área «contratos» de las tareas"
    )
    assert is_valid(area_label("a" * 45))
    assert not is_valid(area_label("a" * 46))  # area: + 46 = 51 caracteres


def test_is_valid_mira_longitudes_y_color() -> None:
    assert is_valid(Label("a" * 50, "000000", "d" * 100))
    assert not is_valid(Label("", "000000", ""))
    assert not is_valid(Label("a", "000000", "d" * 101))
    assert not is_valid(Label("a", "#00000", ""))
    assert not is_valid(Label("a", "ABCDEF", ""))
