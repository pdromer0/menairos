# ADR 0020 — Stack de Menairos: Python 3.14 con uv

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** stack
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** `diseno.md` 5

## Contexto

Menairos necesita un stack para su CLI que sea, además, la primera plantilla que ofrece a otros proyectos.

## Decisión

- **Python 3.14 con uv**, ruff, pytest con timeout, pyright y pre-commit con gitleaks: el stack ya probado con el método v2.
- Bash solo para los hooks y los envoltorios mínimos; la lógica, en Python con tests.
- Dependencias mínimas: TOML de la biblioteca estándar, un validador de JSON Schema y un lector de YAML; GitHub, por `gh api`.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Menairos se come su propia comida: su repo sigue la plantilla `python-uv`.
- Las versiones se verifican con herramientas en el momento, no de memoria.
