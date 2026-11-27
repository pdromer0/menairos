"""Steps, reports and the machine of ``menairos entorno`` (hito-0.md 3.4).

Every step ends in one of four states: ``ok`` (it was already there),
``hecho`` (done now), ``manual`` (it is the user's turn, with the exact order)
or ``error``. Everything the layers ask the machine goes through a
:class:`System`; the tests replace :func:`default_system` with a double.
"""

import os
import shutil
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from menairos import github

STATES = ("ok", "hecho", "manual", "error")
GREEN = frozenset({"ok", "hecho"})
_TAIL = 20
GIT_LOCATION = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
        "GIT_OBJECT_DIRECTORY",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_IMPLICIT_WORK_TREE",
        "GIT_GRAFT_FILE",
        "GIT_INDEX_FILE",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_REPLACE_REF_BASE",
        "GIT_PREFIX",
        "GIT_SHALLOW_FILE",
        "GIT_COMMON_DIR",
    }
)
"""``git rev-parse --local-env-vars`` (git 2.43): what points git to another repo.

Run from a git hook, they would make every ``git`` act on the outer repo."""


class UsageError(Exception):
    """The order cannot run: no project root or no valid ``menairos.toml``."""


@dataclass
class Step:
    """One step of a layer; ``lists`` carries named lists for the JSON output."""

    layer: str
    name: str
    state: str
    detail: str
    order: str | None = None
    warnings: list[str] = field(default_factory=list[str])
    lists: dict[str, list[str]] = field(default_factory=dict[str, list[str]])

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"estado desconocido: {self.state}")


StepMaker = Callable[..., Step]


def maker(layer: str, name: str) -> StepMaker:
    """``make(state, detail, order=None, …)``: a step of ``layer`` called ``name``."""

    def make(
        state: str,
        detail: str,
        order: str | None = None,
        *,
        lists: dict[str, list[str]] | None = None,
    ) -> Step:
        return Step(layer, name, state, detail, order, lists=dict(lists or {}))

    return make


@dataclass
class Layer:
    """The steps of one layer and the ones it did not reach."""

    name: str
    steps: list[Step] = field(default_factory=list[Step])
    not_run: list[str] = field(default_factory=list[str])

    @property
    def green(self) -> bool:
        return not self.not_run and all(s.state in GREEN for s in self.steps)


@dataclass
class Report:
    """What ``menairos entorno`` did, layer by layer."""

    root: Path
    check_only: bool
    layers: list[Layer]
    later: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return all(layer.green for layer in self.layers)

    def steps(self) -> Iterator[Step]:
        for layer in self.layers:
            yield from layer.steps


@dataclass(frozen=True)
class Result:
    """What a program gave: its exit code and its output."""

    code: int
    out: str = ""
    err: str = ""

    def tail(self) -> str:
        """The last lines of its output, for an error message."""
        lines = (self.out + "\n" + self.err).strip().splitlines()
        return "\n".join(lines[-_TAIL:]) or f"código de salida {self.code}"


class System(Protocol):
    """What the layers ask the machine; the tests use a double."""

    def which(self, program: str) -> str | None: ...

    def run(
        self, argv: Sequence[str], cwd: Path | None = None, timeout: float = 120
    ) -> Result: ...

    def resolve(self, path: Path) -> Path: ...

    def home(self) -> Path: ...

    def wsl(self) -> bool: ...


class RealSystem:
    """The real machine: ``shutil.which``, ``subprocess.run`` and the file system."""

    def which(self, program: str) -> str | None:
        return shutil.which(program)

    def run(
        self, argv: Sequence[str], cwd: Path | None = None, timeout: float = 120
    ) -> Result:
        env = environment_for_children(os.environ)
        try:
            done = subprocess.run(
                list(argv),
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return Result(127, "", f"no se encuentra «{argv[0]}»")
        except subprocess.TimeoutExpired:
            return Result(124, "", f"«{' '.join(argv)}» no terminó en {timeout:g} s")
        return Result(done.returncode, done.stdout, done.stderr)

    def resolve(self, path: Path) -> Path:
        return Path(os.path.realpath(path))

    def home(self) -> Path:
        return Path.home()

    def wsl(self) -> bool:
        try:
            release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
        except OSError:
            return False
        return "microsoft" in release.lower()


def environment_for_children(parent: Mapping[str, str]) -> dict[str, str]:
    """The environment of the programs: no outer venv nor outer repo, and gh quiet."""
    env = {
        key: value
        for key, value in parent.items()
        if key != "VIRTUAL_ENV" and key not in GIT_LOCATION
    }
    return env | dict(github.GH_ENV)


def default_system() -> System:
    """The machine used when none is given; the tests replace this function."""
    return RealSystem()
