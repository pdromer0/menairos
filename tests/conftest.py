"""Fixtures comunes de los tests.

- ``_sin_github_real`` (autouse): ningún test puede lanzar ``gh``.
- ``doble_github``: un ``FakeGitHub`` conectado a ``menairos.github``. Cualquier
  ``GitHub()`` creado en el test lo usa como transporte, y las esperas entre
  reintentos se anotan en ``doble_github.sleeps`` sin esperar. El tope se cambia
  con ``doble_github.limit``.
"""

import subprocess

import pytest
from doble_github import FakeGitHub, GuardedPopen

from menairos import github


@pytest.fixture(autouse=True)
def _sin_github_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hace fallar con ``RealGitHubCall`` cualquier ejecución de ``gh``."""
    monkeypatch.setattr(subprocess, "Popen", GuardedPopen)


@pytest.fixture
def doble_github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    """El doble de GitHub, conectado como transporte y espera por defecto."""
    doble = FakeGitHub()
    monkeypatch.setattr(github, "default_transport", lambda: doble)
    monkeypatch.setattr(github, "default_sleep", doble.sleeps.append)
    return doble
