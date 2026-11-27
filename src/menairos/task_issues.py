"""The GitHub issue of a task: title, body, labels, fingerprint and marker.

``spec publicar`` writes one issue per task of ``hito-N.tareas.yaml`` and
recognises it later by the hidden marker at the end of its body (hito-0.md
2.4)::

    <!-- menairos:tarea=T-08 hito=0 modo=didactico huella=<title>.<body>.<labels> -->

The fingerprint has three parts, each the first 16 hex digits of a SHA-256:
of the title, of the generated body without the marker, and of the sorted
labels of the YAML (its ``modo:*`` included, even when the issue keeps another
one put by hand). Compared whole, it says whether the task changed; compared
part by part, it says what changed and whether the current body is still the
generated one.

``modo=`` names the ``modo:*`` label that is ``spec publicar``'s: the task's
mode, if the issue has it once published. It is missing when the task sets no
mode or the issue lacks it (another mode put by hand, or removed by hand). It
is worked out only when the marker is written: on a new issue, or when the
fingerprint changed.

The title, the body and the fingerprint depend only on the task, its milestone
and the repository name, never on GitHub's state; only ``modo=`` looks at the
issue.
"""

import hashlib
import posixpath
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from menairos import labels, markdown

PART_LENGTH = 16
TITLE_MAX = 256
"""GitHub's limit for an issue title."""
BODY_MAX = 65536
"""GitHub's limit for an issue body."""

_MARKER = re.compile(
    r"^<!-- menairos:tarea=(?P<task>[^\s>]+) hito=(?P<milestone>0|[1-9][0-9]*)"
    r"(?P<rest>(?: [^\n]*?)?) -->$",
    re.MULTILINE,
)
_STATE = re.compile(
    rf"(?: modo=(?P<mode>{'|'.join(map(re.escape, labels.MODES))}))?"
    r" huella=(?P<title>[0-9a-f]{16})\.(?P<body>[0-9a-f]{16})"
    r"\.(?P<labels>[0-9a-f]{16})"
)
"""What follows ``hito=N`` in a readable marker: the mode, if any, and the
fingerprint."""
_LINE_BREAK = re.compile(r"[ \t]*\n[ \t]*")
_ANY_LINE_BREAK = re.compile(r"\r\n|\r|\n")  # as menairos.markdown splits lines
_MODE_NAMES = {"manual": "manual", "didactico": "didáctico", "automatico": "automático"}
_WHO = {"claude": "Claude", "codex": "Codex"}


def digest(text: str) -> str:
    """First 16 hex digits of the SHA-256 of ``text`` (UTF-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:PART_LENGTH]


def labels_digest(names: Iterable[str]) -> str:
    """Digest of a set of label names: lower-cased, sorted, one per line."""
    return digest("\n".join(sorted({name.lower() for name in names})))


@dataclass(frozen=True)
class Fingerprint:
    """The three parts of the fingerprint of an issue."""

    title: str
    body: str
    labels: str

    def __str__(self) -> str:
        return f"{self.title}.{self.body}.{self.labels}"


@dataclass(frozen=True)
class Marker:
    """A marker found in an issue body.

    ``fingerprint`` and ``mode`` are both ``None`` when the part after
    ``hito=N`` cannot be read (an unreadable marker): a mode is never read
    without its fingerprint. ``start`` and ``end`` locate it in the normalised
    body.
    """

    task: str
    milestone: int
    fingerprint: Fingerprint | None
    mode: str | None
    start: int
    end: int


@dataclass(frozen=True)
class RenderedIssue:
    """What ``spec publicar`` writes for a task."""

    task: str
    title: str
    content: str
    """The body without the marker."""
    labels: tuple[str, ...]
    """Sorted and lower-cased."""
    mode: str | None
    """The task's mode."""
    fingerprint: Fingerprint
    marker: str
    """The marker of a new issue, which gets every label of the YAML."""

    @property
    def body(self) -> str:
        """The whole body of a new issue."""
        return self.body_with(self.marker)

    def body_with(self, marker: str) -> str:
        """The content, a blank line and ``marker``."""
        return f"{self.content}\n\n{marker}"


def marker_text(
    task: str, milestone: int, mode: str | None, fingerprint: Fingerprint
) -> str:
    """The marker line of a task; ``mode`` is the ``modo:*`` that is publicar's."""
    shown = f" modo={mode}" if mode is not None else ""
    return (
        f"<!-- menairos:tarea={task} hito={milestone}{shown} huella={fingerprint} -->"
    )


def one_line(text: str) -> str:
    """``text`` with its line breaks (and the blanks around them) as one space."""
    return _LINE_BREAK.sub(" ", text.replace("\r\n", "\n")).strip()


def issue_title(task: Mapping[str, Any]) -> str:
    """``T-08 · title of the task``."""
    return f"{task['id']} · {one_line(task['titulo'])}"


def issue_labels(task: Mapping[str, Any]) -> tuple[str, ...]:
    """The labels ``spec publicar`` puts on the issue of a task, sorted."""
    names = {labels.TASK, labels.area_label(task["area"]).name}
    if task["critica"]:
        names.add(labels.CRITICAL)
    if task["modo"] is not None:
        names.add(labels.mode_label(task["modo"]))
    return tuple(sorted(names))


def render(
    task: Mapping[str, Any],
    *,
    milestone: int,
    repo: str,
    tasks_file: str,
) -> RenderedIssue:
    """The issue of ``task`` (with the defaults of its schema applied).

    ``tasks_file`` is the YAML's path from the root, with ``/``, from which the
    links of ``especificacion`` are resolved. Nothing of another task goes in:
    renaming a task must not rewrite the bodies of the tasks that depend on it.
    """
    title = issue_title(task)
    content = _content(task, milestone, repo, tasks_file)
    names = issue_labels(task)
    fingerprint = Fingerprint(digest(title), digest(content), labels_digest(names))
    return RenderedIssue(
        task["id"],
        title,
        content,
        names,
        task["modo"],
        fingerprint,
        marker_text(task["id"], milestone, task["modo"], fingerprint),
    )


def _content(
    task: Mapping[str, Any],
    milestone: int,
    repo: str,
    tasks_file: str,
) -> str:
    lines = [f"Tarea **{task['id']}** del hito {milestone}, área `{task['area']}`."]
    if task["critica"]:
        lines += ["", f"**Crítica:** {one_line(task.get('motivo_critica') or '')}"]
    lines += ["", "## Especificación", ""]
    base = posixpath.dirname(tasks_file)
    for link in task["especificacion"]:
        name, _, anchor = link.partition("#")
        path = posixpath.normpath(posixpath.join(base, name))
        url = f"https://github.com/{repo}/blob/main/{quote(path)}"
        if anchor:
            url += f"#{anchor}"
        shown = link.replace("[", "\\[").replace("]", "\\]")
        lines.append(f"- [{shown}]({url})")
    lines += ["", "## Criterios de aceptación", ""]
    lines += [
        f"- [ ] {_list_item(criterion)}" for criterion in task["criterios_aceptacion"]
    ]
    lines += [
        "",
        "## Datos",
        "",
        f"- **Rama:** `{task['rama']}`",
        f"- **Depende de:** {_dependencies(task['depende_de'])}",
        "- **Necesita el portátil:** "
        + ("sí (donde: local)" if task["donde"] == "local" else "no"),
        f"- **La hace:** {_WHO.get(task['quien'], task['quien'])}",
        f"- **Modo:** {_mode(task['modo'])}",
        "",
        f"*Generado por `menairos spec publicar` desde `{tasks_file}`: los cambios "
        "se hacen allí.*",
    ]
    return "\n".join(lines).rstrip()


def _list_item(text: str) -> str:
    """A list item's text: lines after the first indented, so they stay inside."""
    first, *rest = text.replace("\r\n", "\n").strip().split("\n")
    return "\n".join([first, *(f"  {line}" if line.strip() else "" for line in rest)])


def _dependencies(ids: Sequence[str]) -> str:
    """Only the ids: the native «blocked by» relation already shows the titles."""
    return ", ".join(ids) if ids else "ninguna"


def _mode(mode: str | None) -> str:
    if mode is None:
        return "el del hito"
    return f"{_MODE_NAMES.get(mode, mode)} (etiqueta `{labels.mode_label(mode)}`)"


# ── Reading an issue that already exists ────────────────────────────────────


def normalize_body(body: str | None) -> str:
    """The body as ``spec publicar`` compares it: ``None`` is empty, CRLF is LF."""
    return (body or "").replace("\r\n", "\n")


def find_markers(body: str) -> list[Marker]:
    """Every marker of a normalised body: a whole line, outside fenced code.

    A marker inside a code block is a quotation (a bug that copies an issue's
    body), not the issue's own marker.
    """
    code = {line.number for line in markdown.parse(body).lines if line.in_code}
    found: list[Marker] = []
    for match in _MARKER.finditer(body):
        if len(_ANY_LINE_BREAK.findall(body, 0, match.start())) + 1 in code:
            continue
        state = _STATE.fullmatch(match["rest"])
        found.append(
            Marker(
                match["task"],
                int(match["milestone"]),
                Fingerprint(state["title"], state["body"], state["labels"])
                if state
                else None,
                state["mode"] if state else None,
                match.start(),
                match.end(),
            )
        )
    return found


def content_without(body: str, marker: Marker) -> str:
    """A normalised body without ``marker`` and without trailing blanks."""
    return (body[: marker.start] + body[marker.end :]).rstrip()


def with_marker(body: str, marker: Marker, new_marker: str) -> str:
    """A normalised body with ``marker`` replaced by ``new_marker``."""
    return body[: marker.start] + new_marker + body[marker.end :]
