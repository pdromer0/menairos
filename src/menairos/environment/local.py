"""The local layer of ``menairos entorno`` (hito-0.md 3.4): it only reads.

The path of the repo (never on a Windows drive), the tools of the manifests and
their versions, the ``gh`` session and ``.wslconfig``. It never installs
anything: a missing or old tool is ``manual``, with the exact order.
"""

import configparser
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from menairos import github, stacks
from menairos.environment.core import GREEN, Layer, Step, System, maker
from menairos.schemas import apply_defaults

LAYER = "local"
_WINDOWS_DRIVE = re.compile(r"/mnt/[A-Za-z](?:/.*)?")
_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){0,2}")
PROFILE_ARGV = ("cmd.exe", "/c", "chcp 65001 >nul && echo %USERPROFILE%")


@dataclass(frozen=True)
class Tool:
    """How to install a missing tool and how to update an old one."""

    install: str | None
    update: str | None
    link: str | None = None


TOOLS: Mapping[str, Tool] = {
    "git": Tool("sudo apt install git", "sudo apt install --only-upgrade git"),
    github.PROGRAM: Tool(
        "sudo apt install gh",
        "sudo apt update && sudo apt install --only-upgrade gh",
        "https://github.com/cli/cli/blob/trunk/docs/install_linux.md",
    ),
    "claude": Tool("curl -fsSL https://claude.ai/install.sh | bash", "claude update"),
    "uv": Tool("curl -LsSf https://astral.sh/uv/install.sh | sh", "uv self update"),
    "codex": Tool("npm install -g @openai/codex", "codex update"),
    "docker": Tool(None, None, "https://docs.docker.com/desktop/features/wsl/"),
}
"""The tools a manifest can ask for (the schema's closed list), but Python,
which is uv's and is looked for with ``uv python find``."""


def local_layer(
    root: Path,
    config: Mapping[str, Any],
    system: System,
    roots: Sequence[Traversable] = (stacks.PACKAGE_ROOT,),
) -> Layer:
    """The local layer; ``--comprobar`` changes nothing here."""
    layer = Layer(LAYER, [path_step(root, system)])
    try:
        wanted = required_tools(config, roots)
    except stacks.StackError as error:
        make = maker(LAYER, "herramientas")
        layer.steps.append(make("error", "; ".join(error.problems)))
        return layer
    for name, requirements in wanted.items():
        layer.steps.append(tool_step(name, requirements, root, system))
        if name == github.PROGRAM and layer.steps[-1].state in GREEN:
            layer.steps.append(session_step(system))
    if system.wsl():
        layer.steps.append(wslconfig_step(system))
    return layer


def required_tools(
    config: Mapping[str, Any], roots: Sequence[Traversable] = (stacks.PACKAGE_ROOT,)
) -> dict[str, list[str]]:
    """Each tool and its requirements, in the order the manifests give them.

    ``codex`` is added, with no version, if a reviewer of ``menairos.toml`` is
    Codex (two of them are, by default).
    """
    effective = apply_defaults("menairos", config)
    wanted: dict[str, list[str]] = {}
    for template in stacks.resolve(effective, roots):
        for name, requirement in template.tools.items():
            needs = wanted.setdefault(name, [])
            if requirement not in needs:
                needs.append(requirement)
    if "codex" in effective["revisores"].values():
        wanted.setdefault("codex", [])
    return wanted


def path_step(root: Path, system: System) -> Step:
    """Error on a Windows drive (``/mnt/<letra>/``); warning out of ``~/proyectos/``."""
    make = maker(LAYER, "ruta")
    real = system.resolve(root)
    if _WINDOWS_DRIVE.fullmatch(real.as_posix()):
        return make(
            "error",
            f"«{real}» está en una unidad de Windows: git y uv van muy lentos y los "
            "permisos de ejecución no se guardan. Mueve el proyecto a ~/proyectos/",
        )
    projects = system.resolve(system.home() / "proyectos")
    step = make("ok", str(real))
    if real == projects or not real.is_relative_to(projects):
        step.warnings.append(
            f"el proyecto no está dentro de {projects}/, donde Menairos espera los "
            "proyectos"
        )
    return step


def version_of(text: str) -> tuple[int, ...] | None:
    """The first version (one to three numbers) in a ``--version`` output."""
    match = _VERSION.search(text)
    if match is None:
        return None
    return tuple(int(part) for part in match.group().split("."))


def satisfies(version: tuple[int, ...], requirement: str) -> bool:
    """``>=X`` compares numbers, filling with zeros; ``X`` must match its parts."""
    if requirement.startswith(">="):
        wanted = tuple(int(part) for part in requirement[2:].split("."))
        size = max(len(version), len(wanted))
        pad = (0,) * size
        return (version + pad)[:size] >= (wanted + pad)[:size]
    wanted = tuple(int(part) for part in requirement.split("."))
    return version[: len(wanted)] == wanted


def tool_step(
    name: str, requirements: Sequence[str], root: Path, system: System
) -> Step:
    """Whether a tool is there and new enough."""
    if name == "python":
        return python_step(requirements, root, system)
    make = maker(LAYER, name)
    tool = TOOLS[name]
    shown = " y ".join(requirements)
    link = f"; instrucciones: {tool.link}" if tool.link else ""
    if system.which(name) is None:
        asked = f" (se pide {shown})" if shown else ""
        return make("manual", f"no está instalada{asked}{link}", tool.install)
    result = system.run([name, "--version"], root)
    lines = (result.out.strip() or result.err.strip()).splitlines()
    first = lines[0] if lines else ""
    version = version_of(first)
    if result.code != 0:
        return make("error", f"«{name} --version» falló: {result.tail()}")
    if version is None:
        if not requirements:
            return make("ok", first or "instalada")
        return make(
            "error",
            f"«{name} --version» no da una versión que se entienda: {result.tail()}",
        )
    found = ".".join(map(str, version))
    failed = [r for r in requirements if not satisfies(version, r)]
    if failed:
        detail = f"tiene {found} y se pide {' y '.join(failed)}{link}"
        return make("manual", detail, tool.update)
    return make("ok", f"{found} ({shown})" if shown else found)


def python_step(requirements: Sequence[str], root: Path, system: System) -> Step:
    """Python is uv's: ``uv python find`` must find each requested version."""
    make = maker(LAYER, "python")
    if system.which("uv") is None:
        return make("manual", "se busca con uv: antes, instala uv", TOOLS["uv"].install)
    for requirement in requirements:
        argv = ["uv", "python", "find", "--no-project", requirement]
        if system.run(argv, root).code != 0:
            version = requirement.removeprefix(">=")
            detail = f"uv no encuentra Python {requirement}"
            return make("manual", detail, f"uv python install {version}")
    return make("ok", " y ".join(requirements))


def session_step(system: System) -> Step:
    """The GitHub CLI must have a session open."""
    make = maker(LAYER, "sesión de GitHub")
    if system.run(github.AUTH_STATUS, timeout=30).code == 0:
        return make("ok", "la CLI de GitHub tiene sesión abierta")
    return make("manual", "la CLI de GitHub no tiene sesión abierta", github.AUTH_LOGIN)


def wslconfig_step(system: System) -> Step:
    """``.wslconfig`` with ``memory`` and ``swap`` in ``[wsl2]``: only a warning."""
    step = maker(LAYER, ".wslconfig")("ok", "")
    profile = windows_profile(system)
    if profile is None:
        step.detail = "no se encontró la carpeta del usuario de Windows"
        step.warnings.append("no se pudo comprobar .wslconfig")
        return step
    path = profile / ".wslconfig"
    step.detail = str(path)
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read_string(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        step.warnings.append(
            f"no hay {path}: sin él, WSL2 usa sus valores de memoria y swap por "
            "defecto. Pon memory y swap en su sección [wsl2]"
        )
        return step
    except (OSError, UnicodeDecodeError, configparser.Error) as error:
        step.warnings.append(f"no se puede leer {path}: {error}")
        return step
    missing = [
        key
        for key in ("memory", "swap")
        if not parser.get("wsl2", key, fallback="").strip()
    ]
    if missing:
        step.warnings.append(
            f"a la sección [wsl2] de {path} le falta {' y '.join(missing)}: sin ello, "
            "WSL2 usa sus valores por defecto"
        )
    return step


def windows_profile(system: System) -> Path | None:
    """The Windows user folder as a WSL path (``%USERPROFILE%`` and ``wslpath``)."""
    # chcp 65001: in UTF-8, not in the OEM code page, for a name with accents.
    found = system.run(PROFILE_ARGV, Path("/mnt/c"), 30)
    value = found.out.strip()
    if found.code != 0 or not value or "%" in value:
        return None
    converted = system.run(["wslpath", "-u", value], timeout=30)
    if converted.code != 0 or not converted.out.strip():
        return None
    return Path(converted.out.strip())
