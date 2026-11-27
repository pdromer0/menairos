"""Tests de las plantillas de stack y del contrato común (T-10, hito-0.md 3.3).

La composición se prueba en memoria; los scripts que compone, en
test_scripts_contrato.py, y un proyecto generado de verdad, en
test_stack_generado.py (slow).
"""

import difflib
import json
import tomllib
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest
import yaml
from ayuda_stacks import (
    JUGUETES,
    RAICES,
    RAIZ,
    configuracion,
    manifiesto_lenguaje,
    partes,
    plantilla,
)

from menairos import stacks
from menairos.schemas import load_document, load_text
from menairos.stacks import Contract, Owner, StackError

CARPETA = RAIZ / "src" / "menairos" / "plantillas" / "stacks"


def _error(funcion, *argumentos, **opciones) -> str:  # type: ignore[no-untyped-def]
    with pytest.raises(StackError) as error:
        funcion(*argumentos, **opciones)
    return str(error.value)


def _base_y(tmp_path: Path) -> tuple[Traversable, ...]:
    """Las raíces con las plantillas del paquete y las creadas en ``tmp_path``."""
    return (stacks.PACKAGE_ROOT, tmp_path)


# ── Las plantillas del paquete ──────────────────────────────────────────────


def test_las_plantillas_del_paquete_son_base_y_python_uv() -> None:
    assert stacks.available() == ("base", "python-uv")


@pytest.mark.parametrize("nombre", ["base", "python-uv"])
def test_cada_plantilla_del_paquete_se_carga(nombre: str) -> None:
    plantilla_cargada = stacks.load(nombre)
    assert plantilla_cargada.name == nombre
    assert plantilla_cargada.version == "1.0.0"


def test_todos_los_ficheros_de_las_plantillas_llevan_el_sufijo() -> None:
    ficheros = [p for p in CARPETA.rglob("*") if p.is_file()]
    assert ficheros
    for fichero in ficheros:
        assert fichero.name == stacks.MANIFEST or fichero.name.endswith(".plantilla"), (
            fichero
        )


def test_las_ordenes_de_python_uv_aparecen_tal_cual_en_sus_partes() -> None:
    """lint, tipos y tests_area son lo que ejecuta la parte N1; lint y tipos, la N3."""
    python = stacks.load("python-uv")
    n1 = python.files["scripts/stack/python-uv/n1.sh"]
    n3 = python.files["scripts/stack/python-uv/n3.sh"]
    tests_area = python.orders["tests_area"].replace("{rutas}", '"${rutas[@]}"')
    for orden in (python.orders["lint"], python.orders["tipos"], tests_area):
        assert f"paso {orden}\n" in n1, orden
    for orden in (python.orders["lint"], python.orders["tipos"]):
        assert f"paso {orden}\n" in n3, orden
    assert python.orders["formato"].replace(" .", " --check .") in n3


def test_denegar_de_base_es_el_deny_de_menairos() -> None:
    ajustes = json.loads((RAIZ / ".claude" / "settings.json").read_text("utf-8"))
    assert list(stacks.load("base").deny) == ajustes["permissions"]["deny"]


def test_las_versiones_de_los_manifiestos_llevan_su_fecha() -> None:
    for nombre in ("base", "python-uv"):
        texto = (CARPETA / nombre / stacks.MANIFEST).read_text("utf-8")
        cabecera = texto.split("[herramientas]")[0].rsplit("\n\n", 1)[-1]
        assert "comprobadas" in cabecera.lower() and "2026-" in cabecera, nombre


# ── Manifiestos que no valen ────────────────────────────────────────────────


def test_un_manifiesto_que_no_cumple_el_esquema_es_un_error(tmp_path: Path) -> None:
    plantilla(tmp_path, "mala", '[plantilla]\nnombre = "mala"\n', {})
    mensaje = _error(stacks.load, "mala", (tmp_path,))
    assert "«mala/plantilla.toml»" in mensaje
    assert "falta la clave obligatoria «version»" in mensaje


def test_un_manifiesto_que_no_es_toml_es_un_error(tmp_path: Path) -> None:
    plantilla(tmp_path, "rota", "[plantilla\n", {})
    assert "no se puede leer" in _error(stacks.load, "rota", (tmp_path,))


def test_un_fichero_sin_el_sufijo_es_un_error(tmp_path: Path) -> None:
    plantilla(
        tmp_path, "x", manifiesto_lenguaje("x"), partes("x") | {"README.md": "hola\n"}
    )
    mensaje = _error(stacks.load, "x", (tmp_path,))
    assert "«x/ficheros/README.md» no acaba en «.plantilla»" in mensaje


def test_el_nombre_tiene_que_ser_el_de_su_carpeta(tmp_path: Path) -> None:
    plantilla(tmp_path, "carpeta", manifiesto_lenguaje("otro"), partes("otro"))
    assert "no es el de su carpeta" in _error(stacks.load, "carpeta", (tmp_path,))


def test_una_plantilla_que_se_requiere_a_si_misma_es_un_error(tmp_path: Path) -> None:
    plantilla(tmp_path, "x", manifiesto_lenguaje("x", requiere='["x"]'), partes("x"))
    assert "se requiere a sí misma" in _error(stacks.load, "x", (tmp_path,))


def test_le_falta_una_parte(tmp_path: Path) -> None:
    ficheros = {"scripts/stack/x/n1.sh.plantilla": "#!/usr/bin/env bash\n"}
    plantilla(tmp_path, "x", manifiesto_lenguaje("x"), ficheros)
    assert "falta el fichero «scripts/stack/x/n3.sh.plantilla»" in _error(
        stacks.load, "x", (tmp_path,)
    )


def test_una_orden_de_otro_tipo_y_un_hueco_que_falta(tmp_path: Path) -> None:
    manifiesto = manifiesto_lenguaje("x").replace(
        'tests_area = "p {rutas}"', 'tests_area = "p"\nn1 = "scripts/n1.sh"'
    )
    plantilla(tmp_path, "x", manifiesto, partes("x"))
    mensaje = _error(stacks.load, "x", (tmp_path,))
    assert "la orden «n1» no es de una plantilla de tipo lenguaje" in mensaje
    assert "la orden «tests_area» tiene que llevar el hueco {rutas}" in mensaje


def test_un_fusionable_sin_regla_o_que_no_esta(tmp_path: Path) -> None:
    manifiesto = manifiesto_lenguaje("x", fusionables='["README.md", "AGENTS.md"]')
    plantilla(tmp_path, "x", manifiesto, partes("x") | {"README.md.plantilla": "x\n"})
    mensaje = _error(stacks.load, "x", (tmp_path,))
    assert "«README.md» no se puede fusionar" in mensaje
    assert "el fusionable «AGENTS.md» no está en ficheros/" in mensaje


@pytest.mark.parametrize("generado", stacks.GENERATED)
def test_una_plantilla_no_puede_traer_lo_que_genera_menairos(
    tmp_path: Path, generado: str
) -> None:
    ficheros = partes("x") | {f"{generado}.plantilla": "{}\n"}
    plantilla(tmp_path, "x", manifiesto_lenguaje("x"), ficheros)
    assert f"trae «{generado}», que genera menairos" in _error(
        stacks.load, "x", (tmp_path,)
    )


def _base_propia(tmp_path: Path, ci: str) -> None:
    base = stacks.load("base")
    ficheros = {f"{ruta}.plantilla": texto for ruta, texto in base.files.items()}
    ficheros[f"{stacks.CI_FILE}.plantilla"] = ci
    manifiesto = (CARPETA / "base" / stacks.MANIFEST).read_text("utf-8")
    plantilla(tmp_path, "base", manifiesto, ficheros)


@pytest.mark.parametrize(
    "ci",
    [
        "jobs: {}\n",
        f"{stacks.CI_MARKER}\n\n{stacks.CI_MARKER}\n\n",
        f"{stacks.CI_MARKER}\n      - name: N3\n",
    ],
    ids=["sin-marcador", "dos-marcadores", "sin-linea-en-blanco"],
)
def test_el_marcador_del_ci_de_base(tmp_path: Path, ci: str) -> None:
    _base_propia(tmp_path, ci)
    assert "línea marcador" in _error(stacks.load, "base", (tmp_path,))


def test_una_plantilla_de_lenguaje_no_lleva_el_marcador(tmp_path: Path) -> None:
    ficheros = partes("x") | {
        f"{stacks.CI_FILE}.plantilla": f"{stacks.CI_MARKER}\n",
    }
    manifiesto = manifiesto_lenguaje("x", fusionables=f'["{stacks.CI_FILE}"]')
    plantilla(tmp_path, "x", manifiesto, ficheros)
    assert "lleva la línea marcador, que es de base" in _error(
        stacks.load, "x", (tmp_path,)
    )


def test_solo_base_puede_ser_de_tipo_base(tmp_path: Path) -> None:
    manifiesto = (CARPETA / "base" / stacks.MANIFEST).read_text("utf-8")
    base = stacks.load("base")
    ficheros = {f"{ruta}.plantilla": texto for ruta, texto in base.files.items()}
    plantilla(tmp_path, "otra", manifiesto.replace('"base"', '"otra"', 1), ficheros)
    assert "solo la plantilla «base» puede ser de tipo base" in _error(
        stacks.load, "otra", (tmp_path,)
    )


def test_el_mismo_nombre_en_dos_raices_es_un_error(tmp_path: Path) -> None:
    plantilla(tmp_path, "base", "", {})
    assert "«base» está repetida" in _error(stacks.available, _base_y(tmp_path))


def test_una_plantilla_que_no_existe() -> None:
    mensaje = _error(stacks.load, "rust")
    assert mensaje == "la plantilla «rust» no existe; las que hay: base, python-uv"


# ── Orden y stack ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("escritas", "aplicadas"),
    [
        (["python-uv", "base"], ["base", "python-uv"]),
        (["base", "python-uv"], ["base", "python-uv"]),
        (["juguete", "base", "python-uv"], ["base", "juguete", "python-uv"]),
        (["base", "python-uv", "juguete"], ["base", "python-uv", "juguete"]),
    ],
)
def test_el_orden_respeta_requiere(escritas: list[str], aplicadas: list[str]) -> None:
    orden = stacks.resolve({"stack": {"plantillas": escritas}}, RAICES)
    assert [t.name for t in orden] == aplicadas


def test_una_plantilla_del_stack_que_no_existe() -> None:
    mensaje = _error(stacks.resolve, {"stack": {"plantillas": ["base", "rust", "go"]}})
    assert mensaje.splitlines() == [
        "la plantilla «rust» no existe; las que hay: base, python-uv",
        "la plantilla «go» no existe; las que hay: base, python-uv",
    ]


def test_un_requiere_que_no_esta_en_el_stack(tmp_path: Path) -> None:
    plantilla(
        tmp_path, "x", manifiesto_lenguaje("x", requiere='["base", "y"]'), partes("x")
    )
    mensaje = _error(
        stacks.resolve, {"stack": {"plantillas": ["base", "x"]}}, _base_y(tmp_path)
    )
    assert mensaje == "«x» requiere «y», que no está en stack.plantillas"


def test_un_ciclo_de_requiere_es_un_error(tmp_path: Path) -> None:
    plantilla(
        tmp_path, "a", manifiesto_lenguaje("a", requiere='["base", "b"]'), partes("a")
    )
    plantilla(
        tmp_path,
        "b",
        manifiesto_lenguaje("b", requiere='["a"]', extensiones='[".b"]', carpetas="[]"),
        partes("b"),
    )
    mensaje = _error(
        stacks.resolve, {"stack": {"plantillas": ["base", "a", "b"]}}, _base_y(tmp_path)
    )
    assert mensaje == "las plantillas se requieren en ciclo: a → b"


def test_solo_base_es_un_error() -> None:
    mensaje = _error(stacks.resolve, {"stack": {"plantillas": ["base"]}})
    assert "no tiene ninguna plantilla de lenguaje" in mensaje


def test_dos_plantillas_no_comparten_extension_ni_carpeta(tmp_path: Path) -> None:
    plantilla(
        tmp_path,
        "x",
        manifiesto_lenguaje("x", extensiones='[".py"]', carpetas='["tests/unit/"]'),
        partes("x"),
    )
    mensaje = _error(
        stacks.resolve,
        {"stack": {"plantillas": ["base", "python-uv", "x"]}},
        _base_y(tmp_path),
    )
    assert mensaje.splitlines() == [
        "la extensión «.py» es de «python-uv» y de «x»",
        "las carpetas «tests/» de «python-uv» y «tests/unit/» de «x» se solapan",
    ]


# ── Composición ─────────────────────────────────────────────────────────────


def _compuesto(*nombres: str, **opciones: str) -> dict[str, stacks.StackFile]:
    return stacks.compose(configuracion(*nombres, **opciones), RAICES)


def test_la_composicion_de_base_y_python_uv() -> None:
    ficheros = _compuesto("base", "python-uv")
    assert sorted(ficheros) == [
        ".claude/settings.json",
        ".github/workflows/ci.yml",
        ".gitignore",
        ".pre-commit-config.yaml",
        ".python-version",
        "AGENTS.md",
        "CLAUDE.md",
        "SECURITY.md",
        "pyproject.toml",
        "scripts/n1.sh",
        "scripts/n2.sh",
        "scripts/n3.sh",
        "scripts/stack/plantillas.txt",
        "scripts/stack/python-uv/n1.sh",
        "scripts/stack/python-uv/n3.sh",
        "src/demo_proyecto/__init__.py",
        "tests/test_humo.py",
    ]
    assert tomllib.loads(ficheros["pyproject.toml"].text)["project"]["name"] == (
        "demo-proyecto"
    )
    assert "import demo_proyecto\n" in ficheros["tests/test_humo.py"].text
    assert "ejemplo/proyecto/security" in ficheros["SECURITY.md"].text
    restos = [
        r for r, f in ficheros.items() if "{{" in f.text.replace("${{ github.", "")
    ]
    assert restos == []


def test_los_sh_salen_ejecutables() -> None:
    ficheros = _compuesto("base", "python-uv")
    ejecutables = sorted(r for r, f in ficheros.items() if f.executable)
    assert ejecutables == [
        "scripts/n1.sh",
        "scripts/n2.sh",
        "scripts/n3.sh",
        "scripts/stack/python-uv/n1.sh",
        "scripts/stack/python-uv/n3.sh",
    ]


def test_github_ref_sale_intacto_en_el_ci() -> None:
    ci = _compuesto("base", "python-uv")[stacks.CI_FILE].text
    assert "group: ci-${{ github.ref }}\n" in ci


def test_la_composicion_con_dos_plantillas_de_lenguaje() -> None:
    """El ejemplo de dos plantillas del plan, texto a texto."""
    ficheros = _compuesto("base", "python-uv", "juguete")
    assert ficheros["scripts/stack/plantillas.txt"].text.splitlines()[-2:] == [
        "python-uv .py .pyi src/ tests/",
        "juguete .jug juguete/",
    ]
    assert ficheros[".gitignore"].text == (
        ".cache/\n.env\n\n"
        ".venv/\n__pycache__/\n*.pyc\n.pytest_cache/\n.ruff_cache/\ndist/\nbuild/\n"
        "*.egg-info/\n\n*.jug.tmp\n"
    )
    ci = ficheros[stacks.CI_FILE].text
    pasos = yaml.safe_load(ci)["jobs"]["ci"]["steps"]
    assert [p["name"] for p in pasos] == [
        "Checkout",
        "Setup uv",
        "Sync dependencies",
        "Juguete",
        "N3",
    ]
    assert "        run: uv sync --frozen\n\n      - name: Juguete\n" in ci
    agentes = ficheros["AGENTS.md"].text
    assert agentes.index("## Python (python-uv)") < agentes.index("## Juguete")
    assert "\n\n## Juguete\n\n- Los ficheros `.jug` de demo-proyecto" in agentes
    assert agentes.endswith("son del juguete.\n")
    assert "scripts/stack/juguete/n1.sh" in ficheros


def test_el_pre_commit_fusionado_tiene_los_hooks_de_todas() -> None:
    texto = _compuesto("base", "python-uv", "juguete")[".pre-commit-config.yaml"].text
    repos = load_text(texto, ".yaml")["repos"]
    ids = [hook["id"] for repo in repos for hook in repo["hooks"]]
    assert ids == [
        "end-of-file-fixer",
        "trailing-whitespace",
        "check-yaml",
        "check-toml",
        "gitleaks",
        "ruff-format",
        "ruff-check",
        "pyright",
        "juguete",
    ]
    assert texto.count("repos:") == 1
    assert "\n\n  - repo: local\n    hooks:\n      - id: juguete\n" in texto


def test_el_marcador_del_ci_nunca_queda() -> None:
    """Sin pasos de lenguaje (juguete2 no trae CI), el marcador desaparece entero."""
    ci = _compuesto("base", "juguete2")[stacks.CI_FILE].text
    assert stacks.CI_MARKER.strip() not in ci
    assert "persist-credentials: false\n\n      - name: N3\n" in ci


def test_dos_plantillas_con_el_mismo_fichero_no_fusionable_es_un_error(
    tmp_path: Path,
) -> None:
    plantilla(
        tmp_path,
        "x",
        manifiesto_lenguaje("x"),
        partes("x") | {"SECURITY.md.plantilla": "otra\n"},
    )
    mensaje = _error(stacks.compose, configuracion("base", "x"), _base_y(tmp_path))
    assert mensaje == "«SECURITY.md» lo traen «base» y «x», y no es fusionable"


def test_un_fusionable_que_solo_declara_una_de_las_dos(tmp_path: Path) -> None:
    plantilla(
        tmp_path,
        "x",
        manifiesto_lenguaje("x"),
        partes("x") | {"AGENTS.md.plantilla": "## X\n"},
    )
    mensaje = _error(stacks.compose, configuracion("base", "x"), _base_y(tmp_path))
    assert mensaje == "«AGENTS.md» lo traen «base» y «x», y no es fusionable"


def test_dos_rutas_que_coinciden_despues_de_rellenar(tmp_path: Path) -> None:
    ficheros = partes("x") | {"src/demo_proyecto/__init__.py.plantilla": "x = 1\n"}
    plantilla(tmp_path, "x", manifiesto_lenguaje("x"), ficheros)
    mensaje = _error(
        stacks.compose,
        configuracion("base", "python-uv", "x"),
        _base_y(tmp_path),
    )
    assert (
        mensaje
        == "«src/demo_proyecto/__init__.py» lo traen «python-uv» y «x», y no es "
        "fusionable"
    )


def test_un_hueco_que_no_existe_sale_con_su_plantilla(tmp_path: Path) -> None:
    ficheros = partes("x") | {"x/a.txt.plantilla": "{{proyecto.nombr}}\n"}
    plantilla(tmp_path, "x", manifiesto_lenguaje("x"), ficheros)
    mensaje = _error(stacks.compose, configuracion("base", "x"), _base_y(tmp_path))
    assert mensaje.startswith("«x/x/a.txt», línea 1: la clave «proyecto.nombr»")


def test_un_menairos_toml_no_valido_es_un_error() -> None:
    configuracion_mala = configuracion("base", "python-uv")
    configuracion_mala["modo"] = {"defecto": "rapido"}
    assert "menairos.toml no es válido: modo.defecto" in _error(
        stacks.compose, configuracion_mala
    )


def test_un_yaml_compuesto_que_no_se_lee_es_un_error(tmp_path: Path) -> None:
    ficheros = partes("x") | {"x/a.yaml.plantilla": "a: 1\na: 2\n"}
    plantilla(tmp_path, "x", manifiesto_lenguaje("x"), ficheros)
    mensaje = _error(stacks.compose, configuracion("base", "x"), _base_y(tmp_path))
    assert mensaje.startswith("«x/a.yaml» compuesto no es válido: clave repetida")


# ── {{paquete}} ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("nombre", "paquete"),
    [("menairos", "menairos"), ("Mi-Proyecto", "mi_proyecto"), ("api-v2", "api_v2")],
)
def test_el_paquete_sale_del_nombre(nombre: str, paquete: str) -> None:
    assert stacks.package_name(nombre) == (paquete, None)


@pytest.mark.parametrize(
    ("nombre", "motivo"),
    [
        ("mi proyecto", "no sirve de nombre de paquete"),
        ("mi.proyecto", "no sirve de nombre de paquete"),
        ("2048", "no sirve de nombre de paquete"),
        ("año", "no sirve de nombre de paquete"),
        ("x-", "no sirve de nombre de paquete"),
        ("a--b", "no sirve de nombre de paquete"),
        ("_x", "no sirve de nombre de paquete"),
        ("K", "no sirve de nombre de paquete"),
        ("class", "palabra reservada"),
        ("json", "biblioteca estándar"),
        ("Os", "biblioteca estándar"),
    ],
)
def test_un_nombre_que_no_da_paquete_es_un_error(nombre: str, motivo: str) -> None:
    _, problema = stacks.package_name(nombre)
    assert problema is not None and motivo in problema
    assert motivo in _error(
        stacks.compose, configuracion("base", "python-uv", nombre=nombre)
    )


def test_un_nombre_sin_paquete_vale_si_ninguna_plantilla_usa_el_hueco() -> None:
    ficheros = _compuesto("base", "juguete", nombre="mi proyecto")
    assert "de mi proyecto son del juguete" in ficheros["AGENTS.md"].text


# ── .claude/settings.json ───────────────────────────────────────────────────


def _ajustes(**opciones: str) -> dict[str, object]:
    texto = _compuesto("base", "python-uv", "juguete", **opciones)[
        stacks.SETTINGS_FILE
    ].text
    assert texto.endswith("}\n")
    return json.loads(texto)


def test_los_ajustes_son_iguales_en_los_tres_modos() -> None:
    """En el H0 el modo no cambia el fichero (P2): es uno por repo."""
    manual = _ajustes(modo="manual")
    assert _ajustes(modo="didactico") == manual == _ajustes(modo="automatico")


def test_los_ajustes_unen_las_reglas_de_cada_plantilla_sin_repetir() -> None:
    permisos = _ajustes()["permissions"]
    assert isinstance(permisos, dict)
    assert permisos["ask"] == ["Bash(menairos cierre * --aprobar)"]
    assert permisos["allow"][-4:] == [
        "Bash(git push *)",
        "Bash(uv run *)",
        "Bash(uv sync *)",
        "Bash(juguete *)",
    ]
    assert permisos["allow"].count("Bash(git status *)") == 1
    assert "Bash(gh pr merge *)" in permisos["deny"]


def test_el_marketplace_se_fija_a_la_version() -> None:
    ajustes = _ajustes(version="3.1.0")
    assert ajustes["extraKnownMarketplaces"] == {
        "menairos": {
            "source": {"source": "github", "repo": "pdromer0/menairos", "ref": "v3.1.0"}
        }
    }
    assert ajustes["enabledPlugins"] == {"menairos@menairos": True}


def test_una_prerelease_va_sin_ref() -> None:
    """3.0.0-dev no tiene etiqueta todavía: sigue la rama por defecto (T-04)."""
    fuente = _ajustes(version="3.0.0-dev")["extraKnownMarketplaces"]
    assert fuente == {
        "menairos": {"source": {"source": "github", "repo": "pdromer0/menairos"}}
    }


# ── Equivalencia con los ficheros de Menairos (decisión 1 de Pedro) ─────────

COMPARADOS = (
    "scripts/n1.sh",
    "scripts/n2.sh",
    "scripts/n3.sh",
    "scripts/stack/plantillas.txt",
    "scripts/stack/python-uv/n1.sh",
    "scripts/stack/python-uv/n3.sh",
    ".github/workflows/ci.yml",
    ".pre-commit-config.yaml",
)

# Lo que el repo de Menairos tiene («+») y la composición no, o al revés («-»).
# Una diferencia que no esté aquí pone el CI en rojo, y una de aquí que ya no
# exista, también.
DIFERENCIAS = {
    (
        "scripts/n3.sh",
        "+",
        "# En Menairos, la N3 valida también la especificación del propio repo.",
    ),
    ("scripts/n3.sh", "+", "paso spec uv run --frozen menairos spec validar"),
    (
        ".pre-commit-config.yaml",
        "+",
        "        # Esta plantilla solo es YAML una vez rellena "
        "(hito: {{hito.numero}}): la comprueban los tests.",
    ),
    (
        ".pre-commit-config.yaml",
        "+",
        r"        exclude: ^src/menairos/plantillas/docs/hito-N\.tareas\.yaml$",
    ),
}


def _diferencias(ruta: str, repo: str, compuesto: str) -> set[tuple[str, str, str]]:
    a, b = repo.splitlines(), compuesto.splitlines()
    encontradas: set[tuple[str, str, str]] = set()
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for etiqueta, i1, i2, j1, j2 in matcher.get_opcodes():
        if etiqueta != "equal":
            encontradas |= {(ruta, "+", linea) for linea in a[i1:i2]}
            encontradas |= {(ruta, "-", linea) for linea in b[j1:j2]}
    if repo.endswith("\n") != compuesto.endswith("\n"):
        encontradas.add((ruta, "+" if repo.endswith("\n") else "-", "(salto final)"))
    return encontradas


def test_la_composicion_de_menairos_es_la_del_repo() -> None:
    """base + python-uv con el menairos.toml del repo dan sus scripts, CI y hooks."""
    configuracion_repo = load_document(RAIZ / "menairos.toml")
    ficheros = stacks.compose(configuracion_repo)
    encontradas: set[tuple[str, str, str]] = set()
    for ruta in COMPARADOS:
        repo = (RAIZ / ruta).read_text(encoding="utf-8")
        encontradas |= _diferencias(ruta, repo, ficheros[ruta].text)
    assert encontradas == DIFERENCIAS


@pytest.mark.parametrize("ruta", [r for r in COMPARADOS if r.endswith(".sh")])
def test_los_scripts_de_menairos_son_ejecutables(ruta: str) -> None:
    assert (RAIZ / ruta).stat().st_mode & 0o111


# ── El contrato ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ruta", "extension"),
    [
        ("a.py", ".py"),
        ("a.b.py", ".py"),
        ("tests/x/a.py", ".py"),
        (".py", ""),
        ("..py", ""),
        (".bashrc.py", ".py"),
        ("x.", ""),
        ("tests", ""),
        ("dir.d/fichero", ""),
    ],
)
def test_la_extension_de_una_ruta(ruta: str, extension: str) -> None:
    assert stacks.extension(ruta) == extension


def _contrato(tmp_path: Path | None = None) -> Contract:
    return stacks.contract(
        configuracion("base", "python-uv", "juguete"), tmp_path, RAICES
    )


# (ruta, plantilla dueña): los mismos casos los reparte scripts/n1.sh en
# test_scripts_contrato.py (test diferencial).
DUENAS = [
    ("tests/test_a.py", "python-uv"),
    ("./tests/test_a.py", "python-uv"),
    ("tests", "python-uv"),
    ("tests/", "python-uv"),
    ("tests/data/x.json", "python-uv"),
    ("tests/c.jug", "juguete"),
    ("juguete/b.jug", "juguete"),
    ("juguete/x.py", "python-uv"),
    ("juguete", "juguete"),
    ("a.b.py", "python-uv"),
    ("tests/con espacio.py", "python-uv"),
    ("src/paquete/m.pyi", "python-uv"),
    ("x/.py", None),
    ("docs/x.md", None),
    ("testsx/a.txt", None),
    ("pyproject.toml", None),
]


@pytest.mark.parametrize(("ruta", "duena"), DUENAS)
def test_la_duena_de_una_ruta(ruta: str, duena: str | None) -> None:
    owner = _contrato().owner(ruta)
    assert (owner.name if owner else None) == duena


def test_la_extension_gana_a_la_carpeta() -> None:
    owner = _contrato().owner("tests/c.jug")
    assert owner is not None and owner.name == "juguete"


def test_owner_con_ruta_absoluta(tmp_path: Path) -> None:
    contrato = Contract([Owner("python-uv", (".py",), ("tests/",), {})], tmp_path)
    owner = contrato.owner(tmp_path / "tests" / "data" / "x.txt")
    assert owner is not None and owner.name == "python-uv"
    assert contrato.relative(tmp_path / "src" / ".." / "a.py") == "a.py"


@pytest.mark.parametrize("ruta", ["../fuera.py", "/etc/passwd", "tests/../../x.py"])
def test_una_ruta_fuera_del_repo_es_un_error(tmp_path: Path, ruta: str) -> None:
    contrato = Contract([], tmp_path)
    assert "está fuera del repo" in _error(contrato.owner, ruta)


def test_el_formato_se_elige_por_extension() -> None:
    contrato = _contrato()
    assert contrato.format_command("src/a b.py") == (
        "uv run --frozen ruff format 'src/a b.py'"
    )
    assert contrato.format_command("tests/c.jug") == "juguete-formato tests/c.jug"
    assert contrato.format_command("tests/data/x.json") is None
    assert contrato.format_command("docs/x.md") is None


def test_las_plantillas_de_los_ficheros_tocados() -> None:
    contrato = _contrato()
    tocados = ["docs/x.md", "juguete/b.jug", "pyproject.toml", "src/a.py"]
    assert contrato.templates_for(tocados) == ("python-uv", "juguete")
    assert contrato.templates_for(["docs/x.md"]) == ()


def test_las_ordenes_de_tests_de_unas_rutas() -> None:
    ordenes = _contrato().tests_commands(["tests/c.jug", "tests/a b.py", "tests"])
    assert ordenes == [
        ("python-uv", "uv run --frozen pytest -m \"not slow\" 'tests/a b.py' tests"),
        ("juguete", "scripts/stack/juguete/n1.sh tests/c.jug"),
    ]


def test_una_ruta_de_tests_sin_duena_es_un_error() -> None:
    mensaje = _error(_contrato().tests_commands, ["tests/a.py", "docs/x.md"])
    assert mensaje == "la ruta «docs/x.md» no es de ninguna plantilla"


def test_con_la_raiz_la_propiedad_sale_de_plantillas_txt(tmp_path: Path) -> None:
    lista = tmp_path / stacks.OWNERSHIP_FILE
    lista.parent.mkdir(parents=True)
    lista.write_text("# comentario\npython-uv .py\njuguete .jug tests/\n", "utf-8")
    contrato = _contrato(tmp_path)
    owner = contrato.owner("tests/data/x.json")
    assert owner is not None and owner.name == "juguete"
    assert contrato.owners[0].orders["lint"] == "uv run --frozen ruff check ."


def test_plantillas_txt_con_una_plantilla_que_no_es_del_stack(tmp_path: Path) -> None:
    lista = tmp_path / stacks.OWNERSHIP_FILE
    lista.parent.mkdir(parents=True)
    lista.write_text("rust .rs\n", "utf-8")
    assert "nombra «rust»" in _error(_contrato, tmp_path)


def test_sin_plantillas_txt_es_un_error(tmp_path: Path) -> None:
    assert "no se puede leer" in _error(_contrato, tmp_path)


def test_el_contrato_de_menairos() -> None:
    contrato = stacks.contract(load_document(RAIZ / "menairos.toml"), RAIZ)
    assert [o.name for o in contrato.owners] == ["python-uv"]
    assert contrato.format_command(RAIZ / "src" / "menairos" / "stacks.py") == (
        "uv run --frozen ruff format src/menairos/stacks.py"
    )


def test_los_juguetes_solo_viven_en_los_tests() -> None:
    assert set(stacks.available((JUGUETES,))) == {"juguete", "juguete2"}
    assert not set(stacks.available()) & {"juguete", "juguete2"}
