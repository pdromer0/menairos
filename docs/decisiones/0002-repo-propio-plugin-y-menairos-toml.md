# ADR 0002 — Repo propio, plugin de Claude Code y `menairos.toml`

- **Estado:** Aceptada
- **Fecha:** 2026-11-24
- **Tipo:** arquitectura
- **Decidido por:** Pedro
- **Reversibilidad:** difícil de revertir
- **Origen:** punto 7 del diseño del método

## Contexto

Con el método v2, cada proyecto nuevo copia el método a mano y cuesta un hito 0 de configuración; las mejoras de un proyecto no llegan a los demás.

## Decisión

- El método vive en **un repo propio** (`pdromer0/menairos`) y se distribuye como **plugin de Claude Code**, con los comandos, los subagentes, los hooks y las plantillas.
- Lo propio de cada proyecto va en **un único fichero**, `menairos.toml`: nombres, idioma, stack, umbrales y módulos activos.
- **`AGENTS.md` es la fuente común** de instrucciones, para que Codex siga el mismo método.
- El método está versionado y cada proyecto anota qué versión usa.
- Comandos en minúsculas y con guiones (`/crear-spec`).

## Alternativas consideradas

- Seguir copiando el método a mano entre proyectos, como en el método v2: descartado por el coste de cada hito 0 y porque las mejoras no se propagan.

## Consecuencias

- Las mejoras llegan a los proyectos actualizando el plugin.
- Hay que verificar que el plugin se instala solo en la nube y en Actions (plan B en `diseno.md` 2.1).
- Actualización (2026-11-26, T-04): en local, el plugin carga con el `.claude/settings.json` del proyecto; en la nube, lo instala el script de entorno (el `settings.json` del repo no basta); en Actions, por verificar en T-26. Ver `diseno.md` 2.1.
