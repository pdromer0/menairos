"""Comprobación deliberada del CI: este test falla a propósito y se revierte."""


def test_fallo_deliberado() -> None:
    """Comprobación deliberada: debe fallar en el CI; el commit se revierte."""
    assert 1 == 2
