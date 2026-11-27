"""Tests del doble de GitHub (T-07): paginación, fidelidad, fallos programables y tope.

Se prueban a través del envoltorio real (menairos.github.GitHub), como lo usarán
T-08, T-12, T-19, T-23 y T-24. Los datos son sintéticos.
"""

import re

import pytest
from doble_github import Call, FakeGitHub, RunawayLoop, UnsupportedRoute

from menairos.github import GitHub, GitHubError, RateLimited

REPO = "repos/ejemplo/ejemplo"


def _cliente(doble: FakeGitHub) -> GitHub:
    return GitHub(doble, sleep=doble.sleeps.append)


# ── Paginación ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("etiquetas", "llamadas"), [(0, 1), (100, 1), (101, 2), (250, 3)]
)
def test_get_all_pagina_de_100_en_100(etiquetas: int, llamadas: int) -> None:
    doble = FakeGitHub()
    nombres = [f"etiqueta-{i:03d}" for i in range(etiquetas)]
    for nombre in nombres:
        doble.add_label(nombre)
    assert [e["name"] for e in _cliente(doble).get_all(f"{REPO}/labels")] == nombres
    assert len(doble.calls) == llamadas
    assert doble.calls[0].query == {"per_page": "100"}


def test_el_link_tiene_la_forma_que_da_github() -> None:
    """Como en la comprobación real de T-07: repositories/{id}, prev/next/last/first."""
    doble = FakeGitHub(repo_id=1234)
    for i in range(5):
        doble.add_label(f"e{i}")
    cli = _cliente(doble)
    base = "https://api.github.com/repositories/1234/labels?per_page=2&page="
    primera = cli.request("GET", f"{REPO}/labels", params={"per_page": 2})
    assert primera.header("link") == f'<{base}2>; rel="next", <{base}3>; rel="last"'
    media = cli.request("GET", f"{REPO}/labels", params={"per_page": 2, "page": 2})
    assert media.header("link") == (
        f'<{base}1>; rel="prev", <{base}3>; rel="next", <{base}3>; rel="last", '
        f'<{base}1>; rel="first"'
    )
    ultima = cli.request("GET", f"{REPO}/labels", params={"per_page": 2, "page": 3})
    assert ultima.header("link") == f'<{base}2>; rel="prev", <{base}1>; rel="first"'
    assert [e["name"] for e in ultima.data] == ["e4"]


def test_get_all_sigue_las_urls_de_repositories_y_el_doble_las_normaliza() -> None:
    doble = FakeGitHub()
    for i in range(5):
        doble.add_label(f"e{i}")
    assert len(_cliente(doble).get_all(f"{REPO}/labels", {"per_page": 2})) == 5
    assert [c.describe() for c in doble.calls] == [
        f"GET {REPO}/labels?per_page=2",
        f"GET {REPO}/labels?per_page=2&page=2",
        f"GET {REPO}/labels?per_page=2&page=3",
    ]


def test_una_sola_pagina_no_lleva_link() -> None:
    doble = FakeGitHub()
    doble.add_label("a")
    assert _cliente(doble).request("GET", f"{REPO}/labels").header("link") is None


def test_per_page_por_defecto_30_y_como_maximo_100() -> None:
    doble = FakeGitHub()
    for i in range(150):
        doble.add_label(f"e{i}")
    cli = _cliente(doble)
    assert len(cli.get(f"{REPO}/labels")) == 30
    assert len(cli.get(f"{REPO}/labels", {"per_page": 500})) == 100


def test_get_all_con_mas_de_100_issues_y_los_filtros_en_cada_pagina() -> None:
    doble = FakeGitHub()
    doble.add_label("tipo:tarea")
    for i in range(1, 231):
        doble.add_issue(
            f"T-{i:02d}", labels=["tipo:tarea"], state="closed" if i % 2 else "open"
        )
    issues = _cliente(doble).get_all(f"{REPO}/issues", {"state": "all"})
    assert len(issues) == 230
    assert [i["number"] for i in issues] == list(range(230, 0, -1))
    assert len(doble.calls) == 3
    assert all(c.query["state"] == "all" for c in doble.calls)


# ── Fidelidad ──────────────────────────────────────────────────────────────


def test_el_id_nunca_es_el_numero() -> None:
    doble = FakeGitHub()
    doble.add_label("a")
    doble.add_milestone("Hito 0 — Núcleo")
    issues = [doble.add_issue(f"T-0{i}") for i in range(1, 4)]
    assert all(i["id"] != i["number"] for i in issues)
    ids = [doble.labels[0]["id"], doble.milestones[0]["id"], *[i["id"] for i in issues]]
    assert len(set(ids)) == len(ids)
    assert all(ident > 1000 for ident in ids)


def test_issues_y_milestones_solo_abiertos_si_no_se_pide_state() -> None:
    doble = FakeGitHub()
    doble.add_issue("abierto")
    doble.add_issue("cerrado", state="closed")
    doble.add_issue("un PR", pull_request=True)
    doble.add_milestone("Hito 0", state="closed")
    cli = _cliente(doble)
    assert [i["title"] for i in cli.get_all(f"{REPO}/issues")] == ["un PR", "abierto"]
    todos = cli.get_all(f"{REPO}/issues", {"state": "all"})
    assert [i["title"] for i in todos] == ["un PR", "cerrado", "abierto"]
    assert "pull_request" in todos[0] and "pull_request" not in todos[1]
    assert cli.get_all(f"{REPO}/milestones") == []
    assert [
        m["title"] for m in cli.get_all(f"{REPO}/milestones", {"state": "all"})
    ] == ["Hito 0"]


def test_filtro_de_issues_por_etiquetas() -> None:
    doble = FakeGitHub()
    for nombre in ("tipo:tarea", "critica"):
        doble.add_label(nombre)
    doble.add_issue("a", labels=["tipo:tarea"])
    doble.add_issue("b", labels=["tipo:tarea", "critica"])
    issues = _cliente(doble).get_all(f"{REPO}/issues", {"labels": "tipo:tarea,critica"})
    assert [i["title"] for i in issues] == ["b"]


def test_crear_una_etiqueta_y_repetirla_en_otras_mayusculas_da_422() -> None:
    doble = FakeGitHub()
    cli = _cliente(doble)
    creada = cli.post(f"{REPO}/labels", {"name": "area:contratos", "color": "c5def5"})
    assert (creada["name"], creada["color"]) == ("area:contratos", "c5def5")
    with pytest.raises(GitHubError, match="Label.name: already_exists") as error:
        cli.post(f"{REPO}/labels", {"name": "AREA:Contratos"})
    assert error.value.status == 422
    assert error.value.detail["status"] == "422"
    assert len(doble.labels) == 1


def test_leer_una_etiqueta_por_su_nombre_codificado() -> None:
    doble = FakeGitHub()
    doble.add_label("modo:didáctico x")
    cli = _cliente(doble)
    assert (
        cli.get(f"{REPO}/labels/modo%3Adid%C3%A1ctico%20x")["name"]
        == "modo:didáctico x"
    )
    with pytest.raises(GitHubError) as error:
        cli.get(f"{REPO}/labels/no-existe")
    assert error.value.status == 404
    assert error.value.detail == {
        "message": "Not Found",
        "documentation_url": "https://docs.github.com/rest",
        "status": "404",
    }


def test_milestone_repetido_da_422() -> None:
    doble = FakeGitHub()
    cli = _cliente(doble)
    assert cli.post(f"{REPO}/milestones", {"title": "Hito 0 — Núcleo"})["number"] == 1
    with pytest.raises(GitHubError, match="Milestone.title: already_exists"):
        cli.post(f"{REPO}/milestones", {"title": "Hito 0 — Núcleo"})


def test_crear_y_actualizar_un_issue() -> None:
    doble = FakeGitHub()
    for nombre in ("tipo:tarea", "critica"):
        doble.add_label(nombre)
    doble.add_milestone("Hito 0")
    cli = _cliente(doble)
    issue = cli.post(
        f"{REPO}/issues",
        {"title": "T-01 · Algo", "body": "<!-- menairos:tarea=T-01 hito=0 -->",
         "labels": ["tipo:tarea"], "milestone": 1},
    )  # fmt: skip
    assert issue["number"] == 1
    assert issue["milestone"]["title"] == "Hito 0"
    assert [e["name"] for e in issue["labels"]] == ["tipo:tarea"]
    numero = issue["number"]
    cambiado = cli.patch(
        f"{REPO}/issues/{numero}", {"body": "nuevo", "labels": ["critica"]}
    )
    assert (cambiado["body"], cambiado["title"]) == ("nuevo", "T-01 · Algo")
    assert [e["name"] for e in cli.get(f"{REPO}/issues/1")["labels"]] == ["critica"]


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"title": "x", "labels": ["no-existe"]},
        {"title": "x", "milestone": 7},
        {"title": "  "},
        {"body": "sin título"},
    ],
    ids=["etiqueta", "milestone", "titulo-vacio", "sin-titulo"],
)
def test_issue_invalido_da_422_y_no_se_crea(cuerpo: dict[str, object]) -> None:
    doble = FakeGitHub()
    with pytest.raises(GitHubError) as error:
        _cliente(doble).post(f"{REPO}/issues", cuerpo)
    assert error.value.status == 422
    assert doble.issues == {}


def test_un_issue_que_no_existe_da_404() -> None:
    cli = _cliente(FakeGitHub())
    with pytest.raises(GitHubError) as error:
        cli.patch(f"{REPO}/issues/9", {"body": "x"})
    assert error.value.status == 404


def test_blocked_by_se_crea_con_el_id_y_no_con_el_numero() -> None:
    doble = FakeGitHub()
    a, b = doble.add_issue("T-01"), doble.add_issue("T-02", state="closed")
    cli = _cliente(doble)
    ruta = f"{REPO}/issues/{a['number']}/dependencies/blocked_by"
    with pytest.raises(GitHubError) as error:
        cli.post(ruta, {"issue_id": b["number"]})
    assert error.value.status == 404
    assert cli.post(ruta, {"issue_id": b["id"]})["number"] == b["number"]
    assert [i["number"] for i in cli.get_all(ruta)] == [b["number"]]
    assert doble.blocked_by == {a["number"]: [b["number"]]}


@pytest.mark.parametrize("caso", ["repetida", "a-si-misma", "id-no-entero"])
def test_blocked_by_invalido_da_422(caso: str) -> None:
    doble = FakeGitHub()
    a, b = doble.add_issue("T-01"), doble.add_issue("T-02")
    doble.add_blocked_by(a["number"], b["number"])
    cuerpo = {
        "repetida": {"issue_id": b["id"]},
        "a-si-misma": {"issue_id": a["id"]},
        "id-no-entero": {"issue_id": str(b["id"])},
    }[caso]
    with pytest.raises(GitHubError) as error:
        _cliente(doble).post(f"{REPO}/issues/1/dependencies/blocked_by", cuerpo)
    assert error.value.status == 422
    assert doble.blocked_by == {1: [2]}


def test_quitar_un_blocked_by_con_el_unico_delete_permitido() -> None:
    doble = FakeGitHub()
    a, b = doble.add_issue("T-01"), doble.add_issue("T-02")
    doble.add_blocked_by(a["number"], b["number"])
    cli = _cliente(doble)
    ruta = f"{REPO}/issues/1/dependencies/blocked_by/{b['id']}"
    cli.delete(ruta)
    assert doble.blocked_by == {1: []}
    with pytest.raises(GitHubError) as error:
        cli.delete(ruta)
    assert error.value.status == 404
    assert [c.method for c in doble.calls] == ["DELETE", "DELETE"]


@pytest.mark.parametrize(
    ("metodo", "ruta", "params", "cuerpo"),
    [
        ("GET", "repos/otro/repo/labels", None, None),
        ("GET", f"{REPO}/pulls", None, None),
        ("PATCH", f"{REPO}/labels/a", None, {"color": "000000"}),
        ("GET", f"{REPO}/issues", {"sort": "updated"}, None),
        ("POST", f"{REPO}/issues", None, {"title": "x", "assignees": ["ejemplo"]}),
    ],
    ids=["otro-repo", "ruta", "metodo", "parametro", "campo"],
)
def test_lo_que_el_doble_no_modela_falla_a_la_vista(
    metodo: str,
    ruta: str,
    params: dict[str, str] | None,
    cuerpo: dict[str, object] | None,
) -> None:
    doble = FakeGitHub()
    doble.add_label("a")
    with pytest.raises(UnsupportedRoute):
        _cliente(doble).request(metodo, ruta, params=params, body=cuerpo)


# ── Fallos programables ────────────────────────────────────────────────────


def test_502_en_la_llamada_n_y_el_get_se_reintenta() -> None:
    doble = FakeGitHub()
    for i in range(250):
        doble.add_label(f"e{i:03d}")
    doble.fail(502, call=2)
    assert len(_cliente(doble).get_all(f"{REPO}/labels")) == 250
    assert len(doble.calls) == 4
    assert doble.calls[1] == doble.calls[2]
    assert doble.sleeps == [1.0]


def test_la_llamada_n_se_cuenta_desde_1() -> None:
    doble = FakeGitHub()
    doble.fail(502, call=3)
    cli = _cliente(doble)
    for _ in range(2):
        cli.post(f"{REPO}/labels", {"name": f"e{len(doble.labels)}"})
    with pytest.raises(GitHubError) as error:
        cli.post(f"{REPO}/labels", {"name": "tercera"})
    assert error.value.status == 502
    assert [e["name"] for e in doble.labels] == ["e0", "e1"]


def test_404_y_422_programados_por_metodo_y_ruta() -> None:
    doble = FakeGitHub()
    doble.add_label("a")
    doble.fail(404, method="GET", path=f"{REPO}/labels")
    doble.fail(
        422,
        method="POST",
        path=re.compile(r"repos/[^/]+/[^/]+/milestones"),
        body={
            "message": "Validation Failed",
            "errors": [{"code": "custom", "message": "no"}],
        },
    )
    cli = _cliente(doble)
    with pytest.raises(GitHubError) as error:
        cli.get_all(f"{REPO}/labels")
    assert error.value.status == 404
    assert len(cli.get_all(f"{REPO}/labels")) == 1
    with pytest.raises(GitHubError, match="custom no"):
        cli.post(f"{REPO}/milestones", {"title": "Hito 0"})
    assert doble.milestones == []


def test_fallo_siempre_y_fallo_n_veces() -> None:
    doble = FakeGitHub()
    doble.fail(503, path=f"{REPO}/labels", times=None)
    doble.fail(502, path=f"{REPO}/milestones", times=2)
    cli = _cliente(doble)
    with pytest.raises(GitHubError, match="tras 3 reintentos"):
        cli.get(f"{REPO}/labels")
    assert cli.get(f"{REPO}/milestones") == []
    assert len(doble.calls) == 4 + 3


def test_fallo_a_mitad_con_apply_la_escritura_queda_hecha() -> None:
    """Lo que §2.4 pide para T-08: GitHub guarda el issue pero responde 502."""
    doble = FakeGitHub()
    doble.fail(502, method="POST", path=f"{REPO}/issues", apply=True)
    cli = _cliente(doble)
    with pytest.raises(GitHubError):
        cli.post(f"{REPO}/issues", {"title": "T-01 · Algo"})
    assert [i["title"] for i in cli.get_all(f"{REPO}/issues")] == ["T-01 · Algo"]
    assert len(doble.calls_to("POST", r".*/issues")) == 1


def test_fallo_con_cabeceras_de_limite_de_uso() -> None:
    doble = FakeGitHub()
    doble.fail(
        403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1795780800"}
    )
    with pytest.raises(RateLimited, match="12:00:00 UTC"):
        _cliente(doble).get(f"{REPO}/labels")


def test_calls_to_filtra_por_metodo_y_ruta() -> None:
    doble = FakeGitHub()
    cli = _cliente(doble)
    cli.post(f"{REPO}/labels", {"name": "a"})
    cli.get(f"{REPO}/labels")
    assert doble.calls_to("post", r".*/labels") == [
        Call("POST", f"{REPO}/labels", {}, {"name": "a"})
    ]
    assert doble.calls_to("GET", r"repos/ejemplo/ejemplo/labels") == [
        Call("GET", f"{REPO}/labels", {})
    ]


# ── Tope ───────────────────────────────────────────────────────────────────


def test_el_tope_por_defecto_es_generoso() -> None:
    assert FakeGitHub().limit == 500


def test_el_tope_exacto_y_el_mensaje() -> None:
    doble = FakeGitHub(limit=3)
    cli = _cliente(doble)
    for i in range(3):
        cli.post(f"{REPO}/labels", {"name": f"e{i}"})
    with pytest.raises(RunawayLoop) as error:
        cli.get(f"{REPO}/labels", {"page": 9})
    assert (error.value.count, error.value.limit) == (4, 3)
    assert [c.describe() for c in error.value.last] == [
        f"POST {REPO}/labels",
        f"POST {REPO}/labels",
        f"POST {REPO}/labels",
        f"GET {REPO}/labels?page=9",
    ]
    assert str(error.value) == (
        "El doble de GitHub pasó su tope de 3 llamadas (van 4): ¿un bucle? Últimas: "
        f"POST {REPO}/labels; POST {REPO}/labels; POST {REPO}/labels; "
        f"GET {REPO}/labels?page=9"
    )


def test_el_mensaje_lleva_solo_las_5_ultimas() -> None:
    doble = FakeGitHub(limit=10)
    cli = _cliente(doble)
    with pytest.raises(RunawayLoop) as error:
        for page in range(1, 100):
            cli.get(f"{REPO}/labels", {"page": page})
    assert error.value.count == 11
    assert [c.query["page"] for c in error.value.last] == ["7", "8", "9", "10", "11"]


def test_except_exception_no_se_traga_el_tope_y_el_tope_se_repite() -> None:
    doble = FakeGitHub(limit=2)
    cli = _cliente(doble)
    vueltas = 0
    with pytest.raises(RunawayLoop):
        while True:  # un bucle que se traga los errores
            vueltas += 1
            try:
                cli.get(f"{REPO}/labels")
            except Exception:
                continue
    assert vueltas == 3
    with pytest.raises(RunawayLoop):
        cli.get(f"{REPO}/labels")


def test_el_tope_cuenta_tambien_las_respuestas_de_error() -> None:
    doble = FakeGitHub(limit=3)
    doble.fail(502, times=None)
    with pytest.raises(RunawayLoop):
        _cliente(doble).get(f"{REPO}/labels")
    assert len(doble.calls) == 4


# ── Fixture ────────────────────────────────────────────────────────────────


def test_la_fixture_conecta_el_doble_a_github(doble_github: FakeGitHub) -> None:
    doble_github.add_label("a")
    doble_github.fail(502, call=1)
    assert [e["name"] for e in GitHub().get_all(f"{REPO}/labels")] == ["a"]
    assert len(doble_github.calls) == 2
    assert doble_github.sleeps == [1.0]


def test_la_fixture_permite_cambiar_el_tope(doble_github: FakeGitHub) -> None:
    doble_github.limit = 1
    cli = GitHub()
    cli.get(f"{REPO}/labels")
    with pytest.raises(RunawayLoop):
        cli.get(f"{REPO}/labels")


def test_la_fixture_permite_cambiar_el_repo(doble_github: FakeGitHub) -> None:
    doble_github.repo = "otro/prueba"
    doble_github.add_label("a")
    assert len(GitHub().get_all("repos/otro/prueba/labels")) == 1
