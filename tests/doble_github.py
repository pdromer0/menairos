"""Test double for GitHub and the guard that keeps tests away from the real one.

- ``FakeGitHub``: an in-memory GitHub, used as the transport of
  ``menairos.github.GitHub`` through the ``doble_github`` fixture of
  ``conftest.py``. Past its call limit it raises ``RunawayLoop``.
- ``RealGitHubCall``: raised by the autouse fixture of ``conftest.py`` when a
  test tries to launch ``gh``.
"""

import copy
import itertools
import re
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath, PureWindowsPath
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlencode

from menairos.github import Request, Response

_GH_NAMES = frozenset({"gh", "gh.exe"})


class RealGitHubCall(AssertionError):
    """A test tried to run the real ``gh``."""


_SHELLS = frozenset({"sh", "bash", "dash", "zsh", "ksh"})
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")


def _name(program: str) -> str:
    return PureWindowsPath(program).name.lower()


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _shell_programs(command: str) -> list[str]:
    """Programs a shell command line starts: the first word of each simple command.

    Leading ``VAR=value`` words are skipped; ``&&``, ``||``, ``;``, ``|``, ``&``
    and parentheses start a new command.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError:
        return command.split()[:1]
    programs: list[str] = []
    starts = True
    for word in words:
        if set(word) <= set("&|;()"):
            starts = True
        elif starts and not _ASSIGNMENT.fullmatch(word):
            programs.append(word)
            starts = False
    return programs


def _argv_programs(argv: list[str]) -> list[str]:
    """Programs an argv starts, looking through ``env`` and ``sh -c``."""
    if not argv:
        return []
    first = _name(argv[0])
    if first in ("env", "env.exe"):
        rest = [
            w
            for w in argv[1:]
            if not w.startswith("-") and not _ASSIGNMENT.fullmatch(w)
        ]
        return [argv[0], *_argv_programs(rest)]
    if first in _SHELLS and "-c" in argv[1:-1]:
        return [argv[0], *_shell_programs(argv[argv.index("-c") + 1])]
    return [argv[0]]


def launches_gh(args: Any, executable: Any = None, shell: bool = False) -> bool:
    """Whether a ``Popen(args, executable=..., shell=...)`` call starts ``gh``.

    It sees ``gh`` as the program, after ``env`` or leading assignments, and in
    each command of ``sh -c`` or of a ``shell=True`` line. Whatever it misses is
    caught by the fake ``gh`` that ``conftest.py`` puts first in ``PATH``.
    """
    if executable is not None and _name(_text(executable)) in _GH_NAMES:
        return True
    if isinstance(args, str | bytes | PurePath):
        text = _text(args)
        programs = _shell_programs(text) if shell else [text]
    elif isinstance(args, Sequence):
        argv = [_text(word) for word in args]  # pyright: ignore[reportUnknownVariableType]
        if shell and argv:
            programs = _shell_programs(argv[0])
        else:
            programs = _argv_programs(argv)
    else:
        return False
    return any(_name(program) in _GH_NAMES for program in programs)


class GuardedPopen(subprocess.Popen):  # pyright: ignore[reportMissingTypeArgument]
    """``subprocess.Popen`` that refuses to start ``gh`` and runs anything else."""

    def __init__(self, args: Any, *rest: Any, **kwargs: Any) -> None:
        executable = kwargs.get("executable", rest[1] if len(rest) > 1 else None)
        if launches_gh(args, executable, bool(kwargs.get("shell"))):
            raise RealGitHubCall(
                f"Un test intentó ejecutar gh de verdad: {args!r}. "
                "Usa la fixture doble_github."
            )
        super().__init__(args, *rest, **kwargs)


class RunawayLoop(BaseException):
    """The double went past its call limit: the code under test is looping.

    It derives from ``BaseException``, like ``pytest.fail``, so an
    ``except Exception`` in the code under test cannot swallow it.
    """

    def __init__(self, count: int, limit: int, last: list[Call]) -> None:
        self.count = count
        self.limit = limit
        self.last = last
        shown = "; ".join(call.describe() for call in last)
        super().__init__(
            f"El doble de GitHub pasó su tope de {limit} llamadas (van {count}): "
            f"¿un bucle? Últimas: {shown}"
        )


class UnsupportedRoute(AssertionError):
    """The code under test called something the double does not model."""


@dataclass(frozen=True)
class Call:
    """One call the double received.

    ``path`` has no query and uses the ``repos/{owner}/{repo}`` form, also for
    the ``repositories/{id}`` URLs of the ``Link`` header.
    """

    method: str
    path: str
    query: dict[str, str]
    body: Any = None

    def describe(self) -> str:
        query = f"?{urlencode(self.query)}" if self.query else ""
        return f"{self.method} {self.path}{query}"


@dataclass
class _Failure:
    status: int
    call: int | None
    method: str | None
    path: str | re.Pattern[str] | None
    times: int | None
    body: Any
    headers: dict[str, str]
    apply: bool
    used: int = 0

    def matches(self, number: int, call: Call) -> bool:
        if self.times is not None and self.used >= self.times:
            return False
        if self.call is not None and self.call != number:
            return False
        if self.method is not None and self.method.upper() != call.method:
            return False
        if isinstance(self.path, str) and self.path != call.path:
            return False
        return not (
            isinstance(self.path, re.Pattern) and not self.path.fullmatch(call.path)
        )


_MESSAGES = {
    401: "Bad credentials",
    403: "Forbidden",
    404: "Not Found",
    422: "Validation Failed",
    429: "Too Many Requests",
    500: "Server Error",
    502: "Server Error",
    503: "Service Unavailable",
}


def _error_body(
    status: int, errors: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"message": _MESSAGES.get(status, "Error")}
    if errors:
        body["errors"] = errors
    body["documentation_url"] = "https://docs.github.com/rest"
    body["status"] = str(status)
    return body


class _Reply(Exception):
    """Internal: a non-2xx answer of a route."""

    def __init__(self, status: int, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(status)
        self.response = Response(status, {}, _error_body(status, errors))


def _invalid(resource: str, field: str, code: str = "invalid") -> _Reply:
    return _Reply(422, [{"resource": resource, "code": code, "field": field}])


def _dependency_error(problem: str) -> _Reply:
    """The 422 GitHub gives for a dependency it refuses: only a message (T-08)."""
    reply = _Reply(422)
    reply.response = Response(
        422,
        {},
        {
            "message": (
                "An error occurred while adding the blocking issue to the issue. "
                f"Validation failed: {problem}"
            ),
            "documentation_url": "https://docs.github.com/rest/issues/issue-dependencies",
            "status": "422",
        },
    )
    return reply


LABEL_NAME_MAX = 50
LABEL_DESCRIPTION_MAX = 100
ISSUE_TITLE_MAX = 256
ISSUE_BODY_MAX = 65536


def _too_long(value: Any, limit: int) -> bool:
    return isinstance(value, str) and len(value) > limit


API = "https://api.github.com"


class FakeGitHub:
    """GitHub double: a transport for ``menairos.github.GitHub`` with a call limit.

    It keeps labels, milestones, issues (and pull requests, which ``/issues``
    lists too) and «blocked by» relations in memory, records every call, and
    paginates like GitHub (``per_page`` 30 by default and 100 at most, ``page``,
    and a ``Link`` header with ``repositories/{id}`` URLs, as observed in T-07).

    Faithful where callers trip: ``id`` is never the issue ``number``; issue and
    milestone lists only show open ones unless ``state`` says otherwise; a
    repeated label name (any case) or milestone title is a 422
    ``already_exists``.

    Stricter than GitHub when unsure: an issue with a label or milestone that
    does not exist is a 422, and an unknown route, query parameter or body field
    raises ``UnsupportedRoute``. GitHub's length limits (label name 50 and
    description 100 characters, issue title 256 and body 65536) are a 422.

    The dependency routes were verified in T-08 against the test repository:
    ``issue_id`` is the blocking issue's ``id``; adding answers 201 with the
    *blocked* issue; a repeated relation or an issue blocked by itself is a 422
    with only a ``message``; an unknown id is a 404; a closed blocking issue is
    accepted and listed. A blocking issue from another repository can be set up
    with ``add_foreign_blocked_by`` (its number may clash with a local one).

    Past ``limit`` calls it raises ``RunawayLoop``, and keeps raising it: the
    count only grows.
    """

    def __init__(
        self, repo: str = "ejemplo/ejemplo", *, limit: int = 500, repo_id: int = 424242
    ) -> None:
        self.repo = repo
        self.repo_id = repo_id
        self.limit = limit
        self.calls: list[Call] = []
        self.sleeps: list[float] = []
        self.labels: list[dict[str, Any]] = []
        self.milestones: list[dict[str, Any]] = []
        self.issues: dict[int, dict[str, Any]] = {}
        self.blocked_by: dict[int, list[int]] = {}
        self.foreign_blocked_by: dict[int, list[dict[str, Any]]] = {}
        self._failures: list[_Failure] = []
        self._ids = itertools.count(9001)
        self._route_table = [
            (re.compile(pattern), handlers) for pattern, handlers in self._routes()
        ]

    # ── State ────────────────────────────────────────────────────────────

    def add_label(
        self, name: str, color: str = "ededed", description: str = ""
    ) -> dict[str, Any]:
        """Add a label directly (no call is recorded)."""
        ident = next(self._ids)
        label: dict[str, Any] = {
            "id": ident,
            "node_id": f"LA_{ident}",
            "url": f"{API}/repos/{self.repo}/labels/{quote(name, safe='')}",
            "name": name,
            "color": color,
            "default": False,
            "description": description or None,
            "archived_at": None,
            "archived_by": None,
        }
        self.labels.append(label)
        return label

    def add_milestone(
        self, title: str, state: str = "open", description: str = ""
    ) -> dict[str, Any]:
        """Add a milestone directly (no call is recorded)."""
        ident = next(self._ids)
        number = len(self.milestones) + 1
        milestone: dict[str, Any] = {
            "id": ident,
            "node_id": f"MI_{ident}",
            "number": number,
            "title": title,
            "description": description or None,
            "state": state,
            "url": f"{API}/repos/{self.repo}/milestones/{number}",
            "html_url": f"https://github.com/{self.repo}/milestone/{number}",
        }
        self.milestones.append(milestone)
        return milestone

    def add_issue(
        self,
        title: str,
        body: str = "",
        labels: Sequence[str] = (),
        state: str = "open",
        milestone: int | None = None,
        pull_request: bool = False,
    ) -> dict[str, Any]:
        """Add an issue (or a pull request) directly (no call is recorded).

        Its labels and milestone must exist already (``ValueError`` if not).
        """
        missing = [name for name in labels if not self._has_label(name)]
        if missing:
            raise ValueError(
                f"add_issue: el doble no tiene las etiquetas {missing}; créalas antes "
                "con add_label"
            )
        if milestone is not None and not any(
            m["number"] == milestone for m in self.milestones
        ):
            raise ValueError(
                f"add_issue: el doble no tiene el milestone {milestone}; créalo antes "
                "con add_milestone"
            )
        ident = next(self._ids)
        number = len(self.issues) + 1
        kind = "pull" if pull_request else "issues"
        issue: dict[str, Any] = {
            "id": ident,
            "node_id": f"I_{ident}",
            "number": number,
            "title": title,
            "body": body or None,
            "state": state,
            "labels": [self._label(name) for name in labels],
            "milestone": self._milestone(milestone),
            "url": f"{API}/repos/{self.repo}/issues/{number}",
            "html_url": f"https://github.com/{self.repo}/{kind}/{number}",
        }
        if pull_request:
            issue["pull_request"] = {"url": f"{API}/repos/{self.repo}/pulls/{number}"}
        self.issues[number] = issue
        return issue

    def add_blocked_by(self, number: int, blocking_number: int) -> None:
        """Mark issue ``number`` as blocked by ``blocking_number`` (no call)."""
        missing = [n for n in (number, blocking_number) if n not in self.issues]
        if missing:
            raise ValueError(f"add_blocked_by: el doble no tiene los issues {missing}")
        self.blocked_by.setdefault(number, []).append(blocking_number)

    def add_foreign_blocked_by(
        self,
        number: int,
        *,
        repo: str = "otro/repo",
        foreign_number: int = 1,
        state: str = "open",
    ) -> dict[str, Any]:
        """Mark issue ``number`` as blocked by an issue of another repo (no call).

        Returns the foreign issue, with its own ``id``.
        """
        if number not in self.issues:
            raise ValueError(
                f"add_foreign_blocked_by: el doble no tiene el issue {number}"
            )
        ident = next(self._ids)
        foreign: dict[str, Any] = {
            "id": ident,
            "node_id": f"I_{ident}",
            "number": foreign_number,
            "title": f"Issue {foreign_number} de {repo}",
            "body": None,
            "state": state,
            "labels": [],
            "milestone": None,
            "url": f"{API}/repos/{repo}/issues/{foreign_number}",
            "repository_url": f"{API}/repos/{repo}",
            "html_url": f"https://github.com/{repo}/issues/{foreign_number}",
        }
        self.foreign_blocked_by.setdefault(number, []).append(foreign)
        return foreign

    # ── Failures and queries ─────────────────────────────────────────────

    def fail(
        self,
        status: int,
        *,
        call: int | None = None,
        method: str | None = None,
        path: str | re.Pattern[str] | None = None,
        times: int | None = 1,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        apply: bool = False,
    ) -> None:
        """Answer ``status`` to the calls that match every criterion given.

        ``call`` is the call number (from 1); ``path`` is compared without the
        query, exactly (``str``) or with ``fullmatch`` (``re.Pattern``);
        ``times=None`` fails every time. With ``apply=True`` a write is done
        before answering the error, like a failure after GitHub saved it.
        """
        self._failures.append(
            _Failure(
                status,
                call,
                method,
                path,
                times,
                body if body is not None else _error_body(status),
                dict(headers or {}),
                apply,
            )
        )

    def calls_to(self, method: str, path: str) -> list[Call]:
        """Calls with that method whose path ``fullmatch``-es the regex."""
        pattern = re.compile(path)
        return [
            call
            for call in self.calls
            if call.method == method.upper() and pattern.fullmatch(call.path)
        ]

    # ── Transport ────────────────────────────────────────────────────────

    def send(self, request: Request, timeout: float) -> Response:
        del timeout
        raw_path, _, raw_query = request.path.partition("?")
        call = Call(
            request.method,
            self._normalize(raw_path),
            dict(parse_qsl(raw_query, keep_blank_values=True)),
            request.body,
        )
        self.calls.append(call)
        if len(self.calls) > self.limit:
            raise RunawayLoop(len(self.calls), self.limit, self.calls[-5:])
        failure = next(
            (f for f in self._failures if f.matches(len(self.calls), call)), None
        )
        if failure is not None:
            failure.used += 1
            if failure.apply:
                self._answer(call)
            return Response(failure.status, failure.headers, failure.body)
        return self._answer(call)

    def _normalize(self, path: str) -> str:
        prefix = f"repositories/{self.repo_id}/"
        if path.startswith(prefix):
            return f"repos/{self.repo}/{path.removeprefix(prefix)}"
        return path

    def _answer(self, call: Call) -> Response:
        try:
            return self._route(call)
        except _Reply as reply:
            return reply.response

    def _route(self, call: Call) -> Response:
        base = f"repos/{self.repo}/"
        if not call.path.startswith(base):
            raise UnsupportedRoute(f"El doble no modela {call.describe()}")
        rest = call.path.removeprefix(base)
        method = call.method
        for pattern, handlers in self._route_table:
            match = pattern.fullmatch(rest)
            if match and method in handlers:
                return handlers[method](call, *match.groups())
        raise UnsupportedRoute(f"El doble no modela {call.describe()}")

    def _routes(self) -> list[tuple[str, dict[str, Callable[..., Response]]]]:
        return [
            ("labels", {"GET": self._list_labels, "POST": self._create_label}),
            ("labels/([^/]+)", {"GET": self._get_label}),
            (
                "milestones",
                {"GET": self._list_milestones, "POST": self._create_milestone},
            ),
            ("issues", {"GET": self._list_issues, "POST": self._create_issue}),
            ("issues/([0-9]+)", {"GET": self._get_issue, "PATCH": self._update_issue}),
            (
                "issues/([0-9]+)/dependencies/blocked_by",
                {"GET": self._list_blocked_by, "POST": self._add_blocked_by},
            ),
            (
                "issues/([0-9]+)/dependencies/blocked_by/([0-9]+)",
                {"DELETE": self._remove_blocked_by},
            ),
        ]

    # ── Helpers ──────────────────────────────────────────────────────────

    def _only(self, call: Call, *allowed: str) -> None:
        unknown = sorted(set(call.query) - {"per_page", "page", *allowed})
        if unknown:
            raise UnsupportedRoute(
                f"El doble no modela el parámetro {unknown} de {call.describe()}"
            )

    def _body(self, call: Call, *allowed: str) -> dict[str, Any]:
        body = call.body if call.body is not None else {}
        if not isinstance(body, dict):
            raise _Reply(400)
        unknown = sorted(set(body) - set(allowed))  # pyright: ignore[reportUnknownArgumentType]
        if unknown:
            raise UnsupportedRoute(
                f"El doble no modela el campo {unknown} de {call.describe()}"
            )
        return body  # pyright: ignore[reportUnknownVariableType]

    def _page(self, call: Call, items: list[dict[str, Any]]) -> Response:
        """One page of ``items`` and its ``Link`` header, as GitHub builds them."""
        try:
            per_page = min(max(int(call.query.get("per_page", "30")), 1), 100)
            page = max(int(call.query.get("page", "1")), 1)
        except ValueError:
            raise _Reply(422) from None
        pages = max(1, -(-len(items) // per_page))
        chosen = items[(page - 1) * per_page : page * per_page]
        links: list[str] = []
        if pages > 1:
            rest = call.path.removeprefix(f"repos/{self.repo}/")

            def url(number: int) -> str:
                query = {**call.query, "page": str(number)}
                return f"<{API}/repositories/{self.repo_id}/{rest}?{urlencode(query)}>"

            if page > 1:
                links.append(f'{url(page - 1)}; rel="prev"')
            if page < pages:
                links.append(f'{url(page + 1)}; rel="next"')
                links.append(f'{url(pages)}; rel="last"')
            if page > 1:
                links.append(f'{url(1)}; rel="first"')
        headers = {"Link": ", ".join(links)} if links else {}
        return Response(200, headers, copy.deepcopy(chosen))

    def _state(self, call: Call, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        state = call.query.get("state", "open")
        if state not in ("open", "closed", "all"):
            raise _Reply(422)
        return [item for item in items if state in ("all", item["state"])]

    def _has_label(self, name: str) -> bool:
        return any(label["name"].lower() == name.lower() for label in self.labels)

    def _label(self, name: str) -> dict[str, Any]:
        for label in self.labels:
            if label["name"].lower() == name.lower():
                return label
        raise _invalid("Label", "name")

    def _milestone(self, number: int | None) -> dict[str, Any] | None:
        if number is None:
            return None
        for milestone in self.milestones:
            if milestone["number"] == number:
                return milestone
        raise _invalid("Issue", "milestone")

    def _issue(self, number: int) -> dict[str, Any]:
        if number not in self.issues:
            raise _Reply(404)
        return self.issues[number]

    def _check_issue_lengths(self, body: Mapping[str, Any]) -> None:
        if _too_long(body.get("title"), ISSUE_TITLE_MAX):
            raise _invalid("Issue", "title")
        if _too_long(body.get("body"), ISSUE_BODY_MAX):
            raise _invalid("Issue", "body")

    def _created(self, item: dict[str, Any]) -> Response:
        return Response(201, {}, copy.deepcopy(item))

    # ── Routes ───────────────────────────────────────────────────────────

    def _list_labels(self, call: Call) -> Response:
        self._only(call)
        return self._page(call, self.labels)

    def _get_label(self, call: Call, name: str) -> Response:
        self._only(call)
        try:
            return Response(200, {}, copy.deepcopy(self._label(unquote(name))))
        except _Reply:
            raise _Reply(404) from None

    def _create_label(self, call: Call) -> Response:
        body = self._body(call, "name", "color", "description")
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise _invalid("Label", "name", "missing_field")
        if _too_long(name, LABEL_NAME_MAX):
            raise _invalid("Label", "name")
        if _too_long(body.get("description"), LABEL_DESCRIPTION_MAX):
            raise _invalid("Label", "description")
        if any(label["name"].lower() == name.lower() for label in self.labels):
            raise _invalid("Label", "name", "already_exists")
        return self._created(
            self.add_label(
                name, body.get("color", "ededed"), body.get("description", "")
            )
        )

    def _list_milestones(self, call: Call) -> Response:
        self._only(call, "state")
        return self._page(call, self._state(call, self.milestones))

    def _create_milestone(self, call: Call) -> Response:
        body = self._body(call, "title", "state", "description")
        title = body.get("title")
        if not isinstance(title, str) or not title.strip():
            raise _invalid("Milestone", "title", "missing_field")
        if any(milestone["title"] == title for milestone in self.milestones):
            raise _invalid("Milestone", "title", "already_exists")
        state = body.get("state", "open")
        return self._created(
            self.add_milestone(title, state, body.get("description", ""))
        )

    def _list_issues(self, call: Call) -> Response:
        self._only(call, "state", "labels")
        issues = self._state(
            call, sorted(self.issues.values(), key=lambda i: -i["number"])
        )
        wanted = [
            name.lower() for name in call.query.get("labels", "").split(",") if name
        ]
        if wanted:
            issues = [
                issue
                for issue in issues
                if set(wanted) <= {label["name"].lower() for label in issue["labels"]}
            ]
        return self._page(call, issues)

    def _create_issue(self, call: Call) -> Response:
        body = self._body(call, "title", "body", "labels", "milestone")
        title = body.get("title")
        if not isinstance(title, str) or not title.strip():
            raise _invalid("Issue", "title", "missing_field")
        self._check_issue_lengths(body)
        labels = body.get("labels", [])
        if not isinstance(labels, list) or not all(isinstance(n, str) for n in labels):  # pyright: ignore[reportUnknownVariableType]
            raise _invalid("Issue", "labels")
        for name in labels:  # pyright: ignore[reportUnknownVariableType]
            self._label(name)  # pyright: ignore[reportUnknownArgumentType]
        milestone = body.get("milestone")
        self._milestone(milestone)
        issue = self.add_issue(
            title, body.get("body") or "", labels, milestone=milestone
        )  # pyright: ignore[reportUnknownArgumentType]
        return self._created(issue)

    def _get_issue(self, call: Call, number: str) -> Response:
        self._only(call)
        return Response(200, {}, copy.deepcopy(self._issue(int(number))))

    def _update_issue(self, call: Call, number: str) -> Response:
        issue = self._issue(int(number))
        body = self._body(call, "title", "body", "state", "labels", "milestone")
        if "title" in body and (
            not isinstance(body["title"], str) or not body["title"].strip()
        ):
            raise _invalid("Issue", "title")
        if body.get("state", "open") not in ("open", "closed"):
            raise _invalid("Issue", "state")
        self._check_issue_lengths(body)
        labels = (
            [self._label(name) for name in body.get("labels", [])]
            if "labels" in body
            else None
        )
        milestone = self._milestone(body["milestone"]) if "milestone" in body else None
        for key in ("title", "body", "state"):
            if key in body:
                issue[key] = body[key]
        if labels is not None:
            issue["labels"] = labels
        if "milestone" in body:
            issue["milestone"] = milestone
        return Response(200, {}, copy.deepcopy(issue))

    def _by_id(self, ident: Any) -> int:
        for number, issue in self.issues.items():
            if issue["id"] == ident:
                return number
        raise _Reply(404)

    def _list_blocked_by(self, call: Call, number: str) -> Response:
        self._only(call)
        self._issue(int(number))
        blocking = [self.issues[n] for n in self.blocked_by.get(int(number), [])]
        blocking += self.foreign_blocked_by.get(int(number), [])
        return self._page(call, blocking)

    def _add_blocked_by(self, call: Call, number: str) -> Response:
        blocked = int(number)
        self._issue(blocked)
        body = self._body(call, "issue_id")
        ident = body.get("issue_id")
        if not isinstance(ident, int) or isinstance(ident, bool):
            raise _invalid("IssueDependency", "issue_id")
        blocking = self._by_id(ident)
        if blocking == blocked:
            raise _dependency_error(
                "Target issue cannot be the same as the source issue"
            )
        if blocking in self.blocked_by.get(blocked, []):
            raise _dependency_error("Target issue has already been taken")
        self.blocked_by.setdefault(blocked, []).append(blocking)
        # GitHub answers with the blocked issue, not the blocking one (T-08).
        return self._created(self.issues[blocked])

    def _remove_blocked_by(self, call: Call, number: str, ident: str) -> Response:
        blocked = int(number)
        self._issue(blocked)
        foreign = self.foreign_blocked_by.get(blocked, [])
        match = [issue for issue in foreign if issue["id"] == int(ident)]
        if match:
            foreign.remove(match[0])
        else:
            blocking = self._by_id(int(ident))
            if blocking not in self.blocked_by.get(blocked, []):
                raise _Reply(404)
            self.blocked_by[blocked].remove(blocking)
        return Response(200, {}, copy.deepcopy(self.issues[blocked]))
