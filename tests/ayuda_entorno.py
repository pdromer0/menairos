"""Ayudas de los tests de ``menairos entorno`` (T-11).

- ``proyecto``: una carpeta en el ``~/proyectos/`` del doble con un
  ``menairos.toml`` sintético.
- ``estados``: los pasos de un informe como ``{(capa, paso): estado}``.
- ``foto``: el contenido, el modo y la fecha de cada fichero de una carpeta,
  para comprobar que nada cambió.
"""

from collections.abc import Sequence
from pathlib import Path

from doble_sistema import FakeSystem

from menairos.environment import Report, Step


def menairos_toml(
    plantillas: Sequence[str] = ("base", "python-uv"),
    *,
    nombre: str = "demo-proyecto",
    extra: str = "",
) -> str:
    listadas = ", ".join(f'"{p}"' for p in plantillas)
    return (
        '[menairos]\nversion = "3.0.0"\n\n'
        f'[proyecto]\nnombre = "{nombre}"\nrepo = "ejemplo/{nombre}"\n\n'
        f"[stack]\nplantillas = [{listadas}]\n{extra}"
    )


def proyecto(
    sistema: FakeSystem,
    nombre: str = "demo-proyecto",
    *,
    plantillas: Sequence[str] = ("base", "python-uv"),
    extra: str = "",
) -> Path:
    raiz = sistema.home() / "proyectos" / nombre
    raiz.mkdir(parents=True, exist_ok=True)
    texto = menairos_toml(plantillas, nombre=nombre, extra=extra)
    (raiz / "menairos.toml").write_text(texto, encoding="utf-8")
    return raiz


def estados(informe: Report) -> dict[tuple[str, str], str]:
    return {(paso.layer, paso.name): paso.state for paso in informe.steps()}


def paso(informe: Report, capa: str, nombre: str) -> Step:
    return next(p for p in informe.steps() if (p.layer, p.name) == (capa, nombre))


def foto(raiz: Path) -> dict[str, tuple[bytes, int, int]]:
    """Cada fichero bajo ``raiz`` (sin ``.git``): bytes, modo y ``mtime_ns``."""
    resultado: dict[str, tuple[bytes, int, int]] = {}
    for ruta in sorted(raiz.rglob("*")):
        relativa = ruta.relative_to(raiz)
        if relativa.parts[0] == ".git" or ruta.is_dir() or ruta.is_symlink():
            continue
        datos = ruta.stat()
        resultado[relativa.as_posix()] = (
            ruta.read_bytes(),
            datos.st_mode,
            datos.st_mtime_ns,
        )
    return resultado
