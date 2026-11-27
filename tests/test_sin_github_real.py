"""Barreras de T-07: ningún test llama a GitHub y solo menairos.github lanza gh."""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from doble_github import RealGitHubCall, launches_gh

RAIZ = Path(__file__).resolve().parents[1]
PAQUETE = RAIZ / "src" / "menairos"
ENVOLTORIO = PAQUETE / "github.py"

# Un texto que nombra el ejecutable gh: «gh», «gh api …», «/usr/bin/gh», «gh.exe».
_GH = re.compile(r"(?:^|[/\\])gh(?:\.exe)?(?:\s|$)", re.IGNORECASE)


def textos_que_lanzan_gh(fuente: str) -> list[str]:
    """Textos del código (no docstrings ni comentarios) que nombran el ejecutable gh."""
    arbol = ast.parse(fuente)
    docstrings = {
        id(nodo.value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Expr)
        and isinstance(nodo.value, ast.Constant)
        and isinstance(nodo.value.value, str)
    }
    return [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and id(nodo) not in docstrings
        and _GH.search(nodo.value)
    ]


def _modulos_del_paquete() -> list[Path]:
    return sorted(PAQUETE.rglob("*.py"))


def test_solo_menairos_github_lanza_gh() -> None:
    """Ningún módulo de src/menairos salvo github.py nombra el ejecutable gh."""
    encontrados = {
        str(ruta.relative_to(RAIZ)): textos
        for ruta in _modulos_del_paquete()
        if ruta != ENVOLTORIO
        and (textos := textos_que_lanzan_gh(ruta.read_text(encoding="utf-8")))
    }
    assert encontrados == {}


def test_el_recorrido_incluye_los_modulos_del_paquete() -> None:
    """El test anterior recorre de verdad los módulos (y no una carpeta vacía)."""
    nombres = {ruta.name for ruta in _modulos_del_paquete()}
    assert {"cli.py", "schemas.py", "spec_validation.py"} <= nombres


@pytest.mark.parametrize(
    "fuente",
    [
        'import subprocess\nsubprocess.run(["gh", "api", "user"])\n',
        'import os\nos.system("gh api user")\n',
        'import shutil\nshutil.which("gh")\n',
        'PROGRAMA = "/usr/bin/gh"\n',
        'PROGRAMA = "C:\\\\bin\\\\GH.EXE"\n',
        'orden = f"gh api {ruta}"\n',
    ],
    ids=["subprocess", "os-system", "which", "ruta", "windows", "f-string"],
)
def test_el_test_estatico_detecta_un_lanzamiento_de_gh(fuente: str) -> None:
    assert textos_que_lanzan_gh(fuente) != []


@pytest.mark.parametrize(
    "fuente",
    [
        '"""Habla con GitHub por gh api."""\n',
        'def f():\n    """gh api, solo REST."""\n',
        'URL = "https://github.com"\n',
        'RAMA = "gh-pages"\n',
        "# gh api user\nx = 1\n",
        'TEXTO = "por gh api"\n',
    ],
    ids=[
        "docstring",
        "docstring-funcion",
        "github",
        "gh-pages",
        "comentario",
        "en-medio",
    ],
)
def test_el_test_estatico_no_da_falsos_positivos(fuente: str) -> None:
    assert textos_que_lanzan_gh(fuente) == []


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        (["gh", "api", "user"], {}),
        (["/usr/bin/gh", "--version"], {}),
        ([b"gh", b"auth", b"status"], {}),
        ("gh api user", {"shell": True}),
        ("gh", {}),
        (["programa"], {"executable": "/usr/local/bin/gh"}),
        (["GH.EXE", "api"], {}),
        ("cd . && gh api user", {"shell": True}),
        ("GH_TOKEN=x gh api user", {"shell": True}),
        ("true; (gh api user)", {"shell": True}),
        (["gh api user"], {"shell": True}),
        (["sh", "-c", "gh api user"], {}),
        (["bash", "-lc", "x"], {"executable": "gh"}),
        (["env", "-i", "GH_TOKEN=x", "gh", "api"], {}),
    ],
    ids=[
        "lista",
        "ruta",
        "bytes",
        "shell",
        "texto",
        "executable",
        "windows",
        "y-luego",
        "variable",
        "subshell",
        "shell-lista",
        "sh-c",
        "executable-con-shell",
        "env",
    ],  # fmt: skip
)
def test_la_fixture_autouse_impide_ejecutar_gh(
    args: object, kwargs: dict[str, object]
) -> None:
    with pytest.raises(RealGitHubCall):
        subprocess.run(args, check=False, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]


def test_executable_posicional() -> None:
    with pytest.raises(RealGitHubCall):
        subprocess.Popen(["programa"], -1, "/usr/bin/gh")


def test_un_proceso_hijo_encuentra_el_gh_falso_y_no_el_real() -> None:
    """Fuera del proceso de pytest no hay Popen vigilado: lo cubre el PATH."""
    hijo = (
        "import subprocess; r = subprocess.run(['gh', 'api', 'user'], "
        "capture_output=True); print(r.returncode, r.stderr.decode().strip())"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", hijo], capture_output=True, text=True, check=True
    )
    assert resultado.stdout.strip() == (
        "97 gh bloqueado en los tests: usa la fixture doble_github"
    )


def test_os_system_encuentra_el_gh_falso() -> None:
    assert os.waitstatus_to_exitcode(os.system("gh api user 2>/dev/null")) == 97


def test_la_fixture_autouse_tambien_cubre_popen_y_check_output() -> None:
    with pytest.raises(RealGitHubCall):
        subprocess.Popen(["gh", "--version"])
    with pytest.raises(RealGitHubCall):
        subprocess.check_output(["gh", "--version"])


def test_la_fixture_autouse_deja_ejecutar_otros_programas() -> None:
    """git, el propio Python y una orden de shell siguen funcionando."""
    resultado = subprocess.run(
        [sys.executable, "-c", "print('hola')"], capture_output=True, check=True
    )
    assert resultado.stdout.strip() == b"hola"
    assert subprocess.run(["git", "--version"], capture_output=True).returncode == 0
    assert subprocess.run("echo gh", shell=True, capture_output=True).stdout == b"gh\n"


def test_launches_gh_no_confunde_otros_programas() -> None:
    assert not launches_gh(["github-cli"])
    assert not launches_gh(["ghc", "--version"])
    assert not launches_gh(["git", "gh"])
    assert not launches_gh([])
    assert not launches_gh("", shell=True)
    assert not launches_gh("echo gh", shell=True)
    assert not launches_gh(["sh", "-c", "echo gh"])
    assert not launches_gh(["env", "GH=1", "git", "status"])
