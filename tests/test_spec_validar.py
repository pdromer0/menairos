"""Tests de `menairos spec validar` (T-06): E01–E12, A01–A04 y casos límite de 2.3.

Cada test construye un proyecto mínimo válido en una carpeta temporal y le cambia
lo que prueba. Los datos son sintéticos.
"""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from menairos import spec_validation
from menairos.spec_validation import (
    DATA_CHECKS,
    Report,
    UsageError,
    validate_spec,
)

RAIZ = Path(__file__).resolve().parents[1]

TOML = """\
[menairos]
version = "3.0.0"

[proyecto]
nombre = "ejemplo"
repo = "ejemplo/ejemplo"

[stack]
plantillas = ["base"]
"""

HITO_MD = """\
# Hito 1 — Ejemplo

## 1.1 Primera

## 1.2 Segunda

## Validación funcional

- ✅ La primera funciona — `uv run pytest`
- 👁 La segunda se ve bien.
"""

ABIERTAS = """\
# Abiertas

## Producto

### ¿Algo pendiente?

**Justificación:** se decide más adelante.
"""

ADR = """\
# 0001. Stack

- **Tipo:** stack
- **Decidido por:** pedro
"""


def _tarea(numero: int, **cambios: Any) -> dict[str, Any]:
    tid = f"T-{numero:02d}"
    tarea: dict[str, Any] = {
        "id": tid,
        "titulo": f"Tarea {numero}",
        "rama": f"feat/h1-tarea-{numero}",
        "area": "nucleo",
        "especificacion": ["hito-1.md#11-primera"],
        "criterios_aceptacion": ["Funciona"],
    }
    tarea.update(cambios)
    return tarea


def _tareas_base() -> dict[str, Any]:
    return {
        "hito": 1,
        "titulo": "Hito 1 — Ejemplo",
        "tareas": [
            _tarea(1),
            _tarea(2, depende_de=["T-01"], especificacion=["hito-1.md#12-segunda"]),
            _tarea(3, depende_de=["T-01", "T-02"], especificacion=["hito-1.md"]),
        ],
    }


def _yaml(documento: Any) -> str:
    return yaml.safe_dump(documento, allow_unicode=True, sort_keys=False)


def _proyecto(
    raiz: Path,
    *,
    tareas: Any = None,
    tareas_texto: str | None = None,
    toml: str = TOML,
    hito_md: str = HITO_MD,
    abiertas: str = ABIERTAS,
    adrs: dict[str, str] | None = None,
    hito: int = 1,
) -> Path:
    """Escribe un proyecto mínimo (válido si no se cambia nada) y devuelve su raíz."""
    specs = raiz / "docs" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (raiz / "docs" / "decisiones").mkdir(exist_ok=True)
    (raiz / "menairos.toml").write_text(toml, encoding="utf-8")
    texto = tareas_texto
    if texto is None:
        texto = _yaml(_tareas_base() if tareas is None else tareas)
    (specs / f"hito-{hito}.tareas.yaml").write_text(texto, encoding="utf-8")
    (specs / f"hito-{hito}.md").write_text(hito_md, encoding="utf-8")
    (raiz / "docs" / "abiertas.md").write_text(abiertas, encoding="utf-8")
    for nombre, contenido in ({"0001-stack.md": ADR} if adrs is None else adrs).items():
        (raiz / "docs" / "decisiones" / nombre).write_text(contenido, encoding="utf-8")
    return raiz


def _con(cambio: Callable[[dict[str, Any]], object]) -> dict[str, Any]:
    documento = copy.deepcopy(_tareas_base())
    cambio(documento)
    return documento


def _codigos(informe: Report) -> list[tuple[str, str, str]]:
    return [(f.code, f.file, f.path) for f in informe.errors + informe.warnings]


TAREAS = "docs/specs/hito-1.tareas.yaml"


# ── Proyecto válido y repo ──────────────────────────────────────────────────


def test_el_proyecto_minimo_es_valido(tmp_path: Path) -> None:
    informe = validate_spec(_proyecto(tmp_path))
    assert informe.ok
    assert _codigos(informe) == []
    assert informe.milestone == 1
    assert informe.tasks_file == TAREAS
    assert informe.skipped == ()


def test_el_propio_repo_valida() -> None:
    """La especificación de Menairos pasa sin errores ni avisos (decisión de Pedro)."""
    informe = validate_spec(RAIZ)
    assert informe.errors == ()
    assert informe.warnings == ()


def test_bom_y_crlf_en_todos_los_ficheros(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path)
    for ruta in raiz.rglob("*"):
        if ruta.is_file():
            texto = ruta.read_text(encoding="utf-8").replace("\n", "\r\n")
            ruta.write_bytes(("﻿" + texto).encode())
    assert _codigos(validate_spec(raiz)) == []


# ── E01: menairos.toml ──────────────────────────────────────────────────────


def test_e01_menairos_toml_no_cumple_el_esquema(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, toml=TOML + "\n[modo]\ndefeto = 'manual'\n")
    assert _codigos(validate_spec(raiz)) == [("E01", "menairos.toml", "modo.defeto")]


@pytest.mark.parametrize(
    ("toml", "mensaje"),
    [
        (TOML + "\n[proyecto\n", "no se puede leer el TOML: "),
        (TOML.replace('"ejemplo"\n', '"ejemplo"\nnombre = "otro"\n', 1), "TOML"),
    ],
    ids=["sintaxis", "clave-repetida"],
)
def test_e01_un_toml_ilegible_es_e01_y_no_un_error_de_uso(
    tmp_path: Path, toml: str, mensaje: str
) -> None:
    informe = validate_spec(_proyecto(tmp_path, toml=toml))
    assert _codigos(informe) == [("E01", "menairos.toml", "")]
    assert mensaje in informe.errors[0].message


def test_e01_no_utf8(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path)
    (raiz / "menairos.toml").write_bytes(TOML.encode("utf-16"))
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("E01", "menairos.toml", "")]
    assert informe.errors[0].message == "no se puede leer: no está en UTF-8"


def test_con_e01_no_se_comprueba_e03_a_e09_pero_si_e10_a_e12(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][1].update(depende_de=["T-99"]))
    raiz = _proyecto(
        tmp_path,
        toml="[menairos]\n",
        tareas=tareas,
        hito_md="# Hito 1\n",
        abiertas="### Punto\n",
        adrs={},
    )
    informe = validate_spec(raiz)
    assert [f.code for f in informe.errors] == [
        "E01",
        "E01",
        "E01",
        "E10",
        "E11",
        "E12",
    ]
    assert informe.skipped == DATA_CHECKS


# ── E02: hito-N.tareas.yaml ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("texto", "ruta"),
    [
        ("", ""),
        ("hito: 1\ntitulo: Hito\ntareas: []\n", "tareas"),
        ("hito: 1\ntitulo: null\ntareas: []\n", "titulo"),
    ],
    ids=["yaml-vacio", "tareas-vacia", "valor-null"],
)
def test_e02_casos_vacios(tmp_path: Path, texto: str, ruta: str) -> None:
    informe = validate_spec(_proyecto(tmp_path, tareas_texto=texto))
    assert ("E02", TAREAS, ruta) in _codigos(informe)
    assert {f.code for f in informe.errors} == {"E02"}
    assert informe.skipped == DATA_CHECKS


def test_e02_null_en_una_lista_de_una_tarea(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(depende_de=None))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E02", TAREAS, "tareas[0].depende_de")]


def test_e02_id_sin_relleno(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(id="T-1"))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E02", TAREAS, "tareas[0].id")]


def test_e02_id_de_tres_digitos_con_cero(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][1].update(depende_de=["T-001"]))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E02", TAREAS, "tareas[1].depende_de[0]")]


def test_e02_anclas_y_alias_de_yaml_se_aceptan(tmp_path: Path) -> None:
    texto = _yaml(_tareas_base()).replace(
        "  criterios_aceptacion:\n  - Funciona\n",
        "  criterios_aceptacion: &criterios\n  - Funciona\n",
        1,
    )
    texto = texto.replace(
        "  criterios_aceptacion:\n  - Funciona\n",
        "  criterios_aceptacion: *criterios\n",
    )
    assert "*criterios" in texto
    assert _codigos(validate_spec(_proyecto(tmp_path, tareas_texto=texto))) == []


def test_e02_un_alias_en_bucle_es_error_de_esquema(tmp_path: Path) -> None:
    texto = _yaml(_tareas_base()).replace(
        "  criterios_aceptacion:\n  - Funciona\n",
        "  criterios_aceptacion: &bucle\n  - *bucle\n",
        1,
    )
    informe = validate_spec(_proyecto(tmp_path, tareas_texto=texto))
    assert {f.code for f in informe.errors} == {"E02"}


def test_e02_clave_repetida(tmp_path: Path) -> None:
    texto = _yaml(_tareas_base()).replace("hito: 1\n", "hito: 1\nhito: 1\n", 1)
    informe = validate_spec(_proyecto(tmp_path, tareas_texto=texto))
    assert _codigos(informe) == [("E02", TAREAS, "")]
    assert "clave repetida «hito» en la línea 2" in informe.errors[0].message


def test_e02_sintaxis_con_linea_y_columna(tmp_path: Path) -> None:
    informe = validate_spec(_proyecto(tmp_path, tareas_texto="hito: [1\ntitulo: x\n"))
    assert _codigos(informe) == [("E02", TAREAS, "")]
    assert informe.errors[0].message.startswith("no se puede leer el YAML (línea ")


def test_e02_un_entero_de_mas_de_4300_cifras_no_rompe(tmp_path: Path) -> None:
    texto = _yaml(_tareas_base()).replace("hito: 1\n", f"hito: {'9' * 5000}\n", 1)
    informe = validate_spec(_proyecto(tmp_path, tareas_texto=texto))
    assert _codigos(informe) == [("E02", TAREAS, "")]


def test_e02_un_anidamiento_muy_hondo_no_rompe(tmp_path: Path) -> None:
    texto = "hito: 1\ntitulo: x\ntareas: " + "[" * 5000 + "]" * 5000 + "\n"
    informe = validate_spec(_proyecto(tmp_path, tareas_texto=texto))
    assert {f.code for f in informe.errors} == {"E02"}


def test_e02_el_hito_no_coincide_con_el_nombre_y_no_corta_el_resto(
    tmp_path: Path,
) -> None:
    tareas = _con(
        lambda d: (d.update(hito=0), d["tareas"][1].update(depende_de=["T-99"]))
    )
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [
        ("E02", TAREAS, "hito"),
        ("E05", TAREAS, "tareas[1].depende_de[0]"),
    ]
    assert "del hito 1 y «hito» dice 0" in informe.errors[0].message


def test_con_e02_no_se_comprueba_e03_a_e09_pero_si_e10(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"].append({"id": "T-01"}))
    raiz = _proyecto(tmp_path, tareas=tareas, hito_md="# Hito 1\n")
    informe = validate_spec(raiz)
    assert {f.code for f in informe.errors} == {"E02", "E10"}
    assert informe.skipped == DATA_CHECKS


# ── E03–E06 ─────────────────────────────────────────────────────────────────


def test_e03_id_repetido_en_el_ultimo_elemento(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"].append(_tarea(1, rama="feat/h1-otra")))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E03", TAREAS, "tareas[3].id")]
    assert (
        informe.errors[0].message
        == "el id «T-01» está repetido: ya se usó en tareas[0]"
    )


def test_e04_rama_repetida(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][2].update(rama="feat/h1-tarea-1"))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E04", TAREAS, "tareas[2].rama")]
    assert "ya se usó en tareas[0]" in informe.errors[0].message


def test_e05_dependencia_que_no_existe_en_el_primero_y_el_ultimo(
    tmp_path: Path,
) -> None:
    tareas = _con(lambda d: d["tareas"][2].update(depende_de=["T-98", "T-01", "T-99"]))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [
        ("E05", TAREAS, "tareas[2].depende_de[0]"),
        ("E05", TAREAS, "tareas[2].depende_de[2]"),
    ]


def test_e06_dependencia_de_si_misma_no_es_e07(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(depende_de=["T-01"]))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert _codigos(informe) == [("E06", TAREAS, "tareas[0].depende_de[0]")]
    assert informe.errors[0].message == "«T-01» depende de sí misma"


# ── E07: ciclos ─────────────────────────────────────────────────────────────


def _cadena(n: int, desde: int = 1) -> list[dict[str, Any]]:
    """n tareas en ciclo: cada una depende de la siguiente y la última de la primera."""
    numeros = list(range(desde, desde + n))
    return [
        _tarea(k, rama=f"feat/h1-t{k}", depende_de=[f"T-{numeros[(i + 1) % n]:02d}"])
        for i, k in enumerate(numeros)
    ]


def _e07(informe: Report) -> list[tuple[str, str]]:
    return [(f.path, f.message) for f in informe.errors if f.code == "E07"]


def test_e07_un_ciclo_con_su_ejemplo(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(depende_de=["T-03"]))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert [f.code for f in informe.errors] == ["E07"]
    assert _e07(informe) == [
        (
            "tareas[0].depende_de[0]",
            "ciclo de dependencias: T-01 → T-03 → T-01; "
            "dependen unas de otras T-01, T-02 y T-03",
        )
    ]


def test_e07_un_ciclo_de_60_tareas(tmp_path: Path) -> None:
    tareas = {"hito": 1, "titulo": "Hito 1", "tareas": _cadena(60)}
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    ((ruta, mensaje),) = _e07(informe)
    ids = [f"T-{k:02d}" for k in range(1, 61)]
    assert ruta == "tareas[0].depende_de[0]"
    assert mensaje == "ciclo de dependencias: " + " → ".join([*ids, "T-01"])


def test_e07_un_ciclo_de_1000_tareas_no_agota_la_recursion(tmp_path: Path) -> None:
    tareas = {"hito": 1, "titulo": "Hito 1", "tareas": _cadena(1000, desde=0)}
    tareas["tareas"][0]["id"] = "T-00"
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert [f.code for f in informe.errors] == ["E07"]
    assert informe.errors[0].message.count("→") == 1000


def test_e07_varios_ciclos_a_la_vez_en_orden_estable(tmp_path: Path) -> None:
    # Tres componentes, desordenadas en el YAML, y una cuarta con dos ciclos solapados.
    tareas = [
        _tarea(30, rama="feat/h1-t30", depende_de=["T-31"]),
        _tarea(10, rama="feat/h1-t10", depende_de=["T-11"]),
        _tarea(31, rama="feat/h1-t31", depende_de=["T-30"]),
        _tarea(20, rama="feat/h1-t20", depende_de=["T-21", "T-22"]),
        _tarea(11, rama="feat/h1-t11", depende_de=["T-10"]),
        _tarea(21, rama="feat/h1-t21", depende_de=["T-20"]),
        _tarea(22, rama="feat/h1-t22", depende_de=["T-20"]),
        _tarea(40, rama="feat/h1-t40", depende_de=["T-10"]),
    ]
    informe = validate_spec(
        _proyecto(tmp_path, tareas={"hito": 1, "titulo": "Hito 1", "tareas": tareas})
    )
    assert _e07(informe) == [
        ("tareas[0].depende_de[0]", "ciclo de dependencias: T-30 → T-31 → T-30"),
        ("tareas[1].depende_de[0]", "ciclo de dependencias: T-10 → T-11 → T-10"),
        (
            "tareas[3].depende_de[0]",
            "ciclo de dependencias: T-20 → T-21 → T-20; "
            "dependen unas de otras T-20, T-21 y T-22",
        ),
    ]


def test_e07_no_cuenta_dependencias_que_no_existen(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(depende_de=["T-99"]))
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert [f.code for f in informe.errors] == ["E05"]


def test_e07_con_ids_repetidos_junta_sus_dependencias(tmp_path: Path) -> None:
    tareas = _con(
        lambda d: d["tareas"].append(
            _tarea(1, rama="feat/h1-otra", depende_de=["T-02"])
        )
    )
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert [f.code for f in informe.errors] == ["E03", "E07"]
    assert _e07(informe) == [
        ("tareas[3].depende_de[0]", "ciclo de dependencias: T-01 → T-02 → T-01")
    ]


# ── E08–E09: enlaces ────────────────────────────────────────────────────────


def _enlaces(*enlaces: str) -> dict[str, Any]:
    return _con(lambda d: d["tareas"][2].update(especificacion=list(enlaces)))


def test_e08_fichero_que_no_existe_en_el_ultimo_enlace(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, tareas=_enlaces("hito-1.md", "otro.md"))
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("E08", TAREAS, "tareas[2].especificacion[1]")]
    assert informe.errors[0].message == (
        "el fichero «otro.md» no existe (se busca en «docs/specs/otro.md»)"
    )


def test_e08_los_enlaces_se_resuelven_desde_la_carpeta_del_yaml(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, tareas=_enlaces("../abiertas.md#algo-pendiente"))
    (raiz / "hito-1.md").write_text("# Solo en la raíz\n", encoding="utf-8")
    assert _codigos(validate_spec(raiz)) == []
    raiz2 = _proyecto(tmp_path / "otro", tareas=_enlaces("docs/specs/hito-1.md"))
    assert [f.code for f in validate_spec(raiz2).errors] == ["E08"]


@pytest.mark.parametrize(
    "enlace", ["../../../fuera.md", "/etc/fuera.md"], ids=["relativo", "absoluto"]
)
def test_e08_enlace_fuera_del_repo(tmp_path: Path, enlace: str) -> None:
    raiz = _proyecto(tmp_path / "repo", tareas=_enlaces(enlace))
    (tmp_path / "fuera.md").write_text("# Fuera\n", encoding="utf-8")
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("E08", TAREAS, "tareas[2].especificacion[0]")]
    assert informe.errors[0].message == f"«{enlace}» apunta fuera del repo"


def test_e08_symlink_que_sale_del_repo(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path / "repo", tareas=_enlaces("enlace.md"))
    (tmp_path / "fuera.md").write_text("# Fuera\n", encoding="utf-8")
    (raiz / "docs" / "specs" / "enlace.md").symlink_to(tmp_path / "fuera.md")
    assert [f.code for f in validate_spec(raiz).errors] == ["E08"]


def test_e08_una_carpeta_no_es_un_fichero(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, tareas=_enlaces("carpeta.md"))
    (raiz / "docs" / "specs" / "carpeta.md").mkdir()
    assert [f.code for f in validate_spec(raiz).errors] == ["E08"]


def test_e08_mayusculas_distintas_aunque_el_disco_no_las_distinga(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raiz = _proyecto(tmp_path)
    original = spec_validation.os.listdir

    def listdir(carpeta: Path) -> list[str]:
        return [n.replace("hito-1.md", "Hito-1.md") for n in original(carpeta)]

    monkeypatch.setattr(spec_validation.os, "listdir", listdir)
    informe = validate_spec(raiz)
    assert {f.code for f in informe.errors} == {"E08"}
    assert "no coincide en mayúsculas" in informe.errors[0].message


ANCLAS_MD = (
    HITO_MD
    + """
## ¿Qué?

## `menairos.toml`

## Repetido

## Repetido

```
## Dentro de código
```
"""
)


@pytest.mark.parametrize(
    "ancla",
    ["11-primera", "validación-funcional", "qué", "menairostoml", "repetido-1"],
)
def test_e09_anclas_que_existen(tmp_path: Path, ancla: str) -> None:
    raiz = _proyecto(tmp_path, tareas=_enlaces(f"hito-1.md#{ancla}"), hito_md=ANCLAS_MD)
    assert _codigos(validate_spec(raiz)) == []


@pytest.mark.parametrize(
    ("ancla", "parecida"),
    [
        ("dentro-de-código", None),
        ("zzz", None),
        ("repetido-2", "repetido-1"),
        ("validacion-funcional", "validación-funcional"),
        ("validaci%C3%B3n-funcional", "validación-funcional"),
        ("Validación-funcional", "validación-funcional"),
    ],
)
def test_e09_anclas_que_no_existen(
    tmp_path: Path, ancla: str, parecida: str | None
) -> None:
    raiz = _proyecto(
        tmp_path, tareas=_enlaces("hito-1.md", f"hito-1.md#{ancla}"), hito_md=ANCLAS_MD
    )
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("E09", TAREAS, "tareas[2].especificacion[1]")]
    mensaje = f"el ancla «#{ancla}» no existe en «hito-1.md»"
    if parecida:
        mensaje += f"; la más parecida es «#{parecida}»"
    assert informe.errors[0].message == mensaje


def test_e09_destino_que_no_es_utf8(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, tareas=_enlaces("otro.md#x"))
    (raiz / "docs" / "specs" / "otro.md").write_bytes(b"# \xff\n")
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("E09", TAREAS, "tareas[2].especificacion[0]")]
    assert informe.errors[0].message == "«otro.md»: no se puede leer: no está en UTF-8"


# ── E10: validación funcional ───────────────────────────────────────────────

HITO = "docs/specs/hito-1.md"


def _e10(tmp_path: Path, seccion: str) -> list[tuple[str, str]]:
    hito_md = "# Hito 1\n\n## 1.1 Primera\n\n## 1.2 Segunda\n\n" + seccion
    informe = validate_spec(_proyecto(tmp_path, hito_md=hito_md))
    assert {f.code for f in informe.errors} <= {"E10"}
    return [(f.path, f.message) for f in informe.errors]


def test_e10_sin_seccion(tmp_path: Path) -> None:
    assert _e10(tmp_path, "## Otra cosa\n") == [
        ("", "falta la sección «Validación funcional» (un encabezado con ese texto)")
    ]


def test_e10_seccion_sin_comprobaciones(tmp_path: Path) -> None:
    errores = _e10(
        tmp_path,
        "## Validación funcional\n\n- Una lista normal\n\n"
        "```\n- ✅ en código — `x`\n```\n",
    )
    assert errores == [
        (
            "#validación-funcional",
            "la sección «Validación funcional» (línea 7) no tiene ninguna "
            "comprobación: "
            "un elemento de lista que empiece por ✅ o 👁",
        )
    ]


def test_e10_las_comprobaciones_de_otra_seccion_no_cuentan(tmp_path: Path) -> None:
    errores = _e10(tmp_path, "## Validación funcional\n\n## Después\n\n- 👁 Fuera\n")
    assert [m for _, m in errores][0].startswith("la sección «Validación funcional»")


@pytest.mark.parametrize(
    "linea",
    [
        "- ✅ Sin orden",
        "- ✅ Orden sin raya `uv run pytest`",
        "- ✅ Raya sin código — uv run pytest",
        "- ✅ Código vacío — ` `",
        "- ✅ Dos fragmentos — `a` y `b`",
        "- ✅ Orden en medio — `a` y más texto",
    ],
)
def test_e10_una_comprobacion_sin_su_orden(tmp_path: Path, linea: str) -> None:
    errores = _e10(tmp_path, f"## Validación funcional\n\n- 👁 Bien\n{linea}\n")
    assert errores == [
        (
            "#validación-funcional",
            "la comprobación ✅ de la línea 10 no termina con su orden: "
            "« — `orden`» (6.2)",
        )
    ]


@pytest.mark.parametrize(
    "lineas",
    [
        "- ✅ En una línea — `uv run pytest tests/x.py`",
        "- ✅ En varias líneas, con la orden\n  al final — `uv run pytest`",
        "* ✅ Con asterisco — ``orden con ` dentro``",
        "- 👁 Solo de Pedro, sin orden",
    ],
)
def test_e10_comprobaciones_validas(tmp_path: Path, lineas: str) -> None:
    assert _e10(tmp_path, f"## Validación funcional\n\n{lineas}\n") == []


def test_e10_seccion_repetida(tmp_path: Path) -> None:
    seccion = (
        "## Validación funcional\n\n- 👁 Uno\n\n## Validación funcional\n\n- 👁 Dos\n"
    )
    assert _e10(tmp_path, seccion) == [
        (
            "#validación-funcional-1",
            "la sección «Validación funcional» está repetida: líneas 7 y 11",
        )
    ]


def test_e10_hito_que_no_es_utf8(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path)
    (raiz / HITO).write_bytes(b"\xff")
    assert _codigos(validate_spec(raiz)) == [
        ("E09", TAREAS, "tareas[0].especificacion[0]"),
        ("E09", TAREAS, "tareas[1].especificacion[0]"),
        ("E10", HITO, ""),
    ]


# ── E11: abiertas.md ────────────────────────────────────────────────────────

ABIERTAS_MD = "docs/abiertas.md"


def _e11(tmp_path: Path, abiertas: str) -> list[tuple[str, str]]:
    informe = validate_spec(_proyecto(tmp_path, abiertas=abiertas))
    assert {f.code for f in informe.errors} <= {"E11"}
    return [(f.path, f.message) for f in informe.errors]


def test_e11_sin_puntos_es_valido(tmp_path: Path) -> None:
    assert _e11(tmp_path, "# Abiertas\n\n## Supuestos\n\n- Uno.\n") == []


def test_e11_punto_sin_justificacion(tmp_path: Path) -> None:
    assert _e11(tmp_path, "## Grupo\n\n### ¿Uno?\n\nTexto.\n") == [
        (
            "#uno",
            "el punto «¿Uno?» (línea 3) no tiene una línea "
            "«**Justificación:**» con texto",
        )
    ]


@pytest.mark.parametrize(
    "cuerpo",
    ["**Justificación:**", "**Justificación:**   ", "```\n**Justificación:** x\n```"],
    ids=["vacia", "espacios", "en-codigo"],
)
def test_e11_justificacion_vacia_o_en_codigo(tmp_path: Path, cuerpo: str) -> None:
    assert [r for r, _ in _e11(tmp_path, f"### Uno\n\n{cuerpo}\n")] == ["#uno"]


def test_e11_la_justificacion_de_un_punto_no_vale_para_el_anterior(
    tmp_path: Path,
) -> None:
    abiertas = "### Uno\n\nTexto.\n\n### Dos\n\n**Justificación:** sí.\n"
    assert [r for r, _ in _e11(tmp_path, abiertas)] == ["#uno"]


def test_e11_un_subapartado_es_parte_del_punto(tmp_path: Path) -> None:
    abiertas = "### Uno\n\n#### Detalle\n\n**Justificación:** sí.\n\n## Otro\n"
    assert _e11(tmp_path, abiertas) == []


# ── E12: ADR de tipo stack ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "adrs",
    [
        {},
        {"README.md": "Formato:\n\n- **Tipo:** stack\n"},
        {"0001-x.md": "- **Tipo:** proceso | arquitectura | seguridad | stack\n"},
        {"0001-x.md": "```\n- **Tipo:** stack\n```\n"},
        {"0001-x.md": "- **Tipo:** proceso\n", "x-0002.md": "- **Tipo:** stack\n"},
    ],
    ids=["sin-adrs", "solo-readme", "lista-de-tipos", "en-codigo", "nombre-sin-numero"],
)
def test_e12_sin_adr_de_tipo_stack(tmp_path: Path, adrs: dict[str, str]) -> None:
    informe = validate_spec(_proyecto(tmp_path, adrs=adrs))
    assert _codigos(informe) == [("E12", "docs/decisiones/", "")]


def test_e12_basta_con_uno(tmp_path: Path) -> None:
    adrs = {"0001-a.md": "- **Tipo:** proceso\n", "0002-b.md": ADR}
    assert _codigos(validate_spec(_proyecto(tmp_path, adrs=adrs))) == []


def test_e12_adr_que_no_es_utf8(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path)
    (raiz / "docs" / "decisiones" / "0002-roto.md").write_bytes(b"\xff")
    assert _codigos(validate_spec(raiz)) == [
        ("E12", "docs/decisiones/0002-roto.md", "")
    ]


# ── Avisos ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("critica", [None, False])
def test_a01_motivo_critica_en_una_tarea_no_critica(
    tmp_path: Path, critica: bool | None
) -> None:
    def cambio(d: dict[str, Any]) -> None:
        d["tareas"][2]["motivo_critica"] = "Porque sí"
        if critica is not None:
            d["tareas"][2]["critica"] = critica

    informe = validate_spec(_proyecto(tmp_path, tareas=_con(cambio)))
    assert informe.ok
    assert _codigos(informe) == [("A01", TAREAS, "tareas[2].motivo_critica")]


def test_a01_no_salta_en_una_tarea_critica(tmp_path: Path) -> None:
    tareas = _con(lambda d: d["tareas"][0].update(critica=True, motivo_critica="Sí"))
    assert _codigos(validate_spec(_proyecto(tmp_path, tareas=tareas))) == []


PARALELO = TOML + "\n[autonomia]\nparalelismo = {}\n"


@pytest.mark.parametrize("paralelismo", [2, 10**30])
def test_a02_tarea_sin_area_con_paralelismo(tmp_path: Path, paralelismo: int) -> None:
    tareas = _con(lambda d: d["tareas"][0].pop("area"))
    raiz = _proyecto(tmp_path, tareas=tareas, toml=PARALELO.format(paralelismo))
    informe = validate_spec(raiz)
    assert _codigos(informe) == [("A02", TAREAS, "tareas[0]")]
    assert f"autonomia.paralelismo es {paralelismo}" in informe.warnings[0].message


def test_a02_no_salta_sin_paralelismo_ni_con_area_explicita(tmp_path: Path) -> None:
    sin_area = _con(lambda d: d["tareas"][0].pop("area"))
    assert _codigos(validate_spec(_proyecto(tmp_path / "a", tareas=sin_area))) == []
    con_general = _con(lambda d: d["tareas"][0].update(area="general"))
    raiz = _proyecto(tmp_path / "b", tareas=con_general, toml=PARALELO.format(3))
    assert _codigos(validate_spec(raiz)) == []


def test_a03_automatico_en_un_repo_privado(tmp_path: Path) -> None:
    toml = TOML.replace(
        'repo = "ejemplo/ejemplo"\n',
        'repo = "ejemplo/ejemplo"\nvisibilidad = "privado"\n',
    )
    raiz = _proyecto(tmp_path, toml=toml + '\n[modo]\ndefecto = "automatico"\n')
    assert _codigos(validate_spec(raiz)) == [("A03", "menairos.toml", "modo.defecto")]


def test_a03_codex_como_revisor_de_los_pr(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, toml=TOML + '\n[revisores]\npr = "codex"\n')
    informe = validate_spec(raiz)
    assert informe.ok
    assert _codigos(informe) == [("A03", "menairos.toml", "revisores.pr")]


@pytest.mark.parametrize(
    ("modo_tarea", "modo_proyecto", "salta"),
    [
        (None, "manual", False),
        (None, "didactico", True),
        (None, "automatico", True),
        ("didactico", "manual", True),
        ("automatico", "manual", True),
        ("manual", "didactico", False),
    ],
)
def test_a04_codex_fuera_del_modo_manual(
    tmp_path: Path, modo_tarea: str | None, modo_proyecto: str, salta: bool
) -> None:
    tareas = _con(lambda d: d["tareas"][1].update(quien="codex", modo=modo_tarea))
    toml = TOML + f'\n[modo]\ndefecto = "{modo_proyecto}"\n'
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas, toml=toml))
    esperado = [("A04", TAREAS, "tareas[1].quien")] if salta else []
    assert _codigos(informe) == esperado


def test_los_avisos_de_tareas_no_se_dan_con_las_tareas_invalidas(
    tmp_path: Path,
) -> None:
    tareas = _con(
        lambda d: (
            d["tareas"][0].update(motivo_critica="x", titulo=""),
            d["tareas"][1].update(quien="codex", modo="didactico"),
        )
    )
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas))
    assert [f.code for f in informe.errors] == ["E02"]
    assert informe.warnings == ()


def test_con_e01_sigue_a01_pero_no_a02_ni_a04(tmp_path: Path) -> None:
    tareas = _con(
        lambda d: (
            d["tareas"][0].update(motivo_critica="x"),
            d["tareas"][1].update(quien="codex", modo="didactico"),
            d["tareas"][2].pop("area"),
        )
    )
    raiz = _proyecto(tmp_path, tareas=tareas, toml=PARALELO.format(2) + "x = 1\n")
    informe = validate_spec(raiz)
    assert [f.code for f in informe.warnings] == ["A01"]


# ── Ficheros que faltan y elección del hito ─────────────────────────────────


@pytest.mark.parametrize(
    "falta",
    [
        "menairos.toml",
        "docs/specs/hito-1.md",
        "docs/abiertas.md",
        "docs/decisiones/",
    ],
)
def test_falta_un_fichero_es_un_error_de_uso(tmp_path: Path, falta: str) -> None:
    raiz = _proyecto(tmp_path)
    ruta = raiz / falta
    if ruta.is_dir():
        for hijo in ruta.iterdir():
            hijo.unlink()
        ruta.rmdir()
    else:
        ruta.unlink()
    with pytest.raises(UsageError, match=f"«{falta}»"):
        validate_spec(raiz)


def test_un_hito_que_no_existe_es_un_error_de_uso(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="«docs/specs/hito-7.tareas.yaml»"):
        validate_spec(_proyecto(tmp_path), milestone=7)


def test_sin_ningun_hito_es_un_error_de_uso(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path)
    (raiz / "docs" / "specs" / "hito-1.tareas.yaml").unlink()
    with pytest.raises(UsageError, match="no hay ningún docs/specs/hito-N.tareas.yaml"):
        validate_spec(raiz)


def test_una_raiz_que_no_existe_es_un_error_de_uso(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="no existe o no es una carpeta"):
        validate_spec(tmp_path / "no-existe")


def _del_hito(n: int) -> dict[str, Any]:
    """Las tareas base, del hito n y con los enlaces a hito-n.md."""

    def cambio(d: dict[str, Any]) -> None:
        d["hito"] = n
        for tarea in d["tareas"]:
            tarea["especificacion"] = [
                e.replace("hito-1.md", f"hito-{n}.md") for e in tarea["especificacion"]
            ]

    return _con(cambio)


def test_sin_hito_se_elige_el_mayor_como_numero(tmp_path: Path) -> None:
    raiz = _proyecto(tmp_path, hito=2, tareas=_del_hito(2))
    _proyecto(raiz, hito=10, tareas=_del_hito(10))
    (raiz / "docs" / "specs" / "hito-011.tareas.yaml").write_text("x", encoding="utf-8")
    informe = validate_spec(raiz)
    assert informe.milestone == 10
    assert informe.ok


def test_hito_enorme(tmp_path: Path) -> None:
    n = 10**30
    raiz = _proyecto(tmp_path, hito=n, tareas=_del_hito(n))
    informe = validate_spec(raiz)
    assert informe.milestone == n
    assert informe.ok
    assert validate_spec(raiz, milestone=n).ok


def test_los_errores_se_ordenan_por_codigo_y_fichero(tmp_path: Path) -> None:
    tareas = _con(
        lambda d: (
            d["tareas"][2].update(depende_de=["T-99"]),
            d["tareas"][1].update(especificacion=["no.md"]),
            d["tareas"][0].update(depende_de=["T-98"]),
        )
    )
    informe = validate_spec(_proyecto(tmp_path, tareas=tareas, adrs={}))
    assert _codigos(informe) == [
        ("E05", TAREAS, "tareas[0].depende_de[0]"),
        ("E05", TAREAS, "tareas[2].depende_de[0]"),
        ("E08", TAREAS, "tareas[1].especificacion[0]"),
        ("E12", "docs/decisiones/", ""),
    ]
