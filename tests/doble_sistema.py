"""Doble del sistema para ``menairos entorno`` y la barrera que aparta el real.

- ``FakeSystem``: una máquina en memoria con la forma de
  ``menairos.environment.core.System``. Tiene programas con su salida de
  ``--version``, respuestas por argv (fijas o con un efecto, como crear
  ``uv.lock``), ``realpath`` falsos para fingir rutas como ``/mnt/c`` y su
  propio ``home``. Anota cada llamada y, ante un argv que no conoce, lanza
  ``UnknownCommand``. ``git`` es el de verdad, pero con una configuración
  propia (sin la de la máquina) y nunca con ``push``.
- ``RealSystemCall``: lo lanza la fixture autouse de ``conftest.py`` si un test
  llega al sistema real.
- ``preparado``: un doble con todo lo de base + python-uv ya instalado y en
  orden, con los efectos de ``uv sync`` y ``pre-commit install``.
"""

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from menairos import github
from menairos.environment.core import Result

Effect = Callable[[Path | None], Result]

# Lo que escribe en la carpeta del proyecto cada orden que actúa.
ACTING = (
    ("git", "init"),
    ("git", "add"),
    ("git", "commit"),
    ("git", "symbolic-ref", "HEAD"),
    ("uv", "sync"),
    ("uv", "lock"),
    ("uv", "python", "install"),
    ("uv", "run", "--frozen", "pre-commit", "install"),
)


class RealSystemCall(AssertionError):
    """Un test llegó al sistema real de ``menairos entorno``."""


class UnknownCommand(AssertionError):
    """El código probado lanzó un programa que el doble no conoce."""


class ForbiddenPush(AssertionError):
    """El código probado intentó un ``git push``."""


def acts(argv: Sequence[str]) -> bool:
    """Si ``argv`` es una de las órdenes que escriben (``uv sync --check`` no)."""
    if "--check" in argv:
        return False
    words = tuple(argv)
    return any(words[: len(prefix)] == prefix for prefix in ACTING)


@dataclass
class FakeSystem:
    """Una máquina falsa; ``calls`` guarda cada argv con su carpeta."""

    home_dir: Path
    git_config: Path
    is_wsl: bool = False
    programs: dict[str, str] = field(default_factory=dict[str, str])
    answers: dict[tuple[str, ...], Effect] = field(
        default_factory=dict[tuple[str, ...], Effect]
    )
    fake_paths: dict[Path, Path] = field(default_factory=dict[Path, Path])
    calls: list[tuple[tuple[str, ...], Path | None]] = field(
        default_factory=list[tuple[tuple[str, ...], Path | None]]
    )

    # ── Preparación ──

    def install(self, name: str, version: str | None = None) -> None:
        """Pone ``name`` en el PATH; ``version`` es la salida de ``--version``."""
        self.programs[name] = f"/usr/bin/{name}"
        if version is not None:
            self.answer([name, "--version"], out=version + "\n")

    def remove(self, name: str) -> None:
        self.programs.pop(name, None)

    def answer(
        self,
        argv: Sequence[str],
        code: int = 0,
        out: str = "",
        err: str = "",
        effect: Callable[[Path | None], None] | None = None,
    ) -> None:
        """Lo que da ``argv``; ``effect`` se ejecuta antes, con la carpeta."""

        def respond(cwd: Path | None) -> Result:
            if effect is not None:
                effect(cwd)
            return Result(code, out, err)

        self.answers[tuple(argv)] = respond

    def respond(self, argv: Sequence[str], effect: Effect) -> None:
        """``argv`` da lo que devuelva ``effect`` en cada llamada."""
        self.answers[tuple(argv)] = effect

    # ── El protocolo System ──

    def which(self, program: str) -> str | None:
        return self.programs.get(program)

    def run(
        self, argv: Sequence[str], cwd: Path | None = None, timeout: float = 120
    ) -> Result:
        words = tuple(argv)
        self.calls.append((words, cwd))
        if words[0] not in self.programs:
            return Result(127, "", f"no se encuentra «{words[0]}»")
        if words[0] == "git":
            return self._git(words, cwd, timeout)
        if words not in self.answers:
            raise UnknownCommand(f"el doble no conoce «{' '.join(words)}»")
        return self.answers[words](cwd)

    def resolve(self, path: Path) -> Path:
        real = Path(os.path.realpath(path))
        for fake, shown in self.fake_paths.items():
            if real == fake or real.is_relative_to(fake):
                return shown / real.relative_to(fake)
        return real

    def home(self) -> Path:
        return self.home_dir

    def wsl(self) -> bool:
        return self.is_wsl

    # ── Ayudas ──

    def _git(self, words: tuple[str, ...], cwd: Path | None, timeout: float) -> Result:
        if "push" in words:
            raise ForbiddenPush(f"git push en un test: {' '.join(words)}")
        if words in self.answers:
            return self.answers[words](cwd)
        done = subprocess.run(
            list(words),
            cwd=cwd,
            env=self.git_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return Result(done.returncode, done.stdout, done.stderr)

    def git_env(self) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") and key != "VIRTUAL_ENV"
        }
        env |= {"GIT_CONFIG_GLOBAL": str(self.git_config), "GIT_CONFIG_NOSYSTEM": "1"}
        return env

    def acting_calls(self) -> list[tuple[str, ...]]:
        """Las llamadas que escriben algo."""
        return [argv for argv, _ in self.calls if acts(argv)]


HOOK = """#!/bin/sh
# File generated by pre-commit: https://pre-commit.com
exit 0
"""


def preparado(tmp: Path, *, wsl: bool = False) -> FakeSystem:
    """Un doble con base + python-uv en orden (las versiones son las mínimas)."""
    home = tmp / "casa"
    (home / "proyectos").mkdir(parents=True, exist_ok=True)
    config = tmp / "gitconfig"
    config.write_text(
        "[user]\n\tname = Prueba\n\temail = prueba@example.invalid\n"
        "[init]\n\tdefaultBranch = master\n",
        encoding="utf-8",
    )
    system = FakeSystem(home, config, wsl)
    system.install("git", "git version 2.43.0")
    system.install(github.PROGRAM, "gh version 2.103.3 (2026-10-26)")
    system.install("claude", "2.1.326 (Claude Code)")
    system.install("uv", "uv 0.13.10 (x86_64-unknown-linux-gnu)")
    system.install("codex", "codex-cli 0.166.0")
    system.answer(github.AUTH_STATUS)
    system.answer(["uv", "python", "find", "--no-project", "3.14"], out="/py/3.14\n")
    entorno_uv(system)
    return system


def entorno_uv(system: FakeSystem) -> None:
    """``uv sync`` crea ``uv.lock`` y ``.venv``; ``--check`` mira si están."""

    def synced(cwd: Path | None) -> bool:
        assert cwd is not None
        return (cwd / "uv.lock").is_file() and (cwd / ".venv").is_dir()

    def check(cwd: Path | None) -> Result:
        return Result(0 if synced(cwd) else 1)

    def sync(cwd: Path | None) -> Result:
        assert cwd is not None
        if not (cwd / "uv.lock").exists():
            (cwd / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        (cwd / ".venv").mkdir(exist_ok=True)
        return Result(0)

    def install_hook(cwd: Path | None) -> Result:
        assert cwd is not None
        hook = cwd / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(HOOK, encoding="utf-8")
        hook.chmod(0o755)
        return Result(0, "pre-commit installed at .git/hooks/pre-commit\n")

    system.respond(["uv", "sync", "--check"], check)
    system.respond(["uv", "sync", "--check", "--locked"], check)
    system.respond(["uv", "sync"], sync)
    system.respond(["uv", "sync", "--locked"], sync)
    system.answer(["uv", "lock", "--check"])
    system.respond(["uv", "run", "--frozen", "pre-commit", "install"], install_hook)
