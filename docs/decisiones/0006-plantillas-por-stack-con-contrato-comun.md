# ADR 0006 — Plantillas por stack con contrato común

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** punto 11 del diseño del método

## Contexto

Cada proyecto nuevo montaba a mano su entorno, su CI y sus comprobaciones; `/implementar` necesita funcionar igual sea cual sea el lenguaje.

## Decisión

- `/preparar-entorno` con scripts idempotentes y un modo `--comprobar`, en cuatro capas: local (WSL2), repo, GitHub (por la API) y nube.
- **Plantillas mantenidas por stack**, empezando por Python + uv, y **componibles**: base + lenguaje + extras.
- **Contrato común** de toda plantilla: las órdenes de lint, formato, tipos y tests; los scripts N1, N2 y N3; pre-commit; el job de CI; los permisos del agente; y la sección de comandos de `AGENTS.md`.
- Una tecnología sin plantilla la crea el primer proyecto que la usa, en modo manual, con las versiones verificadas con herramientas y sus comprobaciones deliberadas.
- El modo automático no arranca con una plantilla sin validar.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Cambiar el contrato común es una versión mayor.
- Los pasos manuales de Pedro quedan en una lista corta, verificada después por la API.
