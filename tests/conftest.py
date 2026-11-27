"""Fixtures comunes de los tests.

- ``_sin_github_real`` (autouse): ningún test puede lanzar ``gh``. En el proceso
  de pytest, ``subprocess.Popen`` lo rechaza con ``RealGitHubCall``; en los
  procesos hijos y en ``os.system``, un ``gh`` falso, primero en el ``PATH``,
  sale con 97 sin llamar a nada.
- ``doble_github``: un ``FakeGitHub`` conectado a ``menairos.github``. Cualquier
  ``GitHub()`` creado en el test lo usa como transporte, y las esperas entre
  reintentos se anotan en ``doble_github.sleeps`` sin esperar. El tope se cambia
  con ``doble_github.limit``.
- ``_sin_sistema_real`` (autouse): ``menairos entorno`` no puede usar la máquina
  real; ``default_system`` lanza ``RealSystemCall``.
- ``doble_sistema``: un ``FakeSystem`` con base + python-uv en orden, que
  ``menairos entorno`` usa cuando no se le pasa un sistema.
"""

import os
import subprocess
from pathlib import Path

import pytest
from doble_github import FakeGitHub, GuardedPopen
from doble_sistema import FakeSystem, RealSystemCall, preparado

from menairos import github
from menairos.environment import core

GH_FALSO = """#!/bin/sh
echo "gh bloqueado en los tests: usa la fixture doble_github" >&2
exit 97
"""


@pytest.fixture(scope="session")
def _carpeta_gh_falso(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Carpeta con un ``gh`` falso que sale con 97."""
    carpeta = tmp_path_factory.mktemp("gh-falso")
    gh = carpeta / "gh"
    gh.write_text(GH_FALSO, encoding="utf-8")
    gh.chmod(0o755)
    return carpeta


@pytest.fixture(autouse=True)
def _sin_github_real(monkeypatch: pytest.MonkeyPatch, _carpeta_gh_falso: Path) -> None:
    """Hace fallar cualquier ejecución de ``gh``, también en los procesos hijos."""
    monkeypatch.setattr(subprocess, "Popen", GuardedPopen)
    monkeypatch.setenv(
        "PATH", f"{_carpeta_gh_falso}{os.pathsep}{os.environ.get('PATH', '')}"
    )


@pytest.fixture
def doble_github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    """El doble de GitHub, conectado como transporte y espera por defecto."""
    doble = FakeGitHub()
    monkeypatch.setattr(github, "default_transport", lambda: doble)
    monkeypatch.setattr(github, "default_sleep", doble.sleeps.append)
    return doble


def _sistema_real() -> core.System:
    raise RealSystemCall(
        "Un test llegó a la máquina real de menairos entorno: usa doble_sistema."
    )


@pytest.fixture(autouse=True)
def _sin_sistema_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """``menairos entorno`` sin sistema inyectado lanza ``RealSystemCall``."""
    monkeypatch.setattr(core, "default_system", _sistema_real)


@pytest.fixture
def doble_sistema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeSystem:
    """El doble del sistema, con todo en orden, como sistema por defecto."""
    doble = preparado(tmp_path)
    monkeypatch.setattr(core, "default_system", lambda: doble)
    return doble
