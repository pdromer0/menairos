"""La orden menairos entorno en la CLI y la barrera del sistema real (T-11)."""

import json
from pathlib import Path

import pytest
from ayuda_entorno import proyecto
from doble_sistema import FakeSystem, RealSystemCall

from menairos import github
from menairos.cli import main
from menairos.environment import core, run_environment


def _main(capsys: pytest.CaptureFixture[str], *argumentos: str) -> tuple[int, str, str]:
    codigo = main(["entorno", *argumentos])
    salida = capsys.readouterr()
    return codigo, salida.out, salida.err


def test_sin_capa_hace_local_y_repo_y_avisa_de_github_y_nube(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = proyecto(doble_sistema)
    codigo, salida, errores = _main(capsys, "--raiz", str(raiz))
    assert codigo == 0, salida
    assert "\nCapa local\n" in salida and "\nCapa repo\n" in salida
    assert "  hecho  primer commit" in salida
    assert "Las capas github y nube aún no están" in salida
    assert salida.endswith("\nResultado: todo en verde.\n")
    assert "gitleaks se compila" in errores  # el aviso, antes del commit

    codigo, salida, _ = _main(capsys, "--raiz", str(raiz), "--json")
    datos = json.loads(salida)
    assert codigo == 0
    assert datos["ok"] is True and datos["comprobar"] is False
    assert [c["capa"] for c in datos["capas"]] == ["local", "repo"]
    assert {p["estado"] for c in datos["capas"] for p in c["pasos"]} == {"ok"}
    assert datos["despues"] == ["github", "nube"]


def test_con_una_capa_no_avisa_de_las_que_faltan(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo, salida, _ = _main(capsys, "local", "--raiz", str(proyecto(doble_sistema)))
    assert codigo == 0
    assert "Capa repo" not in salida
    assert "Las capas github y nube" not in salida


def test_comprobar_sale_con_1_y_da_la_orden(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = proyecto(doble_sistema)
    codigo, salida, _ = _main(
        capsys, "repo", "--comprobar", "--json", "--raiz", str(raiz)
    )
    datos = json.loads(salida)
    assert codigo == 1
    assert datos["comprobar"] is True
    git = datos["capas"][0]["pasos"][0]
    assert (git["estado"], git["orden"]) == ("manual", "menairos entorno repo")
    assert datos["capas"][0]["sin_ejecutar"] == [
        "plantillas",
        "uv sync",
        "pre-commit",
        "primer commit",
    ]
    assert not (raiz / ".git").exists()


def test_un_paso_manual_sale_con_1_aunque_no_haya_errores(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    doble_sistema.answer(github.AUTH_STATUS, code=1)
    raiz = proyecto(doble_sistema)
    codigo, salida, _ = _main(capsys, "--raiz", str(raiz))
    assert codigo == 1
    assert f"orden: {github.AUTH_LOGIN}" in salida
    assert "no se ejecutó: antes tiene que quedar en verde la capa local" in salida
    assert salida.endswith("\nResultado: 2 manuales.\n")
    assert not (raiz / ".git").exists()


def test_un_conflicto_se_lista_en_el_texto(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = proyecto(doble_sistema)
    (raiz / "AGENTS.md").write_text("mío\n", encoding="utf-8")
    codigo, salida, _ = _main(capsys, "repo", "--raiz", str(raiz))
    assert codigo == 1
    assert "conflictos:\n           AGENTS.md: existe con otro contenido\n" in salida
    assert "Sin ejecutar: uv sync, pre-commit, primer commit." in salida


def test_sin_menairos_toml_sale_con_2(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    codigo, salida, errores = _main(capsys, "--raiz", str(tmp_path))
    assert (codigo, salida) == (2, "")
    assert "no hay menairos.toml" in errores and "/crear-spec" in errores
    assert doble_sistema.calls == []


def test_un_menairos_toml_no_valido_sale_con_2(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = proyecto(doble_sistema, extra='\n[modo]\ndefecto = "rapido"\n')
    codigo, _, errores = _main(capsys, "--raiz", str(raiz))
    assert codigo == 2
    assert "menairos.toml no es válido (modo.defecto" in errores


def test_una_raiz_que_no_existe_sale_con_2(
    doble_sistema: FakeSystem, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    codigo, _, errores = _main(capsys, "--raiz", str(tmp_path / "no-existe"))
    assert codigo == 2
    assert "no es una carpeta" in errores


@pytest.mark.parametrize("capa", ["github", "nube"])
def test_las_capas_de_t12_aun_no_se_admiten(
    capsys: pytest.CaptureFixture[str], capa: str
) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["entorno", capa])
    assert salida.value.code == 2
    assert "orden no válida" in capsys.readouterr().err


# ── La barrera ──────────────────────────────────────────────────────────────


def test_sin_doble_la_orden_no_llega_al_sistema_real(tmp_path: Path) -> None:
    (tmp_path / "menairos.toml").write_text(
        '[menairos]\nversion = "3.0.0"\n[proyecto]\nnombre = "demo"\n'
        'repo = "ejemplo/demo"\n[stack]\nplantillas = ["base", "python-uv"]\n',
        encoding="utf-8",
    )
    with pytest.raises(RealSystemCall):
        run_environment(tmp_path, "local")
    with pytest.raises(RealSystemCall):
        core.default_system()


def test_el_entorno_de_los_programas_no_lleva_otro_repo_ni_otro_venv() -> None:
    padre = {
        "PATH": "/usr/bin",
        "GIT_DIR": "/otro/.git",
        "GIT_INDEX_FILE": "/otro/.git/index",
        "GIT_WORK_TREE": "/otro",
        "GIT_AUTHOR_NAME": "Prueba",
        "VIRTUAL_ENV": "/otro/.venv",
    }
    assert core.environment_for_children(padre) == {
        "PATH": "/usr/bin",
        "GIT_AUTHOR_NAME": "Prueba",
        **github.GH_ENV,
    }


def test_la_raiz_del_json_es_la_ruta_real(
    doble_sistema: FakeSystem,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raiz = proyecto(doble_sistema)
    monkeypatch.chdir(raiz)
    _, salida, _ = _main(capsys, "local", "--json")
    assert json.loads(salida)["raiz"] == str(raiz.resolve())


def test_el_sistema_real_no_lanza_lo_que_no_existe(tmp_path: Path) -> None:
    sistema = core.RealSystem()
    resultado = sistema.run(["programa-que-no-existe-en-ninguna-parte"], tmp_path)
    assert resultado.code == 127
    assert sistema.which("programa-que-no-existe-en-ninguna-parte") is None
