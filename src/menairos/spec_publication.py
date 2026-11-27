"""``menairos spec publicar``: publish a milestone's tasks to GitHub (hito-0.md 2.4).

:func:`publish_spec` checks the specification with ``spec validar``, reads
GitHub (labels, milestones, issues and their «blocked by» relations), works out
everything it has to do and then writes it, in this order: labels, milestone,
issues and dependencies. With ``dry_run`` it only reads.

It never closes or deletes an issue, a label or a milestone. The only thing it
removes is a «blocked by» relation between two issues of the milestone's tasks
(those with a marker of this milestone, also of tasks deleted from the YAML):
dependencies between tasks are managed only in ``depende_de``.

Idempotence rests on the marker of :mod:`menairos.task_issues`:

- same fingerprint: the issue is not touched, even if edited by hand;
- different fingerprint, open issue: it is read again and only the parts that
  changed are rewritten (title, body, labels), with the new marker;
- different fingerprint, closed issue: nothing is touched, with a warning.

Relations are synchronised on every run, whatever the fingerprint says, so a
run cut short between the issues and the dependencies is completed by the next.
"""

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from menairos import labels as catalog
from menairos.github import GitHub, GitHubError
from menairos.schemas import apply_defaults, load_document
from menairos.spec_validation import CONFIG_FILE, Finding, validate_spec
from menairos.task_issues import (
    BODY_MAX,
    TITLE_MAX,
    Marker,
    RenderedIssue,
    content_without,
    digest,
    find_markers,
    normalize_body,
    previous_labels,
    render,
    with_marker,
)

WRITE_INTERVAL = 1.0
"""Seconds between two writes, as GitHub asks (P7 of T-08)."""

type Item = dict[str, Any]


@dataclass
class Publication:
    """What ``spec publicar`` did (or, with ``dry_run``, would do).

    Every element of ``created``, ``updated``, ``removed`` and ``unchanged`` has
    a ``tipo`` (``etiqueta``, ``milestone``, ``issue`` or ``dependencia``);
    warnings and errors have a ``codigo`` and a ``mensaje``.
    """

    repo: str | None
    milestone: int
    dry_run: bool
    created: list[Item] = field(default_factory=list[Item])
    updated: list[Item] = field(default_factory=list[Item])
    removed: list[Item] = field(default_factory=list[Item])
    unchanged: list[Item] = field(default_factory=list[Item])
    warnings: list[Item] = field(default_factory=list[Item])
    errors: list[Item] = field(default_factory=list[Item])

    @property
    def ok(self) -> bool:
        """True if nothing failed (warnings do not count)."""
        return not self.errors

    @property
    def writes(self) -> int:
        """Writes done (or that would be done): created, updated and removed."""
        return len(self.created) + len(self.updated) + len(self.removed)


def notice(
    code: str, message: str, task: str | None = None, number: int | None = None
) -> Item:
    """A warning or an error of the report."""
    item: Item = {"codigo": code, "mensaje": message}
    if task is not None:
        item["tarea"] = task
    if number is not None:
        item["numero"] = number
    return item


def publish_spec(
    root: Path,
    milestone: int | None = None,
    *,
    dry_run: bool = False,
    client: GitHub | None = None,
) -> Publication:
    """Publish (or, with ``dry_run``, plan) the issues of a milestone.

    Raises :class:`menairos.spec_validation.UsageError` when ``spec validar``
    cannot run (exit code 2 in the CLI). Errors of the specification, a
    repeated marker, a GitHub limit or a failed call end up in ``errors``.
    """
    validation = validate_spec(root, milestone)
    root = Path(os.path.normpath(root))  # as validate_spec does
    publication = Publication(None, validation.milestone, dry_run)
    publication.warnings += [_finding(f) for f in validation.warnings]
    if not validation.ok:
        publication.errors += [_finding(f) for f in validation.errors]
        return publication

    config = apply_defaults("menairos", load_document(root / CONFIG_FILE))
    spec = apply_defaults("tareas", load_document(root / validation.tasks_file))
    publication.repo = config["proyecto"]["repo"]
    publisher = _Publisher(
        client if client is not None else GitHub(write_interval=WRITE_INTERVAL),
        config["proyecto"]["repo"],
        validation.milestone,
        spec,
        validation.tasks_file,
        publication,
    )
    publisher.run()
    return publication


def _finding(finding: Finding) -> Item:
    return {
        "codigo": finding.code,
        "mensaje": finding.message,
        "fichero": finding.file,
        "ruta": finding.path,
    }


@dataclass
class _Existing:
    """An issue of this milestone's tasks, found by its marker."""

    issue: dict[str, Any]
    marker: Marker
    body: str
    """The normalised body (``None`` → empty, CRLF → LF)."""

    @property
    def number(self) -> int:
        return self.issue["number"]

    @property
    def id(self) -> int:
        return self.issue["id"]

    @property
    def open(self) -> bool:
        return self.issue["state"] == "open"


@dataclass
class _Ref:
    """The issue of a task: one that exists, or one to create (ids filled later)."""

    task: str
    id: int | None
    number: int | None


@dataclass
class _Dependencies:
    """The relations to remove and add on the issue of one task."""

    task: str
    remove: list[dict[str, Any]]
    add: list[str]


class _Stop(Exception):
    """Internal: the run stops; the reason is already in the report's errors."""


class _Publisher:
    def __init__(
        self,
        client: GitHub,
        repo: str,
        milestone: int,
        spec: Mapping[str, Any],
        tasks_file: str,
        publication: Publication,
    ) -> None:
        self.client = client
        self.repo = repo
        self.base = f"repos/{repo}"
        self.milestone = milestone
        self.milestone_title = spec["titulo"].strip()
        self.tasks: list[Mapping[str, Any]] = spec["tareas"]
        by_id = {task["id"]: task for task in self.tasks}
        self.rendered: dict[str, RenderedIssue] = {
            task["id"]: render(
                task, by_id, milestone=milestone, repo=repo, tasks_file=tasks_file
            )
            for task in self.tasks
        }
        self.areas = list(dict.fromkeys(task["area"] for task in self.tasks))
        self.wanted_labels = [
            *catalog.BASE_LABELS,
            *(catalog.area_label(area) for area in self.areas),
        ]
        self.out = publication
        self.dry_run = publication.dry_run
        # Filled while reading.
        self.label_names: dict[str, str] = {}
        self.existing: dict[str, _Existing] = {}
        self.orphans: list[_Existing] = []
        self.owned_ids: dict[int, str] = {}
        self.blocked_by: dict[str, list[dict[str, Any]]] = {}
        self.refs: dict[str, _Ref] = {}
        self.milestone_number: int | None = None
        self.pending_write = ""

    # ── Run ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            self._check_limits()
            self._read()
            plan = self._plan()
            if not self.dry_run:
                self._apply(*plan)
        except _Stop:
            return
        except GitHubError as error:
            message = error.message
            if self.pending_write:
                message += (
                    f" Escritura con resultado desconocido: {self.pending_write}; "
                    "puede que GitHub la guardara. La siguiente ejecución lo comprueba "
                    "y completa lo que falta, sin duplicar nada."
                )
            elif self.dry_run or self.out.writes == 0:
                message += " No se ha escrito nada en GitHub."
            self.out.errors.append(notice("github", message))

    def _stop(self, item: Item) -> None:
        self.out.errors.append(item)
        raise _Stop

    # ── Limits ──────────────────────────────────────────────────────────

    def _check_limits(self) -> None:
        found: list[Item] = []
        for label in self.wanted_labels:
            if not catalog.is_valid(label):
                found.append(
                    notice(
                        "limite",
                        f"la etiqueta «{label.name}» tiene {len(label.name)} "
                        f"caracteres y GitHub admite {catalog.NAME_MAX}: acorta el "
                        "área en el YAML",
                    )
                )
        for task, issue in self.rendered.items():
            if len(issue.title) > TITLE_MAX:
                found.append(
                    notice(
                        "limite",
                        f"el título del issue tiene {len(issue.title)} caracteres y "
                        f"GitHub admite {TITLE_MAX}",
                        task,
                    )
                )
            if len(issue.body) > BODY_MAX:
                found.append(
                    notice(
                        "limite",
                        f"el cuerpo del issue tiene {len(issue.body)} caracteres y "
                        f"GitHub admite {BODY_MAX}",
                        task,
                    )
                )
        if found:
            self.out.errors += found
            raise _Stop

    # ── Reading ─────────────────────────────────────────────────────────

    def _read(self) -> None:
        for label in self.client.get_all(f"{self.base}/labels"):
            self.label_names.setdefault(label["name"].lower(), label["name"])
        milestones = self.client.get_all(f"{self.base}/milestones", {"state": "all"})
        issues = [
            issue
            for issue in self.client.get_all(f"{self.base}/issues", {"state": "all"})
            if not issue.get("pull_request")
        ]
        self._find_milestone(milestones)
        self._find_issues(issues)
        for task in self.tasks:
            found = self.existing.get(task["id"])
            if found is not None and found.open:
                self.blocked_by[task["id"]] = self.client.get_all(
                    f"{self.base}/issues/{found.number}/dependencies/blocked_by"
                )
        self._possible_duplicates(issues)

    def _find_milestone(self, milestones: Sequence[Mapping[str, Any]]) -> None:
        wanted = self.milestone_title.casefold()
        for milestone in milestones:
            if milestone["title"].strip().casefold() == wanted:
                self.milestone_number = milestone["number"]
                item = {
                    "tipo": "milestone",
                    "titulo": milestone["title"],
                    "numero": milestone["number"],
                }
                self.out.unchanged.append(item)
                if milestone["state"] != "open":
                    self.out.warnings.append(
                        notice(
                            "milestone-cerrado",
                            f"el milestone «{milestone['title']}» "
                            f"(#{milestone['number']}) está cerrado: los issues nuevos "
                            "se le asignan igual",
                        )
                    )
                return

    def _find_issues(self, issues: Sequence[dict[str, Any]]) -> None:
        by_task: dict[str, list[_Existing]] = {}
        repeated: list[Item] = []
        for issue in issues:
            body = normalize_body(issue.get("body"))
            markers = [m for m in find_markers(body) if m.milestone == self.milestone]
            if len(markers) > 1:
                repeated.append(
                    notice(
                        "marca-repetida",
                        f"el issue #{issue['number']} lleva {len(markers)} marcas del "
                        f"hito {self.milestone} "
                        f"({', '.join(m.task for m in markers)}): deja solo una",
                        number=issue["number"],
                    )
                )
            elif markers:
                by_task.setdefault(markers[0].task, []).append(
                    _Existing(issue, markers[0], body)
                )
        for task, found in by_task.items():
            if len(found) > 1:
                numbers = " y ".join(f"#{n}" for n in sorted(e.number for e in found))
                repeated.append(
                    notice(
                        "marca-repetida",
                        f"los issues {numbers} llevan la misma marca de {task}: "
                        "deja la marca en uno solo",
                        task,
                    )
                )
        if repeated:
            for item in repeated:
                item["mensaje"] += ". No se ha escrito nada en GitHub."
            self.out.errors += repeated
            raise _Stop
        wanted = {task["id"] for task in self.tasks}
        for task, [found] in by_task.items():
            self.owned_ids[found.id] = task
            if task in wanted:
                self.existing[task] = found
            else:
                self.orphans.append(found)

    def _possible_duplicates(self, issues: Sequence[Mapping[str, Any]]) -> None:
        marked = {found.number for found in self.existing.values()} | {
            found.number for found in self.orphans
        }
        by_title: dict[str, list[int]] = {}
        for issue in issues:
            if issue["number"] not in marked:
                by_title.setdefault(issue["title"], []).append(issue["number"])
        for task in self.tasks:
            if task["id"] in self.existing:
                continue
            for number in by_title.get(self.rendered[task["id"]].title, []):
                self.out.warnings.append(
                    notice(
                        "posible-duplicado",
                        f"el issue #{number} tiene el título de {task['id']} pero "
                        "no su marca: se crea uno nuevo. Si era el mismo, devuélvele "
                        "la marca y cierra el nuevo",
                        task["id"],
                        number,
                    )
                )

    # ── Plan ────────────────────────────────────────────────────────────

    def _plan(
        self,
    ) -> tuple[list[catalog.Label], bool, list[str], list[str], list[_Dependencies]]:
        new_labels = [
            label
            for label in self.wanted_labels
            if label.name.lower() not in self.label_names
        ]
        for label in self.wanted_labels:
            if label.name.lower() in self.label_names:
                self.out.unchanged.append({"tipo": "etiqueta", "nombre": label.name})
        to_create: list[str] = []
        to_update: list[str] = []
        for task in self.tasks:
            tid = task["id"]
            found = self.existing.get(tid)
            if found is None:
                to_create.append(tid)
                self.refs[tid] = _Ref(tid, None, None)
                continue
            self.refs[tid] = _Ref(tid, found.id, found.number)
            same = found.marker.fingerprint == self.rendered[tid].fingerprint
            if same:
                self.out.unchanged.append(self._issue_item(tid, found.number))
            elif not found.open:
                self.out.warnings.append(
                    notice(
                        "issue-cerrado",
                        f"la tarea cambió, pero su issue #{found.number} está cerrado: "
                        "no se toca",
                        tid,
                        found.number,
                    )
                )
            else:
                to_update.append(tid)
        for orphan in self.orphans:
            self.out.warnings.append(
                notice(
                    "tarea-borrada",
                    f"el issue #{orphan.number} es de {orphan.marker.task}, que ya no "
                    "está en el YAML: no se cierra ni se borra",
                    orphan.marker.task,
                    orphan.number,
                )
            )
        create_milestone = bool(to_create) and self.milestone_number is None
        dependencies = [self._dependencies(task) for task in self.tasks]
        if self.dry_run:
            self._report_dry_run(new_labels, create_milestone, to_create, to_update)
            for planned in dependencies:
                self._report_dependencies(planned)
        return (
            new_labels,
            create_milestone,
            to_create,
            to_update,
            [d for d in dependencies if d.remove or d.add],
        )

    def _dependencies(self, task: Mapping[str, Any]) -> _Dependencies:
        tid = task["id"]
        found = self.existing.get(tid)
        if found is not None and not found.open:
            return _Dependencies(tid, [], [])
        current = self.blocked_by.get(tid, [])
        current_ids = {issue["id"] for issue in current}
        wanted_ids = {self.refs[dep].id for dep in task["depende_de"]}
        remove = [
            issue
            for issue in current
            if issue["id"] in self.owned_ids and issue["id"] not in wanted_ids
        ]
        add: list[str] = []
        for dep in task["depende_de"]:
            ref = self.refs[dep]
            if ref.id is not None and ref.id in current_ids:
                self.out.unchanged.append(self._dependency_item(tid, dep, ref.number))
            else:
                add.append(dep)
        return _Dependencies(tid, remove, add)

    # ── Writing ─────────────────────────────────────────────────────────

    def _apply(
        self,
        new_labels: list[catalog.Label],
        create_milestone: bool,
        to_create: list[str],
        to_update: list[str],
        dependencies: list[_Dependencies],
    ) -> None:
        for label in new_labels:
            self._write(f"crear la etiqueta «{label.name}»")
            self.client.post(
                f"{self.base}/labels",
                {
                    "name": label.name,
                    "color": label.color,
                    "description": label.description,
                },
            )
            self.label_names[label.name.lower()] = label.name
            self._written({"tipo": "etiqueta", "nombre": label.name}, self.out.created)
        if create_milestone:
            self._write(f"crear el milestone «{self.milestone_title}»")
            created = self.client.post(
                f"{self.base}/milestones", {"title": self.milestone_title}
            )
            self.milestone_number = created["number"]
            self._written(
                {
                    "tipo": "milestone",
                    "titulo": self.milestone_title,
                    "numero": created["number"],
                },
                self.out.created,
            )
        updates = set(to_update)
        creates = set(to_create)
        for task in self.tasks:
            tid = task["id"]
            if tid in creates:
                self._create_issue(tid)
            elif tid in updates:
                self._update_issue(tid)
        for planned in dependencies:
            self._write_dependencies(planned)

    def _write(self, what: str) -> None:
        self.pending_write = what

    def _written(self, item: Item, where: list[Item]) -> None:
        self.pending_write = ""
        where.append(item)

    def _create_issue(self, tid: str) -> None:
        issue = self.rendered[tid]
        self._write(f"crear el issue de {tid}")
        created = self.client.post(
            f"{self.base}/issues",
            {
                "title": issue.title,
                "body": issue.body,
                "labels": [self.label_names.get(n, n) for n in issue.labels],
                "milestone": self.milestone_number,
            },
        )
        self.refs[tid] = _Ref(tid, created["id"], created["number"])
        self._written(self._issue_item(tid, created["number"]), self.out.created)

    def _update_issue(self, tid: str) -> None:
        number = self.existing[tid].number
        fresh = self.client.get(f"{self.base}/issues/{number}")
        body = normalize_body(fresh.get("body"))
        markers = [
            m
            for m in find_markers(body)
            if m.milestone == self.milestone and m.task == tid
        ]
        if fresh["state"] != "open" or len(markers) != 1:
            self.out.warnings.append(
                notice(
                    "issue-cambiado",
                    f"el issue #{number} cambió durante la publicación (se cerró o "
                    "perdió su marca): no se toca",
                    tid,
                    number,
                )
            )
            return
        found = _Existing(fresh, markers[0], body)
        if found.marker.fingerprint == self.rendered[tid].fingerprint:
            self.out.unchanged.append(self._issue_item(tid, number))
            return
        patch, changes = self._patch(tid, found)
        self._write(f"actualizar el issue #{number} de {tid}")
        self.client.patch(f"{self.base}/issues/{number}", patch)
        item = {**self._issue_item(tid, number), "cambios": changes}
        self._written(item, self.out.updated)

    def _write_dependencies(self, planned: _Dependencies) -> None:
        ref = self.refs[planned.task]
        for blocking in planned.remove:
            self._write(
                f"quitar la dependencia de #{ref.number} con #{blocking['number']}"
            )
            self.client.delete(
                f"{self.base}/issues/{ref.number}/dependencies/blocked_by/{blocking['id']}"
            )
            item = self._dependency_item(
                planned.task, self.owned_ids.get(blocking["id"]), blocking["number"]
            )
            self._written(item, self.out.removed)
        for dep in planned.add:
            blocking = self.refs[dep]
            self._write(f"añadir la dependencia de {planned.task} con {dep}")
            self.client.post(
                f"{self.base}/issues/{ref.number}/dependencies/blocked_by",
                {"issue_id": blocking.id},
            )
            item = self._dependency_item(planned.task, dep, blocking.number)
            self._written(item, self.out.created)

    # ── The patch of an issue that changed ──────────────────────────────

    def _patch(self, tid: str, found: _Existing) -> tuple[dict[str, Any], list[str]]:
        """The fields to send to bring ``found`` up to date, and what changes."""
        new = self.rendered[tid]
        old = found.marker.fingerprint
        number = found.number
        patch: dict[str, Any] = {}
        changes: list[str] = []
        if old is None:
            self.out.warnings.append(
                notice(
                    "marca-ilegible",
                    f"la huella de la marca del issue #{number} no se puede leer: se "
                    "reescribe como si hubiera cambiado todo",
                    tid,
                    number,
                )
            )
        title = found.issue["title"]
        if (old is None or old.title != new.fingerprint.title) and title != new.title:
            patch["title"] = new.title
            changes.append("titulo")
            if old is not None and digest(title) != old.title:
                self.out.warnings.append(
                    notice(
                        "titulo-reescrito",
                        f"se ha reescrito un título cambiado a mano en el issue "
                        f"#{number}: «{title}» pasa a «{new.title}»",
                        tid,
                        number,
                    )
                )
        content = content_without(found.body, found.marker)
        if old is None or old.body != new.fingerprint.body:
            patch["body"] = new.body
            if content != new.content:
                changes.append("cuerpo")
                edited = old is None or digest(content) != old.body
                if edited:
                    self.out.warnings.append(
                        notice(
                            "cuerpo-reescrito",
                            f"se ha reescrito un cuerpo editado a mano en el issue "
                            f"#{number}",
                            tid,
                            number,
                        )
                    )
        else:
            patch["body"] = with_marker(found.body, found.marker, new.marker)
        if old is None or old.labels != new.fingerprint.labels:
            names = self._labels(tid, found)
            if names is not None:
                patch["labels"] = names
                changes.append("etiquetas")
        if not changes:
            changes.append("marca")
        return patch, changes

    def _labels(self, tid: str, found: _Existing) -> list[str] | None:
        """The issue's new label list, or ``None`` if it does not change."""
        new = self.rendered[tid]
        old = found.marker.fingerprint
        current = [label["name"] for label in found.issue["labels"]]
        present = {name.lower() for name in current}
        wanted = set(new.labels)
        issue_areas = [
            name.removeprefix(catalog.AREA_PREFIX)
            for name in present
            if name.startswith(catalog.AREA_PREFIX)
        ]
        before = (
            previous_labels(old, [*self.areas, *issue_areas])
            if old is not None
            else None
        )
        if before is not None:
            remove = {name for name in present if name in before and name not in wanted}
        else:
            remove = {
                name for name in present if _always_ours(name) and name not in wanted
            }
        add = [name for name in new.labels if name not in present]
        hand_modes = sorted(
            name
            for name in present
            if name.startswith(catalog.MODE_PREFIX)
            and name not in remove
            and name not in wanted
        )
        mode = next((n for n in add if n.startswith(catalog.MODE_PREFIX)), None)
        if mode is not None and hand_modes:
            add.remove(mode)
            self.out.warnings.append(
                notice(
                    "modo-a-mano",
                    f"el issue #{found.number} tiene {', '.join(hand_modes)} puesto a "
                    f"mano y la tarea fija {mode}: se deja el de Pedro",
                    tid,
                    found.number,
                )
            )
        if not remove and not add:
            return None
        kept = _unique(name for name in current if name.lower() not in remove)
        return [*kept, *(self.label_names.get(name, name) for name in add)]

    # ── Report ──────────────────────────────────────────────────────────

    def _issue_item(self, tid: str, number: int | None) -> Item:
        return {
            "tipo": "issue",
            "tarea": tid,
            "numero": number,
            "titulo": self.rendered[tid].title,
        }

    def _dependency_item(self, tid: str, dep: str | None, blocking: int | None) -> Item:
        return {
            "tipo": "dependencia",
            "tarea": tid,
            "numero": self.refs[tid].number,
            "depende_de": dep,
            "bloqueado_por": blocking,
        }

    def _report_dry_run(
        self,
        new_labels: Iterable[catalog.Label],
        create_milestone: bool,
        to_create: Iterable[str],
        to_update: Iterable[str],
    ) -> None:
        self.out.created += [{"tipo": "etiqueta", "nombre": n.name} for n in new_labels]
        if create_milestone:
            self.out.created.append(
                {"tipo": "milestone", "titulo": self.milestone_title, "numero": None}
            )
        self.out.created += [self._issue_item(tid, None) for tid in to_create]
        for tid in to_update:
            found = self.existing[tid]
            _, changes = self._patch(tid, found)
            self.out.updated.append(
                {**self._issue_item(tid, found.number), "cambios": changes}
            )

    def _report_dependencies(self, planned: _Dependencies) -> None:
        for blocking in planned.remove:
            self.out.removed.append(
                self._dependency_item(
                    planned.task, self.owned_ids.get(blocking["id"]), blocking["number"]
                )
            )
        for dep in planned.add:
            self.out.created.append(
                self._dependency_item(planned.task, dep, self.refs[dep].number)
            )


def _always_ours(name: str) -> bool:
    """Labels only ``spec publicar`` puts (diseno.md 3.4): never a ``modo:*``."""
    return name in (catalog.TASK, catalog.CRITICAL) or name.startswith(
        catalog.AREA_PREFIX
    )


def _unique(names: Iterable[str]) -> list[str]:
    """``names`` without repeats, whatever their case, in order."""
    seen: set[str] = set()
    kept: list[str] = []
    for name in names:
        if name.lower() not in seen:
            seen.add(name.lower())
            kept.append(name)
    return kept
