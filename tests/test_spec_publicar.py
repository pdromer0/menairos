"""Tests de `menairos spec publicar` (T-08): idempotencia y casos límite de 2.4.

Cada test copia el proyecto de ejemplo (tests/data/spec_publicar/ejemplo) a una
carpeta temporal y publica contra el doble de GitHub, conectado con la fixture
doble_github. Los datos son sintéticos.
"""

import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from doble_github import Call, FakeGitHub

from menairos.github import GitHub, Request, Response
from menairos.schemas import apply_defaults, load_document
from menairos.spec_publication import Publication, publish_spec
from menairos.task_issues import render

EJEMPLO = Path(__file__).resolve().parent / "data" / "spec_publicar" / "ejemplo"
REPO = "pdromer0/menairos-prueba"
YAML = "docs/specs/hito-0.tareas.yaml"
BASE = f"repos/{REPO}"

# La primera publicación del ejemplo: 3 lecturas y 21 escrituras (12 etiquetas, el
# milestone, 4 issues y 4 dependencias).
LLAMADAS_PRIMERA = 24


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    destino = tmp_path / "proyecto"
    shutil.copytree(EJEMPLO, destino)
    return destino


@pytest.fixture
def doble(doble_github: FakeGitHub) -> FakeGitHub:
    doble_github.repo = REPO
    return doble_github


# ── Ayudas ──────────────────────────────────────────────────────────────────


def publicar(raiz: Path, **opciones: Any) -> Publication:
    return publish_spec(raiz, **opciones)


def escrituras(doble: FakeGitHub, desde: int = 0) -> list[Call]:
    return [c for c in doble.calls[desde:] if c.method != "GET"]


def editar(raiz: Path, cambio: Callable[[dict[str, Any]], None]) -> None:
    ruta = raiz / YAML
    documento = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    cambio(documento)
    ruta.write_text(
        yaml.safe_dump(documento, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def tarea(documento: dict[str, Any], tid: str) -> dict[str, Any]:
    return next(t for t in documento["tareas"] if t["id"] == tid)


def numero(doble: FakeGitHub, tid: str) -> int:
    """El número del issue de una tarea, por su marca."""
    return next(
        n
        for n, issue in doble.issues.items()
        if issue.get("pull_request") is None
        and f"menairos:tarea={tid} hito=0 " in (issue["body"] or "")
    )


def issue(doble: FakeGitHub, tid: str) -> dict[str, Any]:
    return doble.issues[numero(doble, tid)]


def etiquetas(doble: FakeGitHub, tid: str) -> list[str]:
    return sorted(label["name"] for label in issue(doble, tid)["labels"])


def poner_etiquetas(doble: FakeGitHub, n: int, nombres: list[str]) -> None:
    """Cambia a mano las etiquetas de un issue (como Pedro en la web)."""
    for nombre in nombres:
        if not any(label["name"] == nombre for label in doble.labels):
            doble.add_label(nombre)
    doble.issues[n]["labels"] = [
        next(label for label in doble.labels if label["name"] == nombre)
        for nombre in nombres
    ]


def estado(doble: FakeGitHub) -> dict[str, Any]:
    """Todo lo que publicar deja en el doble, sin los id."""
    return {
        "etiquetas": [label["name"] for label in doble.labels],
        "milestones": [(m["number"], m["title"], m["state"]) for m in doble.milestones],
        "issues": {
            n: (
                i["title"],
                i["body"],
                sorted(label["name"] for label in i["labels"]),
                i["state"],
                (i["milestone"] or {}).get("number"),
            )
            for n, i in doble.issues.items()
        },
        "blocked_by": {n: list(v) for n, v in doble.blocked_by.items() if v},
    }


def codigos(lista: list[dict[str, Any]]) -> list[str]:
    return [item["codigo"] for item in lista]


def de_tipo(lista: list[dict[str, Any]], tipo: str) -> list[dict[str, Any]]:
    return [item for item in lista if item["tipo"] == tipo]


def cuerpo_generado(tid: str, raiz: Path = EJEMPLO) -> str:
    documento = apply_defaults("tareas", load_document(raiz / YAML))
    tareas = {t["id"]: t for t in documento["tareas"]}
    return render(tareas[tid], tareas, milestone=0, repo=REPO, tasks_file=YAML).body


def patch_de(doble: FakeGitHub, desde: int, n: int) -> dict[str, Any]:
    [patch] = [c for c in escrituras(doble, desde) if c.path == f"{BASE}/issues/{n}"]
    assert patch.method == "PATCH"
    return patch.body


# ── Tabla de idempotencia ───────────────────────────────────────────────────


def test_segunda_ejecucion_no_escribe_nada(raiz: Path, doble: FakeGitHub) -> None:
    primera = publicar(raiz)
    assert primera.ok and primera.writes == 21
    antes = len(doble.calls)
    segunda = publicar(raiz)
    assert segunda.ok, segunda.errors
    assert escrituras(doble, antes) == []
    assert len(doble.calls) - antes == 7  # 3 listas y 4 blocked_by
    assert (segunda.created, segunda.updated, segunda.removed) == ([], [], [])
    tipos = [item["tipo"] for item in segunda.unchanged]
    assert tipos.count("etiqueta") == 12
    assert tipos.count("milestone") == 1
    assert tipos.count("issue") == 4
    assert tipos.count("dependencia") == 4
    assert segunda.warnings == []


def test_tarea_nueva_crea_su_issue_y_sus_dependencias(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    editar(
        raiz,
        lambda d: d["tareas"].append(
            {
                "id": "T-05",
                "titulo": "Quinta",
                "rama": "feat/h0-quinta",
                "depende_de": ["T-04"],
                "area": "datos",
                "especificacion": ["hito-0.md#11-datos-de-ejemplo"],
                "criterios_aceptacion": ["Existe"],
            }
        ),
    )
    antes = len(doble.calls)
    resultado = publicar(raiz)
    nuevas = escrituras(doble, antes)
    assert [(c.method, c.path) for c in nuevas] == [
        ("POST", f"{BASE}/issues"),
        ("POST", f"{BASE}/issues/5/dependencies/blocked_by"),
    ]
    assert nuevas[0].body["milestone"] == 1
    assert nuevas[1].body == {"issue_id": doble.issues[4]["id"]}
    assert doble.blocked_by[5] == [4]
    assert [i["tarea"] for i in de_tipo(resultado.created, "issue")] == ["T-05"]


def test_misma_huella_no_toca_el_issue_editado_a_mano(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-01")
    doble.issues[n]["title"] = "Título cambiado por Pedro"
    doble.issues[n]["body"] = "Nota de Pedro\n\n" + doble.issues[n]["body"]
    poner_etiquetas(doble, n, ["en-curso", "modo:automatico"])
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert escrituras(doble, antes) == []
    assert {"tipo": "issue", "tarea": "T-01", "numero": n} | {
        "titulo": "T-01 · Datos de ejemplo"
    } in resultado.unchanged
    assert doble.issues[n]["title"] == "Título cambiado por Pedro"


@pytest.mark.parametrize(
    ("cambio", "campos", "cambios"),
    [
        ("titulo", {"title", "body"}, ["titulo"]),
        ("cuerpo", {"body"}, ["cuerpo"]),
        ("cuerpo-y-etiquetas", {"body", "labels"}, ["cuerpo", "etiquetas"]),
    ],
)
def test_tarea_cambiada_issue_abierto_actualiza_solo_lo_cambiado(
    raiz: Path, doble: FakeGitHub, cambio: str, campos: set[str], cambios: list[str]
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    cuerpo_antes = doble.issues[n]["body"]

    def cambiar(d: dict[str, Any]) -> None:
        t = tarea(d, "T-04")
        if cambio == "titulo":
            t["titulo"] = "Revisión con Codex, otra vez"
        elif cambio == "cuerpo":
            t["criterios_aceptacion"].append("Un criterio nuevo")
        else:
            t["critica"] = True
            t["motivo_critica"] = "Ahora es crítica"

    editar(raiz, cambiar)
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert resultado.ok, resultado.errors
    leidas = [c for c in doble.calls[antes:] if c.path == f"{BASE}/issues/{n}"]
    assert [c.method for c in leidas] == ["GET", "PATCH"]  # se relee antes del PATCH
    patch = patch_de(doble, antes, n)
    assert set(patch) == campos
    [actualizado] = resultado.updated
    assert (actualizado["tarea"], actualizado["cambios"]) == ("T-04", cambios)
    assert doble.issues[n]["body"] == cuerpo_generado("T-04", raiz)
    if cambio == "titulo":
        assert patch["body"] != cuerpo_antes  # solo cambia la marca
        assert patch["body"].split("<!--")[0] == cuerpo_antes.split("<!--")[0]
    if cambio == "cuerpo-y-etiquetas":
        assert etiquetas(doble, "T-04") == ["area:entorno", "critica", "tipo:tarea"]
    assert resultado.warnings == []
    antes = len(doble.calls)
    assert publicar(raiz).ok
    assert escrituras(doble, antes) == []


def test_cuerpo_a_mano_se_conserva_si_solo_cambia_el_titulo(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    editado = doble.issues[n]["body"].replace(
        "## Datos", "Nota de Pedro: ojo con la cuota.\n\n## Datos"
    )
    doble.issues[n]["body"] = editado
    editar(raiz, lambda d: tarea(d, "T-04").update(titulo="Otro título"))
    resultado = publicar(raiz)
    assert doble.issues[n]["title"] == "T-04 · Otro título"
    assert "Nota de Pedro: ojo con la cuota." in doble.issues[n]["body"]
    assert doble.issues[n]["body"].split("<!--")[0] == editado.split("<!--")[0]
    assert codigos(resultado.warnings) == []
    antes = len(doble.calls)
    publicar(raiz)
    assert escrituras(doble, antes) == []


def test_titulo_a_mano_se_conserva_si_solo_cambia_el_cuerpo(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["title"] = "El título de Pedro"
    editar(raiz, lambda d: tarea(d, "T-04")["criterios_aceptacion"].append("Otro"))
    antes = len(doble.calls)
    publicar(raiz)
    assert "title" not in patch_de(doble, antes, n)
    assert doble.issues[n]["title"] == "El título de Pedro"


def test_cuerpo_editado_a_mano_se_reescribe_con_aviso(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["body"] = doble.issues[n]["body"].replace("- [ ]", "- [x]")
    editar(raiz, lambda d: tarea(d, "T-04")["criterios_aceptacion"].append("Otro"))
    resultado = publicar(raiz)
    assert codigos(resultado.warnings) == ["cuerpo-reescrito"]
    assert resultado.warnings[0]["numero"] == n
    assert "cuerpo editado a mano" in resultado.warnings[0]["mensaje"]
    assert doble.issues[n]["body"] == cuerpo_generado("T-04", raiz)


def test_cuerpo_sin_editar_no_avisa(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    editar(raiz, lambda d: tarea(d, "T-04")["criterios_aceptacion"].append("Otro"))
    resultado = publicar(raiz)
    assert resultado.warnings == []
    assert [i["cambios"] for i in resultado.updated] == [["cuerpo"]]


def test_titulo_cambiado_a_mano_y_en_el_yaml_se_reescribe_con_aviso(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["title"] = "El título de Pedro"
    editar(raiz, lambda d: tarea(d, "T-04").update(titulo="Nuevo"))
    resultado = publicar(raiz)
    assert codigos(resultado.warnings) == ["titulo-reescrito"]
    assert doble.issues[n]["title"] == "T-04 · Nuevo"


class Entremedias:
    """Transporte que deja cambiar el doble justo antes de que se relea un issue."""

    def __init__(self, doble: FakeGitHub, antes_de_releer: Callable[[], None]) -> None:
        self.doble = doble
        self.antes_de_releer = antes_de_releer

    def send(self, request: Request, timeout: float) -> Response:
        if request.method == "GET" and re.fullmatch(
            rf"{BASE}/issues/[0-9]+", request.path
        ):
            self.antes_de_releer()
        return self.doble.send(request, timeout)


def test_el_patch_parte_del_issue_recien_leido(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    editar(
        raiz,
        lambda d: tarea(d, "T-04").update(critica=True, motivo_critica="Crítica"),
    )

    def pedro_trabaja() -> None:
        poner_etiquetas(
            doble,
            n,
            [*(label["name"] for label in doble.issues[n]["labels"]), "en-curso"],
        )

    cliente = GitHub(Entremedias(doble, pedro_trabaja), sleep=doble.sleeps.append)
    assert publish_spec(raiz, client=cliente).ok
    assert etiquetas(doble, "T-04") == [
        "area:entorno",
        "critica",
        "en-curso",
        "tipo:tarea",
    ]


def test_el_cuerpo_editado_durante_la_publicacion_no_se_pierde(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    editar(raiz, lambda d: tarea(d, "T-04").update(titulo="Otro"))

    def pedro_edita() -> None:
        doble.issues[n]["body"] = "Nota de última hora\n\n" + doble.issues[n]["body"]

    cliente = GitHub(Entremedias(doble, pedro_edita), sleep=doble.sleeps.append)
    assert publish_spec(raiz, client=cliente).ok
    assert doble.issues[n]["body"].startswith("Nota de última hora\n\n")


def test_tarea_cambiada_issue_cerrado_solo_avisa(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["state"] = "closed"

    def cambiar(d: dict[str, Any]) -> None:
        tarea(d, "T-04")["criterios_aceptacion"].append("Otro")
        tarea(d, "T-04")["depende_de"] = ["T-02"]

    editar(raiz, cambiar)
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert resultado.ok
    assert escrituras(doble, antes) == []
    assert codigos(resultado.warnings) == ["issue-cerrado"]
    assert (resultado.warnings[0]["tarea"], resultado.warnings[0]["numero"]) == (
        "T-04",
        n,
    )
    assert doble.blocked_by[n] == [numero(doble, "T-02"), numero(doble, "T-03")]


def test_tarea_borrada_solo_avisa(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    editar(raiz, lambda d: d["tareas"].remove(tarea(d, "T-04")))
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert escrituras(doble, antes) == []
    assert codigos(resultado.warnings) == ["tarea-borrada"]
    assert resultado.warnings[0]["numero"] == n
    assert doble.issues[n]["state"] == "open"


def test_dependencia_nueva_se_anade_con_el_id(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    editar(raiz, lambda d: tarea(d, "T-04")["depende_de"].append("T-01"))
    antes = len(doble.calls)
    publicar(raiz)
    n, uno = numero(doble, "T-04"), numero(doble, "T-01")
    [nueva] = [c for c in escrituras(doble, antes) if c.method == "POST"]
    assert nueva.path == f"{BASE}/issues/{n}/dependencies/blocked_by"
    assert nueva.body == {"issue_id": doble.issues[uno]["id"]}
    assert doble.issues[uno]["id"] != uno
    assert uno in doble.blocked_by[n]


def test_dependencia_quitada_se_quita(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    editar(raiz, lambda d: tarea(d, "T-04").update(depende_de=["T-02"]))
    antes = len(doble.calls)
    resultado = publicar(raiz)
    n, tres = numero(doble, "T-04"), numero(doble, "T-03")
    borrados = [c for c in escrituras(doble, antes) if c.method == "DELETE"]
    assert [c.path for c in borrados] == [
        f"{BASE}/issues/{n}/dependencies/blocked_by/{doble.issues[tres]['id']}"
    ]
    assert doble.blocked_by[n] == [numero(doble, "T-02")]
    assert resultado.removed == [
        {
            "tipo": "dependencia",
            "tarea": "T-04",
            "numero": n,
            "depende_de": "T-03",
            "bloqueado_por": tres,
        }
    ]


def test_dependencia_de_una_tarea_borrada_se_quita(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    tres = numero(doble, "T-03")

    def borrar(d: dict[str, Any]) -> None:
        d["tareas"].remove(tarea(d, "T-03"))
        tarea(d, "T-04")["depende_de"] = ["T-02"]

    editar(raiz, borrar)
    resultado = publicar(raiz)
    assert tres not in doble.blocked_by[numero(doble, "T-04")]
    assert codigos(resultado.warnings) == ["tarea-borrada"]
    assert [r["depende_de"] for r in resultado.removed] == ["T-03"]


def test_relaciones_ajenas_no_se_tocan(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n, tres = numero(doble, "T-04"), numero(doble, "T-03")
    bug = doble.add_issue("Un bug sin marca")
    doble.add_blocked_by(n, bug["number"])
    ajeno = doble.add_foreign_blocked_by(n, foreign_number=tres)
    editar(raiz, lambda d: tarea(d, "T-04").update(depende_de=["T-02"]))
    antes = len(doble.calls)
    publicar(raiz)
    borrados = [c.path for c in escrituras(doble, antes) if c.method == "DELETE"]
    assert borrados == [
        f"{BASE}/issues/{n}/dependencies/blocked_by/{doble.issues[tres]['id']}"
    ]
    assert doble.blocked_by[n] == [numero(doble, "T-02"), bug["number"]]
    assert doble.foreign_blocked_by[n] == [ajeno]
    antes = len(doble.calls)
    publicar(raiz)
    assert escrituras(doble, antes) == []


def test_dependencia_que_falta_se_completa_con_la_misma_huella(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n, dos = numero(doble, "T-04"), numero(doble, "T-02")
    doble.blocked_by[n].remove(dos)  # quitada a mano, o un fallo a mitad
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert [(c.method, c.body) for c in escrituras(doble, antes)] == [
        ("POST", {"issue_id": doble.issues[dos]["id"]})
    ]
    assert resultado.updated == []
    assert dos in doble.blocked_by[n]


def test_relacion_a_mano_entre_dos_tareas_se_quita(
    raiz: Path, doble: FakeGitHub
) -> None:
    """Las dependencias entre tareas del hito solo se gestionan en el YAML."""
    publicar(raiz)
    n, uno = numero(doble, "T-04"), numero(doble, "T-01")
    doble.add_blocked_by(n, uno)
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert [c.method for c in escrituras(doble, antes)] == ["DELETE"]
    assert uno not in doble.blocked_by[n]
    assert [r["depende_de"] for r in resultado.removed] == ["T-01"]


def test_modo_de_publicar_se_quita(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    assert etiquetas(doble, "T-03") == ["area:entorno", "modo:didactico", "tipo:tarea"]
    editar(raiz, lambda d: tarea(d, "T-03").update(modo=None))
    resultado = publicar(raiz)
    assert etiquetas(doble, "T-03") == ["area:entorno", "tipo:tarea"]
    assert resultado.warnings == []


def test_modo_de_publicar_se_cambia_por_el_nuevo(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    editar(raiz, lambda d: tarea(d, "T-03").update(modo="automatico"))
    publicar(raiz)
    assert etiquetas(doble, "T-03") == ["area:entorno", "modo:automatico", "tipo:tarea"]


def test_modo_puesto_a_mano_no_se_toca(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    poner_etiquetas(
        doble, n, ["area:entorno", "en-curso", "modo:automatico", "tipo:tarea"]
    )
    editar(
        raiz,
        lambda d: tarea(d, "T-04").update(critica=True, motivo_critica="Crítica"),
    )
    resultado = publicar(raiz)
    assert etiquetas(doble, "T-04") == [
        "area:entorno",
        "critica",
        "en-curso",
        "modo:automatico",
        "tipo:tarea",
    ]
    assert resultado.warnings == []


def test_sin_deducir_las_etiquetas_de_antes_un_modo_es_de_pedro(
    raiz: Path, doble: FakeGitHub
) -> None:
    """El área vieja ya no está en el YAML ni en el issue: la huella no basta."""
    publicar(raiz)
    n = numero(doble, "T-04")
    poner_etiquetas(doble, n, ["en-curso", "modo:automatico", "tipo:tarea"])

    def cambiar(d: dict[str, Any]) -> None:
        tarea(d, "T-04").update(area="nueva", critica=True, motivo_critica="Crítica")
        tarea(d, "T-03").update(area="otra")

    editar(raiz, cambiar)
    publicar(raiz)
    assert etiquetas(doble, "T-04") == [
        "area:nueva",
        "critica",
        "en-curso",
        "modo:automatico",
        "tipo:tarea",
    ]


def test_choque_de_modo_avisa_y_converge(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-01")
    poner_etiquetas(doble, n, ["area:datos", "modo:manual", "tipo:tarea"])
    editar(raiz, lambda d: tarea(d, "T-01").update(modo="didactico"))
    resultado = publicar(raiz)
    assert codigos(resultado.warnings) == ["modo-a-mano"]
    assert etiquetas(doble, "T-01") == ["area:datos", "modo:manual", "tipo:tarea"]
    antes = len(doble.calls)
    otra = publicar(raiz)
    assert escrituras(doble, antes) == []
    assert otra.warnings == []


def test_critica_y_areas_de_mas_se_quitan_aunque_la_huella_las_deduzca(
    raiz: Path, doble: FakeGitHub
) -> None:
    """tipo:tarea, critica y area:* son siempre de publicar (3.4; revisión de T-08)."""
    publicar(raiz)
    n = numero(doble, "T-01")
    poner_etiquetas(
        doble, n, ["area:datos", "area:vieja", "critica", "en-curso", "tipo:tarea"]
    )
    editar(raiz, lambda d: tarea(d, "T-01").update(area="nueva"))
    publicar(raiz)
    assert etiquetas(doble, "T-01") == ["area:nueva", "en-curso", "tipo:tarea"]


def test_issue_cerrado_durante_la_publicacion_no_toca_sus_dependencias(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")

    def cambiar(d: dict[str, Any]) -> None:
        tarea(d, "T-04").update(depende_de=["T-02", "T-01"])

    editar(raiz, cambiar)

    def pedro_cierra() -> None:
        doble.issues[n]["state"] = "closed"

    antes = len(doble.calls)
    cliente = GitHub(Entremedias(doble, pedro_cierra), sleep=doble.sleeps.append)
    resultado = publish_spec(raiz, client=cliente)
    assert resultado.ok
    assert escrituras(doble, antes) == []
    assert codigos(resultado.warnings) == ["issue-cambiado"]
    assert doble.blocked_by[n] == [numero(doble, "T-02"), numero(doble, "T-03")]


# ── Casos límite de 2.4 ─────────────────────────────────────────────────────


def test_repo_sin_etiquetas_ni_milestone_y_orden_de_las_escrituras(
    raiz: Path, doble: FakeGitHub
) -> None:
    resultado = publicar(raiz)
    assert resultado.ok
    rutas = [c.path.removeprefix(f"{BASE}/") for c in escrituras(doble)]
    assert rutas == [
        *["labels"] * 12,
        "milestones",
        *["issues"] * 4,
        "issues/2/dependencies/blocked_by",
        "issues/3/dependencies/blocked_by",
        "issues/4/dependencies/blocked_by",
        "issues/4/dependencies/blocked_by",
    ]
    assert [label["name"] for label in doble.labels][-2:] == [
        "area:datos",
        "area:entorno",
    ]
    assert doble.milestones[0]["title"] == "Hito 0 — Ejemplo de spec publicar (T-08)"
    assert all(i["milestone"]["number"] == 1 for i in doble.issues.values())
    assert doble.blocked_by == {2: [1], 3: [1], 4: [2, 3]}
    assert doble.sleeps == [1.0] * 20  # una pausa entre cada dos escrituras


def test_titulo_cambiado_se_reconoce_por_la_marca(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    doble.issues[numero(doble, "T-01")]["title"] = "Otro título"
    antes = len(doble.calls)
    publicar(raiz)
    assert escrituras(doble, antes) == []
    assert len(doble.issues) == 4


def test_marca_repetida_para_sin_escribir(raiz: Path, doble: FakeGitHub) -> None:
    cuerpo = cuerpo_generado("T-01")
    doble.add_issue("Uno", cuerpo)
    doble.add_issue("Otro", cuerpo)
    resultado = publicar(raiz)
    assert not resultado.ok
    assert codigos(resultado.errors) == ["marca-repetida"]
    assert "#1 y #2" in resultado.errors[0]["mensaje"]
    assert "No se ha escrito nada" in resultado.errors[0]["mensaje"]
    assert escrituras(doble) == []
    assert len(doble.calls) == 3


def test_cuerpo_con_dos_marcas_para_sin_escribir(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_issue("Dos", cuerpo_generado("T-01") + "\n" + cuerpo_generado("T-02"))
    resultado = publicar(raiz)
    assert codigos(resultado.errors) == ["marca-repetida"]
    assert escrituras(doble) == []


def test_pr_y_otro_hito_con_la_marca_se_ignoran(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_issue("Un PR", cuerpo_generado("T-01"), pull_request=True)
    doble.add_issue("Otro hito", "<!-- menairos:tarea=T-01 hito=1 -->")
    resultado = publicar(raiz)
    assert resultado.ok
    assert [i["tarea"] for i in de_tipo(resultado.created, "issue")] == [
        "T-01",
        "T-02",
        "T-03",
        "T-04",
    ]


@pytest.mark.parametrize("apply", [False, True], ids=["sin-guardar", "guardada"])
@pytest.mark.parametrize("llamada", range(1, LLAMADAS_PRIMERA + 1))
def test_fallo_en_la_llamada_n_de_una_publicacion_nueva(
    raiz: Path, doble: FakeGitHub, llamada: int, apply: bool
) -> None:
    limpio = FakeGitHub(REPO)
    publish_spec(raiz, client=GitHub(limpio, sleep=limpio.sleeps.append))
    assert len(limpio.calls) == LLAMADAS_PRIMERA

    doble.fail(502, call=llamada, apply=apply)
    primera = publicar(raiz)
    escritura = doble.calls[llamada - 1].method != "GET"
    assert primera.ok is not escritura
    if escritura:
        assert codigos(primera.errors) == ["github"]
        assert "resultado desconocido" in primera.errors[0]["mensaje"]
    assert publicar(raiz).ok
    assert estado(doble) == estado(limpio)
    antes = len(doble.calls)
    assert publicar(raiz).ok
    assert escrituras(doble, antes) == []


def _cambios_de_actualizacion(d: dict[str, Any]) -> None:
    tarea(d, "T-04")["titulo"] = "Revisión final"
    tarea(d, "T-01")["criterios_aceptacion"].append("Un criterio más")
    tarea(d, "T-02")["area"] = "lectura"
    tarea(d, "T-04")["depende_de"] = ["T-02", "T-01"]
    d["tareas"].append(
        {
            "id": "T-05",
            "titulo": "Quinta",
            "rama": "feat/h0-quinta",
            "depende_de": ["T-02"],
            "area": "datos",
            "especificacion": ["hito-0.md"],
            "criterios_aceptacion": ["Existe"],
        }
    )


def test_fallo_en_la_llamada_n_de_una_actualizacion(raiz: Path) -> None:
    """Para cada llamada de una actualización, un 502 con y sin la escritura hecha."""
    limpio = FakeGitHub(REPO)
    cliente = GitHub(limpio, sleep=limpio.sleeps.append)
    publish_spec(raiz, client=cliente)
    editar(raiz, _cambios_de_actualizacion)
    antes = len(limpio.calls)
    assert publish_spec(raiz, client=cliente).ok
    llamadas = len(limpio.calls) - antes
    metodos = {c.method for c in limpio.calls[antes:]}
    assert metodos == {"GET", "POST", "PATCH", "DELETE"}
    original = raiz.parent / "original"
    shutil.copytree(EJEMPLO, original)

    for apply in (False, True):
        for llamada in range(1, llamadas + 1):
            doble = FakeGitHub(REPO)
            cli = GitHub(doble, sleep=doble.sleeps.append)
            assert publish_spec(original, client=cli).ok
            doble.fail(502, call=len(doble.calls) + llamada, apply=apply)
            publish_spec(raiz, client=cli)
            caso = f"llamada {llamada}, apply={apply}"
            assert publish_spec(raiz, client=cli).ok, caso
            assert estado(doble) == estado(limpio), caso
            n = len(doble.calls)
            assert publish_spec(raiz, client=cli).ok, caso
            assert escrituras(doble, n) == [], caso


def test_mas_de_100_issues_y_etiquetas(raiz: Path, doble: FakeGitHub) -> None:
    for i in range(101):
        doble.add_label(f"otra-{i:03d}")
    doble.add_label("tipo:tarea")
    doble.add_label("area:datos")
    for i in range(40):
        doble.add_label(f"mas-{i:03d}")
    uno = doble.add_issue(
        "Lo que sea", cuerpo_generado("T-01"), ["tipo:tarea", "area:datos"]
    )
    for i in range(150):
        doble.add_issue(f"Ajeno {i}", pull_request=i % 3 == 0)
    resultado = publicar(raiz)
    assert resultado.ok
    creadas = [c.body["name"] for c in escrituras(doble) if c.path == f"{BASE}/labels"]
    assert "tipo:tarea" not in creadas and "area:datos" not in creadas
    assert len(creadas) == 10
    issues_creados = [
        c.body["title"] for c in escrituras(doble) if c.path == f"{BASE}/issues"
    ]
    assert issues_creados == [
        "T-02 · Lectura de los datos",
        "T-03 · Entorno local",
        "T-04 · Revisión con Codex",
    ]
    assert doble.blocked_by[numero(doble, "T-02")] == [uno["number"]]
    assert len(doble.calls_to("GET", rf"{BASE}/issues")) == 2
    assert len(doble.calls_to("GET", rf"{BASE}/labels")) == 2


def test_dependencia_a_un_issue_cerrado_se_crea_una_vez(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    uno = numero(doble, "T-01")
    doble.issues[uno]["state"] = "closed"
    editar(raiz, lambda d: tarea(d, "T-04")["depende_de"].append("T-01"))
    publicar(raiz)
    assert uno in doble.blocked_by[numero(doble, "T-04")]
    antes = len(doble.calls)
    assert publicar(raiz).ok
    assert escrituras(doble, antes) == []


# ── Más casos límite del plan ───────────────────────────────────────────────


def test_cuerpo_con_crlf_se_reconoce(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    for i in doble.issues.values():  # como los guarda la web: CRLF, también al final
        i["body"] = i["body"].replace("\n", "\r\n") + "\r\n"
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert escrituras(doble, antes) == []
    assert len(doble.issues) == 4
    assert resultado.warnings == []


def test_cuerpo_con_crlf_no_cuenta_como_editado(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["body"] = doble.issues[n]["body"].replace("\n", "\r\n")
    editar(raiz, lambda d: tarea(d, "T-04")["criterios_aceptacion"].append("Otro"))
    assert publicar(raiz).warnings == []


@pytest.mark.parametrize("estado_issue", ["open", "closed"])
def test_marca_ilegible(raiz: Path, doble: FakeGitHub, estado_issue: str) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    cuerpo = doble.issues[n]["body"]
    doble.issues[n]["body"] = re.sub(r"huella=\S+", "huella=rota", cuerpo)
    doble.issues[n]["state"] = estado_issue
    poner_etiquetas(doble, n, ["area:entorno", "modo:manual", "tipo:tarea"])
    resultado = publicar(raiz)
    if estado_issue == "closed":
        assert codigos(resultado.warnings) == ["issue-cerrado"]
        assert "huella=rota" in doble.issues[n]["body"]
        return
    assert codigos(resultado.warnings) == ["marca-ilegible"]
    assert doble.issues[n]["body"] == cuerpo_generado("T-04")
    assert "modo:manual" in etiquetas(doble, "T-04")  # se trata como puesto a mano
    antes = len(doble.calls)
    publicar(raiz)
    assert escrituras(doble, antes) == []


def test_marca_ilegible_con_el_titulo_a_mano_avisa(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    n = numero(doble, "T-04")
    doble.issues[n]["body"] = re.sub(
        r"huella=\S+", "huella=rota", doble.issues[n]["body"]
    )
    doble.issues[n]["title"] = "El título de Pedro"
    resultado = publicar(raiz)
    assert codigos(resultado.warnings) == ["marca-ilegible", "titulo-reescrito"]
    assert doble.issues[n]["title"] == "T-04 · Revisión con Codex"


def test_cuerpo_none_en_un_issue_ajeno(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_issue("Sin cuerpo")
    assert doble.issues[1]["body"] is None
    assert publicar(raiz).ok


def test_etiqueta_existente_con_otras_mayusculas(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_label("Critica")
    doble.add_label("TIPO:TAREA")
    publicar(raiz)
    creadas = [c.body["name"] for c in escrituras(doble) if c.path == f"{BASE}/labels"]
    assert "critica" not in creadas and "tipo:tarea" not in creadas
    assert etiquetas(doble, "T-02") == ["Critica", "TIPO:TAREA", "area:datos"]
    editar(raiz, lambda d: tarea(d, "T-02").update(area="otra"))
    publicar(raiz)
    assert etiquetas(doble, "T-02") == ["Critica", "TIPO:TAREA", "area:otra"]
    antes = len(doble.calls)
    publicar(raiz)
    assert escrituras(doble, antes) == []


def test_milestone_cerrado_se_usa_con_aviso(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_milestone("Hito 0 — Ejemplo de spec publicar (T-08)", state="closed")
    resultado = publicar(raiz)
    assert resultado.ok
    assert codigos(resultado.warnings) == ["milestone-cerrado"]
    assert len(doble.milestones) == 1
    assert all(i["milestone"]["number"] == 1 for i in doble.issues.values())


def test_milestone_con_otras_mayusculas_se_usa(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_milestone("  hito 0 — ejemplo de spec publicar (t-08) ")
    assert publicar(raiz).ok
    assert len(doble.milestones) == 1


def test_sin_issues_nuevos_no_se_crea_el_milestone(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    editar(raiz, lambda d: d.update(titulo="Hito 0 — Otro título"))
    antes = len(doble.calls)
    assert publicar(raiz).ok
    assert escrituras(doble, antes) == []
    assert len(doble.milestones) == 1


def test_titulo_del_hito_nuevo_con_una_tarea_nueva(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    editar(raiz, lambda d: d.update(titulo="Hito 0 — Otro título"))
    editar(raiz, _cambios_de_actualizacion)
    publicar(raiz)
    assert [m["title"] for m in doble.milestones] == [
        "Hito 0 — Ejemplo de spec publicar (T-08)",
        "Hito 0 — Otro título",
    ]
    assert issue(doble, "T-05")["milestone"]["number"] == 2
    assert issue(doble, "T-01")["milestone"]["number"] == 1


def test_dependencia_hacia_delante(raiz: Path, doble: FakeGitHub) -> None:
    def mover(d: dict[str, Any]) -> None:
        primera = tarea(d, "T-01")
        d["tareas"].remove(primera)
        d["tareas"].append(primera)

    editar(raiz, mover)
    assert publicar(raiz).ok
    assert doble.blocked_by[numero(doble, "T-02")] == [numero(doble, "T-01")]


def test_posible_duplicado(raiz: Path, doble: FakeGitHub) -> None:
    doble.add_issue("T-01 · Datos de ejemplo", "Sin marca")
    resultado = publicar(raiz)
    assert codigos(resultado.warnings) == ["posible-duplicado"]
    assert resultado.warnings[0]["numero"] == 1
    assert len(de_tipo(resultado.created, "issue")) == 4


@pytest.mark.parametrize("limite", ["area", "titulo", "cuerpo"])
def test_un_limite_de_github_no_escribe_nada(
    raiz: Path, doble: FakeGitHub, limite: str
) -> None:
    def pasar(d: dict[str, Any]) -> None:
        t = tarea(d, "T-04")
        if limite == "area":
            t["area"] = "a" * 46  # area: + 46 = 51
        elif limite == "titulo":
            t["titulo"] = "t" * 250
        else:
            t["criterios_aceptacion"] = ["c" * 66000]

    editar(raiz, pasar)
    resultado = publicar(raiz)
    assert codigos(resultado.errors) == ["limite"]
    assert doble.calls == []


def test_area_en_el_limite_se_publica(raiz: Path, doble: FakeGitHub) -> None:
    editar(raiz, lambda d: tarea(d, "T-04").update(area="a" * 45))
    assert publicar(raiz).ok


def test_spec_con_errores_no_llama_a_github(raiz: Path, doble: FakeGitHub) -> None:
    editar(raiz, lambda d: tarea(d, "T-04")["depende_de"].append("T-99"))
    resultado = publicar(raiz)
    assert codigos(resultado.errors) == ["E05"]
    assert resultado.errors[0]["fichero"] == YAML
    assert doble.calls == []


def test_un_404_al_leer_no_escribe_nada(raiz: Path, doble: FakeGitHub) -> None:
    doble.fail(404, call=1)
    resultado = publicar(raiz)
    assert codigos(resultado.errors) == ["github"]
    assert "No se ha escrito nada" in resultado.errors[0]["mensaje"]
    assert len(doble.calls) == 1


def test_limite_de_uso_a_mitad_y_la_siguiente_completa(
    raiz: Path, doble: FakeGitHub
) -> None:
    doble.fail(
        403,
        call=10,
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1893456000"},
        body={"message": "API rate limit exceeded"},
    )
    primera = publicar(raiz)
    assert codigos(primera.errors) == ["github"]
    assert "Límite de uso" in primera.errors[0]["mensaje"]
    assert publicar(raiz).ok
    assert len(doble.issues) == 4 and len(doble.labels) == 12


def test_un_4xx_en_una_escritura_dice_que_no_se_guardo(
    raiz: Path, doble: FakeGitHub
) -> None:
    doble.fail(422, call=4)  # la primera etiqueta
    resultado = publicar(raiz)
    [error] = resultado.errors
    assert "No se guardó: crear la etiqueta «tipo:tarea»" in error["mensaje"]
    assert "resultado desconocido" not in error["mensaje"]
    assert publicar(raiz).ok


def test_una_peticion_que_rechaza_el_cliente_es_un_error_y_no_una_traza(
    raiz: Path, doble: FakeGitHub
) -> None:
    fuera = '<https://otro.example/repos/x/y/issues?page=2>; rel="next"'
    doble.fail(200, call=3, headers={"Link": fuera}, body=[])
    resultado = publicar(raiz)
    assert codigos(resultado.errors) == ["github"]
    assert "rechazó una petición antes de enviarla" in resultado.errors[0]["mensaje"]
    assert "No se ha escrito nada" in resultado.errors[0]["mensaje"]
    assert escrituras(doble) == []


def test_un_bug_que_cita_el_cuerpo_de_un_issue_no_se_lleva_su_marca(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    citado = issue(doble, "T-01")["body"]
    doble.add_issue("Un bug", f"Al publicar sale esto:\n\n```\n{citado}\n```\n")
    antes = len(doble.calls)
    resultado = publicar(raiz)
    assert resultado.ok
    assert escrituras(doble, antes) == []


def test_seco_no_escribe(raiz: Path, doble: FakeGitHub) -> None:
    resultado = publicar(raiz, dry_run=True)
    assert resultado.ok and resultado.dry_run
    assert escrituras(doble) == []
    assert len(doble.calls) == 3
    assert resultado.writes == 21
    assert [i["numero"] for i in de_tipo(resultado.created, "issue")] == [None] * 4
    assert de_tipo(resultado.created, "milestone") == [
        {
            "tipo": "milestone",
            "titulo": "Hito 0 — Ejemplo de spec publicar (T-08)",
            "numero": None,
        }
    ]
    assert de_tipo(resultado.created, "dependencia")[0] == {
        "tipo": "dependencia",
        "tarea": "T-02",
        "numero": None,
        "depende_de": "T-01",
        "bloqueado_por": None,
    }


def test_seco_con_cambios_dice_lo_que_haria(raiz: Path, doble: FakeGitHub) -> None:
    publicar(raiz)
    editar(raiz, _cambios_de_actualizacion)
    antes = len(doble.calls)
    seco = publicar(raiz, dry_run=True)
    assert escrituras(doble, antes) == []
    real = publicar(raiz)
    assert (seco.updated, seco.removed) == (real.updated, real.removed)
    assert seco.warnings == real.warnings

    def resumen(lista: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [
            (i["tipo"], i.get("tarea"), i.get("nombre"), i.get("depende_de"))
            for i in lista
        ]

    assert resumen(seco.created) == resumen(real.created)
    assert [i["tarea"] for i in de_tipo(seco.created, "issue")] == ["T-05"]


def test_area_nueva_crea_su_etiqueta_y_cambia_la_del_issue(
    raiz: Path, doble: FakeGitHub
) -> None:
    publicar(raiz)
    editar(raiz, lambda d: tarea(d, "T-02").update(area="lectura"))
    resultado = publicar(raiz)
    assert de_tipo(resultado.created, "etiqueta") == [
        {"tipo": "etiqueta", "nombre": "area:lectura"}
    ]
    assert etiquetas(doble, "T-02") == ["area:lectura", "critica", "tipo:tarea"]
    assert any(label["name"] == "area:datos" for label in doble.labels)


def test_avisos_de_spec_validar_se_incluyen(raiz: Path, doble: FakeGitHub) -> None:
    editar(raiz, lambda d: tarea(d, "T-01").update(motivo_critica="Sin ser crítica"))
    resultado = publicar(raiz)
    assert resultado.ok
    assert codigos(resultado.warnings) == ["A01"]


# ── La orden de la CLI ──────────────────────────────────────────────────────


def _cli(raiz: Path, *opciones: str) -> int:
    from menairos.cli import main

    return main(["spec", "publicar", "--raiz", str(raiz), *opciones])


def test_cli_json_y_segunda_ejecucion(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    assert _cli(raiz, "--json") == 0
    salida = json.loads(capsys.readouterr().out)
    assert list(salida) == [
        "ok",
        "seco",
        "repo",
        "hito",
        "creados",
        "actualizados",
        "quitados",
        "sin_cambios",
        "avisos",
        "errores",
    ]
    assert (salida["ok"], salida["seco"], salida["repo"], salida["hito"]) == (
        True,
        False,
        REPO,
        0,
    )
    assert len(salida["creados"]) == 21
    assert _cli(raiz, "--json") == 0
    segunda = json.loads(capsys.readouterr().out)
    assert (segunda["creados"], segunda["actualizados"], segunda["quitados"]) == (
        [],
        [],
        [],
    )
    assert len(segunda["sin_cambios"]) == 21


def test_cli_json_conserva_los_acentos(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(raiz, "--json", "--seco") == 0
    salida = capsys.readouterr().out
    assert "Revisión con Codex" in salida and "\\u" not in salida


def test_cli_seco_legible(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(raiz, "--seco") == 0
    salida = capsys.readouterr().out
    assert escrituras(doble) == []
    lineas = salida.splitlines()
    assert lineas[:2] == [
        "spec publicar · hito 0 · pdromer0/menairos-prueba",
        "En seco: no se escribe nada en GitHub; esto es lo que haría.",
    ]
    assert "Se crearían (21):" in lineas
    assert "  etiqueta     tipo:tarea" in lineas
    assert "  milestone    (nuevo) Hito 0 — Ejemplo de spec publicar (T-08)" in lineas
    assert "  issue        (nuevo) T-02 · Lectura de los datos" in lineas
    assert "  dependencia  (nuevo) T-02 depende de (nuevo) T-01" in lineas
    assert lineas[-1] == "Resultado: haría 21 escrituras."


def test_cli_legible_con_cambios_y_avisos(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(raiz) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "Resultado: 21 escrituras."
    doble.issues[numero(doble, "T-03")]["state"] = "closed"

    def cambiar(d: dict[str, Any]) -> None:
        tarea(d, "T-03")["criterios_aceptacion"].append("Otro")
        tarea(d, "T-04").update(depende_de=["T-02"], titulo="Revisión final")

    editar(raiz, cambiar)
    assert _cli(raiz) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert "Actualizados (1):" in lineas
    assert "  issue        #4 T-04 · Revisión final  (titulo, cuerpo)" in lineas
    assert "Quitados (1):" in lineas
    assert "  dependencia  #4 T-04 ya no depende de #3 T-03" in lineas
    assert (
        # Las dependencias del issue cerrado (T-03) no se leen ni se cuentan.
        "Sin cambios: 12 etiquetas, 1 milestone, 2 issues y 2 dependencias." in lineas
    )
    assert "  issue-cerrado  T-03  #3" in lineas
    assert lineas[-1] == "Resultado: 2 escrituras."


def test_cli_errores_de_la_spec_salen_con_1(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    editar(raiz, lambda d: tarea(d, "T-04")["depende_de"].append("T-99"))
    assert _cli(raiz) == 1
    lineas = capsys.readouterr().out.splitlines()
    assert "Errores (1):" in lineas
    assert "  E05  docs/specs/hito-0.tareas.yaml  tareas[3].depende_de[2]" in lineas
    assert lineas[-1] == "Resultado: con errores, tras ninguna escritura."
    assert doble.calls == []


def test_cli_fallo_de_github_sale_con_1(
    raiz: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    doble.fail(502, call=5)
    assert _cli(raiz, "--json") == 1
    import json

    salida = json.loads(capsys.readouterr().out)
    assert salida["ok"] is False
    assert [e["codigo"] for e in salida["errores"]] == ["github"]
    assert len(salida["creados"]) == 1  # la etiqueta de la llamada 4


def test_cli_error_de_uso_sale_con_2(
    tmp_path: Path, doble: FakeGitHub, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(tmp_path / "no-existe") == 2
    salida = capsys.readouterr()
    assert salida.out == ""
    assert salida.err.startswith("menairos spec publicar: error: la raíz")
    assert doble.calls == []
