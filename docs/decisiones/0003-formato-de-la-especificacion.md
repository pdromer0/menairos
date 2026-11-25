# ADR 0003 — Formato de la especificación: documentos y tareas en YAML

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** proceso
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** punto 8 del diseño del método

## Contexto

Las especificaciones dependían de una conversación larga con el chat, sin un formato que un script pudiera comprobar ni publicar.

## Decisión

- `/crear-spec` produce `docs/producto.md` (el qué), `docs/diseno.md` (el cómo), `docs/hitos.md` (hoja de ruta con la demo funcional de cada hito), `docs/decisiones/` (ADRs), `docs/specs/hito-N.md` con su anexo, `docs/specs/hito-N.tareas.yaml` y `docs/abiertas.md`, además de `menairos.toml`.
- **Solo se detalla el próximo hito**; la revisión de cada hito alimenta la especificación del siguiente.
- **Las tareas van en YAML**: id, título, rama, dependencias, criterios de aceptación comprobables, `critica` con su motivo, `donde`, quién la hace, `area` y las secciones que enlaza. El issue resume y enlaza; nunca copia la especificación.
- `producto.md` y `diseno.md` van separados: primero se valida el qué y después el cómo.
- Cada hito lleva su **validación funcional** escrita de antemano.
- La conversación tiene dos modos (lluvia de ideas y MVP) y se guarda por fases.

## Alternativas consideradas

- No constan alternativas discutidas en la especificación para esta decisión.

## Consecuencias

- El YAML de tareas es un contrato con esquema (ADR 0018): cambiarlo es una versión mayor.
- La capa 1 de `/validar-spec` puede comprobar la especificación sin modelo.
