"""Tests lentos de las plantillas de stack (T-10, hito-0.md 3.8).

- Un proyecto generado con base + python-uv en una carpeta temporal pasa su
  propia N3, con un ``uv sync`` de verdad (necesita red la primera vez).
- Las comprobaciones deliberadas de 3.6 que ve la N3 (formato, tipos y un test
  que falla) hacen fallar su paso, y cada paso nombra el fichero de su falta.
  Provocarlas a través de los hooks de pre-commit, la clave falsa con gitleaks
  y las remotas son de T-13.
- Las plantillas viajan en el wheel, con sus ficheros ocultos.
"""

import subprocess
import zipfile
from pathlib import Path

import pytest
from ayuda_stacks import RAIZ, configuracion, entorno_git, escribir, git

from menairos import stacks

CARPETA = RAIZ / "src" / "menairos" / "plantillas" / "stacks"

FALTAS = {
    "src/demo_proyecto/mal_formato.py": 'valor = {  "a":1 }\n',
    "src/demo_proyecto/tipos.py": 'numero: int = "uno"\n',
    "tests/test_falla.py": "def test_falla() -> None:\n    assert 1 + 1 == 3\n",
}

# Cada paso de la N3 de python-uv y el fichero que tiene que nombrar al fallar.
PASOS = {
    "uv run --frozen ruff format --check .": "mal_formato.py",
    "uv run --frozen pyright": "tipos.py",
    "uv run --frozen pytest": "test_falla.py",
}


def _n3(raiz: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["scripts/n3.sh"],
        cwd=raiz,
        env=entorno_git(),
        capture_output=True,
        text=True,
        timeout=600,
    )


def _salida_del_paso(salida: str, paso: str) -> str:
    """Lo que imprimió un paso de la N3, desde su anuncio hasta el siguiente."""
    inicio = salida.index(f"N3 · {paso}\n")
    fin = salida.find("\nN3 · ", inicio + 1)
    return salida[inicio : fin if fin != -1 else len(salida)]


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_un_proyecto_generado_pasa_su_n3_y_salta_con_sus_fallos(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "demo-proyecto"
    raiz.mkdir()
    escribir(stacks.compose(configuracion("base", "python-uv")), raiz)
    git(raiz, "init", "-q", "-b", "main")
    subprocess.run(
        ["uv", "sync"],
        cwd=raiz,
        env=entorno_git(),
        capture_output=True,
        text=True,
        check=True,
        timeout=600,
    )

    verde = _n3(raiz)
    assert verde.returncode == 0, verde.stdout + verde.stderr
    assert verde.stdout.endswith("Resumen N3:\n  OK     python-uv\n")
    for paso in PASOS:
        assert f"  OK     {paso}\n" in verde.stdout, paso

    for ruta, texto in FALTAS.items():
        (raiz / ruta).write_text(texto, encoding="utf-8")
    rojo = _n3(raiz)
    assert rojo.returncode == 1, rojo.stdout
    assert rojo.stdout.endswith("Resumen N3:\n  FALLO  python-uv\n")
    for paso, fichero in PASOS.items():
        assert f"  FALLO  {paso}\n" in rojo.stdout, paso
        assert fichero in _salida_del_paso(rojo.stdout, paso), paso
    en_la_n3 = [c for c in stacks.load("python-uv").checks if c.caught_by == "n3"]
    assert en_la_n3
    for comprobacion in en_la_n3:
        assert comprobacion.message in rojo.stdout, comprobacion.name


@pytest.mark.slow
def test_las_plantillas_de_stack_viajan_en_el_wheel(tmp_path: Path) -> None:
    """uv tool install solo instala el paquete: van dentro, también las ocultas."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        timeout=300,
    )
    [rueda] = tmp_path.glob("menairos-*.whl")
    with zipfile.ZipFile(rueda) as contenido:
        nombres = set(contenido.namelist())
    ficheros = [p for p in CARPETA.rglob("*") if p.is_file()]
    assert any(p.name == ".gitignore.plantilla" for p in ficheros)
    assert any("{{paquete}}" in str(p) for p in ficheros)
    for fichero in ficheros:
        dentro = "menairos/" + fichero.relative_to(RAIZ / "src" / "menairos").as_posix()
        assert dentro in nombres, dentro
