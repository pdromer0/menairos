"""Tests de humo del paquete menairos."""

import pytest

import menairos
from menairos.cli import main


def test_version_devuelve_cero_e_imprime_la_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--version` devuelve 0 e imprime exactamente "menairos <versión>"."""
    codigo = main(["--version"])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert salida == "menairos " + menairos.__version__ + "\n"


def test_version_del_paquete() -> None:
    """La versión del paquete procede de pyproject.toml y es 3.0.0.dev0."""
    assert menairos.__version__ == "3.0.0.dev0"


def test_sin_argumentos_devuelve_cero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sin argumentos se imprime la ayuda y se devuelve 0."""
    codigo = main([])
    salida = capsys.readouterr().out
    assert codigo == 0
    assert "menairos" in salida
