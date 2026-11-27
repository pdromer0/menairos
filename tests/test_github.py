"""Tests del envoltorio de gh api (T-07): argv, salida de --include, rutas, DELETE,
GraphQL, errores, reintentos y paginación.

Aquí el transporte es enlatado (una lista de respuestas); los tests contra el doble
de GitHub están en test_doble_github.py. Ningún test lanza gh.
"""

import subprocess
from datetime import UTC, datetime
from typing import Any

import pytest
from doble_github import RealGitHubCall

from menairos import github
from menairos.github import (
    ForbiddenRequest,
    GhCli,
    GitHub,
    GitHubError,
    RateLimited,
    Request,
    Response,
    check_path,
    next_link,
    parse_include,
)

REPO = "repos/ejemplo/ejemplo"
QUITAR = f"{REPO}/issues/3/dependencies/blocked_by/4002"


class Enlatado:
    """Transporte que devuelve (o lanza) las respuestas dadas, en orden."""

    def __init__(self, *respuestas: Response | Exception) -> None:
        self.respuestas = list(respuestas)
        self.peticiones: list[Request] = []
        self.timeouts: list[float] = []

    def send(self, request: Request, timeout: float) -> Response:
        self.peticiones.append(request)
        self.timeouts.append(timeout)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def ok(data: Any = None, status: int = 200, **cabeceras: str) -> Response:
    return Response(
        status, {k.replace("_", "-"): v for k, v in cabeceras.items()}, data
    )


def fallo(status: int, data: Any = None, **cabeceras: str) -> Response:
    return ok(data, status, **cabeceras)


def cliente(*respuestas: Response | Exception) -> tuple[GitHub, Enlatado, list[float]]:
    transporte = Enlatado(*respuestas)
    esperas: list[float] = []
    return GitHub(transporte, sleep=esperas.append), transporte, esperas


# ── GhCli: la orden y su salida ─────────────────────────────────────────────


class Ejecutor:
    """Sustituye a subprocess.run: anota la llamada y devuelve lo que se le dé."""

    def __init__(
        self,
        stdout: bytes = b"HTTP/2.0 200 OK\r\n\r\n{}",
        stderr: bytes = b"",
        returncode: int = 0,
        lanza: BaseException | None = None,
    ) -> None:
        self.salida = subprocess.CompletedProcess[bytes]([], returncode, stdout, stderr)
        self.lanza = lanza
        self.llamadas: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(
        self, argv: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        self.llamadas.append((argv, kwargs))
        if self.lanza is not None:
            raise self.lanza
        return self.salida


CABECERAS = [
    "--header",
    "Accept: application/vnd.github+json",
    "--header",
    "X-GitHub-Api-Version: 2022-11-28",
]


def test_argv_de_un_get_lleva_siempre_el_metodo() -> None:
    ejecutor = Ejecutor()
    GhCli(ejecutor).send(Request("GET", f"{REPO}/labels?per_page=100"), 30)
    argv, kwargs = ejecutor.llamadas[0]
    assert argv == [
        "gh", "api", "--method", "GET", "--include", *CABECERAS,
        "--", f"{REPO}/labels?per_page=100",
    ]  # fmt: skip
    assert kwargs["input"] is None


def test_argv_de_un_post_manda_el_cuerpo_por_stdin_en_json() -> None:
    ejecutor = Ejecutor(b"HTTP/2.0 201 Created\r\n\r\n{}")
    cuerpo = {"title": "T-01 · Ñandú", "labels": ["tipo:tarea"], "milestone": 1}
    GhCli(ejecutor).send(Request("POST", f"{REPO}/issues", cuerpo), 30)
    argv, kwargs = ejecutor.llamadas[0]
    assert argv == [
        "gh", "api", "--method", "POST", "--include", *CABECERAS,
        "--input", "-", "--", f"{REPO}/issues",
    ]  # fmt: skip
    assert (
        kwargs["input"]
        == (
            '{"title": "T-01 · Ñandú", "labels": ["tipo:tarea"], "milestone": 1}'
        ).encode()
    )


def test_ghcli_pasa_el_tiempo_maximo_y_no_pide_nada_por_terminal() -> None:
    ejecutor = Ejecutor()
    GhCli(ejecutor).send(Request("GET", "user"), 12.5)
    _, kwargs = ejecutor.llamadas[0]
    assert kwargs["timeout"] == 12.5
    assert kwargs["capture_output"] is True
    assert kwargs["check"] is False
    assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"


def test_tiempo_agotado_es_un_error_sin_codigo_http() -> None:
    ejecutor = Ejecutor(lanza=subprocess.TimeoutExpired(["gh"], 30))
    with pytest.raises(GitHubError, match="no respondió en 30 s") as error:
        GhCli(ejecutor).send(Request("GET", "user"), 30)
    assert error.value.status is None


def test_sin_gh_instalado_es_un_error_claro() -> None:
    ejecutor = Ejecutor(lanza=FileNotFoundError("gh"))
    with pytest.raises(GitHubError, match="No se encuentra gh") as error:
        GhCli(ejecutor).send(Request("GET", "user"), 30)
    assert error.value.status is None


def test_fallo_sin_linea_http_lleva_el_stderr_de_gh() -> None:
    ejecutor = Ejecutor(b"", b"error connecting to api.github.com\n", 1)
    with pytest.raises(GitHubError, match="error connecting") as error:
        GhCli(ejecutor).send(Request("GET", "user"), 30)
    assert error.value.status is None


def test_fallo_sin_linea_http_ni_stderr_lleva_el_codigo_de_salida() -> None:
    with pytest.raises(GitHubError, match="código de salida 4"):
        GhCli(Ejecutor(b"", b"", 4)).send(Request("GET", "user"), 30)


def test_un_error_http_sale_como_respuesta_aunque_gh_acabe_con_1() -> None:
    salida = (
        b"HTTP/2.0 404 Not Found\r\nX-Github-Request-Id: A\r\n\r\n"
        b'{"message":"Not Found"}'
    )
    respuesta = GhCli(Ejecutor(salida, b"gh: Not Found (HTTP 404)\n", 1)).send(
        Request("GET", f"{REPO}/labels/x"), 30
    )
    assert respuesta.status == 404
    assert respuesta.data == {"message": "Not Found"}


def test_ghcli_real_no_se_puede_lanzar_en_los_tests() -> None:
    """La fixture autouse lo impide: si no, este test llamaría a GitHub."""
    with pytest.raises(RealGitHubCall):
        GhCli().send(Request("GET", "user"), 30)


@pytest.mark.parametrize("fin", ["\r\n", "\n"], ids=["crlf", "lf"])
def test_parse_include_con_crlf_y_con_lf(fin: str) -> None:
    salida = fin.join(
        [
            "HTTP/2.0 200 OK",
            'Link: <https://api.github.com/x?page=2>; rel="next"',
            "X-Ratelimit-Remaining: 4999",
            "",
            '[{"name": "a"}]',
        ]
    )
    respuesta = parse_include(salida.encode())
    assert respuesta is not None
    assert respuesta.status == 200
    assert respuesta.header("link") == '<https://api.github.com/x?page=2>; rel="next"'
    assert respuesta.header("X-RateLimit-Remaining") == "4999"
    assert respuesta.data == [{"name": "a"}]


def test_parse_include_con_el_formato_real_de_gh() -> None:
    """Visto en la comprobación real de T-07 (gh 2.103.3): la línea de estado acaba
    en LF y las cabeceras en CRLF; un 404 sale igual por stdout aunque gh acabe con 1.
    """
    salida = (
        b"HTTP/2.0 404 Not Found\n"
        b"Access-Control-Allow-Origin: *\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"X-Ratelimit-Remaining: 4987\r\n"
        b"\r\n"
        b'{"message":"Not Found","documentation_url":'
        b'"https://docs.github.com/rest/issues/labels#get-a-label","status":"404"}'
    )
    respuesta = parse_include(salida)
    assert respuesta is not None
    assert respuesta.status == 404
    assert respuesta.header("X-RateLimit-Remaining") == "4987"
    assert respuesta.header("content-type") == "application/json; charset=utf-8"
    assert respuesta.data["status"] == "404"


def test_parse_include_junta_las_cabeceras_repetidas() -> None:
    respuesta = parse_include(b"HTTP/1.1 200 OK\nVary: Accept\nvary: Origin\n\n{}")
    assert respuesta is not None
    assert respuesta.header("Vary") == "Accept, Origin"


def test_parse_include_sin_cuerpo() -> None:
    respuesta = parse_include(b"HTTP/2.0 204 No Content\r\nServer: GitHub.com\r\n\r\n")
    assert respuesta is not None
    assert (respuesta.status, respuesta.data, respuesta.text) == (204, None, "")


def test_parse_include_con_un_cuerpo_que_no_es_json() -> None:
    respuesta = parse_include(b"HTTP/2.0 502 Bad Gateway\r\n\r\n<html>502</html>")
    assert respuesta is not None
    assert (respuesta.status, respuesta.data, respuesta.text) == (
        502,
        None,
        "<html>502</html>",
    )


@pytest.mark.parametrize("salida", [b"", b"{}", b"gh: algo\n\nHTTP/2.0 200 OK"])
def test_parse_include_sin_linea_de_estado(salida: bytes) -> None:
    assert parse_include(salida) is None


def test_response_pone_las_cabeceras_en_minusculas() -> None:
    respuesta = Response(200, {"Link": "x", "X-RateLimit-Reset": "1"})
    assert dict(respuesta.headers) == {"link": "x", "x-ratelimit-reset": "1"}
    assert respuesta.header("LINK") == "x"


# ── Rutas, GraphQL y DELETE ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ruta",
    [
        f"{REPO}/labels",
        f"{REPO}/labels/area%3Acontratos",
        f"{REPO}/issues?state=all&per_page=100",
        "user",
        "repositories/123/labels?page=2",
        f"{REPO}/labels/estado%3Arepo",
        f"{REPO}/labels/a:repository",
    ],
)
def test_rutas_validas(ruta: str) -> None:
    assert check_path(ruta) == ruta


@pytest.mark.parametrize(
    "ruta",
    [
        "",
        f"/{REPO}/labels",
        f"https://api.github.com/{REPO}/labels",
        "-X DELETE",
        "--method=DELETE",
        "repos/{owner}/{repo}/labels",
        f"{REPO}/labels/a b",
        f"{REPO}/labels\nx",
        f"{REPO}/labels\tx",
        f"{REPO}/labels/área",
        f"{REPO}/labels#x",
        f"{REPO}//labels",
        f"{REPO}/labels/",
        f"{REPO}/../../user",
        f"{REPO}/./labels",
        f"{REPO}/labels/estado:repo",
        f"{REPO}/labels/x:owner",
        "repos/:owner/:repo/branches/:branch",
    ],
    ids=[
        "vacia", "barra", "url", "guion", "opcion", "llaves", "espacio", "salto",
        "tabulador", "no-ascii", "almohadilla", "doble-barra", "barra-final", "puntos",
        "punto", "dos-puntos-repo", "dos-puntos-owner", "dos-puntos-branch",
    ],
)  # fmt: skip
def test_rutas_rechazadas(ruta: str) -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="no válida"):
        cli.get(ruta)
    assert transporte.peticiones == []


@pytest.mark.parametrize(
    "ruta", ["graphql", "GraphQL", "graphql?query=x", "/graphql", "graphql/x"]
)
def test_graphql_se_rechaza(ruta: str) -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="solo usa la API REST"):
        cli.post(ruta, {"query": "{ viewer { login } }"})
    assert transporte.peticiones == []


def test_un_repo_que_se_llama_graphql_no_es_graphql() -> None:
    cli, transporte, _ = cliente(ok([]))
    cli.get("repos/ejemplo/graphql/labels")
    assert transporte.peticiones[0].path == "repos/ejemplo/graphql/labels"


@pytest.mark.parametrize("metodo", ["DELETE", "delete", "Delete"])
def test_delete_permitido_quitar_un_blocked_by(metodo: str) -> None:
    cli, transporte, _ = cliente(ok(status=204))
    cli.request(metodo, QUITAR)
    assert transporte.peticiones == [Request("DELETE", QUITAR)]


@pytest.mark.parametrize(
    "ruta",
    [
        f"{REPO}/labels/tipo%3Atarea",
        f"{REPO}/milestones/1",
        f"{REPO}/issues/3",
        f"{REPO}/issues/3/dependencies/blocked_by",
        f"{QUITAR}/x",
        f"{QUITAR}?x=1",
        f"{REPO}/issues/3/dependencies/blocked_by/04002",
        f"{REPO}/issues/03/dependencies/blocked_by/4002",
        f"{REPO}/issues/3/dependencies/blocking/4002",
        f"x/{QUITAR}",
        "repos/ejemplo",
    ],
    ids=[
        "etiqueta", "milestone", "issue", "lista", "tramo-de-mas", "consulta",
        "cero-id", "cero-numero", "blocking", "prefijo", "repo",
    ],
)  # fmt: skip
@pytest.mark.parametrize("metodo", ["DELETE", "delete"])
def test_cualquier_otro_delete_se_rechaza_antes_de_llamar_a_gh(
    metodo: str, ruta: str
) -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="no borra nada"):
        cli.request(metodo, ruta)
    assert transporte.peticiones == []


def test_delete_con_parametros_se_rechaza() -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="no borra nada"):
        cli.request("DELETE", QUITAR, params={"x": 1})
    assert transporte.peticiones == []


def test_la_lista_de_delete_permitidos_tiene_un_solo_patron() -> None:
    assert len(github._ALLOWED_DELETES) == 1  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("metodo", ["HEAD", "OPTIONS", "TRACE", "GETX"])
def test_metodos_no_admitidos(metodo: str) -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="no admitido"):
        cli.request(metodo, "user")
    assert transporte.peticiones == []


def test_un_get_no_lleva_cuerpo() -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="no lleva cuerpo"):
        cli.request("GET", "user", body={"x": 1})
    assert transporte.peticiones == []


def test_parametros_codificados() -> None:
    cli, transporte, _ = cliente(ok([]), ok([]))
    cli.get(
        f"{REPO}/issues", {"state": "all", "labels": "tipo:tarea,área x", "x": True}
    )
    cli.get(f"{REPO}/issues?state=all", {"page": 2})
    assert [p.path for p in transporte.peticiones] == [
        f"{REPO}/issues?state=all&labels=tipo%3Atarea%2C%C3%A1rea+x&x=true",
        f"{REPO}/issues?state=all&page=2",
    ]


@pytest.mark.parametrize("valor", [["tipo:tarea", "hito:0"], None, 1.5, {"a": 1}])
def test_un_parametro_que_no_es_texto_entero_ni_booleano_se_rechaza(
    valor: object,
) -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest, match="texto, entero o booleano"):
        cli.get(f"{REPO}/issues", {"labels": valor})
    assert transporte.peticiones == []


def test_el_tiempo_maximo_llega_al_transporte() -> None:
    transporte = Enlatado(ok({}))
    GitHub(transporte, timeout=7).get("user")
    assert transporte.timeouts == [7]


# ── Errores ────────────────────────────────────────────────────────────────


def _error(*respuestas: Response, metodo: str = "GET") -> GitHubError:
    cli, _, _ = cliente(*respuestas)
    with pytest.raises(GitHubError) as error:
        cli.request(
            metodo, f"{REPO}/labels", body={"name": "x"} if metodo != "GET" else None
        )
    return error.value


def test_404() -> None:
    error = _error(fallo(404, {"message": "Not Found"}))
    assert error.status == 404
    assert str(error) == (
        f"GitHub no encuentra {REPO}/labels (HTTP 404) en GET: "
        "no existe o el token no tiene acceso."
    )
    assert error.detail == {"message": "Not Found"}
    assert (error.method, error.path) == ("GET", f"{REPO}/labels")


def test_401() -> None:
    error = _error(fallo(401, {"message": "Bad credentials"}))
    assert error.status == 401
    assert "gh auth login" in str(error)


def test_403_sin_limite_de_uso_es_permiso_denegado() -> None:
    error = _error(fallo(403, {"message": "Resource not accessible by integration"}))
    assert not isinstance(error, RateLimited)
    assert str(error) == (
        f"Permiso denegado (HTTP 403) en GET {REPO}/labels: "
        "«Resource not accessible by integration»."
    )


def test_403_con_el_limite_agotado_da_la_hora_de_renovacion() -> None:
    error = _error(
        fallo(
            403,
            {"message": "API rate limit exceeded for user ID 1."},
            X_RateLimit_Remaining="0",
            X_RateLimit_Reset="1795780800",
        )
    )
    assert isinstance(error, RateLimited)
    assert error.status == 403
    assert error.reset_at == datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    assert error.retry_after is None
    assert str(error) == (
        f"Límite de uso de la API de GitHub alcanzado (HTTP 403) en GET {REPO}/labels; "
        "se renueva a las 12:00:00 UTC."
    )


def test_403_con_retry_after_es_el_limite_secundario() -> None:
    error = _error(fallo(403, {"message": "You have exceeded a secondary rate limit"},
                         Retry_After="60"))  # fmt: skip
    assert isinstance(error, RateLimited)
    assert error.retry_after == 60
    assert str(error).endswith("vuelve a intentarlo dentro de 60 s.")


def test_403_que_solo_lo_dice_en_el_mensaje() -> None:
    error = _error(fallo(403, {"message": "secondary rate limit"}))
    assert isinstance(error, RateLimited)
    assert str(error) == (
        f"Límite de uso de la API de GitHub alcanzado (HTTP 403) en GET {REPO}/labels."
    )


@pytest.mark.parametrize(
    "valor",
    ["²", "-5", "1e9", "", " ", "１２", "9" * 19],
)
def test_cabeceras_de_limite_raras_no_rompen_el_error(valor: str) -> None:
    error = _error(
        fallo(429, {"message": "x"}, X_RateLimit_Reset=valor, Retry_After=valor)
    )
    assert isinstance(error, RateLimited)
    assert (error.reset_at, error.retry_after) == (None, None)
    assert str(error) == (
        f"Límite de uso de la API de GitHub alcanzado (HTTP 429) en GET {REPO}/labels."
    )


def test_una_hora_de_renovacion_fuera_de_rango_se_ignora() -> None:
    error = _error(fallo(403, {"message": "x"}, X_RateLimit_Remaining="0",
                         X_RateLimit_Reset="99999999999999"))  # fmt: skip
    assert isinstance(error, RateLimited)
    assert error.reset_at is None
    assert str(error).endswith(f"en GET {REPO}/labels.")


def test_429() -> None:
    error = _error(fallo(429, {"message": "Too Many Requests"}, Retry_After="5"))
    assert isinstance(error, RateLimited)
    assert error.status == 429
    assert error.retry_after == 5


def test_422_con_el_detalle_de_github() -> None:
    error = _error(
        fallo(
            422,
            {
                "message": "Validation Failed",
                "errors": [
                    {"resource": "Label", "code": "already_exists", "field": "name"},
                    {"resource": "Issue", "field": "title", "code": "custom",
                     "message": "title is too long"},
                    "texto suelto",
                ],
            },
        ),
        metodo="POST",
    )  # fmt: skip
    assert error.status == 422
    assert str(error) == (
        f"GitHub rechaza los datos de POST {REPO}/labels (HTTP 422): "
        "«Validation Failed»; Label.name: already_exists; "
        "Issue.title: custom title is too long; texto suelto."
    )


def test_422_sin_errores() -> None:
    error = _error(fallo(422, {"message": "Validation Failed"}), metodo="POST")
    assert str(error) == (
        f"GitHub rechaza los datos de POST {REPO}/labels (HTTP 422): "
        "«Validation Failed»."
    )


@pytest.mark.parametrize("status", [500, 502, 503])
def test_5xx_en_una_escritura(status: int) -> None:
    error = _error(fallo(status), metodo="POST")
    assert error.status == status
    assert str(error) == (
        f"Error de GitHub (HTTP {status}) en POST {REPO}/labels. "
        "Mira https://www.githubstatus.com antes de buscar el fallo."
    )


def test_otro_4xx_con_el_mensaje_de_github() -> None:
    error = _error(fallo(409, {"message": "Conflict"}), metodo="POST")
    assert str(error) == f"GitHub respondió HTTP 409 en POST {REPO}/labels: «Conflict»."


def test_un_error_con_un_cuerpo_que_no_es_json_lleva_su_texto() -> None:
    error = _error(Response(400, {}, None, "Bad request"), metodo="POST")
    assert (
        str(error) == f"GitHub respondió HTTP 400 en POST {REPO}/labels: «Bad request»."
    )
    assert error.detail == "Bad request"


def test_un_2xx_que_no_es_json_es_un_error() -> None:
    cli, _, _ = cliente(Response(200, {}, None, "<html>"))
    with pytest.raises(GitHubError, match="no es JSON") as error:
        cli.get("user")
    assert error.value.status == 200


def test_un_204_sin_cuerpo_devuelve_none() -> None:
    cli, _, _ = cliente(ok(status=204))
    assert cli.delete(QUITAR) is None


# ── Reintentos ─────────────────────────────────────────────────────────────


def test_get_con_502_se_reintenta_hasta_3_veces_con_espera_creciente() -> None:
    cli, transporte, esperas = cliente(fallo(502), fallo(503), fallo(500), ok(["a"]))
    assert cli.get(f"{REPO}/labels") == ["a"]
    assert len(transporte.peticiones) == 4
    assert esperas == [1.0, 2.0, 4.0]


def test_get_con_4_fallos_5xx_seguidos_falla_tras_4_llamadas() -> None:
    cli, transporte, esperas = cliente(*[fallo(502)] * 4)
    with pytest.raises(GitHubError) as error:
        cli.get(f"{REPO}/labels")
    assert len(transporte.peticiones) == 4
    assert esperas == [1.0, 2.0, 4.0]
    assert error.value.status == 502
    assert "tras 3 reintentos" in str(error.value)


@pytest.mark.parametrize("metodo", ["POST", "PATCH", "PUT"])
def test_las_escrituras_no_se_reintentan(metodo: str) -> None:
    cli, transporte, esperas = cliente(fallo(502), ok({}))
    with pytest.raises(GitHubError):
        cli.request(metodo, f"{REPO}/issues", body={"title": "x"})
    assert len(transporte.peticiones) == 1
    assert esperas == []


def test_el_delete_permitido_no_se_reintenta() -> None:
    cli, transporte, _ = cliente(fallo(502), ok(status=204))
    with pytest.raises(GitHubError):
        cli.delete(QUITAR)
    assert len(transporte.peticiones) == 1


@pytest.mark.parametrize("status", [404, 422, 429, 403, 401])
def test_un_get_con_4xx_no_se_reintenta(status: int) -> None:
    cli, transporte, esperas = cliente(fallo(status), ok({}))
    with pytest.raises(GitHubError):
        cli.get(f"{REPO}/labels")
    assert len(transporte.peticiones) == 1
    assert esperas == []


def test_un_tiempo_agotado_no_se_reintenta() -> None:
    agotado = GitHubError("gh api no respondió", status=None, method="GET", path="user")
    cli, transporte, esperas = cliente(agotado, ok({}))
    with pytest.raises(GitHubError, match="no respondió"):
        cli.get("user")
    assert len(transporte.peticiones) == 1
    assert esperas == []


def test_sin_sleep_se_usa_default_sleep_del_modulo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    esperas: list[float] = []
    monkeypatch.setattr(github, "default_sleep", esperas.append)
    GitHub(Enlatado(fallo(502), ok({}))).get("user")
    assert esperas == [1.0]


def test_sin_transporte_se_usa_default_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transporte = Enlatado(ok({"login": "ejemplo"}))
    monkeypatch.setattr(github, "default_transport", lambda: transporte)
    assert GitHub().get("user") == {"login": "ejemplo"}


def test_default_transport_es_gh() -> None:
    assert isinstance(github.default_transport(), GhCli)


# ── Paginación ─────────────────────────────────────────────────────────────


def _link(**rels: str) -> str:
    return ", ".join(
        f'<https://api.github.com/{url}>; rel="{rel}"' for rel, url in rels.items()
    )


def test_next_link() -> None:
    cabecera = _link(prev="x?page=1", next="repositories/9/labels?per_page=2&page=3",
                     last="x?page=5")  # fmt: skip
    assert next_link(cabecera) == "repositories/9/labels?per_page=2&page=3"
    assert next_link(_link(prev="x?page=1", last="x?page=1")) is None
    assert next_link(None) is None
    assert next_link("") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://github.example.com/api/v3/repositories/1/issues?page=2",
        "http://api.github.com/repositories/1/issues?page=2",
        "https://api.github.com.example.com/repositories/1/issues?page=2",
    ],
    ids=["enterprise", "http", "otro-dominio"],
)
def test_un_next_fuera_de_api_github_com_no_se_sigue(url: str) -> None:
    cli, transporte, _ = cliente(ok([1], link=f'<{url}>; rel="next"'))
    with pytest.raises(ForbiddenRequest, match="fuera de https://api.github.com/"):
        cli.get_all(f"{REPO}/issues")
    assert len(transporte.peticiones) == 1


def test_get_all_sigue_el_next_tal_cual_aunque_salte_paginas_o_use_cursor() -> None:
    cli, transporte, _ = cliente(
        ok([1, 2], link=_link(next="repositories/9/labels?per_page=2&page=5")),
        ok([3], link=_link(next=f"{REPO}/labels?per_page=2&after=Y3Vyc29y")),
        ok([4]),
    )
    assert cli.get_all(f"{REPO}/labels") == [1, 2, 3, 4]
    assert [p.path for p in transporte.peticiones] == [
        f"{REPO}/labels?per_page=100",
        "repositories/9/labels?per_page=2&page=5",
        f"{REPO}/labels?per_page=2&after=Y3Vyc29y",
    ]


def test_get_all_respeta_el_per_page_de_quien_llama() -> None:
    cli, transporte, _ = cliente(ok([]), ok([]))
    cli.get_all(f"{REPO}/labels", {"per_page": 2})
    cli.get_all(f"{REPO}/issues?per_page=7&state=all")
    assert [p.path for p in transporte.peticiones] == [
        f"{REPO}/labels?per_page=2",
        f"{REPO}/issues?per_page=7&state=all",
    ]


def test_get_all_con_un_next_repetido_para() -> None:
    cli, transporte, _ = cliente(
        ok([1], link=_link(next=f"{REPO}/labels?per_page=100&page=2")),
        ok([2], link=_link(next=f"{REPO}/labels?per_page=100")),
    )
    with pytest.raises(GitHubError, match="ya leída"):
        cli.get_all(f"{REPO}/labels")
    assert len(transporte.peticiones) == 2


def test_get_all_con_una_pagina_que_no_es_lista() -> None:
    cli, _, _ = cliente(ok({"total_count": 0, "items": []}))
    with pytest.raises(GitHubError, match="no devolvió una lista"):
        cli.get_all("search/issues?q=x")


def test_get_all_reintenta_cada_pagina_por_su_cuenta() -> None:
    cli, transporte, esperas = cliente(
        fallo(502),
        ok([1], link=_link(next=f"{REPO}/labels?per_page=100&page=2")),
        fallo(502),
        fallo(502),
        ok([2]),
    )
    assert cli.get_all(f"{REPO}/labels") == [1, 2]
    assert len(transporte.peticiones) == 5
    assert esperas == [1.0, 1.0, 2.0]


def test_get_all_rechaza_graphql_y_rutas_malas() -> None:
    cli, transporte, _ = cliente()
    with pytest.raises(ForbiddenRequest):
        cli.get_all("graphql")
    with pytest.raises(ForbiddenRequest):
        cli.get_all("/user/repos")
    assert transporte.peticiones == []
