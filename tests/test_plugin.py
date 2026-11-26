"""Tests del marketplace, del manifiesto del plugin y de la skill hola."""

import json
import re
from importlib.metadata import version
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
MARKETPLACE = RAIZ / ".claude-plugin" / "marketplace.json"
PLUGIN = RAIZ / "plugin" / ".claude-plugin" / "plugin.json"
SKILL = RAIZ / "plugin" / "skills" / "hola" / "SKILL.md"


def _leer_json(ruta: Path) -> dict[str, Any]:
    """Lee un fichero JSON y comprueba que su raíz es un objeto."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(datos, dict), f"{ruta} no es un objeto JSON"
    return datos


def test_marketplace_es_json_valido_con_sus_campos_obligatorios() -> None:
    """marketplace.json tiene name, owner.name y plugins, cada uno con name y source."""
    marketplace = _leer_json(MARKETPLACE)
    assert marketplace["name"]
    assert marketplace["owner"]["name"]
    plugins = marketplace["plugins"]
    assert isinstance(plugins, list) and plugins
    for entrada in plugins:
        assert entrada["name"]
        assert entrada["source"]


def test_plugin_json_es_json_valido_con_sus_campos_obligatorios() -> None:
    """plugin.json tiene name, version, description y author.name."""
    plugin = _leer_json(PLUGIN)
    assert plugin["name"]
    assert plugin["version"]
    assert plugin["description"]
    assert plugin["author"]["name"]


def test_la_entrada_del_marketplace_se_llama_como_el_plugin() -> None:
    """La entrada del marketplace lleva el mismo name que plugin.json."""
    entrada = _leer_json(MARKETPLACE)["plugins"][0]
    assert entrada["name"] == _leer_json(PLUGIN)["name"]


def test_el_source_de_la_entrada_existe_y_contiene_el_plugin() -> None:
    """El source es relativo (./), existe y contiene .claude-plugin/plugin.json."""
    source = _leer_json(MARKETPLACE)["plugins"][0]["source"]
    assert isinstance(source, str) and source.startswith("./")
    carpeta = RAIZ / source
    assert carpeta.is_dir()
    assert (carpeta / ".claude-plugin" / "plugin.json").resolve() == PLUGIN


def test_la_version_de_plugin_json_es_la_del_paquete() -> None:
    """La version de plugin.json es la del paquete menairos."""
    assert _leer_json(PLUGIN)["version"] == version("menairos")


def test_la_version_de_la_skill_es_la_del_paquete() -> None:
    """La línea de respuesta de la skill hola lleva la versión del paquete."""
    texto = SKILL.read_text(encoding="utf-8")
    encontrada = re.search(r"menairos (\S+) · cargado desde:", texto)
    assert encontrada is not None, "SKILL.md no tiene la línea de respuesta"
    assert encontrada.group(1) == version("menairos")
