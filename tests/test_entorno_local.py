"""Capa local de menairos entorno (T-11, hito-0.md 3.4 y 3.7).

Todo con el doble del sistema: ningún test mira las herramientas, las rutas ni
el .wslconfig de la máquina real.
"""

from collections.abc import Sequence
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest
from ayuda_entorno import estados, paso, proyecto
from ayuda_stacks import manifiesto_lenguaje, partes, plantilla
from doble_sistema import FakeSystem, preparado

from menairos import github, stacks
from menairos.environment import Report, run_environment
from menairos.environment.local import PROFILE_ARGV, satisfies, version_of


def _local(
    sistema: FakeSystem,
    raiz: Path,
    *,
    check_only: bool = False,
    roots: Sequence[Traversable] = (stacks.PACKAGE_ROOT,),
) -> Report:
    return run_environment(
        raiz, "local", check_only=check_only, system=sistema, roots=roots
    )


# ── Versiones ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("salida", "pedida", "cumple"),
    [
        ("uv 0.13.9 (x)", ">=0.13.10", False),
        ("uv 0.13.10 (x86_64-unknown-linux-gnu)", ">=0.13.10", True),
        ("git version 2.43", ">=2.43.0", True),
        ("gh version 2.103.3 (2026-10-26)", ">=2.103.3", True),
        ("Python 3.14.2", "3.14", True),
        ("Python 3.13.9", "3.14", False),
        ("Python 3.140.0", "3.14", False),
        ("2.1.326 (Claude Code)", ">=2.1.326", True),
        ("uv 0.9.0", ">=0.13", False),
        ("uv 1.0", ">=0.13.10", True),
    ],
)
def test_las_versiones_se_comparan_por_numeros(
    salida: str, pedida: str, cumple: bool
) -> None:
    version = version_of(salida)
    assert version is not None
    assert satisfies(version, pedida) is cumple


def test_version_of_sin_numeros() -> None:
    assert version_of("sin versión") is None


# ── Todo en orden ───────────────────────────────────────────────────────────


def test_con_todo_en_orden_la_capa_local_queda_en_verde(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    informe = _local(sistema, proyecto(sistema))
    assert informe.ok
    assert estados(informe) == {
        ("local", "ruta"): "ok",
        ("local", "git"): "ok",
        ("local", github.PROGRAM): "ok",
        ("local", "sesión de GitHub"): "ok",
        ("local", "claude"): "ok",
        ("local", "uv"): "ok",
        ("local", "python"): "ok",
        ("local", "codex"): "ok",
    }
    assert paso(informe, "local", "uv").detail == "0.13.10 (>=0.13.10)"
    assert all(not p.warnings for p in informe.steps())


def test_la_capa_local_no_escribe_nada(tmp_path: Path) -> None:
    sistema = preparado(tmp_path, wsl=True)
    raiz = proyecto(sistema)
    _local(sistema, raiz)
    _local(sistema, raiz, check_only=True)
    assert sistema.acting_calls() == []
    assert sorted(p.name for p in raiz.iterdir()) == ["menairos.toml"]


# ── Herramientas ────────────────────────────────────────────────────────────


def test_una_herramienta_por_debajo_de_su_version_es_manual(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.install("uv", "uv 0.13.9 (x86_64-unknown-linux-gnu)")
    informe = _local(sistema, proyecto(sistema))
    uv = paso(informe, "local", "uv")
    assert (uv.state, uv.order) == ("manual", "uv self update")
    assert uv.detail == "tiene 0.13.9 y se pide >=0.13.10"
    assert not informe.ok


def test_una_herramienta_que_falta_es_manual_con_su_orden(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.remove("claude")
    claude = paso(_local(sistema, proyecto(sistema)), "local", "claude")
    assert claude.state == "manual"
    assert claude.order == "curl -fsSL https://claude.ai/install.sh | bash"
    assert claude.detail == "no está instalada (se pide >=2.1.326)"


def test_sin_gh_no_se_mira_la_sesion(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.remove(github.PROGRAM)
    informe = _local(sistema, proyecto(sistema))
    assert estados(informe)[("local", github.PROGRAM)] == "manual"
    assert ("local", "sesión de GitHub") not in estados(informe)
    assert "install_linux.md" in paso(informe, "local", github.PROGRAM).detail


def test_gh_sin_sesion_es_manual_con_auth_login(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.answer(github.AUTH_STATUS, code=1, err="You are not logged in\n")
    sesion = paso(_local(sistema, proyecto(sistema)), "local", "sesión de GitHub")
    assert (sesion.state, sesion.order) == ("manual", github.AUTH_LOGIN)


def test_una_version_que_no_se_entiende_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.install("git", "git, de una versión rara")
    git = paso(_local(sistema, proyecto(sistema)), "local", "git")
    assert git.state == "error"
    assert "git --version" in git.detail


def test_python_lo_busca_uv(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.answer(["uv", "python", "find", "--no-project", "3.14"], code=2)
    python = paso(_local(sistema, proyecto(sistema)), "local", "python")
    assert (python.state, python.order) == ("manual", "uv python install 3.14")


def test_sin_uv_python_pide_instalar_uv(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.remove("uv")
    python = paso(_local(sistema, proyecto(sistema)), "local", "python")
    assert python.state == "manual"
    assert python.order == "curl -LsSf https://astral.sh/uv/install.sh | sh"


def test_codex_se_mira_si_algun_revisor_es_codex(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.remove("codex")
    codex = paso(_local(sistema, proyecto(sistema)), "local", "codex")
    assert (codex.state, codex.order) == ("manual", "npm install -g @openai/codex")


def test_codex_no_se_mira_si_ningun_revisor_es_codex(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    claude = (
        '\n[revisores]\nspec = "claude"\npr = "claude"\n'
        'segunda_opinion_critica = "claude"\n'
    )
    informe = _local(sistema, proyecto(sistema, extra=claude))
    assert ("local", "codex") not in estados(informe)
    assert not any(argv[0] == "codex" for argv, _ in sistema.calls)


def test_codex_sin_version_minima_vale_con_que_este(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.install("codex", "codex, sin número")
    codex = paso(_local(sistema, proyecto(sistema)), "local", "codex")
    assert (codex.state, codex.detail) == ("ok", "codex, sin número")


def test_una_herramienta_sin_version_que_no_arranca_es_un_error(
    tmp_path: Path,
) -> None:
    sistema = preparado(tmp_path)
    sistema.answer(
        ["codex", "--version"], code=127, err="env: node: No such file or directory\n"
    )
    codex = paso(_local(sistema, proyecto(sistema)), "local", "codex")
    assert codex.state == "error"
    assert "node" in codex.detail


def test_docker_solo_si_una_plantilla_lo_pide(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    assert ("local", "docker") not in estados(_local(sistema, proyecto(sistema)))

    plantillas = tmp_path / "plantillas"
    manifiesto = manifiesto_lenguaje("x") + '\n[herramientas]\ndocker = ">=27.0"\n'
    plantilla(plantillas, "x", manifiesto, partes("x"))
    raiz = proyecto(sistema, "con-docker", plantillas=("base", "x"))
    informe = _local(sistema, raiz, roots=(stacks.PACKAGE_ROOT, plantillas))
    docker = paso(informe, "local", "docker")
    assert (docker.state, docker.order) == ("manual", None)
    assert "docs.docker.com" in docker.detail

    sistema.install("docker", "Docker version 27.3.1, build ce12230")
    informe = _local(sistema, raiz, roots=(stacks.PACKAGE_ROOT, plantillas))
    assert estados(informe)[("local", "docker")] == "ok"


def test_una_plantilla_que_no_existe_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema, plantillas=("base", "no-existe"))
    herramientas = paso(_local(sistema, raiz), "local", "herramientas")
    assert herramientas.state == "error"
    assert "la plantilla «no-existe» no existe" in herramientas.detail


# ── Ruta ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("unidad", ["/mnt/c/Users/prueba/demo", "/mnt/d/demo"])
def test_un_repo_en_una_unidad_de_windows_es_un_error(
    tmp_path: Path, unidad: str
) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    sistema.fake_paths[raiz] = Path(unidad)
    ruta = paso(_local(sistema, raiz), "local", "ruta")
    assert ruta.state == "error"
    assert "unidad de Windows" in ruta.detail


def test_mnt_wsl_no_es_una_unidad_de_windows(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    sistema.fake_paths[raiz] = Path("/mnt/wsl/demo")
    ruta = paso(_local(sistema, raiz), "local", "ruta")
    assert ruta.state == "ok"
    assert ruta.warnings  # fuera de ~/proyectos/


def test_por_un_enlace_tambien_cuenta_la_ruta_real(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    destino = tmp_path / "windows"
    destino.mkdir()
    enlace = sistema.home() / "proyectos" / "enlazado"
    enlace.symlink_to(destino)
    (destino / "menairos.toml").write_text(
        (proyecto(sistema) / "menairos.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sistema.fake_paths[destino] = Path("/mnt/c/proyecto")
    assert paso(_local(sistema, enlace), "local", "ruta").state == "error"


@pytest.mark.parametrize(
    ("relativa", "aviso"),
    [
        ("proyectos/demo", False),
        ("proyectos/grupo/demo", False),
        ("proyectos", True),
        ("proyectos-viejos/demo", True),
        ("otros/demo", True),
    ],
)
def test_fuera_de_proyectos_es_un_aviso(
    tmp_path: Path, relativa: str, aviso: bool
) -> None:
    sistema = preparado(tmp_path)
    raiz = sistema.home() / relativa
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "menairos.toml").write_text(
        (proyecto(sistema, "molde") / "menairos.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    ruta = paso(_local(sistema, raiz), "local", "ruta")
    assert ruta.state == "ok"
    assert bool(ruta.warnings) is aviso


# ── .wslconfig ──────────────────────────────────────────────────────────────


def _wsl(tmp_path: Path, texto: str | None) -> FakeSystem:
    sistema = preparado(tmp_path, wsl=True)
    perfil = tmp_path / "windows" / "Users" / "Prueba"
    perfil.mkdir(parents=True)
    if texto is not None:
        (perfil / ".wslconfig").write_text(texto, encoding="utf-8")
    sistema.install("cmd.exe")
    sistema.install("wslpath")
    sistema.answer(PROFILE_ARGV, out="C:\\Users\\Prueba\r\n")
    sistema.answer(["wslpath", "-u", "C:\\Users\\Prueba"], out=f"{perfil}\n")
    return sistema


def test_wslconfig_con_memoria_y_swap(tmp_path: Path) -> None:
    sistema = _wsl(tmp_path, "[wsl2]\nmemory=8GB\nswap=8GB\n")
    wsl = paso(_local(sistema, proyecto(sistema)), "local", ".wslconfig")
    assert (wsl.state, wsl.warnings) == ("ok", [])


@pytest.mark.parametrize(
    "texto",
    [None, "[wsl2]\nmemory=8GB\n", "[otra]\nmemory=8GB\nswap=8GB\n", "sin secciones"],
    ids=["no-existe", "sin-swap", "otra-seccion", "no-se-lee"],
)
def test_wslconfig_incompleto_es_solo_un_aviso(
    tmp_path: Path, texto: str | None
) -> None:
    sistema = _wsl(tmp_path, texto)
    informe = _local(sistema, proyecto(sistema))
    wsl = paso(informe, "local", ".wslconfig")
    assert wsl.state == "ok"
    assert len(wsl.warnings) == 1
    assert informe.ok


def test_sin_perfil_de_windows_es_un_aviso(tmp_path: Path) -> None:
    sistema = _wsl(tmp_path, None)
    sistema.answer(PROFILE_ARGV, code=1)
    wsl = paso(_local(sistema, proyecto(sistema)), "local", ".wslconfig")
    assert wsl.warnings == ["no se pudo comprobar .wslconfig"]


def test_fuera_de_wsl_no_se_mira_wslconfig(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    informe = _local(sistema, proyecto(sistema))
    assert ("local", ".wslconfig") not in estados(informe)
    assert not any(argv[0] == "cmd.exe" for argv, _ in sistema.calls)
