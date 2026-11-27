"""GitHub through ``gh api``, REST only (ADR 0016).

Every call the CLI makes to GitHub goes through :class:`GitHub`, in two layers:

- a *transport* sends one :class:`Request` and returns one :class:`Response`.
  The real one is :class:`GhCli`, which runs ``gh api --include``; the tests use
  a double with the same protocol (``tests/doble_github.py``);
- the *client* :class:`GitHub` checks the path, refuses GraphQL and every
  ``DELETE`` but one, follows the ``Link`` header to paginate, retries a ``GET``
  that gets a 5xx and turns any other failure into a :class:`GitHubError` with a
  Spanish message.

The client knows nothing about issues or labels: callers build the REST paths.
A path segment holding free text (a label name) must be percent-encoded by the
caller, with ``urllib.parse.quote(text, safe="")``.

Only plain ``gh api`` options are used (``--method``, ``--include``,
``--input`` and ``--header``), so no recent version of ``gh`` is needed.
"""

import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit

API_VERSION = "2022-11-28"
ACCEPT = "application/vnd.github+json"
DEFAULT_TIMEOUT = 30.0
DEFAULT_PER_PAGE = 100
RETRY_WAITS: tuple[float, ...] = (1.0, 2.0, 4.0)
"""Waits before each retry of a ``GET`` that got a 5xx: at most 3 retries."""

METHODS = frozenset({"GET", "POST", "PATCH", "PUT", "DELETE"})

_ALLOWED_DELETES: tuple[re.Pattern[str], ...] = (
    # Removing a «blocked by» relation between two issues deletes a link, not
    # data (Pedro's decision, 2026-11-27). Route as documented by GitHub; T-08
    # verifies it against the test repository.
    re.compile(
        r"repos/[A-Za-z0-9-]+/[A-Za-z0-9._-]+/issues/[1-9][0-9]*"
        r"/dependencies/blocked_by/[1-9][0-9]*"
    ),
)
"""The only ``DELETE`` requests the client sends (``fullmatch``, no query)."""

_STATUS_LINE = re.compile(r"HTTP/[0-9.]+ ([0-9]{3})(?: .*)?")
_LINK = re.compile(r'<([^>]*)>\s*;\s*rel="([^"]*)"')


class GitHubError(Exception):
    """A call to GitHub failed; ``status`` is ``None`` if there was no HTTP answer."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None,
        method: str,
        path: str,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.method = method
        self.path = path
        self.detail = detail


class RateLimited(GitHubError):
    """GitHub's rate limit was hit (403 or 429)."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        method: str,
        path: str,
        detail: Any = None,
        reset_at: datetime | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(
            message, status=status, method=method, path=path, detail=detail
        )
        self.reset_at = reset_at
        self.retry_after = retry_after


class ForbiddenRequest(ValueError):
    """The client refuses the request before calling ``gh``."""


@dataclass(frozen=True)
class Request:
    """One REST call: ``path`` is relative and carries its query string."""

    method: str
    path: str
    body: Any = None


@dataclass(frozen=True)
class Response:
    """One HTTP answer.

    ``headers`` keys are lower-cased on creation. ``data`` is the parsed JSON
    body, or ``None`` if the body is empty or is not JSON (then ``text`` holds
    it).
    """

    status: int
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    data: Any = None
    text: str = ""

    def __post_init__(self) -> None:
        lowered = {name.lower(): value for name, value in self.headers.items()}
        object.__setattr__(self, "headers", lowered)

    def header(self, name: str) -> str | None:
        """Value of a header, whatever its case."""
        return self.headers.get(name.lower())


class Transport(Protocol):
    """Sends one request to GitHub."""

    def send(self, request: Request, timeout: float) -> Response: ...


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class GhCli:
    """The real transport: one ``gh api --include`` process per request."""

    def __init__(self, run: Runner | None = None) -> None:
        self._run = run

    def argv(self, request: Request) -> list[str]:
        """Command line for a request (the body goes through stdin)."""
        argv = [
            "gh",
            "api",
            "--method",
            request.method,
            "--include",
            "--header",
            f"Accept: {ACCEPT}",
            "--header",
            f"X-GitHub-Api-Version: {API_VERSION}",
        ]
        if request.body is not None:
            argv += ["--input", "-"]
        return [*argv, "--", request.path]

    def send(self, request: Request, timeout: float) -> Response:
        run = self._run or subprocess.run
        body = None
        if request.body is not None:
            body = json.dumps(request.body, ensure_ascii=False).encode("utf-8")
        env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1"}

        def fail(message: str) -> GitHubError:
            return GitHubError(
                message, status=None, method=request.method, path=request.path
            )

        try:
            done = run(
                self.argv(request),
                input=body,
                capture_output=True,
                timeout=timeout,
                env=env,
                check=False,
            )
        except FileNotFoundError:
            raise fail(
                "No se encuentra gh: instálalo y abre sesión con «gh auth login»."
            ) from None
        except subprocess.TimeoutExpired:
            raise fail(
                f"gh api no respondió en {timeout:g} s "
                f"({request.method} {request.path})."
            ) from None
        response = parse_include(done.stdout)
        if response is None:
            stderr = done.stderr.decode("utf-8", "replace").strip()
            raise fail(
                f"gh api falló sin respuesta HTTP ({request.method} {request.path}): "
                f"{stderr or f'código de salida {done.returncode}'}"
            )
        return response


def parse_include(output: bytes) -> Response | None:
    """Parse ``gh api --include`` output: status line, headers, blank line, body.

    Returns ``None`` if the output does not start with an HTTP status line.
    Lines may end in CRLF or LF; repeated headers are joined with ``", "``.
    """
    text = output.decode("utf-8", "replace")
    ends = [i for i in (text.find("\r\n\r\n"), text.find("\n\n")) if i >= 0]
    if ends:
        end = min(ends)
        head, body = text[:end], _after_blank_line(text, end)
    else:
        head, body = text, ""
    lines = head.replace("\r\n", "\n").split("\n")
    match = _STATUS_LINE.fullmatch(lines[0].strip())
    if match is None:
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep:
            continue
        key = name.strip().lower()
        value = value.strip()
        headers[key] = f"{headers[key]}, {value}" if key in headers else value
    data: Any = None
    if body.strip():
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = None
    return Response(int(match.group(1)), headers, data, body)


def _after_blank_line(text: str, end: int) -> str:
    """Body that follows the blank line found at ``end``."""
    if text.startswith("\r\n\r\n", end):
        return text[end + 4 :]
    return text[end + 2 :]


def default_transport() -> Transport:
    """Transport used when none is given; the tests replace this function."""
    return GhCli()


def default_sleep(seconds: float) -> None:
    """Wait used between retries when none is given; the tests replace it."""
    time.sleep(seconds)


def check_path(path: str) -> str:
    """Return ``path`` if the client may send it, or raise ``ForbiddenRequest``."""
    first = path.lstrip("/").split("/", 1)[0].split("?", 1)[0]
    if first.lower() == "graphql":
        raise ForbiddenRequest(
            f"La CLI solo usa la API REST de GitHub: «{path}» es GraphQL (ADR 0016)."
        )
    problem = None
    if not path:
        problem = "está vacía"
    elif "://" in path or path.startswith("/"):
        problem = "tiene que ser relativa, sin «/» delante ni esquema"
    elif path.startswith("-"):
        problem = "no puede empezar por «-»"
    elif any(not (" " < char < "\x7f") for char in path):
        problem = "solo admite ASCII visible: codifica el resto con quote()"
    elif any(char in path for char in "{}#"):
        problem = "no admite «{», «}» ni «#»: codifícalos con quote()"
    elif any(
        segment in ("", ".", "..") for segment in path.split("?", 1)[0].split("/")
    ):
        problem = "tiene un tramo vacío, «.» o «..»"
    if problem:
        raise ForbiddenRequest(f"Ruta de la API no válida («{path}»): {problem}.")
    return path


def _with_params(path: str, params: Mapping[str, Any] | None) -> str:
    if not params:
        return path
    query = urlencode({key: _param(value) for key, value in params.items()})
    return f"{path}{'&' if '?' in path else '?'}{query}"


def _param(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def next_link(header: str | None) -> str | None:
    """Path (with its query) of the ``rel="next"`` URL of a ``Link`` header."""
    if not header:
        return None
    for url, rels in _LINK.findall(header):
        if "next" in rels.split():
            parts = urlsplit(url)
            path = parts.path.lstrip("/")
            return f"{path}?{parts.query}" if parts.query else path
    return None


def _delete_allowed(path: str) -> bool:
    return any(pattern.fullmatch(path) for pattern in _ALLOWED_DELETES)


class GitHub:
    """Client for GitHub's REST API through a transport (``gh api`` by default)."""

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._transport = transport if transport is not None else default_transport()
        self._timeout = timeout
        self._sleep = sleep

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Any = None,
    ) -> Response:
        """Send one request; a ``GET`` with a 5xx is retried up to 3 times."""
        method = method.upper()
        if method not in METHODS:
            raise ForbiddenRequest(f"Método HTTP no admitido: «{method}».")
        full = check_path(_with_params(check_path(path), params))
        if method == "DELETE" and not _delete_allowed(full):
            raise ForbiddenRequest(
                f"La CLI no borra nada en GitHub: DELETE {full} no está permitido. "
                "La única excepción es quitar una relación «blocked by» entre issues."
            )
        if method in ("GET", "DELETE") and body is not None:
            raise ForbiddenRequest(f"Un {method} no lleva cuerpo ({full}).")
        request = Request(method, full, body)
        retries = 0
        while True:
            response = self._transport.send(request, self._timeout)
            if 200 <= response.status < 300:
                if response.data is None and response.text.strip():
                    raise GitHubError(
                        "GitHub devolvió una respuesta que no es JSON en "
                        f"{method} {full}.",
                        status=response.status,
                        method=method,
                        path=full,
                        detail=response.text,
                    )
                return response
            if (
                method == "GET"
                and response.status >= 500
                and retries < len(RETRY_WAITS)
            ):
                self._wait(RETRY_WAITS[retries])
                retries += 1
                continue
            raise error_for(request, response, retries)

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """JSON body of a ``GET``."""
        return self.request("GET", path, params=params).data

    def get_all(self, path: str, params: Mapping[str, Any] | None = None) -> list[Any]:
        """Every element of a paginated list, following ``Link: rel="next"``.

        ``per_page`` is 100 unless the caller gives it. Each page is one call
        (with its own retries). A page that is not a JSON array, or a ``next``
        link already visited, is a ``GitHubError``.
        """
        params = dict(params or {})
        own_query = dict(parse_qsl(urlsplit(path).query))
        if "per_page" not in params and "per_page" not in own_query:
            params["per_page"] = DEFAULT_PER_PAGE
        current = _with_params(check_path(path), params)
        seen: set[str] = set()
        items: list[Any] = []
        while True:
            seen.add(current)
            response = self.request("GET", current)
            if not isinstance(response.data, list):
                raise GitHubError(
                    f"GET {current} no devolvió una lista: no se puede paginar.",
                    status=response.status,
                    method="GET",
                    path=current,
                    detail=response.data,
                )
            items.extend(response.data)  # pyright: ignore[reportUnknownArgumentType]
            following = next_link(response.header("link"))
            if following is None:
                return items
            if following in seen:
                raise GitHubError(
                    f"La paginación de GET {path} vuelve a una página ya leída "
                    f"({following}).",
                    status=response.status,
                    method="GET",
                    path=following,
                )
            current = following

    def post(self, path: str, body: Any = None) -> Any:
        """JSON body of a ``POST`` (never retried)."""
        return self.request("POST", path, body=body).data

    def patch(self, path: str, body: Any) -> Any:
        """JSON body of a ``PATCH`` (never retried)."""
        return self.request("PATCH", path, body=body).data

    def put(self, path: str, body: Any = None) -> Any:
        """JSON body of a ``PUT`` (never retried)."""
        return self.request("PUT", path, body=body).data

    def delete(self, path: str) -> None:
        """``DELETE``, only for the routes in ``_ALLOWED_DELETES``."""
        self.request("DELETE", path)

    def _wait(self, seconds: float) -> None:
        (self._sleep or default_sleep)(seconds)


def error_for(request: Request, response: Response, retries: int = 0) -> GitHubError:
    """The ``GitHubError`` for a non-2xx answer, with a Spanish message."""
    status = response.status
    data = response.data
    where = f"{request.method} {request.path}"
    github_message = ""
    if isinstance(data, dict) and isinstance(data.get("message"), str):  # pyright: ignore[reportUnknownMemberType]
        github_message = str(data["message"])  # pyright: ignore[reportUnknownArgumentType]
    elif data is None and response.text.strip():
        github_message = response.text.strip()[:200]
    said = f": «{github_message}»" if github_message else ""
    common: dict[str, Any] = {
        "status": status,
        "method": request.method,
        "path": request.path,
        "detail": data if data is not None else response.text or None,
    }
    if _rate_limited(response, github_message):
        reset_at = _reset_at(response.header("x-ratelimit-reset"))
        retry_after = _int(response.header("retry-after"))
        when = ""
        if retry_after is not None:
            when = f"; vuelve a intentarlo dentro de {retry_after} s"
        elif reset_at is not None:
            when = f"; se renueva a las {reset_at:%H:%M:%S} UTC"
        return RateLimited(
            f"Límite de uso de la API de GitHub alcanzado (HTTP {status}) "
            f"en {where}{when}.",
            reset_at=reset_at,
            retry_after=retry_after,
            **common,
        )
    if status == 401:
        message = (
            f"GitHub no acepta las credenciales de gh (HTTP 401) en {where}: "
            "abre sesión con «gh auth login» o revisa GH_TOKEN."
        )
    elif status == 403:
        message = f"Permiso denegado (HTTP 403) en {where}{said}."
    elif status == 404:
        message = (
            f"GitHub no encuentra {request.path} (HTTP 404) en {request.method}: "
            "no existe o el token no tiene acceso."
        )
    elif status == 422:
        details = _validation_details(data)
        message = f"GitHub rechaza los datos de {where} (HTTP 422){said}"
        message += f"; {'; '.join(details)}." if details else "."
    elif status >= 500:
        tries = f" tras {retries} reintentos" if retries else ""
        message = (
            f"Error de GitHub (HTTP {status}) en {where}{tries}. "
            "Mira https://www.githubstatus.com antes de buscar el fallo."
        )
    else:
        message = f"GitHub respondió HTTP {status} en {where}{said}."
    return GitHubError(message, **common)


def _rate_limited(response: Response, github_message: str) -> bool:
    if response.status == 429:
        return True
    if response.status != 403:
        return False
    return (
        response.header("x-ratelimit-remaining") == "0"
        or response.header("retry-after") is not None
        or "rate limit" in github_message.lower()
    )


def _int(text: str | None) -> int | None:
    if text is None or not text.strip().isdigit():
        return None
    return int(text.strip())


def _reset_at(text: str | None) -> datetime | None:
    seconds = _int(text)
    return None if seconds is None else datetime.fromtimestamp(seconds, UTC)


def _validation_details(data: Any) -> list[str]:
    """``errors[]`` of a 422 as ``Resource.field: code`` (or their message)."""
    if not isinstance(data, dict):
        return []
    errors: Any = data.get("errors")  # pyright: ignore[reportUnknownMemberType]
    if not isinstance(errors, list):
        return []
    details: list[str] = []
    for error in errors:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(error, str):
            details.append(error)
        elif isinstance(error, dict):
            where = ".".join(
                str(error[key])  # pyright: ignore[reportUnknownArgumentType]
                for key in ("resource", "field")
                if error.get(key)  # pyright: ignore[reportUnknownMemberType]
            )
            what = [
                str(error[key])  # pyright: ignore[reportUnknownArgumentType]
                for key in ("code", "message")
                if error.get(key)  # pyright: ignore[reportUnknownMemberType]
            ]
            text = " ".join(what)
            details.append(f"{where}: {text}" if where and text else where or text)
    return [detail for detail in details if detail]
