"""Test double for GitHub and the guard that keeps tests away from the real one.

``RealGitHubCall`` is raised by the autouse fixture of ``conftest.py`` when a
test tries to launch ``gh``.
"""

import shlex
import subprocess
from collections.abc import Sequence
from pathlib import PurePath, PureWindowsPath
from typing import Any

_GH_NAMES = frozenset({"gh", "gh.exe"})


class RealGitHubCall(AssertionError):
    """A test tried to run the real ``gh``."""


def _program(args: Any, executable: Any, shell: bool) -> str | None:
    """Name of the program a ``Popen`` call would start (``None`` if unknown)."""
    if executable is not None:
        return str(executable)
    if isinstance(args, str | bytes | PurePath):
        text = args.decode() if isinstance(args, bytes) else str(args)
        if not shell:
            return text
        try:
            words = shlex.split(text)
        except ValueError:
            return text
        return words[0] if words else None
    if isinstance(args, Sequence) and args:
        first: Any = args[0]  # pyright: ignore[reportUnknownVariableType]
        return first.decode() if isinstance(first, bytes) else str(first)
    return None


def launches_gh(args: Any, executable: Any = None, shell: bool = False) -> bool:
    """Whether a ``Popen(args, executable=..., shell=...)`` call starts ``gh``."""
    program = _program(args, executable, shell)
    if program is None:
        return False
    return PureWindowsPath(program).name.lower() in _GH_NAMES


class GuardedPopen(subprocess.Popen):  # pyright: ignore[reportMissingTypeArgument]
    """``subprocess.Popen`` that refuses to start ``gh`` and runs anything else."""

    def __init__(self, args: Any, *rest: Any, **kwargs: Any) -> None:
        if launches_gh(args, kwargs.get("executable"), bool(kwargs.get("shell"))):
            raise RealGitHubCall(
                f"Un test intentó ejecutar gh de verdad: {args!r}. "
                "Usa la fixture doble_github."
            )
        super().__init__(args, *rest, **kwargs)
