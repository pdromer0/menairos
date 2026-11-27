"""The GitHub labels of the method (``diseno.md`` 3.4).

``spec publicar`` creates them in the repository, and the github layer of
``menairos entorno`` (T-12) will create the same ones. A label that already
exists is never changed, so colours and descriptions only matter the first
time.
"""

import re
from dataclasses import dataclass

NAME_MAX = 50
"""GitHub's limit for a label name."""
DESCRIPTION_MAX = 100
"""GitHub's limit for a label description."""

TASK = "tipo:tarea"
CRITICAL = "critica"
AREA_PREFIX = "area:"
MODE_PREFIX = "modo:"
MODES = ("manual", "didactico", "automatico")
AREA_COLOR = "c5def5"

_COLOR = re.compile(r"[0-9a-f]{6}")


@dataclass(frozen=True)
class Label:
    """A label as it is created: name, colour (6 hex digits) and description."""

    name: str
    color: str
    description: str


BASE_LABELS: tuple[Label, ...] = (
    Label(TASK, "1d76db", "Unidad de trabajo planificada del método"),
    Label("tipo:bug", "d73a4a", "Algo no funciona como debería"),
    Label("tipo:idea", "a2eeef", "Propuesta para más adelante"),
    Label(CRITICAL, "b60205", "Tarea crítica: revisión del plan y fusión con Pedro"),
    Label("modo:manual", "5319e7", "La tarea se hace en modo manual"),
    Label("modo:didactico", "5319e7", "La tarea se hace en modo didáctico"),
    Label("modo:automatico", "5319e7", "La tarea se hace en modo automático"),
    Label("en-curso", "fbca04", "Alguien trabaja en la tarea ahora mismo"),
    Label("necesita-pedro", "d93f0b", "Escalada: espera una decisión de Pedro"),
    Label(
        "aprobado-pedro", "0e8a16", "Aprobada por Pedro: desbloquea el check politica"
    ),
)
"""The labels of ``diseno.md`` 3.4, in the order they are created."""


def area_label(area: str) -> Label:
    """The ``area:*`` label of an area of the tasks file."""
    return Label(f"{AREA_PREFIX}{area}", AREA_COLOR, f"Área «{area}» de las tareas")


def mode_label(mode: str) -> str:
    """The ``modo:*`` label of a mode (``manual``, ``didactico``, ``automatico``)."""
    return f"{MODE_PREFIX}{mode}"


def is_valid(label: Label) -> bool:
    """Whether GitHub accepts the label: lengths and colour."""
    return (
        0 < len(label.name) <= NAME_MAX
        and len(label.description) <= DESCRIPTION_MAX
        and _COLOR.fullmatch(label.color) is not None
    )
