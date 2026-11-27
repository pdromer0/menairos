"""Fixtures comunes de los tests.

- ``_sin_github_real`` (autouse): ningún test puede lanzar ``gh``.
"""

import subprocess

import pytest
from doble_github import GuardedPopen


@pytest.fixture(autouse=True)
def _sin_github_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hace fallar con ``RealGitHubCall`` cualquier ejecución de ``gh``."""
    monkeypatch.setattr(subprocess, "Popen", GuardedPopen)
