"""Capa repo de menairos entorno (T-11, hito-0.md 3.4 y 3.7).

El git es el de verdad, dentro de tmp_path y sin la configuración de la
máquina; uv y pre-commit son del doble, que simula lo que escriben.
"""

import os
import shlex
from collections.abc import Sequence
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest
from ayuda_entorno import estados, foto, menairos_toml, paso, proyecto
from ayuda_stacks import manifiesto_lenguaje, partes, plantilla
from doble_sistema import FakeSystem, preparado

from menairos import stacks
from menairos.environment import Report, read_config, run_environment
from menairos.environment.repo import FIRST_COMMIT, RERUN

PASOS = ("git", "plantillas", "uv sync", "pre-commit", "primer commit")


def _repo(
    sistema: FakeSystem,
    raiz: Path,
    *,
    check_only: bool = False,
    roots: Sequence[Traversable] = (stacks.PACKAGE_ROOT,),
) -> Report:
    return run_environment(
        raiz, "repo", check_only=check_only, system=sistema, roots=roots
    )


def _git(sistema: FakeSystem, raiz: Path, *argumentos: str) -> str:
    resultado = sistema.run(["git", *argumentos], raiz)
    assert resultado.code == 0, resultado.err
    return resultado.out


def _compuestos(raiz: Path) -> dict[str, stacks.StackFile]:
    return stacks.compose(read_config(raiz))


def _con_historia(sistema: FakeSystem, raiz: Path) -> None:
    _git(sistema, raiz, "init", "-q", "-b", "main")
    (raiz / "README.md").write_text("# Proyecto con historia\n", encoding="utf-8")
    _git(sistema, raiz, "add", "README.md")
    _git(sistema, raiz, "commit", "-q", "-m", "primero")


def _todos(informe: Report, estado: str) -> bool:
    return [p.name for p in informe.steps()] == list(PASOS) and all(
        p.state == estado for p in informe.steps()
    )


# ── Carpeta vacía ───────────────────────────────────────────────────────────


def test_una_carpeta_vacia_queda_hecha_y_la_segunda_vez_todo_ok(
    tmp_path: Path,
) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    primera = _repo(sistema, raiz)
    assert _todos(primera, "hecho"), estados(primera)
    assert primera.ok

    assert _git(sistema, raiz, "log", "--format=%s").splitlines() == [FIRST_COMMIT]
    assert _git(sistema, raiz, "symbolic-ref", "--short", "HEAD").strip() == "main"
    assert _git(sistema, raiz, "status", "--porcelain") == ""
    versionados = set(_git(sistema, raiz, "ls-files").splitlines())
    assert set(_compuestos(raiz)) | {"uv.lock", "menairos.toml"} == versionados
    for ruta, fichero in _compuestos(raiz).items():
        assert (raiz / ruta).read_bytes() == fichero.text.encode()
        assert bool(os.stat(raiz / ruta).st_mode & 0o111) is fichero.executable, ruta
    commit = paso(primera, "repo", "primer commit")
    assert commit.lists == {"fuera_de_las_plantillas": ["menairos.toml"]}

    hechas = len(sistema.acting_calls())
    antes = foto(raiz)
    segunda = _repo(sistema, raiz)
    assert _todos(segunda, "ok"), estados(segunda)
    assert len(sistema.acting_calls()) == hechas
    assert foto(raiz) == antes


def test_nunca_hay_push(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    _repo(sistema, proyecto(sistema))
    assert not any("push" in argv for argv, _ in sistema.calls)


def test_comprobar_en_una_carpeta_vacia_no_escribe_nada(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    antes = foto(raiz)
    resultados = [_repo(sistema, raiz, check_only=True) for _ in range(2)]
    for informe in resultados:
        git = paso(informe, "repo", "git")
        assert (git.state, git.order) == ("manual", RERUN)
        assert informe.layers[0].not_run == list(PASOS[1:])
        assert not informe.ok
    assert estados(resultados[0]) == estados(resultados[1])
    assert foto(raiz) == antes
    assert not (raiz / ".git").exists()
    assert sistema.acting_calls() == []


def test_comprobar_dos_veces_en_un_repo_completo(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _repo(sistema, raiz)
    hechas = len(sistema.acting_calls())
    antes = foto(raiz)
    for _ in range(2):
        informe = _repo(sistema, raiz, check_only=True)
        assert _todos(informe, "ok"), estados(informe)
    assert len(sistema.acting_calls()) == hechas
    assert foto(raiz) == antes


def test_comprobar_un_fichero_que_falta(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _repo(sistema, raiz)
    (raiz / "SECURITY.md").unlink()
    informe = _repo(sistema, raiz, check_only=True)
    plantillas = paso(informe, "repo", "plantillas")
    assert (plantillas.state, plantillas.order) == ("manual", RERUN)
    assert plantillas.lists == {"faltan": ["SECURITY.md"]}
    assert not (raiz / "SECURITY.md").exists()


# ── Ficheros sueltos y conflictos ───────────────────────────────────────────


def test_los_ficheros_sueltos_entran_en_el_commit_y_se_listan(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    (raiz / "docs").mkdir()
    (raiz / "docs" / "producto.md").write_text("# Producto\n", encoding="utf-8")
    informe = _repo(sistema, raiz)
    assert informe.ok, estados(informe)
    assert paso(informe, "repo", "primer commit").lists == {
        "fuera_de_las_plantillas": ["docs/producto.md", "menairos.toml"]
    }
    assert "docs/producto.md" in _git(sistema, raiz, "ls-files")


@pytest.mark.parametrize("ruta", ["AGENTS.md", "pyproject.toml", ".gitignore"])
def test_un_fichero_distinto_es_un_conflicto_y_no_se_toca(
    tmp_path: Path, ruta: str
) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    (raiz / ruta).write_text("lo de antes\n", encoding="utf-8")
    antes = foto(raiz)[ruta]
    informe = _repo(sistema, raiz)
    plantillas = paso(informe, "repo", "plantillas")
    assert plantillas.state == "manual"
    assert plantillas.lists["conflictos"] == [f"{ruta}: existe con otro contenido"]
    assert foto(raiz)[ruta] == antes
    assert informe.layers[0].not_run == ["uv sync", "pre-commit", "primer commit"]
    assert sistema.run(["git", "rev-parse", "-q", "--verify", "HEAD"], raiz).code != 0
    assert not (raiz / "uv.lock").exists()
    assert (raiz / "SECURITY.md").is_file()  # lo demás sí se escribe


def test_un_repo_con_historia_no_lleva_primer_commit(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _con_historia(sistema, raiz)
    informe = _repo(sistema, raiz)
    assert informe.ok, estados(informe)
    commit = paso(informe, "repo", "primer commit")
    assert commit.state == "ok"
    assert "SECURITY.md" in commit.warnings[0]
    assert "uv.lock" in commit.warnings[0]
    assert _git(sistema, raiz, "log", "--format=%s").splitlines() == ["primero"]
    assert estados(_repo(sistema, raiz))[("repo", "plantillas")] == "ok"


def test_un_repo_con_historia_y_conflictos_no_se_toca(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _con_historia(sistema, raiz)
    for ruta in (".pre-commit-config.yaml", ".github/workflows/ci.yml"):
        (raiz / ruta).parent.mkdir(parents=True, exist_ok=True)
        (raiz / ruta).write_text("repos: []\n", encoding="utf-8")
    antes = foto(raiz)
    informe = _repo(sistema, raiz)
    conflictos = paso(informe, "repo", "plantillas").lists["conflictos"]
    assert len(conflictos) == 2
    despues = foto(raiz)
    assert {r: despues[r] for r in antes} == antes
    assert _git(sistema, raiz, "rev-list", "--count", "HEAD").strip() == "1"


def test_un_sh_igual_sin_bit_de_ejecucion_se_arregla(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _repo(sistema, raiz)
    n1 = raiz / "scripts" / "n1.sh"
    n1.chmod(0o644)
    informe = _repo(sistema, raiz)
    plantillas = paso(informe, "repo", "plantillas")
    assert plantillas.state == "hecho"
    assert plantillas.lists == {"sin_bit_de_ejecucion": ["scripts/n1.sh"]}
    assert n1.stat().st_mode & 0o111


def test_comprobar_un_sh_sin_bit_no_lo_arregla(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _repo(sistema, raiz)
    n1 = raiz / "scripts" / "n1.sh"
    n1.chmod(0o644)
    assert estados(_repo(sistema, raiz, check_only=True))[("repo", "plantillas")] == (
        "manual"
    )
    assert not n1.stat().st_mode & 0o111


def test_un_enlace_que_sale_de_la_raiz_es_un_conflicto(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    (raiz / "scripts").symlink_to(fuera, target_is_directory=True)
    informe = _repo(sistema, raiz)
    conflictos = paso(informe, "repo", "plantillas").lists["conflictos"]
    assert "scripts/n1.sh: «scripts» es un enlace simbólico" in conflictos
    assert list(fuera.iterdir()) == []


def test_un_fichero_donde_va_una_carpeta_es_un_conflicto(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    (raiz / "scripts").write_text("no soy una carpeta\n", encoding="utf-8")
    conflictos = paso(_repo(sistema, raiz), "repo", "plantillas").lists["conflictos"]
    assert "scripts/n1.sh: «scripts» no es una carpeta" in conflictos


# ── git ─────────────────────────────────────────────────────────────────────


def test_la_raiz_dentro_de_otro_repo_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    exterior = sistema.home() / "proyectos" / "grande"
    exterior.mkdir()
    _git(sistema, exterior, "init", "-q", "-b", "main")
    raiz = exterior / "sub"
    raiz.mkdir()
    (raiz / "menairos.toml").write_text(menairos_toml(), encoding="utf-8")
    git = paso(_repo(sistema, raiz), "repo", "git")
    assert git.state == "error"
    assert "está dentro del repo" in git.detail
    assert sorted(p.name for p in raiz.iterdir()) == ["menairos.toml"]


def test_un_repo_que_git_no_reconoce_no_se_reinicia(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _git(sistema, raiz, "init", "-q", "-b", "main")
    sistema.answer(
        ["git", "rev-parse", "--show-toplevel"],
        code=128,
        err=f"fatal: detected dubious ownership in repository at '{raiz}'\n",
    )
    git = paso(_repo(sistema, raiz), "repo", "git")
    assert git.state == "error"
    assert "dubious ownership" in git.detail
    inits = [argv for argv in sistema.acting_calls() if argv[:2] == ("git", "init")]
    assert len(inits) == 1  # el del propio test


def test_un_fichero_que_no_se_puede_leer_es_un_conflicto(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    agentes = raiz / "AGENTS.md"
    agentes.write_text("mío\n", encoding="utf-8")
    agentes.chmod(0)
    try:
        if os.access(agentes, os.R_OK):
            pytest.skip("con root, los permisos no impiden leer")
        conflictos = paso(_repo(sistema, raiz), "repo", "plantillas").lists[
            "conflictos"
        ]
    finally:
        agentes.chmod(0o644)
    assert "AGENTS.md: no se puede leer: Permission denied" in conflictos


def test_un_repo_sin_commits_en_master_pasa_a_main(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _git(sistema, raiz, "init", "-q")  # defaultBranch = master en la config del doble
    assert _git(sistema, raiz, "symbolic-ref", "--short", "HEAD").strip() == "master"
    assert estados(_repo(sistema, raiz, check_only=True))[("repo", "git")] == "manual"
    informe = _repo(sistema, raiz)
    assert paso(informe, "repo", "git").state == "hecho"
    assert informe.ok
    assert _git(sistema, raiz, "symbolic-ref", "--short", "HEAD").strip() == "main"


def test_git_sin_identidad_es_manual(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.git_config.write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
    raiz = proyecto(sistema)
    commit = paso(_repo(sistema, raiz), "repo", "primer commit")
    assert commit.state == "manual"
    assert commit.order is not None and "user.email" in commit.order
    assert sistema.run(["git", "rev-parse", "-q", "--verify", "HEAD"], raiz).code != 0


def test_sin_git_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.remove("git")
    raiz = proyecto(sistema)
    assert paso(_repo(sistema, raiz), "repo", "git").state == "error"
    assert sorted(p.name for p in raiz.iterdir()) == ["menairos.toml"]


# ── uv sync ─────────────────────────────────────────────────────────────────


def test_con_uv_lock_se_sincroniza_con_locked(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    (raiz / "uv.lock").write_text("version = 1\n# el de antes\n", encoding="utf-8")
    antes = (raiz / "uv.lock").read_bytes()
    informe = _repo(sistema, raiz)
    assert informe.ok, estados(informe)
    llamadas = [argv for argv, _ in sistema.calls]
    assert ("uv", "sync", "--locked") in llamadas
    assert ("uv", "sync") not in llamadas
    assert (raiz / "uv.lock").read_bytes() == antes


def test_un_uv_lock_desfasado_es_manual(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.answer(["uv", "lock", "--check"], code=1)
    raiz = proyecto(sistema)
    (raiz / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    uv = paso(_repo(sistema, raiz), "repo", "uv sync")
    assert (uv.state, uv.order) == ("manual", "uv lock")
    assert not any(
        argv[:2] == ("uv", "sync") and "--check" not in argv
        for argv, _ in sistema.calls
    )


def test_un_uv_sync_que_falla_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    sistema.answer(["uv", "sync"], code=2, err="error: sin red\n")
    informe = _repo(sistema, proyecto(sistema))
    uv = paso(informe, "repo", "uv sync")
    assert uv.state == "error"
    assert "sin red" in uv.detail
    assert informe.layers[0].not_run == ["pre-commit", "primer commit"]


# ── pre-commit ──────────────────────────────────────────────────────────────


def test_core_hooks_path_es_manual(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _git(sistema, raiz, "init", "-q", "-b", "main")
    _git(sistema, raiz, "config", "core.hooksPath", "otros-hooks")
    pre = paso(_repo(sistema, raiz), "repo", "pre-commit")
    orden = "git config --file .git/config --unset-all core.hooksPath"
    assert (pre.state, pre.order) == ("manual", orden)
    _git(sistema, raiz, *shlex.split(orden)[1:])
    assert paso(_repo(sistema, raiz), "repo", "pre-commit").state == "hecho"


def test_core_hooks_path_global_pide_quitarlo_de_la_global(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    with sistema.git_config.open("a", encoding="utf-8") as config:
        config.write("[core]\n\thooksPath = /otros/hooks\n")
    raiz = proyecto(sistema)
    pre = paso(_repo(sistema, raiz), "repo", "pre-commit")
    orden = f"git config --file {sistema.git_config} --unset-all core.hooksPath"
    assert (pre.state, pre.order) == ("manual", orden)
    assert "configuración global" in pre.detail
    _git(sistema, raiz, *shlex.split(orden)[1:])
    assert paso(_repo(sistema, raiz), "repo", "pre-commit").state == "hecho"


def test_un_hook_ajeno_es_manual_y_no_se_toca(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _git(sistema, raiz, "init", "-q", "-b", "main")
    hook = raiz / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho mío\n", encoding="utf-8")
    pre = paso(_repo(sistema, raiz), "repo", "pre-commit")
    assert pre.state == "manual"
    assert hook.read_text(encoding="utf-8") == "#!/bin/sh\necho mío\n"
    assert ("uv", "run", "--frozen", "pre-commit", "install") not in [
        argv for argv, _ in sistema.calls
    ]


def test_un_hook_que_falla_en_el_primer_commit_se_completa_despues(
    tmp_path: Path,
) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema)
    _repo(sistema, raiz, check_only=True)
    _git(sistema, raiz, "init", "-q", "-b", "main")
    hook = raiz / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        "#!/bin/sh\n# File generated by pre-commit: https://pre-commit.com\n"
        "echo 'leaks found' >&2\nexit 1\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    primera = _repo(sistema, raiz)
    commit = paso(primera, "repo", "primer commit")
    assert commit.state == "error"
    assert "leaks found" in commit.detail

    hook.write_text(hook.read_text(encoding="utf-8").replace("exit 1", "exit 0"))
    segunda = _repo(sistema, raiz)
    assert paso(segunda, "repo", "primer commit").state == "hecho"
    assert segunda.ok


# ── Composición ─────────────────────────────────────────────────────────────


def test_una_plantilla_que_no_existe_es_un_error(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raiz = proyecto(sistema, plantillas=("base", "no-existe"))
    plantillas = paso(_repo(sistema, raiz), "repo", "plantillas")
    assert plantillas.state == "error"
    assert "la plantilla «no-existe» no existe" in plantillas.detail
    assert sorted(p.name for p in raiz.iterdir()) == [".git", "menairos.toml"]


@pytest.mark.parametrize(
    ("ficheros", "mensaje"),
    [
        (
            {"SECURITY.md.plantilla": "otra\n"},
            "«SECURITY.md» lo traen «base» y «x», y no es fusionable",
        ),
        ({"x/a.txt.plantilla": "{{proyecto.nombr}}\n"}, "la clave «proyecto.nombr»"),
        ({"x/b.txt.plantilla": "{{ proyecto.nombre }}\n"}, "x/x/b.txt"),
    ],
    ids=["no-fusionable", "clave-que-no-existe", "hueco-mal-escrito"],
)
def test_una_composicion_que_falla_no_escribe_nada(
    tmp_path: Path, ficheros: dict[str, str], mensaje: str
) -> None:
    sistema = preparado(tmp_path)
    raices = tmp_path / "plantillas"
    plantilla(raices, "x", manifiesto_lenguaje("x"), partes("x") | ficheros)
    raiz = proyecto(sistema, plantillas=("base", "x"))
    informe = _repo(sistema, raiz, roots=(stacks.PACKAGE_ROOT, raices))
    plantillas = paso(informe, "repo", "plantillas")
    assert plantillas.state == "error"
    assert mensaje in plantillas.detail
    assert sorted(p.name for p in raiz.iterdir()) == [".git", "menairos.toml"]


def test_una_plantilla_sin_preparacion_va_directa_al_commit(tmp_path: Path) -> None:
    sistema = preparado(tmp_path)
    raices = tmp_path / "plantillas"
    plantilla(raices, "x", manifiesto_lenguaje("x"), partes("x"))
    raiz = proyecto(sistema, plantillas=("base", "x"))
    informe = _repo(sistema, raiz, roots=(stacks.PACKAGE_ROOT, raices))
    assert [p.name for p in informe.steps()] == ["git", "plantillas", "primer commit"]
    assert informe.ok, estados(informe)
