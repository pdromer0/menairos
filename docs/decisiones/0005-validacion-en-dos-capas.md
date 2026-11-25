# ADR 0005 — Validación en dos capas y publicación con OK de Pedro

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** reversible
- **Origen:** punto 10 del diseño del método

## Contexto

Una especificación con errores de forma o ambigua se paga después, en paradas y correcciones durante la implementación.

## Decisión

- **Capa 1, un script sin tokens**: YAML válido, criterios presentes, dependencias sin ciclos, enlaces a secciones que existen, `abiertas.md` justificado, ADR de stack, validación funcional y plantilla del stack. Si falla, no se llama al modelo.
- **Capa 2, un revisor con contexto limpio**, configurable (Codex o Claude): coherencia, ambigüedad, criterios comprobables, cobertura de los casos de uso, tamaño de las tareas, etiqueta `critica` y predicción de paradas.
- Ciclo: el revisor propone, el autor aplica y las preguntas van a Pedro; como máximo dos rondas.
- **Publicación** (milestone, issues, dependencias y etiquetas) solo sin bloqueantes y con el OK de Pedro, con un script idempotente.

## Alternativas consideradas

- Revisor de la capa 2: Codex o Claude; queda configurable en `menairos.toml` (`revisores.spec`).

## Consecuencias

- Las paradas predichas se le preguntan a Pedro antes de arrancar el hito (ADR 0011).
