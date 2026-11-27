"""Tests de los scripts del contrato: scripts/n1.sh, n2.sh y n3.sh de base (T-10).

Se compone base con las dos plantillas de juguete en una carpeta temporal: sus
partes anotan sus argumentos en .cache/partes/ y salen con SALIDA_JUGUETE o
SALIDA_JUGUETE2, así que se prueba el reparto sin lanzar ruff ni pytest. Los
casos de reparto son los mismos que los de Contract.split (test diferencial).
"""

import os
import subprocess
from pathlib import Path

import pytest
from ayuda_stacks import RAICES, configuracion, entorno_git, escribir, git

from menairos import stacks
from menairos.stacks import StackError


@pytest.fixture
def proyecto(tmp_path: Path) -> Path:
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    escribir(stacks.compose(configuracion("base", "juguete", "juguete2"), RAICES), raiz)
    return raiz


def _ejecutar(
    raiz: Path, script: str, *argumentos: str, cwd: Path | None = None, **entorno: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(raiz / "scripts" / script), *argumentos],
        cwd=cwd or raiz,
        env=entorno_git() | entorno,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _argumentos(raiz: Path, parte: str) -> list[str] | None:
    """Lo que recibió la parte (None si no se ejecutó)."""
    registro = raiz / ".cache" / "partes" / parte
    if not registro.exists():
        return None
    texto = registro.read_text(encoding="utf-8")
    return [] if texto == "\n" else texto.splitlines()


def _borrar_registros(raiz: Path) -> None:
    for registro in (raiz / ".cache" / "partes").glob("*"):
        registro.unlink()


# ── N1 ──────────────────────────────────────────────────────────────────────


def test_n1_sin_rutas_ejecuta_cada_parte_sin_argumentos(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n1.sh")
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") == []
    assert _argumentos(proyecto, "juguete2.n1") == []
    assert "N1 · juguete · scripts/stack/juguete/n1.sh\n" in resultado.stdout
    assert resultado.stdout.endswith(
        "Resumen N1:\n  OK     juguete\n  OK     juguete2\n"
    )


def test_n1_reparte_las_rutas_y_la_extension_gana_a_la_carpeta(proyecto: Path) -> None:
    resultado = _ejecutar(
        proyecto, "n1.sh", "juguete/a.jug", "juguete2/b.jug", "c.jug2", "juguete2"
    )
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") == ["juguete/a.jug", "juguete2/b.jug"]
    assert _argumentos(proyecto, "juguete2.n1") == ["c.jug2", "juguete2"]


def test_una_parte_sin_rutas_propias_no_ejecuta_tests(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n1.sh", "juguete/a.jug")
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete2.n1") == ["--sin-tests"]


def test_una_ruta_sin_plantilla_es_un_error(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n1.sh", "juguete/a.jug", "docs/x.md")
    assert resultado.returncode == 1
    assert "la ruta «docs/x.md» no es de ninguna plantilla" in resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") is None


@pytest.mark.parametrize("ruta", ["../fuera.jug", "/etc/x.jug"])
def test_una_ruta_fuera_del_repo_es_un_error(proyecto: Path, ruta: str) -> None:
    resultado = _ejecutar(proyecto, "n1.sh", ruta)
    assert resultado.returncode == 1
    assert "está fuera del repo" in resultado.stdout


def test_las_rutas_se_toman_desde_donde_se_lanza(proyecto: Path) -> None:
    (proyecto / "juguete").mkdir()
    resultado = _ejecutar(
        proyecto,
        "n1.sh",
        "a.jug",
        str(proyecto / "juguete2" / "abs.jug2"),
        cwd=proyecto / "juguete",
    )
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") == ["juguete/a.jug"]
    assert _argumentos(proyecto, "juguete2.n1") == ["juguete2/abs.jug2"]


def test_las_rutas_valen_si_se_llega_al_repo_por_un_enlace(
    proyecto: Path, tmp_path: Path
) -> None:
    """Manda la ruta lógica: un enlace simbólico no saca la ruta del repo."""
    enlace = tmp_path / "enlace"
    enlace.symlink_to(proyecto, target_is_directory=True)
    resultado = subprocess.run(
        ["scripts/n1.sh", "juguete/a.jug"],
        cwd=enlace,
        env=entorno_git() | {"PWD": str(enlace)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") == ["juguete/a.jug"]


def test_n1_ejecuta_todas_las_partes_aunque_falle_una(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n1.sh", SALIDA_JUGUETE="1")
    assert resultado.returncode == 1
    assert _argumentos(proyecto, "juguete2.n1") == []
    assert resultado.stdout.endswith(
        "Resumen N1:\n  FALLO  juguete\n  OK     juguete2\n"
    )


def test_n1_sale_con_1_si_una_parte_sale_con_otro_codigo(proyecto: Path) -> None:
    assert _ejecutar(proyecto, "n1.sh", SALIDA_JUGUETE2="3").returncode == 1


def test_una_parte_que_falta_es_un_fallo(proyecto: Path) -> None:
    (proyecto / "scripts" / "stack" / "juguete2" / "n1.sh").unlink()
    resultado = _ejecutar(proyecto, "n1.sh")
    assert resultado.returncode == 1
    assert "  FALLO  juguete2\n" in resultado.stdout
    assert _argumentos(proyecto, "juguete.n1") == []


@pytest.mark.parametrize("script", ["n1.sh", "n3.sh"])
def test_sin_la_lista_de_plantillas_es_un_error(proyecto: Path, script: str) -> None:
    (proyecto / stacks.OWNERSHIP_FILE).unlink()
    resultado = _ejecutar(proyecto, script)
    assert resultado.returncode == 1
    assert "no se puede leer scripts/stack/plantillas.txt" in resultado.stdout


@pytest.mark.parametrize("script", ["n1.sh", "n3.sh"])
def test_una_lista_sin_plantillas_es_un_error(proyecto: Path, script: str) -> None:
    (proyecto / stacks.OWNERSHIP_FILE).write_text("# nada\n", encoding="utf-8")
    resultado = _ejecutar(proyecto, script)
    assert resultado.returncode == 1
    assert "no tiene ninguna plantilla de lenguaje" in resultado.stdout


# El reparto de scripts/n1.sh y el de Contract.split, sobre los mismos casos.
REPARTO = [
    "juguete/a.jug",
    "./juguete/a.jug",
    "juguete",
    "juguete/",
    "juguete/datos/x.json",
    "juguete2/b.jug",
    "juguete/c.jug2",
    "a.b.jug",
    "con espacio.jug",
    ".jug",
    "x/.jug2",
    "..jug",
    "x.",
    "juguetex/a.txt",
    "docs/x.md",
    "juguete/../juguete2/y",
]


@pytest.mark.parametrize("ruta", REPARTO)
def test_el_reparto_de_bash_es_el_del_contrato(proyecto: Path, ruta: str) -> None:
    contrato = stacks.contract(
        configuracion("base", "juguete", "juguete2"), proyecto, RAICES
    )
    try:
        esperado = contrato.split([ruta])
    except StackError:
        esperado = None
    resultado = _ejecutar(proyecto, "n1.sh", ruta)
    if esperado is None:
        assert resultado.returncode == 1
        assert "no es de ninguna plantilla" in resultado.stdout
        return
    assert resultado.returncode == 0, resultado.stdout
    for parte in ("juguete", "juguete2"):
        assert _argumentos(proyecto, f"{parte}.n1") == esperado.get(
            parte, ["--sin-tests"]
        ), parte


# ── N3 ──────────────────────────────────────────────────────────────────────


def test_n3_ejecuta_cada_parte_y_dice_que_ejecuto(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n3.sh")
    assert resultado.returncode == 0, resultado.stdout
    assert _argumentos(proyecto, "juguete.n3") == []
    assert "N3 · juguete2 · scripts/stack/juguete2/n3.sh\n" in resultado.stdout
    assert resultado.stdout.endswith(
        "Resumen N3:\n  OK     juguete\n  OK     juguete2\n"
    )


def test_n3_ejecuta_todas_las_partes_y_sale_con_1(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n3.sh", SALIDA_JUGUETE="7")
    assert resultado.returncode == 1
    assert _argumentos(proyecto, "juguete2.n3") == []
    assert "  FALLO  juguete\n  OK     juguete2\n" in resultado.stdout


# ── N2 ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def repo(proyecto: Path) -> Path:
    git(proyecto, "init", "-q", "-b", "main")
    git(proyecto, "add", "-A")
    git(proyecto, "commit", "-q", "-m", "inicio")
    return proyecto


def _n2_en_verde_y_sellado(raiz: Path) -> None:
    primera = _ejecutar(raiz, "n2.sh")
    assert primera.returncode == 0, primera.stdout
    assert "verde: sello guardado" in primera.stdout
    _borrar_registros(raiz)
    segunda = _ejecutar(raiz, "n2.sh")
    assert segunda.returncode == 0
    assert "sin cambios desde el último verde" in segunda.stdout
    assert _argumentos(raiz, "juguete.n1") is None


def test_n2_ejecuta_la_n1_y_despues_no_hace_nada(repo: Path) -> None:
    _n2_en_verde_y_sellado(repo)


def test_n2_ve_un_fichero_nuevo_y_uno_modificado_sin_anadir(repo: Path) -> None:
    _n2_en_verde_y_sellado(repo)
    (repo / "nuevo.jug").write_text("bien\n", encoding="utf-8")
    assert _ejecutar(repo, "n2.sh").returncode == 0
    assert _argumentos(repo, "juguete.n1") == []
    _borrar_registros(repo)
    with (repo / "AGENTS.md").open("a", encoding="utf-8") as agentes:
        agentes.write("Una línea más.\n")
    assert "hay cambios" in _ejecutar(repo, "n2.sh").stdout
    assert _argumentos(repo, "juguete.n1") == []
    assert "?? nuevo.jug" in git(repo, "status", "--porcelain")


def test_n2_ve_un_fichero_borrado(repo: Path) -> None:
    _n2_en_verde_y_sellado(repo)
    (repo / "SECURITY.md").unlink()
    assert "hay cambios" in _ejecutar(repo, "n2.sh").stdout


def test_n2_no_ve_lo_ignorado(repo: Path) -> None:
    _n2_en_verde_y_sellado(repo)
    (repo / "x.jug.tmp").write_text("ignorado\n", encoding="utf-8")
    assert "sin cambios" in _ejecutar(repo, "n2.sh").stdout


def test_n2_no_sella_un_rojo(repo: Path) -> None:
    rojo = _ejecutar(repo, "n2.sh", SALIDA_JUGUETE="1")
    assert rojo.returncode == 1
    assert "rojo: no se guarda el sello" in rojo.stdout
    assert not (repo / ".cache" / "menairos" / "n2.sello").exists()
    _borrar_registros(repo)
    assert "hay cambios" in _ejecutar(repo, "n2.sh").stdout
    assert _argumentos(repo, "juguete.n1") == []


def test_n2_en_un_repo_sin_commits(proyecto: Path) -> None:
    git(proyecto, "init", "-q", "-b", "main")
    _n2_en_verde_y_sellado(proyecto)
    assert git(proyecto, "status", "--porcelain").startswith("??")


def test_n2_fuera_de_git_es_un_error(proyecto: Path) -> None:
    resultado = _ejecutar(proyecto, "n2.sh", GIT_CEILING_DIRECTORIES=str(proyecto))
    assert resultado.returncode == 1
    assert "hace falta un repo git" in resultado.stdout


def test_la_n1_no_hereda_el_indice_temporal(repo: Path) -> None:
    parte = repo / "scripts" / "stack" / "juguete" / "n1.sh"
    parte.write_text(
        '#!/usr/bin/env bash\ncd "$(dirname "$0")/../../.."\nmkdir -p .cache/partes\n'
        'echo "${GIT_INDEX_FILE:-ninguno}" >.cache/partes/indice\n',
        encoding="utf-8",
    )
    os.chmod(parte, 0o755)
    assert _ejecutar(repo, "n2.sh").returncode == 0
    indice = (repo / ".cache" / "partes" / "indice").read_text(encoding="utf-8")
    assert indice == "ninguno\n"
