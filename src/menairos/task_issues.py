"""The GitHub issue of a task: title, body, labels, fingerprint and marker.

``spec publicar`` writes one issue per task of ``hito-N.tareas.yaml`` and
recognises it later by the hidden marker at the end of its body (hito-0.md
2.4)::

    <!-- menairos:tarea=T-08 hito=0 huella=<title>.<body>.<labels> -->

The fingerprint has three parts, each the first 16 hex digits of a SHA-256:
of the title, of the generated body without the marker, and of the sorted
labels ``spec publicar`` puts. Compared whole, it says whether the task changed;
compared part by part, it says what changed, whether the current body is still
the generated one, and which ``modo:*`` label ``spec publicar`` put.

Everything here depends only on the tasks file and the repository name, never
on GitHub's state, so the same YAML always gives the same issue.
"""

import hashlib
import itertools
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
_FINGERPRINT = re.compile(
    r" huella=([0-9a-f]{16})\.([0-9a-f]{16})\.([0-9a-f]{16})",
)
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

    ``fingerprint`` is ``None`` when the part after ``hito=N`` is not a valid
    fingerprint (an unreadable marker). ``start`` and ``end`` locate it in the
    normalised body.
    """

    task: str
    milestone: int
    fingerprint: Fingerprint | None
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
    fingerprint: Fingerprint
    marker: str

    @property
    def body(self) -> str:
        """The whole body: the content, a blank line and the marker."""
        return f"{self.content}\n\n{self.marker}"


def marker_text(task: str, milestone: int, fingerprint: Fingerprint) -> str:
    """The marker line of a task."""
    return f"<!-- menairos:tarea={task} hito={milestone} huella={fingerprint} -->"


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
    tasks: Mapping[str, Mapping[str, Any]],
    *,
    milestone: int,
    repo: str,
    tasks_file: str,
) -> RenderedIssue:
    """The issue of ``task`` (with the defaults of its schema applied).

    ``tasks`` maps every task id of the milestone to its task, for the titles
    of the dependencies; ``tasks_file`` is the YAML's path from the root, with
    ``/``, from which the links of ``especificacion`` are resolved.
    """
    title = issue_title(task)
    content = _content(task, tasks, milestone, repo, tasks_file)
    names = issue_labels(task)
    fingerprint = Fingerprint(digest(title), digest(content), labels_digest(names))
    return RenderedIssue(
        task["id"],
        title,
        content,
        names,
        fingerprint,
        marker_text(task["id"], milestone, fingerprint),
    )


def _content(
    task: Mapping[str, Any],
    tasks: Mapping[str, Mapping[str, Any]],
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
        f"- **Depende de:** {_dependencies(task['depende_de'], tasks)}",
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


def _dependencies(ids: Sequence[str], tasks: Mapping[str, Mapping[str, Any]]) -> str:
    if not ids:
        return "ninguna"
    shown = [
        f"{tid} · {one_line(tasks[tid]['titulo'])}" if tid in tasks else tid
        for tid in ids
    ]
    return "; ".join(shown)


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
        parts = _FINGERPRINT.fullmatch(match["rest"])
        fingerprint = Fingerprint(*parts.groups()) if parts else None
        found.append(
            Marker(
                match["task"],
                int(match["milestone"]),
                fingerprint,
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


def previous_labels(
    fingerprint: Fingerprint, areas: Iterable[str]
) -> frozenset[str] | None:
    """The labels ``spec publicar`` put last time, recovered from its fingerprint.

    The candidates come from a closed set of values, not from the issue's
    current labels (Pedro may have changed them): ``tipo:tarea``, with or
    without ``critica``, one ``area:*`` of ``areas`` and no mode or one of the
    three. ``None`` if no candidate gives the fingerprint's third part.
    """
    for area, critical, mode in itertools.product(
        sorted(set(areas)), (False, True), (None, *labels.MODES)
    ):
        names = {labels.TASK, labels.area_label(area).name}
        if critical:
            names.add(labels.CRITICAL)
        if mode is not None:
            names.add(labels.mode_label(mode))
        if labels_digest(names) == fingerprint.labels:
            return frozenset(names)
    return None
