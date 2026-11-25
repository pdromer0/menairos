# ADR 0001 — Menairos es la v3 del método

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 19 del diseño del método

## Contexto

El método v2 funciona en dos proyectos, pero se copia a mano entre ellos y sus mejoras no llegan a los demás. Hacía falta decidir si el método nuevo es una evolución o un proyecto aparte, y cómo se versiona.

## Decisión

- Menairos es la **v3** del método: continúa la v2 y reutiliza lo probado, generalizado (el ciclo de `tarea.md`, `revisor-plan`, `mutante`, los niveles N1–N3, los ADRs, el anexo y los módulos con disparadores).
- Versionado semántico: *mayor* si cambia un contrato (YAML de tareas, contrato de plantillas, `menairos.toml`); *menor*, un módulo o una plantilla nueva; *parche*, correcciones. La primera versión publicada es `v3.0.0`.
- Cada proyecto fija su versión en `menairos.toml`; `/actualizar-menairos` aplica las migraciones en un PR (en un cambio mayor, siempre con revisión de Pedro).
- Los proyectos que usan el método v2 siguen con él, sin migrar.
- Menairos se construye con el propio método: el hito 0 en modo manual.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Las piezas probadas del método v2 se traen como plantillas, subagentes y órdenes de la CLI, no como copias sueltas.
- Un cambio de contrato obliga a una versión mayor y a una migración.
