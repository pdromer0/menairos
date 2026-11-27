"""Ayudas de los tests de las plantillas de stack (T-10).

- ``RAICES``: las plantillas del paquete y las de juguete de ``tests/data/stacks/``.
- ``configuracion``: un ``menairos.toml`` sintético.
- ``escribir``: escribe en una carpeta lo compuesto en memoria, con el bit de
  ejecución de los ``.sh``. Escribir en un repo de verdad es de T-11.
- ``entorno_git``: un entorno sin la configuración de git de la máquina ni las
  variables ``GIT_*`` heredadas, con un autor sintético.
- ``plantilla``: crea una plantilla de prueba en una carpeta.
"""

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from menairos import stacks

RAIZ = Path(__file__).resolve().parents[1]
JUGUETES = RAIZ / "tests" / "data" / "stacks"
RAICES = (stacks.PACKAGE_ROOT, JUGUETES)


def configuracion(
    *plantillas: str,
    nombre: str = "demo-proyecto",
    version: str = "3.0.0",
    modo: str = "manual",
) -> dict[str, object]:
    return {
        "menairos": {"version": version},
        "proyecto": {"nombre": nombre, "repo": "ejemplo/proyecto"},
        "stack": {"plantillas": list(plantillas)},
        "modo": {"defecto": modo},
    }


def escribir(ficheros: Mapping[str, stacks.StackFile], raiz: Path) -> None:
    for ruta, fichero in ficheros.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(fichero.text, encoding="utf-8")
        if fichero.executable:
            destino.chmod(0o755)


def entorno_git() -> dict[str, str]:
    entorno = {
        clave: valor
        for clave, valor in os.environ.items()
        if not clave.startswith("GIT_") and clave != "VIRTUAL_ENV"
    }
    entorno |= {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Prueba",
        "GIT_AUTHOR_EMAIL": "prueba@example.invalid",
        "GIT_COMMITTER_NAME": "Prueba",
        "GIT_COMMITTER_EMAIL": "prueba@example.invalid",
    }
    return entorno


def git(raiz: Path, *argumentos: str) -> str:
    resultado = subprocess.run(
        ["git", *argumentos],
        cwd=raiz,
        env=entorno_git(),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return resultado.stdout


def plantilla(
    raiz: Path, nombre: str, manifiesto: str, ficheros: Mapping[str, str]
) -> Path:
    """Una plantilla en ``raiz/nombre``: su manifiesto y sus ficheros (con sufijo)."""
    carpeta = raiz / nombre
    carpeta.mkdir(parents=True)
    (carpeta / stacks.MANIFEST).write_text(manifiesto, encoding="utf-8")
    for ruta, texto in ficheros.items():
        destino = carpeta / stacks.FILES_DIR / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return carpeta


def manifiesto_lenguaje(
    nombre: str,
    *,
    extensiones: str = '[".x"]',
    carpetas: str = '["x/"]',
    requiere: str = '["base"]',
    fusionables: str = "[]",
) -> str:
    return f"""[plantilla]
nombre = "{nombre}"
version = "1.0.0"
tipo = "lenguaje"
requiere = {requiere}

[propiedad]
extensiones = {extensiones}
carpetas = {carpetas}

[ordenes]
formato = "f ."
formato_fichero = "f {{fichero}}"
lint = "l ."
tipos = "t"
tests_area = "p {{rutas}}"

[ficheros]
fusionables = {fusionables}
"""


def partes(nombre: str) -> dict[str, str]:
    """Las dos partes mínimas de una plantilla de lenguaje de prueba."""
    return {
        f"scripts/stack/{nombre}/n1.sh.plantilla": "#!/usr/bin/env bash\nexit 0\n",
        f"scripts/stack/{nombre}/n3.sh.plantilla": "#!/usr/bin/env bash\nexit 0\n",
    }
