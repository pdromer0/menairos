# ADR 0018 — Esquemas JSON como contrato versionado

- **Estado:** Aceptada
- **Fecha:** 2026-11-25
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** `diseno.md` 2.5

## Contexto

`menairos.toml`, el YAML de tareas y los ficheros de decisiones los escriben modelos y personas, y los leen scripts: necesitan una forma comprobable.

## Decisión

- JSON Schema versionados para los tres formatos; los usa `menairos spec validar` y documentan el contrato.
- Una clave desconocida es un error (`additionalProperties: false`).

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- Un cambio de esquema que rompa la compatibilidad es una versión mayor (ADR 0001).
