"""``menairos entorno``: the local layer for now (hito-0.md 3.4).

Every step checks, acts if it has to and checks again; running the order again
changes nothing once everything is in place. With ``check_only`` nothing is
written: what the order would do is ``manual``, with the order that does it.
Without a layer, both run in order, and the repo layer only runs if the local
one is green. The github and nube layers come later (T-12).

* :mod:`menairos.environment.core`: steps, report and the machine.
* :mod:`menairos.environment.local`: tools, versions, path and ``.wslconfig``.
"""

from collections.abc import Callable, Sequence
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from menairos import stacks
from menairos.environment import core
from menairos.environment.core import Layer, Report, Step, System, UsageError
from menairos.environment.local import local_layer
from menairos.schemas import load_document, validate

__all__ = ["LAYERS", "Report", "Step", "UsageError", "read_config", "run_environment"]

CONFIG_FILE = "menairos.toml"
LAYERS = ("local",)
LATER_LAYERS = ("repo", "github", "nube")
"""The layers of hito-0.md 3.4 that this version does not have yet."""


def run_environment(
    root: Path,
    layer: str | None = None,
    *,
    check_only: bool = False,
    system: System | None = None,
    roots: Sequence[Traversable] = (stacks.PACKAGE_ROOT,),
    notify: Callable[[str], None] | None = None,
) -> Report:
    """Run ``layer`` (both, in order, if ``None``) on the project at ``root``.

    ``notify`` is told before a long action (``uv sync``, the first commit).
    Raises :class:`UsageError` if there is no project to work on.
    """
    if layer is not None and layer not in LAYERS:
        raise UsageError(
            f"la capa «{layer}» no existe; las que hay: {', '.join(LAYERS)}"
        )
    config = read_config(root)
    machine = system if system is not None else core.default_system()
    layers: list[Layer] = []
    if layer in (None, "local"):
        layers.append(local_layer(root, config, machine, roots))
    later = LATER_LAYERS if layer is None else ()
    return Report(root, check_only, layers, later)


def read_config(root: Path) -> dict[str, Any]:
    """``menairos.toml`` as read; a missing or invalid one is a :class:`UsageError`."""
    if not root.is_dir():
        raise UsageError(f"la raíz «{root}» no es una carpeta")
    path = root / CONFIG_FILE
    if not path.is_file():
        raise UsageError(
            f"no hay {CONFIG_FILE} en «{root}»: lo crea /crear-spec, que es donde se "
            "decide el stack"
        )
    try:
        config = load_document(path)
    except Exception as error:  # TOML syntax or encoding: its message says which
        raise UsageError(f"{CONFIG_FILE} no se puede leer: {error}") from None
    issues = validate("menairos", config)
    if issues:
        listed = "; ".join(f"{i.path or 'la raíz'}: {i.message}" for i in issues)
        raise UsageError(
            f"{CONFIG_FILE} no es válido ({listed}); «menairos spec validar» lo detalla"
        )
    return config
